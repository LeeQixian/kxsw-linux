#!/usr/bin/env bash
# 检测 sing-box 新出现的节点公钥失效，打印需要更新的机场（供 singbox-update 调用）
set -u
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/pubkey-check.state"
NODES=$(journalctl --user -u sing-box --since "24 hours ago" --no-pager 2>/dev/null \
    | grep "unrecognized remote public key" \
    | grep -oP 'hysteria2\[\K[^\]]+|outbound \K[^ ]+(?= unavailable)' | sort -u)

[ -f "$STATE" ] && PREV=$(cat "$STATE") || PREV=""
NEW=$(comm -13 <(printf '%s\n' "$PREV") <(printf '%s\n' "$NODES") | grep -v '^$')
printf '%s\n' "$NODES" > "$STATE"
if [ -z "$NEW" ]; then
    exit 0
fi
COUNT=$(printf '%s\n' "$NEW" | wc -l)
SPS=$(printf '%s\n' "$NEW" | awk -F- '{print $3}' | sort -u | paste -sd'、')
echo "警告: $SPS 机场 $COUNT 个节点公钥失效, 运行 python3 fetch.py 更新订阅"
