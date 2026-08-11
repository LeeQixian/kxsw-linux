#!/usr/bin/env bash
# 检测 sing-box 节点公钥轮换，失效节点集合变化时桌面通知（列出机场）
set -u
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/pubkey-check.state"
NODES=$(journalctl --user -u sing-box --since "24 hours ago" --no-pager 2>/dev/null \
    | grep "unrecognized remote public key" \
    | grep -oP 'hysteria2\[\K[^\]]+|outbound \K[^ ]+(?= unavailable)' | sort -u)

if [ -z "$NODES" ]; then
    exit 0
fi
COUNT=$(printf '%s\n' "$NODES" | wc -l)
SPS=$(printf '%s\n' "$NODES" | awk -F- '{print $3}' | sort -u | paste -sd'、')
[ -f "$STATE" ] && PREV=$(cat "$STATE") || PREV=""
if [ "$NODES" != "$PREV" ]; then
    printf '%s\n' "$NODES" > "$STATE"
    notify-send -u critical \
        "sing-box 节点失效" "请更新 $SPS 机场：$COUNT 个节点公钥失效，运行 python3 fetch.py 更新订阅"
fi
