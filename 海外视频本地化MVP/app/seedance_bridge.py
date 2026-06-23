"""通过 overseas-loc-mvp 子进程调用 SeedDance 2.0（fal.ai）。"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from dotenv import dotenv_values

from paths import OVERSEAS_ENV, OVERSEAS_MVP_DIR, OVERSEAS_RUNS_DIR

from .olm_bridge import _olm_python

SEEDANCE_PIPELINE = (
    "脚本生成 → 分镜生成 → 视频 Prompt → SeedDance 2.0 → 输出视频 → 保存成稿"
)


def _run_olm(code: str, *args: str) -> dict[str, Any]:
    proc = subprocess.run(
        [str(_olm_python()), "-c", code, *args],
        cwd=str(OVERSEAS_MVP_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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
    fal_key = (env.get("FAL_KEY") or "").strip()
    use_fast = (env.get("SEEDANCE_USE_FAST") or "0").strip().lower() in ("1", "true", "yes")
    text_model = (env.get("SEEDANCE_TEXT_MODEL") or "bytedance/seedance-2.0/text-to-video").strip()
    image_model = (env.get("SEEDANCE_IMAGE_MODEL") or "bytedance/seedance-2.0/image-to-video").strip()
    if use_fast:
        text_model = text_model.replace("/text-to-video", "/text-to-video/fast")
        image_model = image_model.replace("/image-to-video", "/image-to-video/fast")
    return {
        "configured": bool(fal_key),
        "label": "SeedDance 2.0（fal.ai · 视频 B-roll）",
        "provider": "fal.ai",
        "text_model": text_model,
        "image_model": image_model,
        "use_fast": use_fast,
        "setup": "双击工作区根目录「配置SeedDance.cmd」，在 overseas-loc-mvp/.env 填写 FAL_KEY",
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


def run_all(slug: str) -> dict[str, Any]:
    code = """
import asyncio, json, sys
from app.main import _seedance_generate_all
from app.storage import project_dir
from app.workflow import seedance_status, save_finished_record
slug = sys.argv[1]
results = asyncio.run(_seedance_generate_all(slug))
status = seedance_status(project_dir(slug))
if any(r.get("status") == "ok" for r in results):
    save_finished_record(project_dir(slug))
print(json.dumps({"results": results, "seedance": status}, ensure_ascii=False))
"""
    return _run_olm(code, slug)
