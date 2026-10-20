import json
import shutil
import subprocess
from pathlib import Path

DAT = Path("/usr/share/v2ray-rules-dat/geosite.dat")
TYPES = {0: "domain_keyword", 1: "domain_regex", 2: "domain_suffix", 3: "domain"}


def _varint(data, i):
    value = shift = 0
    while True:
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, i


def _fields(data):
    i = 0
    while i < len(data):
        key, i = _varint(data, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = _varint(data, i)
        elif wire == 2:
            length, i = _varint(data, i)
            value = data[i:i + length]
            i += length
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield field, wire, value


def categories():
    if not DAT.exists():
        raise SystemExit(f"geosite database not found: {DAT}")
    result = {}
    for field, wire, value in _fields(DAT.read_bytes()):
        if field != 1 or wire != 2:
            continue
        code = ""
        domains = []
        for sub_field, sub_wire, sub_value in _fields(value):
            if sub_field == 1 and sub_wire == 2:
                code = sub_value.decode()
            elif sub_field == 2 and sub_wire == 2:
                kind = 0
                name = ""
                for item_field, item_wire, item_value in _fields(sub_value):
                    if item_field == 1 and item_wire == 0:
                        kind = item_value
                    elif item_field == 2 and item_wire == 2:
                        name = item_value.decode()
                domains.append((kind, name))
        if code:
            result[code] = domains
    return result


def build(names, out_dir):
    cats = categories()
    binary = shutil.which("sing-box") or "/usr/bin/sing-box"
    if not Path(binary).exists():
        raise SystemExit("sing-box not found")
    source_dir = out_dir.parent / "cache" / "rulesets"
    source_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        code = name.upper()
        if code not in cats:
            raise SystemExit(f"geosite category not found: {code}")
        rules = {}
        seen = {key: set() for key in TYPES.values()}
        for kind, domain in cats[code]:
            key = TYPES.get(kind)
            if key is None or not domain or domain in seen[key]:
                continue
            seen[key].add(domain)
            rules.setdefault(key, []).append(domain)
        source = source_dir / f"{name}.json"
        source.write_text(json.dumps({"version": 2, "rules": [rules]}, ensure_ascii=False) + "\n")
        target = out_dir / f"geosite-{name}.srs"
        subprocess.run([binary, "rule-set", "compile", str(source), "-o", str(target)], check=True)
