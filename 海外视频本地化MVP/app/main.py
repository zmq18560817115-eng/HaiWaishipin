from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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
    load_materials,
    load_script_payload,
    material_detail,
)
from .jobs import job_status, start_job
from .library_api import list_feedback, list_finished, load_feedback, load_templates, save_feedback
from .llm_script import pick_template
from .olm_bridge import (
    build_delivery_zip,
    delivery_ready,
    ensure_delivery_project,
    finish_project,
    project_exists,
)
from .product_tags import normalize_selected_tags, product_delivery_tags
from .products import get_product, list_products, update_product
from .scene_script import scenario_conflict_note
from .script_gen import generate_script
from .seedance_bridge import project_status, run_all, seedance_config, test_connection

app = FastAPI(title="海外视频本地化工作台", version="1.0.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
UI_VERSION = 20


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
    publish_views: str = ""
    publish_engagement: str = ""
    publish_notes: str = ""


class JobStartRequest(BaseModel):
    engine: str = "auto"


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    items = load_materials()
    return {
        "ok": True,
        "ui_version": UI_VERSION,
        "workbench": True,
        "materials": len(items),
        "analyzed": sum(1 for i in items if i.get("has_analysis")),
        "products": len(list_products()),
        "finished": len(list_finished()),
        "job": job_status(),
        "llm": {
            "available": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
            "model": os.getenv("OVERSEAS_LOC_MODEL", "claude-sonnet-4-6"),
            "fallback": "rule_template（无 Key 时自动使用）",
        },
        "aigc_primary": "seedance-2.0",
        "seedance": seedance_config(),
    }


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


@app.get("/api/materials/{link_id}")
async def material(link_id: int) -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    return detail


@app.get("/api/materials/{link_id}/preview")
async def material_preview(link_id: int, product_id: str = "") -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    if not detail.get("analysis"):
        raise HTTPException(status_code=409, detail="该素材尚无 AI 拆解，请先在「设置」运行拆解")

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
        "selected_tags": selected,
        "scenario_conflict_note": scenario_conflict_note(scenario_tags),
        "can_finish": has_script,
        "script_pack": detail.get("script_pack"),
        "workflow_note": (
            "仅借鉴本条竞品的钩子/节奏/分镜结构；成片口播与画面统一露出我方品牌，不出现竞品名。"
        ),
        "seedance": project_status(slug) if project_exists(slug) else None,
    }


@app.post("/api/materials/{link_id}/generate")
async def generate(link_id: int, body: GenerateRequest) -> dict:
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
            },
        )
        slug = f"ref-{link_id:03d}"
        result["slug"] = slug
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成失败: {exc}") from exc


@app.get("/api/products")
async def products() -> dict:
    rows = list_products()
    return {"total": len(rows), "items": rows}


@app.get("/api/products/{product_id}")
async def product_one(product_id: str) -> dict:
    row = get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="产品不存在")
    return row


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
        return start_job(job_name, engine=(body.engine if body else "auto"))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/delivery/{slug}/finish")
async def delivery_finish(slug: str) -> dict:
    try:
        link_id = int(slug.replace("ref-", ""))
        ensure_delivery_project(link_id)
        return finish_project(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@app.post("/api/delivery/{slug}/seedance/run")
async def delivery_seedance_run(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        status = project_status(slug)
        if not status.get("shots"):
            raise HTTPException(status_code=409, detail="本项目无 AI_BROLL 镜头，无需 SeedDance")
        return run_all(slug)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8788, reload=False)


if __name__ == "__main__":
    main()
