#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.common import dedup_rename

ROOT = Path(__file__).parent.parent
SOURCE = "ovo"
UA = "sing-box"

INFO_KEYS = ("剩余流量", "剩余", "重置", "到期", "套餐", "官网", "http")


def _is_info(tag):
    return any(k in tag for k in INFO_KEYS)


def parse(raw, source=SOURCE):
    data = json.loads(raw)
    rows = []
    for ob in data.get("outbounds", []):
        if not isinstance(ob, dict):
            continue
        if ob.get("type") != "hysteria2":
            continue
        tag = ob.get("tag", "")
        if _is_info(tag):
            continue
        server = ob.get("server", "")
        port = str(ob.get("server_port", ""))
        tls = ob.get("tls") or {}
        sni = tls.get("server_name", "")
        insecure = "true" if tls.get("insecure") else "false"
        password = ob.get("password", "")
        if not server or not port:
            continue
        rows.append([server, port, "hysteria2", password, sni, "true", insecure, tag, source])

    return dedup_rename(rows, source)


def main():
    cache = ROOT / "cache" / f"{SOURCE}.txt"
    if not cache.exists():
        print(f"[{SOURCE}] no cache file", file=sys.stderr)
        sys.exit(1)
    raw = cache.read_text(encoding="utf-8").strip()
    if not raw:
        print(f"[{SOURCE}] cache empty", file=sys.stderr)
        sys.exit(1)
    rows = parse(raw, SOURCE)
    out = ROOT / "nodes" / f"{SOURCE}-hy2.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["server", "port", "proto", "password", "sni", "udp", "skip_cert", "name", "source"])
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    main()
