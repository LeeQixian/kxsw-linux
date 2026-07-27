import json
from pathlib import Path

_MAP_FILE = Path(__file__).parent.parent / "country_map.json"

if _MAP_FILE.exists():
    _raw = json.loads(_MAP_FILE.read_text(encoding="utf-8"))
    _ALIAS_MAP = []
    for canonical, aliases in _raw.items():
        for alias in aliases:
            _ALIAS_MAP.append((alias, canonical))
    _ALIAS_MAP.sort(key=lambda x: -len(x[0]))
else:
    _ALIAS_MAP = []


def detect_country(name):
    for alias, canonical in _ALIAS_MAP:
        if alias in name:
            return canonical
    return "OTHER"


def dedup_rename(rows, source):
    """
    rows: list of lists, format [server, port, ..., name, source]
    去重策略: 同server:port只留一个，优先留name里命中countries的行
    重命名格式: 国家-编号-source
    """
    groups = {}
    for r in rows:
        key = f"{r[0]}:{r[1]}"
        groups.setdefault(key, []).append(r)

    deduped = []
    for key, group in groups.items():
        best = group[0]
        for r in group:
            if detect_country(r[-2]) != "OTHER":
                best = r
                break
        deduped.append(best)

    seq = {}
    for r in deduped:
        c = detect_country(r[-2])
        seq.setdefault(c, 0)
        seq[c] += 1
        r[-2] = f"{c}-{seq[c]:02d}-{source}"

    return deduped
