from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MVP_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = MVP_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from paths import RAW_LINKS_CSV, VIDEOS_META_CSV


WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
if str(WORKFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT))

from tiktok_collector.models import CollectRequest, ReviewedTikTokVideoRecord
from tiktok_collector.repository import TikTokVideoRepository
from tiktok_collector.service import TikTokCollectorService


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

VIDEO_META_FIELDS = [
    "link_id",
    "url",
    "video_id",
    "author",
    "author_url",
    "title",
    "description",
    "duration_sec",
    "view_count",
    "like_count",
    "comment_count",
    "share_count",
    "hashtags",
    "thumbnail_url",
    "fetched_at",
    "fetch_status",
    "fetch_provider",
    "error_message",
]


@dataclass(slots=True)
class CollectorImportResult:
    total_collected: int
    total_cleaned: int
    total_dropped: int
    imported_new_links: int
    updated_existing_links: int
    json_path: str | None
    csv_path: str | None
    clean_json_path: str | None
    clean_csv_path: str | None
    review_json_path: str | None
    output_dir: str


@dataclass(slots=True)
class CollectorDatabaseQueryResult:
    db_enabled: bool
    total: int
    items: list[dict[str, Any]]


@dataclass(slots=True)
class CollectorDatabaseSyncResult:
    db_enabled: bool
    queried_total: int
    synced_count: int
    imported_new_links: int
    updated_existing_links: int


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _guess_category(keyword: str) -> tuple[str, str]:
    blob = keyword.strip().lower()
    if "pump" in blob or "breast pump" in blob:
        return "breast_pump", "吸奶器"
    if any(token in blob for token in ("bottle", "warmer", "milk warmer")):
        return "bottle_warmer", "便携恒温杯"
    if "baby" in blob:
        return "baby_products", "母婴用品"
    return "tiktok_search", "TikTok搜索"


def _hashtags_json(tags: list[str]) -> str:
    return json.dumps(tags or [], ensure_ascii=False)


def import_reviewed_records(
    records: list[ReviewedTikTokVideoRecord],
    *,
    total_collected: int,
    total_dropped: int,
    json_path: str | None,
    csv_path: str | None,
    clean_json_path: str | None,
    clean_csv_path: str | None,
    review_json_path: str | None,
    output_dir: str,
    product_id: str = "",
) -> CollectorImportResult:
    from app.brand_policy import product_material_match
    from app.material_scope import material_dict_matches_product, scope_for_product, trim_material_library_to_product

    product_id = (product_id or "").strip()
    scoped = scope_for_product(product_id) if product_id else None
    raw_links = _read_csv(RAW_LINKS_CSV)
    videos_meta = _read_csv(VIDEOS_META_CSV)

    raw_by_url = {row.get("url", ""): row for row in raw_links if row.get("url")}
    meta_by_link_id = {row.get("link_id", ""): row for row in videos_meta if row.get("link_id")}
    meta_by_url = {row.get("url", ""): row for row in videos_meta if row.get("url")}

    max_link_id = max((int(row.get("link_id") or 0) for row in raw_links), default=0)
    imported_new_links = 0
    updated_existing_links = 0
    skipped_other_category = 0

    for record in records:
        category, subcategory = _guess_category(record.source_keyword)
        if scoped:
            category = scoped["category"]
            subcategory = scoped["subcategory"]
        preview = {
            "title": record.caption,
            "author": record.author_name,
            "hashtags": record.hashtags,
            "category": category,
            "subcategory": subcategory,
        }
        if product_id and not product_material_match(product_id, preview) and not material_dict_matches_product(preview, product_id):
            skipped_other_category += 1
            continue
        raw_row = raw_by_url.get(record.video_url)
        if raw_row is None:
            max_link_id += 1
            if not scoped:
                category, subcategory = _guess_category(record.source_keyword)
            raw_row = {
                "link_id": str(max_link_id),
                "url": record.video_url,
                "category": category,
                "platform": "tiktok",
                "subcategory": subcategory,
                "source": "tiktok_collector",
                "status": "pending",
                "notes": f"keyword:{record.source_keyword}",
                "added_at": _today_utc(),
            }
            raw_links.append(raw_row)
            raw_by_url[record.video_url] = raw_row
            imported_new_links += 1
        else:
            updated_existing_links += 1

        link_id = str(raw_row["link_id"])
        meta_row = meta_by_link_id.get(link_id) or meta_by_url.get(record.video_url)
        if meta_row is None:
            meta_row = {field: "" for field in VIDEO_META_FIELDS}
            videos_meta.append(meta_row)

        meta_row.update(
            {
                "link_id": link_id,
                "url": record.video_url,
                "video_id": record.video_id,
                "author": record.author_name,
                "author_url": record.author_url,
                "title": record.caption,
                "description": record.caption,
                "duration_sec": meta_row.get("duration_sec", ""),
                "view_count": meta_row.get("view_count", ""),
                "like_count": str(record.like_count),
                "comment_count": str(record.comment_count),
                "share_count": str(record.share_count),
                "hashtags": _hashtags_json(record.hashtags),
                "thumbnail_url": record.cover_url,
                "fetched_at": record.crawl_time,
                "fetch_status": "ok",
                "fetch_provider": "tiktok_collector_playwright",
                "error_message": "",
            }
        )
        meta_by_link_id[link_id] = meta_row
        meta_by_url[record.video_url] = meta_row

    raw_links.sort(key=lambda row: int(row.get("link_id") or 0))
    videos_meta.sort(key=lambda row: int(row.get("link_id") or 0))
    _write_csv(RAW_LINKS_CSV, raw_links, RAW_LINK_FIELDS)
    _write_csv(VIDEOS_META_CSV, videos_meta, VIDEO_META_FIELDS)

    if product_id:
        trim_material_library_to_product(product_id)

    return CollectorImportResult(
        total_collected=total_collected,
        total_cleaned=len(records),
        total_dropped=total_dropped,
        imported_new_links=imported_new_links,
        updated_existing_links=updated_existing_links,
        json_path=json_path,
        csv_path=csv_path,
        clean_json_path=clean_json_path,
        clean_csv_path=clean_csv_path,
        review_json_path=review_json_path,
        output_dir=output_dir,
    )


def run_collector_import(
    keywords: list[str],
    *,
    limit_per_keyword: int = 20,
    product_id: str = "",
) -> CollectorImportResult:
    service = TikTokCollectorService()
    request = CollectRequest(
        keywords=keywords,
        limit_per_keyword=limit_per_keyword,
        export_json=True,
        export_csv=True,
    )
    run = service.collect(request)
    return import_reviewed_records(
        run.response.clean_records,
        total_collected=run.response.total_records,
        total_dropped=run.response.dropped_records,
        json_path=str(run.json_file) if run.json_file else None,
        csv_path=str(run.csv_file) if run.csv_file else None,
        clean_json_path=str(run.clean_json_file) if run.clean_json_file else None,
        clean_csv_path=str(run.clean_csv_file) if run.clean_csv_file else None,
        review_json_path=str(run.review_json_file) if run.review_json_file else None,
        output_dir=str(service.settings.output_dir),
        product_id=product_id,
    )


def query_collector_database(
    *,
    q: str = "",
    source_keyword: str = "",
    processing_status: str = "",
    limit: int = 20,
) -> CollectorDatabaseQueryResult:
    service = TikTokCollectorService()
    if not service.db.enabled:
        return CollectorDatabaseQueryResult(db_enabled=False, total=0, items=[])

    repository = TikTokVideoRepository(service.db)
    total, records = repository.list_records(
        q=q,
        source_keyword=source_keyword,
        processing_status=processing_status,
        limit=limit,
    )
    return CollectorDatabaseQueryResult(
        db_enabled=True,
        total=total,
        items=[record.model_dump() for record in records],
    )


def collector_database_enabled() -> bool:
    service = TikTokCollectorService()
    return bool(service.db.enabled)


def sync_collector_database_to_workflow(
    *,
    q: str = "",
    source_keyword: str = "",
    processing_status: str = "",
    limit: int = 20,
    product_id: str = "",
) -> CollectorDatabaseSyncResult:
    service = TikTokCollectorService()
    if not service.db.enabled:
        return CollectorDatabaseSyncResult(
            db_enabled=False,
            queried_total=0,
            synced_count=0,
            imported_new_links=0,
            updated_existing_links=0,
        )

    repository = TikTokVideoRepository(service.db)
    total, records = repository.list_records(
        q=q,
        source_keyword=source_keyword,
        processing_status=processing_status,
        limit=limit,
    )
    reviewed_records = [
        ReviewedTikTokVideoRecord(
            **record.model_dump(),
            clean_status="kept",
            relevance_score=0,
            clean_reasons=["imported_from_mysql"],
        )
        for record in records
    ]
    imported = import_reviewed_records(
        reviewed_records,
        total_collected=len(reviewed_records),
        total_dropped=0,
        json_path=None,
        csv_path=None,
        clean_json_path=None,
        clean_csv_path=None,
        review_json_path=None,
        output_dir=str(service.settings.output_dir),
        product_id=product_id,
    )
    return CollectorDatabaseSyncResult(
        db_enabled=True,
        queried_total=total,
        synced_count=len(reviewed_records),
        imported_new_links=imported.imported_new_links,
        updated_existing_links=imported.updated_existing_links,
    )
