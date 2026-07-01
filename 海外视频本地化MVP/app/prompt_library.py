"""动态提示词库 — 反推、反馈与手动条目统一存储。"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from paths import PROMPT_LIBRARY_JSON

from .brand_policy import detect_content_line


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slug(text: str, limit: int = 48) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", (text or "").strip()).strip("-")
    return (s[:limit] or "prompt").lower()


def _load() -> list[dict[str, Any]]:
    if not PROMPT_LIBRARY_JSON.exists():
        return []
    try:
        data = json.loads(PROMPT_LIBRARY_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("items") or [])
    return []


def _save(items: list[dict[str, Any]]) -> None:
    PROMPT_LIBRARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "updated_at": _utc(), "items": items}
    PROMPT_LIBRARY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_prompts(
    *,
    product_id: str = "",
    content_line: str = "",
    source: str = "",
    reverse_type: str = "",
    prompt_type: str = "",
    limit: int = 200,
) -> list[dict[str, Any]]:
    ensure_default_presets()
    items = _load()
    out: list[dict[str, Any]] = []
    for row in items:
        if product_id and str(row.get("product_id") or "") not in ("", product_id):
            continue
        if content_line and str(row.get("content_line") or "") not in ("", content_line):
            continue
        if source and row.get("source") != source:
            continue
        if reverse_type and row.get("reverse_type") != reverse_type:
            continue
        if prompt_type and row.get("prompt_type") != prompt_type:
            continue
        out.append(row)
    out.sort(key=_sort_key)
    return out[: max(1, limit)]


def _entry_key(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "")
    if source == "preset":
        return f"preset|{row.get('prompt_type') or _slug(str(row.get('label') or ''), 32)}|"
    return "|".join(
        [
            source,
            str(row.get("reverse_type") or ""),
            str(row.get("link_id") or ""),
            str(row.get("shot_index") if row.get("shot_index") is not None else ""),
            _slug(str(row.get("label") or ""), 32),
        ]
    )


DEFAULT_PROMPT_PRESETS: list[dict[str, Any]] = [
    {
        "prompt_type": "scene-use",
        "sort_order": 1,
        "label": "场景种草",
        "sub": "真实场景 · 卖点展示",
        "prompt_text": (
            "竖屏 9:16，真实育儿日常场景（客厅或外出休息区）。妈妈从妈咪包取出便携恒温杯，"
            "倒入温水后特写杯身数字屏稳定在约 98°F（37°C），口播自然讲解「外出也能随时冲奶」。"
            "镜头节奏紧凑：中景使用→特写温度屏→产品入画，突出便携、恒温、一键操作。"
            "禁止蒸汽、沸腾、奶液喷溅或夸张热雾画面。"
        ),
    },
    {
        "prompt_type": "pain-hook",
        "sort_order": 2,
        "label": "痛点钩子",
        "sub": "3秒钩子 · 问题切入",
        "prompt_text": (
            "开场 3 秒钩子：宝宝饿哭/户外找不到合适水温的焦虑特写，字幕点出「凉水冲奶、保温难」痛点。"
            "随后便携恒温杯入画解决问题：加水→设定温度→屏显约 98°F 稳定。"
            "结构：痛点场景→产品介入→快速演示→效果确认→软性引导关注。"
            "口播口语化、镜头短平快，禁止蒸汽与沸腾夸张表现。"
        ),
    },
    {
        "prompt_type": "unbox",
        "sort_order": 3,
        "label": "开箱测评",
        "sub": "开箱 → 演示 → 推荐",
        "prompt_text": (
            "开箱测评结构：包装开箱→配件陈列→通电/setup 演示→外出场景实测→总结推荐。"
            "重点展示杯身做工、数字温控屏、续航与 USB-C 充电，实测冲奶/保温流程，"
            "强调「便携、恒温、外出友好」。结尾口播总结 2–3 个核心卖点。"
            "画面真实明亮，禁止蒸汽、沸腾、夸张热雾。"
        ),
    },
    {
        "prompt_type": "demo-proof",
        "sort_order": 4,
        "label": "功能演示",
        "sub": "操作特写 · 效果验证",
        "prompt_text": (
            "近景跟拍操作：单手开盖、加水、设定目标温度，特写屏幕从室温升至并稳定在约 98°F。"
            "穿插中景展示杯身尺寸与妈咪包收纳，字幕标注「恒温」「便携」「续航」。"
            "结尾对比使用前（凉水奶瓶）与使用后（温度适宜）的安心表情。"
            "禁止蒸汽、沸腾、液体飞溅。"
        ),
    },
    {
        "prompt_type": "travel-test",
        "sort_order": 5,
        "label": "出行实测",
        "sub": "车载 / 户外 · 真实续航",
        "prompt_text": (
            "出行实测：车载或公园长椅场景，家长带娃外出，从包中取出恒温杯完成一次冲奶/保温流程。"
            "展示 USB-C 充电、电量指示与长时间保温能力，口播强调「7 小时续航」「出门必备」。"
            "镜头含环境建立镜头+产品操作特写，氛围生活化、真实可信。"
            "禁止蒸汽、夸张热力特效。"
        ),
    },
    {
        "prompt_type": "soft-cta",
        "sort_order": 6,
        "label": "软性种草",
        "sub": "生活方式 · 温和推荐",
        "prompt_text": (
            "生活方式软性种草：清晨/午后育儿片段，恒温杯作为背景道具自然出现，"
            "妈妈从容冲奶、宝宝满足饮用。旁白或字幕温和推荐「新手爸妈外出必备」。"
            "色调温暖、节奏舒缓，1–2 次产品特写即可，避免硬广口吻。"
            "温度展示约 98°F，禁止蒸汽与沸腾画面。"
        ),
    },
]


def ensure_default_presets() -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for spec in DEFAULT_PROMPT_PRESETS:
        entry: dict[str, Any] = {
            "source": "preset",
            "prompt_type": spec["prompt_type"],
            "label": spec["label"],
            "sub": spec.get("sub", ""),
            "prompt_text": spec["prompt_text"],
            "prompt_text_en": spec.get("prompt_text_en", ""),
            "product_id": "",
            "content_line": "",
            "sort_order": spec.get("sort_order", 99),
            "tags": ["preset", spec["prompt_type"]],
            "prompt_id": f"pl-preset-{spec['prompt_type']}",
        }
        saved.append(upsert_prompt(entry))
    return saved


def _sort_key(row: dict[str, Any]) -> tuple:
    src = str(row.get("source") or "")
    if src == "preset":
        return (0, int(row.get("sort_order") or 99), "")
    return (1, -int(row.get("usage_count") or 0), str(row.get("updated_at") or ""))


def upsert_prompt(entry: dict[str, Any]) -> dict[str, Any]:
    items = _load()
    now = _utc()
    entry = dict(entry)
    key = _entry_key(entry)
    existing = next((r for r in items if r.get("_key") == key), None)
    if existing:
        existing.update(
            {
                k: v
                for k, v in entry.items()
                if k not in ("prompt_id", "created_at", "usage_count", "_key")
            }
        )
        existing["updated_at"] = now
        _save(items)
        return existing

    entry.setdefault("prompt_id", f"pl-{_slug(entry.get('label', ''), 20)}-{uuid.uuid4().hex[:8]}")
    entry.setdefault("usage_count", 0)
    entry.setdefault("created_at", now)
    entry["updated_at"] = now
    entry["_key"] = key
    items.append(entry)
    _save(items)
    return entry


def upsert_many(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for entry in entries:
        if entry.get("prompt_text") or entry.get("prompt_text_en"):
            saved.append(upsert_prompt(entry))
    return saved


def record_usage(prompt_id: str) -> dict[str, Any] | None:
    items = _load()
    for row in items:
        if row.get("prompt_id") == prompt_id:
            row["usage_count"] = int(row.get("usage_count") or 0) + 1
            row["last_used_at"] = _utc()
            row["updated_at"] = row["last_used_at"]
            _save(items)
            return row
    return None


def material_content_line(material: dict[str, Any]) -> str:
    return detect_content_line(material) or str(material.get("subcategory") or "")
