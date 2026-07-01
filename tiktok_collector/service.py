from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from .cleaner import review_records
from .config import CollectorSettings, load_settings
from .db import DatabaseManager
from .exporters import export_csv, export_json, export_review_json
from .models import CollectRequest, CollectResponse, CollectRunResult, ExportArtifacts, TikTokVideoRecord
from .repository import TikTokVideoRepository
from .scraper import TikTokScraper


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "keyword"


class TikTokCollectorService:
    def __init__(self, settings: CollectorSettings | None = None) -> None:
        self.settings = settings or load_settings()
        self.scraper = TikTokScraper(self.settings)
        self.db = DatabaseManager(self.settings)
        self.repository = TikTokVideoRepository(self.db)

    def collect(self, request: CollectRequest) -> CollectRunResult:
        started_at = _utc_now()
        records: list[TikTokVideoRecord] = []
        limit = min(request.limit_per_keyword, self.settings.max_results)
        for keyword in request.keywords:
            records.extend(self.scraper.collect_keyword(keyword, limit=limit))
        if self.db.enabled:
            self.db.init_db()
        db_upserted = self.repository.upsert_records(records)
        clean_records, dropped_records = review_records(records, min_score=self.settings.clean_min_score)
        json_file: Path | None = None
        csv_file: Path | None = None
        clean_json_file: Path | None = None
        clean_csv_file: Path | None = None
        review_json_file: Path | None = None
        if request.export_json or request.export_csv:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            keyword_stub = _slugify("-".join(request.keywords[:3]))
            raw_base = self.settings.output_dir / f"{stamp}_{keyword_stub}"
            clean_dir = self.settings.output_dir / "clean"
            clean_base = clean_dir / f"{stamp}_{keyword_stub}"
            if request.export_json:
                json_file = raw_base.with_suffix(".json")
                export_json(json_file, records)
                clean_json_file = clean_base.with_suffix(".json")
                export_json(clean_json_file, clean_records)
                review_json_file = clean_base.with_name(f"{clean_base.name}_review").with_suffix(".json")
                export_review_json(review_json_file, clean_records, dropped_records)
            if request.export_csv:
                csv_file = raw_base.with_suffix(".csv")
                export_csv(csv_file, records)
                clean_csv_file = clean_base.with_suffix(".csv")
                export_csv(clean_csv_file, clean_records)
        response = CollectResponse(
            keywords=request.keywords,
            limit_per_keyword=limit,
            total_records=len(records),
            kept_records=len(clean_records),
            dropped_records=len(dropped_records),
            records=records,
            clean_records=clean_records,
            dropped_items=dropped_records,
            artifacts=ExportArtifacts(
                json_path=str(json_file) if json_file else None,
                csv_path=str(csv_file) if csv_file else None,
                clean_json_path=str(clean_json_file) if clean_json_file else None,
                clean_csv_path=str(clean_csv_file) if clean_csv_file else None,
                review_json_path=str(review_json_file) if review_json_file else None,
            ),
            started_at=started_at,
            finished_at=_utc_now(),
            db_enabled=self.db.enabled,
            db_upserted=db_upserted,
        )
        return CollectRunResult(
            response=response,
            json_file=json_file,
            csv_file=csv_file,
            clean_json_file=clean_json_file,
            clean_csv_file=clean_csv_file,
            review_json_file=review_json_file,
        )
