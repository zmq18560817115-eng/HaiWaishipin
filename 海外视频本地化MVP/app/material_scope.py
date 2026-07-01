"""素材库按当前产品品类收窄（如仅保留便携恒温杯）。"""
from __future__ import annotations

import csv
import os
import shutil
from pathlib import Path
from typing import Any

from paths import (
    DECOMPOSE_DIR,
    GENERATED_SCRIPTS_DIR,
    RAW_LINKS_CSV,
    THUMBNAILS_DIR,
    VIDEO_ANALYSIS_CSV,
    VIDEOS_META_CSV,
)

from .brand_policy import detect_content_line, product_material_match

# product_id（工作台所选产品）→ 抓取/入库用的 category / subcategory
PRODUCT_SCOPE: dict[str, dict[str, str]] = {
    "便携恒温杯": {"category": "bottle_warmer", "subcategory": "便携恒温杯"},
    "吸奶器": {"category": "breast_pump", "subcategory": "吸奶器"},
}

RAW_LINK_FIELDS = [
    "link_id", "url", "category", "platform", "subcategory", "source", "status", "notes", "added_at",
]
VIDEO_META_FIELDS = [
    "link_id", "url", "video_id", "author", "author_url", "title", "description",
    "duration_sec", "view_count", "like_count", "comment_count", "share_count",
    "hashtags", "thumbnail_url", "fetched_at", "fetch_status", "fetch_provider", "error_message",
]
ANALYSIS_FIELDS = [
    "link_id", "url", "video_id", "author", "hook_3s", "pain_points", "selling_points", "scenes",
    "video_structure", "subtitle_layout", "cta", "reusable_template",
    "analyzed_at", "analyze_status", "analyze_provider", "error_message",
]


def active_product_id() -> str:
    return (os.getenv("ACTIVE_PRODUCT_ID") or os.getenv("MATERIAL_DEFAULT_PRODUCT") or "").strip()


def scope_for_product(product_id: str) -> dict[str, str] | None:
    return PRODUCT_SCOPE.get(product_id)


def link_row_matches_product(link: dict[str, Any], product_id: str) -> bool:
    if not product_id:
        return True
    spec = scope_for_product(product_id)
    if not spec:
        return True
    cat = str(link.get("category") or "").strip()
    sub = str(link.get("subcategory") or "").strip()
    if cat and cat == spec["category"]:
        return True
    if sub and (sub == spec.get("subcategory") or sub == product_id):
        return True
    return False


def candidate_row_matches_product(row: dict[str, Any], product_id: str) -> bool:
    return link_row_matches_product(row, product_id)


def material_dict_matches_product(material: dict[str, Any], product_id: str) -> bool:
    if not product_id:
        return True
    line = detect_content_line(material)
    if line:
        return line == product_id
    raw = {
        "category": material.get("category", ""),
        "subcategory": material.get("subcategory", ""),
    }
    return link_row_matches_product(raw, product_id)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def _remove_link_artifacts(link_id: str) -> None:
    lid = str(link_id)
    for path in (
        DECOMPOSE_DIR / lid,
        GENERATED_SCRIPTS_DIR / lid,
        THUMBNAILS_DIR / f"{lid}.jpg",
    ):
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def trim_material_library_to_product(product_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    """删除与当前产品品类不一致的素材（CSV + 拆解目录）。"""
    if not product_id or os.getenv("MATERIAL_SCOPE_TRIM", "1").strip() in ("0", "false", "no"):
        return {"product_id": product_id, "removed": 0, "skipped": True}

    raw_rows = _read_csv(RAW_LINKS_CSV)
    meta_rows = _read_csv(VIDEOS_META_CSV)
    analysis_rows = _read_csv(VIDEO_ANALYSIS_CSV)
    raw_by_id = {str(r.get("link_id")): r for r in raw_rows if r.get("link_id")}
    meta_by_id = {str(r.get("link_id")): r for r in meta_rows if r.get("link_id")}

    all_ids = set(raw_by_id) | set(meta_by_id)
    keep_ids: set[str] = set()
    for lid in all_ids:
        meta = meta_by_id.get(lid, {})
        raw = raw_by_id.get(lid, {})
        merged = {**raw, **meta, "analysis": {}}
        if material_dict_matches_product(merged, product_id):
            keep_ids.add(lid)
        elif product_material_match(product_id, merged):
            keep_ids.add(lid)

    drop_ids = sorted(all_ids - keep_ids, key=lambda x: int(x) if x.isdigit() else 0)
    if not drop_ids:
        return {"product_id": product_id, "removed": 0, "kept": len(keep_ids)}

    if not dry_run:
        _write_csv(RAW_LINKS_CSV, [r for r in raw_rows if str(r.get("link_id")) in keep_ids], RAW_LINK_FIELDS)
        _write_csv(VIDEOS_META_CSV, [r for r in meta_rows if str(r.get("link_id")) in keep_ids], VIDEO_META_FIELDS)
        _write_csv(
            VIDEO_ANALYSIS_CSV,
            [r for r in analysis_rows if str(r.get("link_id")) in keep_ids],
            ANALYSIS_FIELDS,
        )
        for lid in drop_ids:
            _remove_link_artifacts(lid)

    return {
        "product_id": product_id,
        "removed": len(drop_ids),
        "kept": len(keep_ids),
        "dry_run": dry_run,
        "sample_removed": drop_ids[:15],
    }
