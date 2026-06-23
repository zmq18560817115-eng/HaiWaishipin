"""从 DS223 Obsidian 知识库同步产品资料 → product_materials。"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from paths import (
    DS223_PRODUCTS_ROOT,
    PRODUCT_MATERIALS_CSV,
    PRODUCT_MATERIALS_DIR,
    WORKFLOW_ROOT,
)

LOCAL_PRODUCT_ROOTS = [
    WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "products",
]
LOCAL_COMPLIANCE_ROOTS = [
    WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "compliance",
    WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "processes",
]

# 试点试运行：产品库仅保留两款主产品
PILOT_PRODUCT_IDS = ("便携恒温杯", "吸奶器")
PILOT_PRODUCT_FILES = ("便携恒温杯", "吸奶器")

# DS223 目录含会议纪要/项目动态；仅同步正式产品资料
PRODUCT_DOC_INCLUDE = (
    "产品介绍",
    "品牌信息",
    "品牌手册",
    "竞品对比",
    "技术原理",
    "泌乳知识",
    "便携恒温杯",
    "恒温杯",
)
PRODUCT_DOC_EXCLUDE = (
    "agent",
    "笔记创作",
    "推进",
    "动态",
    "qa",
    "618",
    "评审助手",
    "模型切换",
    "项目关键文档",
    "詹少珠",
    "怎么选奶瓶",
    "羊脂膏",
    "奶瓶1v1",
    "奶瓶产品",
    "文案",
    "pro-vs-plus",
    "小红书",
)

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

SECTION_TO_FIELD: list[tuple[str, str]] = [
    ("适用人群", "target_audience"),
    ("目标用户", "target_audience"),
    ("用户画像", "target_audience"),
    ("核心卖点", "core_selling_points"),
    ("卖点", "core_selling_points"),
    ("feature", "core_selling_points"),
    ("advantage", "core_selling_points"),
    ("benefit", "core_selling_points"),
    ("fab", "core_selling_points"),
    ("产品特点", "core_selling_points"),
    ("用户痛点", "pain_points"),
    ("痛点", "pain_points"),
    ("使用场景", "usage_scenarios"),
    ("场景", "usage_scenarios"),
    ("禁用", "forbidden_terms"),
    ("禁词", "forbidden_terms"),
    ("风险", "forbidden_terms"),
    ("价格", "price_range"),
    ("竞品", "competitor_ref"),
    ("对比", "competitor_ref"),
    ("品牌", "competitor_ref"),
    ("原理", "core_selling_points"),
    ("技术", "core_selling_points"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if re.search(r"[a-z]", s):
        return s[:48] or "product"
    return f"product-{abs(hash(name)) % 10000:04d}"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2]


def _section_map(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "_intro"
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            if buf:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if buf:
        sections[current] = "\n".join(buf).strip()
    return sections


def _bullets(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*•]\s*", "", line)
        line = re.sub(r"^\d+\.\s*", "", line)
        if line.startswith("|"):
            continue
        lines.append(line)
    return "；".join(lines[:12])


def _match_field(section_title: str) -> str | None:
    low = section_title.lower()
    for key, field in SECTION_TO_FIELD:
        if key.lower() in low:
            return field
    return None


def _collect_forbidden() -> str:
    terms: list[str] = []
    for root in LOCAL_COMPLIANCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                if line.strip().startswith("|") and "---" not in line:
                    cols = [c.strip() for c in line.strip("|").split("|")]
                    if cols and cols[0] and cols[0] not in ("禁止 EN", "禁止表述"):
                        terms.append(cols[0])
                elif line.strip().startswith("- ") and re.search(r"[a-zA-Z]", line):
                    terms.append(line.strip()[2:])
    return "；".join(dict.fromkeys(terms))


def parse_product_md(path: Path, global_forbidden: str) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    sections = _section_map(body)
    title = str(meta.get("title") or path.stem)
    product_name = title.split("·")[0].strip() if "·" in title else title
    stem = path.stem
    if stem == "吸奶器" or "吸奶器" in product_name or "panda-bubu" in stem.lower():
        product_id = "吸奶器"
        product_name = "熊猫布布吸奶器"
    elif stem == "便携恒温杯" or "恒温杯" in product_name:
        product_id = "便携恒温杯"
        product_name = "便携恒温杯"
    else:
        return None

    row: dict[str, str] = {
        "product_id": product_id,
        "product_name": product_name,
        "target_audience": "",
        "core_selling_points": "",
        "pain_points": "",
        "usage_scenarios": "",
        "forbidden_terms": global_forbidden,
        "price_range": "",
        "competitor_ref": "",
        "source_path": str(path),
        "synced_at": utc_now(),
    }

    for sec_title, content in sections.items():
        field = _match_field(sec_title)
        if not field or not content:
            continue
        chunk = _bullets(content)
        if row[field]:
            row[field] += "；" + chunk
        else:
            row[field] = chunk

    if "恒温杯" in product_name or "暖奶" in product_name:
        if not row["target_audience"]:
            row["target_audience"] = "0-12月新手爸妈；夜奶/外出行程家庭；瓶喂与混合喂养妈妈"
        if not row["usage_scenarios"]:
            row["usage_scenarios"] = "夜间卧室喂奶；车内杯架；机场旅途；公园遛娃；办公室背奶"
        if not row["pain_points"]:
            row["pain_points"] = "外出没热水；加热太慢；温度不均；传统暖奶器不便携；夜喂等待久"
    elif "吸奶器" in product_name or "panda" in product_name.lower():
        if not row["target_audience"]:
            row["target_audience"] = "0-6月新手妈妈；背奶职场妈妈；夜间吸奶人群"
        if not row["usage_scenarios"]:
            row["usage_scenarios"] = "夜间吸奶；背奶通勤；居家哺乳角；办公室隐蔽吸奶"
        if not row["pain_points"]:
            row["pain_points"] = "护罩尺寸不合；吸力不适；清洗繁琐；夜间噪音打扰；外出不便"

    if "竞品" in path.stem or "对比" in path.stem:
        row["competitor_ref"] = row.get("competitor_ref") or _bullets(body)[:500]

    if "品牌" in path.stem and not row["competitor_ref"]:
        row["competitor_ref"] = "Momcozy、Spectra、Medela、Willow、Elvie 等（详见竞品对比文档）"

    return row


def _is_local_product_doc(path: Path) -> bool:
    return any(path.is_relative_to(root) for root in LOCAL_PRODUCT_ROOTS if root.exists())


def _is_product_doc(path: Path) -> bool:
    """正式产品资料：本地 knowledge/products 全收；DS223 按关键词白名单。"""
    if _is_local_product_doc(path):
        return True
    stem = path.stem.lower()
    if any(x.lower() in stem for x in PRODUCT_DOC_EXCLUDE):
        return False
    return any(x.lower() in stem for x in PRODUCT_DOC_INCLUDE)


def discover_sources() -> tuple[list[Path], str]:
    """试点模式：只从本地 knowledge/products 读取两款主产品。"""
    files: list[Path] = []
    for root in LOCAL_PRODUCT_ROOTS:
        if not root.exists():
            continue
        for stem in PILOT_PRODUCT_FILES:
            path = root / f"{stem}.md"
            if path.exists():
                files.append(path)
    if not files:
        raise FileNotFoundError(
            f"未找到试点产品资料，请确认存在：{', '.join(f'{s}.md' for s in PILOT_PRODUCT_FILES)}"
        )
    names = "、".join(PILOT_PRODUCT_FILES)
    return files, f"试点产品 {len(files)} 款（{names}）"


def sync_products() -> tuple[list[dict[str, str]], str]:
    global_forbidden = _collect_forbidden()
    sources, status = discover_sources()
    if not sources:
        raise FileNotFoundError("未找到产品资料。请连接 DS223 或检查本地 knowledge/products/")

    rows: list[dict[str, str]] = []
    for path in sources:
        try:
            row = parse_product_md(path, global_forbidden)
            if row:
                rows.append(row)
        except OSError:
            continue

    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        pid = row["product_id"]
        if pid not in PILOT_PRODUCT_IDS:
            continue
        if pid not in by_id:
            by_id[pid] = row
            continue
        for field in PRODUCT_FIELDS:
            if field in ("product_id", "product_name", "source_path", "synced_at"):
                continue
            if row.get(field) and row[field] not in (by_id[pid].get(field) or ""):
                by_id[pid][field] = (by_id[pid].get(field) or "") + "；" + row[field]

    merged = [by_id[pid] for pid in PILOT_PRODUCT_IDS if pid in by_id]

    PRODUCT_MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    keep_ids = {row["product_id"] for row in merged}
    for old in PRODUCT_MATERIALS_DIR.glob("*.md"):
        if old.stem not in keep_ids:
            old.unlink(missing_ok=True)
    for row in merged:
        md = (
            f"# {row['product_name']}\n\n"
            f"- **适用人群**: {row['target_audience']}\n"
            f"- **核心卖点**: {row['core_selling_points']}\n"
            f"- **用户痛点**: {row['pain_points']}\n"
            f"- **使用场景**: {row['usage_scenarios']}\n"
            f"- **禁用词/风险**: {row['forbidden_terms']}\n"
            f"- **价格区间**: {row['price_range'] or '待补充'}\n"
            f"- **竞品参考**: {row['competitor_ref']}\n\n"
            f"> 来源: {row['source_path']}\n"
        )
        (PRODUCT_MATERIALS_DIR / f"{row['product_id']}.md").write_text(md, encoding="utf-8")

    PRODUCT_MATERIALS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with PRODUCT_MATERIALS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRODUCT_FIELDS)
        w.writeheader()
        for row in merged:
            w.writerow({k: row.get(k, "") for k in PRODUCT_FIELDS})

    return merged, status


if __name__ == "__main__":
    rows, status = sync_products()
    print(f"OK product_materials: {len(rows)} 条（{status}）")
