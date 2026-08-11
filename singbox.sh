#!/usr/bin/env bash
# 生成 sing-box 配置并重启服务生效
set -e
cd "$(dirname "$0")"

python3 gen.py
sing-box check -c sing-box.json
systemctl --user restart sing-box
echo "restart ok"
