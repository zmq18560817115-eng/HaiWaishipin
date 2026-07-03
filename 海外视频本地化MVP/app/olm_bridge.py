"""调用 overseas-loc-mvp 完成交付（避免 app 包名冲突，走子进程）。"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from paths import (
    GENERATED_SCRIPTS_DIR,
    MVP_ROOT,
    OVERSEAS_MVP_DIR,
    OVERSEAS_RUNS_DIR,
    PRODUCTION_ARCHIVE_DIR,
)

from .llm_script import pack_to_bridge_shots
from .character_assets import stage_project_production_assets

USER_DELIVERABLES = (
    "交付脚本包.md",
    "交付脚本包.json",
    "subtitles.srt",
    "剪辑单.html",
)


def _olm_module(module: str):
    """从 overseas-loc-mvp/app 加载模块，避免与工作台 app 包名冲突。"""
    import importlib.util
    import sys

    rel = module.replace(".", "/") + ".py"
    path = OVERSEAS_MVP_DIR / "app" / rel
    if not path.is_file():
        raise RuntimeError(f"缺少 overseas-loc-mvp 模块: {path}")
    mod_name = f"olm_{module.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _olm_python() -> Path:
    venv_py = OVERSEAS_MVP_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return venv_py
    return Path(sys.executable)


def ensure_delivery_project(link_id: int) -> str:
    """确保 overseas-loc 项目存在，并同步最新 script-pack。"""
    slug = f"ref-{link_id:03d}"
    proj = OVERSEAS_RUNS_DIR / slug
    gen_pack_path = GENERATED_SCRIPTS_DIR / str(link_id) / "script-pack.json"

    if not proj.exists():
        cmd = [sys.executable, str(MVP_ROOT / "scripts" / "pipeline.py"), "bridge", "--id", str(link_id), "--force"]
        proc = subprocess.run(
            cmd,
            cwd=str(MVP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                **os.environ,
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            },
        )
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "bridge 失败")[-800:]
            raise RuntimeError(tail)

    if gen_pack_path.exists():
        try:
            raw = json.loads(gen_pack_path.read_text(encoding="utf-8"))
            pack = raw.get("pack") or raw
            payload = raw.get("payload") or {}
            proj.mkdir(parents=True, exist_ok=True)
            pack_doc = raw if isinstance(raw.get("pack"), dict) and isinstance(raw.get("payload"), dict) else {
                "pack": pack,
                "payload": payload,
            }
            if raw.get("meta") and "meta" not in pack_doc:
                pack_doc["meta"] = raw["meta"]
            (proj / "script-pack.json").write_text(
                json.dumps(pack_doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            shots = payload.get("shots") or pack.get("storyboard") or []
            if shots:
                bridge_shots = pack_to_bridge_shots(pack) if pack.get("storyboard") else []
                if not bridge_shots:
                    for row in shots:
                        bridge_shots.append({
                            "number": int(row.get("number", len(bridge_shots) + 1)),
                            "role": row.get("role", ""),
                            "timing": row.get("timing", ""),
                            "visual": row.get("visual", ""),
                            "copy": row.get("copy") or row.get("voiceover_en") or row.get("subtitle_en", ""),
                            "footage_type": row.get("footage_type", "LIVE_ACTION"),
                            "notes": row.get("seedance_prompt") or row.get("notes") or row.get("visual_prompt", ""),
                        })
                (proj / "storyboard.json").write_text(
                    json.dumps({"shots": bridge_shots}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            _sync_brief_tags(proj, payload)
            _stage_product_image(proj, payload)
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"同步 script-pack 失败: {exc}") from exc

    if not proj.exists():
        raise RuntimeError(f"交付项目 {slug} 不存在，请先生成脚本")
    return slug


def _stage_product_image(project: Path, payload: dict[str, Any]) -> None:
    product_id = str(payload.get("product_id") or "").strip()
    if not product_id:
        brief_path = project / "localization-brief.yaml"
        if brief_path.exists():
            try:
                import yaml

                brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
                product_id = str(brief.get("sku") or "").strip()
            except Exception:
                product_id = ""
    if product_id:
        stage_project_production_assets(
            project,
            product_id,
            {
                "audience_tags": payload.get("audience_tags") or [],
                "scenario_tags": payload.get("scenario_tags") or [],
            },
        )


def _sync_brief_tags(project: Path, payload: dict[str, Any]) -> None:
    brief_path = project / "localization-brief.yaml"
    if not brief_path.exists():
        return
    try:
        import yaml

        brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
        brief["audience_tags"] = payload.get("audience_tags") or []
        brief["scenario_tags"] = payload.get("scenario_tags") or []
        vp = {
            k: payload[k]
            for k in ("resolution", "aspect_ratio", "duration_sec", "generate_count", "edit_mode")
            if payload.get(k) is not None
        }
        if vp:
            brief["video_production"] = vp
        brief_path.write_text(yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception:
        pass


def finish_project(slug: str) -> dict[str, Any]:
    code = """
import asyncio, json, sys
from app.main import quick_finish
slug = sys.argv[1]
result = asyncio.run(quick_finish(slug))
print(json.dumps({"ok": True, "slug": slug, "delivery_ready": result.get("delivery_ready"), "message": result.get("message", "")}, ensure_ascii=False))
"""
    proc = subprocess.run(
        [str(_olm_python()), "-c", code, slug],
        cwd=str(OVERSEAS_MVP_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        },
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "交付失败")[-800:]
        raise RuntimeError(tail)
    line = (proc.stdout or "").strip().splitlines()[-1]
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"交付子进程返回无效 JSON: {line[:200]}") from exc


def _valid_mp4(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 1000


def _latest_archived_final(slug: str) -> Path | None:
    base = PRODUCTION_ARCHIVE_DIR / slug
    if not base.is_dir():
        return None
    for folder in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        final = folder / "final-video.mp4"
        if _valid_mp4(final):
            return final
    return None


def _try_assemble_final(slug: str) -> None:
    """分镜已齐但 runs 无成片时，下载 zip 前再尝试拼接一次。"""
    from .seedance_bridge import assemble_project

    project = OVERSEAS_RUNS_DIR / slug
    final = project / "broll" / "final-video.mp4"
    if _valid_mp4(final):
        return
    broll = project / "broll"
    if not broll.is_dir() or not list(broll.glob("shot-*.mp4")):
        return
    try:
        assemble_project(slug)
    except (RuntimeError, OSError):
        pass


def resolve_final_video_path(slug: str, *, try_assemble: bool = True) -> Path | None:
    project = OVERSEAS_RUNS_DIR / slug
    final = project / "broll" / "final-video.mp4"
    if try_assemble:
        _try_assemble_final(slug)
    if _valid_mp4(final):
        return final
    return _latest_archived_final(slug)


def build_delivery_zip(slug: str) -> tuple[bytes, str]:
    project = OVERSEAS_RUNS_DIR / slug
    if not project.exists():
        raise FileNotFoundError("项目不存在")
    final_path = resolve_final_video_path(slug)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in USER_DELIVERABLES:
            path = project / name
            if path.exists():
                zf.write(path, name)
        broll = project / "broll"
        if broll.exists():
            for mp4 in sorted(broll.glob("shot-*.mp4")):
                zf.write(mp4, mp4.relative_to(project).as_posix())
        if final_path and _valid_mp4(final_path):
            zf.write(final_path, "final-video.mp4")
            runs_final = project / "broll" / "final-video.mp4"
            if _valid_mp4(runs_final):
                zf.write(runs_final, runs_final.relative_to(project).as_posix())
            else:
                zf.write(final_path, "broll/final-video.mp4")
    return buf.getvalue(), f"{slug}-delivery.zip"


def project_exists(slug: str) -> bool:
    return (OVERSEAS_RUNS_DIR / slug).exists()


def delivery_ready(slug: str) -> bool:
    project = OVERSEAS_RUNS_DIR / slug
    if not project.exists():
        return False
    return any((project / name).exists() for name in USER_DELIVERABLES)


def sync_project_video_settings(slug: str, settings: dict[str, Any]) -> dict[str, Any]:
    """将工作台底部选取的分辨率/画幅写入 runs 项目，供 SeedDance 出片严格读取。"""
    vp_mod = _olm_module("video_production")
    normalize_video_settings = vp_mod.normalize_video_settings

    project = OVERSEAS_RUNS_DIR / slug
    if not project.is_dir():
        raise FileNotFoundError(f"项目不存在: {slug}")
    normalized = normalize_video_settings(settings)
    payload_patch = normalized.as_dict()

    pack_path = project / "script-pack.json"
    if pack_path.is_file():
        try:
            raw = json.loads(pack_path.read_text(encoding="utf-8"))
            payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            payload.update(payload_patch)
            raw["payload"] = payload
            pack_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"更新 script-pack 出片参数失败: {exc}") from exc

    brief_path = project / "localization-brief.yaml"
    if brief_path.is_file():
        try:
            import yaml

            brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
            brief["video_production"] = payload_patch
            brief_path.write_text(yaml.safe_dump(brief, allow_unicode=True, sort_keys=False), encoding="utf-8")
        except Exception:
            pass

    return payload_patch
