#!/usr/bin/env bash
# 检测 sing-box 节点公钥轮换（hysteria2 pinSHA256 失效），变化时桌面通知一次
set -u
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/pubkey-check.state"
KEYS=$(journalctl --user -u sing-box --since "24 hours ago" --no-pager 2>/dev/null \
    | grep -oP 'unrecognized remote public key: \K[A-Za-z0-9+/=]+' | sort -u)

if [ -z "$KEYS" ]; then
    exit 0
fi
N=$(printf '%s\n' "$KEYS" | wc -l)
[ -f "$STATE" ] && PREV=$(cat "$STATE") || PREV=""
if [ "$KEYS" != "$PREV" ]; then
    printf '%s\n' "$KEYS" > "$STATE"
    notify-send -u critical \
        "sing-box 节点公钥轮换" "$N 个 hysteria2 节点公钥失效，运行 python3 fetch.py 更新订阅"
fi
