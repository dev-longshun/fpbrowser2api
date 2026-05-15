---
name: deploy
description: 部署 fpbrowser2api 到远程服务器。引导用户提供服务器信息，通过 SSH 完成安装、配置、初始化。当用户说"部署到服务器"、"新服务器"、"迁移到 VPS"、"deploy"时触发。
user-invocable: true
allowed-tools: Bash Read Edit Write
argument-hint: "[server-ip]"
---

# 服务器部署工作流

将 fpbrowser2api + Roxy Browser 部署到远程 Windows 服务器的交互式流程。

## 第 1 步：收集服务器信息

向用户询问：
1. 服务器 IP 地址
2. SSH / RDP 凭据（用户名 + 密码）
3. 操作系统（推荐 Windows Server）
4. 是否已安装 Python 3.10？
5. 是否已安装 Roxy Browser？

## 第 2 步：验证环境

```bash
ssh user@{server-ip} "echo 'connected' && python --version"
```

检查项：
- Python 3.10.x（必须精确匹配，.pyc 兼容性要求）
- Roxy Browser 运行中（端口 50000）
- 磁盘空间 > 1GB
- 网络连通 dreamina.capcut.com

## 第 3 步：传输项目文件

```bash
scp -r /path/to/fpbrowser2api user@{server-ip}:~/fpbrowser2api
```

## 第 4 步：远程安装依赖

```bash
ssh user@{server-ip} "cd ~/fpbrowser2api && python -m venv .venv && .venv\\Scripts\\activate && pip install -r requirements.txt && pip install httpx[socks]"
```

## 第 5 步：配置

编辑远程 `config/setting.toml`：
- `api_key` 设为强随机字符串
- `admin_password` 设为安全密码
- `host = "0.0.0.0"` 保持不变

## 第 6 步：启动服务

```bash
ssh user@{server-ip} "cd ~/fpbrowser2api && .venv\\Scripts\\activate && python main.py"
```

## 第 7 步：初始化管理层级

通过 SSH 执行管理 API 调用，依次创建：
1. Admin 登录获取 token
2. 创建 Project
3. 创建 Browser Server（填入服务器上 Roxy Browser 的 API token）
4. 创建 Space（填入 Roxy workspace ID）
5. 同步窗口
6. 绑定窗口到 dreamina_workflow 任务类型

## 第 8 步：用户操作 — 登录账号

提示用户：
> "请通过 RDP 远程连接到服务器，打开 Roxy Browser，在浏览器窗口中登录你的即梦/Dreamina 账号。完成后告诉我，我来验证连接。"

## 第 9 步：验证并测试

用户确认登录后：
1. 刷新每个窗口的额度
2. 提交测试视频生成任务
3. 监控至完成
4. 报告结果

## 第 10 步：生产加固

- 防火墙规则（只暴露 8000 端口，或用 nginx 反向代理）
- SSL/TLS 证书
- 自动重启（Windows Task Scheduler / Linux systemd）
- 日志监控

## 服务器配置要求

| 组件 | 最低 | 推荐 |
|------|------|------|
| OS | Windows 10 / Server 2019 | Windows Server 2022 |
| RAM | 4 GB | 8 GB |
| 磁盘 | 10 GB | 50 GB |
| CPU | 2 核 | 4 核 |
| 网络 | 稳定连接 | 日本/新加坡 VPS（低延迟） |
| Python | 3.10.x（精确匹配） | 3.10.x |

## 注意事项

- Roxy Browser 需要桌面环境（Windows RDP 最简单）
- 日本或新加坡 VPS 位置对 Dreamina SG 数据中心延迟最佳
- region-patch 仅 JP/SG 账号需要；美区账号使用默认 URL
- 首次部署后，记录新服务器的管理层级 ID 供后续操作使用
