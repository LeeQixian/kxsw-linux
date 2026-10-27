#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.common import dedup_rename

ROOT = Path(__file__).parent.parent
SOURCE = "Monika"

INFO_KEYS = ("剩余", "重置", "到期", "套餐", "官网", "http", "过期", "流量")


def _is_info(tag):
    return any(k in tag for k in INFO_KEYS)


def parse(raw, source=SOURCE):
    data = json.loads(raw)
    rows = []
    for ob in data.get("outbounds", []):
        if not isinstance(ob, dict):
            continue
        typ = ob.get("type")
        tag = ob.get("tag", "")
        if _is_info(tag):
            continue
        server = ob.get("server", "")
        port = str(ob.get("server_port", ""))
        if not server or not port:
            continue
        tls = ob.get("tls") or {}
        sni = tls.get("server_name", "")
        insecure = "1" if tls.get("insecure") else "0"
        if typ == "tuic":
            proto = "tuic"
            cred = ob.get("uuid", "")
            token = ob.get("password", "")
            cc = ob.get("congestion_control", "bbr")
            rows.append([server, port, proto, cred, token, cc, sni, insecure, tag, source])
        elif typ == "shadowsocks":
            proto = "ss"
            rows.append([server, port, proto, ob.get("method", ""), ob.get("password", ""), "", "", "", tag, source])
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
    by_proto = {}
    for r in rows:
        by_proto.setdefault(r[2], []).append(r)
    for proto, prows in by_proto.items():
        out = ROOT / "nodes" / f"{SOURCE}-{proto}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["server", "port", "proto", "uuid", "password", "cc", "sni", "insecure", "name", "source"])
            for r in prows:
                w.writerow(r)


if __name__ == "__main__":
    main()
