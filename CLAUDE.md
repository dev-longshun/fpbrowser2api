# fpbrowser2api — Claude Code Project Guide

## What This Project Does

fpbrowser2api is a reverse-proxy server that turns Jimeng (Dreamina/Seedance) browser sessions into OpenAI-compatible video generation API endpoints. It connects to Roxy Browser (a fingerprint browser) via Playwright CDP, executes API calls in the browser context using logged-in sessions, and returns CDN video URLs to callers.

**The user's goal**: Operate an account pool of Jimeng/Dreamina accounts, expose a unified `/v1/videos` API, and let downstream users generate Seedance AI videos. The user manages account logins; Claude handles all technical operations via natural language.

## Technical Constraints

- **Python 3.10 only** — the project is distributed as compiled .pyc bytecode
- **Region patch required** — `main.py` patches US datacenter URLs to SG for JP/SG-region accounts. Verify on every server start: `[region-patch] Patched 4 Dreamina URLs` in logs
- **Roxy Browser is a GUI app** — requires a desktop environment (Windows RDP or Linux with VNC)
- **Dashboard tab bug** — if Roxy Browser's dashboard tab is open, Playwright CDP hangs. Close it via CDP before connecting.

## Skill Workflows

Use these skills to operate the platform. They can be invoked via `/skill-name` or triggered automatically by natural language.

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `/manage` | "启动服务"、"添加账号"、"任务卡住了"、"检查状态" | 平台管理：启停服务、管理账号池、重置错误、排查故障 |
| `/deploy` | "部署到服务器"、"新服务器"、"deploy" | 部署到远程 Windows VPS |
| `/video` | "生成视频"、"做一个视频"、"generate video" | 提交视频任务、监控进度、返回结果 |

## Current Environment (Local Mac)

| Component | Detail |
|-----------|--------|
| fpbrowser2api | `/Users/longshun/Desktop/Program/00_use/fpbrowser2api` |
| Roxy Browser automation | `/Users/longshun/Desktop/Program/00_use/roxy-browser-automation` |
| Python venv | `.venv/` (Python 3.10) |
| Config | `config/setting.toml` |
| Database | `data/fpbrowser.db` (SQLite) |
| Admin UI | `http://127.0.0.1:8000/admin` (admin/admin) |
| Video API | `POST http://127.0.0.1:8000/v1/videos` |
| API key | `mirrmart_sora2_880315` |
| Roxy API | `http://127.0.0.1:50000` |

## API Quick Reference

```bash
# Video generation
POST /v1/videos  (Bearer: api_key)
  {"model":"dreamina_workflow", "prompt":"...", "duration":10, "model_name":"seedance-2.0-fast"}

# Check task
GET /v1/videos/{task_id}  (Bearer: api_key)

# Admin login → token
POST /api/admin/login  {"username":"admin","password":"admin"}

# Reset stuck window
PATCH /api/admin/task-type-windows/{mapping_id}  (Bearer: admin_token)
  {"consecutive_errors":0, "remaining_quota":9999, "inflight_slots":0, "error_cooldown_until":"2020-01-01 00:00:00"}

# Refresh quota
POST /api/admin/task-type-windows/{mapping_id}/refresh-remaining-quota  (Bearer: admin_token)
```

## Important Gotchas

1. Always `unset all_proxy` before starting the server (prevents socksio errors)
2. Video `duration` must be 10 or 15 — other values are rejected
3. The `model` field in `/v1/videos` is the task type code (`dreamina_workflow`), not the actual model name. Pass the model via `model_name`
4. CDN video URLs are temporary — callers should download promptly
5. After any task failure, check and reset `consecutive_errors`, `error_cooldown_until`, and `inflight_slots` on the window mapping
6. The region patch fires via threading.Timer — check `server.log` for `[region-patch]` to confirm it applied
