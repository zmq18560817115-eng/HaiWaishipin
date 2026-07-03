from __future__ import annotations

import io
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .ai_video import (
    ai_video_concat_enabled,
    ai_video_concat_min_shots,
    ai_video_max_shots,
    ai_video_mode,
    ai_video_on_finish,
    sanitize_seedance_prompt,
    shot_generates_video,
)
from .video_assemble import assemble_storyboard_video
from .knowledge import context_text, search_knowledge
from .models import (
    BriefRequest,
    FeedbackUpdateRequest,
    KnowledgeSearchRequest,
    LocalizeRequest,
    ManualLocalizeRequest,
    SeedanceRequest,
    SlugRequest,
    StoryboardRequest,
)
from .library import (
    FINISHED_DIR,
    FINISHED_INDEX,
    FEEDBACK_INDEX,
    load_feedback,
    list_feedback,
    list_finished,
    save_finished_record,
    update_feedback,
)
from .providers import SYSTEM_PROMPT, call_seedance, test_seedance_connection
from .storage import (
    atomic_write,
    file_inventory,
    project_dir,
    read_json,
    read_text,
    read_yaml,
    safe_project_file,
    write_json,
    write_yaml,
)
from .workflow import (
    FORBIDDEN_TERMS,
    demo_localization,
    generate_srt,
    make_gate_report,
    make_storyboard,
    USER_DELIVERABLES,
    write_editor_deliverables,
    delivery_zip_entries,
    render_user_prompt,
    scan_project,
    seedance_status,
    simple_flow_status,
    utc_now,
    validate_localization,
)


app = FastAPI(title="海外短视频本地化 MVP", version="0.1.0")
_ENABLE_UI = os.getenv("OVERSEAS_LOC_ENABLE_UI", "").strip().lower() in ("1", "true", "yes")
if _ENABLE_UI:
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


def _require(project: Path, *names: str) -> None:
    missing = [name for name in names if not (project / name).exists()]
    if missing:
        raise HTTPException(status_code=409, detail=f"缺少前置文件: {', '.join(missing)}")


def _purge_legacy_delivery(project: Path) -> None:
    for name in ("交付包.md", "制作包.md", "delivery-summary.md", "剪辑单.csv"):
        path = project / name
        if path.exists():
            path.unlink()


def _sync_delivery_pack(project: Path) -> None:
    """补写剪辑单与脚本包；移除旧版交付物。"""
    if not (project / "subtitles.srt").exists():
        return
    brief_path = project / "localization-brief.yaml"
    if not brief_path.exists():
        return
    brief = read_yaml(brief_path)
    compliance: dict = {}
    report_path = project / "compliance-report.json"
    if report_path.exists():
        compliance = read_json(report_path)
    elif (project / "en-localization-pack.md").exists():
        compliance = scan_project(project, brief)
    write_editor_deliverables(project, brief, compliance)
    _purge_legacy_delivery(project)


def _user_deliverables(project: Path) -> list[dict[str, str]]:
    _sync_delivery_pack(project)
    items: list[dict[str, str]] = []
    labels = {
        "交付脚本包.md": "七项脚本（标题/口播/分镜/SeedDance）",
        "交付脚本包.json": "机器可读脚本包",
        "subtitles.srt": "PR / 剪映导入字幕",
        "剪辑单.html": "剪辑分镜单（浏览器）",
    }
    for name in USER_DELIVERABLES:
        path = project / name
        if path.exists():
            items.append({"name": name, "path": name, "label": labels.get(name, name)})
    broll = project / "broll"
    if broll.exists():
        for mp4 in sorted(broll.glob("shot-*.mp4")):
            rel = mp4.relative_to(project).as_posix()
            items.append({"name": rel, "path": rel, "label": "SeedDance 空镜 mp4"})
    return items


def _delivery_ready(project: Path) -> bool:
    return all((project / name).exists() for name in USER_DELIVERABLES)


def _brief_context(project: Path) -> dict:
    path = project / "localization-brief.yaml"
    if not path.exists():
        return {}
    brief = read_yaml(path)
    link_id = brief.get("source_link_id")
    label = brief.get("theme") or project.name
    if link_id:
        label = f"竞品 #{link_id} · {(brief.get('theme') or '')[:48]}"
    return {
        "theme": brief.get("theme", ""),
        "sku": brief.get("sku", ""),
        "source_link_id": link_id,
        "source_tiktok_url": brief.get("source_tiktok_url", ""),
        "from_competitor": str(project.name).startswith("ref-"),
        "label": label.strip(),
    }


def _project_payload(slug: str) -> dict:
    project = project_dir(slug, create=False)
    if not project.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    _sync_delivery_pack(project)
    status = simple_flow_status(project)
    payload = {
        "slug": slug,
        "status": status,
        "files": file_inventory(slug),
        "brief": _brief_context(project),
    }
    sb = project / "storyboard.json"
    if sb.exists():
        payload["storyboard"] = read_json(sb).get("shots", [])
    va = project / "video-analysis.json"
    if va.exists():
        payload["analysis"] = read_json(va)
    sb_md = project / "storyboard-cn.md"
    if sb_md.exists():
        payload["storyboard_md"] = read_text(sb_md)
    en = project / "en-localization-pack.md"
    if en.exists():
        payload["english_md"] = read_text(en)
    payload["deliverables"] = _user_deliverables(project)
    payload["delivery_ready"] = _delivery_ready(project)
    payload["seedance"] = seedance_status(project)
    feedback = load_feedback(slug)
    if feedback:
        payload["feedback"] = feedback
    for name in ("compliance-report.json", "localize-meta.json"):
        path = project / name
        if path.exists():
            payload[name.removesuffix(".json").replace("-", "_")] = read_json(path)
    return payload


def _project_list_item(path: Path) -> dict:
    brief = _brief_context(path)
    status = simple_flow_status(path)
    return {
        "slug": path.name,
        "label": brief.get("label") or path.name,
        "from_competitor": brief.get("from_competitor", False),
        "source_link_id": brief.get("source_link_id"),
        "flow_step": status.get("flow_step", 1),
        "flow_label": status.get("flow_label", ""),
        **status,
    }


_ENGINE_NOTICE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>交付引擎 API</title></head>
<body style="font-family:sans-serif;max-width:640px;margin:48px auto;line-height:1.6">
  <h1>overseas-loc-mvp · 内部交付引擎</h1>
  <p>日常请使用 <strong><a href="http://127.0.0.1:8788">工作台 8788</a></strong>（素材库 → 脚本生成 → 完成交付）。</p>
  <p>本服务仅提供 API（字幕、交付 zip、SeedDance），由 8788 通过子进程调用，无需单独打开页面。</p>
  <p><a href="/docs">OpenAPI 文档</a></p>
</body></html>"""


@app.get("/", response_model=None)
async def index() -> HTMLResponse | FileResponse:
    if _ENABLE_UI:
        return FileResponse(settings.static_dir / "index.html")
    return HTMLResponse(_ENGINE_NOTICE)


@app.get("/api/health")
async def health() -> dict:
    roots = [
        {"path": str(root), "available": root.exists()} for root in settings.knowledge_roots
    ]
    return {
        "ok": True,
        "ui_version": 6,
        "delivery_zip": True,
        "delivery_files": list(USER_DELIVERABLES),
        "aigc_primary": "seedance-2.0",
        "seedance": {
            "configured": settings.seedance_configured,
            "provider": settings.seedance_provider_resolved or "none",
            "label": "SeedDance 2.0（fal.ai · 视频 B-roll）",
            "provider": "fal.ai",
            "image_model": settings.seedance_image_model_resolved,
            "text_model": settings.seedance_text_model_resolved,
            "use_fast": settings.seedance_use_fast,
            "setup": "在 overseas-loc-mvp/.env 填写 ARK_API_KEY 或 FAL_KEY；在工作台测试连接",
            "docs": "https://fal.ai/models/bytedance/seedance-2.0/text-to-video/api",
        },
        "localize_mode": {
            "label": "英文脚本包（规则模板 / 人工粘贴）",
            "uses_external_llm": False,
        },
        "knowledge": {
            "kro_script_available": settings.resolved_kro_script.exists(),
            "kro_config": str(
                (settings.base_dir / settings.kro_config_path).resolve()
                if settings.kro_config_path
                and not Path(settings.kro_config_path).is_absolute()
                else Path(settings.kro_config_path).resolve()
                if settings.kro_config_path
                else ""
            ),
            "roots": roots,
        },
        "runs_dir": str(settings.runs_dir),
    }


@app.get("/api/projects")
async def projects() -> dict:
    items = []
    for path in sorted(settings.runs_dir.iterdir()):
        if path.is_dir() and not path.name.startswith("."):
            items.append(_project_list_item(path))
    items.sort(key=lambda x: (0 if x.get("from_competitor") else 1, x["slug"]))
    return {"projects": items}


@app.get("/api/projects/{slug}")
async def project(slug: str) -> dict:
    try:
        return _project_payload(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{slug}/delivery.zip")
async def delivery_zip(slug: str) -> StreamingResponse:
    project = project_dir(slug, create=False)
    if not project.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    _sync_delivery_pack(project)
    if not _delivery_ready(project):
        raise HTTPException(status_code=409, detail="请先点「生成交付包」")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in delivery_zip_entries(project):
            path = project / name
            archive.write(path, arcname=name)
    buffer.seek(0)
    filename = f"{slug}-delivery.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{slug}/files/{relative_path:path}")
async def project_file(slug: str, relative_path: str) -> FileResponse:
    try:
        path = safe_project_file(slug, relative_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=path.name)


@app.get("/api/seedance/test")
async def seedance_test() -> dict:
    return await test_seedance_connection()


@app.get("/api/projects/{slug}/seedance")
async def project_seedance(slug: str) -> dict:
    project = project_dir(slug, create=False)
    if not project.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    return seedance_status(project)


@app.post("/api/projects/{slug}/seedance/run")
async def seedance_run_all(slug: str, force: bool = Query(False)) -> dict:
    project = project_dir(slug)
    status = seedance_status(project)
    if not status["shots"]:
        raise HTTPException(status_code=409, detail="本项目无可生成的 AI 分镜视频")
    results = await _seedance_generate_all(slug, force=force)
    assemble_result = _maybe_assemble_final_video(slug)
    payload = _project_payload(slug)
    payload["seedance_results"] = results
    payload["assemble"] = assemble_result
    if any(item.get("status") == "ok" for item in results):
        save_finished_record(project)
    return payload


def _project_seedance_source_image(project: Path) -> Path | None:
    from .character_assets import resolve_staged_seedance_source

    return resolve_staged_seedance_source(project)


def _clear_broll_for_regenerate(project: Path) -> list[str]:
    """删除已有分镜/成片，便于按最新 Prompt 与垫图重跑 SeedDance。"""
    broll = project / "broll"
    if not broll.is_dir():
        return []
    removed: list[str] = []
    for pattern in ("*.mp4", "*-seedance-meta.json", "*-seedance-request.json", "final-video-meta.json"):
        for path in broll.glob(pattern):
            try:
                path.unlink()
                removed.append(path.name)
            except OSError:
                pass
    return removed


async def _seedance_generate_all(slug: str, *, force: bool = False) -> list[dict[str, Any]]:
    project = project_dir(slug)
    if force:
        _clear_broll_for_regenerate(project)
    status = seedance_status(project)
    if not status["shots"]:
        return []
    if not settings.seedance_configured:
        return [
            {
                "number": shot["number"],
                "status": "skipped",
                "message": "未配置 ARK_API_KEY / FAL_KEY，仅生成了脚本与 Prompt",
            }
            for shot in status["shots"]
        ]
    image_path = _project_seedance_source_image(project)
    image_ref = image_path.relative_to(project).as_posix() if image_path else None
    results: list[dict[str, Any]] = []
    max_n = ai_video_max_shots()
    generated = 0
    for shot in status["shots"]:
        number = shot["number"]
        if max_n and generated >= max_n:
            results.append({
                "number": number,
                "status": "skipped",
                "message": f"已达本次上限 {max_n} 镜（可调 AI_VIDEO_MAX_SHOTS）",
            })
            continue
        if shot["ready"]:
            results.append({"number": number, "status": "skipped", "message": "已有视频"})
            continue
        prompt = sanitize_seedance_prompt(shot.get("prompt") or "")
        if len(prompt) < 10:
            results.append({"number": number, "status": "error", "message": "缺少视频 Prompt"})
            continue
        shot_image_ref = shot.get("image_ref") or image_ref
        try:
            meta = await seedance_broll(
                SeedanceRequest(
                    slug=slug,
                    shot_number=number,
                    prompt=prompt,
                    mode="submit",
                    image_ref=shot_image_ref,
                    source_approved=bool(shot_image_ref),
                )
            )
            results.append({"number": number, "status": "ok", "file": meta.get("local_file")})
            generated += 1
        except HTTPException as exc:
            # One retry for transient Ark/network failures (e.g. last shot timeout).
            try:
                meta = await seedance_broll(
                    SeedanceRequest(
                        slug=slug,
                        shot_number=number,
                        prompt=prompt,
                        mode="submit",
                        image_ref=shot_image_ref,
                        source_approved=bool(shot_image_ref),
                    )
                )
                results.append({
                    "number": number,
                    "status": "ok",
                    "file": meta.get("local_file"),
                    "retried": True,
                })
                generated += 1
            except HTTPException:
                results.append({"number": number, "status": "error", "message": exc.detail})
    return results


def _maybe_assemble_final_video(slug: str) -> dict[str, Any]:
    if not ai_video_concat_enabled():
        return {"ok": False, "message": "AI_VIDEO_CONCAT=0，未拼接成片", "file": None}
    project = project_dir(slug)
    result = assemble_storyboard_video(project, min_shots=ai_video_concat_min_shots())
    if result.get("ok"):
        from .production_archive import archive_production

        archive_production(project, slug, assemble_meta=result)
        write_editor_deliverables(
            project,
            read_yaml(project / "localization-brief.yaml"),
            read_json(project / "compliance-report.json"),
        )
    return result


@app.post("/api/projects/{slug}/assemble")
async def project_assemble(slug: str) -> dict:
    project = project_dir(slug, create=False)
    if not project.exists():
        raise HTTPException(status_code=404, detail="项目不存在")
    result = _maybe_assemble_final_video(slug)
    payload = _project_payload(slug)
    payload["assemble"] = result
    if result.get("ok"):
        save_finished_record(project)
    return payload


@app.get("/api/library/finished")
async def library_finished_list() -> dict:
    return {
        "items": list_finished(),
        "index_csv": str(FINISHED_INDEX),
    }


@app.get("/api/library/finished/{slug}")
async def library_finished_one(slug: str) -> dict:
    path = FINISHED_DIR / f"{slug}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="成稿记录不存在")
    return read_json(path)


@app.get("/api/library/feedback")
async def library_feedback_list() -> dict:
    return {
        "items": list_feedback(),
        "index_csv": str(FEEDBACK_INDEX),
    }


@app.get("/api/library/feedback/{slug}")
async def library_feedback_one(slug: str) -> dict:
    record = load_feedback(slug)
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    return record


@app.post("/api/library/feedback/{slug}")
async def library_feedback_save(slug: str, body: FeedbackUpdateRequest) -> dict:
    try:
        record = update_feedback(
            slug,
            {
                "manual_edits": body.manual_edits,
                "adopted": body.adopted,
                "notes": body.notes,
                "publish": {
                    "views": body.publish_views,
                    "engagement": body.publish_engagement,
                    "notes": body.publish_notes,
                },
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "feedback": record, "index_csv": str(FEEDBACK_INDEX)}


@app.post("/api/brief")
async def save_brief(request: BriefRequest) -> dict:
    if request.material_id != request.slug:
        raise HTTPException(status_code=422, detail="MVP 要求 material_id 与 slug 一致")
    project = project_dir(request.slug)
    data = request.model_dump()
    write_yaml(project / "localization-brief.yaml", data)
    atomic_write(project / "gate-report.md", make_gate_report(data))
    return _project_payload(request.slug)


@app.post("/api/storyboard")
async def save_storyboard(request: StoryboardRequest) -> dict:
    project = project_dir(request.slug)
    _require(project, "localization-brief.yaml", "gate-report.md")
    brief = read_yaml(project / "localization-brief.yaml")
    shots = [shot.model_dump(by_alias=True) for shot in request.shots]
    atomic_write(project / "storyboard-cn.md", make_storyboard(brief, shots))
    write_json(project / "storyboard.json", {"shots": shots})
    return _project_payload(request.slug)


@app.post("/api/quick/{slug}/finish")
async def quick_finish(slug: str) -> dict:
    """一键：英文+字幕+七项脚本包；可选 SeedDance 空镜（SKIP_SEEDANCE=1 时跳过）。"""
    await _run_localize(slug, "demo_local")
    result = await srt(SlugRequest(slug=slug))
    compliance = result.get("compliance", {})
    skip_seedance = not ai_video_on_finish()
    seedance_results: list[dict[str, Any]] = []
    if not skip_seedance:
        seedance_results = await _seedance_generate_all(slug)
    project = project_dir(slug)
    assemble_result: dict[str, Any] | None = None
    if not skip_seedance:
        st = seedance_status(project)
        if any(s.get("ready") for s in st.get("shots") or []):
            assemble_result = _maybe_assemble_final_video(slug)
    if any(r.get("status") == "ok" for r in seedance_results):
        write_editor_deliverables(
            project,
            read_yaml(project / "localization-brief.yaml"),
            compliance,
        )
    save_finished_record(project)
    result = _project_payload(slug)
    result["compliance"] = read_json(project / "compliance-report.json")
    result["seedance_results"] = seedance_results
    if assemble_result:
        result["assemble"] = assemble_result
    msg_extra = ""
    if any(r.get("status") == "ok" for r in seedance_results):
        msg_extra = " + AI 分镜视频"
    if assemble_result and assemble_result.get("ok"):
        msg_extra += " + 拼接成片"
    result["message"] = "交付完成：七项脚本包 + 字幕" + msg_extra
    result["delivery_ready"] = True
    return result


@app.post("/api/quick/{slug}/english")
async def quick_english(slug: str) -> dict:
    result = await _run_localize(slug, "demo_local")
    result["knowledge_hint"] = "已自动检索公司知识库并写入英文脚本上下文"
    return result


@app.post("/api/quick/{slug}/deliver")
async def quick_deliver(slug: str) -> dict:
    return await srt(SlugRequest(slug=slug))


@app.post("/api/knowledge/search")
async def knowledge_search(request: KnowledgeSearchRequest) -> dict:
    return search_knowledge(request.query, request.limit)


async def _run_localize(slug: str, provider: str) -> dict:
    project = project_dir(slug)
    _require(project, "localization-brief.yaml", "gate-report.md", "storyboard-cn.md")
    brief = read_yaml(project / "localization-brief.yaml")
    if not brief.get("allowed_claims_available") or not brief.get("allowed_claims_en"):
        raise HTTPException(status_code=409, detail="B3 allowed_claims_en 尚未批准")
    storyboard = read_text(project / "storyboard-cn.md")
    query = " ".join(
        [brief.get("sku", ""), brief.get("theme", ""), " ".join(brief["allowed_claims_en"])]
    )
    knowledge_payload = search_knowledge(query, 6)
    forbidden = list(dict.fromkeys(FORBIDDEN_TERMS + brief.get("forbidden_terms_extra", [])))
    localize_request = {
        "$schema": "localize-request-v1",
        "material_id": brief["material_id"],
        "slug": brief["slug"],
        "sku": brief["sku"],
        "target_market": brief["target_country"],
        "language": brief["language"],
        "theme": brief["theme"],
        "tone": "us_tiktok_spoken",
        "output_schema": "en-localization-pack-v1",
        "prompt_version": settings.prompt_version,
        "allowed_claims_en": brief["allowed_claims_en"],
        "forbidden_terms": forbidden,
        "storyboard_cn": storyboard,
    }
    write_json(project / "localize-request.json", localize_request)
    user_prompt = render_user_prompt(localize_request, storyboard, context_text(knowledge_payload))
    write_json(
        project / "prompt-snapshot.json",
        {
            "prompt_version": settings.prompt_version,
            "system": SYSTEM_PROMPT,
            "user": user_prompt,
            "knowledge": knowledge_payload,
        },
    )

    markdown = demo_localization(brief, storyboard)
    meta = {
        "model": "rule-template-v1",
        "provider": "rule_template",
        "requested_at": utc_now(),
        "latency_ms": 0,
        "input_tokens": None,
        "output_tokens": None,
        "status": "template_success",
    }
    validation = validate_localization(markdown, brief["allowed_claims_en"], forbidden)
    meta.update(
        {
            "material_id": brief["material_id"],
            "prompt_version": settings.prompt_version,
            "validation": validation,
        }
    )
    atomic_write(project / "en-localization-pack.md", markdown)
    write_json(project / "localize-meta.json", meta)
    return {
        **_project_payload(slug),
        "provider": "rule_template",
        "validation": validation,
        "markdown": markdown,
    }


@app.post("/api/localize")
async def localize(request: LocalizeRequest) -> dict:
    return await _run_localize(request.slug, request.provider)


@app.post("/api/localize/import")
async def import_localize(request: ManualLocalizeRequest) -> dict:
    project = project_dir(request.slug)
    _require(project, "localization-brief.yaml", "storyboard-cn.md")
    brief = read_yaml(project / "localization-brief.yaml")
    forbidden = list(dict.fromkeys(FORBIDDEN_TERMS + brief.get("forbidden_terms_extra", [])))
    validation = validate_localization(
        request.markdown, brief["allowed_claims_en"], forbidden
    )
    atomic_write(project / "en-localization-pack.md", request.markdown)
    write_json(
        project / "localize-meta.json",
        {
            "material_id": brief["material_id"],
            "prompt_version": settings.prompt_version,
            "model": "manual",
            "provider": "manual_paste",
            "requested_at": utc_now(),
            "latency_ms": None,
            "status": "manual_success",
            "validation": validation,
        },
    )
    return {**_project_payload(request.slug), "validation": validation}


@app.post("/api/srt")
async def srt(request: SlugRequest) -> dict:
    project = project_dir(request.slug)
    _require(
        project,
        "localization-brief.yaml",
        "storyboard-cn.md",
        "en-localization-pack.md",
    )
    brief = read_yaml(project / "localization-brief.yaml")
    markdown = read_text(project / "en-localization-pack.md")
    try:
        srt_text = generate_srt(markdown)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    atomic_write(project / "subtitles.srt", srt_text)
    compliance = scan_project(project, brief)
    delivery_pack = write_editor_deliverables(project, brief, compliance)
    save_finished_record(project)
    return {
        **_project_payload(request.slug),
        "compliance": compliance,
        "srt": srt_text,
        "delivery_pack": delivery_pack,
    }


@app.post("/api/compliance/scan")
async def compliance_scan(request: SlugRequest) -> dict:
    project = project_dir(request.slug)
    _require(project, "localization-brief.yaml", "en-localization-pack.md")
    brief = read_yaml(project / "localization-brief.yaml")
    return scan_project(project, brief)


@app.post("/api/upload/{slug}")
async def upload(slug: str, file: UploadFile = File(...)) -> dict:
    project = project_dir(slug)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=415, detail="仅支持 PNG/JPG/WEBP")
    inputs = project / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    target = inputs / f"seedance-source{suffix}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    return {"image_ref": target.relative_to(project).as_posix(), "bytes": target.stat().st_size}


@app.post("/api/seedance/broll")
async def seedance_broll(request: SeedanceRequest) -> dict:
    project = project_dir(request.slug)
    _require(project, "storyboard.json")
    shots = read_json(project / "storyboard.json")["shots"]
    shot = next((item for item in shots if item["number"] == request.shot_number), None)
    if not shot or not shot_generates_video(str(shot.get("footage_type") or ""), ai_video_mode()):
        raise HTTPException(status_code=409, detail="该镜头未标记为 AI 可生成视频（AI_BROLL / AI_VIDEO）")
    image_path = None
    if request.image_ref:
        if not request.source_approved:
            raise HTTPException(status_code=409, detail="图片必须确认已审核并有使用权")
        try:
            image_path = safe_project_file(request.slug, request.image_ref)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")
    from .video_production import read_project_video_settings

    prod = read_project_video_settings(project)
    preview = {
        "provider": "fal.ai",
        "model": settings.seedance_image_model_resolved if image_path else settings.seedance_text_model_resolved,
        "shot_number": request.shot_number,
        "prompt": request.prompt,
        "image_ref": request.image_ref,
        "duration": str(prod.duration_sec),
        "resolution": prod.resolution,
        "aspect_ratio": prod.aspect_ratio,
        "generate_audio": False,
        "status": "preview",
        "requested_at": utc_now(),
    }
    broll_dir = project / "broll"
    broll_dir.mkdir(parents=True, exist_ok=True)
    write_json(broll_dir / f"shot-{request.shot_number}-seedance-request.json", preview)
    if request.mode == "preview":
        return preview
    if not settings.seedance_configured:
        raise HTTPException(
            status_code=409,
            detail="未配置 ARK_API_KEY / FAL_KEY；请求预览已保存，请配置后再提交",
        )
    try:
        return await call_seedance(project, request.prompt, image_path, request.shot_number, prod_settings=prod)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
