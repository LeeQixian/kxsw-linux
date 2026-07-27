#!/usr/bin/env python3
import re
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.common import dedup_rename

ROOT = Path(__file__).parent.parent
SOURCE = "ovo"
UA = "mihomo"


def _field(line, key):
    m = re.search(rf"{key}:\s*'([^']*)'", line)
    if m:
        return m.group(1)
    m = re.search(rf'{key}:\s*"([^"]*)"', line)
    if m:
        return m.group(1)
    m = re.search(rf"{key}:\s*(true|false)", line)
    if m:
        return m.group(1)
    m = re.search(rf"{key}:\s*(\S+)", line)
    if m:
        v = m.group(1).rstrip(",}")
        if not v.startswith(("'", '"', "{")):
            return v
    return ""


def _rtype(line):
    types = re.findall(r"type:\s*([a-zA-Z0-9_-]+)", line)
    return types[-1] if types else ""


def _rport(line):
    m = re.search(r"port:\s*([0-9]+)", line)
    return m.group(1) if m else "443"


def extract_blocks(raw):
    lines = raw.splitlines()
    start = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("proxies") and ":" in s:
            start = i + 1
            break
    if start < 0:
        return []

    blocks = []
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s and not s[0].isspace() and not s.startswith("-"):
            break
        if s.startswith("- {"):
            blocks.append(s)
    return blocks


def parse(raw, source=SOURCE):
    rows = []
    for block in extract_blocks(raw):
        name = _field(block, "name")
        server = _field(block, "server")
        proto = _rtype(block)
        if not server or not proto:
            continue

        port = _rport(block)
        password = _field(block, "password")
        sni = _field(block, "sni")
        skip_cert = _field(block, "skip-cert-verify")
        udp = _field(block, "udp")

        rows.append([server, port, proto, password, sni, udp, skip_cert, name, source])

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
