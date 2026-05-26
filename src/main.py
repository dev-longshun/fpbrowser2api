"""Route wrapper around the packaged sourceless app.

The released project keeps the real FastAPI application in ``src/main.pyc``.
This source wrapper loads that application unchanged and adds local admin
pages that are safe to maintain without rebuilding the packaged bytecode.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Body, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

from .core.database import Database
from .core.paths import STATIC_DIR
from .services.playwright_broswer_context import get_or_create_ctx, pick_working_page_from_context


_ORIGINAL_MAIN_PATH = Path(__file__).with_suffix(".pyc")


def _load_original_app():
    spec = importlib.util.spec_from_file_location("src._main_pyc", _ORIGINAL_MAIN_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load packaged app from {_ORIGINAL_MAIN_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


app = _load_original_app()

from .api.admin import verify_admin_token  # noqa: E402


def _page(path: Path) -> Response:
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse(f"<h1>页面不存在</h1><p>{path.name}</p>", status_code=404)


@app.get("/admin/workflow", response_class=HTMLResponse)
async def admin_workflow_page():
    return _page(STATIC_DIR / "workflow.html")


_DREAMINA_ACCOUNT_JS = r"""
() => {
  const parseJson = (value) => {
    if (!value) return null;
    if (typeof value === "object") return value;
    if (typeof value !== "string") return null;
    try { return JSON.parse(value); } catch (_err) { return null; }
  };

  const fromWindowObject = () => {
    const raw = window.__userInfo || parseJson(window.__userInfoStringify);
    const data = raw && raw.data ? raw.data : raw;
    return data && data.user_info ? data.user_info : null;
  };

  const fromGtwScript = () => {
    const el = document.getElementById("__GTW_USER_INFO__");
    const outer = parseJson(el && el.textContent);
    const raw = outer && outer.__userInfoStringify ? parseJson(outer.__userInfoStringify) : null;
    return raw && raw.data && raw.data.user_info ? raw.data.user_info : null;
  };

  const fromVisibleProfile = () => {
    const el = document.querySelector("[class*='user-name']");
    const nick = el && (el.textContent || "").trim();
    return nick ? { nick_name: nick } : null;
  };

  const info = fromWindowObject() || fromGtwScript() || fromVisibleProfile() || {};
  const profileLink = document.querySelector("a[href*='/ai-tool/personal/']");
  const profileUrl = location.href.includes("/ai-tool/personal/")
    ? location.href
    : (profileLink && profileLink.href ? profileLink.href : location.href);

  return {
    nick_name: String(info.nick_name || info.nickname || info.user_name || info.username || "").trim(),
    user_id: String(info.user_id || info.uid || "").trim(),
    email: String(info.email || "").trim(),
    profile_url: profileUrl,
  };
}
"""


def _compact_account_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    nick_name = str(payload.get("nick_name") or "").strip()
    user_id = str(payload.get("user_id") or "").strip()
    profile_url = str(payload.get("profile_url") or "").strip()
    email = str(payload.get("email") or "").strip()
    return {
        "account": nick_name,
        "user_id": user_id,
        "profile_url": profile_url,
        "email": email,
    }


async def _read_dreamina_account_from_window(mapping: Dict[str, Any]) -> Dict[str, Any]:
    ctx = get_or_create_ctx(
        vendor=str(mapping.get("vendor") or ""),
        base_url=str(mapping.get("lan_addr") or ""),
        access_key=mapping.get("access_key"),
        space_id=str(mapping.get("space_id") or ""),
        window_key=str(mapping.get("window_key") or ""),
    )
    pure_mode = bool(mapping.get("pure_mode", True))
    await ctx.ensure_open(headless=False, require_page=True, pure_mode=pure_mode)
    page = ctx.page
    if page is None and ctx.context is not None:
        page = await pick_working_page_from_context(ctx.context)
    if page is None:
        raise HTTPException(status_code=409, detail="窗口已打开，但未找到可读取的页面")
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=8000)
    except Exception:
        pass
    payload = await page.evaluate(_DREAMINA_ACCOUNT_JS)
    if not isinstance(payload, dict):
        payload = {}
    return _compact_account_payload(payload)


@app.post("/api/admin/task-type-windows/{mapping_id}/sync-dreamina-account")
async def sync_dreamina_account_name(
    mapping_id: int,
    token: str = Depends(verify_admin_token),
):
    del token
    db = Database()
    mapping: Optional[Dict[str, Any]] = await db.get_task_type_window_context(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="绑定窗口不存在")
    if str(mapping.get("create_task_handler") or mapping.get("task_code") or "") != "dreamina_workflow":
        raise HTTPException(status_code=400, detail="当前接口仅支持 Dreamina / 即梦窗口")

    account = await _read_dreamina_account_from_window(mapping)
    account_name = str(account.get("account") or "").strip()
    if not account_name:
        raise HTTPException(status_code=409, detail="未能从当前即梦页面读取账号名，请先确认窗口已登录")

    window = await db.get_window(int(mapping.get("window_pk") or 0))
    if not window:
        raise HTTPException(status_code=404, detail="窗口记录不存在")

    await db.update_window_platform_binding(
        space_pk=int(window.space_pk),
        window_key=str(mapping.get("window_key") or ""),
        platform_account_id=None,
        platform_account=account_name,
        platform_url=str(account.get("profile_url") or ""),
    )
    return {
        "success": True,
        "message": "即梦账号名已读取",
        **account,
    }


# ─── Multi API Key Management ────────────────────────────────────────────────

import secrets
import aiosqlite

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = str(_DATA_DIR / "fpbrowser.db")

_API_KEYS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    key_value TEXT NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT (datetime('now','localtime')),
    last_used_at TIMESTAMP DEFAULT NULL
);
"""


@app.on_event("startup")
async def _ensure_api_keys_table():
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute(_API_KEYS_TABLE_SQL)
        await conn.commit()


@app.get("/api/admin/api-keys")
async def list_api_keys(token: str = Depends(verify_admin_token)):
    del token
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT id, name, key_value, enabled, created_at, last_used_at FROM api_keys ORDER BY id"
        )
        rows = await cursor.fetchall()
    keys = []
    for r in rows:
        kv = r["key_value"]
        preview = kv[:6] + "..." + kv[-4:] if len(kv) > 12 else kv
        keys.append({
            "id": r["id"],
            "name": r["name"],
            "key_value": kv,
            "key_preview": preview,
            "enabled": bool(r["enabled"]),
            "created_at": r["created_at"],
            "last_used_at": r["last_used_at"],
        })
    return {"keys": keys}


@app.post("/api/admin/api-keys")
async def create_api_key(body: Dict[str, Any] = Body(...), token: str = Depends(verify_admin_token)):
    del token
    name = str(body.get("name") or "").strip()
    key_value = str(body.get("key_value") or "").strip()
    if not key_value:
        key_value = "sk-" + secrets.token_urlsafe(32)
    if len(key_value) < 6:
        raise HTTPException(status_code=400, detail="API Key 至少 6 个字符")
    async with aiosqlite.connect(_DB_PATH) as conn:
        try:
            await conn.execute(
                "INSERT INTO api_keys (name, key_value) VALUES (?, ?)",
                (name, key_value),
            )
            await conn.commit()
        except aiosqlite.IntegrityError:
            raise HTTPException(status_code=409, detail="该 API Key 已存在")
    return {"success": True, "key_value": key_value, "name": name}


@app.patch("/api/admin/api-keys/{key_id}")
async def update_api_key(key_id: int, body: Dict[str, Any] = Body(...), token: str = Depends(verify_admin_token)):
    del token
    sets = []
    params = []
    if "name" in body:
        sets.append("name = ?")
        params.append(str(body["name"]))
    if "enabled" in body:
        sets.append("enabled = ?")
        params.append(1 if body["enabled"] else 0)
    if not sets:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    params.append(key_id)
    async with aiosqlite.connect(_DB_PATH) as conn:
        r = await conn.execute(f"UPDATE api_keys SET {', '.join(sets)} WHERE id = ?", params)
        await conn.commit()
        if r.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key 不存在")
    return {"success": True}


@app.delete("/api/admin/api-keys/{key_id}")
async def delete_api_key(key_id: int, token: str = Depends(verify_admin_token)):
    del token
    async with aiosqlite.connect(_DB_PATH) as conn:
        r = await conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        await conn.commit()
        if r.rowcount == 0:
            raise HTTPException(status_code=404, detail="Key 不存在")
    return {"success": True}
