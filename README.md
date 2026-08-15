# 科学上网配置管理

dae + sing-box 双层代理方案：dae 负责内核层直连分流与广告拦截，sing-box 负责代理流量分流与节点管理，clashtui 负责终端观测与控制。

## 架构

```
应用流量
  │
  ▼
dae（tproxy 透明代理）── 直连规则命中 → 国内/私有网段直连
  │（其余流量）
  ▼
sing-box（mixed 入站 127.0.0.1:20122）── geosite 规则分流 → ai / mass / all 三组 → 机场节点
  │
  ▼
clashtui（clash api 127.0.0.1:9090）── 节点/延迟/连接/日志观测
```

- **dae**：tproxy 透明代理。负责直连（geosite:cn、baidu/apple/microsoft、私有网段、qbittorrent/aria2c/zerotier 等进程）、广告拦截（geosite:category-ads），其余流量 fallback 到 sing-box。配置为手写静态文件 `dae_config.dae`。
- **sing-box**：mixed 入站 20122 接收 dae 转来的流量，geosite 规则集在内部完成 ai/mass/all 分组分流，clash api 9090 对外提供观测与控制接口。配置由 `gen.py` 从 `nodes/*.csv` 生成。
- **clashtui**：Rust TUI（基于 clashtui 删减改造，仅支持 sing-box）。四页：Status / Proxies / Connections / Logs，另含健康监视器。

## 目录结构

```
.
├── fetch.py              # 拉订阅、解析节点 → nodes/*.csv
├── gen.py                # 按 config.json 策略生成 sing-box.json
├── unlock.py             # AI 解锁批量检测（--sync 自动维护 ai 组）
├── config.json           # 节点分组策略（需自建，参考 config.example.json）
├── config.example.json   # 配置模板
├── dae_config.dae        # dae 静态配置（手写维护，勿用 gen.py 生成）
├── dae.sh                # 应用 dae 配置：sudo bash dae.sh
├── singbox.sh            # 生成 sing-box 配置 + 校验 + 热重载（bashrc 别名 singbox-update）
├── country_map.json      # 国家/地区别名映射（parsers 使用）
├── parsers/              # 各机场解析器（fetch.py 动态加载）
├── rulesets/             # geosite 规则集（gen.py 引用，本地 srs 文件）
├── sing-box.json         # 生成的 sing-box 配置（gitignore）
├── .clashtui/            # clashtui 配置目录（keymap/theme/日志，gitignore）
└── clashtui/             # TUI 源码（bin/clashtui 为构建产物，gitignore）
```

## 使用

### 更新节点

```bash
python3 fetch.py   # 拉取 validity=false 的机场 → nodes/*.csv（有更新时才跑）
singbox-update     # 生成 + 校验 + 热重载，一步完成（bashrc 别名）
```

`singbox-update` 等价于：`python3 gen.py` + `sing-box check` + `systemctl --user restart sing-box`。任一步失败都会报错中止，不会把坏配置推给运行中的 sing-box；重启会断流几秒（现有连接重连）。

dae 配置无需变动（节点在 sing-box 侧管理）。

### 应用 dae 配置

```bash
sudo bash dae.sh          # 拷贝 dae_config.dae 到 /etc/dae 并 reload
```

### 观测与控制

```bash
clashtui                  # 终端 TUI（bashrc 别名）
```

TUI 快捷键：1-4 切换页面，Status 页含监视器状态，Proxies 页 `t` 测延迟 / `H` 隐藏死节点（history 为空者）/ 节点名段对齐显示，Connections 页实时连接（`p` 暂停/恢复），Logs 页按 `p` 开始捕获、默认停在最新一行、按 `/` 输入关键词回车过滤（Esc 取消）、F2 开关健康监视器。

### 分组逻辑

分组与规则全部由 `config.json` 声明（`groups` + `rules` 数组），`gen.py` 只做渲染，改配置无需动代码。

- **stable** — top 日/台 + ovo 日/台/新，urltest（2m/100ms），日常浏览与开发流量（google、telegram、github 等）
- **ai** — haita 海外节点，selector 手动选择 + 健康监视器保底，仅承载 AI 流量（openai/gemini/grok）；ovo 因 IP 不纯净被排除
- **mass** — top 全部，urltest（30s/300ms），专供 youtube 大流量
- **all** — top + ovo 兜底，urltest（60s/50ms），其余流量

规则映射：`geosite-openai/google-gemini/xai` → ai；`geosite-youtube` → mass；`geosite-google/telegram/twitter/cloudflare/category-dev/protonmail/mozilla` + greasyfork → stable；其余 → all。注意 `google` 分类 include 了 `youtube` 与 `google-deepmind`，所以 youtube/gemini 规则必须排在 google 之前（先匹配先赢）。

新增组：往 `groups` 数组加一项（`include_sp` 选机场、`regions` 按节点名过滤、`nodes` 精确名单，三选一，`nodes` 优先级最高；`type` 为 urltest/selector）。新增规则集：用 `sing-box geosite export <分类>`（需 geosite.db）导出 source 后经 `sing-box rule-set compile` 编译为 srs 放入 `rulesets/`，再在 `rules` 数组引用。

### 解锁批量测试

`python3 unlock.py <sp | 组名 | 节点名>` 逐个节点测 GPT（chatgpt.com）与 Gemini（aistudio）解锁，输出表格：`python3 unlock.py top` 测 top 全部节点，`python3 unlock.py ai` 测 ai 组，`python3 unlock.py 日本-01-top-vless` 测单个。脚本依赖 dae 的 `pname(aria2c) -> direct` 规则保证节点直连。

**自动维护 ai 组**：给机场打 `purity: true`（声称解锁 AI 的机场），跑 `python3 unlock.py --sync`——脚本自动扫描所有 purity 机场的节点，把 GPT+Gemini 双解锁的写入 config.json 的 ai 组 `nodes` 列表（非 purity 机场的手动节点保留），然后 `singbox-update` 生效。

### 健康监视器

ai 组对 IP 质量要求高，采用手动选择 + 自动保底：每 30 秒只测当前选中节点，延迟 ≤1200ms 则保持不动；超标或测速失败则平行测同组其他节点，自动切到延迟最低者。F2 开关，状态显示在 Status 页。阈值与周期在 `clashtui/src/tui/monitor.rs` 顶部常量。

## 服务管理

| 服务 | 类型 | 状态 |
|------|------|------|
| dae | systemd 系统服务 | 已 enable，开机自启 |
| sing-box | systemd 用户服务（sing-box.service） | 已 enable + linger，开机自启 |
| clashtui | bashrc 别名 | 手动启动 |

sing-box 用户服务日志：`journalctl --user -u sing-box`。

## 踩坑记录

- dae 的 routing 目标**必须是 group 名**，不能直接引用节点名；`dae validate` 不校验 routing 目标，reload 时才报错，改完配置务必 `dae.sh` reload 并查 `journalctl -u dae`
- dae 2.0 进程匹配函数是 `pname()`，不存在 `process()`（reload 报 unknown function: process）
- dae 配置权限必须 600（0644 会被拒绝加载）
- sing-box 1.13 的 DNS server 用新格式（type: udp/https），旧 address 格式已废弃
- 生成配置后必须 `sing-box check`，规则集文件缺失时 check 报错
- **geosite 数据里 `google` 分类 include 了 `youtube` 和 `google-deepmind`**：规则顺序敏感（先匹配先赢），youtube/gemini 必须排在 google 前面
- **`sing-box geosite export` 默认输出 source 格式 JSON**：路由加载要求 binary srs，需先 `sing-box rule-set compile`
- **sing-box 的 clash API 不支持配置重载**：`PUT /configs` 是空实现（返回 204 但不做任何事，仅 mihomo 兼容），`PATCH /configs` 只能切 mode。改配置唯一生效方式是 `systemctl --user restart sing-box`（不要信 204）
- **DNS 的 detour 不能直接指向代理组**：DoH 走 ai/mass 等组会循环依赖（DNS 查询经代理发出，而代理节点的服务器域名解析又要用这个 DNS，exchange 全部超时，表现为 `lookup <节点域名>: context deadline exceeded`）。正确架构（已落地）：节点出站加 `domain_resolver: ali` 直连解析节点域名防循环，海外解析用带 detour 的 remote server（`final: remote`）——注意 sing-box 1.12+ 已废弃 `outbound` DNS 规则项，用 outbound 的 `domain_resolver` 字段替代
- sing-box 配置没有热更新能力，gen.py 后必须手动触发重载（用 singbox-update，勿忘）

## 添加新机场

1. 在 `parsers/` 下新建 `{sp}.py`，仿照现有 parser 实现 `parse()` 和 `main()`
2. 在 `config.json` 的 `providers` 中加一条 `{ "sp": "...", "sublink": "...", "validity": false, ... }`
3. 普通机场：把它加进 `groups` 数组对应组的 `include_sp`，然后 fetch + singbox-update
4. 声称解锁 AI 的机场：额外加 `"purity": true`，拉取后跑 `python3 unlock.py --sync {sp}` 自动把双解锁节点写进 ai 组

## 现有机场

每个 parser 系仓库持有者基于自身网络环境测试过的节点获取方案，**不对机场质量、可用性、线路稳定性做任何保证**。选择机场前建议自行评估。

| parser | 协议 | UA | 备注 |
|--------|------|-----|------|
| haita | trojan | v2rayN | ai 组（IP 干净） |
| ovo | hysteria2 | mihomo | stable/all 组（IP 不纯，不进 ai） |
| top | hysteria2 / vless | mihomo | mass 组 + ai（部分节点解锁） |
| xfltd | anytls / vless | mihomo | 已从 config.json 移除，parser 保留备用 |
