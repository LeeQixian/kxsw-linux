#!/usr/bin/env python3
import json
import csv
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = ROOT / "config.json"
NODES_DIR = ROOT / "nodes"
CONFIG_OUT = ROOT / "dae_config.dae"

GLOBAL = """global {
    tproxy_port: 12345
    tproxy_port_protect: true
    log_level: info
    wan_interface: auto
    auto_config_kernel_parameter: true
    dial_mode: domain
    tcp_check_url: 'http://cp.cloudflare.com,1.1.1.1,2606:4700:4700::1111'
    tcp_check_http_method: HEAD
    udp_check_dns: 'dns.google:53,8.8.8.8,2001:4860:4860::8888'
    check_interval: 30s
    check_tolerance: 50ms
    allow_insecure: false
    sniffing_timeout: 30ms
    tls_implementation: tls
    tls_fragment: false
    mptcp: false
    bootstrap_resolver: '127.0.0.53:53'
}"""

DNS = """dns {
    upstream {
        ali: 'udp://223.5.5.5:53'
        google: 'https://8.8.8.8/dns-query'
    }
    routing {
        request {
            qname(geosite:cn) -> ali
            fallback: google
        }
    }
}"""

ROUTING = """routing {
    pname(NetworkManager,dnsmasq,systemd-resolved) -> direct
    dip(224.0.0.0/3, 'ff00::/8') -> direct
    pname(opencode) -> direct
    pname(pi) -> direct
    pname(qbittorrent) && dport(48494) -> direct
    pname(aria2c) -> direct
    domain(geosite:category-ads) -> block
    domain(geosite:category-ads-all) -> block
    pname(dnf5, flatpak) -> mass
    domain(geosite:youtube) -> mass
    domain(geosite:twitter, geosite:google, geosite:openai) -> ai
    domain(keyword:github) -> ai
    domain(geosite:microsoft) -> direct
    domain(geosite:cn) -> direct
    dip(geoip:private, geoip:cn) -> direct
    fallback: all
}"""


def load_nodes():
    nodes = {}
    for f in sorted(NODES_DIR.glob("*.csv")):
        sp = f.stem.split("-")[0]
        proto = f.stem.split("-")[1]
        with open(f) as fp:
            rows = list(csv.DictReader(fp))
        for r in rows:
            r["_sp"] = sp
            r["_proto"] = proto
        nodes.setdefault(sp, []).extend(rows)
    return nodes


def gen_share_link(r):
    proto = r["_proto"]
    name = r["name"]
    server = r["server"]
    port = r["port"]

    if proto == "trojan":
        password = r.get("password", "")
        sni = r.get("sni", "")
        params = f"type=tcp&security=tls&sni={sni}"
        if r.get("allowInsecure") == "1":
            params += "&allowInsecure=1"
        return f"trojan://{password}@{server}:{port}?{params}#{name}"

    elif proto == "hy2":
        password = r.get("password", "")
        sni = r.get("sni", "")
        params = f"sni={sni}"
        if r.get("skip_cert") == "true" or r.get("insecure") == "1":
            params += "&insecure=1"
        return f"hysteria2://{password}@{server}:{port}?{params}#{name}"

    elif proto == "vless":
        uuid = r.get("uuid", "")
        sni = r.get("sni", "")
        flow = r.get("flow", "")
        pbk = r.get("pbk", "")
        sid = r.get("sid", "")
        fp = r.get("fp", "")
        transport = r.get("type", "tcp")
        security = r.get("security", "reality")
        params = f"type={transport}&security={security}&sni={sni}&flow={flow}&pbk={pbk}&sid={sid}"
        if fp:
            params += f"&fp={fp}"
        return f"vless://{uuid}@{server}:{port}?{params}#{name}"

    elif proto == "anytls":
        uuid = r.get("uuid", "")
        sni = r.get("sni", "")
        transport = r.get("type", "tcp")
        params = f"type={transport}&security=tls&sni={sni}"
        if r.get("insecure") == "1":
            params += "&allowInsecure=1"
        return f"anytls://{uuid}@{server}:{port}?{params}#{name}"

    return ""


def _kw_str(items):
    return ", ".join(repr(str(i)) for i in items)


def gen_groups(cfg):
    providers = cfg.get("providers", [])
    mass_sp = [p["sp"] for p in providers if p.get("mass")]
    purity_sp = [p["sp"] for p in providers if p.get("purity")]
    non_mass = [p["sp"] for p in providers if not p.get("mass")]
    non_purity = [p["sp"] for p in providers if not p.get("purity")]
    nearby = cfg.get("nearby", [])
    oversea = cfg.get("oversea", [])
    settings = cfg.get("group_settings", {})

    subgroups = []

    # mass
    mass_parts = []
    if nearby:
        mass_parts.append(f"name(keyword: {_kw_str(nearby)})")
    for s in non_mass:
        mass_parts.append(f"!name(keyword: {repr(s)})")
    mass_fl = f"        filter: {' && '.join(mass_parts)}\n" if mass_parts else ""
    subgroups.append(_build_subgroup("mass", mass_fl, "random", settings.get("mass", {})))

    # ai
    ai_parts = []
    if oversea:
        ai_parts.append(f"name(keyword: {_kw_str(oversea)})")
    for s in non_purity:
        ai_parts.append(f"!name(keyword: {repr(s)})")
    ai_fl = f"        filter: {' && '.join(ai_parts)}\n" if ai_parts else ""
    subgroups.append(_build_subgroup("ai", ai_fl, "min_moving_avg", settings.get("ai", {})))

    # all
    all_parts = []
    for s in purity_sp:
        all_parts.append(f"!name(keyword: {repr(s)})")
    all_fl = f"        filter: {' && '.join(all_parts)}\n" if all_parts else ""
    subgroups.append(_build_subgroup("all", all_fl, "random", settings.get("all", {})))

    return "group {\n" + "\n".join(subgroups) + "\n}"


def _build_subgroup(name, filter_line, policy, s):
    lines = [f"    {name} {{"]
    if filter_line:
        lines.append(filter_line.rstrip("\n"))
    lines.append(f"        policy: {policy}")
    for key in ("check_interval", "check_tolerance", "tcp_check_url"):
        if key in s:
            lines.append(f"        {key}: {s[key]}")
    lines.append("    }")
    return "\n".join(lines)


def main():
    cfg = json.loads(CONFIG.read_text())
    nodes_by_sp = load_nodes()

    node_lines = ["node {"]
    for sp, rows in sorted(nodes_by_sp.items()):
        node_lines.append(f"  # {sp}")
        for r in rows:
            sl = gen_share_link(r)
            if sl:
                node_lines.append(f"    '{sl}'")
    node_lines.append("}")

    groups = gen_groups(cfg)

    config_text = (
        GLOBAL + "\n"
        + "\n".join(node_lines) + "\n\n"
        + groups + "\n"
        + DNS + "\n"
        + ROUTING
    )

    CONFIG_OUT.write_text(config_text)
    print(f"written: {CONFIG_OUT}")


if __name__ == "__main__":
    main()
