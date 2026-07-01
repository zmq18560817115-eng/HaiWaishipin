"""豆包视频拆解配置（复用火山方舟 ARK_API_KEY）。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from paths import MVP_ROOT, OVERSEAS_ENV

DEFAULT_TURBO = "doubao-seed-2-1-turbo-260628"
DEFAULT_PRO = "doubao-seed-2-1-pro-260628"
DEFAULT_SCRIPT_PROVIDER = "auto"


def _env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (OVERSEAS_ENV, MVP_ROOT / ".env"):
        if path.exists():
            for k, v in dotenv_values(path).items():
                if v is not None:
                    merged[k] = str(v).strip()
    for k, v in os.environ.items():
        if v:
            merged.setdefault(k, v)
    return merged


def doubao_config() -> dict:
    env = _env()
    key = (env.get("ARK_API_KEY") or "").strip()
    mode = (env.get("DOUBAO_VIDEO_ANALYSIS_MODE") or "auto").strip().lower()
    turbo = (env.get("DOUBAO_VIDEO_ANALYSIS_MODEL") or DEFAULT_TURBO).strip()
    pro = (env.get("DOUBAO_VIDEO_ANALYSIS_MODEL_PRO") or DEFAULT_PRO).strip()
    base = (env.get("ARK_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    asr_on = (env.get("DOUBAO_ASR_ENABLED") or "1").strip().lower() not in ("0", "false", "no")
    asr_ready = bool(
        (env.get("VOLCENGINE_ASR_APP_ID") or "").strip()
        and (env.get("VOLCENGINE_ASR_ACCESS_TOKEN") or "").strip()
    )
    provider_default = (env.get("DECOMPOSE_PROVIDER") or "auto").strip().lower()
    llm_enabled = _env_flag(env.get("DOUBAO_VIDEO_ANALYSIS_ENABLED"), default=True)
    auto_enabled = _env_flag(env.get("VIDEO_ANALYSIS_AUTO"), default=True)
    return {
        "configured": bool(key),
        "provider_default": provider_default,
        "mode": mode,
        "turbo_model": turbo,
        "pro_model": pro,
        "base_url": base,
        "asr_enabled": asr_on,
        "asr_configured": asr_ready,
        "llm_enabled": llm_enabled,
        "auto_enabled": auto_enabled,
        "paused": not llm_enabled and not auto_enabled,
        "pause_message": (
            "视频结构拆解已暂停：已分析素材不会重复调豆包，新抓取素材也不会自动分析。"
            "恢复请在 overseas-loc-mvp/.env 将 DOUBAO_VIDEO_ANALYSIS_ENABLED、VIDEO_ANALYSIS_AUTO 设为 1。"
        ),
        "env_path": str(OVERSEAS_ENV),
        "setup": "在 overseas-loc-mvp/.env 填写 ARK_API_KEY，并开通豆包视频理解模型",
        "docs": "https://www.volcengine.com/docs/82379/1895586",
    }


def _env_flag(raw: str | None, *, default: bool) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def video_analysis_policy() -> dict:
    """视频拆解策略（读 overseas-loc-mvp/.env）。"""
    cfg = doubao_config()
    on_view = _env_flag(_env().get("VIDEO_ANALYSIS_ON_VIEW"), default=False)
    return {
        "llm_enabled": bool(cfg.get("llm_enabled")),
        "auto_enabled": bool(cfg.get("auto_enabled")),
        "on_view": on_view,
        "paused": bool(cfg.get("paused")),
        "message": str(cfg.get("pause_message") or ""),
        "token_saving": token_saving_hints(),
    }


def decompose_batch_limit() -> int:
    raw = (_env().get("DECOMPOSE_BATCH_LIMIT") or "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def token_saving_hints() -> dict[str, str]:
    return {
        "decompose": "仅对入选结构参考手动点「精细拆解」；批量用规则拆解；设 VIDEO_ANALYSIS_ON_VIEW=0",
        "script": "脚本用 DOUBAO_SCRIPT_MODE=turbo 试跑，定稿再用 pro",
        "video": "试跑设 AI_VIDEO_MAX_SHOTS=2；关闭 AI_VIDEO_ON_FINISH 避免交付时自动出片",
    }


def resolve_model(mode: str | None = None) -> str:
    cfg = doubao_config()
    m = (mode or cfg["mode"] or "auto").strip().lower()
    if m == "pro":
        return cfg["pro_model"]
    if m == "turbo":
        return cfg["turbo_model"]
    return cfg["turbo_model"]


def resolve_script_model(mode: str | None = None) -> str:
    """脚本生成用豆包模型（默认 pro，质量更好）。"""
    env = _env()
    explicit = (env.get("DOUBAO_SCRIPT_MODEL") or "").strip()
    if explicit:
        return explicit
    cfg = doubao_config()
    m = (mode or env.get("DOUBAO_SCRIPT_MODE") or "pro").strip().lower()
    if m == "turbo":
        return cfg["turbo_model"]
    if m == "pro":
        return cfg["pro_model"]
    return cfg["pro_model"]


def script_llm_config() -> dict:
    """脚本生成 LLM 路由（豆包 / Claude / 规则）。"""
    env = _env()
    provider = (env.get("SCRIPT_LLM_PROVIDER") or DEFAULT_SCRIPT_PROVIDER).strip().lower()
    if provider not in ("auto", "doubao", "anthropic", "rule"):
        provider = DEFAULT_SCRIPT_PROVIDER
    ark_ready = bool((env.get("ARK_API_KEY") or "").strip())
    doubao_enabled = ark_ready and _env_flag(env.get("DOUBAO_SCRIPT_ENABLED"), default=True)
    anthropic_key = (env.get("ANTHROPIC_API_KEY") or "").strip()
    anthropic_ready = bool(anthropic_key)
    script_model = resolve_script_model()

    if provider == "auto":
        if doubao_enabled:
            effective = "doubao"
            label = f"豆包脚本（{script_model}，与拆解共用 ARK_API_KEY）"
        elif anthropic_ready:
            effective = "anthropic"
            label = f"Claude（{env.get('OVERSEAS_LOC_MODEL') or 'claude-sonnet-4-6'}）"
        else:
            effective = "rule"
            label = "规则模板（未配置 ARK_API_KEY / ANTHROPIC_API_KEY）"
    elif provider == "doubao":
        effective = "doubao" if doubao_enabled else "rule"
        label = (
            f"豆包脚本（{script_model}）"
            if doubao_enabled
            else "规则模板（豆包未配置或已关闭 DOUBAO_SCRIPT_ENABLED）"
        )
    elif provider == "anthropic":
        effective = "anthropic" if anthropic_ready else "rule"
        label = (
            f"Claude（{env.get('OVERSEAS_LOC_MODEL') or 'claude-sonnet-4-6'}）"
            if anthropic_ready
            else "规则模板（未配置 ANTHROPIC_API_KEY）"
        )
    else:
        effective = "rule"
        label = "规则模板（SCRIPT_LLM_PROVIDER=rule）"

    return {
        "provider": provider,
        "effective_provider": effective,
        "label": label,
        "doubao_configured": ark_ready,
        "doubao_enabled": doubao_enabled,
        "doubao_model": script_model,
        "anthropic_available": anthropic_ready,
        "anthropic_model": (env.get("OVERSEAS_LOC_MODEL") or "claude-sonnet-4-6").strip(),
        "fallback": "rule_template（LLM 失败或未配置时自动使用）",
        "env_path": str(OVERSEAS_ENV),
        "setup": "在 overseas-loc-mvp/.env 填写 ARK_API_KEY；可选 SCRIPT_LLM_PROVIDER=auto|doubao|anthropic|rule",
    }


def ark_api_key() -> str:
    return doubao_config()["configured"] and _env().get("ARK_API_KEY", "") or ""
