#!/usr/bin/env python3
"""将工作区核心数据备份到 06_备份库（或 WORKFLOW_BACKUP_DIR）。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
if str(MVP_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(MVP_ROOT / "scripts"))
if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))

from paths import (  # noqa: E402
    FEEDBACK_LIBRARY_DIR,
    FINISHED_LIBRARY_DIR,
    MATERIAL_LIBRARY_DIR,
    OVERSEAS_RUNS_DIR,
    PRODUCTION_ARCHIVE_DIR,
    WORKFLOW_ROOT,
)

try:
    from app.deploy_config import backup_root  # noqa: E402
except ImportError:
    def backup_root() -> Path:
        return WORKFLOW_ROOT / "06_备份库"


BACKUP_TARGETS = (
    ("01_素材库", MATERIAL_LIBRARY_DIR),
    ("03_产出库", PRODUCTION_ARCHIVE_DIR),
    ("04_成稿库", FINISHED_LIBRARY_DIR),
    ("05_反馈库", FEEDBACK_LIBRARY_DIR),
    ("runs", OVERSEAS_RUNS_DIR),
)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_backup(*, dest: Path | None = None, dry_run: bool = False) -> dict:
    root = dest or backup_root()
    stamp = _stamp()
    out = root / stamp
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workflow_root": str(WORKFLOW_ROOT),
        "destination": str(out),
        "items": [],
    }
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)
    for label, src in BACKUP_TARGETS:
        row = {"label": label, "source": str(src), "ok": False, "message": ""}
        if not src.exists():
            row["message"] = "跳过（目录不存在）"
            manifest["items"].append(row)
            continue
        target = out / label
        if dry_run:
            row["ok"] = True
            row["message"] = f"将复制到 {target}"
        else:
            try:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(src, target)
                row["ok"] = True
                row["message"] = "已复制"
            except OSError as exc:
                row["message"] = str(exc)
        manifest["items"].append(row)
    if not dry_run:
        (out / "backup-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        latest = root / "latest.json"
        latest.write_text(
            json.dumps({"stamp": stamp, "path": str(out)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="备份工作区核心目录")
    parser.add_argument("--dest", type=Path, default=None, help="备份根目录，默认 06_备份库")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = run_backup(dest=args.dest, dry_run=args.dry_run)
    ok = sum(1 for row in manifest["items"] if row.get("ok"))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\n完成：{ok}/{len(manifest['items'])} 项", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
