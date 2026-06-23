from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import PRODUCT_MATERIALS_CSV

PILOT_PRODUCT_IDS = ("便携恒温杯", "吸奶器")

PRODUCT_FIELDS = [
    "product_id",
    "product_name",
    "target_audience",
    "core_selling_points",
    "pain_points",
    "usage_scenarios",
    "forbidden_terms",
    "price_range",
    "competitor_ref",
    "source_path",
    "synced_at",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=PRODUCT_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in PRODUCT_FIELDS})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff" + buf.getvalue(), encoding="utf-8")


def list_products() -> list[dict[str, str]]:
    rows = _read_csv(PRODUCT_MATERIALS_CSV)
    return [r for r in rows if r.get("product_id") in PILOT_PRODUCT_IDS]


def get_product(product_id: str) -> dict[str, str] | None:
    for row in list_products():
        if row.get("product_id") == product_id:
            return row
    return None


def update_product(product_id: str, updates: dict[str, str]) -> dict[str, str]:
    rows = list_products()
    found = False
    editable = set(PRODUCT_FIELDS) - {"product_id", "source_path", "synced_at"}
    for row in rows:
        if row.get("product_id") != product_id:
            continue
        for key, value in updates.items():
            if key in editable:
                row[key] = str(value or "")
        row["synced_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        found = True
        break
    if not found:
        raise ValueError("产品不存在")
    _write_csv(PRODUCT_MATERIALS_CSV, rows)
    return get_product(product_id) or {}
