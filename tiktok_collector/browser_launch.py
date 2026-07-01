from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from playwright._impl._errors import Error as PlaywrightError


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)

COLLECTOR_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-session-crashed-bubble",
]


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
    blocked = collector_launch_blocked_reason()
    return {
        "cursor_sandbox": sandbox_path and not browsers,
        "playwright_sandbox_path": sandbox_path,
        "system_browsers": [str(path) for _, path in browsers],
        "collector_ready": bool(browsers) and not blocked,
        "launch_blocked": blocked,
        "workbench_launcher": os.environ.get("WORKBENCH_LAUNCHER", ""),
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


def collector_launch_blocked_reason() -> str | None:
    """Return user-facing reason when TikTok collector cannot run in this process."""
    sanitize_playwright_env()
    if os.environ.get("WORKBENCH_LAUNCHER") != "startup-cmd":
        return (
            "当前工作台不是通过「启动页面.cmd」启动（常见于 Cursor 内置终端）。"
            "请关闭本服务窗口，在资源管理器中双击 "
            "海外视频本地化MVP\\启动页面.cmd 或根目录「启动工作台.cmd」，再重试采集。"
        )
    if running_in_cursor_sandbox() and not discover_system_browsers():
        return cursor_sandbox_hint()
    return None


def should_skip_bundled_chromium() -> bool:
    if os.getenv("TIKTOK_COLLECTOR_SKIP_BUNDLED", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return running_in_cursor_sandbox()


def release_stale_profile_lock(user_data_dir: Path) -> None:
    """Remove Chromium singleton locks left by crashed Chrome/Edge sessions."""
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        path = user_data_dir / name
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError:
            pass


def _launch_error_retryable(message: str) -> bool:
    lower = message.lower()
    return any(
        token in lower
        for token in (
            "executable doesn't exist",
            "playwright install",
            "failed to launch",
            "chrome-headless-shell",
            "chromium_headless_shell",
            "cursor-sandbox-cache",
            "has been closed",
            "target page, context or browser",
            "singletonlock",
            "profile appears to be in use",
            "user data directory is already in use",
        )
    )


def _headless_modes(requested: bool) -> tuple[bool, ...]:
    return (False, True) if requested else (False,)


def _try_persistent_context(
    playwright: Any,
    *,
    user_data: str,
    headless: bool,
    locale: str,
    channel: str | None = None,
    executable_path: Path | None = None,
) -> Any:
    opts: dict[str, Any] = {
        "headless": headless,
        "locale": locale,
        "viewport": {"width": 1440, "height": 1080},
        "user_agent": DEFAULT_USER_AGENT,
        "args": list(COLLECTOR_BROWSER_ARGS),
    }
    if executable_path is not None:
        opts["executable_path"] = str(executable_path)
    elif channel:
        opts["channel"] = channel
    return playwright.chromium.launch_persistent_context(user_data, **opts)


def _try_ephemeral_context(
    playwright: Any,
    *,
    headless: bool,
    locale: str,
    executable_path: Path | None = None,
    channel: str | None = None,
) -> Any:
    launch_opts: dict[str, Any] = {
        "headless": headless,
        "args": list(COLLECTOR_BROWSER_ARGS),
    }
    if executable_path is not None:
        launch_opts["executable_path"] = str(executable_path)
    elif channel:
        launch_opts["channel"] = channel
    browser = playwright.chromium.launch(**launch_opts)
    context = browser.new_context(
        locale=locale,
        viewport={"width": 1440, "height": 1080},
        user_agent=DEFAULT_USER_AGENT,
    )
    context._collector_browser = browser  # type: ignore[attr-defined]
    return context


def close_collector_context(context: Any) -> None:
    browser = getattr(context, "_collector_browser", None)
    try:
        context.close()
    except PlaywrightError:
        pass
    if browser is not None:
        try:
            browser.close()
        except PlaywrightError:
            pass


def launch_collector_context(playwright: Any, settings: Any) -> Any:
    """Launch Chrome/Edge for TikTok scraping with profile-lock recovery."""
    from .config import CollectorSettings

    if not isinstance(settings, CollectorSettings):
        raise TypeError("settings must be CollectorSettings")

    sanitize_playwright_env()
    if running_in_cursor_sandbox() and not discover_system_browsers():
        raise RuntimeError(cursor_sandbox_hint())

    settings.user_data_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = settings.user_data_dir
    channel_errors: list[str] = []
    last_error: PlaywrightError | None = None

    profile_attempts: list[Path] = [profile_dir]
    session_dir = profile_dir.parent / "_session"
    profile_attempts.append(session_dir)

    def attempt_launch(
        *,
        user_data: Path,
        headless: bool,
        executable_path: Path | None = None,
        channel: str | None = None,
        label: str,
    ) -> Any | None:
        nonlocal last_error
        user_data.mkdir(parents=True, exist_ok=True)
        release_stale_profile_lock(user_data)
        try:
            return _try_persistent_context(
                playwright,
                user_data=str(user_data),
                headless=headless,
                locale=settings.locale,
                channel=channel,
                executable_path=executable_path,
            )
        except PlaywrightError as exc:
            last_error = exc
            mode = "headless" if headless else "headed"
            channel_errors.append(f"{label} ({mode}, profile={user_data.name}): {str(exc).splitlines()[0]}")
            if _launch_error_retryable(str(exc)):
                release_stale_profile_lock(user_data)
            return None

    # 1) System Chrome/Edge with persistent profile (main + session fallback)
    for name, exe in discover_system_browsers():
        for user_data in profile_attempts:
            for headless in _headless_modes(settings.headless):
                ctx = attempt_launch(
                    user_data=user_data,
                    headless=headless,
                    executable_path=exe,
                    label=f"{name}@{exe.name}",
                )
                if ctx is not None:
                    return ctx
        for headless in _headless_modes(settings.headless):
            try:
                return _try_ephemeral_context(
                    playwright,
                    headless=headless,
                    locale=settings.locale,
                    executable_path=exe,
                )
            except PlaywrightError as exc:
                last_error = exc
                mode = "headless" if headless else "headed"
                channel_errors.append(
                    f"{name}@{exe.name} ({mode}, ephemeral): {str(exc).splitlines()[0]}"
                )

    # 2) Playwright channel fallback
    channels = [c for c in settings.browser_channels if c is not None]
    if not should_skip_bundled_chromium() and None in settings.browser_channels:
        channels.append(None)

    for channel in channels:
        label = channel or "chromium"
        for user_data in profile_attempts:
            for headless in _headless_modes(settings.headless):
                ctx = attempt_launch(
                    user_data=user_data,
                    headless=headless,
                    channel=channel,
                    label=label,
                )
                if ctx is not None:
                    return ctx

    tried = "；".join(channel_errors[-6:]) if channel_errors else str(last_error)
    browsers = discover_system_browsers()
    if not browsers:
        hint = (
            "未在本机找到 Google Chrome 或 Microsoft Edge。"
            f"详情：{tried}。"
            "请先安装 Chrome/Edge，并用「启动页面.cmd」启动工作台。"
        )
    elif any("has been closed" in item.lower() for item in channel_errors):
        hint = (
            "浏览器启动后立即被关闭，通常是配置目录被占用。"
            f"详情：{tried}。"
            "请先关闭所有 Chrome/Edge 窗口，双击「启动页面.cmd」重启工作台后再采集；"
            "仍失败可删除 tiktok_collector\\data\\browser_profile 后重试。"
        )
    else:
        hint = (
            "无法启动本机浏览器。"
            f"详情：{tried}。"
            "请完全关闭工作台后，双击「启动页面.cmd」重新打开（勿用 Cursor 终端），再试采集。"
        )
    raise RuntimeError(hint) from last_error
