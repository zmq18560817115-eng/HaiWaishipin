"""视频 / 脚本反推 → 提示词库。"""
from __future__ import annotations

from typing import Any

from .brand_policy import detect_content_line
from .data import load_analysis_detail, load_materials, material_detail
from .prompt_library import material_content_line, upsert_many


STRUCTURE_LABELS = {
    "hook": "钩子",
    "demo": "演示",
    "proof": "验证",
    "cta": "引导",
    "transition": "转场",
}


def _shot_en_prompt(shot: dict[str, Any]) -> str:
    parts = [
        str(shot.get("camera_action") or "").strip(),
        str(shot.get("visual_description") or shot.get("visual") or "").strip(),
    ]
    role = str(shot.get("structure_role") or "").strip()
    if role:
        parts.append(f"Structure: {role}")
    scene = str(shot.get("scene_type") or "").strip()
    if scene:
        parts.append(f"Scene: {scene}")
    return ". ".join(p for p in parts if p)


def _shot_cn_note(shot: dict[str, Any]) -> str:
    return (
        str(shot.get("reuse_note") or "").strip()
        or str(shot.get("visual_description") or "").strip()
    )


def reverse_from_video(material: dict[str, Any], detail: dict[str, Any]) -> list[dict[str, Any]]:
    shots = detail.get("shots") or []
    if not shots:
        analysis = detail.get("analysis") or material.get("analysis") or {}
        if not analysis:
            return []
        text = "\n".join(
            filter(
                None,
                [
                    analysis.get("hook_3s"),
                    analysis.get("video_structure"),
                    analysis.get("reusable_template"),
                ],
            )
        ).strip()
        if not text:
            return []
        line = material_content_line(material)
        return [
            {
                "source": "reverse_video",
                "reverse_type": "video",
                "link_id": material.get("link_id"),
                "material_title": material.get("title", ""),
                "content_line": line,
                "product_id": line,
                "label": f"视频反推 · {material.get('title', '')[:20] or material.get('link_id')}",
                "prompt_text": text,
                "prompt_text_en": "",
                "structure_role": "full",
                "shot_index": -1,
                "tags": ["reverse", "structure"],
            }
        ]

    entries: list[dict[str, Any]] = []
    line = material_content_line(material)
    title = (material.get("title") or f"#{material.get('link_id')}").strip()[:32]

    for shot in shots:
        idx = int(shot.get("index", len(entries)))
        role = str(shot.get("structure_role") or "shot")
        role_zh = STRUCTURE_LABELS.get(role, role)
        en = _shot_en_prompt(shot)
        cn = _shot_cn_note(shot)
        entries.append(
            {
                "source": "reverse_video",
                "reverse_type": "video",
                "link_id": material.get("link_id"),
                "material_title": material.get("title", ""),
                "content_line": line,
                "product_id": line,
                "label": f"{title} · {role_zh}",
                "prompt_text": cn or en,
                "prompt_text_en": en,
                "structure_role": role,
                "shot_index": idx,
                "tags": ["reverse", "video", role],
            }
        )

    composite_en = "\n\n".join(
        f"Shot {i + 1} ({s.get('structure_role', 'shot')}): {_shot_en_prompt(s)}"
        for i, s in enumerate(shots)
    )
    composite_cn = "\n".join(
        f"{i + 1}. [{STRUCTURE_LABELS.get(str(s.get('structure_role') or ''), s.get('structure_role'))}] "
        f"{_shot_cn_note(s)}"
        for i, s in enumerate(shots)
    )
    entries.append(
        {
            "source": "reverse_video",
            "reverse_type": "video",
            "link_id": material.get("link_id"),
            "material_title": material.get("title", ""),
            "content_line": line,
            "product_id": line,
            "label": f"完整分镜 · {title}",
            "prompt_text": composite_cn,
            "prompt_text_en": composite_en,
            "structure_role": "full",
            "shot_index": -1,
            "tags": ["reverse", "video", "full"],
        }
    )
    return entries


def reverse_from_script(material: dict[str, Any], detail: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = detail.get("analysis") or material.get("analysis") or {}
    pack = material.get("script_pack") or {}
    storyboard = pack.get("storyboard") or []

    entries: list[dict[str, Any]] = []
    line = material_content_line(material)
    title = (material.get("title") or f"#{material.get('link_id')}").strip()[:32]

    if storyboard:
        for i, shot in enumerate(storyboard):
            role = str(shot.get("structure_role") or shot.get("footage_type") or "shot")
            cn = str(shot.get("visual_prompt") or shot.get("visual") or shot.get("dialogue") or "").strip()
            en = str(shot.get("seedance_prompt") or "").strip()
            entries.append(
                {
                    "source": "reverse_script",
                    "reverse_type": "script",
                    "link_id": material.get("link_id"),
                    "material_title": material.get("title", ""),
                    "content_line": line,
                    "product_id": line,
                    "label": f"脚本镜 {i + 1} · {title}",
                    "prompt_text": cn,
                    "prompt_text_en": en,
                    "structure_role": role,
                    "shot_index": i,
                    "tags": ["reverse", "script", role],
                }
            )

    if analysis:
        sections = [
            ("钩子", analysis.get("hook_3s")),
            ("痛点", analysis.get("pain_points")),
            ("卖点", analysis.get("selling_points")),
            ("结构", analysis.get("video_structure")),
            ("模板", analysis.get("reusable_template")),
            ("CTA", analysis.get("cta")),
        ]
        text = "\n\n".join(f"【{name}】{val}" for name, val in sections if val)
        if text:
            entries.append(
                {
                    "source": "reverse_script",
                    "reverse_type": "script",
                    "link_id": material.get("link_id"),
                    "material_title": material.get("title", ""),
                    "content_line": line,
                    "product_id": line,
                    "label": f"脚本结构 · {title}",
                    "prompt_text": text,
                    "prompt_text_en": "",
                    "structure_role": "structure",
                    "shot_index": -1,
                    "tags": ["reverse", "script", "structure"],
                }
            )

    return entries


def run_reverse_prompt(
    link_id: int,
    *,
    reverse_type: str = "video",
    product_id: str = "",
    save: bool = True,
) -> dict[str, Any]:
    material = material_detail(link_id)
    if not material:
        raise ValueError("素材不存在")
    detail = load_analysis_detail(str(link_id)) or {}
    if not detail.get("shots") and not detail.get("analysis") and not material.get("script_pack"):
        raise ValueError("素材尚未拆解，请先在设置中运行结构拆解")

    if reverse_type == "script":
        entries = reverse_from_script(material, {**detail, **material})
    else:
        entries = reverse_from_video(material, detail)

    if not entries:
        raise ValueError("无法从该素材反推提示词，请确认已完成分镜或结构拆解")

    if product_id:
        for row in entries:
            row["product_id"] = product_id
            row["content_line"] = product_id

    line = product_id or material_content_line(material)
    primary = entries[-1]
    primary_text = primary.get("prompt_text_en") or primary.get("prompt_text") or ""

    saved = upsert_many(entries) if save else entries
    return {
        "ok": True,
        "link_id": link_id,
        "reverse_type": reverse_type,
        "content_line": line or detect_content_line(material),
        "saved_count": len(saved),
        "items": saved,
        "primary_prompt": primary_text,
        "composite_label": primary.get("label", ""),
    }
