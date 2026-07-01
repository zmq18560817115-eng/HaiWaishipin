"""内网部署：监听地址、访问令牌、备份目录。"""
from __future__ import annotations

import os
from pathlib import Path

from paths import PRODUCTION_ARCHIVE_DIR, WORKFLOW_ROOT


def workbench_host() -> str:
    return (os.getenv("WORKBENCH_HOST") or "127.0.0.1").strip() or "127.0.0.1"


def workbench_port() -> int:
    try:
        return max(1, min(65535, int(os.getenv("WORKBENCH_PORT", "8788"))))
    except ValueError:
        return 8788


def api_token() -> str:
    return (os.getenv("WORKBENCH_API_TOKEN") or "").strip()


def backup_root() -> Path:
    raw = (os.getenv("WORKFLOW_BACKUP_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return WORKFLOW_ROOT / "06_备份库"


def public_status() -> dict:
    host = workbench_host()
    return {
        "host": host,
        "port": workbench_port(),
        "intranet_mode": host not in ("127.0.0.1", "localhost", "::1"),
        "auth_enabled": bool(api_token()),
        "workflow_root": str(WORKFLOW_ROOT),
        "production_archive": str(PRODUCTION_ARCHIVE_DIR),
        "backup_root": str(backup_root()),
        "download": {
            "runs_zip": "/api/delivery/{slug}/zip",
            "archive_zip": "/api/archive/{slug}/latest/zip",
            "note": "用户下载到本机；服务器同时保留 runs 工作副本与 03_产出库 版本归档",
        },
    }
