---
name: video
description: 生成视频。提交 Seedance 视频生成任务，监控进度，返回结果 URL。当用户说"生成视频"、"做一个视频"、"测试视频"、"generate video"时触发。
user-invocable: true
allowed-tools: Bash Read
argument-hint: "[prompt]"
---

# 视频生成工作流

快速生成 Seedance AI 视频。

## 流程

### 1. 确认服务器

确定目标服务器地址和 API key：
- 本地: `http://127.0.0.1:8000`，API key 从 `config/setting.toml` 读取
- 远程: `http://{server-ip}:8000`，API key 需用户提供或从 memory 读取

### 2. 验证服务运行中

```bash
curl -s http://{host}:8000/v1/task-types \
  -H "Authorization: Bearer {api_key}" -o /dev/null -w "%{http_code}"
```

如果返回非 200，启动服务（参考 /manage skill）。

### 3. 提交任务

```bash
curl -s -X POST "http://{host}:8000/v1/videos" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {api_key}" \
  -d '{
    "model": "dreamina_workflow",
    "prompt": "{用户提供的提示词}",
    "aspect_ratio": "{比例}",
    "duration": {时长},
    "model_name": "{模型}"
  }'
```

**默认值**（用户未指定时）：
- `aspect_ratio`: `"16:9"`
- `duration`: `10`
- `model_name`: `"seedance-2.0-fast"`

**参数约束**：
- `model`: 固定为 `"dreamina_workflow"`（任务类型代码，不是模型名）
- `model_name`: `seedance-2.0-fast` / `seedance-2.0` / `seedance-2.0-pro`
- `duration`: 仅支持 `10` 或 `15`
- `aspect_ratio`: `"16:9"` / `"9:16"` / `"1:1"`

### 4. 监控进度

使用 Monitor 工具每 15 秒轮询：

```bash
until curl -s "http://{host}:8000/v1/videos/{task_id}" \
  -H "Authorization: Bearer {api_key}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
status = d.get('status','')
progress = d.get('progress', 0)
print(f'status={status} progress={progress}%', flush=True)
if status in ('completed','failed','error'):
    print(json.dumps(d, indent=2, ensure_ascii=False), flush=True)
    sys.exit(0)
sys.exit(1)
"; do sleep 15; done
```

状态流转: `queued` → `in_progress` (0-100%) → `completed` / `failed`

### 5. 返回结果

- **成功**: 将 `video_url`（CDN 链接）返回给用户。提醒用户 CDN 链接有时效性，需尽快下载。
- **失败**: 检查错误信息，根据 [troubleshooting.md](../manage/troubleshooting.md) 排查。

### 常见失败处理

| 错误 | 处理 |
|------|------|
| 内容审核拒绝 | 换提示词重试 |
| login error | 检查 region-patch |
| 任务卡在 queued | 重置窗口映射（/manage skill） |
| duration 错误 | 修正为 10 或 15 |
