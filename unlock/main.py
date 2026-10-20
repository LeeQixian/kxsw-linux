import json
import shutil

from . import aistudio, claude, gemini, gpt, grok
from .core import BASE_PORT, BIN, ROOT, Result, cleanup, load, provider_of, start

SERVICES = (
    ("claude", claude.check, "ai-claude"),
    ("gpt", gpt.check, "ai-gpt"),
    ("gemini", gemini.check, "ai-gemini"),
    ("aistudio", aistudio.check, "ai-aistudio"),
    ("grok", grok.check, "ai-grok"),
)
WIDTH = 18


def scan(nodes):
    if not BIN.exists():
        shutil.copy("/usr/bin/sing-box", BIN)
    result = {}
    for i, ob in enumerate(nodes):
        port = BASE_PORT + i
        p = start(ob, port)
        if p is None:
            result[ob["tag"]] = {name: Result("start-failed") for name, _, _ in SERVICES}
            continue
        result[ob["tag"]] = {name: fn(port) for name, fn, _ in SERVICES}
        p.terminate()
        p.wait()
        cleanup(port)
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
    nodes = load()
    pool = [n for n in nodes if provider_of(n["tag"], purity)]
    if not pool:
        print("no nodes from purity providers")
        return
    print(f"scanning {len(pool)} nodes from {','.join(purity)}")
    result = scan(pool)
    print(f"{'node':<30}" + "".join(f"{name:<{WIDTH}}" for name, _, _ in SERVICES))
    for tag, r in result.items():
        print(f"{tag:<30}" + "".join(f"{r[name].text:<{WIDTH}}" for name, _, _ in SERVICES))
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
