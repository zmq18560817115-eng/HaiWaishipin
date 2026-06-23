"""调用 overseas-loc-mvp 完成交付（避免 app 包名冲突，走子进程）。"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from paths import GENERATED_SCRIPTS_DIR, MVP_ROOT, OVERSEAS_MVP_DIR, OVERSEAS_RUNS_DIR

from .llm_script import pack_to_bridge_shots

USER_DELIVERABLES = (
    "交付脚本包.md",
    "交付脚本包.json",
    "subtitles.srt",
    "剪辑单.html",
)


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
            (proj / "script-pack.json").write_text(
                json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
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
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"同步 script-pack 失败: {exc}") from exc

    if not proj.exists():
        raise RuntimeError(f"交付项目 {slug} 不存在，请先生成脚本")
    return slug


def _sync_brief_tags(project: Path, payload: dict[str, Any]) -> None:
    brief_path = project / "localization-brief.yaml"
    if not brief_path.exists():
        return
    try:
        import yaml

        brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
        brief["audience_tags"] = payload.get("audience_tags") or []
        brief["scenario_tags"] = payload.get("scenario_tags") or []
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
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "交付失败")[-800:]
        raise RuntimeError(tail)
    line = (proc.stdout or "").strip().splitlines()[-1]
    return json.loads(line)


def build_delivery_zip(slug: str) -> tuple[bytes, str]:
    project = OVERSEAS_RUNS_DIR / slug
    if not project.exists():
        raise FileNotFoundError("项目不存在")
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
    return buf.getvalue(), f"{slug}-delivery.zip"


def project_exists(slug: str) -> bool:
    return (OVERSEAS_RUNS_DIR / slug).exists()


def delivery_ready(slug: str) -> bool:
    project = OVERSEAS_RUNS_DIR / slug
    if not project.exists():
        return False
    return any((project / name).exists() for name in USER_DELIVERABLES)
