from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from paths import DATA_DIR, SCRIPT_TEMPLATES_CSV

from .brand_policy import OUR_BRAND, display_product_name
from .feedback_loop import (
    apply_feedback_to_pack,
    build_feedback_constraints,
    format_constraints_for_llm,
)
from .doubao_config import script_llm_config
from .doubao_script import call_doubao_script
from .product_tags import validate_delivery_selection
from .output_standards import enrich_pack_with_standards
from .scene_script import (
    build_storyboard,
    pump_voiceovers,
    resolve_scenario_profile,
    scenario_conflict_note,
    thermos_voiceovers,
)

DEFAULT_MARKET = {
    "target_country": "US",
    "language": "en",
    "style": "us_tiktok_spoken",
    "tone": "实用、亲切、像妈妈朋友分享技巧",
}

SYSTEM_PROMPT = f"""你是母婴出海短视频脚本策划。根据用户在脚本页定制的人群/场景/卖点/痛点标签、爆款结构模板、竞品视频拆解的节奏分镜，生成 20 秒 TikTok 脚本包。

规则：
1. 只输出合法 JSON，不要 markdown 代码块外的说明。
2. 口播与字幕的产品向内容（人群、场景、卖点、痛点）必须且只能来自 user prompt 中「本次定制下发」四类标签，不得使用竞品拆解里的痛点/卖点原文，不得臆造未选标签。
3. 竞品拆解仅用于借鉴钩子节奏、分镜顺序、字幕密度与 CTA 方式，不得复述竞品品牌/账号/链接。
4. 英文口播禁止医疗承诺、禁词列表中的表述；卖点表述需与所选中文卖点标签语义一致。
5. 总时长 20 秒，恰好 5 镜。
6. seedance_prompts 仅用于 footage_type=AI_BROLL 的镜头，英文描述画面，无人物医疗宣称。
7. 标题/副标题适合目标市场母婴人群。
8. 口播、字幕、画面提示统一露出我方品牌产品名（见 user prompt 中的 brand_product）。
9. 全部 5 镜必须在「本次定制下发」的投放场景内完成，visual/visual_prompt/口播禁止出现未选场景（例如选了卧室禁止车载/外出旅行/机场表述）；各镜 visual_prompt 需写明该场景下的具体画面。
10. **脚本严格执行**：分镜顺序、口播、字幕、时长与 CTA 即为成片执行契约，生成阶段不得擅自增删改镜。
11. **产品外观锁白底主图（最高优先级）**：凡画面中出现产品，外观/颜色/比例/盖型/数显/Logo 必须 100% 对照 `主图/白底主图.png`。**禁止**用 M端/副图场景图、KV、倒出口参考作 SeedDance 垫图或外观依据；场景图只约束环境与用法流程（写在 visual_prompt / seedance_prompt 里）。
12. **场景与用法锁场景图（仅 Prompt）**：道具摆放、环境氛围须对照所选场景标签对应的场景图，但不得让场景图改变产品本体造型。
13. **结构细节锁细节图**：倒出口、翻盖等动作可参考 `倒出口参考` 与细节图，写在 Prompt 中；I2V 垫图仍用白底主图。
14. **人物同一视频前后一致**：若出镜，全片保持同一人物档案（年龄、服饰、发型、肤色、手部）；无法保证时用产品特写或手部镜头。
15. **光影增强真实感**：在保持场景统一的前提下，使用有动机的主光、柔和阴影与自然反射，提升画面真实感，但不得借光影掩盖产品变形。
16. 后续新增品类时，同样必须绑定白底主图 + 场景图 + 细节图后再出脚本或生成。
"""

OUTPUT_SCHEMA = {
    "title": "英文主标题",
    "subtitle": "英文副标题/封面短句",
    "voiceover_20s": "完整 20 秒英文口播（连贯可读）",
    "storyboard": [
        {
            "number": 1,
            "role": "钩子",
            "timing": "0-3s",
            "visual": "中文画面描述",
            "voiceover_en": "该镜英文口播",
            "subtitle_en": "该镜英文字幕（6-10词）",
            "visual_prompt": "实拍/构图提示（中文）",
            "seedance_prompt": "AI空镜时英文 SeedDance 提示词，实拍镜留空",
            "footage_type": "LIVE_ACTION 或 AI_BROLL",
        }
    ],
    "subtitle_copy": ["每镜一条英文字幕"],
    "visual_prompts": ["每镜画面提示"],
    "seedance_prompts": ["仅 AI_BROLL 镜的 SeedDance 2.0 英文提示词"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_templates() -> list[dict[str, str]]:
    if not SCRIPT_TEMPLATES_CSV.exists():
        return []
    with SCRIPT_TEMPLATES_CSV.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def pick_template(
    analysis: dict[str, str],
    templates: list[dict[str, str]],
    *,
    product_id: str = "",
) -> dict[str, str]:
    text = " ".join(
        analysis.get(k, "") for k in ("reusable_template", "video_structure", "selling_points")
    ).lower()
    if any(x in text for x in ("种草", "产品", "测评", "momcozy", "product")):
        key = "product-seed"
    elif any(x in text for x in ("教程", "hack", "技巧", "步骤")):
        key = "tutorial-hack"
    elif any(x in text for x in ("科普", "知识", "ibclc")):
        key = "education"
    else:
        key = "tutorial-hack"
    for row in templates:
        if row.get("template_id") == key:
            chosen = row
            break
    else:
        chosen = templates[0] if templates else {
            "template_id": "tutorial-hack",
            "label": "教程技巧型",
            "structure_chain": "痛点反问 → 步骤演示 → 效果验证 → 收藏引导",
        }
    if product_id:
        hint = build_feedback_constraints(product_id, []).get("template_hint") or {}
        tpl_id = str(hint.get("template_id") or "").strip()
        if tpl_id:
            for row in templates:
                if row.get("template_id") == tpl_id:
                    return row
        tpl_label = str(hint.get("template_label") or "").strip()
        if tpl_label:
            for row in templates:
                if row.get("label") == tpl_label:
                    return row
    return chosen


def _forbidden_from_product(product: dict[str, str]) -> list[str]:
    raw = product.get("forbidden_terms") or ""
    terms = [
        "medical grade", "pain-free", "increase milk supply", "guaranteed", "best", "cure",
    ]
    return [t for t in terms if t in raw.lower()] or terms[:6]


def build_user_prompt(
    *,
    product: dict[str, str],
    analysis: dict[str, str],
    template: dict[str, str],
    market: dict[str, str],
    video_title: str,
    source_url: str,
    feedback_block: dict[str, Any] | None = None,
) -> str:
    tags = validate_delivery_selection(market)
    forbidden = _forbidden_from_product(product)
    pid = product.get("product_id", "")
    if feedback_block is None:
        feedback_block = build_feedback_constraints(pid, tags.get("scenario_tags"))
    feedback_section = format_constraints_for_llm(feedback_block)
    feedback_block_text = f"\n{feedback_section}\n" if feedback_section else ""
    brand_product = display_product_name(pid, product.get("product_name", OUR_BRAND))
    audience_line = "、".join(tags["audience_tags"])
    scenario_line = "、".join(tags["scenario_tags"])
    selling_line = "、".join(tags["selling_tags"])
    pain_line = "、".join(tags["pain_tags"])
    scene_note = scenario_conflict_note(tags["scenario_tags"])
    scene_warn = f"\n- 场景一致性说明: {scene_note}" if scene_note else ""
    profile = resolve_scenario_profile(tags["scenario_tags"])
    creative = (market.get("creative_brief") or "").strip()
    creative_block = f"\n## 创作指令（对话框）\n{creative}\n" if creative else ""
    specs_block = f"""
## 成片规格
- 分辨率: {market.get("resolution", "720P")}
- 宽高比: {market.get("aspect_ratio", "9:16")}
- 目标时长: {market.get("duration_sec", 5)} 秒
- 生成条数: {market.get("generate_count", 1)}
- 提示词增强: {"是" if market.get("prompt_enhanced") else "否"}"""
    return f"""# 任务：生成 script-pack-v1 JSON

## 品牌与替换
- 我方品牌: {OUR_BRAND}
- 成片统一产品名: {brand_product}
- 参考视频标题仅供理解结构节奏，成片不得复述竞品品牌/账号/链接

## 目标市场
- 国家: {market.get("target_country", "US")}
- 语言: {market.get("language", "en")}
- 风格: {market.get("style", "us_tiktok_spoken")} — {market.get("tone", "")}

## 本次定制下发（成片产品向内容必须且只能体现以下勾选，不得超出）
- 目标人群: {audience_line}
- 投放场景: {scenario_line}
- 核心卖点: {selling_line}
- 用户痛点: {pain_line}
- 首要场景（全片统一）: {profile.get("primary_tag", scenario_line)}{scene_warn}
{creative_block}{specs_block}{feedback_block_text}

## 合规禁词（禁止出现在口播/字幕）
{chr(10).join("- " + t for t in forbidden)}

## 爆款结构模板（节奏参考）
- {template.get("label", "")}: {template.get("structure_chain", "")}

## 参考视频结构拆解（仅借节奏与分镜，禁止复述竞品卖点/痛点原文）
- 结构链: {analysis.get("video_structure", "")}
- 钩子节奏: {analysis.get("hook_3s", "")}
- 字幕布局: {analysis.get("subtitle_layout", "")}
- CTA 方式: {analysis.get("cta", "")}
- 可复用结构: {analysis.get("reusable_template", "")}

## 输出 JSON 字段（必须全部包含）
{json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2)}

只返回 JSON 对象。"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _call_anthropic(user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from .doubao_config import _env

    api_key = (_env().get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("未配置 ANTHROPIC_API_KEY")
    model = (_env().get("OVERSEAS_LOC_MODEL") or os.getenv("OVERSEAS_LOC_MODEL") or "claude-sonnet-4-6").strip()
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=90) as client:
        resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    text = "\n".join(
        b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
    )
    pack = _extract_json(text)
    meta = {
        "provider": "anthropic",
        "model": data.get("model", model),
        "status": "success",
        "generated_at": utc_now(),
    }
    return pack, meta


def _call_script_llm(user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """按 SCRIPT_LLM_PROVIDER 调用豆包 / Claude；auto 时豆包优先。"""
    cfg = script_llm_config()
    provider = str(cfg.get("provider") or "auto")
    errors: list[str] = []

    def _try_doubao() -> tuple[dict[str, Any], dict[str, Any]]:
        return call_doubao_script(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    if provider == "rule":
        raise RuntimeError("SCRIPT_LLM_PROVIDER=rule")

    if provider == "doubao":
        if not cfg.get("doubao_enabled"):
            raise RuntimeError("豆包脚本未配置或已关闭 DOUBAO_SCRIPT_ENABLED")
        return _try_doubao()

    if provider == "anthropic":
        return _call_anthropic(user_prompt)

    # auto
    if cfg.get("doubao_enabled"):
        try:
            return _try_doubao()
        except Exception as exc:
            errors.append(f"doubao: {exc}")
    if cfg.get("anthropic_available"):
        try:
            return _call_anthropic(user_prompt)
        except Exception as exc:
            errors.append(f"anthropic: {exc}")
    raise RuntimeError("; ".join(errors) or "未配置 ARK_API_KEY 或 ANTHROPIC_API_KEY")


def _is_thermos_product(product: dict[str, str]) -> bool:
    name = product.get("product_name", "")
    pid = product.get("product_id", "")
    if "吸奶器" in name or pid == "吸奶器":
        return False
    return "恒温杯" in name or "恒温杯" in pid or "warmer" in name.lower()


def _is_pump_product(product: dict[str, str]) -> bool:
    name = product.get("product_name", "")
    pid = product.get("product_id", "")
    return "吸奶器" in name or pid == "吸奶器" or "pump" in name.lower()


def _rule_pack(
    *,
    product: dict[str, str],
    analysis: dict[str, str],
    template: dict[str, str],
    market: dict[str, str],
    video_title: str,
) -> dict[str, Any]:
    validate_delivery_selection(market)
    if _is_thermos_product(product):
        return _rule_pack_thermos(
            product=product,
            analysis=analysis,
            template=template,
            market=market,
            video_title=video_title,
        )
    product_name = display_product_name(
        product.get("product_id", ""),
        product.get("product_name") or "熊猫布布吸奶器",
    )
    profile = resolve_scenario_profile(market.get("scenario_tags") or [])
    vos = pump_voiceovers(market, profile)
    storyboard, subtitle_copy, visual_prompts, seedance_prompts = build_storyboard(
        product_name=product_name,
        market=market,
        profile=profile,
        voiceovers=vos,
    )
    voiceover = " ".join(s["voiceover_en"] for s in storyboard)
    return {
        "title": f"{product_name} tips {profile.get('title', 'for busy moms')}",
        "subtitle": profile.get("subtitle", "Better fit, calmer nights"),
        "voiceover_20s": voiceover,
        "storyboard": storyboard,
        "subtitle_copy": subtitle_copy,
        "visual_prompts": visual_prompts,
        "seedance_prompts": seedance_prompts,
        "inputs": {
            "template": template.get("label", ""),
            "market": market,
            "content_source": "user_selected_tags",
            "structure_source": "competitor_analysis",
            "scenario_profile": profile.get("id"),
            "scenario_primary": profile.get("primary_tag"),
            "scenario_conflict_note": scenario_conflict_note(market.get("scenario_tags") or []),
            "reference_title": video_title[:80],
        },
    }


def _rule_pack_thermos(
    *,
    product: dict[str, str],
    analysis: dict[str, str],
    template: dict[str, str],
    market: dict[str, str],
    video_title: str,
) -> dict[str, Any]:
    validate_delivery_selection(market)
    product_name = display_product_name(
        product.get("product_id", ""),
        product.get("product_name") or "熊猫布布便携恒温杯",
    )
    profile = resolve_scenario_profile(market.get("scenario_tags") or [])
    vos = thermos_voiceovers(market, profile)
    storyboard, subtitle_copy, visual_prompts, seedance_prompts = build_storyboard(
        product_name=product_name,
        market=market,
        profile=profile,
        voiceovers=vos,
    )
    voiceover = " ".join(s["voiceover_en"] for s in storyboard)
    return {
        "title": f"{product_name} tips {profile.get('title', 'for parents')}",
        "subtitle": profile.get("subtitle", "Warm milk in minutes"),
        "voiceover_20s": voiceover,
        "storyboard": storyboard,
        "subtitle_copy": subtitle_copy,
        "visual_prompts": visual_prompts,
        "seedance_prompts": seedance_prompts,
        "inputs": {
            "template": template.get("label", ""),
            "market": market,
            "content_source": "user_selected_tags",
            "structure_source": "competitor_analysis",
            "scenario_profile": profile.get("id"),
            "scenario_primary": profile.get("primary_tag"),
            "scenario_conflict_note": scenario_conflict_note(market.get("scenario_tags") or []),
            "reference_title": video_title[:80],
        },
    }


def normalize_pack(pack: dict[str, Any]) -> dict[str, Any]:
    storyboard = pack.get("storyboard") or []
    if storyboard and not pack.get("subtitle_copy"):
        pack["subtitle_copy"] = [s.get("subtitle_en", "") for s in storyboard]
    if storyboard and not pack.get("visual_prompts"):
        pack["visual_prompts"] = [s.get("visual_prompt", "") for s in storyboard]
    if storyboard and not pack.get("seedance_prompts"):
        pack["seedance_prompts"] = [
            s.get("seedance_prompt", "")
            for s in storyboard
            if s.get("footage_type") in ("AI_BROLL", "AI_VIDEO") and s.get("seedance_prompt")
        ]
    return pack


def _attach_feedback_and_standards(
    pack: dict[str, Any],
    *,
    product: dict[str, str],
    market: dict[str, Any],
    analysis: dict[str, str] | None = None,
    feedback_block: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pid = str(product.get("product_id") or "")
    fb = feedback_block or build_feedback_constraints(pid, market.get("scenario_tags") or [])
    apply_feedback_to_pack(pack, fb)
    enrich_pack_with_standards(pack, product=product, market=market, analysis=analysis)
    return pack


def generate_script_pack(
    *,
    product: dict[str, str],
    analysis: dict[str, str],
    video_title: str,
    source_url: str,
    market: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    market = {**DEFAULT_MARKET, **(market or {})}
    validate_delivery_selection(market)
    pid = str(product.get("product_id") or "")
    feedback_block = build_feedback_constraints(pid, market.get("scenario_tags") or [])
    template = pick_template(analysis, load_templates(), product_id=pid)
    user_prompt = build_user_prompt(
        product=product,
        analysis=analysis,
        template=template,
        market=market,
        video_title=video_title,
        source_url=source_url,
        feedback_block=feedback_block,
    )
    try:
        pack, meta = _call_script_llm(user_prompt)
        pack = normalize_pack(pack)
        pack["inputs"] = {
            "product_name": product.get("product_name", ""),
            "template": template.get("label", ""),
            "template_id": template.get("template_id", ""),
            "template_chain": template.get("structure_chain", ""),
            "market": market,
            "content_source": "user_selected_tags",
            "structure_source": "competitor_analysis",
            "reference_url": source_url,
            "feedback_matched": feedback_block.get("matched_count", 0),
        }
        meta["template_id"] = template.get("template_id", "")
        meta["template_label"] = template.get("label", "")
        meta["feedback_matched"] = feedback_block.get("matched_count", 0)
        _attach_feedback_and_standards(
            pack,
            product=product,
            market=market,
            analysis=analysis,
            feedback_block=feedback_block,
        )
        return pack, meta
    except Exception as exc:
        pack = _rule_pack(
            product=product,
            analysis=analysis,
            template=template,
            market=market,
            video_title=video_title,
        )
        meta = {
            "provider": "rule_template",
            "model": "rule-v1",
            "status": "fallback",
            "error": str(exc)[:200],
            "generated_at": utc_now(),
            "template_id": template.get("template_id", ""),
            "template_label": template.get("label", ""),
            "feedback_matched": feedback_block.get("matched_count", 0),
        }
        _attach_feedback_and_standards(
            pack,
            product=product,
            market=market,
            analysis=analysis,
            feedback_block=feedback_block,
        )
        return pack, meta


def pack_to_bridge_shots(pack: dict[str, Any]) -> list[dict[str, str]]:
    shots = []
    for row in pack.get("storyboard") or []:
        shots.append({
            "number": int(row.get("number", len(shots) + 1)),
            "role": row.get("role", ""),
            "timing": row.get("timing", ""),
            "visual": row.get("visual", ""),
            "copy": row.get("voiceover_en") or row.get("subtitle_en", ""),
            "footage_type": row.get("footage_type", "LIVE_ACTION"),
            "notes": row.get("seedance_prompt") or row.get("visual_prompt", ""),
        })
    return shots


def pack_to_markdown(pack: dict[str, Any], source_url: str) -> str:
    lines = [
        f"# {pack.get('title', 'Script Pack')}",
        f"> {pack.get('subtitle', '')}",
        f"> 结构参考（已换品牌）: {source_url}",
        "",
        "## 20秒口播",
        pack.get("voiceover_20s", ""),
        "",
        "## 分镜脚本",
    ]
    for s in pack.get("storyboard") or []:
        lines.append(
            f"\n### Shot {s.get('number')} · {s.get('role')}（{s.get('timing')}）\n"
            f"- 画面: {s.get('visual', '')}\n"
            f"- 口播 EN: {s.get('voiceover_en', '')}\n"
            f"- 字幕 EN: {s.get('subtitle_en', '')}\n"
            f"- 画面提示: {s.get('visual_prompt', '')}\n"
            f"- SeedDance: {s.get('seedance_prompt', '') or '—'}\n"
            f"- 类型: [{s.get('footage_type', 'LIVE_ACTION')}]"
        )
    lines.extend([
        "",
        "## 字幕文案",
        "\n".join(f"- {x}" for x in pack.get("subtitle_copy") or []),
        "",
        "## SeedDance 2.0 提示词",
        "\n".join(f"- {x}" for x in pack.get("seedance_prompts") or []) or "—",
    ])
    return "\n".join(lines) + "\n"
