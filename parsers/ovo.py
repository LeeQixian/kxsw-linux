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
HEADER = [
    "server",
    "port",
    "proto",
    "password",
    "sni",
    "insecure",
    "pinSHA256",
    "mport",
    "name",
    "source",
]


def _is_info(tag):
    return any(k in tag for k in INFO_KEYS)


def _span(ob):
    spans = ob.get("server_ports")
    if isinstance(spans, str):
        spans = [spans]
    if not isinstance(spans, list):
        return ""
    for s in spans:
        s = str(s or "").strip()
        if s:
            return s
    return ""


def _port(ob, span):
    port = str(ob.get("server_port") or "").strip()
    if port:
        return port
    head = span.split(":")[0].split("-")[0]
    return head if head.isdigit() else ""


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
        span = _span(ob)
        port = _port(ob, span)
        if not server or not port:
            continue
        tls = ob.get("tls") or {}
        sni = tls.get("server_name", "")
        insecure = "1" if tls.get("insecure") else "0"
        pin = tls.get("certificate_public_key_sha256") or []
        pin = pin[0] if isinstance(pin, list) and pin else ""
        password = ob.get("password", "")
        rows.append(
            [
                server,
                port,
                "hysteria2",
                password,
                sni,
                insecure,
                pin,
                span.replace(":", "-"),
                tag,
                source,
            ]
        )

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
        w.writerow(HEADER)
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    main()
