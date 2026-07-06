from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Cursor 内置终端会注入 Playwright 沙箱路径，导致 TikTok 采集无法启动本机 Chrome
_workflow_root = ROOT.parent
if str(_workflow_root) not in sys.path:
    sys.path.insert(0, str(_workflow_root))
try:
    from tiktok_collector.browser_launch import sanitize_playwright_env

    sanitize_playwright_env()
except Exception:
    pass

from ensure_legacy_paths import ensure_legacy_junctions

ensure_legacy_junctions()

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from paths import OVERSEAS_RUNS_DIR, WEB_DIR

from .brand_policy import (
    detect_content_line,
    display_product_name,
    product_material_match,
    sanitize_analysis,
)
from .data import (
    filter_materials,
    filter_options,
    link_has_script,
    load_analysis_detail,
    load_materials,
    load_script_payload,
    material_detail,
    material_already_analyzed,
    needs_doubao_analysis,
    shot_count_for,
)
from .analyze_jobs import analyze_status, clear_analyze_job, start_material_analyze
from .archive_delivery import build_archive_zip, list_archive_versions
from .auth_middleware import WorkbenchAuthMiddleware
from .deploy_config import public_status as deployment_status, workbench_host, workbench_port
from .doubao_config import doubao_config, script_llm_config, video_analysis_policy
from .daily_quota import (
    assert_script_quota,
    assert_video_quota,
    production_profile,
    quota_status,
    record_script_generation,
    record_video_output,
    video_quota_status,
)
from .doubao_script import test_script_connection
from .doubao_video_analysis import test_connection as test_doubao_connection
from .jobs import job_status, start_job
from .video_queue import (
    assert_can_run,
    cancel_ticket,
    complete_ticket,
    is_ticket_cancelled,
    join_queue,
    mark_running,
    queue_snapshot,
    ticket_status,
)
from .library_api import list_feedback, list_finished, load_feedback, load_templates, save_feedback
from .feedback_loop import preview_constraints
from .radar import radar_feed
from .feedback_tags import ISSUE_TAG_DEFS
from .llm_script import pick_template
from .feishu_bridge import feishu_auth_url_payload, feishu_doctor_payload, feishu_status_payload
from .olm_bridge import (
    build_delivery_zip,
    delivery_ready,
    ensure_delivery_project,
    ensure_ffmpeg_ready,
    ffmpeg_status,
    finish_project,
    project_exists,
    sync_project_video_settings,
)
from .product_tags import normalize_selected_tags, product_delivery_tags, enrich_product_from_knowledge
from .products import get_product, list_products, update_product
from .prompt_library import ensure_default_presets, list_prompts, record_usage
from .reverse_prompt import run_reverse_prompt
from .scene_script import scenario_conflict_note
from .script_gen import generate_script, save_script_edits
from .thumbnails import ensure_thumbnail_cached
from .tiktok_collector_bridge import run_collector_import
from .tiktok_collector_bridge import query_collector_database
from .tiktok_collector_bridge import collector_database_enabled
from .tiktok_collector_bridge import sync_collector_database_to_workflow
from .seedance_bridge import (
    assemble_project,
    confirm_hero_frames,
    generate_hero_frames,
    hero_frame_gate_enabled,
    hero_frames_status,
    project_status,
    refresh_project_seedance_source,
    regenerate_hero_frame,
    run_all,
    seedance_config,
    test_connection,
)

app = FastAPI(title="海外视频本地化工作台", version="1.0.0")


class StaticNoCacheMiddleware(BaseHTTPMiddleware):
    """避免浏览器长期缓存 app.js/styles.css，导致 UI 更新不生效。"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path == "/" or (
            path.startswith("/static/")
            and path.rsplit(".", 1)[-1].lower() in ("js", "css", "html")
        ):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.add_middleware(StaticNoCacheMiddleware)
app.add_middleware(WorkbenchAuthMiddleware)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
UI_VERSION = 184


def _render_index() -> HTMLResponse:
    raw = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    raw = raw.replace("{{UI_VERSION}}", str(UI_VERSION))
    from .deploy_config import api_token

    raw = raw.replace("{{WORKBENCH_TOKEN_JS}}", json.dumps(api_token()))
    return HTMLResponse(raw)


def _tiktok_collector_runtime() -> dict:
    workflow_root = ROOT.parent
    if str(workflow_root) not in sys.path:
        sys.path.insert(0, str(workflow_root))
    try:
        from tiktok_collector.browser_launch import collector_runtime_status

        return collector_runtime_status()
    except Exception as exc:
        return {"cursor_sandbox": False, "system_browsers": [], "error": str(exc)}


def _friendly_analyze_message(detail: dict[str, Any] | None, link_id: int | str) -> str:
    analysis = (detail or {}).get("analysis") if detail else None
    err = ""
    if isinstance(analysis, dict):
        err = str(analysis.get("error_message") or "")
    if "ReadTimeout" in err:
        return (
            f"豆包 API 响应超时（约 3 分钟）。可点击「重试拆解」，"
            f"或将源视频放入「源视频/{link_id}.mp4」后重新打开。"
        )
    if "doubao_fallback" in err:
        return "豆包拆解失败，已回退规则模板。可重试拆解，或补充源视频后再试。"
    return "豆包拆解未完成，请稍后重试。"


def _sanitize_analyze_message(message: str | None) -> str:
    text = str(message or "").strip()
    if not text:
        return ""
    if "video_analysis.csv" in text or "豆包失败，已回退规则" in text or "rule shots=" in text:
        return ""
    return text


class GenerateRequest(BaseModel):
    product_id: str = ""
    bridge: bool = Field(default=True, description="同步创建 overseas-loc-mvp 项目")
    target_country: str = "US"
    language: str = "en"
    style: str = "us_tiktok_spoken"
    audience_tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    selling_tags: list[str] = Field(default_factory=list)
    pain_tags: list[str] = Field(default_factory=list)
    aspect_ratio: str = "9:16"
    edit_mode: str = "multi_shot"
    resolution: str = "720P"
    duration_sec: int = 5
    generate_count: int = 1
    creative_brief: str = ""
    prompt_enhanced: bool = False


class ScriptEditRequest(BaseModel):
    title: str = ""
    subtitle: str = ""
    voiceover_20s: str = ""
    storyboard: list[dict[str, Any]] = Field(default_factory=list)


class SeedanceRunRequest(BaseModel):
    resolution: str = "720P"
    aspect_ratio: str = "9:16"
    duration_sec: int = Field(default=5, ge=4, le=20)
    generate_count: int = Field(default=1, ge=1, le=4)
    edit_mode: str = "multi_shot"


class ProductUpdateRequest(BaseModel):
    product_name: str = ""
    target_audience: str = ""
    core_selling_points: str = ""
    pain_points: str = ""
    usage_scenarios: str = ""
    forbidden_terms: str = ""
    price_range: str = ""
    competitor_ref: str = ""


class FeedbackUpdateRequest(BaseModel):
    manual_edits: str = ""
    adopted: str = "待定"
    notes: str = ""
    issue_tags: list[str] = Field(default_factory=list)
    publish_views: str = ""
    publish_engagement: str = ""
    publish_notes: str = ""


class JobStartRequest(BaseModel):
    engine: str = "auto"
    provider: str = "auto"
    product_id: str = ""


class VideoQueueJoinRequest(BaseModel):
    slug: str
    label: str = ""
    client_id: str = ""


class VideoQueueCompleteRequest(BaseModel):
    ok: bool = True
    message: str = ""
    client_id: str = ""


class TikTokCollectorRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    limit_per_keyword: int = Field(default=50, ge=1, le=200)
    product_id: str = ""


class TikTokCollectorDbSyncRequest(BaseModel):
    q: str = ""
    source_keyword: str = ""
    processing_status: str = ""
    limit: int = Field(default=50, ge=1, le=200)
    product_id: str = ""


class EnsureAnalysisRequest(BaseModel):
    provider: str = "rule"  # rule | doubao | auto


class ReversePromptBody(BaseModel):
    reverse_type: str = "video"
    product_id: str = ""
    save: bool = True


@app.get("/")
async def index() -> HTMLResponse:
    return _render_index()


@app.get("/api/health")
async def health() -> dict:
    items = load_materials()
    script_cfg = script_llm_config()
    ensure_default_presets()
    return {
        "ok": True,
        "ui_version": UI_VERSION,
        "workbench": True,
        "materials": len(items),
        "analyzed": sum(1 for i in items if i.get("has_analysis")),
        "products": len(list_products()),
        "finished": len(list_finished()),
        "prompt_library": len(list_prompts()),
        "job": job_status(),
        "video_queue": queue_snapshot(),
        "llm": {
            **script_cfg,
            "available": script_cfg["effective_provider"] in ("doubao", "anthropic"),
            "role": "脚本生成",
        },
        "decompose": {
            "mode": "doubao" if doubao_config().get("configured") else "rule",
            "provider": doubao_config().get("provider_default", "auto"),
            "label": (
                "结构拆解（豆包视频理解 + 规则兜底）"
                if doubao_config().get("configured")
                else "结构拆解（基于标题/话题标签的规则模板）"
            ),
            "doubao": doubao_config(),
            "policy": video_analysis_policy(),
        },
        "delivery_engine": {
            "mode": "subprocess",
            "label": "overseas-loc-mvp（字幕/zip/SeedDance，由工作台子进程调用）",
            "ffmpeg": ffmpeg_status(),
        },
        "aigc_primary": "seedance-2.0",
        "seedance": seedance_config(),
        "hero_frame_gate": hero_frame_gate_enabled(),
        "feishu": feishu_status_payload(),
        "tiktok_collector": {
            "available": True,
            "limit_per_keyword": 50,
            "output_dir": str((ROOT.parent / "tiktok_collector" / "data" / "raw").resolve()),
            "clean_output_dir": str((ROOT.parent / "tiktok_collector" / "data" / "raw" / "clean").resolve()),
            "mysql_enabled": collector_database_enabled(),
            "runtime": _tiktok_collector_runtime(),
        },
        "production": production_profile(),
        "deployment": deployment_status(),
    }


@app.get("/api/feishu/status")
async def feishu_status() -> dict:
    payload = feishu_status_payload()
    return {"feishu": payload, **payload}


@app.post("/api/feishu/auth-url")
async def feishu_auth_url() -> dict:
    return feishu_auth_url_payload()


@app.get("/api/feishu/doctor")
async def feishu_doctor(offline: bool = True) -> dict:
    return feishu_doctor_payload(offline=offline)


@app.get("/api/filters")
async def filters() -> dict:
    return filter_options()


@app.get("/api/materials")
async def materials(
    category: str = "",
    subcategory: str = "",
    q: str = "",
    analyzed_only: bool = False,
) -> dict:
    items = load_materials()
    filtered = filter_materials(
        items,
        category=category,
        subcategory=subcategory,
        keyword=q,
        analyzed_only=analyzed_only,
    )
    return {"total": len(filtered), "items": filtered}


@app.get("/api/radar/feed")
async def radar_feed_api(
    product_id: str = "",
    limit: int = 24,
    analyzed_only: bool = True,
) -> dict:
    """CreatOK 式爆款雷达：综合播放/互动/拆解/品类匹配评分，不替换素材库默认排序。"""
    return radar_feed(product_id=product_id.strip(), limit=limit, analyzed_only=analyzed_only)


@app.get("/api/materials/{link_id}/analysis/detail")
async def material_analysis_detail(link_id: int, auto_start: bool = True) -> dict:
    """打开素材详情时自动触发豆包拆解（若尚未完成）。auto_start=0 仅读缓存，不启动拆解。"""
    try:
        return await _material_analysis_detail_payload(link_id, auto_start=auto_start)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"拆解详情加载失败: {exc}") from exc


async def _material_analysis_detail_payload(link_id: int, *, auto_start: bool = True) -> dict:
    detail = load_analysis_detail(str(link_id))
    job = analyze_status(link_id)
    lid = str(link_id)

    if detail and shot_count_for(lid, detail) >= 1:
        clear_analyze_job(link_id)
        warning = ""
        analysis = detail.get("analysis") or {}
        if isinstance(analysis, dict) and analysis.get("analyze_provider") == "rule":
            if "doubao_fallback" in str(analysis.get("error_message") or ""):
                warning = "最近一次豆包拆解超时，当前展示已有分镜结果。"
        return {**detail, "status": "ready", "warning": warning}

    if needs_doubao_analysis(lid, detail):
        if not auto_start:
            base = detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}
            return {
                **base,
                "status": "pending",
                "message": "尚未精细拆解；一键出片将自动规则拆解，或手动点「精细拆解」",
                "retryable": True,
            }
        if job and job.get("status") == "running":
            base = detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}
            return {**base, "status": "running", "message": "豆包视频拆解中，请稍候…", "job": job}
        if not job or job.get("status") != "running":
            job = start_material_analyze(link_id)
        base = detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}
        return {
            **base,
            "status": "running",
            "message": "豆包视频拆解中，请稍候…",
            "job": job,
        }

    policy = video_analysis_policy()
    if not detail and not policy.get("auto_enabled"):
        raise HTTPException(
            status_code=404,
            detail="素材尚未拆解。请先在设置运行「批量规则拆解（免费）」，或点「精细拆解」",
        )
    if not detail and not policy.get("on_view"):
        raise HTTPException(
            status_code=404,
            detail="素材尚未拆解。请运行「批量规则拆解（免费）」；豆包精细拆解请手动触发",
        )
    if detail and not policy.get("llm_enabled") and shot_count_for(lid, detail) < 1:
        return {
            **detail,
            "status": "ready",
            "warning": policy.get("message") or "视频豆包拆解已暂停，仅展示已有元数据。",
            "retryable": False,
        }

    if detail and isinstance(detail.get("analysis"), dict):
        err = str((detail["analysis"] or {}).get("error_message") or "")
        if "doubao_fallback" in err:
            return {
                **detail,
                "status": "error",
                "message": _friendly_analyze_message(detail, link_id),
                "retryable": True,
                "job": job,
            }

    if job and job.get("status") == "error":
        msg = _sanitize_analyze_message(job.get("output")) or _friendly_analyze_message(detail, link_id)
        return {
            **(detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}),
            "status": "error",
            "message": msg,
            "retryable": True,
            "job": job,
        }

    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在或未抓取元数据")
    return {**detail, "status": "ready"}


@app.post("/api/materials/{link_id}/analyze")
async def material_analyze(link_id: int) -> dict:
    """手动重试豆包拆解。"""
    policy = video_analysis_policy()
    if not policy.get("llm_enabled"):
        raise HTTPException(
            status_code=403,
            detail=policy.get("message") or "视频豆包拆解已暂停",
        )
    from .jobs import PIPELINE, PYTHON
    import subprocess

    clear_analyze_job(link_id)
    proc = subprocess.run(
        [
            str(PYTHON),
            str(PIPELINE),
            "decompose",
            "--provider",
            "doubao",
            "--link-id",
            str(link_id),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    detail = load_analysis_detail(str(link_id))
    if proc.returncode != 0 or (detail and shot_count_for(str(link_id), detail) < 1):
        msg = _friendly_analyze_message(detail, link_id)
        if proc.returncode != 0 and proc.stderr:
            msg = (proc.stderr or proc.stdout or msg)[-300:]
        raise HTTPException(status_code=500, detail=msg)
    return {"ok": True, "status": "ready", "detail": detail}


@app.post("/api/materials/{link_id}/ensure-analysis")
async def ensure_material_analysis(link_id: int, body: EnsureAnalysisRequest | None = None) -> dict:
    """确保素材已有结构拆解：默认规则拆解（省 token），可选豆包精细拆解。"""
    import subprocess

    from .jobs import PIPELINE, PYTHON

    lid = str(link_id)
    if not material_detail(link_id):
        raise HTTPException(status_code=404, detail="素材不存在")

    if material_already_analyzed(lid):
        detail = load_analysis_detail(lid)
        provider = (detail or {}).get("analyze_provider") or "cached"
        return {"ok": True, "status": "ready", "provider": provider, "detail": detail}

    req = body or EnsureAnalysisRequest()
    provider = (req.provider or "rule").strip().lower()
    if provider == "auto":
        policy = video_analysis_policy()
        cfg = doubao_config()
        provider = (
            "doubao"
            if policy.get("llm_enabled") and cfg.get("configured")
            else "rule"
        )
    if provider not in ("rule", "doubao"):
        provider = "rule"
    if provider == "doubao" and not video_analysis_policy().get("llm_enabled"):
        provider = "rule"

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(PYTHON),
                str(PIPELINE),
                "decompose",
                "--provider",
                provider,
                "--link-id",
                str(link_id),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

    proc = await run_in_threadpool(_run)
    detail = load_analysis_detail(lid)
    if proc.returncode != 0 or not material_already_analyzed(lid):
        msg = _friendly_analyze_message(detail, link_id)
        if proc.returncode != 0:
            msg = ((proc.stderr or proc.stdout or msg) or "拆解失败")[-400:]
        raise HTTPException(status_code=500, detail=msg)
    return {
        "ok": True,
        "status": "ready",
        "provider": (detail or {}).get("analyze_provider") or provider,
        "detail": detail,
    }


@app.get("/api/materials/{link_id}/thumbnail")
async def material_thumbnail(link_id: int) -> FileResponse:
    path = ensure_thumbnail_cached(link_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="封面不可用，请在「设置」运行「同步 TikTok」或「缓存封面」")
    return FileResponse(path, media_type="image/jpeg", filename=f"{link_id}.jpg")


@app.get("/api/materials/{link_id}")
async def material(link_id: int) -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    return detail


@app.get("/api/materials/{link_id}/preview")
async def material_preview(link_id: int, product_id: str = "") -> dict:
    try:
        return await _material_preview_payload(link_id, product_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预览加载失败: {exc}") from exc


async def _material_preview_payload(link_id: int, product_id: str = "") -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    if not detail.get("analysis"):
        raise HTTPException(status_code=409, detail="该素材尚未结构拆解，请先在「设置」运行「结构拆解」")

    products = list_products()
    product = None
    if product_id:
        product = get_product(product_id)
    if not product and products:
        product = get_product("便携恒温杯") or products[0]

    pid = (product or {}).get("product_id", "")
    raw_analysis = detail.get("analysis") or {}
    analysis = sanitize_analysis(raw_analysis, pid) if pid else raw_analysis
    templates = load_templates()
    matched = pick_template(raw_analysis, templates)
    template_hint = analysis.get("reusable_template", "")
    content_line = detect_content_line(detail)
    matched_product = product_material_match(pid, detail) if pid else True
    slug = detail.get("bridged_slug") or f"ref-{link_id:03d}"
    has_script = detail.get("has_script") or link_has_script(link_id)
    delivered = delivery_ready(slug)
    tag_pool = product_delivery_tags(product)
    saved = load_script_payload(link_id)
    pack_market = {}
    if isinstance(detail.get("script_pack"), dict):
        pack_market = (detail["script_pack"].get("inputs") or {}).get("market") or {}
    if pack_market.get("audience_tags"):
        saved = {
            **saved,
            "audience_tags": pack_market.get("audience_tags") or [],
            "scenario_tags": pack_market.get("scenario_tags") or [],
            "selling_tags": pack_market.get("selling_tags") or [],
            "pain_tags": pack_market.get("pain_tags") or [],
        }
    selected = normalize_selected_tags(
        tag_pool,
        audience=saved.get("audience_tags") or None,
        scenarios=saved.get("scenario_tags") or None,
        selling=saved.get("selling_tags") or None,
        pains=saved.get("pain_tags") or None,
    )
    scenario_tags = selected.get("scenarios") or []
    return {
        "material": {**detail, "analysis": analysis, "content_line": content_line},
        "product": product,
        "template": matched,
        "template_hint": template_hint,
        "slug": slug,
        "project_ready": project_exists(slug),
        "has_script": has_script,
        "delivery_ready": delivered,
        "workflow": {
            "ref_ready": bool(raw_analysis),
            "product_ready": bool(pid),
            "script_ready": has_script,
            "delivery_ready": delivered,
        },
        "content_line": content_line,
        "product_match": matched_product,
        "brand_product": display_product_name(pid) if pid else "",
        "delivery_tags": tag_pool,
        "library_tags": tag_pool,
        "selected_tags": selected,
        "scenario_conflict_note": scenario_conflict_note(scenario_tags),
        "can_finish": has_script,
        "script_pack": detail.get("script_pack"),
        "script_meta": detail.get("script_meta"),
        "workflow_note": (
            "仅借鉴本条竞品的钩子/节奏/分镜结构；成片口播与画面统一露出我方品牌，不出现竞品名。"
        ),
        "seedance": await run_in_threadpool(_safe_project_status, slug),
    }


def _safe_project_status(slug: str) -> dict[str, Any] | None:
    if not project_exists(slug):
        return None
    try:
        return project_status(slug)
    except Exception as exc:
        return {
            "available": True,
            "configured": False,
            "error": str(exc)[-400:],
            "shots": [],
        }


@app.post("/api/materials/{link_id}/generate")
async def generate(link_id: int, body: GenerateRequest) -> dict:
    try:
        assert_script_quota()
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    try:
        result = generate_script(
            link_id,
            product_id=body.product_id,
            bridge=body.bridge,
            market={
                "target_country": body.target_country,
                "language": body.language,
                "style": body.style,
                "audience_tags": body.audience_tags,
                "scenario_tags": body.scenario_tags,
                "selling_tags": body.selling_tags,
                "pain_tags": body.pain_tags,
                "aspect_ratio": body.aspect_ratio,
                "edit_mode": body.edit_mode,
                "resolution": body.resolution,
                "duration_sec": body.duration_sec,
                "generate_count": body.generate_count,
                "creative_brief": body.creative_brief,
                "prompt_enhanced": body.prompt_enhanced,
            },
        )
        slug = f"ref-{link_id:03d}"
        result["slug"] = slug
        meta = result.get("meta") if isinstance(result.get("meta"), dict) else {}
        if not meta and isinstance(result.get("script_pack"), dict):
            meta = {"provider": result.get("provider"), "model": result.get("model")}
        result["daily_quota"] = record_script_generation(link_id, result.get("meta") or {})
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成失败: {exc}") from exc


@app.put("/api/materials/{link_id}/script")
async def update_material_script(link_id: int, body: ScriptEditRequest) -> dict:
    try:
        return save_script_edits(link_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存脚本失败: {exc}") from exc


@app.get("/api/products")
async def products() -> dict:
    rows = list_products()
    return {"total": len(rows), "items": rows}


@app.get("/api/products/{product_id}")
async def product_one(product_id: str) -> dict:
    row = get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="产品不存在")
    enriched = enrich_product_from_knowledge(row)
    return {
        **enriched,
        "delivery_tags": product_delivery_tags(enriched),
    }


@app.put("/api/products/{product_id}")
async def product_save(product_id: str, body: ProductUpdateRequest) -> dict:
    try:
        return update_product(product_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/templates")
async def templates() -> dict:
    items = load_templates()
    return {"total": len(items), "items": items}


@app.get("/api/prompt-library")
async def prompt_library(
    product_id: str = Query(""),
    content_line: str = Query(""),
    source: str = Query(""),
    reverse_type: str = Query(""),
    prompt_type: str = Query(""),
    limit: int = Query(200, ge=1, le=500),
) -> dict:
    items = list_prompts(
        product_id=product_id,
        content_line=content_line,
        source=source,
        reverse_type=reverse_type,
        prompt_type=prompt_type,
        limit=limit,
    )
    presets = [i for i in items if i.get("source") == "preset"]
    reverse_items = [i for i in items if str(i.get("source") or "").startswith("reverse")]
    return {
        "total": len(items),
        "preset_count": len(presets),
        "reverse_count": len(reverse_items),
        "items": items,
        "presets": presets,
        "reverse": reverse_items,
    }


@app.post("/api/materials/{link_id}/reverse-prompt")
async def material_reverse_prompt(link_id: int, body: ReversePromptBody) -> dict:
    try:
        return await run_in_threadpool(
            run_reverse_prompt,
            link_id,
            reverse_type=body.reverse_type,
            product_id=body.product_id,
            save=body.save,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/prompt-library/{prompt_id}/use")
async def prompt_library_use(prompt_id: str) -> dict:
    row = record_usage(prompt_id)
    if not row:
        raise HTTPException(status_code=404, detail="提示词不存在")
    return {"ok": True, "item": row}


@app.get("/api/library/finished")
async def library_finished_list() -> dict:
    return {"items": list_finished()}


@app.get("/api/library/finished/{slug}")
async def library_finished_one(slug: str) -> dict:
    for item in list_finished():
        if item.get("slug") == slug:
            return item
    raise HTTPException(status_code=404, detail="成稿记录不存在")


@app.get("/api/library/feedback")
async def library_feedback_list() -> dict:
    return {"items": list_feedback()}


@app.get("/api/library/feedback-tags")
async def library_feedback_tags() -> dict:
    return {
        "items": [
            {"id": tag_id, "label": meta["label"], "hint_zh": meta["hint_zh"]}
            for tag_id, meta in ISSUE_TAG_DEFS.items()
        ],
    }


@app.get("/api/library/feedback-constraints")
async def library_feedback_constraints(
    product_id: str = Query(..., min_length=1),
    scenario_tags: str = Query("", description="逗号分隔场景标签"),
) -> dict:
    tags = [t.strip() for t in scenario_tags.split(",") if t.strip()]
    return preview_constraints(product_id, tags)


@app.get("/api/library/feedback/{slug}")
async def library_feedback_one(slug: str) -> dict:
    record = load_feedback(slug)
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    return record


@app.post("/api/library/feedback/{slug}")
async def library_feedback_save(slug: str, body: FeedbackUpdateRequest) -> dict:
    try:
        record = save_feedback(
            slug,
            {
                "manual_edits": body.manual_edits,
                "adopted": body.adopted,
                "notes": body.notes,
                "issue_tags": body.issue_tags,
                "publish": {
                    "views": body.publish_views,
                    "engagement": body.publish_engagement,
                    "notes": body.publish_notes,
                },
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "feedback": record}


@app.get("/api/jobs/status")
async def jobs_status() -> dict:
    return job_status()


@app.post("/api/jobs/{job_name}")
async def jobs_start(job_name: str, body: JobStartRequest | None = None) -> dict:
    try:
        return start_job(
            job_name,
            engine=(body.engine if body else "auto"),
            provider=(body.provider if body else "auto"),
            product_id=(body.product_id if body else "") or "",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/tiktok-collector/collect")
async def tiktok_collector_collect(body: TikTokCollectorRequest) -> dict:
    keywords = [item.strip() for item in body.keywords if item.strip()]
    if not keywords:
        raise HTTPException(status_code=400, detail="请至少输入一个关键词")
    # 工作台采集一律使用有头浏览器，便于用户完成 TikTok 登录/验证码
    os.environ["TIKTOK_COLLECTOR_HEADLESS"] = "false"
    os.environ.setdefault("TIKTOK_COLLECTOR_MANUAL_VERIFY_WAIT_MS", "180000")
    try:
        result = await run_in_threadpool(
            run_collector_import,
            keywords,
            limit_per_keyword=body.limit_per_keyword,
            product_id=body.product_id or "",
        )
    except Exception as exc:
        msg = str(exc).strip() or "未知错误"
        if not msg.startswith("TikTok") and "Playwright" not in msg:
            msg = f"TikTok 采集失败: {msg}"
        raise HTTPException(status_code=500, detail=msg) from exc
    items = load_materials()
    return {
        "ok": True,
        "keywords": keywords,
        "limit_per_keyword": body.limit_per_keyword,
        "total_collected": result.total_collected,
        "total_cleaned": result.total_cleaned,
        "total_dropped": result.total_dropped,
        "imported_total": result.imported_total,
        "skipped_other_category": result.skipped_other_category,
        "imported_new_links": result.imported_new_links,
        "updated_existing_links": result.updated_existing_links,
        "json_path": result.json_path,
        "csv_path": result.csv_path,
        "clean_json_path": result.clean_json_path,
        "clean_csv_path": result.clean_csv_path,
        "review_json_path": result.review_json_path,
        "output_dir": result.output_dir,
        "materials_total": len(items),
        "materials_analyzed": sum(1 for item in items if item.get("has_analysis")),
    }


@app.get("/api/tiktok-collector/db/videos")
async def tiktok_collector_db_videos(
    q: str = "",
    source_keyword: str = "",
    processing_status: str = "",
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    try:
        result = await run_in_threadpool(
            query_collector_database,
            q=q,
            source_keyword=source_keyword,
            processing_status=processing_status,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TikTok MySQL 查询失败: {exc}") from exc
    return {
        "ok": True,
        "db_enabled": result.db_enabled,
        "total": result.total,
        "items": result.items,
        "filters": {
            "q": q,
            "source_keyword": source_keyword,
            "processing_status": processing_status,
            "limit": limit,
        },
    }


@app.post("/api/tiktok-collector/db/sync")
async def tiktok_collector_db_sync(body: TikTokCollectorDbSyncRequest) -> dict:
    try:
        result = await run_in_threadpool(
            sync_collector_database_to_workflow,
            q=body.q,
            source_keyword=body.source_keyword,
            processing_status=body.processing_status,
            limit=body.limit,
            product_id=body.product_id or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TikTok MySQL 同步失败: {exc}") from exc
    return {
        "ok": True,
        "db_enabled": result.db_enabled,
        "queried_total": result.queried_total,
        "synced_count": result.synced_count,
        "imported_new_links": result.imported_new_links,
        "updated_existing_links": result.updated_existing_links,
    }


@app.post("/api/delivery/{slug}/finish")
async def delivery_finish(slug: str) -> dict:
    try:
        link_id = int(slug.replace("ref-", ""))
        await run_in_threadpool(ensure_delivery_project, link_id)
        return await run_in_threadpool(finish_project, slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"交付失败: {exc}") from exc


@app.get("/api/doubao/test")
async def doubao_test() -> dict:
    video = await test_doubao_connection()
    script = await test_script_connection()
    return {"video_analysis": video, "script_generation": script}


@app.get("/api/script-llm/test")
async def script_llm_test() -> dict:
    return await test_script_connection()


@app.get("/api/seedance/test")
async def seedance_test() -> dict:
    try:
        return test_connection()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/delivery/{slug}/seedance")
async def delivery_seedance(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return project_status(slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/video-queue")
async def video_queue_status(ticket: str = "") -> dict:
    if ticket:
        row = ticket_status(ticket)
        if not row:
            raise HTTPException(status_code=404, detail="排队号不存在")
        return row
    return queue_snapshot()


@app.post("/api/video-queue/join")
async def video_queue_join(body: VideoQueueJoinRequest) -> dict:
    try:
        return join_queue(slug=body.slug, label=body.label, client_id=body.client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/video-queue/{ticket_id}")
async def video_queue_cancel(ticket_id: str, client_id: str = "") -> dict:
    try:
        return cancel_ticket(ticket_id, client_id=client_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/video-queue/{ticket_id}/complete")
async def video_queue_complete(ticket_id: str, body: VideoQueueCompleteRequest) -> dict:
    complete_ticket(ticket_id, ok=body.ok, message=body.message)
    return queue_snapshot()


@app.post("/api/delivery/{slug}/seedance/run")
async def delivery_seedance_run(
    slug: str,
    force: bool = Query(False),
    ticket: str = Query(""),
    body: SeedanceRunRequest = Body(default_factory=SeedanceRunRequest),
) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        assert_video_quota()
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    ticket_id = (ticket or "").strip()
    if not ticket_id:
        raise HTTPException(status_code=400, detail="缺少排队号，请从工作台重新点击「确认生成视频」")
    try:
        await run_in_threadpool(assert_can_run, ticket_id, slug)
        await run_in_threadpool(mark_running, ticket_id, slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        video_settings = await run_in_threadpool(sync_project_video_settings, slug, body.model_dump())
        staged = await run_in_threadpool(refresh_project_seedance_source, slug)
        if not staged or not staged.get("product_ref"):
            raise HTTPException(
                status_code=409,
                detail="缺少白底主图垫图：请在 01_素材库/产品资料/便携恒温杯/listing-0602-nw/主图/ 放置 白底主图.png 后重试",
            )
        status = await run_in_threadpool(project_status, slug)
        if not status.get("shots"):
            raise HTTPException(status_code=409, detail="本项目无可生成的 AI 分镜")
        if hero_frame_gate_enabled():
            hf = await run_in_threadpool(hero_frames_status, slug)
            if not hf.get("confirmed"):
                raise HTTPException(
                    status_code=409,
                    detail="关键帧未确认：请先在预览区确认各镜构图后再生成动态视频",
                )
        payload = await run_in_threadpool(run_all, slug, force=force)
        if is_ticket_cancelled(ticket_id):
            complete_ticket(ticket_id, ok=False, message="用户已取消生成")
            raise HTTPException(status_code=409, detail="生成已取消")
        assemble = payload.get("assemble") if isinstance(payload.get("assemble"), dict) else {}
        seedance = payload.get("seedance") if isinstance(payload.get("seedance"), dict) else {}
        shots = seedance.get("shots") or []
        ready_shots = sum(1 for s in shots if s.get("ready"))
        final_ready = bool(
            assemble.get("ok")
            or (seedance.get("final_video") or {}).get("ready")
        )
        if not final_ready and ready_shots >= 1:
            await run_in_threadpool(lambda: ensure_ffmpeg_ready(raise_on_fail=False))
            retry_asm = await run_in_threadpool(assemble_project, slug)
            payload["assemble"] = retry_asm
            if retry_asm.get("ok"):
                seedance = await run_in_threadpool(project_status, slug)
                payload["seedance"] = seedance
        payload["video_production"] = video_settings
        assemble = payload.get("assemble") if isinstance(payload.get("assemble"), dict) else {}
        final_ready = bool(
            assemble.get("ok")
            or (payload.get("seedance") or {}).get("final_video", {}).get("ready")
        )
        if final_ready:
            payload["daily_video_quota"] = record_video_output(slug, note="seedance/run")
        else:
            payload["daily_video_quota"] = video_quota_status()
        payload["queue_ticket"] = ticket_id
        complete_ticket(ticket_id, ok=True)
        return payload
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "生成失败"
        complete_ticket(ticket_id, ok=False, message=str(detail))
        raise
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        complete_ticket(ticket_id, ok=False, message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        complete_ticket(ticket_id, ok=False, message=str(exc))
        raise HTTPException(status_code=500, detail=f"视频生成失败: {exc}") from exc


@app.post("/api/delivery/{slug}/assemble")
async def delivery_assemble(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        await run_in_threadpool(lambda: ensure_ffmpeg_ready(raise_on_fail=True))
        return await run_in_threadpool(assemble_project, slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/delivery/{slug}/hero-frames")
async def delivery_hero_frames(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return await run_in_threadpool(hero_frames_status, slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/delivery/{slug}/hero-frames/generate")
async def delivery_hero_frames_generate(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return await run_in_threadpool(generate_hero_frames, slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/delivery/{slug}/hero-frames/confirm")
async def delivery_hero_frames_confirm(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return await run_in_threadpool(confirm_hero_frames, slug)
    except RuntimeError as exc:
        msg = str(exc)
        if "关键帧" in msg or "缺少" in msg:
            raise HTTPException(status_code=409, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc


@app.post("/api/delivery/{slug}/hero-frames/{shot_number}/regenerate")
async def delivery_hero_frame_regenerate(slug: str, shot_number: int) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return await run_in_threadpool(regenerate_hero_frame, slug, shot_number)
    except RuntimeError as exc:
        msg = str(exc)
        if "不存在" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=500, detail=msg) from exc


@app.on_event("startup")
async def _warm_delivery_engine() -> None:
    try:
        await run_in_threadpool(ensure_ffmpeg_ready)
    except Exception as exc:
        print(f"[warn] 交付引擎 ffmpeg 预热失败: {exc}")


@app.get("/api/delivery/{slug}/files/{file_path:path}")
async def delivery_file(slug: str, file_path: str) -> FileResponse:
    if not file_path.startswith("broll/"):
        raise HTTPException(status_code=404, detail="文件不存在")
    path = OVERSEAS_RUNS_DIR / slug / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=path.name)


@app.get("/api/delivery/{slug}/zip")
async def delivery_zip(slug: str) -> StreamingResponse:
    try:
        data, filename = build_delivery_zip(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/archive/{slug}/versions")
async def archive_versions(slug: str) -> dict:
    versions = list_archive_versions(slug)
    if not versions:
        raise HTTPException(status_code=404, detail="尚无服务器归档，请先完成成片拼接")
    return {"slug": slug, "total": len(versions), "items": versions}


@app.get("/api/archive/{slug}/{version}/zip")
async def archive_zip(slug: str, version: str) -> StreamingResponse:
    try:
        data, filename = build_archive_zip(slug, version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/admin/backup")
async def admin_backup() -> dict:
    """内网：触发工作区备份到 06_备份库（或 WORKFLOW_BACKUP_DIR）。"""
    from backup_workspace import run_backup

    manifest = await run_in_threadpool(run_backup)
    ok = sum(1 for row in manifest.get("items", []) if row.get("ok"))
    return {"ok": ok > 0, "backed_up": ok, "destination": manifest.get("destination"), "items": manifest.get("items")}


def main() -> None:
    import uvicorn

    host = workbench_host()
    port = workbench_port()
    print(f"工作台启动 http://{host}:{port}  （UI v{UI_VERSION}）")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("内网模式：请确保防火墙放行上述端口；建议配置 WORKBENCH_API_TOKEN")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
