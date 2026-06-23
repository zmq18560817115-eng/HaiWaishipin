from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .storage import write_json
from .workflow import utc_now


SYSTEM_PROMPT = """You are a US-market short-video localization writer for maternity breast pump content.

RULES:
1. Output ONLY valid Markdown matching schema "en-localization-pack-v1".
2. Each EN subtitle line: 6-10 words, spoken US English, TikTok/Amazon ad tone.
3. Use ONLY claims listed in allowed_claims_en. Never invent benefits.
4. NEVER use forbidden terms listed in forbidden_terms (case-insensitive).
5. Preserve shot structure exactly 5 shots from the Chinese storyboard.
6. Mark footage type per shot: [LIVE_ACTION] or [AI_BROLL] from storyboard.
7. Provide exactly 5 hook variants (10 words maximum each) and at least 3 cover titles.
8. No medical promises, no pain-free guarantees, no milk supply claims.
9. Company knowledge context is reference evidence only and cannot expand the claims whitelist.
10. Do not add commentary outside the Markdown document.
"""


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        return "\n".join(lines[1:-1]).strip() + "\n"
    return stripped + "\n"


async def _anthropic_messages(
    messages: list[dict[str, str]],
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    if not settings.anthropic_api_key:
        raise RuntimeError("未配置 ANTHROPIC_API_KEY")
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": settings.max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    start = time.perf_counter()
    last_error = None
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in range(3):
            response = await client.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            )
            if response.status_code != 429:
                break
            last_error = response.text
            if attempt < 2:
                await asyncio.sleep(float(response.headers.get("retry-after", "30")))
        else:
            raise RuntimeError(f"Anthropic 429: {last_error}")
    if response.status_code in (401, 403):
        raise RuntimeError("Anthropic Key 无效或无权限")
    response.raise_for_status()
    data = response.json()
    text_blocks = [
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    ]
    if not text_blocks:
        raise RuntimeError("Anthropic 返回中没有文本内容")
    usage = data.get("usage", {})
    meta = {
        "model": data.get("model", settings.anthropic_model),
        "provider": "anthropic",
        "requested_at": utc_now(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "status": "success",
        "response_id": data.get("id"),
    }
    return strip_markdown_fence("\n".join(text_blocks)), meta, data


async def call_anthropic(user_prompt: str) -> tuple[str, dict[str, Any]]:
    markdown, meta, _ = await _anthropic_messages([{"role": "user", "content": user_prompt}])
    return markdown, meta


async def call_anthropic_with_validation_retry(
    user_prompt: str,
    retry_message: str,
    first_markdown: str,
) -> tuple[str, dict[str, Any]]:
    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": first_markdown},
        {"role": "user", "content": retry_message},
    ]
    markdown, meta, _ = await _anthropic_messages(messages)
    meta["retry"] = True
    meta["retry_reason"] = retry_message
    return markdown, meta


async def call_seedance(
    project: Path,
    prompt: str,
    image_path: Path | None,
    shot_number: int,
) -> dict[str, Any]:
    if not settings.fal_key:
        raise RuntimeError("未配置 FAL_KEY，请在 overseas-loc-mvp/.env 填写 fal.ai 密钥")
    os.environ["FAL_KEY"] = settings.fal_key
    import fal_client

    model_id = (
        settings.seedance_image_model_resolved
        if image_path
        else settings.seedance_text_model_resolved
    )
    arguments: dict[str, Any] = {
        "prompt": prompt,
        "duration": "5",
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generate_audio": False,
    }
    uploaded_url = None
    if image_path:
        uploaded_url = await asyncio.to_thread(fal_client.upload_file, str(image_path))
        arguments["image_urls"] = [uploaded_url]

    start = time.perf_counter()
    result = await asyncio.to_thread(
        fal_client.subscribe,
        model_id,
        arguments=arguments,
        with_logs=True,
    )
    video = result.get("video") or {}
    video_url = video.get("url")
    if not video_url:
        videos = result.get("videos") or []
        video_url = videos[0].get("url") if videos else None
    if not video_url:
        raise RuntimeError("SeedDance 返回中没有视频 URL")

    broll_dir = project / "broll"
    broll_dir.mkdir(parents=True, exist_ok=True)
    output_path = broll_dir / f"shot-{shot_number}.mp4"
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.get(video_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    meta = {
        "provider": "fal.ai",
        "model": model_id,
        "shot_number": shot_number,
        "requested_at": utc_now(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "prompt": prompt,
        "uploaded_image_url": uploaded_url,
        "remote_video_url": video_url,
        "local_file": output_path.relative_to(project).as_posix(),
        "status": "success",
    }
    write_json(broll_dir / f"shot-{shot_number}-seedance-meta.json", meta)
    return meta


async def test_seedance_connection() -> dict[str, Any]:
    """调用 fal.ai 生成 4 秒测试片，验证 FAL_KEY 与模型可用。"""
    if not settings.fal_key:
        return {
            "ok": False,
            "configured": False,
            "message": "未配置 FAL_KEY",
            "setup": "在 overseas-loc-mvp/.env 填写 FAL_KEY=（从 https://fal.ai/dashboard/keys 获取）",
        }
    os.environ["FAL_KEY"] = settings.fal_key
    import fal_client

    model_id = settings.seedance_text_model_resolved
    prompt = (
        "Warm nursery night light, bedside table with pumping accessories, "
        "slow cinematic push-in, no people, commercial b-roll test, vertical 9:16"
    )
    start = time.perf_counter()
    try:
        result = await asyncio.to_thread(
            fal_client.subscribe,
            model_id,
            arguments={
                "prompt": prompt,
                "duration": "4",
                "resolution": "480p",
                "aspect_ratio": "9:16",
                "generate_audio": False,
            },
            with_logs=True,
        )
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "model": model_id,
            "message": str(exc),
        }

    video = result.get("video") or {}
    video_url = video.get("url")
    if not video_url:
        videos = result.get("videos") or []
        video_url = videos[0].get("url") if videos else None
    if not video_url:
        return {
            "ok": False,
            "configured": True,
            "model": model_id,
            "message": "SeedDance 返回中没有视频 URL",
            "raw_keys": list(result.keys()),
        }

    probe_dir = settings.runs_dir / "_seedance_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    output_path = probe_dir / "connection-test.mp4"
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.get(video_url)
        response.raise_for_status()
        output_path.write_bytes(response.content)

    return {
        "ok": True,
        "configured": True,
        "model": model_id,
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "local_file": str(output_path),
        "remote_video_url": video_url,
        "message": "SeedDance 2.0 连接成功",
    }

