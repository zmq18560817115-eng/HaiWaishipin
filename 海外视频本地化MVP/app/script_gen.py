from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import GENERATED_SCRIPTS_DIR, MVP_ROOT, OVERSEAS_RUNS_DIR

from .brand_policy import (
    detect_content_line,
    display_product_name,
    product_material_match,
    sanitize_analysis,
)
from .product_assets import stage_seedance_source_image
from .character_assets import stage_project_production_assets
from .product_tags import validate_delivery_selection
from .data import ANALYSIS_FIELDS, load_analysis, material_detail
from .llm_script import generate_script_pack, normalize_pack, pack_to_bridge_shots, pack_to_markdown

SHOT_EDIT_FIELDS = (
    "visual",
    "voiceover_en",
    "subtitle_en",
    "visual_prompt",
    "seedance_prompt",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pick_product(products: list[dict[str, str]], product_id: str) -> dict[str, str]:
    if product_id:
        for row in products:
            if row.get("product_id") == product_id:
                return row
    preferred_ids = ("便携恒温杯", "吸奶器")
    for pid in preferred_ids:
        for row in products:
            if row.get("product_id") == pid:
                return row
    for row in products:
        name = row.get("product_name", "")
        if "恒温杯" in name:
            return row
    for row in products:
        name = row.get("product_name", "")
        if "吸奶器" in name:
            return row
    return products[0] if products else {}


def generate_script(
    link_id: int,
    product_id: str = "",
    bridge: bool = False,
    market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detail = material_detail(link_id)
    if not detail:
        raise ValueError("素材不存在")
    analysis = detail.get("analysis")
    if not analysis:
        raise ValueError("该素材尚未结构拆解，请先在「设置」运行「结构拆解」")

    product = _pick_product(detail.get("products") or [], product_id)
    pid = product.get("product_id", "")
    if market is None:
        market = {}
    validated = validate_delivery_selection(market)
    market.update(validated)
    content_line = detect_content_line(detail)
    analysis = sanitize_analysis(analysis, pid)
    title = detail.get("title") or f"ref-{link_id:03d}"
    source_url = detail.get("url", "")

    pack, meta = generate_script_pack(
        product=product,
        analysis=analysis,
        video_title=title,
        source_url=source_url,
        market=market,
    )
    shots = pack_to_bridge_shots(pack)
    md = pack_to_markdown(pack, source_url)

    out_dir = GENERATED_SCRIPTS_DIR / str(link_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "link_id": link_id,
        "title": pack.get("title", title),
        "subtitle": pack.get("subtitle", ""),
        "voiceover_20s": pack.get("voiceover_20s", ""),
        "storyboard": pack.get("storyboard", shots),
        "subtitle_copy": pack.get("subtitle_copy", []),
        "visual_prompts": pack.get("visual_prompts", []),
        "seedance_prompts": pack.get("seedance_prompts", []),
        "product_id": product.get("product_id", ""),
        "product_name": product.get("product_name", ""),
        "audience_tags": market.get("audience_tags", []),
        "scenario_tags": market.get("scenario_tags", []),
        "selling_tags": market.get("selling_tags", []),
        "pain_tags": market.get("pain_tags", []),
        "aspect_ratio": market.get("aspect_ratio", "9:16"),
        "edit_mode": market.get("edit_mode", "multi_shot"),
        "resolution": market.get("resolution", "720P"),
        "duration_sec": market.get("duration_sec", 5),
        "generate_count": market.get("generate_count", 1),
        "creative_brief": market.get("creative_brief", ""),
        "prompt_enhanced": bool(market.get("prompt_enhanced")),
        "source_url": source_url,
        "shots": shots,
        "generated_at": utc_now(),
        "provider": meta.get("provider", ""),
        "model": meta.get("model", ""),
    }
    (out_dir / "script-pack.json").write_text(
        json.dumps({"pack": pack, "meta": meta, "payload": payload}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "script-pack.md").write_text(md, encoding="utf-8")
    (out_dir / "analysis-snapshot.json").write_text(
        json.dumps({k: analysis.get(k, "") for k in ANALYSIS_FIELDS}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    bridged_slug = ""
    if bridge:
        bridged_slug = _bridge(link_id, pack=pack, shots=shots, force=True, payload_extra={
            "audience_tags": market.get("audience_tags", []),
            "scenario_tags": market.get("scenario_tags", []),
            "product_id": pid,
        })

    return {
        **payload,
        "script_pack": pack,
        "meta": meta,
        "markdown": md,
        "output_dir": str(out_dir),
        "content_line": content_line,
        "product_match": product_material_match(pid, detail),
        "brand_product": display_product_name(pid),
        "bridged_slug": bridged_slug,
    }


def _bridge(
    link_id: int,
    pack: dict[str, Any],
    shots: list[dict[str, str]],
    force: bool = False,
    payload_extra: dict[str, Any] | None = None,
) -> str:
    slug = f"ref-{link_id:03d}"
    cmd = [sys.executable, str(MVP_ROOT / "scripts" / "pipeline.py"), "bridge", "--id", str(link_id)]
    if force:
        cmd.append("--force")
    subprocess.run(cmd, cwd=str(MVP_ROOT), check=True, capture_output=True, text=True, encoding="utf-8")

    proj = OVERSEAS_RUNS_DIR / slug
    if proj.exists():
        gen_pack_path = GENERATED_SCRIPTS_DIR / str(link_id) / "script-pack.json"
        if gen_pack_path.is_file():
            try:
                raw = json.loads(gen_pack_path.read_text(encoding="utf-8"))
                pack_doc = raw if isinstance(raw.get("pack"), dict) and isinstance(raw.get("payload"), dict) else {
                    "pack": pack,
                    "payload": raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
                }
                pack_text = json.dumps(pack_doc, ensure_ascii=False, indent=2) + "\n"
            except (json.JSONDecodeError, OSError):
                pack_text = json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
        else:
            pack_text = json.dumps(pack, ensure_ascii=False, indent=2) + "\n"
        (proj / "script-pack.json").write_text(pack_text, encoding="utf-8")
        # Keep delivery pack in sync so SeedDance reads the latest scenario prompts.
        (proj / "交付脚本包.json").write_text(pack_text, encoding="utf-8")
        if shots:
            (proj / "storyboard.json").write_text(
                json.dumps({"shots": shots}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        if payload_extra:
            brief_path = proj / "localization-brief.yaml"
            if brief_path.exists():
                try:
                    import yaml

                    brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
                    brief["audience_tags"] = payload_extra.get("audience_tags") or []
                    brief["scenario_tags"] = payload_extra.get("scenario_tags") or []
                    brief_path.write_text(
                        yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8"
                    )
                except Exception:
                    pass
            product_id = str(payload_extra.get("product_id") or "").strip()
            if product_id:
                stage_project_production_assets(
                    proj,
                    product_id,
                    {
                        "audience_tags": payload_extra.get("audience_tags") or [],
                        "scenario_tags": payload_extra.get("scenario_tags") or [],
                    },
                )
    return slug


def recompute_pack_derivatives(pack: dict[str, Any]) -> dict[str, Any]:
    storyboard = pack.get("storyboard") or []
    pack["subtitle_copy"] = [str(s.get("subtitle_en") or "") for s in storyboard]
    pack["visual_prompts"] = [str(s.get("visual_prompt") or s.get("visual") or "") for s in storyboard]
    pack["seedance_prompts"] = [
        str(s.get("seedance_prompt") or "")
        for s in storyboard
        if s.get("footage_type") in ("AI_BROLL", "AI_VIDEO") and s.get("seedance_prompt")
    ]
    voiceover = str(pack.get("voiceover_20s") or "").strip()
    if not voiceover and storyboard:
        voiceover = " ".join(str(s.get("voiceover_en") or "") for s in storyboard if s.get("voiceover_en"))
    pack["voiceover_20s"] = voiceover
    return pack


def apply_pack_edits(pack: dict[str, Any], edits: dict[str, Any]) -> dict[str, Any]:
    out = dict(pack)
    for key in ("title", "subtitle", "voiceover_20s"):
        if key in edits:
            out[key] = str(edits.get(key) or "").strip()

    incoming = edits.get("storyboard") or []
    if incoming:
        existing = list(out.get("storyboard") or [])
        merged: list[dict[str, Any]] = []
        for idx, row in enumerate(incoming):
            base = dict(existing[idx]) if idx < len(existing) else {}
            if row.get("number") is not None:
                base["number"] = int(row.get("number") or idx + 1)
            else:
                base["number"] = idx + 1
            for field in SHOT_EDIT_FIELDS:
                if field in row:
                    base[field] = str(row.get(field) or "").strip()
            for keep in ("role", "timing", "footage_type"):
                if row.get(keep) not in (None, ""):
                    base[keep] = row.get(keep)
            merged.append(base)
        out["storyboard"] = merged

    return recompute_pack_derivatives(normalize_pack(out))


def _sync_saved_pack_to_project(link_id: int, doc: dict[str, Any], shots: list[dict[str, str]]) -> str:
    slug = f"ref-{link_id:03d}"
    proj = OVERSEAS_RUNS_DIR / slug
    if not proj.exists():
        return slug
    pack_text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    (proj / "script-pack.json").write_text(pack_text, encoding="utf-8")
    (proj / "交付脚本包.json").write_text(pack_text, encoding="utf-8")
    if shots:
        (proj / "storyboard.json").write_text(
            json.dumps({"shots": shots}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return slug


def save_script_edits(link_id: int, edits: dict[str, Any]) -> dict[str, Any]:
    detail = material_detail(link_id)
    if not detail:
        raise ValueError("素材不存在")
    out_dir = GENERATED_SCRIPTS_DIR / str(link_id)
    pack_path = out_dir / "script-pack.json"
    if not pack_path.is_file():
        raise ValueError("尚未生成脚本，请先生成脚本")

    raw = json.loads(pack_path.read_text(encoding="utf-8"))
    pack = raw.get("pack") if isinstance(raw.get("pack"), dict) else raw
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}

    pack = apply_pack_edits(pack, edits)
    shots = pack_to_bridge_shots(pack)
    source_url = str(payload.get("source_url") or detail.get("url") or "")
    md = pack_to_markdown(pack, source_url)

    payload.update({
        "title": pack.get("title", ""),
        "subtitle": pack.get("subtitle", ""),
        "voiceover_20s": pack.get("voiceover_20s", ""),
        "storyboard": pack.get("storyboard", []),
        "subtitle_copy": pack.get("subtitle_copy", []),
        "visual_prompts": pack.get("visual_prompts", []),
        "seedance_prompts": pack.get("seedance_prompts", []),
        "shots": shots,
        "edited_at": utc_now(),
    })
    doc = {"pack": pack, "meta": meta, "payload": payload}
    pack_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "script-pack.md").write_text(md, encoding="utf-8")

    slug = _sync_saved_pack_to_project(link_id, doc, shots)
    return {
        "link_id": link_id,
        "slug": slug,
        "script_pack": pack,
        "meta": meta,
        "edited": True,
        "message": "脚本修改已保存，将按当前内容生成视频",
    }
