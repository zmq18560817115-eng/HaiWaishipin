"""素材库瘦身：去重、保留高价值条目、清理候选池与磁盘碎片。

原则：
- 已拆解 / 已出脚本 / 已成稿 / 模板引用 → 默认保留
- 未拆解且低播放、无业务关联 → 可删
- 按 video_id 去重，保留分数最高的一条

用法:
  python scripts/prune_materials.py --dry-run
  python scripts/prune_materials.py --max-total 60
  python scripts/pipeline.py prune --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

MVP_ROOT = Path(__file__).resolve().parents[1]
if str(MVP_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MVP_ROOT / "scripts"))

from paths import (  # noqa: E402
    DECOMPOSE_DIR,
    DISCOVERY_CANDIDATES_CSV,
    FINISHED_LIBRARY_DIR,
    GENERATED_SCRIPTS_DIR,
    OVERSEAS_RUNS_DIR,
    RAW_LINKS_CSV,
    SCRIPT_TEMPLATES_CSV,
    THUMBNAILS_DIR,
    VIDEO_ANALYSIS_CSV,
    VIDEOS_META_CSV,
)

from tiktok_discovery import CANDIDATE_FIELDS  # noqa: E402

RAW_LINK_FIELDS = [
    "link_id", "url", "category", "platform", "subcategory", "source", "status", "notes", "added_at",
]
VIDEO_META_FIELDS = [
    "link_id", "url", "video_id", "author", "author_url", "title", "description",
    "duration_sec", "view_count", "like_count", "comment_count", "share_count",
    "hashtags", "thumbnail_url", "fetched_at", "fetch_status", "fetch_provider", "error_message",
]

ANALYSIS_FIELDS = [
    "link_id",
    "url",
    "video_id",
    "author",
    "hook_3s",
    "pain_points",
    "selling_points",
    "scenes",
    "video_structure",
    "subtitle_layout",
    "cta",
    "reusable_template",
    "analyzed_at",
    "analyze_status",
    "analyze_provider",
    "error_message",
]


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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value or "").strip() or default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off")


def protected_link_ids() -> set[str]:
    protected: set[str] = set()

    if FINISHED_LIBRARY_DIR.is_dir():
        for path in FINISHED_LIBRARY_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            lid = str(data.get("link_id") or "").strip()
            if lid:
                protected.add(lid)

    if SCRIPT_TEMPLATES_CSV.exists():
        for row in _read_csv(SCRIPT_TEMPLATES_CSV):
            raw = row.get("sample_link_ids") or ""
            for part in re.split(r"[,;\s]+", raw):
                part = part.strip()
                if part.isdigit():
                    protected.add(part)

    for lid_dir in GENERATED_SCRIPTS_DIR.glob("*"):
        if not lid_dir.is_dir():
            continue
        if (lid_dir / "script-pack.json").is_file():
            protected.add(lid_dir.name)

    for run_dir in OVERSEAS_RUNS_DIR.glob("ref-*"):
        slug = run_dir.name
        if (run_dir / "script-pack.json").is_file() or (run_dir / "delivery" / "manifest.json").is_file():
            m = re.match(r"ref-(\d+)", slug)
            if m:
                protected.add(str(int(m.group(1))))

    return protected


def analyzed_link_ids() -> set[str]:
    ids: set[str] = set()
    for row in _read_csv(VIDEO_ANALYSIS_CSV):
        if row.get("analyze_status") == "ok" and row.get("link_id"):
            ids.add(str(row["link_id"]))
    if DECOMPOSE_DIR.is_dir():
        for path in DECOMPOSE_DIR.iterdir():
            if path.is_dir() and path.name.isdigit():
                if (path / "analysis.json").is_file() or (path / "shots.json").is_file():
                    ids.add(path.name)
    return ids


def material_score(
    meta: dict[str, str],
    raw: dict[str, str],
    *,
    analyzed: bool,
    protected: bool,
) -> float:
    score = 0.0
    if protected:
        score += 1_000_000
    if analyzed:
        score += 10_000
    score += _int(meta.get("view_count"))
    score += _int(meta.get("like_count")) * 10
    if meta.get("fetch_status") == "ok":
        score += 50
    if raw.get("source") == "manual":
        score += 200
    return score


def dedupe_by_video_id(
    metas: list[dict[str, str]],
    raw_by_id: dict[str, dict[str, str]],
    analyzed: set[str],
    protected: set[str],
) -> tuple[list[dict[str, str]], set[str]]:
    """同一 video_id 只保留得分最高的一条，返回去重后的 meta 与将被删除的 link_id。"""
    groups: dict[str, list[dict[str, str]]] = {}
    no_vid: list[dict[str, str]] = []
    for meta in metas:
        vid = (meta.get("video_id") or "").strip()
        if not vid:
            no_vid.append(meta)
            continue
        groups.setdefault(vid, []).append(meta)

    keep: list[dict[str, str]] = list(no_vid)
    drop: set[str] = set()
    for rows in groups.values():
        if len(rows) == 1:
            keep.append(rows[0])
            continue
        ranked = sorted(
            rows,
            key=lambda m: material_score(
                m,
                raw_by_id.get(str(m.get("link_id")), {}),
                analyzed=str(m.get("link_id")) in analyzed,
                protected=str(m.get("link_id")) in protected,
            ),
            reverse=True,
        )
        keep.append(ranked[0])
        for loser in ranked[1:]:
            drop.add(str(loser.get("link_id")))
    return keep, drop


def select_materials_to_keep(
    *,
    max_total: int,
    keep_analyzed: bool,
    protected: set[str],
) -> tuple[set[str], set[str]]:
    raw_rows = _read_csv(RAW_LINKS_CSV)
    raw_by_id = {str(r.get("link_id")): r for r in raw_rows if r.get("link_id")}
    metas = _read_csv(VIDEOS_META_CSV)
    analyzed = analyzed_link_ids()

    metas, dedupe_drop = dedupe_by_video_id(metas, raw_by_id, analyzed, protected)
    keep_ids: set[str] = {str(m.get("link_id")) for m in metas if m.get("link_id")} - dedupe_drop

    ranked = sorted(
        metas,
        key=lambda m: material_score(
            m,
            raw_by_id.get(str(m.get("link_id")), {}),
            analyzed=str(m.get("link_id")) in analyzed,
            protected=str(m.get("link_id")) in protected,
        ),
        reverse=True,
    )

    selected: set[str] = set(protected)
    if keep_analyzed:
        selected |= analyzed
    for meta in ranked:
        lid = str(meta.get("link_id") or "")
        if not lid:
            continue
        if lid in selected:
            continue
        if max_total > 0 and len(selected) >= max_total:
            break
        selected.add(lid)

    all_ids = {str(m.get("link_id")) for m in metas if m.get("link_id")}
    drop_ids = (all_ids - selected) | dedupe_drop
    return selected, drop_ids


def prune_discovery_candidates(*, max_candidates: int, dry_run: bool) -> dict[str, int]:
    rows = _read_csv(DISCOVERY_CANDIDATES_CSV)
    if not rows or max_candidates <= 0 or len(rows) <= max_candidates:
        return {"candidates_before": len(rows), "candidates_removed": 0, "candidates_after": len(rows)}

    pending = [r for r in rows if r.get("status", "candidate") in ("candidate", "selected")]
    archived = [r for r in rows if r not in pending]
    pending.sort(key=lambda r: _int(r.get("score")), reverse=True)
    keep_pending = pending[:max_candidates]
    removed = len(pending) - len(keep_pending)
    new_rows = archived + keep_pending

    if not dry_run and removed:
        _write_csv(DISCOVERY_CANDIDATES_CSV, new_rows, CANDIDATE_FIELDS)

    return {
        "candidates_before": len(rows),
        "candidates_removed": removed,
        "candidates_after": len(new_rows),
    }


def remove_link_files(link_id: str, *, dry_run: bool) -> list[str]:
    removed: list[str] = []
    lid = str(link_id)
    paths = [
        DECOMPOSE_DIR / lid,
        GENERATED_SCRIPTS_DIR / lid,
        THUMBNAILS_DIR / f"{lid}.jpg",
        OVERSEAS_RUNS_DIR / f"ref-{int(lid):03d}",
    ]
    for path in paths:
        if not path.exists():
            continue
        rel = str(path)
        if dry_run:
            removed.append(rel)
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed.append(rel)
    return removed


def prune_materials(
    *,
    max_total: int,
    max_candidates: int,
    keep_analyzed: bool,
    dry_run: bool,
) -> dict[str, Any]:
    raw_rows = _read_csv(RAW_LINKS_CSV)
    meta_before = _read_csv(VIDEOS_META_CSV)
    protected = protected_link_ids()
    keep_ids, drop_ids = select_materials_to_keep(
        max_total=max_total,
        keep_analyzed=keep_analyzed,
        protected=protected,
    )

    raw_rows = [r for r in raw_rows if str(r.get("link_id")) in keep_ids]
    meta_rows = [r for r in meta_before if str(r.get("link_id")) in keep_ids]
    analysis_rows = [r for r in _read_csv(VIDEO_ANALYSIS_CSV) if str(r.get("link_id")) in keep_ids]

    file_removals: list[str] = []
    for lid in sorted(drop_ids, key=lambda x: int(x) if x.isdigit() else 0):
        file_removals.extend(remove_link_files(lid, dry_run=dry_run))

    if not dry_run and drop_ids:
        _write_csv(RAW_LINKS_CSV, raw_rows, RAW_LINK_FIELDS)
        _write_csv(VIDEOS_META_CSV, meta_rows, VIDEO_META_FIELDS)
        if analysis_rows or VIDEO_ANALYSIS_CSV.exists():
            _write_csv(VIDEO_ANALYSIS_CSV, analysis_rows, ANALYSIS_FIELDS)

    cand = prune_discovery_candidates(max_candidates=max_candidates, dry_run=dry_run)

    return {
        "dry_run": dry_run,
        "max_total": max_total,
        "max_candidates": max_candidates,
        "keep_analyzed": keep_analyzed,
        "protected_count": len(protected),
        "materials_before": len(meta_before),
        "materials_removed": len(drop_ids),
        "materials_after": len(meta_rows),
        "removed_link_ids": sorted(drop_ids, key=lambda x: int(x) if x.isdigit() else 0)[:30],
        "file_removals": len(file_removals),
        **cand,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="素材库瘦身：去重、限额、清理候选池")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    parser.add_argument(
        "--max-total",
        type=int,
        default=_env_int("MATERIAL_MAX_TOTAL", 80),
        help="素材上限（videos_meta 条数，0=仅去重不裁总量）",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=_env_int("DISCOVERY_CANDIDATE_MAX", 150),
        help="discovery_candidates 候选池上限",
    )
    parser.add_argument(
        "--keep-analyzed",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("MATERIAL_KEEP_ANALYZED", True),
        help="始终保留已拆解素材",
    )
    args = parser.parse_args()

    if not VIDEOS_META_CSV.exists():
        print("videos_meta.csv 不存在，无需整理")
        return 0

    report = prune_materials(
        max_total=args.max_total,
        max_candidates=args.max_candidates,
        keep_analyzed=args.keep_analyzed,
        dry_run=args.dry_run,
    )

    mode = "预览" if args.dry_run else "已执行"
    print(f"=== 素材库整理 ({mode}) ===")
    print(f"  素材: {report['materials_before']} → {report['materials_after']}（删除 {report['materials_removed']}）")
    print(f"  受保护: {report['protected_count']} · 保留已拆解: {args.keep_analyzed}")
    print(f"  候选池: {report['candidates_before']} → {report['candidates_after']}（删除 {report['candidates_removed']}）")
    print(f"  磁盘目录/文件: {report['file_removals']}")
    if report.get("removed_link_ids"):
        sample = ", ".join(report["removed_link_ids"][:12])
        suffix = " …" if len(report["removed_link_ids"]) > 12 else ""
        print(f"  示例删除 link_id: {sample}{suffix}")
    if args.dry_run:
        print("  （dry-run 未写入，确认后去掉 --dry-run）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
