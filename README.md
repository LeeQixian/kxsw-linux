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
├── config.json           # 节点分组策略（需自建，参考 config.example.json）
├── config.example.json   # 配置模板
├── dae_config.dae        # dae 静态配置（手写维护，勿用 gen.py 生成）
├── dae.sh                # 应用 dae 配置：sudo bash dae.sh
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
python3 fetch.py          # 拉取 validity=false 的机场 → nodes/*.csv
python3 gen.py            # 按 config 策略生成 sing-box.json
sing-box check -c sing-box.json   # 校验（必做）
systemctl --user restart sing-box # 重启核心生效
```

dae 配置无需变动（节点在 sing-box 侧管理）。

### 应用 dae 配置

```bash
sudo bash dae.sh          # 拷贝 dae_config.dae 到 /etc/dae 并 reload
```

### 观测与控制

```bash
clashtui                  # 终端 TUI（bashrc 别名）
```

TUI 快捷键：1-4 切换页面，Status 页含监视器状态，Proxies 页 `t` 测延迟 / `H` 隐藏死节点（history 为空者），Connections 页实时连接（`p` 暂停/恢复），Logs 页按 `p` 开始捕获，F2 开关健康监视器。

## 分组逻辑

- **mass** — `mass: true` 且节点名命中 `nearby` 地区，urltest（1.13 无 random 出站，升 1.14 后可换）
- **ai** — `purity: true` 且节点名命中 `oversea` 地区，selector 手动选择 + 健康监视器保底
- **all** — 排除所有 `purity: true` 的节点做兜底，urltest

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

## 添加新机场

1. 在 `parsers/` 下新建 `{sp}.py`，仿照现有 parser 实现 `parse()` 和 `main()`
2. 在 `config.json` 的 `providers` 中加一条 `{ "sp": "...", "sublink": "...", ... }`
3. 重新 fetch + gen + 重启 sing-box

## 现有机场

每个 parser 系仓库持有者基于自身网络环境测试过的节点获取方案，**不对机场质量、可用性、线路稳定性做任何保证**。选择机场前建议自行评估。

| parser | 协议 | UA | 备注 |
|--------|------|-----|------|
| haita | trojan | v2rayN | purity 节点（ai 组） |
| ovo | hysteria2 | mihomo | purity 节点（ai 组） |
| top | hysteria2 / vless | mihomo | mass 机场 |
| jinyun | vless | sing-box | purity 节点（ai 组） |
| xfltd | anytls / vless | mihomo | 已从 config.json 移除，parser 保留备用 |
