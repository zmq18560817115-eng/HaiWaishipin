"""TikTok 页面浏览器抓取（Playwright）— 补全 oEmbed 拿不到的播放量等字段。"""

from __future__ import annotations

import json
import re
from typing import Any

HASHTAG_RE = re.compile(r"#([\w\u4e00-\u9fff]+)")
VIDEO_ID_RE = re.compile(r"/video/(\d+)")

_USER_AGENT_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def _to_mobile_url(url: str) -> str:
    match = VIDEO_ID_RE.search(url)
    if not match:
        raise ValueError(f"无法从链接解析 video_id: {url}")
    return f"https://m.tiktok.com/v/{match.group(1)}.html"


def _merge_custom_tdk(payload: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    tdk = payload.get("itemCustomTDK") or {}
    if tdk.get("title") and not item.get("desc"):
        item["desc"] = tdk["title"]
    if tdk.get("desc"):
        extra = str(tdk["desc"]).strip()
        desc = str(item.get("desc") or "").strip()
        if extra and extra not in desc:
            item["desc"] = f"{desc}\n{extra}".strip() if desc else extra
    return item


def _find_item_struct(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        if "itemStruct" in obj and isinstance(obj["itemStruct"], dict):
            return obj["itemStruct"]
        if {"desc", "author", "stats"}.issubset(obj.keys()):
            return obj
        for value in obj.values():
            found = _find_item_struct(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_item_struct(value)
            if found:
                return found
    return None


def _extract_json_blobs(html: str) -> list[dict[str, Any]]:
    blobs: list[dict[str, Any]] = []
    patterns = (
        r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.DOTALL | re.IGNORECASE):
            try:
                blobs.append(json.loads(match.group(1)))
            except json.JSONDecodeError:
                continue
    return blobs


def _item_to_payload(item: dict[str, Any], url: str) -> dict[str, Any]:
    author = item.get("author") or {}
    stats = item.get("stats") or {}
    video = item.get("video") or {}
    title = str(item.get("desc") or item.get("title") or "").strip()
    tags = list(dict.fromkeys(HASHTAG_RE.findall(title)))
    duration = video.get("duration")
    if duration is not None:
        try:
            duration = int(duration)
        except (TypeError, ValueError):
            duration = None
    cover = video.get("cover") or video.get("originCover") or video.get("dynamicCover")
    return {
        "title": title,
        "description": title,
        "author": author.get("uniqueId") or author.get("nickname") or "",
        "author_url": (
            f"https://www.tiktok.com/@{author['uniqueId']}"
            if author.get("uniqueId")
            else None
        ),
        "thumbnail_url": cover,
        "duration_sec": duration,
        "view_count": stats.get("playCount"),
        "like_count": stats.get("diggCount"),
        "comment_count": stats.get("commentCount"),
        "share_count": stats.get("shareCount"),
        "hashtags": json.dumps(tags, ensure_ascii=False),
        "fetch_provider": "playwright",
        "source_url": url,
    }


def _parse_page_html(html: str, url: str) -> dict[str, Any]:
    for blob in _extract_json_blobs(html):
        item = _find_item_struct(blob)
        if item:
            return _item_to_payload(item, url)
    raise RuntimeError("页面内未找到视频 JSON")


def _launch_chromium(playwright: Any, *, headless: bool = True) -> Any:
    last_error: Exception | None = None
    for channel in (None, "chrome", "msedge"):
        try:
            if channel:
                return playwright.chromium.launch(headless=headless, channel=channel)
            return playwright.chromium.launch(headless=headless)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(
        "无法启动 Chromium。请运行：playwright install chromium"
    ) from last_error


class PlaywrightFetcher:
    """复用同一浏览器会话批量抓取（移动版页面含 SSR 数据）。"""

    def __init__(self, *, headless: bool = True, timeout_ms: int = 60000) -> None:
        if not playwright_available():
            raise RuntimeError(
                "未安装 Playwright。请运行：pip install playwright && playwright install chromium"
            )
        from playwright.sync_api import sync_playwright

        self._playwright_cm = sync_playwright()
        self._playwright = self._playwright_cm.__enter__()
        self._browser = _launch_chromium(self._playwright, headless=headless)
        self._context = self._browser.new_context(
            user_agent=_USER_AGENT_MOBILE,
            locale="en-US",
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        self._page = self._context.new_page()
        self._timeout_ms = timeout_ms
        self._custom_tdk: dict[str, Any] | None = None
        self._page.on("response", self._on_response)

    def _on_response(self, response: Any) -> None:
        if "/api/customtdk/item" not in response.url:
            return
        try:
            if "application/json" in (response.headers.get("content-type") or ""):
                self._custom_tdk = response.json()
        except Exception:  # noqa: BLE001
            return

    def fetch(self, url: str) -> dict[str, Any]:
        mobile_url = _to_mobile_url(url)
        self._custom_tdk = None
        self._page.goto(mobile_url, wait_until="networkidle", timeout=self._timeout_ms)
        self._page.wait_for_timeout(1500)
        html = self._page.content()
        payload = _parse_page_html(html, url)
        if self._custom_tdk:
            item = _find_item_struct(self._custom_tdk) or {"desc": "", "author": {}, "stats": {}, "video": {}}
            item = _merge_custom_tdk(self._custom_tdk, item)
            merged = _item_to_payload(item, url)
            for key in ("title", "description", "hashtags"):
                if merged.get(key):
                    payload[key] = merged[key]
        return payload

    def close(self) -> None:
        self._browser.close()
        self._playwright_cm.__exit__(None, None, None)

    def __enter__(self) -> PlaywrightFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def fetch_with_playwright(url: str, *, headless: bool = True, timeout_ms: int = 60000) -> dict[str, Any]:
    """单条抓取（测试用）；批量请用 PlaywrightFetcher。"""
    with PlaywrightFetcher(headless=headless, timeout_ms=timeout_ms) as fetcher:
        return fetcher.fetch(url)
