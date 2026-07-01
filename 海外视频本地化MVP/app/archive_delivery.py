"""从 03_产出库 打包历史成片，供内网用户下载（服务器侧永久留存）。"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

from paths import PRODUCTION_ARCHIVE_DIR


def list_archive_versions(slug: str) -> list[dict[str, Any]]:
    base = PRODUCTION_ARCHIVE_DIR / slug
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for folder in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        manifest_path = folder / "manifest.json"
        manifest: dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                manifest = {}
        final = folder / "final-video.mp4"
        rows.append(
            {
                "version": folder.name,
                "path": str(folder),
                "has_final_video": final.is_file(),
                "bytes": final.stat().st_size if final.is_file() else 0,
                "archived_at": manifest.get("archived_at", ""),
                "shots": manifest.get("shots") or [],
            }
        )
    return rows


def resolve_archive_folder(slug: str, version: str | None = None) -> Path:
    base = PRODUCTION_ARCHIVE_DIR / slug
    if not base.is_dir():
        raise FileNotFoundError(f"归档不存在：{slug}")
    if version in (None, "", "latest"):
        versions = sorted((p for p in base.iterdir() if p.is_dir()), reverse=True)
        if not versions:
            raise FileNotFoundError(f"尚无归档版本：{slug}")
        return versions[0]
    folder = base / version
    if not folder.is_dir():
        raise FileNotFoundError(f"归档版本不存在：{slug}/{version}")
    return folder


def build_archive_zip(slug: str, version: str | None = None) -> tuple[bytes, str]:
    folder = resolve_archive_folder(slug, version)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(folder).as_posix()
            zf.write(path, rel)
    name = f"{slug}-archive-{folder.name}.zip"
    return buf.getvalue(), name
