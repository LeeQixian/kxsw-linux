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

DNF_IN = {
    "type": "mixed",
    "tag": "dnf-in",
    "listen": "127.0.0.1",
    "listen_port": 20123,
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
        "detour": "stable",
    },
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
                "utls": {"enabled": True, "fingerprint": "chrome"},
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


def _group_tags(nodes, spec):
    explicit = spec.get("nodes")
    if explicit:
        wanted = set(explicit)
        tags = []
        for sp, rows in nodes.items():
            for r in rows:
                if r.get("tag") is None:
                    continue
                if r["name"] not in wanted and r["tag"] not in wanted:
                    continue
                tags.append(r["tag"])
                wanted.discard(r["name"])
                wanted.discard(r["tag"])
        if wanted:
            print(f"warning: {spec.get('tag', '?')}: node not found: {sorted(wanted)}")
        return tags
    include = set(spec.get("include_sp", []))
    exclude = set(spec.get("exclude_sp", []))
    regions = spec.get("regions", [])
    tags = []
    for sp, rows in nodes.items():
        if include and sp not in include:
            continue
        if sp in exclude:
            continue
        for r in rows:
            if r.get("tag") is None:
                continue
            if regions and not any(k in r["name"] for k in regions):
                continue
            tags.append(r["tag"])
    return tags


def build_groups(nodes, cfg):
    groups = []
    for spec in cfg.get("groups", []):
        tags = _group_tags(nodes, spec)
        group = {"type": spec.get("type", "urltest"), "tag": spec["tag"], "outbounds": tags}
        if group["type"] == "selector":
            if tags:
                group["default"] = tags[0]
        else:
            group["interval"] = spec.get("interval", "3m")
            group["tolerance"] = _parse_tolerance(spec.get("tolerance", "50ms"))
        groups.append(group)
    return groups


def build_config(nodes, cfg):
    outbounds, skipped = build_outbounds(nodes)
    groups = build_groups(nodes, cfg)
    user_rules = cfg.get("rules", [])
    geosite_names = ["cn"]
    for rule in user_rules:
        for rs in rule.get("rule_set", []):
            name = rs[len("geosite-"):] if rs.startswith("geosite-") else rs
            if name not in geosite_names:
                geosite_names.append(name)
    rule_sets = [
        {
            "type": "local",
            "tag": f"geosite-{name}",
            "format": "binary",
            "path": str((RULESETS / f"geosite-{name}.srs").resolve()),
        }
        for name in geosite_names
    ]
    rules = [{"inbound": ["dnf-in"], "outbound": "mass"}]
    rules += user_rules
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": DNS_SERVERS,
            "rules": [{"rule_set": ["geosite-cn"], "server": "ali", "action": "route"}],
            "final": "remote",
        },
        "inbounds": [MIXED_IN, DNF_IN],
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
