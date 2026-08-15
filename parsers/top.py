#!/usr/bin/env python3
import sys
import csv
import base64
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.common import dedup_rename

ROOT = Path(__file__).parent.parent
SOURCE = "top"
UA = "mihomo"
HY2_HEADER = ["server", "port", "proto", "password", "sni", "insecure", "pinSHA256", "mport", "name", "source"]
VLESS_HEADER = ["server", "port", "proto", "uuid", "security", "flow", "sni", "pbk", "sid", "fp", "type", "insecure", "path", "host", "name", "source"]


def parse(raw, source=SOURCE):
    raw = "".join(raw.split())
    padding = 4 - len(raw) % 4
    if padding != 4:
        raw += "=" * padding
    decoded = base64.b64decode(raw).decode("utf-8")
    hy2_rows, vless_rows = [], []

    for line in decoded.splitlines():
        line = line.strip()
        if not line or not line.startswith(("hysteria2://", "vless://")):
            continue

        u = urlparse(line)
        proto = u.scheme
        org_name = unquote(u.fragment) if u.fragment else ""
        if any(k in org_name for k in ("剩余", "重置", "到期", "套餐", "流量")):
            continue
        server = u.hostname or ""
        port = str(u.port or ("50000" if proto == "hysteria2" else "443"))
        uuid = unquote(u.username) if u.username else ""
        q = parse_qs(u.query)

        def qv(key):
            v = q.get(key, [""])[0]
            return unquote(v) if v else ""

        if proto == "hysteria2":
            hy2_rows.append([
                server, port, proto,
                uuid,
                qv("sni"),
                qv("insecure"),
                qv("pinSHA256"),
                qv("mport"),
                org_name, source,
            ])
        elif proto == "vless":
            vless_rows.append([
                server, port, proto,
                uuid,
                qv("security"),
                qv("flow"),
                qv("sni"),
                qv("pbk"),
                qv("sid"),
                qv("fp"),
                qv("type"),
                qv("insecure"),
                qv("path"),
                qv("host"),
                org_name, source,
            ])

    return dedup_rename(hy2_rows, source), dedup_rename(vless_rows, source)


def main():
    cache = ROOT / "cache" / f"{SOURCE}.txt"
    if not cache.exists():
        print(f"[{SOURCE}] no cache file", file=sys.stderr)
        sys.exit(1)
    raw = cache.read_text(encoding="utf-8").strip()
    if not raw:
        print(f"[{SOURCE}] cache empty", file=sys.stderr)
        sys.exit(1)
    hy2, vless = parse(raw, SOURCE)
    outdir = ROOT / "nodes"
    outdir.mkdir(parents=True, exist_ok=True)
    for header, rows, tag in [
        (HY2_HEADER, hy2, "hy2"),
        (VLESS_HEADER, vless, "vless"),
    ]:
        outpath = outdir / f"{SOURCE}-{tag}.csv"
        with open(outpath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for r in rows:
                w.writerow(r)


if __name__ == "__main__":
    main()
