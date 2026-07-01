from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from playwright._impl._errors import Error as PlaywrightError
from playwright.sync_api import BrowserContext, Page, sync_playwright

from .browser_launch import (
    collector_runtime_status,
    cursor_sandbox_hint,
    discover_system_browsers,
    running_in_cursor_sandbox,
    sanitize_playwright_env,
    should_skip_bundled_chromium,
)
from .config import CollectorSettings
from .models import TikTokVideoRecord


VIDEO_URL_RE = re.compile(r"https://www\.tiktok\.com/@[^/]+/video/\d+")
LIMIT_TEXT_RE = re.compile(
    r"(captcha|verification required|security check|too many requests|rate limit|maximum number of attempts)",
    re.I,
)
ERROR_TEXT_RE = re.compile(r"(something went wrong|try again|server, please try again)", re.I)
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
VIDEOS_TAB_PATTERN = re.compile(r"^(videos|video|视频)$", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_video_url(url: str) -> str:
    match = VIDEO_URL_RE.search(url or "")
    return match.group(0) if match else (url or "").strip()


def epoch_to_iso(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return None


def _decode_json_blob(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    candidates = [text]
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace >= 0 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])
    decoder = json.JSONDecoder()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            for index, char in enumerate(candidate):
                if char != "{":
                    continue
                try:
                    parsed, _ = decoder.raw_decode(candidate[index:])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
    return None


def _walk_for_item_struct(node: Any) -> dict[str, Any] | None:
    if isinstance(node, dict):
        if isinstance(node.get("itemStruct"), dict):
            return node["itemStruct"]
        if {"id", "desc", "stats"}.issubset(node.keys()):
            return node
        item_module = node.get("ItemModule")
        if isinstance(item_module, dict) and item_module:
            first = next(iter(item_module.values()))
            if isinstance(first, dict):
                return first
        for value in node.values():
            found = _walk_for_item_struct(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _walk_for_item_struct(value)
            if found:
                return found
    return None


def _extract_script_payload(page: Page) -> dict[str, Any] | None:
    expression = """() => {
        const selectors = [
          "script#__UNIVERSAL_DATA_FOR_REHYDRATION__",
          "script#SIGI_STATE",
          "script[data-testid='main-context']",
        ];
        for (const selector of selectors) {
          const el = document.querySelector(selector);
          if (el && el.textContent) return el.textContent;
        }
        const fallback = Array.from(document.scripts).find(
          (el) => el.textContent && (
            el.textContent.includes("itemStruct") ||
            el.textContent.includes("ItemModule") ||
            el.textContent.includes("webapp.video-detail")
          )
        );
        return fallback ? fallback.textContent : "";
    }"""
    for _ in range(3):
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            script_text = page.evaluate(expression)
            return _decode_json_blob(script_text)
        except PlaywrightError as exc:
            if "Execution context was destroyed" not in str(exc):
                raise
            page.wait_for_timeout(1200)
    return None


def _search_result_urls(page: Page) -> list[str]:
    hrefs = page.locator("a[href*='/video/']").evaluate_all("(els) => els.map((el) => el.href)")
    unique: list[str] = []
    for href in hrefs:
        url = normalize_video_url(str(href))
        if VIDEO_URL_RE.fullmatch(url) and url not in unique:
            unique.append(url)
    return unique


def _has_visible_results(page: Page) -> bool:
    try:
        if _search_result_urls(page):
            return True
    except PlaywrightError:
        return False
    selectors = [
        "a[href*='/video/']",
        "[data-e2e='search_top-item']",
        "[data-e2e='search-card-item']",
        "div[data-e2e='search-video-item']",
    ]
    for selector in selectors:
        try:
            if page.locator(selector).count() > 0:
                return True
        except PlaywrightError:
            continue
    return False


def _is_challenge_page(page: Page, content: str) -> bool:
    if _has_visible_results(page):
        return False
    return bool(LIMIT_TEXT_RE.search(content))


def _search_input_selectors() -> list[str]:
    return [
        "input[data-e2e='search-user-input']",
        "input[placeholder*='Search']",
        "input[placeholder*='搜索']",
        "input[type='search']",
    ]


def _make_record(item: dict[str, Any], video_url: str, keyword: str) -> TikTokVideoRecord:
    author = item.get("author") or {}
    stats = item.get("stats") or {}
    text_extra = item.get("textExtra") or []
    music = item.get("music") or {}
    video = item.get("video") or {}
    hashtags = [
        str(entry.get("hashtagName") or entry.get("hashtag_name") or "").strip()
        for entry in text_extra
        if isinstance(entry, dict) and str(entry.get("hashtagName") or entry.get("hashtag_name") or "").strip()
    ]
    author_name = str(author.get("nickname") or author.get("uniqueId") or "").strip()
    author_unique_id = str(author.get("uniqueId") or "").strip()
    author_url = f"https://www.tiktok.com/@{author_unique_id}" if author_unique_id else ""
    return TikTokVideoRecord(
        video_url=video_url,
        video_id=str(item.get("id") or ""),
        caption=str(item.get("desc") or "").strip(),
        author_name=author_name,
        author_url=author_url,
        like_count=int(stats.get("diggCount") or 0),
        comment_count=int(stats.get("commentCount") or 0),
        share_count=int(stats.get("shareCount") or 0),
        collect_count=int(stats.get("collectCount") or 0),
        publish_time=epoch_to_iso(item.get("createTime")),
        hashtags=list(dict.fromkeys(hashtags)),
        music_title=str(music.get("title") or "").strip(),
        cover_url=str(video.get("cover") or video.get("originCover") or "").strip(),
        source_keyword=keyword,
        crawl_time=utc_now(),
    )


class TikTokScraper:
    def __init__(self, settings: CollectorSettings) -> None:
        self.settings = settings

    def collect_keyword(self, keyword: str, *, limit: int) -> list[TikTokVideoRecord]:
        keyword = keyword.strip()
        if not keyword:
            return []
        with sync_playwright() as playwright:
            context = self._launch_context(playwright)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                urls = self._collect_urls_for_keyword(page, keyword, limit)
                return self._collect_video_details(context, urls, keyword)
            finally:
                context.close()

    def _launch_context(self, playwright: Any) -> BrowserContext:
        sanitize_playwright_env()
        if running_in_cursor_sandbox() and not discover_system_browsers():
            raise RuntimeError(cursor_sandbox_hint())

        launch_options = {
            "headless": self.settings.headless,
            "locale": self.settings.locale,
            "viewport": {"width": 1440, "height": 1080},
            "user_agent": DEFAULT_USER_AGENT,
        }
        self.settings.user_data_dir.mkdir(parents=True, exist_ok=True)
        user_data = str(self.settings.user_data_dir)
        last_error: PlaywrightError | None = None
        channel_errors: list[str] = []

        def try_launch(
            *,
            channel: str | None = None,
            executable_path: Path | None = None,
            headless: bool | None = None,
        ) -> BrowserContext:
            opts = dict(launch_options)
            if headless is not None:
                opts["headless"] = headless
            if executable_path is not None:
                opts["executable_path"] = str(executable_path)
            elif channel:
                opts["channel"] = channel
            return playwright.chromium.launch_persistent_context(user_data, **opts)

        def retryable(message: str) -> bool:
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
                )
            )

        # 1) 直接指定本机 Chrome/Edge 可执行文件（最可靠）
        for name, exe in discover_system_browsers():
            for use_headless in (False, True) if self.settings.headless else (False,):
                try:
                    return try_launch(executable_path=exe, headless=use_headless)
                except PlaywrightError as exc:
                    last_error = exc
                    mode = "headless" if use_headless else "headed"
                    channel_errors.append(f"{name}@{exe.name} ({mode}): {str(exc).splitlines()[0]}")
                    if use_headless is False and retryable(str(exc)):
                        break
                    if use_headless and retryable(str(exc)):
                        continue
                    break

        # 2) Playwright channel 回退
        channels = [c for c in self.settings.browser_channels if c is not None]
        if not should_skip_bundled_chromium() and None in self.settings.browser_channels:
            channels.append(None)

        for channel in channels:
            headless_modes = [self.settings.headless]
            if self.settings.headless:
                headless_modes.append(False)
            for use_headless in headless_modes:
                label = channel or "chromium"
                mode = "headless" if use_headless else "headed"
                try:
                    return try_launch(channel=channel, headless=use_headless)
                except PlaywrightError as exc:
                    last_error = exc
                    message = str(exc)
                    channel_errors.append(f"{label} ({mode}): {message.splitlines()[0]}")
                    if use_headless and retryable(message):
                        continue
                    break

        tried = "；".join(channel_errors[-4:]) if channel_errors else str(last_error)
        browsers = discover_system_browsers()
        if not browsers:
            hint = (
                "未在本机找到 Google Chrome 或 Microsoft Edge。"
                f"详情：{tried}。"
                "请先安装 Chrome/Edge，并用「启动页面.cmd」启动工作台。"
            )
        else:
            hint = (
                "无法启动本机浏览器。"
                f"详情：{tried}。"
                "请完全关闭工作台后，双击「启动页面.cmd」重新打开（勿用 Cursor 终端），再试采集。"
            )
        raise RuntimeError(hint) from last_error

    def _collect_urls_for_keyword(self, page: Page, keyword: str, limit: int) -> list[str]:
        query_url = f"https://www.tiktok.com/search/video?q={quote_plus(keyword)}"
        self._goto_with_retry(page, query_url)
        page.wait_for_timeout(self.settings.search_wait_ms)
        self._ensure_search_results_page(page, keyword, query_url)
        urls: list[str] = []
        scroll_rounds = max(self.settings.search_scrolls, (limit + 9) // 10)
        for _ in range(scroll_rounds):
            for url in _search_result_urls(page):
                if url not in urls:
                    urls.append(url)
                    if len(urls) >= limit:
                        return urls
            if urls:
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(self.settings.search_wait_ms)
                continue
            content = page.content()
            if ERROR_TEXT_RE.search(content):
                self._recover_from_error_page(page, query_url, keyword)
                content = page.content()
                for url in _search_result_urls(page):
                    if url not in urls:
                        urls.append(url)
                        if len(urls) >= limit:
                            return urls
                if urls:
                    page.mouse.wheel(0, 1800)
                    page.wait_for_timeout(self.settings.search_wait_ms)
                    continue
            if _is_challenge_page(page, content):
                if self._wait_for_manual_verification(page, keyword):
                    if not _has_visible_results(page):
                        self._goto_with_retry(page, query_url)
                        page.wait_for_timeout(self.settings.search_wait_ms)
                        self._ensure_search_results_page(page, keyword, query_url)
                    for url in _search_result_urls(page):
                        if url not in urls:
                            urls.append(url)
                            if len(urls) >= limit:
                                return urls
                    if urls:
                        page.mouse.wheel(0, 1800)
                        page.wait_for_timeout(self.settings.search_wait_ms)
                        continue
                    content = page.content()
                if _is_challenge_page(page, content):
                    raise RuntimeError(
                        "TikTok search page requested login/captcha or rate-limited the session"
                    )
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(self.settings.search_wait_ms)
        return urls[:limit]

    def _wait_for_manual_verification(self, page: Page, keyword: str) -> bool:
        if self.settings.headless:
            return False
        print(
            "TikTok triggered verification or login for keyword "
            f"'{keyword}'. Complete it in the opened browser window within "
            f"{self.settings.manual_verify_wait_ms // 1000} seconds, then wait for auto resume."
        )
        elapsed_ms = 0
        step_ms = 1500
        while elapsed_ms < self.settings.manual_verify_wait_ms:
            page.wait_for_timeout(step_ms)
            elapsed_ms += step_ms
            try:
                if _has_visible_results(page):
                    return True
            except PlaywrightError:
                return False
        return True

    def _recover_from_error_page(self, page: Page, query_url: str, keyword: str) -> None:
        for attempt in range(self.settings.error_retry_count + 1):
            try:
                retry_button = page.get_by_role("button", name=re.compile("try again", re.I))
                if retry_button.count():
                    retry_button.first.click(timeout=3000)
                else:
                    self._goto_with_retry(page, query_url)
            except PlaywrightError:
                self._goto_with_retry(page, query_url)
            page.wait_for_timeout(self.settings.search_wait_ms)
            if not ERROR_TEXT_RE.search(page.content()):
                return
        if self._wait_for_manual_verification(page, keyword):
            self._goto_with_retry(page, query_url)
            page.wait_for_timeout(self.settings.search_wait_ms)

    def _collect_video_details(
        self,
        context: BrowserContext,
        urls: list[str],
        keyword: str,
    ) -> list[TikTokVideoRecord]:
        records: list[TikTokVideoRecord] = []
        page = context.new_page()
        try:
            for url in urls:
                self._goto_with_retry(page, url)
                page.wait_for_timeout(self.settings.video_wait_ms)
                payload = _extract_script_payload(page)
                item = _walk_for_item_struct(payload) if payload else None
                if not item:
                    continue
                records.append(_make_record(item, url, keyword))
        finally:
            page.close()
        return records

    def _goto_with_retry(self, page: Page, url: str) -> None:
        for attempt in range(self.settings.error_retry_count + 2):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                return
            except PlaywrightError as exc:
                message = str(exc)
                if "ERR_NETWORK_CHANGED" not in message or attempt >= self.settings.error_retry_count + 1:
                    raise
                page.wait_for_timeout(1500)

    def _ensure_search_results_page(self, page: Page, keyword: str, query_url: str) -> None:
        current_url = page.url.lower()
        if "/search/" in current_url and _has_visible_results(page):
            return
        if "/search/" in current_url and "/video" in current_url:
            page.wait_for_timeout(self.settings.search_wait_ms)
            if _has_visible_results(page):
                return

        self._goto_with_retry(page, "https://www.tiktok.com/")
        page.wait_for_timeout(self.settings.search_wait_ms)

        search_input = None
        for selector in _search_input_selectors():
            locator = page.locator(selector)
            if locator.count() > 0:
                search_input = locator.first
                break
        if search_input is None:
            self._goto_with_retry(page, query_url)
            page.wait_for_timeout(self.settings.search_wait_ms)
            return

        try:
            search_input.click(timeout=5000)
            search_input.fill(keyword, timeout=5000)
            search_input.press("Enter", timeout=5000)
            page.wait_for_timeout(self.settings.search_wait_ms)
        except PlaywrightError:
            self._goto_with_retry(page, query_url)
            page.wait_for_timeout(self.settings.search_wait_ms)
            return

        try:
            videos_tab = page.get_by_role("link", name=VIDEOS_TAB_PATTERN)
            if videos_tab.count():
                videos_tab.first.click(timeout=5000)
                page.wait_for_timeout(self.settings.search_wait_ms)
            else:
                videos_button = page.get_by_role("button", name=VIDEOS_TAB_PATTERN)
                if videos_button.count():
                    videos_button.first.click(timeout=5000)
                    page.wait_for_timeout(self.settings.search_wait_ms)
        except PlaywrightError:
            pass
