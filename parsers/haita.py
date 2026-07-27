#!/usr/bin/env python3
import sys
import csv
import base64
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.common import dedup_rename

ROOT = Path(__file__).parent.parent
SOURCE = "haita"
UA = "v2rayN"
HEADER = ["server", "port", "proto", "password", "sni", "peer", "allowInsecure", "name", "source"]


def parse(raw, source=SOURCE):
    raw = raw.strip()
    padding = 4 - len(raw) % 4
    if padding != 4:
        raw += "=" * padding
    decoded = base64.b64decode(raw).decode("utf-8")
    rows = []

    for line in decoded.splitlines():
        line = line.strip()
        if not line or not line.startswith("trojan://"):
            continue

        u = urlparse(line)
        server = u.hostname or ""
        port = str(u.port or "443")
        password = u.username or ""
        org_name = unquote(u.fragment) if u.fragment else ""
        q = parse_qs(u.query)

        def qv(key):
            v = q.get(key, [""])[0]
            return unquote(v) if v else ""

        rows.append([
            server, port, "trojan",
            password,
            qv("sni"),
            qv("peer"),
            qv("allowInsecure"),
            org_name, source,
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
    rows = parse(raw, SOURCE)
    out = ROOT / "nodes" / f"{SOURCE}-trojan.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    main()
