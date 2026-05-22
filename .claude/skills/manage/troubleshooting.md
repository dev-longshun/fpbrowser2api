# 故障排查指南

## "login error" (ret:1015)

**原因**: 编译的 executor 硬编码了美国数据中心 URL (`dreamina-api.us.capcut.com`)，但账号是 JP/SG 区域。

**修复**: main.py 中的 region-patch 会自动处理。验证是否生效：
```bash
grep "region-patch" server.log
```
如果没有输出，重启服务。如果显示 "FAILED: jimeng_task_executor never appeared"，检查 Python 版本是否为 3.10。

**URL 映射**:
- `dreamina-api.us.capcut.com` → `mweb-api-sg.capcut.com`
- `commerce.us.capcut.com` → `commerce-api-sg.capcut.com`

## 任务卡在 "queued"（调度器不分配）

**原因**: 窗口被以下条件阻塞：
- `consecutive_errors` >= `continuous_error_threshold` (默认 3)
- `remaining_quota` = 0
- `error_cooldown_until` 在未来时间
- `inflight_slots` 已满（并发数=1 时，1个正在执行的任务就会占满）

**修复**: 重置窗口映射：
```bash
curl -s -X PATCH "http://{host}:8000/api/admin/task-type-windows/{mapping_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"consecutive_errors": 0, "remaining_quota": 9999, "inflight_slots": 0, "error_cooldown_until": "2020-01-01 00:00:00"}'
```

**诊断**: 直接查数据库确认状态：
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/fpbrowser.db')
conn.row_factory = sqlite3.Row
for r in conn.execute('SELECT id, consecutive_errors, remaining_quota, inflight_slots, error_cooldown_until, enabled FROM task_type_windows'):
    print(dict(r))
"
```

## Playwright CDP 超时

**原因**: Roxy Browser 的 dashboard 标签页（`dashboard.html`）导致 Playwright 的 `Target.setAutoAttach` 初始化挂起。这是最常见的任务失败原因。

**修复**: 通过 CDP 关闭 dashboard 标签页（见 operations.md 第 4.1 步和第 7 步）。

**预防**: 每次通过 API 打开 Roxy 窗口后，必须立即检查并关闭 dashboard 标签页。用户不操作 Roxy Browser，所有窗口管理由 Claude 执行，因此这一步由 Claude 在打开窗口后自动完成。

**也可能表现为**: `server restarted` / `task_failed` 错误 — 当 CDP 超时后任务被标记为失败，错误信息可能不直接提到 dashboard。

## "socksio package is not installed"

**原因**: Shell 环境变量 `all_proxy=socks5://...` 被 httpx 捡到。

**修复**:
```bash
unset all_proxy
# 或者安装 socks 支持
pip install httpx[socks]
```

## "duration only supports 10 or 15"

**原因**: Seedance 2.0 只接受 10 或 15 秒时长。

**修复**: 请求中设置 `"duration": 10` 或 `"duration": 15`。

## "task_type_code does not exist"

**原因**: `/v1/videos` 的 `model` 字段被当作任务类型代码查找。

**修复**: 使用 `"model": "dreamina_workflow"`，通过 `"model_name": "seedance-2.0-fast"` 传递实际模型。

## "The audio may contain inappropriate content"

**原因**: Dreamina 内容审核拒绝了生成结果。非技术错误。

**修复**: 用不同的提示词重试。这类错误不会惩罚窗口（NonPenalizedTaskError）。

## 视频生成成功但支持的模型不确定

已确认支持的 model_name 值：
- `seedance-2.0-fast` (快速版)
- `seedance-2.0` (标准版)
- `seedance-2.0-pro` (专业版)

别名也有效：`seedance-2`, `seedance-2-fast`, `seedance-2-pro`, `seedance_2_0`, `seedance_2_0_fast`
