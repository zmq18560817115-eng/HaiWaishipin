from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from paths import (
    DECOMPOSE_DIR,
    GENERATED_SCRIPTS_DIR,
    OVERSEAS_RUNS_DIR,
    PRODUCT_MATERIALS_CSV,
    RAW_LINKS_CSV,
    VIDEO_ANALYSIS_CSV,
    VIDEOS_META_CSV,
)

from .brand_policy import detect_content_line
from .olm_bridge import delivery_ready


ANALYSIS_FIELDS = [
    "hook_3s",
    "pain_points",
    "selling_points",
    "scenes",
    "video_structure",
    "subtitle_layout",
    "cta",
    "reusable_template",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_hashtags(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(x) for x in data] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def load_products() -> list[dict[str, str]]:
    from .products import list_products

    return list_products()


def load_analysis(link_id: str) -> dict[str, str] | None:
    for row in _read_csv(VIDEO_ANALYSIS_CSV):
        if row.get("link_id") == link_id and row.get("analyze_status") == "ok":
            return row
    path = DECOMPOSE_DIR / link_id / "analysis.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def load_materials() -> list[dict[str, Any]]:
    raw = {r["link_id"]: r for r in _read_csv(RAW_LINKS_CSV)}
    items: list[dict[str, Any]] = []
    for meta in _read_csv(VIDEOS_META_CSV):
        lid = meta.get("link_id", "")
        if not lid:
            continue
        link = raw.get(lid, {})
        analysis = load_analysis(lid)
        title = (meta.get("title") or link.get("notes") or f"视频 #{lid}").strip()
        hashtags = _parse_hashtags(meta.get("hashtags") or "")
        row = {
                "link_id": int(lid),
                "url": meta.get("url") or link.get("url", ""),
                "video_id": meta.get("video_id", ""),
                "author": meta.get("author", ""),
                "title": title,
                "description": (meta.get("description") or "")[:280],
                "thumbnail_url": meta.get("thumbnail_url", ""),
                "duration_sec": meta.get("duration_sec") or "",
                "view_count": meta.get("view_count") or "",
                "like_count": meta.get("like_count") or "",
                "category": link.get("category", ""),
                "subcategory": link.get("subcategory", ""),
                "notes": link.get("notes", ""),
                "hashtags": hashtags,
                "fetch_status": meta.get("fetch_status", ""),
                "fetch_provider": meta.get("fetch_provider", ""),
                "has_analysis": analysis is not None,
                "analyze_provider": (analysis or {}).get("analyze_provider", ""),
                "reusable_template": (analysis or {}).get("reusable_template", ""),
            }
        if analysis:
            row["analysis"] = {k: analysis.get(k, "") for k in ANALYSIS_FIELDS}
        row["content_line"] = detect_content_line(row)
        lid_int = int(lid)
        row["has_script"] = link_has_script(lid_int)
        row["delivery_ready"] = delivery_ready(f"ref-{lid_int:03d}")
        items.append(row)
    items.sort(key=lambda x: x["link_id"])
    return items


def filter_materials(
    items: list[dict[str, Any]],
    *,
    category: str = "",
    subcategory: str = "",
    keyword: str = "",
    analyzed_only: bool = False,
) -> list[dict[str, Any]]:
    keyword = keyword.strip().lower()
    out: list[dict[str, Any]] = []
    for item in items:
        if category and item.get("category") != category:
            continue
        if subcategory and item.get("subcategory") != subcategory:
            continue
        if analyzed_only and not item.get("has_analysis"):
            continue
        if keyword:
            hay = " ".join(
                [
                    str(item.get("title", "")),
                    str(item.get("author", "")),
                    str(item.get("notes", "")),
                    " ".join(item.get("hashtags") or []),
                ]
            ).lower()
            if keyword not in hay:
                continue
        out.append(item)
    return out


def link_has_script(link_id: int) -> bool:
    gen_dir = GENERATED_SCRIPTS_DIR / str(link_id)
    if (gen_dir / "script-pack.json").exists():
        return True
    slug = f"ref-{link_id:03d}"
    return (OVERSEAS_RUNS_DIR / slug / "script-pack.json").exists()


def load_script_payload(link_id: int) -> dict[str, Any]:
    for path in (
        GENERATED_SCRIPTS_DIR / str(link_id) / "script-pack.json",
        OVERSEAS_RUNS_DIR / f"ref-{link_id:03d}" / "script-pack.json",
    ):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data.get("payload"), dict):
            return data["payload"]
        if data.get("voiceover_20s") or data.get("storyboard"):
            return data
    return {}


def material_detail(link_id: int) -> dict[str, Any] | None:
    for item in load_materials():
        if item["link_id"] == link_id:
            analysis = load_analysis(str(link_id))
            product_rows = load_products()
            generated = GENERATED_SCRIPTS_DIR / str(link_id)
            pack_path = generated / "script-pack.json"
            script_pack = None
            if pack_path.exists():
                try:
                    script_pack = json.loads(pack_path.read_text(encoding="utf-8")).get("pack")
                except (json.JSONDecodeError, OSError):
                    script_pack = None
            payload = dict(item)
            payload["analysis"] = analysis
            payload["products"] = product_rows
            payload["script_pack"] = script_pack
            payload["generated"] = {
                "exists": generated.exists(),
                "files": sorted(p.name for p in generated.glob("*")) if generated.exists() else [],
            }
            payload["has_script"] = link_has_script(link_id)
            payload["script_payload"] = load_script_payload(link_id)
            bridged = Path(__file__).resolve().parents[2] / "overseas-loc-mvp" / "runs" / f"ref-{link_id:03d}"
            payload["bridged_slug"] = bridged.name if bridged.exists() else ""
            return payload
    return None


def filter_options() -> dict[str, Any]:
    items = load_materials()
    categories = sorted({i["category"] for i in items if i.get("category")})
    subcategories = sorted({i["subcategory"] for i in items if i.get("subcategory")})
    products = [
        {"product_id": p["product_id"], "product_name": p["product_name"]}
        for p in load_products()
    ]
    return {
        "categories": categories,
        "subcategories": subcategories,
        "products": products,
        "total": len(items),
        "analyzed": sum(1 for i in items if i.get("has_analysis")),
    }
