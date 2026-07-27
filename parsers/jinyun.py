#!/usr/bin/env python3
import sys
import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SOURCE = "jinyun"

VLESS_HEADER = ["server", "port", "proto", "uuid", "security", "flow", "sni", "pbk", "sid", "fp", "type", "insecure", "name", "source"]

sys.path.insert(0, str(ROOT))
from parsers.common import dedup_rename


def parse(raw, source=SOURCE):
    cfg = json.loads(raw)
    rows = []

    for o in cfg.get("outbounds", []):
        if o.get("type") != "vless":
            continue

        tag = o.get("tag", "")
        tls = o.get("tls", {})
        reality = tls.get("reality", {})
        utls = tls.get("utls", {})

        rows.append([
            o.get("server", ""),
            str(o.get("server_port", "443")),
            "vless",
            o.get("uuid", ""),
            "reality" if reality.get("enabled") else "tls",
            o.get("flow", ""),
            tls.get("server_name", ""),
            reality.get("public_key", ""),
            reality.get("short_id", ""),
            utls.get("fingerprint", ""),
            "tcp",
            "1" if tls.get("insecure") else "",
            tag,
            source,
        ])

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
    try:
        rows = parse(raw, SOURCE)
    except Exception:
        raise
    out = ROOT / "nodes" / f"{SOURCE}-vless.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(VLESS_HEADER)
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    main()
