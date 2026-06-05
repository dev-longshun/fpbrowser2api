# 操作详细步骤

## 1. 启动服务

```bash
cd /path/to/fpbrowser2api
unset all_proxy
source .venv/bin/activate
nohup python main.py > server.log 2>&1 &
echo $! > fpbrowser2api.pid
```

验证：
```bash
# 检查服务响应
curl -s http://{host}:8000/docs -o /dev/null -w "%{http_code}"  # 应返回 200

# 检查 region-patch（JP/SG 账号必须）
grep "region-patch" server.log
# 应显示: [region-patch] Patched 4 Dreamina URLs to SG datacenter
```

## 2. 停止服务

```bash
kill $(cat fpbrowser2api.pid)
```

## 3. Admin 登录

```bash
TOKEN=$(curl -s -X POST http://{host}:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")
```

## 4. 添加新账号（用户已在 Roxy Browser 中登录后）

步骤：
1. 服务启动时会自动同步窗口，或重启服务触发同步
2. 通过管理 API 将新窗口绑定到 dreamina_workflow 任务类型
3. 刷新额度验证账号可用：
   ```bash
   curl -s -X POST "http://{host}:8000/api/admin/task-type-windows/{mapping_id}/refresh-remaining-quota" \
     -H "Authorization: Bearer $TOKEN"
   ```

## 5. 重置窗口映射（任务失败后）

```bash
curl -s -X PATCH "http://{host}:8000/api/admin/task-type-windows/{mapping_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"consecutive_errors": 0, "remaining_quota": 9999, "inflight_slots": 0, "error_cooldown_until": "2020-01-01 00:00:00"}'
```

## 6. 查看窗口状态（直接查数据库）

```bash
source .venv/bin/activate && python3 -c "
import sqlite3, json
conn = sqlite3.connect('data/fpbrowser.db')
conn.row_factory = sqlite3.Row
for r in conn.execute('SELECT * FROM task_type_windows'):
    print(json.dumps(dict(r), indent=2, ensure_ascii=False))
"
```

## 7. 关闭 Dashboard 标签页（CDP 修复）

```bash
DEBUG_PORT={port}  # 从 Roxy Browser 窗口信息获取

# 列出所有标签页
curl -s http://127.0.0.1:$DEBUG_PORT/json/list | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    print(f\"{t.get('type','?'):10} {t.get('title','')[:60]} {t.get('id','')}\")
"

# 关闭 dashboard 标签
TARGET_ID=$(curl -s http://127.0.0.1:$DEBUG_PORT/json/list | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    if 'dashboard' in t.get('url','').lower():
        print(t['id']); break
")
curl -s http://127.0.0.1:$DEBUG_PORT/json/close/$TARGET_ID
```

## 8. 初始化全新服务器（首次设置管理层级）

需要依次创建：
1. Project（项目）
2. Browser Server（浏览器服务器，填入 Roxy API token）
3. Space（空间，填入 Roxy workspace ID）
4. 同步窗口
5. 创建/启用 dreamina_workflow 任务类型
6. 绑定窗口到任务类型

这些操作可通过管理 UI (http://{host}:8000/admin) 或 admin API 完成。

## API 快速参考

```bash
# 视频生成
POST /v1/videos  (Bearer: api_key)
  {"model":"dreamina_workflow", "prompt":"...", "duration":10, "model_name":"seedance-2.0-fast"}

# 查询任务
GET /v1/videos/{task_id}  (Bearer: api_key)

# 可用模型名: seedance-2.0-fast, seedance-2.0, seedance-2.0-pro
# duration: 仅支持 10 或 15
# aspect_ratio: "16:9", "9:16", "1:1"
```
