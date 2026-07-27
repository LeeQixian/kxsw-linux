# dae 配置管理工具

适用于想要使用 [dae](https://github.com/daeuniverse/dae) 但技术知识不足或财力有限，同时又希望尽可能掌控分流策略的用户。本工具提供一种 vibecoding 的解决方案：写好机场解析器，填好 JSON 配置，两条命令出完整 dae 配置。

## 结构

```
.
├── fetch.py              # 拉订阅、解析节点 → nodes/*.csv
├── gen.py                # 生成 dae_config.dae
├── config.json           # 配置文件（需自建）
├── config.example.json   # 配置模板
├── country_map.json      # 国家/地区别名映射
├── parsers/              # 各机场解析器
│   ├── common.py
│   ├── haita.py
│   ├── ovo.py
│   ├── top.py
│   └── xfltd.py
```

## 使用

```bash
python3 fetch.py   # 拉取 validity=false 的机场
python3 gen.py     # 按 config 策略生成 dae_config.dae
```

## 配置

复制 `config.example.json` 为 `config.json`，填入你的信息：

```json
{
  "nearby": ["日本", "台湾", "香港", "新加坡", "韩国"],
  "oversea": ["新加坡", "美国", "德国"],
  "providers": [
    { "sp": "haita",  "sublink": "https://...", "validity": false, "purity": false, "mass": false },
    { "sp": "ovo",    "sublink": "https://...", "validity": false, "purity": false, "mass": false },
    { "sp": "top",    "sublink": "https://...", "validity": false, "purity": false, "mass": false },
    { "sp": "xfltd",  "sublink": "https://...", "validity": false, "purity": false, "mass": false }
  ],
  "group_settings": {
    "mass": { "check_interval": "120s", "check_tolerance": "50ms" },
    "ai":   { "check_interval": "30s",  "check_tolerance": "100ms" },
    "all":  { "check_interval": "60s",  "check_tolerance": "50ms" }
  }
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `sp` | 机场名，需与 `parsers/` 下同名 `.py` 文件对应 |
| `sublink` | 订阅链接 |
| `validity` | false 则下次 fetch 时重新拉取，成功自动改为 true |
| `purity` | 节点 IP 是否干净可解锁海外 AI，归入 `ai` 组 |
| `mass` | 是否归入 `mass` 组（大流量下载） |
| `nearby` | mass 组按这些地区过滤节点 |
| `oversea` | ai 组按这些地区过滤节点 |
| `group_settings` | 可选，按组覆盖 check_interval / check_tolerance / tcp_check_url |

### 分组逻辑

- **mass** — `mass: true` 且节点名命中 `nearby` 地区，策略 `random`
- **ai** — `purity: true` 且节点名命中 `oversea` 地区，策略 `min_moving_avg`
- **all** — 排除所有 `purity: true` 的节点做兜底，策略 `random`

## 添加新机场

1. 在 `parsers/` 下新建 `{sp}.py`，仿照现有 parser 实现 `parse()` 和 `main()`
2. 在 `config.json` 的 `providers` 中加一条 `{ "sp": "...", "sublink": "...", ... }`

## 现有机场

每个 parser 系仓库持有者基于自身网络环境测试过的节点获取方案，**不对机场质量、可用性、线路稳定性做任何保证**。选择机场前建议自行评估。

| parser | 协议 | UA | 机场官网 |
|--------|------|-----|---------|
| haita | trojan | v2rayN | -- |
| ovo | hysteria2 | mihomo | -- |
| top | hysteria2 / vless | mihomo | -- |
| xfltd | anytls / vless | mihomo | -- |
