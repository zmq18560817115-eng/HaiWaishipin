from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


MVP_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_WORKFLOW_ROOT = MVP_ROOT.parent
_OVERSEAS_ENV_CANDIDATE = _DEFAULT_WORKFLOW_ROOT / "overseas-loc-mvp" / ".env"

load_dotenv(_OVERSEAS_ENV_CANDIDATE)
load_dotenv(MVP_ROOT / ".env")


def _resolve_workflow_root() -> Path:
    raw = os.getenv("WORKFLOW_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _DEFAULT_WORKFLOW_ROOT


WORKFLOW_ROOT = _resolve_workflow_root()

# ── 工作区目录（01 素材库 / 03 产出库 / 04 成稿 / 05 反馈）────────────────
MATERIAL_LIBRARY_DIR = WORKFLOW_ROOT / "01_素材库"
PRODUCTION_ARCHIVE_DIR = WORKFLOW_ROOT / "03_产出库"
FINISHED_LIBRARY_DIR = WORKFLOW_ROOT / "04_成稿库"
FEEDBACK_LIBRARY_DIR = WORKFLOW_ROOT / "05_反馈库"

DATA_DIR = MATERIAL_LIBRARY_DIR / "竞品对标" / "数据表"
DECOMPOSE_DIR = MATERIAL_LIBRARY_DIR / "竞品对标" / "AI拆解结果"
PRODUCT_MATERIALS_DIR = MATERIAL_LIBRARY_DIR / "产品资料"
GENERATED_SCRIPTS_DIR = MATERIAL_LIBRARY_DIR / "脚本快照"
CHARACTER_LIBRARY_DIR = MATERIAL_LIBRARY_DIR / "人像角色"
THUMBNAILS_DIR = MATERIAL_LIBRARY_DIR / "竞品对标" / "封面缓存"

SQL_DIR = MVP_ROOT / "sql"

RAW_LINKS_CSV = DATA_DIR / "raw_links.csv"
DISCOVERY_QUERIES_CSV = DATA_DIR / "discovery_queries.csv"
DISCOVERY_CANDIDATES_CSV = DATA_DIR / "discovery_candidates.csv"
VIDEOS_META_CSV = DATA_DIR / "videos_meta.csv"
VIDEO_ANALYSIS_CSV = DATA_DIR / "video_analysis.csv"
SCRIPT_TEMPLATES_CSV = DATA_DIR / "script_templates.csv"
PROMPT_LIBRARY_JSON = DATA_DIR / "prompt_library.json"
SCRIPT_TEMPLATES_DIR = MVP_ROOT / "script_templates"
PRODUCT_MATERIALS_CSV = DATA_DIR / "product_materials.csv"
WEB_DIR = MVP_ROOT / "web"
DS223_ROOT = Path(r"\\DS223\obsidian知识库")
DS223_PRODUCTS_ROOT = DS223_ROOT / "shared-knowledge" / "products"
KRO_SHAREABLE_DIR = Path.home() / "Downloads" / "knowledge-research-orchestrator-codex-shareable" / "knowledge-research-orchestrator"
KRO_CODEX_DIR = (
    Path.home()
    / ".codex"
    / "skills"
    / "knowledge-research-orchestrator"
)
KRO_CONFIG_PATH = MVP_ROOT / "config" / "knowledge-sources.json"
SCHEMA_SQL = SQL_DIR / "schema.sql"

OVERSEAS_MVP_DIR = WORKFLOW_ROOT / "overseas-loc-mvp"
OVERSEAS_RUNS_DIR = OVERSEAS_MVP_DIR / "runs"
OVERSEAS_ENV = OVERSEAS_MVP_DIR / ".env"


def load_windows_user_env() -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return
    keys = (
        "OVERSEAS_DB_URL",
        "OVERSEAS_DB_USERNAME",
        "OVERSEAS_DB_PASSWORD",
        "OVERSEAS_DB_HOST",
        "OVERSEAS_DB_PORT",
        "OVERSEAS_DB_NAME",
        "ANTHROPIC_API_KEY",
        "OVERSEAS_LOC_MODEL",
    )
    force_keys = {
        "OVERSEAS_DB_URL",
        "OVERSEAS_DB_USERNAME",
        "OVERSEAS_DB_PASSWORD",
        "OVERSEAS_DB_HOST",
        "OVERSEAS_DB_PORT",
        "OVERSEAS_DB_NAME",
    }
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as handle:
        for key in keys:
            if os.getenv(key) and key not in force_keys:
                continue
            try:
                value, _ = winreg.QueryValueEx(handle, key)
            except OSError:
                continue
            if value:
                os.environ[key] = str(value)


load_windows_user_env()
load_dotenv(OVERSEAS_ENV, override=True)
load_dotenv(MVP_ROOT / ".env", override=True)


def kro_script_path() -> Path:
    raw = os.getenv("KRO_SCRIPT_PATH", "").strip()
    if raw:
        configured = Path(raw)
        if configured.exists():
            return configured
    candidates = (
        KRO_CODEX_DIR / "scripts" / "search_local_knowledge.py",
        KRO_SHAREABLE_DIR / "scripts" / "search_local_knowledge.py",
    )
    return next((path for path in candidates if path.exists()), candidates[0])


def kro_config_path() -> Path:
    raw = os.getenv("KRO_CONFIG_PATH", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else MVP_ROOT / p
    return KRO_CONFIG_PATH


def knowledge_roots() -> list[Path]:
    roots: list[Path] = []
    env_root = os.getenv("KNOWLEDGE_RESEARCH_ROOT", "").strip()
    if env_root:
        roots.append(Path(env_root))
    if DS223_ROOT.exists() and DS223_ROOT not in roots:
        roots.append(DS223_ROOT)
    local = OVERSEAS_MVP_DIR / "knowledge"
    if local.exists():
        roots.append(local)
    return roots


def _parse_db_url(url: str) -> dict[str, str]:
    from urllib.parse import urlparse

    cleaned = url.strip()
    if cleaned.startswith("jdbc:"):
        cleaned = cleaned.removeprefix("jdbc:")
    parsed = urlparse(cleaned)
    database = parsed.path.lstrip("/").split("?")[0] if parsed.path else ""
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 3306),
        "database": database or "overseas_video_loc",
        "user": parsed.username or "",
        "password": parsed.password or "",
    }


def db_config() -> dict[str, str | int]:
    url = os.getenv("OVERSEAS_DB_URL", "").strip()
    parsed: dict[str, str] = _parse_db_url(url) if url else {}
    return {
        "host": os.getenv("OVERSEAS_DB_HOST", parsed.get("host") or "127.0.0.1"),
        "port": int(os.getenv("OVERSEAS_DB_PORT", parsed.get("port") or "3306")),
        "user": os.getenv("OVERSEAS_DB_USERNAME", parsed.get("user") or "overseas_app"),
        "password": os.getenv("OVERSEAS_DB_PASSWORD", parsed.get("password") or ""),
        "database": os.getenv("OVERSEAS_DB_NAME", parsed.get("database") or "overseas_video_loc"),
    }


# OVERSEAS_MVP_DIR defined above
