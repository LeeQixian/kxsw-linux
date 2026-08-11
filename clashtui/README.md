# clashtui（删减版）

基于 [JohanChane/clashtui](https://github.com/JohanChane/clashtui) 删减改造的 sing-box 专用 TUI 客户端。

- 仅支持 sing-box（移除 mihomo 双核心支持）
- 四页：Status / Proxies / Connections / Logs
- 健康监视器：每 30s 只测当前选中节点，超阈值自动切换
- 固定连接 127.0.0.1:9090 的 Clash API

## 构建

```bash
cargo build --release
# 产物 target/release/clashtui，日常使用拷到 bin/
```

## 使用

```bash
clashtui [--config-dir DIR]
```

配置目录存放 keymap.yaml / theme.yaml / clashtui.log，默认 `~/.config/clashtui`。

### 快捷键

| 键 | 功能 |
|----|------|
| 1-4 | 切换页面（Status/Proxies/Connections/Logs） |
| q / Ctrl-c | 退出 |
| ? | 快捷键帮助 |
| F2 | 健康监视器开关 |
| Ctrl-g t | 关闭所有连接 |

Proxies 页：`j/k` 上下、`h` 返回上级、`l` 展开、`Enter` 选中（selector 组切换节点）、`t` 测当前、`a t` 全测、`H` 隐藏死节点、`/` 过滤、`f` 组内选择。

Connections 页：`p` 暂停/恢复刷新，`x`/`d` 关闭连接（按 ? 查看）。

Logs 页：按 `p` 开始捕获日志，默认停在最新一行并跟随滚动；按 `/` 进入过滤输入（标题栏输入、回车应用、Esc 取消、空输入回车清除过滤）。

### 健康监视器

ai 组（selector）手动选节点，监视器保底：每 30s 只测当前选中节点延迟，≤1200ms 保持不动；超标或失败则平行测同组其他节点（并发上限 8），自动切到延迟最低者。参数在 `src/tui/monitor.rs` 顶部常量。

### 与上游的差异

- 删除：Files/Settings/CoreSrvCtl 页面、CLI 子命令（profile/service/mode/update）、订阅与模板系统、数据库持久化、mihomo 支持、systemd 服务管理
- 修改：Clash API 地址固定 127.0.0.1:9090；keymap/theme 仅取 sing-box 段
- 新增：健康监视器（启动即检查）、隐藏死节点（H）、节点名段对齐显示（按 - 拆段、类型冗余段自动去除如 -vless/-hy2、各段按最大宽度对齐）、Logs 内置过滤输入框
- 性能：日志缓冲限长、渲染按可视窗口裁剪、阻塞调用移出 UI 线程
