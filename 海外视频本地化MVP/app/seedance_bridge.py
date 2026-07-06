"""通过 overseas-loc-mvp 子进程调用 SeedDance 2.0（fal.ai）。"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from paths import OVERSEAS_ENV, OVERSEAS_MVP_DIR, OVERSEAS_RUNS_DIR

from .olm_bridge import _olm_python, ensure_ffmpeg_ready
from .character_assets import stage_project_production_assets


def _ai_video_mode() -> str:
    env = dotenv_values(OVERSEAS_ENV)
    return (env.get("AI_VIDEO_MODE") or "broll").strip().lower()


def _pipeline_label() -> str:
    if _ai_video_mode() == "script":
        return "脚本生成 → 分镜 → 各镜 Prompt → SeedDance 2.0 → 分镜短视频 → 成稿 zip"
    return "脚本生成 → 分镜生成 → 视频 Prompt → SeedDance 2.0 → 输出视频 → 保存成稿"


SEEDANCE_PIPELINE = _pipeline_label()

_OLM_ENV_PREFIXES = ("AI_VIDEO_", "ARK_", "SEEDANCE_", "FAL_", "SKIP_SEEDANCE", "HERO_FRAME_")


def _olm_subprocess_env() -> dict[str, str]:
    """子进程环境：overseas-loc-mvp/.env 优先于父 shell，避免 AI_VIDEO_MAX_SHOTS 等泄漏。"""
    merged = {k: v for k, v in os.environ.items() if v is not None}
    for key, value in dotenv_values(OVERSEAS_ENV).items():
        if value is None:
            continue
        if key.startswith(_OLM_ENV_PREFIXES) or key in ("ARK_API_KEY", "FAL_KEY"):
            merged[key] = value
    merged["PYTHONIOENCODING"] = "utf-8"
    merged["PYTHONUTF8"] = "1"
    return merged


def _run_olm(code: str, *args: str) -> dict[str, Any]:
    proc = subprocess.run(
        [str(_olm_python()), "-c", code, *args],
        cwd=str(OVERSEAS_MVP_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_olm_subprocess_env(),
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "SeedDance 调用失败")[-800:]
        raise RuntimeError(tail)
    lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("SeedDance 无输出")
    return json.loads(lines[-1])


def seedance_config() -> dict[str, Any]:
    env = dotenv_values(OVERSEAS_ENV)
    ark_key = (env.get("ARK_API_KEY") or "").strip()
    fal_key = (env.get("FAL_KEY") or "").strip()
    provider = (env.get("SEEDANCE_PROVIDER") or "").strip().lower()
    if not provider:
        provider = "ark" if ark_key else ("fal" if fal_key else "")
    use_fast = (env.get("SEEDANCE_USE_FAST") or "0").strip().lower() in ("1", "true", "yes")
    if provider == "ark":
        text_model = (env.get("ARK_SEEDANCE_TEXT_MODEL") or "doubao-seedance-2-0-260128").strip()
        if use_fast:
            text_model = (env.get("ARK_SEEDANCE_FAST_MODEL") or "doubao-seedance-2-0-fast-260128").strip()
        return {
            "configured": bool(ark_key),
            "label": "SeedDance 2.0（火山方舟 Ark · AI 分镜视频）",
            "provider": "volcengine-ark",
            "mode": _ai_video_mode(),
            "text_model": text_model,
            "image_model": text_model,
            "use_fast": use_fast,
            "setup": "在 overseas-loc-mvp/.env 填写 ARK_API_KEY，或运行「配置SeedDance.cmd」",
            "docs": "https://www.volcengine.com/docs/82379/1520757",
            "env_path": str(OVERSEAS_ENV),
        }
    text_model = (env.get("SEEDANCE_TEXT_MODEL") or "bytedance/seedance-2.0/text-to-video").strip()
    image_model = (env.get("SEEDANCE_IMAGE_MODEL") or "bytedance/seedance-2.0/image-to-video").strip()
    if use_fast:
        text_model = text_model.replace("/text-to-video", "/text-to-video/fast")
        image_model = image_model.replace("/image-to-video", "/image-to-video/fast")
    return {
        "configured": bool(fal_key),
        "label": "SeedDance 2.0（fal.ai · AI 分镜视频）",
        "provider": "fal.ai",
        "mode": _ai_video_mode(),
        "text_model": text_model,
        "image_model": image_model,
        "use_fast": use_fast,
        "setup": "在 overseas-loc-mvp/.env 填写 FAL_KEY，或运行「配置SeedDance.cmd」",
        "docs": "https://fal.ai/models/bytedance/seedance-2.0/text-to-video/api",
        "env_path": str(OVERSEAS_ENV),
    }


def test_connection() -> dict[str, Any]:
    code = """
import asyncio, json
from app.providers import test_seedance_connection
print(json.dumps(asyncio.run(test_seedance_connection()), ensure_ascii=False))
"""
    return _run_olm(code)


def project_status(slug: str) -> dict[str, Any]:
    project = OVERSEAS_RUNS_DIR / slug
    cfg = seedance_config()
    if not project.exists():
        return {
            "available": False,
            "configured": cfg["configured"],
            "pipeline": SEEDANCE_PIPELINE,
            "shots": [],
        }
    code = """
import json, sys
from app.storage import project_dir
from app.workflow import seedance_status
slug = sys.argv[1]
print(json.dumps(seedance_status(project_dir(slug, create=False)), ensure_ascii=False))
"""
    return _run_olm(code, slug)


def refresh_project_seedance_source(slug: str) -> dict[str, Any] | None:
    """按 localization-brief 的 sku 强制刷新 inputs/seedance-source 白底主图垫图。"""
    project = OVERSEAS_RUNS_DIR / slug
    if not project.is_dir():
        return None
    product_id = ""
    brief_path = project / "localization-brief.yaml"
    if brief_path.exists():
        try:
            import yaml

            brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
            product_id = str(brief.get("sku") or "").strip()
        except Exception:
            product_id = ""
    if not product_id:
        return None
    return stage_project_production_assets(
        project,
        product_id,
        _brief_market_tags(project),
    )


def _brief_market_tags(project: Path) -> dict[str, Any]:
    brief_path = project / "localization-brief.yaml"
    if not brief_path.exists():
        return {}
    try:
        import yaml

        brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
        return {
            "audience_tags": brief.get("audience_tags") or [],
            "scenario_tags": brief.get("scenario_tags") or [],
        }
    except Exception:
        return {}


def run_all(slug: str, *, force: bool = False) -> dict[str, Any]:
    code = """
import asyncio, json, sys
from app.main import _seedance_generate_all, _maybe_assemble_final_video
from app.storage import project_dir
from app.workflow import seedance_status
from app.library import save_finished_record
slug = sys.argv[1]
force = sys.argv[2] == "1"
results = asyncio.run(_seedance_generate_all(slug, force=force))
assemble = _maybe_assemble_final_video(slug)
status = seedance_status(project_dir(slug))
if any(r.get("status") == "ok" for r in results):
    save_finished_record(project_dir(slug))
print(json.dumps({"results": results, "seedance": status, "assemble": assemble, "force": force}, ensure_ascii=False))
"""
    return _run_olm(code, slug, "1" if force else "0")


def assemble_project(slug: str) -> dict[str, Any]:
    ensure_ffmpeg_ready(raise_on_fail=True)
    code = """
import json, sys
from app.main import _maybe_assemble_final_video
from app.storage import project_dir
from app.workflow import seedance_status
slug = sys.argv[1]
assemble = _maybe_assemble_final_video(slug)
status = seedance_status(project_dir(slug))
print(json.dumps({"assemble": assemble, "seedance": status}, ensure_ascii=False))
"""
    return _run_olm(code, slug)


def hero_frame_gate_enabled() -> bool:
    env = dotenv_values(OVERSEAS_ENV)
    return (env.get("HERO_FRAME_GATE") or "0").strip().lower() in ("1", "true", "yes")


def hero_frames_status(slug: str) -> dict[str, Any]:
    project = OVERSEAS_RUNS_DIR / slug
    if not project.is_dir():
        return {"gate_enabled": hero_frame_gate_enabled(), "confirmed": True, "shots": [], "all_ready": False}
    code = """
import json, sys
from app.storage import project_dir
from app.hero_frames import hero_frames_status
slug = sys.argv[1]
print(json.dumps(hero_frames_status(project_dir(slug, create=False)), ensure_ascii=False))
"""
    return _run_olm(code, slug)


def generate_hero_frames(slug: str) -> dict[str, Any]:
    code = """
import json, sys
from app.storage import project_dir
from app.hero_frames import generate_hero_frames
slug = sys.argv[1]
print(json.dumps(generate_hero_frames(project_dir(slug, create=False)), ensure_ascii=False))
"""
    return _run_olm(code, slug)


def confirm_hero_frames(slug: str) -> dict[str, Any]:
    code = """
import json, sys
from app.storage import project_dir
from app.hero_frames import confirm_hero_frames
slug = sys.argv[1]
print(json.dumps(confirm_hero_frames(project_dir(slug, create=False)), ensure_ascii=False))
"""
    return _run_olm(code, slug)


def regenerate_hero_frame(slug: str, shot_number: int) -> dict[str, Any]:
    code = """
import json, sys
from app.storage import project_dir
from app.hero_frames import regenerate_hero_frame
slug, num = sys.argv[1], int(sys.argv[2])
print(json.dumps(regenerate_hero_frame(project_dir(slug, create=False), num), ensure_ascii=False))
"""
    return _run_olm(code, slug, str(int(shot_number)))


def validate_product_staging(slug: str, product_id: str) -> dict[str, Any]:
    code = """
import json, sys
from app.storage import project_dir
from app.product_staging import validate_product_staging
slug, pid = sys.argv[1], sys.argv[2]
print(json.dumps(validate_product_staging(project_dir(slug, create=False), pid), ensure_ascii=False))
"""
    return _run_olm(code, slug, product_id)
