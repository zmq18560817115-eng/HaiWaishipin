from __future__ import annotations

import os
import sys
from pathlib import Path


def sanitize_playwright_env() -> bool:
    """Remove Cursor sandbox browser path so Playwright can use system Chrome/Edge."""
    changed = False
    browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if "cursor-sandbox-cache" in browsers:
        os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
        changed = True
    return changed


def running_in_cursor_sandbox() -> bool:
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    if "cursor-sandbox-cache" in browsers_path:
        return True
    temp = (os.environ.get("TEMP") or os.environ.get("TMP") or "").replace("\\", "/").lower()
    if "cursor-sandbox-cache" in temp:
        return True
    return False


def collector_runtime_status() -> dict:
    sanitize_playwright_env()
    browsers = discover_system_browsers()
    sandbox_path = (
        "cursor-sandbox-cache" in os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
        or running_in_cursor_sandbox()
    )
    return {
        "cursor_sandbox": sandbox_path and not browsers,
        "playwright_sandbox_path": sandbox_path,
        "system_browsers": [str(path) for _, path in browsers],
        "collector_ready": bool(browsers),
    }


def cursor_sandbox_hint() -> str:
    return (
        "检测到工作台在 Cursor 沙箱/内置终端中运行，Playwright 无法调用本机 Chrome。"
        "请关闭当前服务窗口，在资源管理器中双击「海外视频本地化MVP\\启动页面.cmd」启动，"
        "再重试 TikTok 采集（不要用 Cursor 终端运行 python -m app.main）。"
    )


def discover_system_browsers() -> list[tuple[str, Path]]:
    localappdata = os.environ.get("LOCALAPPDATA", "")
    candidates: list[tuple[str, Path]] = [
        ("chrome", Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")),
        ("chrome", Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe")),
        ("chrome", Path(localappdata) / "Google" / "Chrome" / "Application" / "chrome.exe"),
        ("edge", Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")),
        ("edge", Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")),
    ]
    if sys.platform == "darwin":
        candidates = [
            ("chrome", Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")),
            ("edge", Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")),
        ]
    elif sys.platform.startswith("linux"):
        candidates = [
            ("chrome", Path("/usr/bin/google-chrome")),
            ("chrome", Path("/usr/bin/chromium-browser")),
            ("edge", Path("/usr/bin/microsoft-edge")),
        ]
    seen: set[str] = set()
    found: list[tuple[str, Path]] = []
    for name, path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        if path.is_file():
            seen.add(key)
            found.append((name, path))
    return found


def should_skip_bundled_chromium() -> bool:
    if os.getenv("TIKTOK_COLLECTOR_SKIP_BUNDLED", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return running_in_cursor_sandbox()
