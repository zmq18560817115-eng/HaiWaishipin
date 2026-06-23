from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BriefRequest(BaseModel):
    material_id: str = Field(min_length=3, max_length=64)
    slug: str = Field(min_length=3, max_length=64)
    sku: str = "panda-bubu-pro"
    target_country: str = "US"
    language: str = "en"
    platform: list[str] = Field(default_factory=lambda: ["tiktok", "amazon"])
    theme: str
    master_video_id: str = "placeholder-master"
    owner: str = "content-ops"
    launch_date: str = "TBD"
    allowed_claims_en: list[str] = Field(min_length=1)
    forbidden_terms_extra: list[str] = Field(default_factory=list)
    export_plan_confirmed: bool = False
    overseas_product_page_available: bool = False
    allowed_claims_available: bool = True
    source_video_usage_rights_confirmed: bool = False

    @field_validator("slug", "material_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        import re

        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", normalized):
            raise ValueError("仅允许小写英文、数字和连字符")
        return normalized

    @field_validator("allowed_claims_en", "forbidden_terms_extra")
    @classmethod
    def clean_lines(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class Shot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    number: int = Field(ge=1, le=5)
    role: str
    timing: str
    visual: str
    copy_cn: str = Field(alias="copy")
    footage_type: Literal["LIVE_ACTION", "AI_BROLL"]
    notes: str = ""


class StoryboardRequest(BaseModel):
    slug: str
    shots: list[Shot]

    @field_validator("shots")
    @classmethod
    def exactly_five_shots(cls, value: list[Shot]) -> list[Shot]:
        if len(value) != 5 or sorted(shot.number for shot in value) != [1, 2, 3, 4, 5]:
            raise ValueError("分镜必须恰好包含 Shot 1–5")
        return sorted(value, key=lambda shot: shot.number)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=6, ge=1, le=10)


class LocalizeRequest(BaseModel):
    slug: str
    provider: Literal["demo_local"] = "demo_local"


class ManualLocalizeRequest(BaseModel):
    slug: str
    markdown: str = Field(min_length=50)


class SlugRequest(BaseModel):
    slug: str


class FeedbackUpdateRequest(BaseModel):
    manual_edits: str = ""
    adopted: str = "待定"
    notes: str = ""
    publish_views: str = ""
    publish_engagement: str = ""
    publish_notes: str = ""


class SeedanceRequest(BaseModel):
    slug: str
    shot_number: int = Field(ge=1, le=5)
    prompt: str = Field(min_length=10, max_length=2000)
    image_ref: str | None = None
    source_approved: bool = False
    mode: Literal["submit", "preview"] = "submit"
