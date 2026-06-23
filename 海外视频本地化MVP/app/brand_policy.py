"""竞品品牌剥离 — 脚本只借鉴结构，输出统一为我方品牌。"""

from __future__ import annotations

import re
from typing import Any

OUR_BRAND = "熊猫布布"

# 常见竞品品牌/账号型关键词（口播与字幕中需替换或删除）
COMPETITOR_TERMS = (
    "momcozy",
    "baby brezza",
    "babybrezza",
    "bololo",
    "dr. brown",
    "dr browns",
    "drbrowns",
    "spectra",
    "medela",
    "willow",
    "elvie",
    "lansinoh",
    "philips avent",
    "babymoov",
    "the baby's brew",
    "tommee tippee",
    "munchkin",
)

PRODUCT_DISPLAY = {
    "便携恒温杯": "熊猫布布便携恒温杯",
    "吸奶器": "熊猫布布吸奶器",
}

# 素材 subcategory / category → 适用产品
MATERIAL_PRODUCT_LINES: dict[str, str] = {
    "便携恒温杯": "便携恒温杯",
    "bottle_warmer": "便携恒温杯",
    "breast_pump": "吸奶器",
    "吸奶器": "吸奶器",
}


def display_product_name(product_id: str, fallback: str = "") -> str:
    return PRODUCT_DISPLAY.get(product_id) or fallback or product_id


def _text_blob(material: dict[str, Any]) -> str:
    parts = [
        str(material.get("title") or ""),
        str(material.get("author") or ""),
        " ".join(material.get("hashtags") or []),
    ]
    analysis = material.get("analysis") or {}
    for key in ("hook_3s", "pain_points", "selling_points", "reusable_template"):
        parts.append(str(analysis.get(key) or ""))
    return " ".join(parts).lower()


_PUMP_HINTS = ("pump", "pumping", "breastpump", "flange", "lactation", "吸奶", "背奶")
_WARMER_HINTS = ("warmer", "bottlewarmer", "milkwarmer", "heater", "恒温", "暖奶", "heat milk")


def detect_content_line(material: dict[str, Any]) -> str:
    """从标题/话题/拆解推断内容品类（优先于种子链接上的 subcategory）。"""
    blob = _text_blob(material)
    has_pump = any(k in blob for k in _PUMP_HINTS)
    has_warmer = any(k in blob for k in _WARMER_HINTS)
    if has_pump and not has_warmer:
        return "吸奶器"
    if has_warmer and not has_pump:
        return "便携恒温杯"
    sub = str(material.get("subcategory") or "").strip()
    cat = str(material.get("category") or "").strip().lower()
    if sub in MATERIAL_PRODUCT_LINES:
        return MATERIAL_PRODUCT_LINES[sub]
    if cat in MATERIAL_PRODUCT_LINES:
        return MATERIAL_PRODUCT_LINES[cat]
    return ""


def material_product_line(material: dict[str, Any]) -> str:
    return detect_content_line(material)


def product_material_match(product_id: str, material: dict[str, Any]) -> bool:
    line = detect_content_line(material)
    if not line:
        return True
    return line == product_id


def sanitize_text(text: str, *, product_id: str) -> str:
    if not text:
        return text
    out = text
    our_product = display_product_name(product_id, OUR_BRAND)
    for term in COMPETITOR_TERMS:
        out = re.sub(re.escape(term), our_product, out, flags=re.IGNORECASE)
    # 去掉典型带货口令，保留结构描述
    out = re.sub(r"#\w+", "", out)
    out = re.sub(r"@\w+", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def sanitize_analysis(analysis: dict[str, str], product_id: str) -> dict[str, str]:
    if not analysis:
        return analysis
    cleaned = dict(analysis)
    for key in (
        "hook_3s",
        "pain_points",
        "selling_points",
        "scenes",
        "video_structure",
        "subtitle_layout",
        "cta",
        "reusable_template",
    ):
        if cleaned.get(key):
            cleaned[key] = sanitize_text(str(cleaned[key]), product_id=product_id)
    note = (
        f"【借鉴说明】仅复用本条竞品的钩子/节奏/分镜结构，"
        f"成片统一露出 {display_product_name(product_id)}，不出现竞品品牌与链接。"
    )
    cleaned["reusable_template"] = f"{cleaned.get('reusable_template', '')} {note}".strip()
    return cleaned
