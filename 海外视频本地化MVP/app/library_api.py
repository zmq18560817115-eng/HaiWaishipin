"""成稿库 / 反馈库 — 直接读取工作流根目录 JSON。"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from paths import (
    FEEDBACK_LIBRARY_DIR,
    FINISHED_LIBRARY_DIR,
    GENERATED_SCRIPTS_DIR,
    OVERSEAS_RUNS_DIR,
    SCRIPT_TEMPLATES_CSV,
    WORKFLOW_ROOT,
)

from .feedback_tags import ISSUE_TAG_IDS

FINISHED_DIR = FINISHED_LIBRARY_DIR
FEEDBACK_DIR = FEEDBACK_LIBRARY_DIR


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
    return [_normalize_feedback_record(row) for row in _read_json_dir(FEEDBACK_DIR, "updated_at")]


def load_feedback(slug: str) -> dict[str, Any]:
    path = FEEDBACK_DIR / f"{slug}.json"
    if not path.exists():
        return {}
    record = json.loads(path.read_text(encoding="utf-8"))
    return _normalize_feedback_record(record)


def _load_scenario_tags_for_slug(slug: str, link_id: str = "") -> list[str]:
    proj = OVERSEAS_RUNS_DIR / slug
    brief_path = proj / "localization-brief.yaml"
    if brief_path.is_file():
        try:
            import yaml

            brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
            tags = brief.get("scenario_tags") or []
            if tags:
                return [str(t) for t in tags]
        except Exception:
            pass
    lid = str(link_id or "").strip()
    if not lid and slug.startswith("ref-"):
        lid = slug.replace("ref-", "").lstrip("0") or "0"
    if lid:
        pack_path = GENERATED_SCRIPTS_DIR / lid / "script-pack.json"
        if pack_path.is_file():
            try:
                data = json.loads(pack_path.read_text(encoding="utf-8"))
                payload = data.get("payload") or {}
                tags = payload.get("scenario_tags") or []
                if tags:
                    return [str(t) for t in tags]
                market = (data.get("pack") or {}).get("inputs", {}).get("market") or {}
                tags = market.get("scenario_tags") or []
                if tags:
                    return [str(t) for t in tags]
            except (json.JSONDecodeError, OSError):
                pass
    return []


def _feedback_review_done(record: dict[str, Any]) -> bool:
    if str(record.get("review_status") or "") == "done":
        return True
    if str(record.get("feedback_reviewed_at") or "").strip():
        return True
    if str(record.get("manual_edits") or "").strip():
        return True
    if record.get("issue_tags"):
        return True
    if str(record.get("adopted") or "") not in ("", "待定"):
        return True
    pub = record.get("publish") or {}
    if any(str(pub.get(k) or "").strip() for k in ("views", "engagement", "notes")):
        return True
    return False


def _normalize_feedback_record(record: dict[str, Any]) -> dict[str, Any]:
    slug = str(record.get("slug") or "")
    if slug:
        finished_path = FINISHED_DIR / f"{slug}.json"
        if finished_path.is_file():
            try:
                finished = json.loads(finished_path.read_text(encoding="utf-8"))
                if not record.get("product_id"):
                    record["product_id"] = finished.get("product_id") or (finished.get("brief") or {}).get("sku", "")
                if not record.get("template_id"):
                    record["template_id"] = finished.get("template_id", "")
                if not record.get("template_label"):
                    record["template_label"] = finished.get("template_label", "")
            except (json.JSONDecodeError, OSError):
                pass
        if not record.get("scenario_tags"):
            record["scenario_tags"] = _load_scenario_tags_for_slug(slug, str(record.get("link_id") or ""))
    tags = record.get("issue_tags")
    if not isinstance(tags, list):
        record["issue_tags"] = []
    else:
        record["issue_tags"] = [t for t in tags if t in ISSUE_TAG_IDS]
    record["review_done"] = _feedback_review_done(record)
    return record


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
    if "issue_tags" in updates:
        raw = updates.get("issue_tags") or []
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(",") if x.strip()]
        record["issue_tags"] = [t for t in raw if t in ISSUE_TAG_IDS]
    publish = updates.get("publish") or {}
    pub = record.setdefault("publish", {"views": "", "engagement": "", "notes": ""})
    for key in ("views", "engagement", "notes"):
        if key in publish:
            pub[key] = str(publish[key] or "").strip()
    from datetime import datetime, timezone

    record["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    record["review_status"] = "done"
    record["feedback_reviewed_at"] = record["updated_at"]
    record = _normalize_feedback_record(record)
    path = FEEDBACK_DIR / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    _sync_feedback_csv(slug, record)
    return record


def _sync_feedback_csv(slug: str, record: dict[str, Any]) -> None:
    index = FEEDBACK_DIR / "反馈记录.csv"
    fields = [
        "slug", "link_id", "title", "product_id", "updated_at", "review_status",
        "issue_tags", "manual_edits", "adopted",
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
        "product_id": str(record.get("product_id", "")),
        "updated_at": str(record.get("updated_at", "")),
        "review_status": str(record.get("review_status", "")),
        "issue_tags": ",".join(record.get("issue_tags") or []),
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
