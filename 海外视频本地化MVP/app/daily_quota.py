"""每日 LLM 脚本生成配额（质量优先 · 控量量产）。"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from paths import DATA_DIR

from .doubao_config import _env

QUOTA_LOG_PATH = DATA_DIR / "daily_script_quota.json"
VIDEO_QUOTA_LOG_PATH = DATA_DIR / "daily_video_quota.json"
LLM_PROVIDERS = frozenset({"doubao", "anthropic", "claude"})


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def daily_script_quota_limit() -> int:
    raw = (_env().get("DAILY_SCRIPT_QUOTA") or "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def daily_video_quota_limit() -> int:
    raw = (_env().get("DAILY_VIDEO_QUOTA") or "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _load_log() -> dict[str, Any]:
    if not QUOTA_LOG_PATH.exists():
        return {"date": _today(), "entries": []}
    try:
        data = json.loads(QUOTA_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"date": _today(), "entries": []}
    if data.get("date") != _today():
        return {"date": _today(), "entries": []}
    entries = data.get("entries")
    if not isinstance(entries, list):
        entries = []
    return {"date": _today(), "entries": entries}


def _save_log(log: dict[str, Any]) -> None:
    QUOTA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_video_log() -> dict[str, Any]:
    if not VIDEO_QUOTA_LOG_PATH.exists():
        return {"date": _today(), "entries": []}
    try:
        data = json.loads(VIDEO_QUOTA_LOG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"date": _today(), "entries": []}
    if data.get("date") != _today():
        return {"date": _today(), "entries": []}
    entries = data.get("entries")
    if not isinstance(entries, list):
        entries = []
    return {"date": _today(), "entries": entries}


def _save_video_log(log: dict[str, Any]) -> None:
    VIDEO_QUOTA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    VIDEO_QUOTA_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _provider_counts(provider: str) -> bool:
    token = (provider or "").strip().lower()
    if token in ("rule_template", "rule", ""):
        return False
    return token in LLM_PROVIDERS


def quota_status() -> dict[str, Any]:
    limit = daily_script_quota_limit()
    log = _load_log()
    entries = [e for e in log.get("entries", []) if isinstance(e, dict) and _provider_counts(str(e.get("provider", "")))]
    used = len(entries)
    remaining = max(0, limit - used) if limit > 0 else -1
    return {
        "date": log.get("date", _today()),
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "enabled": limit > 0,
        "items": [
            {
                "link_id": e.get("link_id"),
                "provider": e.get("provider"),
                "model": e.get("model"),
                "at": e.get("at"),
            }
            for e in entries[-20:]
        ],
    }


def assert_script_quota() -> None:
    status = quota_status()
    if not status["enabled"]:
        return
    if status["remaining"] <= 0:
        raise ValueError(
            f"今日 LLM 脚本配额已用完（{status['used']}/{status['limit']}）。"
            "明日再试，或在 overseas-loc-mvp/.env 调整 DAILY_SCRIPT_QUOTA。"
        )


def video_quota_status() -> dict[str, Any]:
    limit = daily_video_quota_limit()
    log = _load_video_log()
    entries = [e for e in log.get("entries", []) if isinstance(e, dict)]
    used = len(entries)
    remaining = max(0, limit - used) if limit > 0 else -1
    return {
        "date": log.get("date", _today()),
        "limit": limit,
        "used": used,
        "remaining": remaining,
        "enabled": limit > 0,
        "items": [
            {
                "slug": e.get("slug"),
                "at": e.get("at"),
                "note": e.get("note", ""),
            }
            for e in entries[-20:]
        ],
    }


def assert_video_quota() -> None:
    status = video_quota_status()
    if not status["enabled"]:
        return
    if status["remaining"] <= 0:
        raise ValueError(
            f"今日成片产出配额已用完（{status['used']}/{status['limit']}）。"
            "明日再试，或在 overseas-loc-mvp/.env 调整 DAILY_VIDEO_QUOTA。"
        )


def record_video_output(slug: str, *, note: str = "") -> dict[str, Any]:
    slug = (slug or "").strip()
    if not slug:
        return video_quota_status()
    log = _load_video_log()
    log["entries"].append(
        {
            "slug": slug,
            "at": datetime.now().strftime("%H:%M:%S"),
            "note": note,
        }
    )
    _save_video_log(log)
    return video_quota_status()


def record_script_generation(link_id: int, meta: dict[str, Any] | None) -> dict[str, Any]:
    meta = meta or {}
    provider = str(meta.get("provider") or "")
    if not _provider_counts(provider):
        return quota_status()
    log = _load_log()
    log["entries"].append(
        {
            "link_id": link_id,
            "provider": provider,
            "model": str(meta.get("model") or ""),
            "at": datetime.now().strftime("%H:%M:%S"),
        }
    )
    _save_log(log)
    return quota_status()


def production_profile() -> dict[str, Any]:
    env = _env()
    return {
        "profile": (env.get("PRODUCTION_PROFILE") or "quality_daily").strip(),
        "daily_script_quota": quota_status(),
        "daily_video_quota": video_quota_status(),
        "script_mode": (env.get("DOUBAO_SCRIPT_MODE") or "pro").strip(),
        "decompose_mode": (env.get("DOUBAO_VIDEO_ANALYSIS_MODE") or "turbo").strip(),
        "ai_video_mode": (env.get("AI_VIDEO_MODE") or "broll").strip(),
        "ai_video_max_shots": (env.get("AI_VIDEO_MAX_SHOTS") or "2").strip(),
        "hints": [
            "测试期默认日产 10 条成片（DAILY_VIDEO_QUOTA）+ 10 条 LLM 脚本（DAILY_SCRIPT_QUOTA）",
            "每条对标只精细拆解 1 次；脚本不满意先改字，最多重生 1 次",
            "试风格用 AI_VIDEO_MAX_SHOTS=2，定稿再改回 5",
            "VIDEO_ANALYSIS_AUTO=0、ON_VIEW=0 保持关闭",
        ],
    }
