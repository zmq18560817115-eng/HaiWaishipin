"""工作台选取的分辨率 / 宽高比 / 时长 — 读取并规范化为 SeedDance API 参数。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VALID_ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1", "3:4", "4:3"})


@dataclass(frozen=True)
class VideoProductionSettings:
    resolution_ui: str
    resolution: str
    aspect_ratio: str
    duration_sec: int
    generate_count: int = 1
    edit_mode: str = "multi_shot"

    def as_dict(self) -> dict[str, Any]:
        return {
            "resolution_ui": self.resolution_ui,
            "resolution": self.resolution,
            "aspect_ratio": self.aspect_ratio,
            "duration_sec": self.duration_sec,
            "generate_count": self.generate_count,
            "edit_mode": self.edit_mode,
        }


def normalize_video_settings(raw: dict[str, Any] | None) -> VideoProductionSettings:
    data = raw or {}
    res_raw = str(data.get("resolution") or data.get("resolution_ui") or "720P").strip().upper()
    resolution = "1080p" if "1080" in res_raw else "720p"
    resolution_ui = "1080P" if resolution == "1080p" else "720P"
    ratio = str(data.get("aspect_ratio") or data.get("aspectRatio") or "9:16").strip()
    if ratio not in VALID_ASPECT_RATIOS:
        ratio = "9:16"
    try:
        duration = int(data.get("duration_sec") or data.get("durationSec") or 5)
    except (TypeError, ValueError):
        duration = 5
    duration = max(4, min(20, duration))
    try:
        generate_count = int(data.get("generate_count") or data.get("generateCount") or 1)
    except (TypeError, ValueError):
        generate_count = 1
    edit_mode = str(data.get("edit_mode") or data.get("editMode") or "multi_shot").strip() or "multi_shot"
    return VideoProductionSettings(
        resolution_ui=resolution_ui,
        resolution=resolution,
        aspect_ratio=ratio,
        duration_sec=duration,
        generate_count=max(1, min(4, generate_count)),
        edit_mode=edit_mode,
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_project_video_settings(project: Path) -> VideoProductionSettings:
    """从 runs 项目 script-pack / localization-brief 读取出片参数。"""
    merged: dict[str, Any] = {}
    pack = _read_json(project / "script-pack.json")
    payload = pack.get("payload") or {}
    if isinstance(payload, dict):
        merged.update(payload)
    brief_path = project / "localization-brief.yaml"
    if brief_path.is_file():
        try:
            import yaml

            brief = yaml.safe_load(brief_path.read_text(encoding="utf-8")) or {}
            vp = brief.get("video_production") or {}
            if isinstance(vp, dict):
                merged.update(vp)
        except Exception:
            pass
    return normalize_video_settings(merged)


def aspect_ratio_prompt(aspect_ratio: str) -> str:
    hints = {
        "9:16": "vertical 9:16",
        "16:9": "horizontal 16:9 widescreen",
        "1:1": "square 1:1",
        "3:4": "vertical 3:4",
        "4:3": "horizontal 4:3",
    }
    return hints.get(aspect_ratio, f"aspect ratio {aspect_ratio}")
