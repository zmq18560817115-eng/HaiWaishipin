from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json

from .storage import atomic_write, read_text, write_json
from .config import settings
from .ai_video import (
    AI_VIDEO_FOOTAGE,
    ai_video_mode,
    build_shot_video_prompt,
    footage_label,
    pipeline_label,
    shot_generates_video,
)
from .character_assets import pick_shot_reference_path, resolve_character


RETRYABLE_VALIDATION_RULES = frozenset({"V1", "V2", "V3", "V4"})


FORBIDDEN_TERMS = [
    "medical grade",
    "pain-free",
    "painless guarantee",
    "increase milk supply",
    "boost lactation",
    "completely silent",
    "cure",
    "treat",
    "diagnose",
    "best",
    "#1",
    "guaranteed",
    "FDA approved",
]

DEFAULT_TIMELINE = [
    (0, 3000),
    (3000, 8000),
    (8000, 13000),
    (13000, 17000),
    (17000, 20000),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_gate_report(brief: dict[str, Any]) -> str:
    checks = [
        ("export_plan_confirmed", brief.get("export_plan_confirmed", False)),
        (
            "target_country / language / platform",
            bool(brief.get("target_country") and brief.get("language") and brief.get("platform")),
        ),
        ("sku / launch_date / owner", bool(brief.get("sku") and brief.get("owner"))),
        (
            "overseas_product_page_available",
            brief.get("overseas_product_page_available", False),
        ),
        ("allowed_claims_available", brief.get("allowed_claims_available", False)),
        (
            "source_video_usage_rights_confirmed",
            brief.get("source_video_usage_rights_confirmed", False),
        ),
    ]
    gaps = [name for name, passed in checks if not passed]
    rows = "\n".join(
        f"| {name} | {'PASS' if passed else 'MISSING'} | |" for name, passed in checks
    )
    script_only_ok = bool(
        brief.get("allowed_claims_available")
        and brief.get("allowed_claims_en")
        and brief.get("master_video_id")
    )
    return f"""# B0 Gate Report · {brief['material_id']}

> 日期: {datetime.now().date().isoformat()} | 评估人: {brief.get('owner', '')}
> 模式: script-only

## 结果

**GO / NO-GO**: {'GO' if not gaps else 'NO-GO'}

## B0 字段检查

| 字段 | 状态 | 缺口说明 |
|---|---|---|
{rows}

## 结论

- script-only 下允许继续脚本包生产: {'是' if script_only_ok else '否'}
- 进入成片/投放前须补齐: {', '.join(gaps) if gaps else '无'}
"""


def make_storyboard(brief: dict[str, Any], shots: list[dict[str, Any]]) -> str:
    blocks = []
    for shot in shots:
        blocks.append(
            f"""## Shot {shot['number']} · {shot['role']}（{shot['timing']}）
- **画面**: {shot['visual']}
- **口播/字幕**: {shot['copy']}
- **类型**: [{shot['footage_type']}]
- **备注**: {shot.get('notes', '')}
"""
        )
    return f"""# 中文分镜 · {brief['theme']}

> material_id: {brief['material_id']}
> master_video_id: {brief['master_video_id']}
> 总时长目标: 20s

{chr(10).join(blocks)}
"""


def render_user_prompt(
    request: dict[str, Any], storyboard: str, company_context: str
) -> str:
    claims = "\n".join(f"- {item}" for item in request["allowed_claims_en"])
    forbidden = "\n".join(f"- {item}" for item in request["forbidden_terms"])
    return f"""# Localization Task

material_id: {request['material_id']}
target_market: {request['target_market']}
theme: {request['theme']}
sku: {request['sku']}

## company_knowledge_context

The snippets below are reference evidence only. They never expand the claims whitelist.

{company_context}

## allowed_claims_en (ONLY these may appear as product claims)
{claims}

## forbidden_terms (must NOT appear)
{forbidden}

## storyboard-cn.md
{storyboard}

## Required output schema: en-localization-pack-v1

Produce a complete Markdown file with these sections IN ORDER:
1. Video structure table (Hook/Problem/Product/Proof/CTA, ~20s total)
2. Subtitles by shot — Shot 1 through Shot 5, each with CN, EN, Chars count
3. Hook variants table — exactly 5 rows
4. Cover title candidates — at least 3 numbered lines
5. Allowed claims used — exact bullet values copied from the whitelist
6. Compliance checklist — three checkboxes
7. Revision log table — one row with today's date

Output the Markdown only.
"""


def demo_localization(brief: dict[str, Any], storyboard: str) -> str:
    cn_lines = re.findall(r"\*\*口播/字幕\*\*:\s*(.+)", storyboard)
    while len(cn_lines) < 5:
        cn_lines.append("")
    theme = str(brief.get("theme", "")).lower()
    if "flange" in theme or "护罩" in theme:
        en_lines = [
            "Wrong flange size can make every session uncomfortable.",
            "Many moms pump with a flange that does not fit well.",
            "Multiple flange sizes help you find a better fit.",
            "Adjustable suction levels support your daily routine.",
            "Portable design keeps your routine moving with you.",
        ]
        hooks = [
            ("flange size", "Find the flange size that fits you"),
            ("back to work", "Pack smarter for your workday routine"),
            ("night pumping", "A calmer setup for late-night pumping"),
            ("easy clean", "Less cleanup between busy moments"),
            ("portable", "Your pumping routine can travel too"),
        ]
        covers = [
            "Find Your Flange Fit",
            "Multiple Sizes, Better Comfort",
            "Pump On Your Schedule",
        ]
    else:
        en_lines = [
            "Make night pumping fit a calmer routine.",
            "Keep your essentials ready for every session.",
            "Adjust the settings to match your routine.",
            "Easy to clean parts simplify the reset.",
            "Pack your pump and keep moving confidently.",
        ]
        hooks = [
            ("night pumping", "A calmer setup for late-night pumping"),
            ("back to work", "Pack smarter for your workday routine"),
            ("flange size", "Find the flange size that fits"),
            ("easy clean", "Less cleanup between busy moments"),
            ("portable", "Your pumping routine can travel too"),
        ]
        covers = [
            "A Calmer Night Routine",
            "Pumping Made More Portable",
            "Simple Setup, Easier Reset",
        ]
    footage = re.findall(r"\*\*类型\*\*:\s*\[(LIVE_ACTION|AI_BROLL)\]", storyboard)
    while len(footage) < 5:
        footage.append("LIVE_ACTION")
    shot_blocks = []
    for index in range(5):
        shot_blocks.append(
            f"""### Shot {index + 1}
- **CN**: {cn_lines[index]}
- **EN**: {en_lines[index]}
- **Chars**: {len(en_lines[index])}
- **Footage**: [{footage[index]}]
"""
        )
    used_claims = brief["allowed_claims_en"][:3]
    return f"""# EN Localization Pack · {brief['theme']}

> material_id: {brief['material_id']}
> master_video_id: {brief['master_video_id']}
> target_market: {brief['target_country']} | language: {brief['language']}
> generated_at: {datetime.now().date().isoformat()} | reviewer: pending

## 1. Video structure

| Segment | Time | Visual | Note |
|---|---|---|---|
| Hook | 0–3s | Relatable opening | [{footage[0]}] |
| Problem | 3–8s | Daily routine | [{footage[1]}] |
| Product | 8–13s | Product detail | [{footage[2]}] |
| Proof | 13–17s | Approved feature | [{footage[3]}] |
| CTA | 17–20s | Closing frame | [{footage[4]}] |

## 2. Subtitles by shot

{chr(10).join(shot_blocks)}
## 3. Hook variants

| # | Theme | EN hook |
|---|---|---|
{chr(10).join(f'| {index + 1} | {theme_name} | {hook} |' for index, (theme_name, hook) in enumerate(hooks))}

## 4. Cover title candidates

{chr(10).join(f'{index + 1}. {title}' for index, title in enumerate(covers))}

## 5. Allowed claims used

{chr(10).join(f'- {claim}' for claim in used_claims)}

## 6. Compliance checklist

- [x] No forbidden terms used
- [x] Product claims copied from whitelist only
- [ ] Human compliance review pending

## 7. Revision log

| Date | Version | Author | Note |
|---|---|---|---|
| {datetime.now().date().isoformat()} | demo-1 | demo_local | Local validation sample |
"""


def extract_en_lines(markdown: str) -> list[str]:
    return [
        match.strip()
        for match in re.findall(r"\*\*EN\*\*:\s*(.+)", markdown, flags=re.IGNORECASE)
    ][:5]


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", text))


def forbidden_hits(texts: dict[str, str], terms: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for source, text in texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            for term in terms:
                normalized = term.lower()
                if normalized in lower:
                    hits.append(
                        {"term": term, "source": source, "line": line_number, "text": line.strip()}
                    )
    return hits


def build_validation_retry_message(errors: list[dict[str, str]]) -> str | None:
    retry_errors = [item for item in errors if item.get("rule") in RETRYABLE_VALIDATION_RULES]
    if not retry_errors:
        return None
    parts = [f"{item['rule']}: {item['message']}" for item in retry_errors]
    return (
        "Your previous output failed validation: "
        + "; ".join(parts)
        + ".\nRegenerate the FULL en-localization-pack-v1 Markdown. "
        "Fix only the listed issues. Output Markdown only."
    )


def validate_localization(
    markdown: str, allowed_claims: list[str], forbidden_terms: list[str]
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    en_lines = extract_en_lines(markdown)
    if len(en_lines) != 5:
        errors.append({"rule": "V1", "message": "Shot 1–5 EN 字幕不完整"})
    invalid_counts = [
        {"shot": index + 1, "words": _word_count(line)}
        for index, line in enumerate(en_lines)
        if not 4 <= _word_count(line) <= 14
    ]
    if invalid_counts:
        errors.append({"rule": "V2", "message": f"字幕词数超限: {invalid_counts}"})

    hook_section = re.search(
        r"## 3\..*?(?=## 4\.)", markdown, flags=re.IGNORECASE | re.DOTALL
    )
    hook_rows = (
        re.findall(r"^\|\s*[1-5]\s*\|", hook_section.group(0), flags=re.MULTILINE)
        if hook_section
        else []
    )
    if len(hook_rows) != 5:
        errors.append({"rule": "V3", "message": "Hook variants 必须恰好 5 行"})

    cover_section = re.search(
        r"## 4\..*?(?=## 5\.)", markdown, flags=re.IGNORECASE | re.DOTALL
    )
    covers = (
        re.findall(r"^\s*\d+\.\s+.+", cover_section.group(0), flags=re.MULTILINE)
        if cover_section
        else []
    )
    if len(covers) < 3:
        errors.append({"rule": "V4", "message": "Cover titles 少于 3 条"})

    hits = forbidden_hits({"en-localization-pack.md": markdown}, forbidden_terms)
    if hits:
        errors.append({"rule": "V5", "message": f"命中禁词: {hits}"})

    used_section = re.search(
        r"## 5\..*?(?=## 6\.)", markdown, flags=re.IGNORECASE | re.DOTALL
    )
    used_claims = (
        [
            item.strip()
            for item in re.findall(r"^\s*-\s+(.+)", used_section.group(0), flags=re.MULTILINE)
        ]
        if used_section
        else []
    )
    allowed_normalized = {item.casefold() for item in allowed_claims}
    violations = [item for item in used_claims if item.casefold() not in allowed_normalized]
    if violations:
        errors.append({"rule": "V6", "message": f"非白名单卖点: {violations}"})

    return {
        "valid": not errors,
        "errors": errors,
        "en_lines": en_lines,
        "word_counts": [_word_count(line) for line in en_lines],
    }


def _format_time(ms: int) -> str:
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def _split_caption(text: str, limit: int = 42) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > limit:
            chunks.append(current)
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def generate_srt(markdown: str) -> str:
    lines = extract_en_lines(markdown)
    if len(lines) != 5:
        raise ValueError("无法生成 SRT：EN Shot 1–5 不完整")
    output: list[str] = []
    sequence = 1
    for shot_index, text in enumerate(lines):
        start, end = DEFAULT_TIMELINE[shot_index]
        chunks = _split_caption(text)
        duration = end - start
        for chunk_index, chunk in enumerate(chunks):
            chunk_start = start + round(duration * chunk_index / len(chunks))
            chunk_end = start + round(duration * (chunk_index + 1) / len(chunks))
            output.extend(
                [
                    str(sequence),
                    f"{_format_time(chunk_start)} --> {_format_time(chunk_end)}",
                    chunk,
                    "",
                ]
            )
            sequence += 1
    return "\n".join(output).rstrip() + "\n"


def _load_pack(project: Path) -> dict[str, Any]:
    """竞品桥接 script-pack 与交付后 交付脚本包 共用读取；取 mtime 最新的一份。"""
    candidates: list[Path] = []
    for name in ("script-pack.json", "交付脚本包.json"):
        path = project / name
        if path.is_file():
            candidates.append(path)
    if not candidates:
        return {}
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _en_lines_from_pack(markdown: str) -> dict[int, str]:
    lines: dict[int, str] = {}
    for match in re.finditer(
        r"### Shot (\d+)\s*\n(?:.*\n)*?- \*\*EN\*\*: (.+)",
        markdown,
        flags=re.IGNORECASE,
    ):
        lines[int(match.group(1))] = match.group(2).strip()
    return lines


def _delivery_rows(project: Path, brief: dict[str, Any]) -> list[dict[str, str]]:
    pack = _load_pack(project)

    en_lines: dict[int, str] = {}
    en_path = project / "en-localization-pack.md"
    if en_path.exists():
        en_lines = _en_lines_from_pack(read_text(en_path))

    rows: list[dict[str, str]] = []
    pack_story = pack.get("storyboard") or []
    if pack_story:
        for shot in pack_story:
            num = int(shot.get("number") or len(rows) + 1)
            rows.append(
                {
                    "number": str(num),
                    "timing": str(shot.get("timing", "")),
                    "visual": str(shot.get("visual", "")),
                    "cn": str(shot.get("subtitle_cn", shot.get("copy", ""))),
                    "en": str(
                        shot.get("voiceover_en", shot.get("subtitle_en", en_lines.get(num, "")))
                    ),
                }
            )
        return rows

    sb_path = project / "storyboard.json"
    if sb_path.exists():
        try:
            shots = json.loads(sb_path.read_text(encoding="utf-8")).get("shots") or []
        except (json.JSONDecodeError, OSError):
            shots = []
        for shot in shots:
            num = int(shot.get("number") or len(rows) + 1)
            rows.append(
                {
                    "number": str(num),
                    "timing": str(shot.get("timing", "")),
                    "visual": str(shot.get("visual", "")),
                    "cn": str(shot.get("copy", "")),
                    "en": en_lines.get(num, ""),
                }
            )
    return rows


def _footage_map(project: Path) -> dict[int, str]:
    mapping: dict[int, str] = {}
    sb_path = project / "storyboard.json"
    if not sb_path.exists():
        return mapping
    try:
        shots = json.loads(sb_path.read_text(encoding="utf-8")).get("shots") or []
    except (json.JSONDecodeError, OSError):
        return mapping
    for shot in shots:
        mapping[int(shot.get("number", 0))] = str(shot.get("footage_type", "LIVE_ACTION"))
    return mapping


def _editor_shot_rows(project: Path, brief: dict[str, Any]) -> list[dict[str, str]]:
    footage = _footage_map(project)
    pack_by_num: dict[int, dict[str, Any]] = {}
    for row in _load_pack(project).get("storyboard") or []:
        pack_by_num[int(row.get("number", 0))] = row

    rows: list[dict[str, str]] = []
    for row in _delivery_rows(project, brief):
        number = int(row["number"])
        idx = number - 1
        start_ms, end_ms = DEFAULT_TIMELINE[idx] if 0 <= idx < len(DEFAULT_TIMELINE) else (0, 0)
        ft = footage.get(number, "LIVE_ACTION")
        pack_shot = pack_by_num.get(number, {})
        if pack_shot.get("footage_type"):
            ft = str(pack_shot.get("footage_type"))
        rows.append(
            {
                **row,
                "in_point": _format_time(start_ms),
                "out_point": _format_time(end_ms),
                "footage_type": ft,
                "footage_label": footage_label(ft),
                "seedance_prompt": str(pack_shot.get("seedance_prompt") or ""),
                "visual_prompt": str(pack_shot.get("visual_prompt") or row.get("visual", "")),
            }
        )
    return rows


def _pack_meta(project: Path, brief: dict[str, Any]) -> dict[str, str]:
    pack = _load_pack(project)
    rows = _editor_shot_rows(project, brief)
    voiceover = pack.get("voiceover_20s", "")
    if not voiceover and rows:
        voiceover = " ".join(r["en"] for r in rows if r["en"])
    return {
        "title": str(pack.get("title") or brief.get("theme", brief.get("material_id", ""))),
        "subtitle": str(pack.get("subtitle", "")),
        "voiceover": voiceover,
    }


def make_editor_html(
    brief: dict[str, Any],
    compliance: dict[str, Any],
    project: Path,
) -> str:
    material_id = brief.get("material_id", "project")
    source_url = brief.get("source_tiktok_url", "")
    link_id = brief.get("source_link_id", "")
    pass_label = "通过" if compliance.get("result") == "PASS" else "需修改"
    meta = _pack_meta(project, brief)
    rows = _editor_shot_rows(project, brief)

    shot_cards = []
    for row in rows:
        shot_cards.append(
            f"""<article class="shot">
  <header>
    <span class="badge">镜 {html.escape(row['number'])}</span>
    <span class="time">{html.escape(row['timing'])}</span>
    <span class="tag">{html.escape(row['footage_label'])}</span>
  </header>
  <p class="tc"><strong>时间轴</strong> {html.escape(row['in_point'])} → {html.escape(row['out_point'])}</p>
  <p><strong>画面</strong> {html.escape(row['visual'])}</p>
  <p><strong>英文字幕</strong> {html.escape(row['en'])}</p>
  <p class="cn"><strong>中文参考</strong> {html.escape(row['cn'])}</p>
</article>"""
        )

    ref = f"竞品 #{link_id}" if link_id else "竞品参考"
    source_html = (
        f'<a href="{html.escape(source_url)}">{html.escape(ref)}</a>'
        if source_url
        else html.escape(ref)
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>剪辑单 · {html.escape(material_id)}</title>
  <style>
    :root {{ font-family: "Segoe UI", "PingFang SC", sans-serif; color: #1a2332; }}
    body {{ margin: 0; background: #f4f6f8; }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 24px 20px 48px; }}
    header.hero {{
      background: linear-gradient(135deg, #1a2f4a, #2d4a6a); color: #fff;
      border-radius: 16px; padding: 24px 28px; margin-bottom: 20px;
    }}
    header.hero h1 {{ margin: 0 0 8px; font-size: 24px; }}
    header.hero p {{ margin: 4px 0; opacity: 0.9; font-size: 14px; }}
    .steps {{
      background: #fff; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px;
      border: 1px solid #dde3ea; line-height: 1.7; font-size: 15px;
    }}
    .steps ol {{ margin: 8px 0 0; padding-left: 22px; }}
    .steps code {{ background: #eef2f6; padding: 2px 6px; border-radius: 4px; }}
    .shots {{ display: grid; gap: 12px; }}
    .shot {{
      background: #fff; border-radius: 12px; padding: 16px 18px;
      border: 1px solid #dde3ea; page-break-inside: avoid;
    }}
    .shot header {{ display: flex; gap: 10px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }}
    .badge {{ background: #c45c3e; color: #fff; font-weight: 700; padding: 4px 10px; border-radius: 8px; }}
    .time {{ font-weight: 600; }}
    .tag {{ font-size: 12px; background: #eef2f6; padding: 3px 8px; border-radius: 6px; }}
    .shot p {{ margin: 6px 0; line-height: 1.55; font-size: 14px; }}
    .shot .tc {{ color: #4a5568; font-size: 13px; }}
    .shot .cn {{ color: #6b7280; font-size: 13px; }}
    footer {{ margin-top: 20px; font-size: 13px; color: #6b7280; }}
    @media print {{
      body {{ background: #fff; }}
      .wrap {{ padding: 0; }}
      header.hero {{ background: #1a2f4a; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1>{html.escape(meta['title'])}</h1>
      <p>{html.escape(meta['subtitle'] or material_id)}</p>
      <p>{source_html} · SKU {html.escape(str(brief.get('sku', '—')))} · {html.escape(str(brief.get('target_country', 'US')))}</p>
    </header>

    <section class="steps">
      <strong>剪辑同事怎么用（3 步）</strong>
      <ol>
        <li>用本页对照 <strong>5 镜画面与时间轴</strong> 剪辑（总长约 20 秒，比例 9:16）</li>
        <li>在 PR / 剪映 / CapCut 中 <strong>导入同目录 <code>subtitles.srt</code></strong> 作为英文字幕轨</li>
        <li>脚本全文见同目录 <code>交付脚本包.md</code></li>
      </ol>
    </section>

    <section class="shots">
      {''.join(shot_cards) if shot_cards else '<p>分镜待生成</p>'}
    </section>

    <footer>
      项目 {html.escape(material_id)} · 口播摘要：{html.escape(meta['voiceover'] or '见各镜英文字幕')}
      · 禁词扫描 {html.escape(pass_label)} · 生成 {html.escape(utc_now())}
    </footer>
  </div>
</body>
</html>
"""


def collect_delivery_pack(project: Path, brief: dict[str, Any]) -> dict[str, Any]:
    """Step 5 七项交付：标题/副标题/口播/分镜/字幕/画面/SeedDance。"""
    pack = _load_pack(project)
    rows = _editor_shot_rows(project, brief)
    storyboard = pack.get("storyboard") or []
    if not storyboard and rows:
        storyboard = [
            {
                "number": int(row["number"]),
                "timing": row["timing"],
                "visual": row["visual"],
                "voiceover_en": row["en"],
                "subtitle_cn": row["cn"],
                "subtitle_en": row["en"],
                "visual_prompt": row["visual"],
                "seedance_prompt": row.get("seedance_prompt", ""),
                "footage_type": row.get("footage_type", "LIVE_ACTION"),
            }
            for row in rows
        ]

    subtitle_copy = pack.get("subtitle_copy") or [s.get("subtitle_en", "") for s in storyboard]
    visual_prompts = pack.get("visual_prompts") or [
        s.get("visual_prompt", s.get("visual", "")) for s in storyboard
    ]
    seedance_prompts = pack.get("seedance_prompts") or []
    if not seedance_prompts:
        seedance_prompts = [
            s.get("seedance_prompt", "")
            for s in storyboard
            if s.get("footage_type") in ("AI_BROLL", "AI_VIDEO") and s.get("seedance_prompt")
        ]

    voiceover = pack.get("voiceover_20s", "")
    if not voiceover and storyboard:
        voiceover = " ".join(s.get("voiceover_en", "") for s in storyboard if s.get("voiceover_en"))

    return {
        "material_id": brief.get("material_id", project.name),
        "title": pack.get("title") or brief.get("theme", project.name),
        "subtitle": pack.get("subtitle", ""),
        "voiceover_20s": voiceover,
        "storyboard": storyboard,
        "subtitle_copy": subtitle_copy,
        "visual_prompts": visual_prompts,
        "seedance_prompts": seedance_prompts,
        "generated_at": utc_now(),
    }


def make_delivery_script_md(pack: dict[str, Any], brief: dict[str, Any]) -> str:
    material_id = pack.get("material_id", "project")
    link_id = brief.get("source_link_id", "")
    source_url = brief.get("source_tiktok_url", "")

    story_lines: list[str] = []
    for shot in pack.get("storyboard") or []:
        story_lines.append(
            f"### 镜 {shot.get('number')} · {shot.get('timing', '')} [{shot.get('footage_type', 'LIVE_ACTION')}]\n"
            f"- **画面**: {shot.get('visual', '')}\n"
            f"- **口播 EN**: {shot.get('voiceover_en', '')}\n"
            f"- **字幕 EN**: {shot.get('subtitle_en', '')}\n"
            f"- **画面提示词**: {shot.get('visual_prompt', '')}\n"
            f"- **SeedDance**: {shot.get('seedance_prompt', '') or '—'}"
        )

    subs = pack.get("subtitle_copy") or []
    subs_block = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(subs)) or "—"
    visuals = pack.get("visual_prompts") or []
    visual_block = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(visuals)) or "—"
    seedance = pack.get("seedance_prompts") or []
    seedance_block = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(seedance)) or "—（无 AI 空镜）"

    ref = f"竞品 #{link_id}" if link_id else "竞品参考"
    return f"""# 交付脚本包 · {material_id}

{ref} · {source_url or "—"} · SKU {brief.get("sku", "—")}

## 1. 标题
{pack.get("title", "")}

## 2. 副标题
{pack.get("subtitle", "") or "—"}

## 3. 20 秒口播脚本
{pack.get("voiceover_20s", "") or "—"}

## 4. 分镜脚本（5 镜）
{chr(10).join(story_lines) if story_lines else "—"}

## 5. 字幕文案
{subs_block}

## 6. 画面提示词
{visual_block}

## 7. SeedDance 2.0 视频生成提示词
{seedance_block}

---
字幕文件：`subtitles.srt` · AI 分镜视频：`broll/shot-N.mp4`（配置 Ark/FAL 后按镜生成）
{pack.get("generated_at", "")}
"""


def write_editor_deliverables(
    project: Path,
    brief: dict[str, Any],
    compliance: dict[str, Any],
) -> dict[str, Any]:
    delivery_pack = collect_delivery_pack(project, brief)
    atomic_write(project / "剪辑单.html", make_editor_html(brief, compliance, project))
    atomic_write(project / "交付脚本包.md", make_delivery_script_md(delivery_pack, brief))
    write_json(project / "交付脚本包.json", delivery_pack)
    stale = project / "剪辑单.csv"
    if stale.exists():
        stale.unlink()
    return delivery_pack


def delivery_zip_entries(project: Path) -> list[str]:
    """用户 zip：脚本文档 + 分镜 mp4 + 成片（不含字幕、剪辑单等）。"""
    names = [name for name in USER_DOWNLOAD_ZIP_SCRIPT if (project / name).is_file()]
    broll = project / "broll"
    if broll.is_dir():
        for mp4 in sorted(broll.glob("shot-*.mp4")):
            rel = mp4.relative_to(project).as_posix()
            if rel not in names:
                names.append(rel)
        final = broll / "final-video.mp4"
        if final.is_file() and final.stat().st_size > 1000:
            rel = final.relative_to(project).as_posix()
            if rel not in names:
                names.append(rel)
    return names


def scan_project(project: Path, brief: dict[str, Any]) -> dict[str, Any]:
    terms = FORBIDDEN_TERMS + brief.get("forbidden_terms_extra", [])
    texts = {}
    for name in ("en-localization-pack.md", "subtitles.srt"):
        path = project / name
        if path.exists():
            texts[name] = read_text(path)
    hits = forbidden_hits(texts, terms)
    report = {
        "material_id": brief["material_id"],
        "scanned_at": utc_now(),
        "forbidden_hits": hits,
        "allowed_claims_violations": [],
        "result": "FAIL" if hits else "PASS",
    }
    write_json(project / "compliance-report.json", report)
    return report


STAGE_LABELS_ZH = {
    "B0_NOT_STARTED": "未开始 · 请先填写立项",
    "B2_STORYBOARD": "进行中 · 待完成 5 镜分镜",
    "B4_LOCALIZE": "进行中 · 待生成英文脚本包",
    "B4B_SCAN": "进行中 · 待合规扫描",
    "B5_SRT": "进行中 · 待生成字幕交付包",
    "B6_AWAITING_SIGNOFF": "待验收 · 三方签字",
}

SIMPLE_FLOW_STAGES = {
    "B0_NOT_STARTED": {"step": 1, "label": "① 先去竞品库生成"},
    "B2_STORYBOARD": {"step": 1, "label": "① 脚本已就绪"},
    "B4_LOCALIZE": {"step": 2, "label": "② 点「完成交付」"},
    "B4B_SCAN": {"step": 2, "label": "② 点「完成交付」"},
    "B5_SRT": {"step": 2, "label": "② 点「完成交付」"},
    "B6_AWAITING_SIGNOFF": {"step": 3, "label": "③ 已交付，可下载"},
}


USER_DELIVERABLES = (
    "交付脚本包.md",
    "交付脚本包.json",
    "subtitles.srt",
    "剪辑单.html",
)

USER_DOWNLOAD_ZIP_SCRIPT = (
    "交付脚本包.md",
    "交付脚本包.json",
)

SEEDANCE_PIPELINE = pipeline_label()


def seedance_status(project: Path) -> dict[str, Any]:
    """分镜 AI 视频状态：broll 模式仅空镜；script 模式覆盖脚本各镜。"""
    pack = _load_pack(project)
    pack_by_num = {
        int(row.get("number", index + 1)): row
        for index, row in enumerate(pack.get("storyboard") or [])
    }
    brief = {}
    brief_path = project / "localization-brief.yaml"
    if brief_path.exists():
        try:
            import yaml

            brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
        except Exception:
            brief = {}

    storyboard_shots: list[dict[str, Any]] = []
    sb_path = project / "storyboard.json"
    if sb_path.exists():
        try:
            storyboard_shots = json.loads(sb_path.read_text(encoding="utf-8")).get("shots") or []
        except (json.JSONDecodeError, OSError):
            storyboard_shots = []

    mode = ai_video_mode()
    product_id = str(brief.get("sku") or "便携恒温杯")
    scene_en = "daily baby feeding"
    pack_scene = pack.get("scene_continuity") or {}
    if pack_scene.get("main_scene_en"):
        scene_en = str(pack_scene["main_scene_en"])
    market = {
        "audience_tags": brief.get("audience_tags") or [],
        "scenario_tags": brief.get("scenario_tags") or [],
    }
    character = resolve_character(market)

    from .video_production import read_project_video_settings

    prod = read_project_video_settings(project)
    shots: list[dict[str, Any]] = []
    for shot in storyboard_shots:
        number = int(shot["number"])
        pack_shot = pack_by_num.get(number, {})
        ft = str(pack_shot.get("footage_type") or shot.get("footage_type") or "LIVE_ACTION")
        if not shot_generates_video(ft, mode):
            continue
        role = str(pack_shot.get("role") or shot.get("role") or "")
        prompt = build_shot_video_prompt(
            role=role,
            pack_shot=pack_shot,
            story_shot=shot,
            scene_en=scene_en,
            product_name=product_id,
            character=character,
            aspect_ratio=prod.aspect_ratio,
        )
        ref_path, asset_type = pick_shot_reference_path(
            product_id=product_id,
            role=role,
            character=character,
            visual=str(shot.get("visual") or pack_shot.get("visual") or ""),
            footage_type=ft,
            project=project,
        )
        image_ref = None
        if ref_path:
            try:
                image_ref = ref_path.relative_to(project).as_posix()
            except ValueError:
                image_ref = None
        mp4 = project / "broll" / f"shot-{number}.mp4"
        shots.append(
            {
                "number": number,
                "role": role,
                "timing": shot.get("timing", ""),
                "visual": shot.get("visual", ""),
                "footage_type": ft,
                "footage_label": footage_label(ft),
                "prompt": prompt,
                "image_ref": image_ref,
                "asset_type": asset_type,
                "character_id": character.get("id") if character and asset_type == "person" else "",
                "ready": mp4.exists(),
                "file": f"broll/shot-{number}.mp4" if mp4.exists() else None,
            }
        )

    return {
        "available": bool(shots),
        "configured": settings.seedance_configured,
        "mode": mode,
        "pipeline": pipeline_label(mode),
        "shots": shots,
        "final_video": _final_video_status(project),
    }


def _final_video_status(project: Path) -> dict[str, Any]:
    final = project / "broll" / "final-video.mp4"
    if not final.is_file():
        return {"ready": False, "file": None, "bytes": 0}
    return {
        "ready": True,
        "file": "broll/final-video.mp4",
        "bytes": final.stat().st_size,
    }


def simple_flow_status(project: Path) -> dict[str, Any]:
    status = project_status(project)
    flow = SIMPLE_FLOW_STAGES.get(status["stage"], {"step": 1, "label": "① 确认中文脚本"})
    return {**status, "flow_step": flow["step"], "flow_label": flow["label"]}


def project_status(project: Path) -> dict[str, Any]:
    present = {
        "localization-brief.yaml": (project / "localization-brief.yaml").exists(),
        "storyboard-cn.md": (project / "storyboard-cn.md").exists(),
        "en-localization-pack.md": (project / "en-localization-pack.md").exists(),
        "subtitles.srt": (project / "subtitles.srt").exists(),
        **{name: (project / name).exists() for name in USER_DELIVERABLES},
    }
    if not present["localization-brief.yaml"]:
        stage = "B0_NOT_STARTED"
    elif not present["storyboard-cn.md"]:
        stage = "B2_STORYBOARD"
    elif not present["en-localization-pack.md"]:
        stage = "B4_LOCALIZE"
    elif not present["subtitles.srt"] or not all(present[name] for name in USER_DELIVERABLES):
        stage = "B5_SRT"
    else:
        stage = "B6_AWAITING_SIGNOFF"
    return {
        "stage": stage,
        "stage_label": STAGE_LABELS_ZH.get(stage, stage),
        "files": present,
        "dod_files_ready": stage == "B6_AWAITING_SIGNOFF",
    }

