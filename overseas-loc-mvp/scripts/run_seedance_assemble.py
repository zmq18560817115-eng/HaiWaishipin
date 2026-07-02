"""本地生成分镜视频并拼接成片；成功后可归档到 03_产出库/。

用法:
  python scripts/run_seedance_assemble.py ref-023
  python scripts/run_seedance_assemble.py 23 --force
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MVP_ROOT = ROOT.parent / "海外视频本地化MVP"
sys.path.insert(0, str(ROOT))

from app.main import _maybe_assemble_final_video, _seedance_generate_all
from app.storage import project_dir
from app.workflow import seedance_status


def _load_workbench_daily_quota():
    path = MVP_ROOT / "app" / "daily_quota.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("workbench_daily_quota", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_quota_mod = _load_workbench_daily_quota()
if _quota_mod:
    assert_video_quota = _quota_mod.assert_video_quota
    record_video_output = _quota_mod.record_video_output
    video_quota_status = _quota_mod.video_quota_status
else:
    def assert_video_quota() -> None:
        return None

    def record_video_output(slug: str, *, note: str = "") -> dict:
        return {}

    def video_quota_status() -> dict:
        return {}


def normalize_slug(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return "ref-001"
    if s.isdigit():
        return f"ref-{int(s):03d}"
    if not s.startswith("ref-"):
        return f"ref-{s}"
    return s


def copy_to_workspace_output(slug: str, project: Path, asm: dict) -> Path | None:
    """成片已由 production_archive 写入 03_产出库；此处返回最新归档路径。"""
    if not asm.get("ok"):
        return None
    from app.production_archive import list_versions

    versions = list_versions(slug)
    if not versions:
        return None
    latest = versions[0] / "final-video.mp4"
    return latest if latest.is_file() else None


async def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]
    slug = normalize_slug(args[0] if args else "ref-001")
    project = project_dir(slug, create=False)
    if not project.exists():
        print(f"[失败] 项目不存在: {project}")
        print("请先在 8788 工作台生成脚本，或运行: 演示长视频.cmd")
        return 1

    try:
        assert_video_quota()
    except ValueError as exc:
        print(f"[失败] {exc}")
        return 1

    print(f"项目: {slug}")
    print(f"目录: {project}")
    if force:
        print("强制模式：已清除旧分镜 mp4，按最新 Prompt 全部重生成…")
    else:
        print("正在调用 SeedDance 生成缺失分镜（已有 mp4 会跳过，加 --force 可覆盖）…")

    results = await _seedance_generate_all(slug, force=force)
    errors = [r for r in results if r.get("status") == "error"]
    if errors:
        for r in errors:
            print(f"  镜 {r.get('number')}: {r.get('message')}")

    asm = _maybe_assemble_final_video(slug)
    st = seedance_status(project)
    ready = sum(1 for s in st["shots"] if s.get("ready"))
    total = len(st["shots"])
    final = st.get("final_video") or {}

    out_copy = copy_to_workspace_output(slug, project, asm)
    video_quota = video_quota_status()
    if out_copy or asm.get("ok") or final.get("ready"):
        video_quota = record_video_output(slug, note="cli/run_seedance_assemble")
    payload = {
        "slug": slug,
        "ready": f"{ready}/{total}",
        "final": final,
        "assemble": asm,
        "workspace_output": str(out_copy) if out_copy else None,
        "daily_video_quota": video_quota,
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if out_copy:
        print(f"\n成片已归档: {out_copy}")
        print(f"浏览器预览（工作副本）: http://127.0.0.1:8788/api/delivery/{slug}/files/broll/final-video.mp4")
    elif ready >= total and total > 0:
        print(f"\n分镜已齐 ({ready}/{total})，但拼接未成功，请检查 ffmpeg / AI_VIDEO_CONCAT_MIN_SHOTS")
    elif ready < total:
        print(f"\n部分完成 ({ready}/{total})，可稍后重跑本命令补生成")

    return 0 if final.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
