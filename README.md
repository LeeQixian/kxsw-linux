# sing-box 配置管理工具

适用于想要使用 [sing-box](https://github.com/SagerNet/sing-box) 但技术知识不足或财力有限，同时又希望尽可能掌控分流策略的用户。本工具提供一种 vibecoding 的解决方案：写好机场解析器，填好 JSON 配置，两步配出完整 sing-box 配置。

> [!note] 原理：
>
> 本质上机场-订阅的服务模式就是，从机场的订阅链接获取配置文件，而后从中获取可用的节点（协议、主机名、端口、密码、其他参数等），sing-box 几乎都可以吃，因此完全可以自己手搓，只需要一丝丝的命令行，就可以在不依赖任何 GUI 的前提下获得纯粹的体验。
>
> 架构：dae 负责内核层直连分流与广告拦截，其余流量经 socks5 转给 sing-box（127.0.0.1:20122），具体的规则集与节点分组在 sing-box 内部完成。dae 配置（dae_config.dae）已固定为静态文件，不再由本工具生成。

## 结构

```
.
├── fetch.py              # 拉订阅、解析节点 → nodes/*.csv
├── gen.py                # 生成 sing-box.json
├── config.json           # 配置文件（需自建）
├── config.example.json   # 配置模板
├── country_map.json      # 国家/地区别名映射
├── rulesets/             # geosite 规则集（本地 srs 文件）
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
python3 gen.py     # 按 config 策略生成 sing-box.json
sing-box check -c sing-box.json   # 校验配置
sing-box run -c sing-box.json     # 运行（调试期手动，稳定后配 systemd）
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
| `group_settings` | 可选，按组覆盖 urltest 的 interval / tolerance |

### 自用分组逻辑

- **mass** — `mass: true` 且节点名命中 `nearby` 地区，urltest（1.13 无 random 出站，升 1.14 后可换）
- **ai** — `purity: true` 且节点名命中 `oversea` 地区，urltest
- **all** — 排除所有 `purity: true` 的节点做兜底，urltest

### 可观测性

sing-box 的 Clash API 监听 127.0.0.1:9090：`GET /proxies` 看分组与当前节点，`GET /proxies/{组}/delay` 手动测延迟，`GET /connections` 看每连接命中的规则与出口，`GET /logs` 实时日志。

## 添加新机场

1. 在 `parsers/` 下新建 `{sp}.py`，仿照现有 parser 实现 `parse()` 和 `main()`（这一步请直接交给你的Agent）
2. 在 `config.json` 的 `providers` 中加一条 `{ "sp": "...", "sublink": "...", ... }`

## 现有机场

每个 parser 系仓库持有者基于自身网络环境测试过的节点获取方案，**不对机场质量、可用性、线路稳定性做任何保证**。选择机场前建议自行评估。

| parser | 协议 | UA | 机场官网 |
|--------|------|-----|---------|
| haita | trojan | v2rayN | 求你了别跑路好吗 |
| ovo | hysteria2 | mihomo | 我愿称之为唯一真神 |
| top | hysteria2 / vless | mihomo | https://顶级机场.com 一分钱一分货，拿来当备用吧。 |
| xfltd | anytls / vless | mihomo | https://xfltd.org 拉完了，不建议使用。 |
