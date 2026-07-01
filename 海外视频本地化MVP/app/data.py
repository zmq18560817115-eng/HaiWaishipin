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

from .thumbnails import public_thumbnail_url
from .olm_bridge import delivery_ready
from .brand_policy import detect_content_line


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


def load_analysis_detail(link_id: str) -> dict[str, Any] | None:
    base = DECOMPOSE_DIR / str(link_id)
    shots_path = base / "shots.json"
    transcript_path = base / "transcript.json"
    analysis = load_analysis(str(link_id))
    if not analysis and not shots_path.exists():
        return None
    detail: dict[str, Any] = {
        "link_id": link_id,
        "analysis": analysis,
        "summary": (analysis or {}).get("summary", ""),
        "full_transcript": (analysis or {}).get("full_transcript", ""),
        "shot_count": (analysis or {}).get("shot_count", 0),
        "analyze_provider": (analysis or {}).get("analyze_provider", ""),
        "analyze_model": (analysis or {}).get("analyze_model", ""),
        "shots": [],
        "transcript": {},
    }
    if shots_path.exists():
        try:
            shots_doc = json.loads(shots_path.read_text(encoding="utf-8"))
            detail["shots"] = shots_doc.get("shots") or []
            detail["shot_count"] = len(detail["shots"])
            if detail["shots"] and shots_doc.get("model"):
                detail["analyze_provider"] = "doubao_video"
                detail["analyze_model"] = shots_doc.get("model", "")
        except (json.JSONDecodeError, OSError):
            pass
    if transcript_path.exists():
        try:
            detail["transcript"] = json.loads(transcript_path.read_text(encoding="utf-8"))
            if not detail["full_transcript"]:
                detail["full_transcript"] = detail["transcript"].get("full_transcript", "")
        except (json.JSONDecodeError, OSError):
            pass
    if not detail.get("summary") and detail.get("shots"):
        dlg = " ".join(
            str(s.get("dialogue") or "") for s in detail["shots"] if s.get("dialogue")
        ).strip()
        if dlg:
            detail["summary"] = dlg[:280]
    return detail


def shot_count_for(link_id: str, detail: dict[str, Any] | None = None) -> int:
    if detail:
        shots = detail.get("shots") or []
        if shots:
            return len(shots)
    shots_path = DECOMPOSE_DIR / link_id / "shots.json"
    if shots_path.exists():
        try:
            return len(json.loads(shots_path.read_text(encoding="utf-8")).get("shots") or [])
        except (json.JSONDecodeError, OSError):
            pass
    return 0


def material_already_analyzed(link_id: str, detail: dict[str, Any] | None = None) -> bool:
    """是否已有拆解结果（含规则/豆包），用于避免重复调大模型。"""
    if shot_count_for(link_id, detail) >= 1:
        return True
    if load_analysis(link_id):
        return True
    aj = DECOMPOSE_DIR / str(link_id) / "analysis.json"
    return aj.exists()


def needs_doubao_analysis(link_id: str, detail: dict[str, Any] | None = None) -> bool:
    """是否需自动跑豆包精细拆解。"""
    from .doubao_config import _env, _env_flag, doubao_config, video_analysis_policy

    policy = video_analysis_policy()
    if not policy.get("llm_enabled"):
        return False
    if not policy.get("auto_enabled"):
        return False
    if not _env_flag(_env().get("VIDEO_ANALYSIS_ON_VIEW"), default=False):
        return False
    if not doubao_config().get("configured"):
        return False
    if material_already_analyzed(link_id, detail):
        return False
    detail = detail if detail is not None else load_analysis_detail(link_id)
    analysis = (detail or {}).get("analysis") if detail else None
    err = ""
    if isinstance(analysis, dict):
        err = str(analysis.get("error_message") or "")
    if "doubao_fallback" in err:
        return False
    if not detail:
        return True
    return detail.get("analyze_provider") != "doubao_video"


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
                "thumbnail_url": public_thumbnail_url(lid),
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
            script_meta = None
            if pack_path.exists():
                try:
                    raw_pack = json.loads(pack_path.read_text(encoding="utf-8"))
                    script_pack = raw_pack.get("pack")
                    script_meta = raw_pack.get("meta")
                except (json.JSONDecodeError, OSError):
                    script_pack = None
                    script_meta = None
            payload = dict(item)
            payload["analysis"] = analysis
            payload["products"] = product_rows
            payload["script_pack"] = script_pack
            payload["script_meta"] = script_meta
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
