"""豆包（火山方舟）文本脚本生成：与视频拆解共用 ARK_API_KEY。"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from .doubao_config import _env, doubao_config, resolve_script_model, script_llm_config


def _extract_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or "")
    if "output" in data:
        for item in data.get("output") or []:
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    return str(c["text"])
    return ""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def call_doubao_script(*, system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = script_llm_config()
    if not cfg.get("doubao_enabled"):
        raise RuntimeError("豆包脚本未启用：请在 overseas-loc-mvp/.env 配置 ARK_API_KEY")

    env = _env()
    api_key = (env.get("ARK_API_KEY") or "").strip()
    base = (env.get("ARK_BASE_URL") or doubao_config()["base_url"]).rstrip("/")
    model = resolve_script_model()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.65,
        "max_tokens": 4096,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(f"{base}/chat/completions", headers=headers, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"豆包 Chat API {resp.status_code}: {resp.text[:400]}")
    text = _extract_text(resp.json())
    if not text.strip():
        raise RuntimeError("豆包返回空内容")
    pack = _extract_json(text)
    meta = {
        "provider": "doubao",
        "model": model,
        "status": "success",
        "generated_at": _utc_now(),
    }
    return pack, meta


async def test_script_connection() -> dict[str, Any]:
    cfg = script_llm_config()
    if not cfg.get("doubao_configured"):
        return {"ok": False, "message": "未配置 ARK_API_KEY"}
    if not cfg.get("doubao_enabled"):
        return {"ok": False, "message": "DOUBAO_SCRIPT_ENABLED=0，豆包脚本已关闭"}
    try:
        pack, meta = call_doubao_script(
            system_prompt='只回复 JSON：{"ok":true}',
            user_prompt='返回 {"ok": true}',
        )
        if pack.get("ok") is True:
            return {
                "ok": True,
                "message": f"豆包脚本已连通 · 模型 {meta['model']}",
                "model": meta["model"],
            }
        return {"ok": False, "message": "豆包返回格式异常"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:300]}
