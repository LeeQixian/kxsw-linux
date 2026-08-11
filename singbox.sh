#!/usr/bin/env bash
# 生成 sing-box 配置并热重载（不重启进程）
set -e
cd "$(dirname "$0")"

python3 gen.py
sing-box check -c sing-box.json
curl -sS -f -X PUT "http://127.0.0.1:9090/configs?force=true" \
    -d "{\"path\": \"$(pwd)/sing-box.json\", \"payload\": \"\"}" \
    -w "\nreload: %{http_code}\n"
