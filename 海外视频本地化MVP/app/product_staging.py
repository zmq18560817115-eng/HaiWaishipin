"""固定产品垫图：出片前强制白底主图 + 倒出口参考注入（便携恒温杯）。"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .character_assets import (
    get_product_usage_pour_image,
    resolve_staged_seedance_source,
    stage_project_character_refs,
)
from .product_assets import get_product_white_hero_image, stage_seedance_source_image

FIXED_PRODUCT_IDS = frozenset({"便携恒温杯"})


def is_fixed_product(product_id: str) -> bool:
    return str(product_id or "").strip() in FIXED_PRODUCT_IDS


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_manifest(project: Path, payload: dict[str, Any]) -> None:
    path = project / "inputs" / "product-staging.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def force_stage_product_assets(
    project: Path,
    product_id: str,
    *,
    market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .character_assets import resolve_character

    pid = str(product_id or "").strip()
    hero_src = get_product_white_hero_image(pid)
    if not hero_src:
        raise ValueError(f"缺少白底主图：01_素材库/产品资料/{pid}/listing-0602-nw/主图/白底主图.png")

    product_ref_path = stage_seedance_source_image(project, pid)
    if not product_ref_path or not product_ref_path.is_file():
        raise ValueError("白底主图注入失败，无法生成视频")

    pour_src = get_product_usage_pour_image(pid)
    usage_ref_path: Path | None = None
    inputs = project / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for old in inputs.glob("seedance-usage-ref.*"):
        try:
            old.unlink()
        except OSError:
            pass
    if pour_src and pour_src.is_file():
        usage_ref_path = inputs / f"seedance-usage-ref{pour_src.suffix.lower()}"
        shutil.copy2(pour_src, usage_ref_path)

    character = resolve_character(market)
    char_dir = stage_project_character_refs(project, character)

    manifest = {
        "product_id": pid,
        "fixed_product_lock": is_fixed_product(pid),
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "hero_source": str(hero_src),
        "hero_sha256": _sha256(hero_src),
        "hero_staged": product_ref_path.name,
        "usage_source": str(pour_src) if pour_src else "",
        "usage_sha256": _sha256(pour_src) if pour_src and pour_src.is_file() else "",
        "usage_staged": usage_ref_path.name if usage_ref_path else "",
        "i2v_rule": "白底主图唯一 I2V 垫图；人像仅 Prompt；倒出口参考仅 Prompt",
    }
    _write_manifest(project, manifest)
    return {
        "product_ref": product_ref_path.relative_to(project).as_posix(),
        "usage_ref": usage_ref_path.relative_to(project).as_posix() if usage_ref_path else "",
        "character_refs": char_dir.relative_to(project).as_posix() if char_dir else "",
        "manifest": manifest,
    }


def validate_product_staging(project: Path, product_id: str) -> dict[str, Any]:
    pid = str(product_id or "").strip()
    hero_src = get_product_white_hero_image(pid)
    staged = resolve_staged_seedance_source(project)
    errors: list[str] = []
    if not hero_src:
        errors.append("缺少白底主图源文件")
    if not staged or not staged.is_file():
        errors.append("项目内未注入 seedance-source 白底主图")
    elif hero_src and _sha256(staged) != _sha256(hero_src):
        errors.append("seedance-source 与白底主图不一致，请重新交付或出片")

    return {
        "ok": not errors,
        "product_id": pid,
        "fixed_product_lock": is_fixed_product(pid),
        "errors": errors,
        "hero_source": str(hero_src) if hero_src else "",
        "hero_staged": staged.relative_to(project).as_posix() if staged else "",
    }
