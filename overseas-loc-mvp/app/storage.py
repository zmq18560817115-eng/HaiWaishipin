from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .config import settings


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def project_dir(slug: str, create: bool = True) -> Path:
    slug = slug.strip().lower()
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("非法 slug")
    target = (settings.runs_dir / slug).resolve()
    if settings.runs_dir.resolve() not in target.parents:
        raise ValueError("非法项目路径")
    if create:
        target.mkdir(parents=True, exist_ok=True)
    return target


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(content)
        temp_name = handle.name
    os.replace(temp_name, path)


def write_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    atomic_write(
        path,
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
    )


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path.name)
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(read_text(path)) or {}


def safe_project_file(slug: str, relative: str) -> Path:
    base = project_dir(slug)
    target = (base / relative).resolve()
    if base.resolve() not in target.parents:
        raise ValueError("非法文件路径")
    return target


def file_inventory(slug: str) -> list[dict[str, Any]]:
    base = project_dir(slug, create=False)
    if not base.exists():
        return []
    items = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            items.append(
                {
                    "path": path.relative_to(base).as_posix(),
                    "bytes": path.stat().st_size,
                    "updated_at": path.stat().st_mtime,
                }
            )
    return items

