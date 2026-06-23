"""成稿库 / 反馈库 — 直接读取工作流根目录 JSON。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from paths import SCRIPT_TEMPLATES_CSV, WORKFLOW_ROOT

FINISHED_DIR = WORKFLOW_ROOT / "成稿库"
FEEDBACK_DIR = WORKFLOW_ROOT / "反馈库"


def _read_json_dir(folder: Path, sort_key: str) -> list[dict[str, Any]]:
    if not folder.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        try:
            items.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    items.sort(key=lambda row: row.get(sort_key, ""), reverse=True)
    return items


def list_finished() -> list[dict[str, Any]]:
    return _read_json_dir(FINISHED_DIR, "saved_at")


def list_feedback() -> list[dict[str, Any]]:
    return _read_json_dir(FEEDBACK_DIR, "updated_at")


def load_feedback(slug: str) -> dict[str, Any]:
    path = FEEDBACK_DIR / f"{slug}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_feedback(slug: str, updates: dict[str, Any]) -> dict[str, Any]:
    import sys

    olm = WORKFLOW_ROOT / "overseas-loc-mvp"
    if str(olm) not in sys.path:
        sys.path.insert(0, str(olm))
    # 子进程式隔离：直接写 JSON + 同步 CSV
    record = load_feedback(slug)
    if not record:
        raise ValueError("反馈记录不存在")
    if "manual_edits" in updates:
        record["manual_edits"] = str(updates["manual_edits"] or "").strip()
    if "adopted" in updates:
        adopted = str(updates["adopted"] or "").strip()
        if adopted not in {"待定", "已采纳", "未采纳", "修改后采纳"}:
            raise ValueError("adopted 须为：待定 / 已采纳 / 未采纳 / 修改后采纳")
        record["adopted"] = adopted
    if "notes" in updates:
        record["notes"] = str(updates["notes"] or "").strip()
    publish = updates.get("publish") or {}
    pub = record.setdefault("publish", {"views": "", "engagement": "", "notes": ""})
    for key in ("views", "engagement", "notes"):
        if key in publish:
            pub[key] = str(publish[key] or "").strip()
    from datetime import datetime, timezone

    record["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path = FEEDBACK_DIR / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _sync_feedback_csv(slug, record)
    return record


def _sync_feedback_csv(slug: str, record: dict[str, Any]) -> None:
    index = FEEDBACK_DIR / "反馈记录.csv"
    fields = [
        "slug", "link_id", "title", "updated_at", "manual_edits", "adopted",
        "publish_views", "publish_engagement", "publish_notes", "notes",
    ]
    rows: list[dict[str, str]] = []
    if index.exists():
        with index.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    rows = [r for r in rows if r.get("slug") != slug]
    publish = record.get("publish") or {}
    rows.append({
        "slug": slug,
        "link_id": str(record.get("link_id", "")),
        "title": str(record.get("title", "")),
        "updated_at": str(record.get("updated_at", "")),
        "manual_edits": str(record.get("manual_edits", "")),
        "adopted": str(record.get("adopted", "")),
        "publish_views": str(publish.get("views", "")),
        "publish_engagement": str(publish.get("engagement", "")),
        "publish_notes": str(publish.get("notes", "")),
        "notes": str(record.get("notes", "")),
    })
    rows.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    index.write_text("\ufeff" + buf.getvalue(), encoding="utf-8")


def load_templates() -> list[dict[str, str]]:
    if not SCRIPT_TEMPLATES_CSV.exists():
        return []
    with SCRIPT_TEMPLATES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))
