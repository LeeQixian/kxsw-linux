import json
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = Path(tempfile.gettempdir()) / "aria2c"
BASE_PORT = 19000
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
WAF_MARKS = (
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
    "access denied",
    "request blocked",
    "unusual traffic",
)


@dataclass
class Result:
    text: str
    ok: bool = False
    loc: str = ""


@dataclass
class Response:
    status: int
    final: str
    body: str


def load():
    cfg = json.loads((ROOT / "sing-box.json").read_text())
    return [o for o in cfg["outbounds"] if o.get("type") not in ("urltest", "selector")]


def provider_of(tag, sps):
    segs = set(tag.split("-"))
    for sp in sps:
        if sp in segs:
            return sp
    return None


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start(ob, port):
    cfg = {
        "log": {"level": "error"},
        "dns": {
            "servers": [
                {"type": "udp", "tag": "ali", "server": "223.5.5.5", "server_port": 53},
                {"type": "https", "tag": "remote", "server": "8.8.8.8", "server_port": 443, "path": "/dns-query", "detour": ob["tag"]},
            ],
            "final": "remote",
        },
        "inbounds": [{"type": "socks", "listen": "127.0.0.1", "listen_port": port}],
        "outbounds": [ob],
        "route": {"final": ob["tag"], "default_domain_resolver": "remote"},
    }
    base = Path(tempfile.gettempdir()) / f"unlock-{port}"
    cfg_path = base.with_suffix(".json")
    cfg_path.write_text(json.dumps(cfg))
    log = open(base.with_suffix(".log"), "w")
    p = subprocess.Popen([str(BIN), "run", "-c", str(cfg_path)], stdout=log, stderr=log)
    for _ in range(50):
        if port_open(port):
            return p
        if p.poll() is not None:
            return None
        time.sleep(0.1)
    return p


def cleanup(port):
    base = Path(tempfile.gettempdir()) / f"unlock-{port}"
    for f in (base.with_suffix(".json"), base.with_suffix(".log")):
        f.unlink(missing_ok=True)


def get(port, url, headers=None, follow=True, timeout=15):
    cmd = [
        "curl", "-s", "-m", str(timeout),
        "-x", f"socks5h://127.0.0.1:{port}",
        "-A", UA,
        "-w", "\n%{http_code}|%{url_effective}",
    ]
    if follow:
        cmd.append("-L")
    for k, v in (headers or {}).items():
        cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    body, _, meta = r.stdout.rpartition("\n")
    raw, _, final = meta.partition("|")
    try:
        status = int(raw)
    except ValueError:
        status = 0
    return Response(status, final, body)


def trace(port, url, timeout=10):
    r = get(port, url, follow=False, timeout=timeout)
    if r.status != 200:
        return ""
    for line in r.body.splitlines():
        if line.startswith("loc="):
            return line[4:].strip().lower()
    return ""


def waf(body):
    text = body.lower()
    return any(mark in text for mark in WAF_MARKS)
