"""TikTok 竞品采集流水线 — 唯一入口。

用法:
  python scripts/pipeline.py links          # 生成 raw_links.csv
  python scripts/pipeline.py fetch          # 默认 oEmbed（快）
  python scripts/pipeline.py fetch --engine auto        # Playwright 优先，失败回退 oEmbed
  python scripts/pipeline.py fetch --engine playwright  # 仅浏览器，含播放量/时长
  python scripts/pipeline.py db             # 导入 MySQL（需本机数据库可用）
  python scripts/pipeline.py decompose      # 结构拆解（规则）→ video_analysis
  python scripts/pipeline.py templates      # 归纳爆款结构 → script_templates
  python scripts/pipeline.py products       # DS223 → product_materials
  python scripts/pipeline.py knowledge      # KRO 知识库检索
  python scripts/pipeline.py bridge --id 19 # 对接到 MVP
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pymysql
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from paths import (
    DECOMPOSE_DIR,
    MVP_ROOT,
    OVERSEAS_RUNS_DIR,
    PRODUCT_MATERIALS_CSV,
    RAW_LINKS_CSV,
    SCHEMA_SQL,
    SCRIPT_TEMPLATES_CSV,
    SCRIPT_TEMPLATES_DIR,
    VIDEO_ANALYSIS_CSV,
    VIDEOS_META_CSV,
    db_config,
    kro_config_path,
    kro_script_path,
)
from seed_links import seed_rows

if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))

VIDEO_ID_RE = re.compile(r"/video/(\d+)")
AUTHOR_RE = re.compile(r"@([^/]+)")
HASHTAG_RE = re.compile(r"#([\w\u4e00-\u9fff]+)")

DEFAULT_CLAIMS = [
    "portable design for travel",
    "heats milk to comfortable temperature",
    "rechargeable battery for on-the-go use",
    "fits in diaper bag or cup holder",
    "USB-C charging",
    "even heating in minutes",
]

DEFAULT_SKU = "便携恒温杯"

META_FIELDS = [
    "link_id", "url", "video_id", "author", "author_url", "title", "description",
    "duration_sec", "view_count", "like_count", "comment_count", "share_count",
    "hashtags", "thumbnail_url", "fetched_at", "fetch_status", "fetch_provider", "error_message",
]

ANALYSIS_FIELDS = [
    "link_id", "url", "video_id", "author",
    "hook_3s", "pain_points", "selling_points", "scenes",
    "video_structure", "subtitle_layout", "cta", "reusable_template",
    "analyzed_at", "analyze_status", "analyze_provider", "error_message",
]

TEMPLATE_FIELDS = [
    "template_id", "label", "structure_chain", "video_count",
    "sample_link_ids", "suitable_for", "notes", "updated_at",
]

# 爆款结构模板库（从多条 video_analysis 归纳）
TEMPLATE_CATALOG: list[dict[str, Any]] = [
    {
        "template_id": "product-seed",
        "label": "产品种草型",
        "structure_chain": "痛点开场 → 产品出现 → 使用演示 → 效果对比 → 购买引导",
        "suitable_for": "便携暖奶器测评、外出加热、旅行种草",
        "keywords": [
            "momcozy", "babybrezza", "bololo", "babysbrew",
            "bottlewarmer", "portablebottlewarmer", "milkwarmer",
            "travel", "warmer", "heater",
        ],
    },
    {
        "template_id": "tutorial-hack",
        "label": "教程技巧型",
        "structure_chain": "痛点反问 → 踩坑演示 → 步骤拆解 → 效果验证 → 收藏引导",
        "suitable_for": "组装、设置、清洁、穿戴技巧",
        "keywords": [
            "how to", "hack", "tips", "assembly", "settings", "clean",
            "flange", "hands free", "nursing bra", "pumpinghack", "howtopump",
        ],
    },
    {
        "template_id": "education",
        "label": "知识科普型",
        "structure_chain": "钩子提问 → 痛点放大 → 知识讲解 → 案例证明 → 关注引导",
        "suitable_for": "哺乳指导、IBCLC、误区纠正",
        "keywords": [
            "ibclc", "lactation", "breastfeeding", "lowmilksupply", "flangesize",
            "exclusive pumping", "postpartum", "newborn",
        ],
    },
    {
        "template_id": "comparison",
        "label": "对比选购型",
        "structure_chain": "悬念开场 → 双品对比 → 优缺点 → 适用人群 → 评论互动",
        "suitable_for": "Wearable vs 台式、品牌横评",
        "keywords": ["vs", "comparison", "compare", "which", "better", "360", "s1", "s2"],
    },
    {
        "template_id": "mom-life",
        "label": "妈妈生活型",
        "structure_chain": "真实场景 → 情绪共鸣 → 解决方案 → 使用反馈 → 软性CTA",
        "suitable_for": "背奶日常、职场妈妈、产后生活",
        "keywords": ["momlife", "momtok", "postpartum", "working mom", "pumpingmom", "newmom"],
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"))


# ── links ──────────────────────────────────────────────────────────────────

def cmd_links() -> int:
    rows = seed_rows()
    RAW_LINKS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with RAW_LINKS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    safe_print(f"OK {RAW_LINKS_CSV} ({len(rows)} links)")
    return 0


# ── fetch ──────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _parse_video_id(url: str) -> str | None:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _parse_author(url: str) -> str | None:
    m = AUTHOR_RE.search(url)
    return m.group(1) if m else None


def _fetch_oembed(url: str, client: httpx.Client) -> dict[str, Any]:
    r = client.get("https://www.tiktok.com/oembed", params={"url": url}, timeout=20)
    r.raise_for_status()
    return r.json()


def _fetch_one(
    url: str,
    client: httpx.Client,
    engine: str,
    pw: Any | None = None,
) -> tuple[dict[str, Any], str]:
    """返回 (字段更新, fetch_provider)。"""
    if engine in ("playwright", "auto") and pw is not None:
        try:
            data = pw.fetch(url)
            return data, "playwright"
        except Exception:
            if engine == "playwright":
                raise
    data = _fetch_oembed(url, client)
    title = data.get("title") or ""
    tags = list(dict.fromkeys(HASHTAG_RE.findall(title)))
    return {
        "title": title,
        "description": title,
        "author": data.get("author_name"),
        "author_url": data.get("author_url"),
        "thumbnail_url": data.get("thumbnail_url"),
        "hashtags": json.dumps(tags, ensure_ascii=False),
        "fetch_provider": "oembed",
    }, "oembed"


def cmd_fetch(sleep: float = 0.4, engine: str = "oembed", product_id: str = "") -> int:
    from app.material_scope import active_product_id, link_row_matches_product, trim_material_library_to_product

    product_id = (product_id or active_product_id()).strip()
    if not RAW_LINKS_CSV.exists():
        cmd_links()
    links = _read_csv(RAW_LINKS_CSV)
    if product_id:
        before = len(links)
        links = [link for link in links if link_row_matches_product(link, product_id)]
        safe_print(f"品类过滤「{product_id}」: {before} → {len(links)} 条待抓取")
    if not links:
        safe_print("无同品类链接可抓取")
        return 1

    existing_meta = {str(r.get("link_id")): r for r in _read_csv(VIDEOS_META_CSV) if r.get("link_id")}
    rows: list[dict[str, Any]] = []
    ok = 0
    pw_ctx = None
    if engine in ("playwright", "auto"):
        from tiktok_browser import PlaywrightFetcher

        pw_ctx = PlaywrightFetcher()
    try:
        with httpx.Client(headers={"User-Agent": "OverseasVideoLocMVP/1.0"}) as client:
            for i, link in enumerate(links, 1):
                url = link["url"].strip()
                row: dict[str, Any] = {
                    "link_id": link["link_id"], "url": url,
                    "video_id": _parse_video_id(url), "author": _parse_author(url),
                    "author_url": None, "title": None, "description": None,
                    "duration_sec": None, "view_count": None, "like_count": None,
                    "comment_count": None, "share_count": None, "hashtags": "",
                    "thumbnail_url": None, "fetched_at": None,
                    "fetch_status": "failed", "fetch_provider": None, "error_message": None,
                }
                try:
                    payload, provider = _fetch_one(url, client, engine, pw_ctx)
                    row.update(payload)
                    row["fetch_status"] = "ok"
                    row["fetch_provider"] = provider
                    row["fetched_at"] = utc_now()
                    ok += 1
                    try:
                        from app.thumbnails import ensure_thumbnail_cached

                        ensure_thumbnail_cached(row["link_id"], force=True)
                    except Exception:
                        pass
                except Exception as exc:  # noqa: BLE001
                    row["error_message"] = str(exc)
                existing_meta[str(row["link_id"])] = row
                rows.append(row)
                safe_print(f"[{i}/{len(links)}] id={row['link_id']} {row['fetch_status']} ({row.get('fetch_provider') or '-'})")
                if i < len(links):
                    time.sleep(sleep)
    finally:
        if pw_ctx is not None:
            pw_ctx.close()
    VIDEOS_META_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged = list(existing_meta.values())
    merged.sort(key=lambda r: int(r.get("link_id") or 0))
    with VIDEOS_META_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        w.writeheader()
        for row in merged:
            w.writerow({k: row.get(k, "") for k in META_FIELDS})
    ok = sum(1 for r in rows if r.get("fetch_status") == "ok")
    safe_print(f"OK {VIDEOS_META_CSV} ({ok}/{len(rows)} fetched, total {len(merged)} in library)")
    if product_id:
        trim = trim_material_library_to_product(product_id)
        safe_print(f"品类收窄：保留 {trim.get('kept', 0)} 条，移除 {trim.get('removed', 0)} 条")
    return 0


def cmd_cache_thumbnails(*, force: bool = False) -> int:
    """将 TikTok 封面下载到本地 01_素材库/竞品对标/封面缓存。"""
    from app.thumbnails import cache_all_thumbnails

    result = cache_all_thumbnails(force=force)
    safe_print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("cached", 0) else 1


# ── discover ───────────────────────────────────────────────────────────────

def cmd_discover(limit_per_query: int = 30, engine: str = "auto", product_id: str = "") -> int:
    """低频发现公开候选 URL → discovery_candidates.csv。"""
    from app.material_scope import active_product_id
    from tiktok_discovery import discover_candidates

    product_id = (product_id or active_product_id()).strip()
    result = discover_candidates(limit_per_query=limit_per_query, engine=engine, product_id=product_id)
    safe_print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def cmd_promote(limit: int = 20, min_score: float = 0.0, product_id: str = "") -> int:
    """候选池评分筛选 → raw_links.csv。"""
    from app.material_scope import active_product_id, trim_material_library_to_product
    from tiktok_discovery import promote_candidates

    product_id = (product_id or active_product_id()).strip()
    result = promote_candidates(limit=limit, min_score=min_score, product_id=product_id)
    safe_print(json.dumps(result, ensure_ascii=False, indent=2))
    if product_id and result.get("ok"):
        trim = trim_material_library_to_product(product_id)
        safe_print(f"品类收窄：保留 {trim.get('kept', 0)} 条，移除 {trim.get('removed', 0)} 条")
    return 0 if result.get("ok") else 1


# ── db ─────────────────────────────────────────────────────────────────────

def _db_connect():
    cfg = db_config()
    if not cfg["password"]:
        safe_print("缺少 OVERSEAS_DB_PASSWORD。请先运行根目录「检查开发环境.cmd」。")
        sys.exit(1)
    return pymysql.connect(
        host=cfg["host"], port=int(cfg["port"]),
        user=cfg["user"], password=cfg["password"],
        database=cfg["database"], charset="utf8mb4",
    )


def _nullable(value: str | None) -> Any:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _nullable_int(value: str | None) -> int | None:
    s = _nullable(value)
    return int(s) if s else None


def _upsert_db(conn, raw_rows: list[dict], meta_rows: list[dict]) -> None:
    with conn.cursor() as cur:
        for row in raw_rows:
            cur.execute(
                """INSERT INTO raw_links (link_id,url,category,platform,subcategory,source,status,notes,added_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE category=VALUES(category), status=VALUES(status)""",
                (
                    int(row["link_id"]), row["url"].strip(), row.get("category", "breast_pump"),
                    row.get("platform", "tiktok"), _nullable(row.get("subcategory")),
                    row.get("source", "manual"), row.get("status", "pending"),
                    _nullable(row.get("notes")), _nullable(row.get("added_at")),
                ),
            )
        for row in meta_rows:
            tags = _nullable(row.get("hashtags"))
            cur.execute(
                """INSERT INTO videos_meta (
                     link_id,url,video_id,author,title,description,hashtags,thumbnail_url,
                     fetched_at,fetch_status,fetch_provider,error_message)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE title=VALUES(title), fetch_status=VALUES(fetch_status)""",
                (
                    int(row["link_id"]), row["url"].strip(), _nullable(row.get("video_id")),
                    _nullable(row.get("author")), _nullable(row.get("title")),
                    _nullable(row.get("description")), tags, _nullable(row.get("thumbnail_url")),
                    _nullable(row.get("fetched_at")), row.get("fetch_status", "pending"),
                    _nullable(row.get("fetch_provider")), _nullable(row.get("error_message")),
                ),
            )
        if VIDEO_ANALYSIS_CSV.exists():
            for row in _read_csv(VIDEO_ANALYSIS_CSV):
                if row.get("analyze_status") != "ok":
                    continue
                cur.execute(
                    """INSERT INTO video_analysis (
                         link_id,url,video_id,author,hook_3s,pain_points,selling_points,scenes,
                         video_structure,subtitle_layout,cta,reusable_template,
                         analyzed_at,analyze_status,analyze_provider,error_message)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                         hook_3s=VALUES(hook_3s), pain_points=VALUES(pain_points),
                         selling_points=VALUES(selling_points), scenes=VALUES(scenes),
                         video_structure=VALUES(video_structure), subtitle_layout=VALUES(subtitle_layout),
                         cta=VALUES(cta), reusable_template=VALUES(reusable_template)""",
                    (
                        int(row["link_id"]), row["url"].strip(),
                        _nullable(row.get("video_id")), _nullable(row.get("author")),
                        _nullable(row.get("hook_3s")), _nullable(row.get("pain_points")),
                        _nullable(row.get("selling_points")), _nullable(row.get("scenes")),
                        _nullable(row.get("video_structure")), _nullable(row.get("subtitle_layout")),
                        _nullable(row.get("cta")), _nullable(row.get("reusable_template")),
                        _nullable(row.get("analyzed_at")), row.get("analyze_status", "ok"),
                        _nullable(row.get("analyze_provider")), _nullable(row.get("error_message")),
                    ),
                )
        if SCRIPT_TEMPLATES_CSV.exists():
            for row in _read_csv(SCRIPT_TEMPLATES_CSV):
                cur.execute(
                    """INSERT INTO script_templates (
                         template_id,label,structure_chain,video_count,
                         sample_link_ids,suitable_for,notes,updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE
                         video_count=VALUES(video_count),
                         sample_link_ids=VALUES(sample_link_ids),
                         updated_at=VALUES(updated_at)""",
                    (
                        row["template_id"], row["label"], row["structure_chain"],
                        int(row.get("video_count") or 0),
                        _nullable(row.get("sample_link_ids")),
                        _nullable(row.get("suitable_for")),
                        _nullable(row.get("notes")),
                        _nullable(row.get("updated_at")),
                    ),
                )
        if PRODUCT_MATERIALS_CSV.exists():
            for row in _read_csv(PRODUCT_MATERIALS_CSV):
                cur.execute(
                    """INSERT INTO product_materials (
                         product_id,product_name,target_audience,core_selling_points,
                         pain_points,usage_scenarios,forbidden_terms,price_range,
                         competitor_ref,source_path,synced_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON DUPLICATE KEY UPDATE product_name=VALUES(product_name),
                         core_selling_points=VALUES(core_selling_points)""",
                    (
                        row["product_id"], row["product_name"],
                        _nullable(row.get("target_audience")),
                        _nullable(row.get("core_selling_points")),
                        _nullable(row.get("pain_points")),
                        _nullable(row.get("usage_scenarios")),
                        _nullable(row.get("forbidden_terms")),
                        _nullable(row.get("price_range")),
                        _nullable(row.get("competitor_ref")),
                        _nullable(row.get("source_path")),
                        _nullable(row.get("synced_at")),
                    ),
                )
    conn.commit()


def cmd_db() -> int:
    if not VIDEOS_META_CSV.exists():
        safe_print("请先运行: python scripts/pipeline.py fetch")
        return 1
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    conn = _db_connect()
    try:
        with conn.cursor() as cur:
            for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
                cur.execute(stmt)
        conn.commit()
        _upsert_db(conn, _read_csv(RAW_LINKS_CSV), _read_csv(VIDEOS_META_CSV))
        na = len(_read_csv(VIDEO_ANALYSIS_CSV)) if VIDEO_ANALYSIS_CSV.exists() else 0
        nt = len(_read_csv(SCRIPT_TEMPLATES_CSV)) if SCRIPT_TEMPLATES_CSV.exists() else 0
        np = len(_read_csv(PRODUCT_MATERIALS_CSV)) if PRODUCT_MATERIALS_CSV.exists() else 0
        safe_print(f"OK MySQL 导入完成（video_analysis {na}，script_templates {nt}，product_materials {np}）")
        return 0
    except pymysql.MySQLError as exc:
        safe_print(f"MySQL 失败: {exc}")
        safe_print("请用根目录「检查开发环境.cmd」确认账号密码。")
        return 1
    finally:
        conn.close()


# ── decompose → video_analysis ─────────────────────────────────────────────

def _tags(meta: dict[str, str]) -> list[str]:
    raw = meta.get("hashtags") or ""
    try:
        return json.loads(raw) if raw.startswith("[") else []
    except json.JSONDecodeError:
        return []


def _rule_analysis(meta: dict[str, str]) -> dict[str, str]:
    """基于标题/话题的规则拆解（无 API Key 时的默认方案）。"""
    title = (meta.get("title") or meta.get("description") or "").strip()
    short = title[:50] if title else "这条母婴短视频"
    tags = _tags(meta)
    tag_text = "、".join(tags[:5]) if tags else "便携暖奶"
    category_hint = meta.get("notes") or tag_text
    blob = f"{title} {tag_text} {category_hint}".lower()
    has_warmer = any(
        k in blob for k in ("warmer", "bottlewarmer", "milkwarmer", "heater", "恒温", "暖奶")
    )
    has_pump = any(
        k in blob for k in ("pump", "pumping", "breastpump", "flange", "lactation", "吸奶", "背奶")
    )
    is_warmer = has_warmer and not has_pump

    if is_warmer:
        return {
            "hook_3s": f"0-3s 抛出外出加热痛点：「{short[:30]}…」抓住停留",
            "pain_points": f"爸妈常见困扰：{category_hint}（外出没热水、加热慢、温度不稳、携带不便）",
            "selling_points": f"视频强调：便携、快充、均匀加热、妈咪包/杯架友好（话题：{tag_text}）",
            "scenes": "车内杯架、妈咪包、夜间卧室喂奶台、机场旅途；产品特写+手部加热演示",
            "video_structure": "钩子(0-3s) → 痛点(3-8s) → 产品演示(8-15s) → 场景证明(15-18s) → CTA(18-20s)",
            "subtitle_layout": "每镜 1 条主字幕，6-12 词；突出 portable / warm / travel；底部居中",
            "cta": "收藏好物清单 / 评论区问链接 / 关注获取更多喂养技巧",
            "reusable_template": (
                "【模板】外出痛点开场 → 便携暖奶器演示 → 场景种草 → 软性 CTA。"
                "适用于便携恒温杯/暖奶器测评与旅行种草短视频。"
            ),
        }

    return {
        "hook_3s": f"0-3s 抛出反问或反差：「{short[:30]}…」抓住停留",
        "pain_points": f"妈妈常见困扰：{category_hint} 相关的不便、踩坑或焦虑（如配件不合、步骤繁琐、夜间打扰）",
        "selling_points": f"视频强调的价值点：实用技巧、省时省力、更好体验（从标题/话题推断：{tag_text}）",
        "scenes": "居家卧室/哺乳角、洗手台清洗区、外出包内便携场景；以近景口播+手部实操为主",
        "video_structure": "钩子(0-3s) → 痛点(3-8s) → 方法演示(8-15s) → 效果/对比(15-18s) → CTA(18-20s)",
        "subtitle_layout": "每镜 1 条主字幕，6-12 字；关键词加粗或贴纸强调；底部居中，避免遮挡产品",
        "cta": "收藏教程 / 评论区交流经验 / 关注获取更多背奶技巧",
        "reusable_template": (
            "【模板】痛点反问开场 → 3步实操演示 → 前后对比一句 → 软性 CTA。"
            "适用于教程类、测评类、hack 类母婴短视频。"
        ),
    }


def _analysis_to_storyboard(analysis: dict[str, str], theme: str) -> dict[str, Any]:
    """把 8 字段拆解转成 MVP 需要的 5 镜分镜。"""
    return {
        "theme": theme[:80],
        "shots": [
            {
                "number": 1, "role": "钩子", "timing": "0-3s",
                "visual": "近景口播或问题特写",
                "copy": analysis["hook_3s"][:60],
                "footage_type": "LIVE_ACTION", "notes": "",
            },
            {
                "number": 2, "role": "痛点", "timing": "3-8s",
                "visual": "展示困扰场景",
                "copy": analysis["pain_points"][:60],
                "footage_type": "LIVE_ACTION", "notes": "",
            },
            {
                "number": 3, "role": "方案", "timing": "8-13s",
                "visual": analysis["scenes"][:40],
                "copy": analysis["selling_points"][:60],
                "footage_type": "LIVE_ACTION", "notes": "",
            },
            {
                "number": 4, "role": "证明", "timing": "13-17s",
                "visual": "结构中段演示",
                "copy": analysis["video_structure"][:60],
                "footage_type": "LIVE_ACTION", "notes": analysis["subtitle_layout"][:40],
            },
            {
                "number": 5, "role": "行动号召", "timing": "17-20s",
                "visual": "口播对镜+文字贴纸",
                "copy": analysis["cta"][:60],
                "footage_type": "LIVE_ACTION", "notes": analysis["reusable_template"][:40],
            },
        ],
    }


def cmd_decompose(
    limit: int = 0,
    provider: str = "auto",
    link_id: int | None = None,
    model: str = "auto",
    force: bool = False,
) -> int:
    if not VIDEOS_META_CSV.exists():
        safe_print("请先运行 fetch")
        return 1
    metas = [r for r in _read_csv(VIDEOS_META_CSV) if r.get("fetch_status") == "ok"]
    if link_id:
        metas = [r for r in metas if str(r.get("link_id")) == str(link_id)]
    if limit:
        metas = metas[:limit]

    from app.data import material_already_analyzed
    from app.doubao_config import doubao_config, video_analysis_policy

    policy = video_analysis_policy()

    use_doubao = provider in ("doubao", "doubao_video")
    if provider == "auto":
        try:
            use_doubao = doubao_config().get("configured", False) and policy.get("llm_enabled", True)
        except Exception:
            use_doubao = False

    existing: dict[str, dict[str, Any]] = {}
    if VIDEO_ANALYSIS_CSV.exists():
        for row in _read_csv(VIDEO_ANALYSIS_CSV):
            existing[str(row.get("link_id", ""))] = row

    DECOMPOSE_DIR.mkdir(parents=True, exist_ok=True)
    skipped = 0
    for meta in metas:
        lid = meta["link_id"]
        key = str(lid)

        if material_already_analyzed(key):
            safe_print(f"  跳过 id={lid}: 已有拆解结果，不重复分析")
            skipped += 1
            continue

        if not policy.get("auto_enabled") and not force:
            safe_print(f"  跳过 id={lid}: 新素材分析已暂停（VIDEO_ANALYSIS_AUTO=0）")
            skipped += 1
            continue

        if use_doubao and not policy.get("llm_enabled"):
            safe_print(f"  跳过 id={lid}: 豆包拆解已暂停（DOUBAO_VIDEO_ANALYSIS_ENABLED=0）")
            skipped += 1
            continue

        try:
            if use_doubao:
                from app.doubao_video_analysis import analyze_material

                enrich = {
                    **meta,
                    "link_id": lid,
                    "hashtags": _tags(meta),
                    "thumbnail_url": meta.get("thumbnail_url", ""),
                }
                row = analyze_material(enrich, model_mode=model)
            else:
                analysis = _rule_analysis(meta)
                row = {
                    "link_id": lid,
                    "url": meta.get("url", ""),
                    "video_id": meta.get("video_id", ""),
                    "author": meta.get("author", ""),
                    **analysis,
                    "analyzed_at": utc_now(),
                    "analyze_status": "ok",
                    "analyze_provider": "rule",
                    "error_message": "",
                }
                out = DECOMPOSE_DIR / lid
                out.mkdir(parents=True, exist_ok=True)
                (out / "analysis.json").write_text(
                    json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
        except Exception as exc:
            analysis = _rule_analysis(meta)
            row = {
                "link_id": lid,
                "url": meta.get("url", ""),
                "video_id": meta.get("video_id", ""),
                "author": meta.get("author", ""),
                **analysis,
                "analyzed_at": utc_now(),
                "analyze_status": "ok",
                "analyze_provider": "rule",
                "error_message": f"doubao_fallback: {exc!r}"[:500],
            }
            out = DECOMPOSE_DIR / lid
            out.mkdir(parents=True, exist_ok=True)
            (out / "analysis.json").write_text(
                json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            safe_print(f"  id={lid} 豆包失败，已回退规则: {exc}")
        existing[str(lid)] = {k: row.get(k, "") for k in ANALYSIS_FIELDS}
        prov = row.get("analyze_provider", "?")
        safe_print(f"  id={lid} {prov} shots={row.get('shot_count', '-')}")

    VIDEO_ANALYSIS_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_rows = sorted(existing.values(), key=lambda r: int(r.get("link_id") or 0))
    with VIDEO_ANALYSIS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ANALYSIS_FIELDS)
        w.writeheader()
        for row in all_rows:
            w.writerow({k: row.get(k, "") for k in ANALYSIS_FIELDS})

    mode = "豆包+规则兜底" if use_doubao else "规则"
    processed = len(metas) - skipped
    safe_print(
        f"OK 数据表/video_analysis.csv（本次处理 {processed} 条，跳过 {skipped} 条，"
        f"合计 {len(all_rows)} 条，{mode}）"
    )
    return 0


# ── templates → script_templates ───────────────────────────────────────────

def _classify_video(row: dict[str, str], meta: dict[str, str]) -> str:
    text = " ".join(
        filter(
            None,
            [
                meta.get("title", ""),
                meta.get("description", ""),
                meta.get("hashtags", ""),
                meta.get("notes", ""),
                row.get("reusable_template", ""),
            ],
        )
    ).lower()
    scores: dict[str, int] = {}
    for tpl in TEMPLATE_CATALOG:
        score = sum(1 for kw in tpl["keywords"] if kw in text)
        scores[tpl["template_id"]] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "tutorial-hack"


def cmd_templates() -> int:
    if not VIDEO_ANALYSIS_CSV.exists():
        safe_print("请先运行 decompose")
        return 1
    analyses = [r for r in _read_csv(VIDEO_ANALYSIS_CSV) if r.get("analyze_status") == "ok"]
    meta_map = {r["link_id"]: r for r in _read_csv(VIDEOS_META_CSV)} if VIDEOS_META_CSV.exists() else {}
    raw_map = {r["link_id"]: r for r in _read_csv(RAW_LINKS_CSV)} if RAW_LINKS_CSV.exists() else {}

    buckets: dict[str, list[str]] = {t["template_id"]: [] for t in TEMPLATE_CATALOG}
    for row in analyses:
        lid = row["link_id"]
        m = meta_map.get(lid, {})
        m = {**raw_map.get(lid, {}), **m}
        tid = _classify_video(row, m)
        buckets[tid].append(lid)

    now = utc_now()
    out_rows: list[dict[str, Any]] = []
    SCRIPT_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    for tpl in TEMPLATE_CATALOG:
        ids = buckets[tpl["template_id"]]
        sample = ",".join(ids[:8])
        out_rows.append(
            {
                "template_id": tpl["template_id"],
                "label": tpl["label"],
                "structure_chain": tpl["structure_chain"],
                "video_count": len(ids),
                "sample_link_ids": sample,
                "suitable_for": tpl["suitable_for"],
                "notes": f"从 {len(analyses)} 条竞品归纳",
                "updated_at": now,
            }
        )
        md = (
            f"# {tpl['label']}\n\n"
            f"**结构链**：{tpl['structure_chain']}\n\n"
            f"**适用**：{tpl['suitable_for']}\n\n"
            f"**样本数**：{len(ids)} 条（link_id: {sample or '无'}）\n"
        )
        (SCRIPT_TEMPLATES_DIR / f"{tpl['template_id']}.md").write_text(md, encoding="utf-8")

    with SCRIPT_TEMPLATES_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TEMPLATE_FIELDS)
        w.writeheader()
        for row in out_rows:
            w.writerow({k: row.get(k, "") for k in TEMPLATE_FIELDS})

    safe_print(f"OK script_templates/ + 数据表/script_templates.csv（{len(out_rows)} 个模板）")
    for row in sorted(out_rows, key=lambda r: -int(r["video_count"])):
        safe_print(f"  · {row['label']}: {row['video_count']} 条 → {row['structure_chain']}")
    return 0


# ── products → product_materials（DS223 + 本地）────────────────────────────

def cmd_products() -> int:
    from sync_products import sync_products

    try:
        rows, status = sync_products()
    except FileNotFoundError as exc:
        safe_print(str(exc))
        return 1
    safe_print(f"OK product_materials（{len(rows)} 个产品，{status}）")
    for row in rows:
        safe_print(f"  · {row['product_name']} → {row['product_id']}")
    return 0


# ── knowledge（KRO skill）──────────────────────────────────────────────────

def cmd_knowledge(query: str, limit: int) -> int:
    script = kro_script_path()
    config = kro_config_path()
    if not script.exists():
        safe_print(f"未找到 KRO 脚本: {script}")
        safe_print("请确认 Downloads 中的 knowledge-research-orchestrator 已解压。")
        return 1
    if not config.exists():
        safe_print(f"未找到配置: {config}")
        return 1

    cmd = [sys.executable, str(script), "--config", str(config)]
    if query:
        cmd.extend([query, "--limit", str(limit), "--json"])
    else:
        cmd.append("--list-sources")

    safe_print(f"KRO: {script.name} | 配置: {config.name}")
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
    except subprocess.SubprocessError as exc:
        safe_print(f"检索失败: {exc}")
        return 1

    out = (completed.stdout or "").strip()
    err = (completed.stderr or "").strip()
    if completed.returncode != 0:
        safe_print(err or out or "KRO 执行失败")
        if "DS223" in err or "obsidian" in err.lower():
            safe_print("提示: 请连接公司内网，确保 \\\\DS223\\obsidian知识库 可访问。")
        return 1

    if query:
        try:
            payload = json.loads(out)
            safe_print(f"命中 {payload.get('result_count', 0)} 条")
            for item in payload.get("results", [])[:limit]:
                safe_print(f"  [{item.get('score', 0):.0f}] {item.get('title', '')}")
                safe_print(f"       {item.get('path', '')}")
        except json.JSONDecodeError:
            safe_print(out[:2000])
    else:
        safe_print(out[:3000])
    return 0


# ── bridge ─────────────────────────────────────────────────────────────────

def _storyboard_md(brief: dict, shots: list) -> str:
    blocks = [
        f"## Shot {s['number']} · {s['role']}（{s['timing']}）\n"
        f"- **画面**: {s['visual']}\n- **口播/字幕**: {s['copy']}\n"
        f"- **类型**: [{s['footage_type']}]\n- **备注**: {s.get('notes', '')}\n"
        for s in sorted(shots, key=lambda x: x["number"])
    ]
    return (
        f"# 中文分镜 · {brief['theme']}\n\n"
        f"> ref: {brief['source_tiktok_url']}\n> 总时长: 20s\n\n"
        + "\n".join(blocks)
    )


def _gate_report(brief: dict) -> str:
    return f"""# B0 Gate · {brief['material_id']}

**GO / NO-GO**: GO（script-only）

竞品参考: {brief.get('source_tiktok_url', '')}
"""


def cmd_bridge(ids: list[int], force: bool) -> int:
    raw = {r["link_id"]: r for r in _read_csv(RAW_LINKS_CSV)} if RAW_LINKS_CSV.exists() else {}
    meta = {r["link_id"]: r for r in _read_csv(VIDEOS_META_CSV)} if VIDEOS_META_CSV.exists() else {}
    analysis_map: dict[str, dict[str, str]] = {}
    if VIDEO_ANALYSIS_CSV.exists():
        analysis_map = {r["link_id"]: r for r in _read_csv(VIDEO_ANALYSIS_CSV) if r.get("analyze_status") == "ok"}

    if not ids:
        ids = sorted(int(k) for k in analysis_map) or sorted(
            int(p.name) for p in DECOMPOSE_DIR.iterdir()
            if p.is_dir() and p.name.isdigit() and (p / "analysis.json").exists()
        )
    done = 0
    for link_id in ids:
        key = str(link_id)
        analysis = analysis_map.get(key)
        if not analysis:
            aj = DECOMPOSE_DIR / key / "analysis.json"
            if aj.exists():
                analysis = json.loads(aj.read_text(encoding="utf-8"))
        if not analysis:
            safe_print(f"跳过 {link_id}: 无 video_analysis，请先运行 decompose")
            continue

        slug = f"ref-{link_id:03d}"
        proj = OVERSEAS_RUNS_DIR / slug
        if proj.exists() and not force:
            safe_print(f"跳过 {slug}: 已存在")
            continue

        m = meta.get(key, {})
        r = raw.get(key, {})
        theme = (m.get("title") or r.get("notes") or slug)[:80]
        storyboard = _analysis_to_storyboard(analysis, theme)
        shots = storyboard["shots"]
        brief = {
            "material_id": slug, "slug": slug, "sku": DEFAULT_SKU,
            "target_country": "US", "language": "en", "platform": ["tiktok", "amazon"],
            "theme": storyboard["theme"], "master_video_id": m.get("video_id") or f"tiktok-{link_id}",
            "owner": "content-ops", "launch_date": "TBD",
            "allowed_claims_en": list(DEFAULT_CLAIMS), "forbidden_terms_extra": [],
            "export_plan_confirmed": False, "overseas_product_page_available": False,
            "allowed_claims_available": True, "source_video_usage_rights_confirmed": False,
            "source_link_id": link_id,
            "source_tiktok_url": m.get("url") or r.get("url", ""),
        }
        proj.mkdir(parents=True, exist_ok=True)
        (proj / "localization-brief.yaml").write_text(
            yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        (proj / "gate-report.md").write_text(_gate_report(brief), encoding="utf-8")
        (proj / "storyboard.json").write_text(
            json.dumps({"shots": shots}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (proj / "storyboard-cn.md").write_text(_storyboard_md(brief, shots), encoding="utf-8")
        (proj / "video-analysis.json").write_text(
            json.dumps({k: analysis.get(k, "") for k in ANALYSIS_FIELDS if k not in ("error_message",)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        safe_print(f"OK → overseas-loc-mvp/runs/{slug}")
        done += 1
    safe_print(f"完成 {done} 条。返回工作台 http://127.0.0.1:8788 → 脚本生成 → 完成交付。")
    return 0 if done else 1


def cmd_prune(
    dry_run: bool = False,
    max_total: int = 0,
    max_candidates: int = 0,
    keep_analyzed: bool = True,
    product_id: str = "",
) -> int:
    from prune_materials import prune_materials, _env_int, _env_bool

    if max_total <= 0:
        max_total = _env_int("MATERIAL_MAX_TOTAL", 80)
    if max_candidates <= 0:
        max_candidates = _env_int("DISCOVERY_CANDIDATE_MAX", 150)

    trim_report: dict | None = None
    pid = (product_id or os.getenv("ACTIVE_PRODUCT_ID") or os.getenv("MATERIAL_DEFAULT_PRODUCT") or "").strip()
    if pid:
        mvp_root = Path(__file__).resolve().parents[1]
        if str(mvp_root) not in sys.path:
            sys.path.insert(0, str(mvp_root))
        from app.material_scope import trim_material_library_to_product

        trim_report = trim_material_library_to_product(pid, dry_run=dry_run)
        mode = "预览" if dry_run else "完成"
        safe_print(
            f"品类收窄{mode}({pid}): 保留 {trim_report.get('kept', 0)}，"
            f"移除非品类 {trim_report.get('removed', 0)}"
        )

    report = prune_materials(
        max_total=max_total,
        max_candidates=max_candidates,
        keep_analyzed=keep_analyzed,
        dry_run=dry_run,
    )
    mode = "预览" if dry_run else "完成"
    safe_print(f"素材库整理{mode}: {report['materials_before']} → {report['materials_after']}（删 {report['materials_removed']}）")
    safe_print(f"候选池: {report['candidates_before']} → {report['candidates_after']}")
    if trim_report and trim_report.get("sample_removed"):
        safe_print(f"品类移除样例 link_id: {', '.join(trim_report['sample_removed'][:10])}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="TikTok 竞品流水线")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("links", help="生成 raw_links.csv")
    f = sub.add_parser("fetch", help="抓取元数据 → videos_meta.csv")
    f.add_argument(
        "--engine",
        choices=("oembed", "auto", "playwright"),
        default="oembed",
        help="oembed=官方 API（快）；auto=先 Playwright 再 oEmbed；playwright=仅浏览器",
    )
    f.add_argument("--product-id", default="", help="仅抓取并保留当前产品品类")
    ds = sub.add_parser("discover", help="发现 TikTok 公开候选 URL → discovery_candidates")
    ds.add_argument("--limit-per-query", type=int, default=30)
    ds.add_argument("--engine", choices=("none", "oembed", "auto", "playwright"), default="auto")
    ds.add_argument("--product-id", default="", help="仅发现当前产品品类（如 便携恒温杯）")
    pr = sub.add_parser("promote", help="候选评分筛选 → raw_links")
    pr.add_argument("--limit", type=int, default=20)
    pr.add_argument("--min-score", type=float, default=0.0)
    pr.add_argument("--product-id", default="", help="仅入库当前产品品类")
    sub.add_parser("db", help="导入 MySQL")
    d = sub.add_parser("decompose", help="结构拆解 → video_analysis（规则或豆包）")
    d.add_argument("--limit", type=int, default=0)
    d.add_argument("--link-id", type=int, default=0)
    d.add_argument("--provider", choices=("auto", "rule", "doubao"), default="auto")
    d.add_argument("--model", choices=("auto", "turbo", "pro"), default="auto")
    d.add_argument(
        "--force",
        action="store_true",
        help="忽略新素材暂停开关（已有拆解结果仍不会重复分析）",
    )
    sub.add_parser("templates", help="归纳爆款结构 → script_templates")
    sub.add_parser("products", help="从 DS223 同步 product_materials")
    ct = sub.add_parser("cache-thumbnails", help="下载封面到本地（修复列表缩略图）")
    ct.add_argument("--force", action="store_true", help="强制重新下载")
    pm = sub.add_parser("prune", help="素材库瘦身：去重、限额、清候选池")
    pm.add_argument("--dry-run", action="store_true")
    pm.add_argument("--product-id", default="", help="先移除非该品类素材（如 便携恒温杯）")
    pm.add_argument("--max-total", type=int, default=0, help="素材上限，0=读 MATERIAL_MAX_TOTAL")
    pm.add_argument("--max-candidates", type=int, default=0, help="候选池上限，0=读 DISCOVERY_CANDIDATE_MAX")
    pm.add_argument("--keep-analyzed", action=argparse.BooleanOptionalAction, default=True)
    k = sub.add_parser("knowledge", help="KRO 知识库检索（默认列出来源）")
    k.add_argument("query", nargs="?", default="", help="检索词，如: 熊猫布布 吸奶器 合规")
    k.add_argument("--limit", type=int, default=6)
    b = sub.add_parser("bridge", help="对接到 MVP runs/ref-XXX")
    b.add_argument("--id", type=int, action="append", dest="ids")
    b.add_argument("--force", action="store_true")
    args = p.parse_args()
    if args.cmd == "links":
        return cmd_links()
    if args.cmd == "fetch":
        return cmd_fetch(
            engine=getattr(args, "engine", "oembed"),
            product_id=getattr(args, "product_id", "") or "",
        )
    if args.cmd == "discover":
        return cmd_discover(
            limit_per_query=getattr(args, "limit_per_query", 30),
            engine=getattr(args, "engine", "auto"),
            product_id=getattr(args, "product_id", "") or "",
        )
    if args.cmd == "promote":
        return cmd_promote(
            limit=getattr(args, "limit", 20),
            min_score=getattr(args, "min_score", 0.0),
            product_id=getattr(args, "product_id", "") or "",
        )
    if args.cmd == "db":
        return cmd_db()
    if args.cmd == "decompose":
        return cmd_decompose(
            args.limit,
            provider=getattr(args, "provider", "auto"),
            link_id=getattr(args, "link_id", 0) or None,
            model=getattr(args, "model", "auto"),
            force=getattr(args, "force", False),
        )
    if args.cmd == "templates":
        return cmd_templates()
    if args.cmd == "products":
        return cmd_products()
    if args.cmd == "cache-thumbnails":
        return cmd_cache_thumbnails(force=getattr(args, "force", False))
    if args.cmd == "prune":
        return cmd_prune(
            dry_run=getattr(args, "dry_run", False),
            max_total=getattr(args, "max_total", 0),
            max_candidates=getattr(args, "max_candidates", 0),
            keep_analyzed=getattr(args, "keep_analyzed", True),
            product_id=getattr(args, "product_id", "") or "",
        )
    if args.cmd == "knowledge":
        return cmd_knowledge(args.query, args.limit)
    if args.cmd == "bridge":
        return cmd_bridge(args.ids or [], args.force)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
