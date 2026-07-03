"""人像角色素材库：三视图解析、选人、分镜垫图与 Prompt 锚定。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from paths import MATERIAL_LIBRARY_DIR, WORKFLOW_ROOT

from .product_assets import get_product_usage_pour_image, get_product_white_hero_image, product_listing_dir, resolve_staged_seedance_source

CHARACTER_LIBRARY_DIR = MATERIAL_LIBRARY_DIR / "人像角色"
MANIFEST_PATH = CHARACTER_LIBRARY_DIR / "characters.json"

PERSON_SHOT_ROLES = frozenset({"钩子", "痛点", "方案", "行动号召"})
PRODUCT_FOCUS_ROLES = frozenset({"证明"})


def _rel(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return path.relative_to(WORKFLOW_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_character_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        return {"characters": [], "selection": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def list_characters() -> list[dict[str, Any]]:
    return list(load_character_manifest().get("characters") or [])


def _character_by_id(char_id: str) -> dict[str, Any] | None:
    for row in list_characters():
        if row.get("id") == char_id:
            return row
    return None


def resolve_character(market: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """按人群标签选择已批准出镜角色；默认女性照护者。"""
    manifest = load_character_manifest()
    chars = manifest.get("characters") or []
    if not chars:
        return None
    market = market or {}
    audience = [str(t) for t in (market.get("audience_tags") or [])]
    blob = " ".join(audience)
    sel = manifest.get("selection") or {}
    male_keys = sel.get("male_audience_keywords") or ["爸爸", "奶爸", "父亲"]
    female_keys = sel.get("female_audience_keywords") or ["妈妈", "母亲", "宝妈", "夜奶"]
    pick_male = any(k in blob for k in male_keys) and not any(k in blob for k in female_keys)
    target_gender = "male" if pick_male else "female"
    for row in chars:
        if row.get("gender") == target_gender and row.get("approval_status") == "approved":
            return row
    default_id = sel.get("default_character_id")
    if default_id:
        return _character_by_id(str(default_id))
    return chars[0]


def character_view_path(character: dict[str, Any], view: str) -> Path | None:
    rel = (character.get("views") or {}).get(view)
    if not rel:
        return None
    path = CHARACTER_LIBRARY_DIR / str(rel)
    return path if path.is_file() else None


def pick_character_view(role: str, *, visual: str = "") -> str:
    """按镜头角色选择三视图角度。"""
    role = (role or "").strip()
    visual_blob = visual or ""
    if role == "方案" or "倒" in visual_blob or "握" in visual_blob:
        return "side"
    if role == "痛点" and ("背影" in visual_blob or "离开" in visual_blob):
        return "back"
    if role in ("证明",):
        return "front"
    return "front"


def shot_needs_person(role: str, footage_type: str | None = None) -> bool:
    role = (role or "").strip()
    if role in PRODUCT_FOCUS_ROLES:
        return False
    if role in PERSON_SHOT_ROLES:
        return True
    ft = (footage_type or "").strip()
    return ft in ("AI_VIDEO",) and role not in PRODUCT_FOCUS_ROLES


PRODUCT_VISIBLE_ROLES = frozenset({"钩子", "方案", "证明", "行动号召"})


def _staged_path(project: Path | None, pattern: str) -> Path | None:
    if not project:
        return None
    if pattern == "seedance-source.*":
        return resolve_staged_seedance_source(project)
    inputs = project / "inputs"
    if not inputs.is_dir():
        return None
    if "*" in pattern:
        for path in sorted(inputs.glob(pattern)):
            if path.is_file():
                return path
        return None
    path = inputs / pattern
    return path if path.is_file() else None


def shot_includes_product(role: str, visual: str = "", footage_type: str | None = None) -> bool:
    role = (role or "").strip()
    if role in PRODUCT_FOCUS_ROLES | PRODUCT_VISIBLE_ROLES:
        return True
    ft = (footage_type or "").strip()
    if ft == "AI_BROLL":
        return True
    blob = f"{visual} {role}".lower()
    keys = ("thermos", "cup", "bottle warmer", "杯", "奶瓶", "恒温", "倒", "握", "warm milk", "product")
    return any(k in blob or k in (visual or "") for k in keys)


def pick_shot_reference_path(
    *,
    product_id: str,
    role: str,
    character: dict[str, Any] | None,
    visual: str = "",
    footage_type: str | None = None,
    project: Path | None = None,
) -> tuple[Path | None, str]:
    """
    返回 (本地绝对路径, 资产类型)。
    资产类型: person | product_identity

    硬性规定：产品可见镜头的 SeedDance I2V 垫图只能是白底主图；场景图/倒出口参考仅 Prompt。
    """
    role = (role or "").strip()
    white = get_product_white_hero_image(product_id)

    if role in PRODUCT_FOCUS_ROLES:
        staged_white = _staged_path(project, "seedance-source.*")
        if staged_white:
            return staged_white, "product_identity"
        return white, "product_identity"

    if role in ("方案", "证明"):
        staged_white = _staged_path(project, "seedance-source.*")
        if staged_white:
            return staged_white, "product_identity"
        return white, "product_identity"

    ft = (footage_type or "").strip()
    if shot_includes_product(role, visual, footage_type) and ft in ("AI_BROLL", "AI_VIDEO", "LIVE_ACTION", ""):
        staged_white = _staged_path(project, "seedance-source.*")
        if staged_white:
            return staged_white, "product_identity"
        if white:
            return white, "product_identity"

    if character and shot_needs_person(role, footage_type) and not shot_includes_product(role, visual, footage_type):
        view = pick_character_view(role, visual=visual)
        cref = character_view_path(character, view)
        if project:
            staged = project / "inputs" / "characters" / str(character.get("id", "char")) / f"{view}.png"
            if staged.is_file():
                return staged, "person"
        if cref:
            return cref, "person"

    staged_white = _staged_path(project, "seedance-source.*")
    if staged_white:
        return staged_white, "product_identity"
    return white, "product_identity"


def build_character_prompt_block(character: dict[str, Any] | None) -> str:
    if not character:
        return "product-only or hands-only; no invented face"
    return (
        f"same approved caregiver as reference: {character.get('label', '')}; "
        f"wardrobe {character.get('wardrobe', '')}; match likeness and realistic hand physics"
    )


def build_character_continuity(market: dict[str, Any] | None, product_id: str) -> dict[str, Any]:
    character = resolve_character(market)
    if not character:
        return {
            "role": "product-only",
            "visibility": "hands-only or product hero",
            "notes": "人像角色库为空，退化为产品/手部镜头",
            "source_refs": [],
        }
    refs = []
    for view in ("front", "side", "back"):
        path = character_view_path(character, view)
        if path:
            refs.append({"view": view, "path": _rel(path)})
    return {
        "character_id": character.get("id"),
        "label": character.get("label"),
        "gender": character.get("gender"),
        "role": "caregiver parent",
        "age_range": character.get("age_range"),
        "wardrobe": character.get("wardrobe"),
        "hair": character.get("hair"),
        "beard": character.get("beard", ""),
        "visibility": "approved reference — match front/side/back per shot",
        "emotional_state": character.get("emotional_state", "calm, practical"),
        "relationship_to_product": character.get("relationship_to_product"),
        "allowed_scene_changes": [],
        "source_refs": refs,
        "notes": "人像镜头用三视图垫图；产品可见镜头一律白底主图垫图，场景图/倒出口参考仅写入 Prompt",
    }


def build_person_asset_manifest_entries() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for character in list_characters():
        if character.get("approval_status") != "approved":
            continue
        for view, rel in (character.get("views") or {}).items():
            path = CHARACTER_LIBRARY_DIR / str(rel)
            if not path.is_file():
                continue
            rows.append({
                "asset_id": f"character:{character.get('id')}:{view}",
                "product": "*",
                "source_path": _rel(path),
                "asset_type": "person",
                "approval_status": "approved",
                "allowed_use": character.get("allowed_use", "on-camera caregiver reference"),
                "forbidden_use": character.get("forbidden_use", "inconsistent identity"),
                "person_profile": character.get("id"),
                "shot_roles": list(PERSON_SHOT_ROLES),
                "notes": f"{character.get('label')} · {view} view",
            })
    return rows


def stage_project_character_refs(project: Path, character: dict[str, Any] | None) -> Path | None:
    """复制角色三视图到项目 inputs/characters/{id}/。"""
    if not character:
        return None
    char_id = str(character.get("id") or "character")
    dest_root = project / "inputs" / "characters" / char_id
    dest_root.mkdir(parents=True, exist_ok=True)
    staged_any = False
    for view in ("front", "side", "back"):
        src = character_view_path(character, view)
        if not src:
            continue
        dest = dest_root / f"{view}{src.suffix.lower()}"
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
        staged_any = True
    if staged_any:
        manifest = {
            "character_id": char_id,
            "label": character.get("label"),
            "views": {
                view: f"inputs/characters/{char_id}/{view}.png"
                for view in ("front", "side", "back")
                if (dest_root / f"{view}.png").is_file()
            },
        }
        (project / "inputs" / "character-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return dest_root
    return None


def stage_project_production_assets(
    project: Path,
    product_id: str,
    market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """交付前注入白底主图垫图 + 倒出口参考 + 角色三视图。"""
    from .product_assets import get_product_usage_pour_image, stage_seedance_source_image

    character = resolve_character(market)
    product_ref = stage_seedance_source_image(project, product_id)
    pour = get_product_usage_pour_image(product_id)
    usage_ref = ""
    if pour:
        inputs = project / "inputs"
        inputs.mkdir(parents=True, exist_ok=True)
        usage_dest = inputs / f"seedance-usage-ref{pour.suffix.lower()}"
        if not usage_dest.exists() or usage_dest.stat().st_size != pour.stat().st_size:
            shutil.copy2(pour, usage_dest)
        usage_ref = _rel(usage_dest)
    char_dir = stage_project_character_refs(project, character)
    return {
        "product_ref": _rel(product_ref) if product_ref else "",
        "usage_ref": usage_ref,
        "character_id": character.get("id") if character else "",
        "character_refs": _rel(char_dir) if char_dir else "",
    }
