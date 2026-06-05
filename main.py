"""FPBrowser2API - Main Entry Point

启动方式：
  cd fpbrowser2api
  python main.py
"""

import pathlib
import sqlite3
import sys
import threading

import uvicorn

_US_TO_SG = {
    "https://dreamina-api.us.capcut.com": "https://mweb-api-sg.capcut.com",
    "https://commerce.us.capcut.com": "https://commerce-api-sg.capcut.com",
    "https://imagex16-normal-us-ttp.capcutapi.us": "https://imagex-normal-sg.capcutapi.com",
}

_patch_attempts = 0


def _patch_dreamina_region():
    """Redirect US-datacenter API URLs to SG for JP/SG-region accounts."""
    global _patch_attempts
    _patch_attempts += 1
    mod = None
    mod_key = None
    for key, m in sys.modules.items():
        if "jimeng_task_executor" in key:
            mod = m
            mod_key = key
            break
    if mod is None:
        if _patch_attempts <= 20:
            threading.Timer(3.0, _patch_dreamina_region).start()
            if _patch_attempts % 5 == 0:
                print(f"[region-patch] Attempt {_patch_attempts}: jimeng_task_executor not yet in sys.modules, retrying...")
        else:
            print("[region-patch] FAILED: jimeng_task_executor never appeared in sys.modules after 60s")
            print(f"[region-patch] Available modules containing 'jimeng': {[k for k in sys.modules if 'jimeng' in k]}")
            print(f"[region-patch] Available modules containing 'executor': {[k for k in sys.modules if 'executor' in k]}")
        return
    print(f"[region-patch] Found module as '{mod_key}' on attempt {_patch_attempts}")
    patched = []
    for attr in ("_DREAMINA_API_BASE", "_DREAMINA_IMAGEX_BASE"):
        old = getattr(mod, attr, None)
        if old and old in _US_TO_SG:
            setattr(mod, attr, _US_TO_SG[old])
            patched.append(f"{attr}: {old} -> {_US_TO_SG[old]}")
    for attr in (
        "_DREAMINA_CREDITS_URL",
        "_DREAMINA_USER_CREDIT_URL",
        "_DREAMINA_SUBSCRIPTION_USER_INFO_URL",
    ):
        old = getattr(mod, attr, None)
        if old:
            new = old
            for us, sg in _US_TO_SG.items():
                new = new.replace(us, sg)
            if new != old:
                setattr(mod, attr, new)
                patched.append(f"{attr}: ...us... -> ...sg...")
    if patched:
        print(f"[region-patch] Patched {len(patched)} Dreamina URLs to SG datacenter")
        for p in patched:
            print(f"  {p}")


def _clear_dreamina_cooldown():
    """Periodically NULL out cooldown_until set more than 10 minutes in the future for dreamina_workflow windows."""
    try:
        db_path = pathlib.Path(__file__).parent / "data" / "fpbrowser.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path), timeout=5)
            cursor = conn.execute(
                """
                UPDATE task_type_windows
                SET cooldown_until = NULL, updated_at = datetime('now','localtime')
                WHERE cooldown_until IS NOT NULL
                  AND cooldown_until > datetime('now', 'localtime', '+10 minutes')
                  AND task_type_id IN (
                      SELECT id FROM task_types WHERE code = 'dreamina_workflow'
                  )
                """
            )
            if cursor.rowcount > 0:
                print(f"[cooldown-patch] Cleared cooldown_until for {cursor.rowcount} dreamina window(s)")
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[cooldown-patch] Error: {e}")
    threading.Timer(60.0, _clear_dreamina_cooldown).start()


if __name__ == "__main__":
    from src.core.config import config

    threading.Timer(2.0, _patch_dreamina_region).start()
    threading.Timer(5.0, _clear_dreamina_cooldown).start()

    uvicorn.run(
        "src.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
        ws_ping_interval=30,
        ws_ping_timeout=120,
    )
