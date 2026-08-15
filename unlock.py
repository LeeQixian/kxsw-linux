#!/usr/bin/env python3
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent
BIN = Path(tempfile.gettempdir()) / "aria2c"
GPT_URL = "https://chatgpt.com/cdn-cgi/trace"
GEMINI_URL = "https://aistudio.google.com/prompts/new_chat"
BASE_PORT = 19000


def load():
    cfg = json.loads((ROOT / "sing-box.json").read_text())
    nodes = [o for o in cfg["outbounds"] if o.get("type") not in ("urltest", "selector")]
    groups = {g["tag"]: g["outbounds"] for g in cfg["outbounds"] if g.get("type") in ("urltest", "selector")}
    return nodes, groups


def provider_of(tag, sps):
    segs = set(tag.split("-"))
    for sp in sps:
        if sp in segs:
            return sp
    return None


def pick(nodes, groups, args):
    if not args or "all" in args:
        return nodes
    wanted = set(args)
    chosen = set()
    for a in wanted:
        chosen.update(groups.get(a, [a]))
    return [n for n in nodes if n["tag"] in chosen or any(a in n["tag"].split("-") for a in wanted)]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start(ob, port):
    cfg = {
        "log": {"level": "error"},
        "dns": {"servers": [{"type": "udp", "tag": "ali", "server": "223.5.5.5", "server_port": 53}], "final": "ali"},
        "inbounds": [{"type": "socks", "listen": "127.0.0.1", "listen_port": port}],
        "outbounds": [ob],
        "route": {"final": ob["tag"]},
    }
    base = Path(tempfile.gettempdir()) / f"unlock-{port}"
    cfg_path = base.with_suffix(".json")
    cfg_path.write_text(json.dumps(cfg))
    log = open(base.with_suffix(".log"), "w")
    p = subprocess.Popen([str(BIN), "run", "-c", str(cfg_path)], stdout=log, stderr=log)
    for _ in range(50):
        if port_open(port):
            return p
        if p.poll() is not None:
            return None
        time.sleep(0.1)
    return p


def probe(port, url):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-x", f"socks5h://127.0.0.1:{port}", "-L", "-w", "\n%{http_code}|%{url_effective}", url],
        capture_output=True,
        text=True,
    )
    body, _, meta = r.stdout.rpartition("\n")
    parts = (meta.split("|") + ["?", "?"])[:2]
    return body, parts[0], parts[1]


def gpt_verdict(status, body):
    if status == "000":
        return "unreachable"
    if status == "200":
        loc = next((l.split("=", 1)[1] for l in body.splitlines() if l.startswith("loc=")), "")
        return f"OK({loc})" if loc else "no-trace"
    if "blocked" in body.lower() or "error" in body.lower():
        return "blocked"
    return f"HTTP{status}"


def gemini_verdict(status, final):
    if status == "000":
        return "unreachable"
    if "aistudio.google.com" in final:
        return f"OK({status})"
    if "accounts.google.com" in final:
        return "OK(login)"
    host = final.split("/")[2] if "://" in final else final
    return f"{status}->{host}"


def cleanup(port):
    base = Path(tempfile.gettempdir()) / f"unlock-{port}"
    for f in (base.with_suffix(".json"), base.with_suffix(".log")):
        f.unlink(missing_ok=True)


def scan(nodes):
    if not BIN.exists():
        shutil.copy("/usr/bin/sing-box", BIN)
    result = {}
    for i, ob in enumerate(nodes):
        port = BASE_PORT + i
        p = start(ob, port)
        if p is None:
            result[ob["tag"]] = ("start-failed", "start-failed")
            continue
        gbody, gstatus, _ = probe(port, GPT_URL)
        _, estatus, efinal = probe(port, GEMINI_URL)
        p.terminate()
        p.wait()
        result[ob["tag"]] = (gpt_verdict(gstatus, gbody), gemini_verdict(estatus, efinal))
        cleanup(port)
    return result


def sync(sp=None):
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text())
    sps = [p["sp"] for p in cfg.get("providers", [])]
    purity_sps = [sp_ for sp_ in sps if any(p.get("purity") for p in cfg.get("providers", []) if p["sp"] == sp_)]
    ai = next((g for g in cfg.get("groups", []) if g.get("tag") == "ai"), None)
    if ai is None or "nodes" not in ai:
        print("error: ai group must exist with nodes list")
        return
    if sp:
        if sp not in sps:
            print(f"error: unknown provider {sp}")
            return
        if not any(p.get("purity") for p in cfg.get("providers", []) if p["sp"] == sp):
            print(f"error: {sp} has no purity flag")
            return
        purity_sps = [sp]
    if not purity_sps:
        print("no purity providers")
        return
    nodes, _ = load()
    keep = [t for t in ai["nodes"] if provider_of(t, sps) not in purity_sps]
    for sp in purity_sps:
        pool = [n for n in nodes if sp in n["tag"].split("-")]
        if not pool:
            continue
        print(f"scanning {sp}: {len(pool)} nodes")
        result = scan(pool)
        ok = [t for t, (g, e) in result.items() if g.startswith("OK(") and e.startswith("OK(")]
        for t, (g, e) in result.items():
            print(f"  {t:<30}{g:<12}{e}")
        if ok:
            keep.extend(ok)
        else:
            print(f"warning: {sp}: no dual-unlock nodes, removed from ai")
    ai["nodes"] = keep
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"ai group: {len(keep)} nodes written to config.json")
    print("run singbox-update to apply")


def main():
    if sys.argv[1:] and sys.argv[1] == "--sync":
        sync(sys.argv[2] if len(sys.argv) > 2 else None)
        return
    nodes, groups = load()
    targets = pick(nodes, groups, sys.argv[1:])
    if not targets:
        print("no nodes matched")
        return
    print(f"{'node':<30}{'gpt':<12}gemini")
    for tag, (g, e) in scan(targets).items():
        print(f"{tag:<30}{g:<12}{e}")


if __name__ == "__main__":
    main()
