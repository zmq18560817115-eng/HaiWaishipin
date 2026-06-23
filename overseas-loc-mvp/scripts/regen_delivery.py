"""为已有项目重新生成剪辑单并清理旧交付物。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import USER_DELIVERABLES, _delivery_ready, _sync_delivery_pack  # noqa: E402
from app.library import save_finished_record  # noqa: E402
from app.storage import project_dir  # noqa: E402


def main() -> int:
    runs = ROOT / "runs"
    count = 0
    for path in sorted(runs.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if not (path / "subtitles.srt").exists():
            continue
        _sync_delivery_pack(path)
        if _delivery_ready(path):
            save_finished_record(path)
            count += 1
            print(f"OK  {path.name}: {', '.join(USER_DELIVERABLES)}")
        else:
            print(f"SKIP {path.name}: 缺少字幕或立项文件")
    print(f"完成，{count} 个项目可下载新格式 zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
