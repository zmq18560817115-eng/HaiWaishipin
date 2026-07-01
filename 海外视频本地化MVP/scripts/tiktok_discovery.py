"""TikTok 爆款候选发现层。

设计原则：
- 只采集公开 URL 与页面可见元数据，不批量下载视频。
- 不绕登录、验证码、地区限制；遇到限制就记录失败并停止该查询。
- 候选先进入 discovery_candidates.csv，人工或评分筛选后再进入 raw_links.csv。
"""

from __future__ import annotations

import csv
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx

from paths import DISCOVERY_CANDIDATES_CSV, DISCOVERY_QUERIES_CSV, RAW_LINKS_CSV


QUERY_FIELDS = [
    "query_id",
    "type",
    "value",
    "category",
    "subcategory",
    "region",
    "min_views",
    "max_days",
    "enabled",
    "notes",
]

CANDIDATE_FIELDS = [
    "candidate_id",
    "video_id",
    "url",
    "author",
    "title",
    "description",
    "duration_sec",
    "view_count",
    "like_count",
    "comment_count",
    "share_count",
    "hashtags",
    "thumbnail_url",
    "category",
    "subcategory",
    "source_query_id",
    "source_type",
    "source_value",
    "discover_provider",
    "fetch_provider",
    "score",
    "status",
    "discovered_at",
    "promoted_at",
    "error_message",
]

RAW_LINK_FIELDS = [
    "link_id",
    "url",
    "category",
    "platform",
    "subcategory",
    "source",
    "status",
    "notes",
    "added_at",
]

VIDEO_RE = re.compile(r"/@([^/?#]+)/video/(\d+)")
HASHTAG_RE = re.compile(r"#([\w\u4e00-\u9fff]+)")
LIMIT_TEXT_RE = re.compile(r"(captcha|verify|verification|login|log in|too many requests)", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def _append_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    existing = _read_csv(path)
    _write_csv(path, [*existing, *rows], fields)


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    match = VIDEO_RE.search(path)
    if not match:
        return url.strip()
    return f"https://www.tiktok.com/@{match.group(1)}/video/{match.group(2)}"


def video_id_from_url(url: str) -> str:
    match = VIDEO_RE.search(url)
    return match.group(2) if match else ""


def author_from_url(url: str) -> str:
    match = VIDEO_RE.search(url)
    return match.group(1) if match else ""


def _int(value: Any) -> int:
    try:
        return int(str(value or "").replace(",", "").strip())
    except ValueError:
        return 0


def _float(value: Any) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return 0.0


def _json_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    raw = str(value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed if str(x).strip()]
    except json.JSONDecodeError:
        pass
    return HASHTAG_RE.findall(raw)


def _score(row: dict[str, Any], query: dict[str, str]) -> float:
    views = _int(row.get("view_count"))
    likes = _int(row.get("like_count"))
    comments = _int(row.get("comment_count"))
    shares = _int(row.get("share_count"))
    score = math.log10(views + 1) * 20 if views else 0.0
    if views:
        score += min(likes / views, 0.2) * 120
        score += min(comments / views, 0.05) * 250
        score += min(shares / views, 0.08) * 220
    text = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("description") or ""),
            " ".join(_json_tags(row.get("hashtags"))),
        ]
    ).lower()
    q = str(query.get("value") or "").lower().replace("#", "")
    if q and q in text:
        score += 18
    for token in re.findall(r"[a-zA-Z0-9]{4,}", q):
        if token in text:
            score += 4
    min_views = _int(query.get("min_views"))
    if min_views and views and views < min_views:
        score -= 30
    return round(max(score, 0.0), 2)


def _query_url(query: dict[str, str]) -> str:
    qtype = (query.get("type") or "keyword").strip().lower()
    value = (query.get("value") or "").strip().lstrip("#@")
    if qtype == "hashtag":
        return f"https://www.tiktok.com/tag/{quote_plus(value)}"
    if qtype == "creator":
        return f"https://www.tiktok.com/@{quote_plus(value)}"
    return f"https://www.tiktok.com/search/video?q={quote_plus(value)}"


def _discover_urls_playwright(
    query: dict[str, str],
    *,
    limit: int,
    headless: bool = True,
    scrolls: int = 4,
    wait_ms: int = 1800,
) -> tuple[list[str], str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("未安装 Playwright，请先运行：pip install playwright && playwright install chromium") from exc

    url = _query_url(query)
    urls: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="en-US",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(wait_ms)
        for _ in range(max(scrolls, 1)):
            html = page.content()
            if LIMIT_TEXT_RE.search(html) and not urls:
                browser.close()
                return [], "页面要求登录/验证或触发限制，已停止该查询"
            hrefs = page.locator("a[href*='/video/']").evaluate_all("(els) => els.map(a => a.href)")
            for href in hrefs:
                normalized = normalize_url(str(href))
                if video_id_from_url(normalized) and normalized not in urls:
                    urls.append(normalized)
                    if len(urls) >= limit:
                        browser.close()
                        return urls, ""
            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(wait_ms)
        browser.close()
    return urls[:limit], ""


def _fetch_oembed(url: str, client: httpx.Client) -> dict[str, Any]:
    r = client.get("https://www.tiktok.com/oembed", params={"url": url}, timeout=20)
    r.raise_for_status()
    data = r.json()
    title = data.get("title") or ""
    tags = list(dict.fromkeys(HASHTAG_RE.findall(title)))
    return {
        "author": data.get("author_name") or author_from_url(url),
        "title": title,
        "description": title,
        "hashtags": json.dumps(tags, ensure_ascii=False),
        "thumbnail_url": data.get("thumbnail_url") or "",
        "fetch_provider": "oembed",
    }


def _fetch_metadata(url: str, engine: str, client: httpx.Client, pw_fetcher: Any | None) -> dict[str, Any]:
    if engine in ("playwright", "auto") and pw_fetcher is not None:
        try:
            data = pw_fetcher.fetch(url)
            data["fetch_provider"] = "playwright"
            return data
        except Exception:
            if engine == "playwright":
                raise
    if engine == "none":
        return {"fetch_provider": "none"}
    return _fetch_oembed(url, client)


def _dedupe_keys() -> set[str]:
    keys: set[str] = set()
    for path in (RAW_LINKS_CSV, DISCOVERY_CANDIDATES_CSV):
        for row in _read_csv(path):
            url = normalize_url(row.get("url", ""))
            vid = row.get("video_id") or video_id_from_url(url)
            if vid:
                keys.add(vid)
            if url:
                keys.add(url)
    return keys


def load_queries(product_id: str = "") -> list[dict[str, str]]:
    rows = _read_csv(DISCOVERY_QUERIES_CSV)
    enabled = [r for r in rows if str(r.get("enabled", "1")).strip() not in ("0", "false", "False", "no")]
    if not product_id:
        return enabled
    from app.material_scope import candidate_row_matches_product

    matched = [r for r in enabled if candidate_row_matches_product(r, product_id)]
    return matched


def discover_candidates(
    *,
    limit_per_query: int = 30,
    engine: str = "auto",
    headless: bool = True,
    sleep: float = 0.8,
    product_id: str = "",
) -> dict[str, Any]:
    queries = load_queries(product_id)
    if not queries:
        msg = f"没有启用的查询：{DISCOVERY_QUERIES_CSV}"
        if product_id:
            msg = f"当前产品「{product_id}」无匹配发现关键词，请在 discovery_queries.csv 配置同品类查询"
        return {"ok": False, "message": msg, "added": 0, "product_id": product_id}
    known = _dedupe_keys()
    existing = _read_csv(DISCOVERY_CANDIDATES_CSV)
    next_id = max([_int(r.get("candidate_id")) for r in existing] or [0]) + 1
    added: list[dict[str, Any]] = []
    errors: list[str] = []
    pw_fetcher = None
    if engine in ("playwright", "auto"):
        try:
            from tiktok_browser import PlaywrightFetcher

            pw_fetcher = PlaywrightFetcher(headless=headless)
        except Exception as exc:  # noqa: BLE001
            if engine == "playwright":
                raise
            errors.append(f"Playwright 元数据补全不可用，已降级 oEmbed：{exc}")
            engine = "oembed"
    try:
        with httpx.Client(headers={"User-Agent": "OverseasVideoLocMVP/1.0"}) as client:
            for query in queries:
                urls, message = _discover_urls_playwright(query, limit=limit_per_query, headless=headless)
                if message:
                    errors.append(f"{query.get('query_id')} {query.get('value')}: {message}")
                for url in urls:
                    vid = video_id_from_url(url)
                    if not vid or vid in known or url in known:
                        continue
                    row: dict[str, Any] = {
                        "candidate_id": next_id,
                        "video_id": vid,
                        "url": url,
                        "author": author_from_url(url),
                        "category": query.get("category") or "tiktok",
                        "subcategory": query.get("subcategory") or "",
                        "source_query_id": query.get("query_id") or "",
                        "source_type": query.get("type") or "",
                        "source_value": query.get("value") or "",
                        "discover_provider": "playwright_public_page",
                        "status": "candidate",
                        "discovered_at": utc_now(),
                    }
                    try:
                        meta = _fetch_metadata(url, engine, client, pw_fetcher)
                        row.update(meta)
                    except Exception as exc:  # noqa: BLE001
                        row["error_message"] = str(exc)[:500]
                        row["fetch_provider"] = "failed"
                    row["score"] = _score(row, query)
                    added.append(row)
                    known.add(vid)
                    known.add(url)
                    next_id += 1
                    if sleep:
                        time.sleep(sleep)
    finally:
        if pw_fetcher is not None:
            pw_fetcher.close()
    if added:
        _append_csv(DISCOVERY_CANDIDATES_CSV, added, CANDIDATE_FIELDS)
    return {
        "ok": True,
        "queries": len(queries),
        "added": len(added),
        "candidate_file": str(DISCOVERY_CANDIDATES_CSV),
        "errors": errors,
        "product_id": product_id,
    }


def promote_candidates(*, limit: int = 20, min_score: float = 0.0, product_id: str = "") -> dict[str, Any]:
    all_candidates = _read_csv(DISCOVERY_CANDIDATES_CSV)
    if not all_candidates:
        return {"ok": False, "message": "候选池为空", "promoted": 0}
    pool = all_candidates
    if product_id:
        from app.material_scope import candidate_row_matches_product

        pool = [r for r in all_candidates if candidate_row_matches_product(r, product_id)]
        if not pool:
            return {
                "ok": False,
                "message": f"候选池无与「{product_id}」同品类条目",
                "promoted": 0,
                "product_id": product_id,
            }
    raw_rows = _read_csv(RAW_LINKS_CSV)
    known: set[str] = set()
    for row in raw_rows:
        url = normalize_url(row.get("url", ""))
        vid = row.get("video_id") or video_id_from_url(url)
        if vid:
            known.add(vid)
        if url:
            known.add(url)
    next_link_id = max([_int(r.get("link_id")) for r in raw_rows] or [0]) + 1
    eligible = [
        row
        for row in pool
        if row.get("status", "candidate") in ("candidate", "selected")
        and _float(row.get("score")) >= min_score
        and (row.get("video_id") or video_id_from_url(row.get("url", ""))) not in known
    ]
    eligible.sort(key=lambda r: _float(r.get("score")), reverse=True)
    promoted_rows: list[dict[str, Any]] = []
    promoted_ids: set[str] = set()
    for row in eligible[:limit]:
        url = normalize_url(row.get("url", ""))
        vid = row.get("video_id") or video_id_from_url(url)
        if not url or vid in known or url in known:
            continue
        promoted_rows.append(
            {
                "link_id": next_link_id,
                "url": url,
                "category": row.get("category") or "tiktok",
                "platform": "tiktok",
                "subcategory": row.get("subcategory") or "",
                "source": "discovery",
                "status": "pending",
                "notes": f"{row.get('source_type')}:{row.get('source_value')} score={row.get('score')}",
                "added_at": today(),
            }
        )
        next_link_id += 1
        known.add(vid)
        known.add(url)
        promoted_ids.add(str(row.get("candidate_id")))
    if promoted_rows:
        _append_csv(RAW_LINKS_CSV, promoted_rows, RAW_LINK_FIELDS)
        now = utc_now()
        for row in all_candidates:
            if str(row.get("candidate_id")) in promoted_ids:
                row["status"] = "promoted"
                row["promoted_at"] = now
        _write_csv(DISCOVERY_CANDIDATES_CSV, all_candidates, CANDIDATE_FIELDS)
    return {
        "ok": True,
        "promoted": len(promoted_rows),
        "raw_links": str(RAW_LINKS_CSV),
        "product_id": product_id,
        "next_step": "运行 fetch --engine auto，再运行 decompose --provider doubao",
    }
