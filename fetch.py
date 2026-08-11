#!/usr/bin/env python3
import json
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
CONFIG = ROOT / "config.json"


def main():
    cfg = json.loads(CONFIG.read_text())
    changed = False

    for p in cfg.get("providers", []):
        sp = p.get("sp", "")
        if not sp:
            print("provider missing 'sp' field, skip", file=sys.stderr)
            continue
        if p.get("validity", True):
            print(f"[{sp}] skip (validity=true)")
            continue

        parser = ROOT / "parsers" / f"{sp}.py"

        sublink = p.get("sublink", "")
        if not sublink:
            print(f"[{sp}] no sublink", file=sys.stderr)
            continue

        print(f"[{sp}] fetching...")
        cache = ROOT / "cache" / f"{sp}.txt"
        if not cache.exists() or not cache.read_text(encoding="utf-8").strip():
            ua = p.get("ua", "v2rayNG")
            result = subprocess.run(
                ["curl", "-sSL", "--max-time", "20", "-A", ua, sublink],
                capture_output=True, text=True
            )
            raw = (result.stdout or "").strip()
            if not raw or len(raw) < 200:
                print(f"[{sp}] curl failed or response too small ({len(raw)} bytes)", file=sys.stderr)
                continue
            cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_suffix(".txt.tmp")
            tmp.write_text(raw, encoding="utf-8")
            os.replace(tmp, cache)
        else:
            print(f"[{sp}] using cache")

        parser = ROOT / "parsers" / f"{sp}.py"
        if parser.exists():
            result = subprocess.run(
                [sys.executable, str(parser)],
                capture_output=False,
            )
            rows = 0
            for f in sorted((ROOT / "nodes").glob(f"{sp}-*.csv")):
                rows += max(0, len(f.read_text(encoding="utf-8").splitlines()) - 1)
            if result.returncode == 0 and rows > 0:
                p["validity"] = True
                changed = True
                print(f"[{sp}] done ({rows} rows)")
                try:
                    cache.unlink()
                except OSError:
                    pass
            else:
                print(
                    f"[{sp}] parse failed or produced 0 rows (rc={result.returncode}), cache kept",
                    file=sys.stderr,
                )
        else:
            print(f"[{sp}] no parser, raw saved to cache")

    if changed:
        CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
