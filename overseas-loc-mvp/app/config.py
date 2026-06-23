from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def _split_paths(raw: str) -> list[Path]:
    return [Path(item.strip()) for item in raw.split(";") if item.strip()]


@dataclass(frozen=True)
class Settings:
    base_dir: Path = BASE_DIR
    runs_dir: Path = BASE_DIR / "runs"
    static_dir: Path = BASE_DIR / "static"
    prompts_dir: Path = BASE_DIR / "prompts"
    local_knowledge_dir: Path = BASE_DIR / "knowledge"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("OVERSEAS_LOC_MODEL", "claude-sonnet-4-6")
    max_tokens: int = int(os.getenv("OVERSEAS_LOC_MAX_TOKENS", "4096"))
    prompt_version: str = os.getenv("OVERSEAS_LOC_PROMPT_VERSION", "localize-v1.1")
    fal_key: str = os.getenv("FAL_KEY", "")
    seedance_image_model: str = os.getenv(
        "SEEDANCE_IMAGE_MODEL", "bytedance/seedance-2.0/image-to-video"
    )
    seedance_text_model: str = os.getenv(
        "SEEDANCE_TEXT_MODEL", "bytedance/seedance-2.0/text-to-video"
    )
    seedance_use_fast: bool = os.getenv("SEEDANCE_USE_FAST", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    knowledge_roots_raw: str = os.getenv("KNOWLEDGE_RESEARCH_ROOT", "")
    kro_config_path: str = os.getenv(
        "KRO_CONFIG_PATH", str(BASE_DIR / "config" / "knowledge-sources.json")
    )
    kro_script_path: str = os.getenv("KRO_SCRIPT_PATH", "")
    host: str = os.getenv("OVERSEAS_LOC_HOST", "127.0.0.1")
    port: int = int(os.getenv("OVERSEAS_LOC_PORT", "8787"))

    @property
    def seedance_text_model_resolved(self) -> str:
        if self.seedance_use_fast:
            return "bytedance/seedance-2.0/fast/text-to-video"
        return self.seedance_text_model

    @property
    def seedance_image_model_resolved(self) -> str:
        if self.seedance_use_fast:
            return "bytedance/seedance-2.0/fast/image-to-video"
        return self.seedance_image_model

    @property
    def knowledge_roots(self) -> list[Path]:
        roots = [self.local_knowledge_dir]
        roots.extend(_split_paths(self.knowledge_roots_raw))
        return roots

    @property
    def resolved_kro_script(self) -> Path:
        if self.kro_script_path:
            return Path(self.kro_script_path)
        return (
            Path.home()
            / ".codex"
            / "skills"
            / "knowledge-research-orchestrator"
            / "scripts"
            / "search_local_knowledge.py"
        )


settings = Settings()
settings.runs_dir.mkdir(parents=True, exist_ok=True)

