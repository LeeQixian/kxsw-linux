import json
import shutil
import subprocess

from . import claude, gemini, gpt, grok
from .core import BASE_PORT, BIN, ROOT, Result, cleanup, free_port, load, provider_of, start

SERVICES = (
    ("claude", claude.check, "ai-claude"),
    ("gpt", gpt.check, "ai-gpt"),
    ("gemini", gemini.check, "google-ai"),
    ("grok", grok.check, "ai-grok"),
)


def probe_node(ob, port, extra, label):
    print(f"{label}{ob['tag']} ...", flush=True)
    p = start(ob, port, extra if ob.get("detour") else None)
    if p is None:
        print("    start-failed", flush=True)
        cleanup(port)
        return None
    row = {}
    try:
        for name, fn, _ in SERVICES:
            r = fn(port)
            row[name] = r
            print(f"    {name}: {r.text}", flush=True)
        return row
    finally:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
        cleanup(port)


def _dump(result):
    out = {t: {k: v.text for k, v in r.items()} for t, r in result.items()}
    (ROOT / "cache").mkdir(parents=True, exist_ok=True)
    (ROOT / "cache" / "unlock-result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))


def scan(nodes, extra=None):
    if not BIN.exists():
        shutil.copy("/usr/bin/sing-box", BIN)
    result = {}
    total = len(nodes)
    for i, ob in enumerate(nodes, 1):
        tag = ob["tag"]
        print(f"[{i}/{total}] {tag} ...", flush=True)
        port = free_port(BASE_PORT + i)
        use_extra = [o for o in (extra or []) if o["tag"] != tag] if ob.get("detour") else []
        row = probe_node(ob, port, use_extra, "")
        if row is None:
            row = {name: Result("start-failed") for name, _, _ in SERVICES}
        result[tag] = row
        _dump(result)
    retry = [next(ob for ob in nodes if ob["tag"] == tag)
             for tag, r in result.items()
             if all(v.text == "unreachable" for v in r.values())]
    if retry:
        print(f"retry pass: {len(retry)} all-unreachable nodes", flush=True)
        for j, ob in enumerate(retry, 1):
            tag = ob["tag"]
            print(f"[retry {j}/{len(retry)}] {tag} ...", flush=True)
            use_extra = [o for o in (extra or []) if o["tag"] != tag] if ob.get("detour") else []
            row = probe_node(ob, free_port(BASE_PORT + total + j), use_extra, "[retry]")
            if row is not None and any(v.ok for v in row.values()):
                result[tag] = row
                _dump(result)
    return result


def sync():
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text())
    purity = [p["sp"] for p in cfg.get("providers", []) if p.get("purity")]
    if not purity:
        print("no purity providers")
        return
    groups = {g["tag"]: g for g in cfg.get("groups", [])}
    missing = [group for _, _, group in SERVICES if group not in groups]
    if missing:
        print(f"error: missing groups: {sorted(missing)}")
        return
    all_nodes, extra = load()
    pool = [n for n in all_nodes if provider_of(n["tag"], purity)]
    if not pool:
        print("no nodes from purity providers")
        return
    print(f"scanning {len(pool)} nodes from {','.join(purity)}")
    result = scan(pool, extra)
    failed = sum(1 for r in result.values() if all(v.text == "start-failed" for v in r.values()))
    if failed * 2 > len(result):
        print(f"error: {failed}/{len(result)} nodes start-failed, abnormal batch, config unchanged")
        print("check cache/unlock-failed/ for instance logs")
        return
    updates = {}
    for name, _, group in SERVICES:
        ok = [tag for tag, r in result.items() if r[name].ok]
        if not ok:
            print(f"error: {group}: no unlocked nodes, config unchanged")
            return
        updates[group] = ok
    for group, ok in updates.items():
        groups[group]["nodes"] = ok
        print(f"{group}: {len(ok)} nodes")
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print("run singbox-update to apply")


def main():
    sync()


if __name__ == "__main__":
    main()
