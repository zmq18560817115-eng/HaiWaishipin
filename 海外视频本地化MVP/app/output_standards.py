"""overseas-video-output-standards skill 的结构化出稿契约（写入 script-pack）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from paths import PRODUCT_MATERIALS_DIR, WORKFLOW_ROOT

from .character_assets import (
    build_character_continuity as build_character_continuity_from_library,
    build_person_asset_manifest_entries,
    pick_shot_reference_path,
    resolve_character,
)
from .product_assets import (
    get_product_usage_pour_image,
    get_product_white_hero_image,
    list_product_images,
    product_listing_dir,
)
from .scene_script import resolve_scenario_profile, scenario_conflict_note

KNOWLEDGE_PRODUCTS = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "products"
COMPLIANCE_DOC = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "processes" / "海外短视频合规禁词.md"


def _rel(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return path.relative_to(WORKFLOW_ROOT).as_posix()
    except ValueError:
        return str(path)


def build_product_sources(product_id: str) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    md = PRODUCT_MATERIALS_DIR / f"{product_id}.md"
    if md.is_file():
        sources.append({"type": "product_doc", "path": _rel(md)})
    listing = product_listing_dir(product_id)
    if listing.is_dir():
        sources.append({"type": "listing_assets", "path": _rel(listing)})
    kbase = KNOWLEDGE_PRODUCTS / f"{product_id}.md"
    if kbase.is_file():
        sources.append({"type": "knowledge_fallback", "path": _rel(kbase)})
    if COMPLIANCE_DOC.is_file():
        sources.append({"type": "compliance", "path": _rel(COMPLIANCE_DOC)})
    sources.append({"type": "skill", "path": "overseas-video-output-standards/SKILL.md"})
    return sources


def build_asset_manifest(product_id: str) -> list[dict[str, Any]]:
    listing = product_listing_dir(product_id)
    white = get_product_white_hero_image(product_id)
    pour = get_product_usage_pour_image(product_id)
    manifest: list[dict[str, Any]] = []

    def add(path: Path | None, asset_type: str, allowed: str, forbidden: str = "") -> None:
        if not path or not path.is_file():
            return
        manifest.append({
            "asset_id": f"{product_id}:{path.name}",
            "product": product_id,
            "source_path": _rel(path),
            "asset_type": asset_type,
            "approval_status": "approved",
            "allowed_use": allowed,
            "forbidden_use": forbidden,
        })

    add(white, "product_identity", "白底主图：产品外观唯一锚点；SeedDance 唯一 I2V 垫图", "禁止用场景图/KV/倒出口参考替代白底主图作垫图或改型改色")
    add(pour, "usage_step", "倒出口/翻盖演示：仅写入 Prompt 约束物理流向", "禁止作为 SeedDance I2V 垫图；禁止替代白底主图锁外观")

    scene_dirs = ("M端", "副图", "A+")
    for path in list_product_images(product_id):
        if white and path.resolve() == white.resolve():
            continue
        sub = path.parent.name
        if sub in scene_dirs:
            add(path, "scene", f"场景图（{sub}）：仅约束环境/道具/用法流程（Prompt）", "禁止作 SeedDance I2V 垫图；禁止替代白底主图锁产品外观")
        elif sub == "主图" and path.name.startswith("倒出口"):
            continue
        else:
            add(path, "detail_proof", f"细节图参考（{sub}）", "unsupported efficacy claim")

    manifest.extend(build_person_asset_manifest_entries())

    if not manifest:
        manifest.append({
            "asset_id": f"{product_id}:missing",
            "product": product_id,
            "source_path": "",
            "asset_type": "product_identity",
            "approval_status": "needs_review",
            "allowed_use": "",
            "forbidden_use": "missing approved hero image",
        })
    return manifest


def build_scene_continuity(market: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    scene_zh = profile.get("zh") or profile.get("primary_tag") or "日常喂养"
    scene_en = profile.get("en") or "daily baby feeding"
    tags = market.get("scenario_tags") or []
    note = scenario_conflict_note(tags)
    props = ["baby feeding bottle", "milk storage bag", "bedside table"]
    if profile.get("id") == "car":
        props = ["car cup holder", "baby bottle", "diaper bag"]
    elif profile.get("id") == "travel":
        props = ["travel bag", "baby bottle", "airport lounge"]
    elif profile.get("id") == "office":
        props = ["office desk", "baby bottle", "pumping bag"]
    return {
        "main_scene_zh": scene_zh,
        "main_scene_en": scene_en,
        "time_of_day": "night" if profile.get("id") == "bedroom" else "daytime",
        "lighting": (
            "soft motivated home light with natural shadows and plausible reflections"
            if profile.get("id") == "bedroom"
            else "natural daylight with soft shadows and realistic surface reflections"
        ),
        "lighting_intent": "enhance scene realism without altering product identity",
        "props": props,
        "allowed_transitions": "single-scene only unless scripted",
        "conflict_note": note,
        "constraints": "Do not mix bedroom/car/airport in one video without scripted reason",
    }


def build_character_continuity(market: dict[str, Any], product_id: str) -> dict[str, Any]:
    return build_character_continuity_from_library(market, product_id)


def build_production_fidelity(product_id: str, asset_manifest: list[dict[str, Any]]) -> dict[str, Any]:
    hero = next((a for a in asset_manifest if a.get("asset_type") == "product_identity" and "白底" in str(a.get("allowed_use", ""))), None)
    if not hero:
        hero = next((a for a in asset_manifest if a.get("asset_type") == "product_identity"), None)
    usage = next((a for a in asset_manifest if a.get("asset_type") == "usage_step"), None)
    scenes = [a for a in asset_manifest if a.get("asset_type") == "scene"]
    details = [a for a in asset_manifest if a.get("asset_type") == "detail_proof"]
    base = {
        "script_lock": "Execute approved storyboard shot order, dialogue, timing, and CTA exactly; no silent rewrites during generation.",
        "hero_image_lock": hero.get("source_path", "") if hero else "",
        "hero_rule": "Product appearance MUST match 白底主图 only. Scene images and pour reference NEVER substitute as SeedDance I2V reference.",
        "scenario_lock": [a.get("source_path", "") for a in scenes[:6]],
        "scenario_rule": "Scene images guide environment/props/usage in prompt text only — not product shape/color.",
        "detail_lock": [a.get("source_path", "") for a in details[:6]],
        "usage_step_lock": usage.get("source_path", "") if usage else "",
        "detail_rule": "Spout, hinge, port, and structural inserts must match detail/usage-step images.",
        "physics_rule": "No impossible pours, wrong container relationships, reversed gravity, or usage-scene mismatch.",
        "person_rule": "Same person profile across all person-visible shots in one video.",
        "lighting_rule": "Motivated light, soft shadows, natural reflections — enhance realism without changing product shape.",
        "new_category_rule": "New products require white hero + scenario images + detail images before scripting or generation.",
        "product_id": product_id,
    }
    if product_id == "便携恒温杯":
        base["temperature_display_rule"] = "Fahrenheit °F only on display (~98°F typical); never Celsius °C."
        base["milk_physics_rule"] = (
            "Body-warm breast milk/formula pour only; no boiling, steam plume, or bubbling hot liquid."
        )
    return base


def build_shot_asset_map(
    storyboard: list[dict[str, Any]],
    *,
    product_id: str,
    asset_manifest: list[dict[str, Any]],
    market: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    character = resolve_character(market)
    hero_path = next(
        (a["source_path"] for a in asset_manifest if a.get("asset_type") == "product_identity" and a.get("source_path")),
        "",
    )
    usage_path = next(
        (a["source_path"] for a in asset_manifest if a.get("asset_type") == "usage_step" and a.get("source_path")),
        hero_path,
    )
    rows: list[dict[str, Any]] = []
    for shot in storyboard:
        role = str(shot.get("role") or "")
        ft = str(shot.get("footage_type") or "LIVE_ACTION")
        is_ai = ft in ("AI_BROLL", "AI_VIDEO")
        ref_path, asset_type = pick_shot_reference_path(
            product_id=product_id,
            role=role,
            character=character,
            visual=str(shot.get("visual") or shot.get("visual_prompt") or ""),
            footage_type=ft,
        )
        asset_path = _rel(ref_path) if ref_path else "missing"
        if asset_path == "missing":
            asset_path = hero_path or "missing"
        method = "SeedDance" if is_ai else "live_action_or_edit"
        guard = shot.get("seedance_prompt") or shot.get("visual_prompt", "")
        guard = (
            f"{guard} | hero_lock={hero_path} | physics_safe=yes | "
            f"no_product_redesign=yes | lighting=realistic_motivated"
        )
        if character and asset_type == "person":
            guard = f"{guard} | person_ref={character.get('id')} | same_video_person_lock=yes"
        rows.append({
            "shot_id": int(shot.get("number", len(rows) + 1)),
            "time_range": shot.get("timing", ""),
            "script_role": role,
            "dialogue_or_subtitle": shot.get("subtitle_en") or shot.get("voiceover_en", ""),
            "visual_description": shot.get("visual") or shot.get("visual_prompt", ""),
            "required_asset_type": asset_type,
            "asset_path_or_status": asset_path if asset_path else "missing",
            "generation_or_edit_method": method,
            "prompt_guardrails": guard,
            "compliance_note": "",
            "character_id": character.get("id") if character and asset_type == "person" else "",
        })
    return rows


def build_claim_guardrails(product_id: str) -> dict[str, Any]:
    if product_id == "便携恒温杯":
        return {
            "allowed_claims": [
                "portable rechargeable warming",
                "pour into cup to warm then pour to bottle",
                "fits cup holder / diaper bag (if selected in tags)",
            ],
            "forbidden_claims": [
                "medical grade",
                "guaranteed",
                "sterilization guarantee",
                "bottle inside cup",
                "commercial milk bottle as input",
                "Celsius display on product screen",
                "boiling milk with steam",
            ],
            "rewrites": {
                "pain-free": "designed for a calmer routine",
                "best": "handy for travel",
            },
        }
    if product_id == "吸奶器":
        return {
            "allowed_claims": ["adjustable suction", "portable", "easier cleaning"],
            "forbidden_claims": [
                "medical grade",
                "pain-free",
                "increase milk supply",
                "FDA approved",
                "通乳",
                "催奶",
            ],
            "rewrites": {"pain-free": "gentler-feeling routine"},
        }
    return {"allowed_claims": [], "forbidden_claims": ["unsupported medical claims"], "rewrites": {}}


def build_delivery_risks(
    *,
    asset_manifest: list[dict[str, Any]],
    shot_asset_map: list[dict[str, Any]],
    scene_continuity: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not any(a.get("asset_type") == "product_identity" and a.get("source_path") for a in asset_manifest):
        blockers.append("缺少已批准白底主图（主图/白底主图.png）")
    if any(s.get("asset_path_or_status") == "missing" for s in shot_asset_map):
        blockers.append("部分镜头缺少素材路径")
    if scene_continuity.get("conflict_note"):
        warnings.append(str(scene_continuity["conflict_note"]))
    status = "BLOCKED" if blockers else ("WARNING" if warnings else "PASS")
    return {"status": status, "blockers": blockers, "warnings": warnings}


def enrich_pack_with_standards(
    pack: dict[str, Any],
    *,
    product: dict[str, str],
    market: dict[str, Any],
    analysis: dict[str, str] | None = None,
) -> dict[str, Any]:
    """将 skill 要求的 7 段契约写入 script-pack。"""
    _ = analysis
    product_id = str(product.get("product_id") or "")
    profile = resolve_scenario_profile(market.get("scenario_tags") or [])
    storyboard = pack.get("storyboard") or []

    asset_manifest = build_asset_manifest(product_id)
    scene_continuity = build_scene_continuity(market, profile)
    character_continuity = build_character_continuity(market, product_id)
    shot_asset_map = build_shot_asset_map(
        storyboard,
        product_id=product_id,
        asset_manifest=asset_manifest,
        market=market,
    )
    claim_guardrails = build_claim_guardrails(product_id)
    production_fidelity = build_production_fidelity(product_id, asset_manifest)
    delivery_risks = build_delivery_risks(
        asset_manifest=asset_manifest,
        shot_asset_map=shot_asset_map,
        scene_continuity=scene_continuity,
    )

    pack["product_sources"] = build_product_sources(product_id)
    pack["asset_manifest"] = asset_manifest
    pack["shot_asset_map"] = shot_asset_map
    pack["scene_continuity"] = scene_continuity
    pack["character_continuity"] = character_continuity
    pack["production_fidelity"] = production_fidelity
    pack["claim_guardrails"] = claim_guardrails
    pack["delivery_risks"] = delivery_risks
    pack["output_standards_version"] = "overseas-video-output-standards-v2"
    return pack
