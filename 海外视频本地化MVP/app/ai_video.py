"""与 overseas-loc-mvp/app/ai_video.py 保持一致的脚本侧配置。"""
from __future__ import annotations

import os
import re
from typing import Any

from .character_assets import build_character_prompt_block, shot_needs_person
from .product_usage import THERMOS_PRODUCT_EN, THERMOS_STRUCTURE_EN

AI_VIDEO_FOOTAGE = frozenset({"AI_BROLL", "AI_VIDEO"})
SEEDANCE_PROMPT_LIMIT = 1990


def ai_video_mode() -> str:
    return (os.getenv("AI_VIDEO_MODE") or "broll").strip().lower()


def default_footage_for_role(role: str) -> str:
    if ai_video_mode() == "script":
        return "AI_VIDEO"
    return "AI_BROLL" if role == "痛点" else "LIVE_ACTION"


def _safe_suffix(character: dict[str, Any] | None, role: str) -> str:
    lighting = "motivated key light, soft shadows, natural reflections, realistic exposure"
    fidelity = (
        "match white-background hero product appearance exactly, no redesign; "
        "physics-safe pour and hand motion; scenario-consistent props"
    )
    if character and shot_needs_person(role):
        return (
            f"vertical 9:16, TikTok product ad style, no medical claim, "
            f"same person identity across all shots, {lighting}, {fidelity}"
        )
    return (
        f"no person face, no medical claim, vertical 9:16, TikTok product ad style, "
        f"{lighting}, {fidelity}"
    )


def _clamp_prompt(text: str, limit: int = SEEDANCE_PROMPT_LIMIT) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= limit:
        return t
    return t[: limit - 3].rstrip() + "..."


def sanitize_seedance_prompt(text: str) -> str:
    return _clamp_prompt(text, SEEDANCE_PROMPT_LIMIT)


def _usage_compact() -> str:
    return (
        "Portable thermos cup warms milk inside; pour body-warm milk OUT through lid spout into baby bottle; "
        "Fahrenheit °F display ~98°F only, no °C; no steam or boiling; "
        "never put bottle inside cup; match white-background hero and pour-spout reference exactly"
    )


def _structure_compact() -> str:
    return THERMOS_STRUCTURE_EN[:280]


def build_role_video_prompt(
    role: str,
    profile: dict[str, Any],
    product_name: str,
    voiceover_en: str,
    *,
    character: dict[str, Any] | None = None,
) -> str:
    scene_en = str(profile.get("en") or "daily baby feeding")
    vo = re.sub(r"\s+", " ", (voiceover_en or "").strip())[:120]
    safe = _safe_suffix(character, role)
    person = build_character_prompt_block(character) if character and shot_needs_person(role) else ""
    cup = THERMOS_PRODUCT_EN
    prod = product_name or cup
    usage = _usage_compact()
    structure = _structure_compact()

    if role == "痛点" and profile.get("seedance") and not (character and shot_needs_person(role)):
        return _clamp_prompt(f"{profile['seedance']} {usage} {structure}")

    if role == "钩子":
        if character and shot_needs_person(role):
            return _clamp_prompt(
                f"Hook opening, {scene_en}, {person}, medium shot holding {cup} beside separate baby bottle "
                f"on bedside table, warm soft light, subtle push-in, {safe}. {usage}. Mood: {vo or 'attention grabbing'}"
            )
        return _clamp_prompt(
            f"Hook shot opening, {scene_en}, sharp close-up of {cup} product hero on bedside table, "
            f"separate baby bottle beside it, cinematic soft light, subtle push-in, {safe}. "
            f"{usage}. Mood: {vo or 'attention grabbing'}"
        )
    if role == "痛点":
        if character and shot_needs_person(role):
            return _clamp_prompt(
                f"Problem moment, {scene_en}, {person}, frustrated with cold milk in baby bottle, "
                f"bulky old bottle warmer in background, moody lighting, realistic hand physics, {safe}. "
                f"{usage}. {vo}"
            )
        return _clamp_prompt(
            f"Problem moment, {scene_en}, cold milk in baby bottle, bulky old bottle warmer contrast, "
            f"moody lighting, {safe}. {usage}. {vo}"
        )
    if role == "方案":
        if character and shot_needs_person(role):
            return _clamp_prompt(
                f"Product demo, {scene_en}, {person}, side angle — flip-top lid open, pour milk INTO {cup}, "
                f"tilt to pour warm milk OUT from lid spout into baby feeding bottle, realistic pour physics, "
                f"vertical display visible, {safe}. {usage}. {structure}. {vo}"
            )
        return _clamp_prompt(
            f"Product demo, {scene_en}, flip-top lid open — pour milk INTO {cup}; tilt to pour warm milk OUT "
            f"from lid spout into baby feeding bottle, {safe}. {usage}. {structure}. {vo}"
        )
    if role == "证明":
        return _clamp_prompt(
            f"Proof detail, {scene_en}, macro shot of body-warm milk pouring OUT from lid spout of {cup} "
            f"into baby feeding bottle, no steam plume or boiling bubbles, hinged lid open, {safe}. {usage}. {structure}. {vo}"
        )
    if role == "行动号召":
        if character and shot_needs_person(role):
            return _clamp_prompt(
                f"CTA closing, {scene_en}, {person}, smiling to camera with {cup} and baby bottle on clean surface, "
                f"flip-top lid closed, digital display visible, natural gesture, {safe}. {usage}. {vo}"
            )
        return _clamp_prompt(
            f"CTA closing, {scene_en}, {cup} with flip-top lid closed on clean surface, baby bottle beside, "
            f"digital display visible, {safe}. {usage}. {vo}"
        )
    return _clamp_prompt(f"{scene_en}, {prod}, cinematic product b-roll, {safe}. {usage}. {vo}")
