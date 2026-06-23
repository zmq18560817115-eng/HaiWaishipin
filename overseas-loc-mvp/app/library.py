from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .storage import atomic_write, read_json, read_yaml, write_json
from .workflow import USER_DELIVERABLES, utc_now

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
FINISHED_DIR = WORKFLOW_ROOT / "成稿库"
FEEDBACK_DIR = WORKFLOW_ROOT / "反馈库"
COMPETITOR_SCRIPTS = WORKFLOW_ROOT / "海外视频本地化MVP" / "生成脚本"

FINISHED_INDEX = FINISHED_DIR / "成稿索引.csv"
FEEDBACK_INDEX = FEEDBACK_DIR / "反馈记录.csv"

FINISHED_FIELDS = [
    "slug",
    "link_id",
    "title",
    "saved_at",
    "script_ref",
    "video_refs",
    "template_id",
    "template_label",
    "product_id",
    "product_name",
    "delivery_files",
    "source_tiktok_url",
]

FEEDBACK_FIELDS = [
    "slug",
    "link_id",
    "title",
    "updated_at",
    "manual_edits",
    "adopted",
    "publish_views",
    "publish_engagement",
    "publish_notes",
    "notes",
]


def _ensure_dirs() -> None:
    FINISHED_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _read_csv_index(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv_index(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    buffer_rows: list[dict[str, str]] = []
    for row in rows:
        buffer_rows.append({key: str(row.get(key, "")) for key in fields})
    lines: list[str] = []
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(buffer_rows)
    atomic_write(path, "\ufeff" + buf.getvalue())


def _video_refs(project: Path) -> list[str]:
    refs: list[str] = []
    broll = project / "broll"
    if broll.exists():
        for mp4 in sorted(broll.glob("shot-*.mp4")):
            refs.append(mp4.relative_to(project).as_posix())
    return refs


def _script_refs(project: Path, link_id: str | int | None) -> dict[str, str]:
    refs: dict[str, str] = {}
    pack = project / "script-pack.json"
    if pack.exists():
        refs["script_pack"] = pack.relative_to(project).as_posix()
    delivery = project / "交付脚本包.json"
    if delivery.exists():
        refs["delivery_pack"] = delivery.relative_to(project).as_posix()
    if link_id:
        gen_dir = COMPETITOR_SCRIPTS / str(link_id)
        if gen_dir.exists():
            refs["generated_dir"] = str(gen_dir)
            for name in ("script-pack.json", "script-pack.md"):
                path = gen_dir / name
                if path.exists():
                    refs[name.removesuffix(".json").replace("-", "_")] = str(path)
    return refs


def _template_info(project: Path, link_id: str | int | None) -> dict[str, str]:
    pack_path = project / "script-pack.json"
    if pack_path.exists():
        try:
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            inputs = pack.get("inputs") or {}
            if inputs.get("template_id") or inputs.get("template"):
                return {
                    "template_id": str(inputs.get("template_id", "")),
                    "template_label": str(inputs.get("template", "")),
                }
            meta = pack.get("meta") or {}
            if meta.get("template_id"):
                return {
                    "template_id": str(meta.get("template_id", "")),
                    "template_label": str(meta.get("template_label", "")),
                }
        except (json.JSONDecodeError, OSError):
            pack = {}
    if link_id:
        snap = COMPETITOR_SCRIPTS / str(link_id) / "analysis-snapshot.json"
        if snap.exists():
            try:
                analysis = json.loads(snap.read_text(encoding="utf-8"))
                return {
                    "template_id": analysis.get("reusable_template", "")[:40],
                    "template_label": analysis.get("reusable_template", "")[:80],
                }
            except (json.JSONDecodeError, OSError):
                pass
    analysis_path = project / "video-analysis.json"
    if analysis_path.exists():
        analysis = read_json(analysis_path)
        return {
            "template_id": str(analysis.get("reusable_template", ""))[:40],
            "template_label": str(analysis.get("reusable_template", ""))[:80],
        }
    return {"template_id": "", "template_label": ""}


def _product_info(project: Path, link_id: str | int | None) -> dict[str, str]:
    if link_id:
        pack_path = COMPETITOR_SCRIPTS / str(link_id) / "script-pack.json"
        if pack_path.exists():
            try:
                data = json.loads(pack_path.read_text(encoding="utf-8"))
                payload = data.get("payload") or data.get("pack") or data
                return {
                    "product_id": str(payload.get("product_id", "")),
                    "product_name": str(payload.get("product_name", "")),
                }
            except (json.JSONDecodeError, OSError):
                pass
    return {"product_id": "", "product_name": ""}


def collect_finished_record(project: Path) -> dict[str, Any]:
    brief_path = project / "localization-brief.yaml"
    brief = read_yaml(brief_path) if brief_path.exists() else {}
    link_id = brief.get("source_link_id", "")
    slug = project.name
    template = _template_info(project, link_id)
    product = _product_info(project, link_id)
    pack_meta = _pack_meta_title(project, brief)

    delivery_files = [
        name for name in USER_DELIVERABLES if (project / name).exists()
    ]

    return {
        "slug": slug,
        "link_id": str(link_id or ""),
        "title": pack_meta,
        "saved_at": utc_now(),
        "script_refs": _script_refs(project, link_id),
        "video_refs": _video_refs(project),
        "template_id": template["template_id"],
        "template_label": template["template_label"],
        "product_id": product["product_id"] or brief.get("sku", ""),
        "product_name": product["product_name"],
        "delivery_files": delivery_files,
        "source_tiktok_url": brief.get("source_tiktok_url", ""),
        "brief": {
            "sku": brief.get("sku", ""),
            "theme": brief.get("theme", ""),
            "target_country": brief.get("target_country", ""),
        },
    }


def _pack_meta_title(project: Path, brief: dict[str, Any]) -> str:
    from .workflow import _load_pack

    pack = _load_pack(project)
    title = pack.get("title")
    if title:
        return str(title)
    return str(brief.get("theme") or project.name)


def save_finished_record(project: Path) -> dict[str, Any]:
    _ensure_dirs()
    record = collect_finished_record(project)
    slug = record["slug"]
    write_json(FINISHED_DIR / f"{slug}.json", record)

    rows = [row for row in _read_csv_index(FINISHED_INDEX) if row.get("slug") != slug]
    rows.append(
        {
            "slug": slug,
            "link_id": record["link_id"],
            "title": record["title"],
            "saved_at": record["saved_at"],
            "script_ref": json.dumps(record["script_refs"], ensure_ascii=False),
            "video_refs": ";".join(record["video_refs"]),
            "template_id": record["template_id"],
            "template_label": record["template_label"],
            "product_id": record["product_id"],
            "product_name": record["product_name"],
            "delivery_files": ";".join(record["delivery_files"]),
            "source_tiktok_url": record["source_tiktok_url"],
        }
    )
    rows.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    _write_csv_index(FINISHED_INDEX, FINISHED_FIELDS, rows)

    feedback_path = FEEDBACK_DIR / f"{slug}.json"
    if not feedback_path.exists():
        init_feedback_record(project, record)
    else:
        _sync_feedback_index(slug)

    return record


def init_feedback_record(project: Path, finished: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_dirs()
    finished = finished or collect_finished_record(project)
    slug = finished["slug"]
    record = {
        "slug": slug,
        "link_id": finished.get("link_id", ""),
        "title": finished.get("title", slug),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "manual_edits": "",
        "adopted": "待定",
        "publish": {
            "views": "",
            "engagement": "",
            "notes": "",
        },
        "notes": "交付后由剪辑/运营填写人工修改与投放数据，用于反哺模型",
    }
    write_json(FEEDBACK_DIR / f"{slug}.json", record)
    _sync_feedback_index(slug)
    return record


def load_feedback(slug: str) -> dict[str, Any]:
    path = FEEDBACK_DIR / f"{slug}.json"
    if not path.exists():
        project = Path(__file__).resolve().parents[1] / "runs" / slug
        if project.exists():
            return init_feedback_record(project)
        return {}
    return read_json(path)


def update_feedback(slug: str, updates: dict[str, Any]) -> dict[str, Any]:
    _ensure_dirs()
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
    record["updated_at"] = utc_now()
    write_json(FEEDBACK_DIR / f"{slug}.json", record)
    _sync_feedback_index(slug)
    return record


def _sync_feedback_index(slug: str) -> None:
    path = FEEDBACK_DIR / f"{slug}.json"
    if not path.exists():
        return
    record = read_json(path)
    publish = record.get("publish") or {}
    rows = [row for row in _read_csv_index(FEEDBACK_INDEX) if row.get("slug") != slug]
    rows.append(
        {
            "slug": slug,
            "link_id": record.get("link_id", ""),
            "title": record.get("title", ""),
            "updated_at": record.get("updated_at", ""),
            "manual_edits": record.get("manual_edits", ""),
            "adopted": record.get("adopted", ""),
            "publish_views": publish.get("views", ""),
            "publish_engagement": publish.get("engagement", ""),
            "publish_notes": publish.get("notes", ""),
            "notes": record.get("notes", ""),
        }
    )
    rows.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    _write_csv_index(FEEDBACK_INDEX, FEEDBACK_FIELDS, rows)


def list_finished() -> list[dict[str, Any]]:
    _ensure_dirs()
    items: list[dict[str, Any]] = []
    for path in sorted(FINISHED_DIR.glob("*.json")):
        try:
            items.append(read_json(path))
        except (json.JSONDecodeError, OSError):
            continue
    items.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    return items


def list_feedback() -> list[dict[str, Any]]:
    _ensure_dirs()
    items: list[dict[str, Any]] = []
    for path in sorted(FEEDBACK_DIR.glob("*.json")):
        try:
            items.append(read_json(path))
        except (json.JSONDecodeError, OSError):
            continue
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return items
