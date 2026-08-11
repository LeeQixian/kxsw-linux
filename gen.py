#!/usr/bin/env python3
import json
import csv
import re
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = ROOT / "config.json"
NODES_DIR = ROOT / "nodes"
RULESETS = ROOT / "rulesets"
CONFIG_OUT = ROOT / "sing-box.json"

MIXED_IN = {
    "type": "mixed",
    "tag": "mixed-in",
    "listen": "127.0.0.1",
    "listen_port": 20122,
}

CLASH_API = {
    "external_controller": "127.0.0.1:9090",
    "access_control_allow_private_network": True,
}

DNS_SERVERS = [
    {"type": "udp", "tag": "ali", "server": "223.5.5.5", "server_port": 53},
    {
        "type": "https",
        "tag": "remote",
        "server": "8.8.8.8",
        "server_port": 443,
        "path": "/dns-query",
        "detour": "ai",
    },
]

GEOSITE_RULES = [
    ("telegram", "ai"),
    ("category-dev", "ai"),
    ("mozilla", "mass"),
    ("protonmail", "mass"),
    ("youtube", "mass"),
    ("cloudflare", "ai"),
    ("twitter", "ai"),
    ("google", "ai"),
    ("openai", "ai"),
]


def load_nodes():
    nodes = {}
    for f in sorted(NODES_DIR.glob("*.csv")):
        parts = f.stem.split("-")
        if len(parts) < 2:
            continue
        sp, proto = parts[0], parts[1]
        with open(f) as fp:
            rows = list(csv.DictReader(fp))
        for r in rows:
            r["_sp"] = sp
            r["_proto"] = proto
        nodes.setdefault(sp, []).extend(rows)
    return nodes


def _outbound(r, tag):
    proto = r["_proto"]
    if proto == "trojan":
        return {
            "type": "trojan",
            "tag": tag,
            "server": r["server"],
            "server_port": int(r["port"]),
            "password": r["password"],
            "tls": {
                "enabled": True,
                "server_name": r.get("sni", ""),
                "insecure": r.get("allowInsecure") == "1",
            },
        }
    if proto == "vless":
        o = {
            "type": "vless",
            "tag": tag,
            "server": r["server"],
            "server_port": int(r["port"]),
            "uuid": r["uuid"],
        }
        sec = r.get("security")
        if sec == "reality":
            tls = {"enabled": True, "server_name": r.get("sni", "")}
            fp = r.get("fp", "")
            if fp:
                tls["utls"] = {"enabled": True, "fingerprint": fp}
            tls["reality"] = {
                "enabled": True,
                "public_key": r.get("pbk", ""),
                "short_id": r.get("sid", ""),
            }
            o["tls"] = tls
        elif sec == "tls":
            tls = {"enabled": True, "server_name": r.get("sni", "")}
            fp = r.get("fp", "")
            if fp:
                tls["utls"] = {"enabled": True, "fingerprint": fp}
            o["tls"] = tls
        if r.get("insecure") == "1" and "tls" in o:
            o["tls"]["insecure"] = True
        if r.get("flow"):
            o["flow"] = r["flow"]
        if r.get("type") == "ws":
            transport = {"type": "ws", "path": r.get("path") or "/"}
            host = r.get("host")
            if host:
                transport["headers"] = {"Host": host}
            o["transport"] = transport
        return o
    if proto == "hy2":
        tls = {
            "enabled": True,
            "server_name": r.get("sni", ""),
            "insecure": r.get("skip_cert") == "true" or r.get("insecure") == "1",
        }
        pin = r.get("pinSHA256", "")
        if pin:
            tls["certificate_public_key_sha256"] = [pin]
        o = {
            "type": "hysteria2",
            "tag": tag,
            "server": r["server"],
            "server_port": int(r["port"]),
            "password": r["password"],
            "tls": tls,
        }
        mport = r.get("mport", "")
        if mport:
            o["server_ports"] = [mport.replace("-", ":")]
        return o
    if proto == "anytls":
        return {
            "type": "anytls",
            "tag": tag,
            "server": r["server"],
            "server_port": int(r["port"]),
            "password": r["password"],
            "tls": {
                "enabled": True,
                "server_name": r.get("sni", ""),
                "insecure": r.get("insecure") == "1",
            },
        }
    return None


def build_outbounds(nodes):
    rows = [r for rows in nodes.values() for r in rows]
    counts = {}
    for r in rows:
        counts[r["name"]] = counts.get(r["name"], 0) + 1
    outbounds = []
    skipped = 0
    for r in rows:
        tag = r["name"] if counts[r["name"]] == 1 else f"{r['name']}-{r['_proto']}"
        ob = _outbound(r, tag)
        if ob is None:
            skipped += 1
            continue
        ob["tag"] = tag
        ob["domain_resolver"] = "ali"
        r["tag"] = tag
        outbounds.append(ob)
    return outbounds, skipped


def _parse_tolerance(s):
    if not s:
        return 50
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s)?", s)
    if not m:
        return 50
    val = float(m.group(1))
    if m.group(2) == "s":
        val *= 1000
    return int(val)


def build_groups(nodes, cfg):
    providers = cfg.get("providers", [])
    mass_sp = {p["sp"] for p in providers if p.get("mass")}
    purity_sp = {p["sp"] for p in providers if p.get("purity")}
    nearby = set(cfg.get("nearby", []))
    oversea = set(cfg.get("oversea", []))
    settings = cfg.get("group_settings", {})
    groups = []
    for kind, pick in (
        ("mass", lambda r, sp: sp in mass_sp and any(k in r["name"] for k in nearby)),
        ("ai", lambda r, sp: sp in purity_sp and any(k in r["name"] for k in oversea)),
        ("all", lambda r, sp: sp not in purity_sp),
    ):
        tags = [
            r["tag"]
            for sp, rows in nodes.items()
            for r in rows
            if pick(r, sp) and r.get("tag") is not None
        ]
        s = settings.get(kind, {})
        if kind == "ai":
            group = {"type": "selector", "tag": kind, "outbounds": tags}
            if tags:
                group["default"] = tags[0]
            groups.append(group)
            continue
        interval = s.get("check_interval", "3m")
        tolerance = _parse_tolerance(s.get("check_tolerance", "50ms"))
        groups.append(
            {"type": "urltest", "tag": kind, "outbounds": tags, "interval": interval, "tolerance": tolerance}
        )
    return groups


def build_config(nodes, cfg):
    outbounds, skipped = build_outbounds(nodes)
    groups = build_groups(nodes, cfg)
    rule_sets = [
        {
            "type": "local",
            "tag": f"geosite-{name}",
            "format": "binary",
            "path": str((RULESETS / f"geosite-{name}.srs").resolve()),
        }
        for name in ["cn"] + [n for n, _ in GEOSITE_RULES]
    ]
    rules = [
        {"rule_set": [f"geosite-{name}"], "outbound": kind}
        for name, kind in GEOSITE_RULES
    ]
    rules.append({"domain_suffix": ["greasyfork.org"], "outbound": "ai"})
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": DNS_SERVERS,
            "rules": [{"rule_set": ["geosite-cn"], "server": "ali", "action": "route"}],
            "final": "remote",
        },
        "inbounds": [MIXED_IN],
        "outbounds": outbounds + groups,
        "route": {
            "rules": rules,
            "rule_set": rule_sets,
            "final": "all",
            "default_domain_resolver": "remote",
        },
        "experimental": {
            "clash_api": CLASH_API,
            "cache_file": {"enabled": True, "path": str((ROOT / "cache.db").resolve())},
        },
    }


def main():
    cfg = json.loads(CONFIG.read_text())
    nodes = load_nodes()
    config = build_config(nodes, cfg)
    CONFIG_OUT.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    n_out = sum(len(v) for v in nodes.values())
    n_grp = {g["tag"]: len(g["outbounds"]) for g in config["outbounds"] if "outbounds" in g}
    print(f"written: {CONFIG_OUT}")
    print(f"nodes: {n_out}, groups: {n_grp}")


if __name__ == "__main__":
    main()
