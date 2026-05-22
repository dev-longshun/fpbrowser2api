# fpbrowser2api — Claude Code Project Guide

## What This Project Does

fpbrowser2api is a reverse-proxy server that turns Jimeng (Dreamina/Seedance) browser sessions into OpenAI-compatible video generation API endpoints. It connects to Roxy Browser (a fingerprint browser) via Playwright CDP, executes API calls in the browser context using logged-in sessions, and returns CDN video URLs to callers.

**The user's goal**: Operate an account pool of Jimeng/Dreamina accounts, expose a unified `/v1/videos` API, and let downstream users generate Seedance AI videos. The user manages account logins; Claude handles all technical operations via natural language.

## Technical Constraints

- **Python 3.10 only** — the project is distributed as compiled .pyc bytecode
- **Region patch required** — `main.py` patches US datacenter URLs to SG for JP/SG-region accounts. Verify on every server start: `[region-patch] Patched 4 Dreamina URLs` in logs
- **Roxy Browser is a GUI app** — requires a desktop environment (Windows RDP or Linux with VNC)
- **Dashboard tab bug** — if Roxy Browser's dashboard tab is open, Playwright CDP hangs. Close it via CDP before connecting.

## Development Protocol

This project uses `./.claude/skills/protocol-dev/` as the general development protocol skill and `./.claude/skills/repo-detach-reset/` for clone/fork detachment and history reset scenarios. Commit message generation must follow the `protocol-dev` commit rules.

The same protocol set is also available for other tools:

- Codex: `./.codex/skills/protocol-dev/` and `./.codex/skills/repo-detach-reset/`
- Cursor: `./.cursor/skills/protocol-dev/` and `./.cursor/skills/repo-detach-reset/`
- Kiro: `./.kiro/steering/`

### Key Rules

- Any code change request must start with a plan and wait for explicit user authorization before editing files.
- Destructive repository operations, including history reset and remote removal, must first explain risks, rollback points, and verification steps, then wait for user authorization.
- DIY/fork-detach work must check license obligations first; when license duties are unclear, keep license and copyright notices by default.
- Detach/reset work must isolate old workflows and deployment links so releases do not target the original repository or namespace.
- Never use `rm` to delete files; use `trash`.
- `git commit` flow: show the exact commit message first, wait for confirmation, then commit with the exact reviewed message. Do not add assistant attribution such as `Co-Authored-By`.
- Do not use Markdown tables in new protocol-oriented output.
- New `git worktree` directories must be created next to the project using `{project-name}--{branch-name}`, with `/` in the branch replaced by `-`; for example `../fpbrowser2api--feat-login/`.

### Build And Verification Rules

- Use Python 3.10.x only.
- Do not casually regenerate or commit `.pyc` files unless the task explicitly asks for a release/build artifact update.
- Before starting the service, run `unset all_proxy`.
- After service startup or Dreamina/Seedance flow changes, check logs for `[region-patch] Patched 4 Dreamina URLs`.
- For Roxy Browser / Playwright CDP changes, account for the GUI requirement and close the dashboard tab after opening windows.

## Skill Workflows

Use these skills to operate the platform. They can be invoked via `/skill-name` or triggered automatically by natural language.

- `/manage`：当用户说“启动服务”“添加账号”“任务卡住了”“检查状态”“刷新额度”等时触发，用于平台管理、启停服务、账号池、窗口绑定、错误重置和故障排查。
- `/deploy`：当用户说“部署到服务器”“新服务器”“迁移到 VPS”“deploy”等时触发，用于部署到远程 Windows VPS。
- `/video`：当用户说“生成视频”“做一个视频”“测试视频”“generate video”等时触发，用于提交 Seedance 视频任务、监控进度并返回结果 URL。
- `protocol-dev`：当用户提出代码修改、Bug 调试、Commit 信息生成、分支合并/同步、文档更新或版本发布需求时触发，用于强制执行开发协议。
- `repo-detach-reset`：当用户提出切断 fork/clone 仓库关联、重置历史、清理原仓库信息或隔离旧部署链路时触发。

## Current Environment (Local Mac)

- fpbrowser2api: `/Users/longshun/Desktop/Program/00_use/fpbrowser2api`
- Roxy Browser automation: `/Users/longshun/Desktop/Program/00_use/roxy-browser-automation`
- Python venv: `.venv/` (Python 3.10)
- Config: `config/setting.toml`
- Database: `data/fpbrowser.db` (SQLite)
- Admin UI: `http://127.0.0.1:8000/admin` (admin/admin)
- Video API: `POST http://127.0.0.1:8000/v1/videos`
- API key: `mirrmart_sora2_880315`
- Roxy API: `http://127.0.0.1:50000`

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
