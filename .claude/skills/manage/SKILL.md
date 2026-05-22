---
name: manage
description: 管理 fpbrowser2api 视频生成平台。启动/停止服务、管理账号池、绑定窗口、重置错误、排查故障。当用户说"启动服务"、"添加账号"、"任务卡住了"、"检查状态"、"刷新额度"时触发。
user-invocable: true
allowed-tools: Bash Read Edit Write
---

# fpbrowser2api 平台管理

你正在操作 fpbrowser2api —— 一个将即梦 (Dreamina/Seedance) 浏览器会话转化为 OpenAI 兼容视频生成 API 的反向代理平台。

## 架构概览

```
下游调用者 (curl / NewAPI / 任何 HTTP 客户端)
        │
        ▼
  fpbrowser2api  (FastAPI, 端口 8000)
        │  调度任务到可用窗口
        ▼
  Playwright CDP 连接
        │
        ▼
  Roxy Browser  (指纹浏览器, API 端口 50000)
        │  每个窗口 = 独立浏览器配置
        ▼
  dreamina.capcut.com  (即梦/Seedance 视频生成)
```

## 管理层级

```
Project → Browser Server (Roxy 实例) → Space (工作区) → Windows (窗口) → Task Type Binding (任务绑定)
```

## 操作流程

执行任何操作前，先确认服务器地址（本地 `127.0.0.1` 或远程 IP）。

### 获取 Admin Token

所有管理 API 需要先登录：

```bash
TOKEN=$(curl -s -X POST http://{host}:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
```

### 操作清单

详细操作步骤参见 [operations.md](operations.md)。

核心操作：
1. **启动服务** — 激活 venv，unset all_proxy，启动 main.py，验证 region-patch
2. **添加账号** — 用户登录 Roxy 窗口后，同步窗口、绑定任务类型、刷新额度
3. **打开窗口** — 通过 Roxy API 打开后，**必须立即关闭 dashboard 标签页**（否则 CDP 超时导致所有任务失败）
4. **重置窗口** — 清除 consecutive_errors、error_cooldown_until、inflight_slots
5. **刷新额度** — POST refresh-remaining-quota 验证账号可用
6. **排查故障** — 检查 server.log、窗口映射状态、CDP 连接

> **关键规则：用户不操作 Roxy Browser，所有窗口管理由 Claude 执行。每次打开窗口后必须检查并关闭 dashboard 标签页。**

### 常见故障排查

详细排查指南参见 [troubleshooting.md](troubleshooting.md)。

| 现象 | 原因 | 修复 |
|------|------|------|
| login error (ret:1015) | 数据中心不匹配 | 检查 region-patch 是否生效 |
| 任务卡在 queued | 窗口被错误/冷却阻塞 | 重置窗口映射 |
| CDP 超时 | dashboard 标签页干扰 | 通过 CDP 关闭 dashboard 标签 |
| socksio 错误 | shell 代理变量 | unset all_proxy |
| duration 错误 | 只支持 10 或 15 秒 | 修正 duration 参数 |
| task_type_code 不存在 | model 字段用错 | model 应为 "dreamina_workflow" |
