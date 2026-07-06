"""对标素材库：同步热点、品类收窄、去重限额 — 供设置内素材维护操作。"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import (
    DECOMPOSE_DIR,
    DISCOVERY_CANDIDATES_CSV,
    MVP_ROOT,
    PROMPT_LIBRARY_JSON,
    RAW_LINKS_CSV,
    THUMBNAILS_DIR,
    VIDEO_ANALYSIS_CSV,
    VIDEOS_META_CSV,
)

from .data import load_materials
from .hotspot_refresh import refresh_hotspot_videos, save_hotspot_state
from .material_scope import trim_material_library_to_product

SCRIPTS_DIR = MVP_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prune_materials import _env_bool, _env_int, prune_materials  # noqa: E402

STATE_PATH = MVP_ROOT / "data" / "material_maintenance.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_maintenance_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_maintenance_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def maintenance_status_payload() -> dict[str, Any]:
    state = load_maintenance_state()
    items = load_materials()
    analyzed = sum(1 for i in items if i.get("has_analysis"))
    return {
        "last_run_at": state.get("last_run_at"),
        "last_product_id": state.get("last_product_id") or "",
        "last_message": state.get("last_message") or "",
        "last_trim_removed": int(state.get("last_trim_removed") or 0),
        "last_prune_removed": int(state.get("last_prune_removed") or 0),
        "materials_total": len(items),
        "materials_analyzed": analyzed,
        "max_total": _env_int("MATERIAL_MAX_TOTAL", 80),
    }


def run_material_maintenance(
    *,
    product_id: str = "",
    sync: bool = True,
    trim: bool = True,
    prune: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    product_id = (product_id or "").strip()
    report: dict[str, Any] = {
        "ok": True,
        "product_id": product_id,
        "dry_run": dry_run,
        "steps": [],
        "message": "",
    }

    if sync:
        sync_out = refresh_hotspot_videos(product_id=product_id, mode="auto")
        report["sync"] = sync_out
        report["steps"].append("sync")

    if trim and product_id:
        trim_out = trim_material_library_to_product(product_id, dry_run=dry_run)
        report["trim"] = trim_out
        report["steps"].append("trim")

    if prune:
        prune_out = prune_materials(
            max_total=_env_int("MATERIAL_MAX_TOTAL", 80),
            max_candidates=_env_int("DISCOVERY_CANDIDATE_MAX", 150),
            keep_analyzed=_env_bool("MATERIAL_KEEP_ANALYZED", True),
            dry_run=dry_run,
        )
        report["prune"] = prune_out
        report["steps"].append("prune")

    items = load_materials()
    report["materials_total"] = len(items)
    report["materials_analyzed"] = sum(1 for i in items if i.get("has_analysis"))
    report["refreshed_at"] = _utc_now()

    trim_n = int((report.get("trim") or {}).get("removed") or 0)
    prune_n = int((report.get("prune") or {}).get("materials_removed") or 0)
    sync_new = int((report.get("sync") or {}).get("imported_new_links") or 0)
    parts = []
    if sync_new:
        parts.append(f"新增 {sync_new} 条热点")
    if trim_n:
        parts.append(f"移除非品类 {trim_n} 条")
    if prune_n:
        parts.append(f"整理删除 {prune_n} 条")
    if not parts:
        parts.append("素材库已是最新，无需清理")
    report["message"] = " · ".join(parts)

    if not dry_run:
        save_maintenance_state(
            {
                "last_run_at": report["refreshed_at"],
                "last_product_id": product_id,
                "last_message": report["message"],
                "last_trim_removed": trim_n,
                "last_prune_removed": prune_n,
                "last_sync_new": sync_new,
            }
        )
    return report


def _write_csv_header(path: Path, header_line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff" + header_line.rstrip("\n") + "\n", encoding="utf-8")


def _purge_dir_contents(folder: Path) -> int:
    if not folder.exists():
        return 0
    removed = 0
    for child in folder.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
        else:
            child.unlink(missing_ok=True)
            removed += 1
    return removed


def _prune_reverse_prompts() -> int:
    if not PROMPT_LIBRARY_JSON.exists():
        return 0
    try:
        data = json.loads(PROMPT_LIBRARY_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    items = data if isinstance(data, list) else list((data or {}).get("items") or [])
    kept = [row for row in items if not str(row.get("source") or "").startswith("reverse")]
    removed = len(items) - len(kept)
    if removed:
        payload = {"version": 1, "updated_at": _utc_now(), "items": kept}
        PROMPT_LIBRARY_JSON.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return removed


def clear_material_library() -> dict[str, Any]:
    """清空对标素材库（保留产品资料、采集关键词与内置提示词预设）。"""
    headers = {
        RAW_LINKS_CSV: "link_id,url,category,platform,subcategory,source,status,notes,added_at",
        VIDEOS_META_CSV: "link_id,url,video_id,author,author_url,title,description,duration_sec,view_count,like_count,comment_count,share_count,hashtags,thumbnail_url,fetched_at,fetch_status,fetch_provider,error_message",
        VIDEO_ANALYSIS_CSV: "link_id,url,video_id,author,hook_3s,pain_points,selling_points,scenes,video_structure,subtitle_layout,cta,reusable_template,analyzed_at,analyze_status,analyze_provider,error_message",
        DISCOVERY_CANDIDATES_CSV: "candidate_id,video_id,url,author,title,description,duration_sec,view_count,like_count,comment_count,share_count,hashtags,thumbnail_url,category,subcategory,source_query_id,source_type,source_value,discover_provider,fetch_provider,score,status,discovered_at,promoted_at,error_message",
    }
    cleared_paths: set[Path] = set()
    for path, header in headers.items():
        key = path.resolve()
        if key in cleared_paths:
            continue
        cleared_paths.add(key)
        _write_csv_header(path, header)
        legacy = MVP_ROOT / "数据表" / path.name
        if legacy.resolve() != key and legacy.exists():
            _write_csv_header(legacy, header)

    decompose_removed = _purge_dir_contents(DECOMPOSE_DIR)
    legacy_decompose = MVP_ROOT / "AI拆解结果"
    if legacy_decompose.resolve() != DECOMPOSE_DIR.resolve():
        decompose_removed += _purge_dir_contents(legacy_decompose)
    thumbs_removed = _purge_dir_contents(THUMBNAILS_DIR)
    prompts_removed = _prune_reverse_prompts()
    legacy_prompt = MVP_ROOT / "数据表" / "prompt_library.json"
    if legacy_prompt.resolve() != PROMPT_LIBRARY_JSON.resolve() and legacy_prompt.exists():
        try:
            legacy_prompt.write_text(PROMPT_LIBRARY_JSON.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    save_maintenance_state({})
    save_hotspot_state({})

    return {
        "ok": True,
        "message": "对标素材库已清空，可从 TikTok 采集重新测试",
        "decompose_dirs_removed": decompose_removed,
        "thumbnails_removed": thumbs_removed,
        "reverse_prompts_removed": prompts_removed,
        "materials_total": 0,
        "materials_analyzed": 0,
        "cleared_at": _utc_now(),
    }
