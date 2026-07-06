"""CreatOK 式爆款雷达 — 综合评分与选题理由（增量于素材库，不替换原排序）。"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from paths import MVP_ROOT

from .data import load_materials
from .material_scope import material_dict_matches_product

_WEIGHTS_PATH = MVP_ROOT.parent / "config" / "radar-weights.json"

_DEFAULT_WEIGHTS: dict[str, Any] = {
    "view_log_cap": 7.0,
    "engagement_cap": 0.12,
    "analysis_fields": ["hook_3s", "video_structure", "reusable_template"],
    "weights": {
        "view_score": 0.35,
        "engagement_score": 0.25,
        "analysis_score": 0.2,
        "product_match": 0.2,
    },
    "min_analyzed_for_radar": True,
}


def load_radar_weights() -> dict[str, Any]:
    if not _WEIGHTS_PATH.is_file():
        return dict(_DEFAULT_WEIGHTS)
    try:
        data = json.loads(_WEIGHTS_PATH.read_text(encoding="utf-8"))
        merged = {**_DEFAULT_WEIGHTS, **data}
        merged["weights"] = {**_DEFAULT_WEIGHTS["weights"], **(data.get("weights") or {})}
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_WEIGHTS)


def _parse_count(raw: Any) -> float:
    text = str(raw or "").strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _engagement_rate(item: dict[str, Any]) -> float:
    views = _parse_count(item.get("view_count"))
    if views <= 0:
        return 0.0
    likes = _parse_count(item.get("like_count"))
    comments = _parse_count(item.get("comment_count"))
    shares = _parse_count(item.get("share_count"))
    return (likes + comments + shares) / views


def _analysis_score(item: dict[str, Any], fields: list[str]) -> float:
    analysis = item.get("analysis") if isinstance(item.get("analysis"), dict) else {}
    if not analysis and not item.get("has_analysis"):
        return 0.0
    filled = sum(1 for f in fields if str(analysis.get(f) or "").strip())
    return filled / max(1, len(fields))


def score_material(item: dict[str, Any], *, product_id: str = "", cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_radar_weights()
    weights = cfg.get("weights") or {}
    view_cap = float(cfg.get("view_log_cap") or 7.0)
    eng_cap = float(cfg.get("engagement_cap") or 0.12)
    fields = list(cfg.get("analysis_fields") or _DEFAULT_WEIGHTS["analysis_fields"])

    views = _parse_count(item.get("view_count"))
    view_score = min(1.0, math.log10(views + 1) / view_cap) if views > 0 else 0.0

    eng = _engagement_rate(item)
    engagement_score = min(1.0, eng / eng_cap) if eng_cap > 0 else 0.0

    analysis_score = _analysis_score(item, fields)

    product_match = 1.0 if (not product_id or material_dict_matches_product(item, product_id)) else 0.35

    radar_score = round(
        100
        * (
            view_score * float(weights.get("view_score", 0.35))
            + engagement_score * float(weights.get("engagement_score", 0.25))
            + analysis_score * float(weights.get("analysis_score", 0.2))
            + product_match * float(weights.get("product_match", 0.2))
        ),
        1,
    )

    tags: list[str] = []
    if views >= 500_000:
        tags.append("高播放")
    elif views >= 100_000:
        tags.append("中播放")
    if eng >= eng_cap * 0.8:
        tags.append("高互动")
    if item.get("has_analysis") and analysis_score >= 0.66:
        tags.append("结构清晰")
    analysis = item.get("analysis") if isinstance(item.get("analysis"), dict) else {}
    if str(analysis.get("hook_3s") or "").strip():
        tags.append("强钩子")
    if product_match >= 0.99:
        tags.append("品类匹配")

    why_parts: list[str] = []
    if views > 0:
        why_parts.append(f"播放 {int(views):,}")
    if eng > 0:
        why_parts.append(f"互动率 {eng * 100:.1f}%")
    if str(analysis.get("hook_3s") or "").strip():
        hook = str(analysis.get("hook_3s") or "")[:36]
        why_parts.append(f"钩子：{hook}")
    elif str(analysis.get("video_structure") or "").strip():
        why_parts.append("结构已拆解，可复刻节奏")
    if not why_parts:
        why_parts.append("同品类对标，适合结构参考")

    return {
        "radar_score": radar_score,
        "radar_tags": tags[:4],
        "why_pick": " · ".join(why_parts[:3]),
        "engagement_rate": round(eng, 4),
    }


def radar_feed(*, product_id: str = "", limit: int = 24, analyzed_only: bool = True) -> dict[str, Any]:
    cfg = load_radar_weights()
    items = load_materials()
    if product_id:
        items = [i for i in items if material_dict_matches_product(i, product_id)]
    if analyzed_only and cfg.get("min_analyzed_for_radar", True):
        items = [i for i in items if i.get("has_analysis")]

    scored: list[dict[str, Any]] = []
    for row in items:
        extra = score_material(row, product_id=product_id, cfg=cfg)
        scored.append({**row, **extra})

    scored.sort(key=lambda x: (x.get("radar_score", 0), _parse_count(x.get("view_count"))), reverse=True)
    lim = max(1, min(48, int(limit or 24)))
    return {
        "product_id": product_id,
        "total": len(scored),
        "items": scored[:lim],
        "weights": cfg.get("weights"),
    }
