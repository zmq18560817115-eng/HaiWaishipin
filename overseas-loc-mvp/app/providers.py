from __future__ import annotations

import asyncio
import base64
import mimetypes
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
    *,
    prod_settings=None,
) -> dict[str, Any]:
    from .video_production import VideoProductionSettings, read_project_video_settings

    prod: VideoProductionSettings = prod_settings or read_project_video_settings(project)
    provider = settings.seedance_provider_resolved
    if provider == "ark":
        return await _call_seedance_ark(project, prompt, image_path, shot_number, prod_settings=prod)
    if provider == "fal":
        return await _call_seedance_fal(project, prompt, image_path, shot_number, prod_settings=prod)
    raise RuntimeError(
        "未配置 SeedDance 密钥：在 overseas-loc-mvp/.env 填写 ARK_API_KEY（火山方舟）或 FAL_KEY（fal.ai）"
    )


def _ark_error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        err = body.get("error") or {}
        return str(err.get("message") or err.get("code") or body.get("message") or response.text or "")
    except Exception:
        return (response.text or "")[:300]


def _ark_person_image_rejected(response: httpx.Response) -> bool:
    detail = _ark_error_detail(response).lower()
    code = ""
    try:
        code = str((response.json().get("error") or {}).get("code") or "")
    except Exception:
        pass
    return (
        "privacyinformation" in code.lower()
        or "real person" in detail
        or "sensitivecontent" in code.lower()
    )


def _project_image_fallbacks(project: Path, primary: Path | None) -> list[Path | None]:
    """When person refs are rejected, try product/usage stills, then text-only."""
    ordered: list[Path | None] = []
    seen: set[str] = set()

    def add(path: Path | None) -> None:
        key = str(path.resolve()) if path else ""
        if key in seen:
            return
        seen.add(key)
        ordered.append(path)

    add(primary)
    inputs = project / "inputs"
    if inputs.is_dir():
        for pattern in ("seedance-source.*",):
            for path in sorted(inputs.glob(pattern)):
                if path.is_file():
                    add(path)
    add(None)
    return ordered


def _extract_video_url(payload: dict[str, Any]) -> str | None:
    content = payload.get("content") or {}
    if isinstance(content, dict):
        for key in ("video_url", "url"):
            if content.get(key):
                return str(content[key])
    video = payload.get("video") or {}
    if isinstance(video, dict) and video.get("url"):
        return str(video["url"])
    videos = payload.get("videos") or []
    if videos and isinstance(videos[0], dict) and videos[0].get("url"):
        return str(videos[0]["url"])
    output = payload.get("output") or {}
    if isinstance(output, dict):
        for key in ("video_url", "url"):
            if output.get(key):
                return str(output[key])
    return None


async def _ark_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.ark_api_key}",
        "Content-Type": "application/json",
    }


async def _ark_create_task(
    client: httpx.AsyncClient,
    *,
    prompt: str,
    image_path: Path | None,
    duration: int,
    resolution: str,
    aspect_ratio: str,
) -> str:
    model_id = (
        settings.ark_image_model_resolved if image_path else settings.ark_text_model_resolved
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if image_path and image_path.exists():
        mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        data_uri = (
            f"data:{mime};base64,"
            f"{base64.b64encode(image_path.read_bytes()).decode('ascii')}"
        )
        content.append({
            "type": "image_url",
            "image_url": {"url": data_uri},
            "role": "reference_image",
        })
    payload = {
        "model": model_id,
        "content": content,
        "resolution": resolution,
        "ratio": aspect_ratio,
        "duration": duration,
        "watermark": False,
        "generate_audio": False,
    }
    response = await client.post(
        f"{settings.ark_base_url}/contents/generations/tasks",
        headers=await _ark_headers(),
        json=payload,
    )
    if response.status_code in (401, 403):
        detail = _ark_error_detail(response)
        hint = detail or f"HTTP {response.status_code}"
        raise RuntimeError(
            f"ARK_API_KEY 无效或无权限（{hint}）。请在火山方舟控制台检查密钥是否过期、"
            "是否开通 SeedDance 2.0，并更新 overseas-loc-mvp/.env 后重启工作台"
        )
    if response.status_code == 400:
        raise httpx.HTTPStatusError(
            _ark_error_detail(response) or "Ark 400 Bad Request",
            request=response.request,
            response=response,
        )
    response.raise_for_status()
    data = response.json()
    task_id = data.get("id") or data.get("task_id")
    if not task_id:
        raise RuntimeError(f"Ark 未返回任务 ID: {data}")
    return str(task_id)


async def _ark_wait_video_url(
    client: httpx.AsyncClient,
    task_id: str,
    *,
    timeout_s: float = 300,
) -> str:
    wait = 8.0
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        response = await client.get(
            f"{settings.ark_base_url}/contents/generations/tasks/{task_id}",
            headers=await _ark_headers(),
        )
        response.raise_for_status()
        data = response.json()
        status = str(data.get("status") or "").lower()
        if status in ("succeeded", "success", "completed"):
            video_url = _extract_video_url(data)
            if video_url:
                return video_url
            raise RuntimeError(f"Ark 任务成功但无视频 URL: {list(data.keys())}")
        if status in ("failed", "expired", "cancelled", "error"):
            err = data.get("error") or data.get("message") or status
            raise RuntimeError(f"Ark 任务失败: {err}")
        await asyncio.sleep(wait)
        wait = min(wait * 1.5, 45.0)
    raise RuntimeError(f"Ark 任务超时（{int(timeout_s)}s）: {task_id}")


async def _download_video(client: httpx.AsyncClient, video_url: str, output_path: Path) -> None:
    response = await client.get(video_url)
    response.raise_for_status()
    output_path.write_bytes(response.content)


async def _call_seedance_ark(
    project: Path,
    prompt: str,
    image_path: Path | None,
    shot_number: int,
    *,
    prod_settings=None,
) -> dict[str, Any]:
    from .video_production import read_project_video_settings

    prod = prod_settings or read_project_video_settings(project)
    if not settings.ark_api_key:
        raise RuntimeError("未配置 ARK_API_KEY")
    start = time.perf_counter()
    last_error: Exception | None = None
    used_image: Path | None = image_path
    used_model = settings.ark_image_model_resolved if image_path else settings.ark_text_model_resolved

    async with httpx.AsyncClient(timeout=300) as client:
        for candidate in _project_image_fallbacks(project, image_path):
            model_id = settings.ark_image_model_resolved if candidate else settings.ark_text_model_resolved
            try:
                task_id = await _ark_create_task(
                    client,
                    prompt=prompt,
                    image_path=candidate,
                    duration=prod.duration_sec,
                    resolution=prod.resolution,
                    aspect_ratio=prod.aspect_ratio,
                )
                used_image = candidate
                used_model = model_id
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if candidate is not None and _ark_person_image_rejected(exc.response):
                    continue
                raise RuntimeError(_ark_error_detail(exc.response) or str(exc)) from exc
        else:
            raise RuntimeError(str(last_error or "Ark 创建任务失败"))

        video_url = await _ark_wait_video_url(
            client, task_id, timeout_s=float(settings.ark_seedance_wait_timeout)
        )
        broll_dir = project / "broll"
        broll_dir.mkdir(parents=True, exist_ok=True)
        output_path = broll_dir / f"shot-{shot_number}.mp4"
        await _download_video(client, video_url, output_path)
    meta = {
        "provider": "volcengine-ark",
        "model": used_model,
        "task_id": task_id,
        "shot_number": shot_number,
        "requested_at": utc_now(),
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "prompt": prompt,
        "image_ref": used_image.relative_to(project).as_posix() if used_image else None,
        "image_fallback": bool(image_path and used_image != image_path),
        "remote_video_url": video_url,
        "local_file": output_path.relative_to(project).as_posix(),
        "resolution": prod.resolution,
        "aspect_ratio": prod.aspect_ratio,
        "duration_sec": prod.duration_sec,
        "status": "success",
    }
    write_json(broll_dir / f"shot-{shot_number}-seedance-meta.json", meta)
    return meta


async def _call_seedance_fal(
    project: Path,
    prompt: str,
    image_path: Path | None,
    shot_number: int,
    *,
    prod_settings=None,
) -> dict[str, Any]:
    from .video_production import read_project_video_settings

    prod = prod_settings or read_project_video_settings(project)
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
        "duration": str(prod.duration_sec),
        "resolution": prod.resolution,
        "aspect_ratio": prod.aspect_ratio,
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
        "resolution": prod.resolution,
        "aspect_ratio": prod.aspect_ratio,
        "duration_sec": prod.duration_sec,
        "status": "success",
    }
    write_json(broll_dir / f"shot-{shot_number}-seedance-meta.json", meta)
    return meta


async def test_seedance_connection() -> dict[str, Any]:
    """生成短测试片，验证 SeedDance 密钥与模型可用（Ark 或 fal.ai）。"""
    provider = settings.seedance_provider_resolved
    if not provider:
        return {
            "ok": False,
            "configured": False,
            "provider": "",
            "message": "未配置 SeedDance 密钥",
            "setup": (
                "在 overseas-loc-mvp/.env 填写 ARK_API_KEY（火山方舟，推荐）"
                " 或 FAL_KEY（fal.ai）"
            ),
        }
    if provider == "ark":
        return await _test_seedance_ark()
    return await _test_seedance_fal()


async def _test_seedance_ark() -> dict[str, Any]:
    model_id = settings.ark_text_model_resolved
    prompt = (
        "Warm nursery night light, bedside table with baby bottle warmer, "
        "slow cinematic push-in, no people, commercial b-roll test, vertical 9:16"
    )
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            task_id = await _ark_create_task(
                client, prompt=prompt, image_path=None, duration=4, resolution="480p", aspect_ratio="9:16"
            )
            video_url = await _ark_wait_video_url(
                client, task_id, timeout_s=float(settings.ark_seedance_wait_timeout)
            )
            probe_dir = settings.runs_dir / "_seedance_probe"
            probe_dir.mkdir(parents=True, exist_ok=True)
            output_path = probe_dir / "connection-test.mp4"
            await _download_video(client, video_url, output_path)
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "provider": "volcengine-ark",
            "model": model_id,
            "message": str(exc),
        }
    return {
        "ok": True,
        "configured": True,
        "provider": "volcengine-ark",
        "model": model_id,
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "local_file": str(output_path),
        "remote_video_url": video_url,
        "message": "SeedDance 2.0（火山方舟 Ark）连接成功",
    }


async def _test_seedance_fal() -> dict[str, Any]:
    """调用 fal.ai 生成 4 秒测试片，验证 FAL_KEY 与模型可用。"""
    if not settings.fal_key:
        return {
            "ok": False,
            "configured": False,
            "provider": "fal.ai",
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
        "provider": "fal.ai",
        "model": model_id,
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "local_file": str(output_path),
        "remote_video_url": video_url,
        "message": "SeedDance 2.0（fal.ai）连接成功",
    }

