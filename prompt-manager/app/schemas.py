"""
OpenLI HIE Prompt Manager - Pydantic Schemas
"""
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ── Templates ──────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=256)
    category: str = Field("general", max_length=64)
    description: Optional[str] = None
    template_body: str
    variables: Optional[dict] = None
    tags: Optional[list[str]] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    template_body: Optional[str] = None
    variables: Optional[dict] = None
    tags: Optional[list[str]] = None


class TemplateResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None
    name: str
    slug: str
    category: str
    description: Optional[str] = None
    template_body: str
    variables: Optional[dict] = None
    tags: Optional[list[str]] = None
    version: int
    is_latest: bool
    is_published: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int


class RenderTemplateRequest(BaseModel):
    variables: dict = Field(default_factory=dict)


class RenderTemplateResponse(BaseModel):
    rendered: str
    template_id: str
    template_name: str


# ── Skills ─────────────────────────────────────────────────────────────────

class SkillCreate(BaseModel):
    name: str = Field(..., max_length=256)
    category: str = Field("general", max_length=64)
    description: Optional[str] = None
    scope: str = Field("platform", max_length=32)
    skill_content: str
    allowed_tools: Optional[str] = None
    is_user_invocable: bool = True


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    skill_content: Optional[str] = None
    allowed_tools: Optional[str] = None
    is_user_invocable: Optional[bool] = None


class SkillResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None
    name: str
    slug: str
    category: str
    description: Optional[str] = None
    scope: str
    skill_content: str
    allowed_tools: Optional[str] = None
    is_user_invocable: bool
    version: int
    is_latest: bool
    is_published: bool
    is_enabled: bool
    source: str
    file_path: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    skills: list[SkillResponse]
    total: int


# ── Usage ──────────────────────────────────────────────────────────────────

class LogUsageRequest(BaseModel):
    template_id: Optional[str] = None
    skill_id: Optional[str] = None
    session_id: Optional[str] = None
    rendered_prompt: Optional[str] = None
    variables_used: Optional[dict] = None
    model_used: Optional[str] = None


class UsageStatsResponse(BaseModel):
    total_uses: int
    templates_used: int
    skills_used: int


# ── Categories ─────────────────────────────────────────────────────────────

class CategoryResponse(BaseModel):
    name: str
    template_count: int = 0
    skill_count: int = 0
