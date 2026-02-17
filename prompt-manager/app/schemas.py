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


# ── Audit Log ─────────────────────────────────────────────────────────────

class AuditLogCreate(BaseModel):
    """Posted by agent-runner after every tool execution."""
    tenant_id: Optional[str] = None
    user_id: str
    user_role: str
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    action: str                                     # tool name
    target_type: Optional[str] = None               # workspace/project/item
    target_id: Optional[str] = None
    input_summary: Optional[str] = None             # PII-sanitised
    result_status: str = "success"                   # success/denied/error
    result_summary: Optional[str] = None            # PII-sanitised


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    user_id: str
    user_role: str
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    input_summary: Optional[str] = None
    result_status: str
    result_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    entries: list[AuditLogResponse]
    total: int


# ── Deployment Approvals ──────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    """Posted by agent-runner when a developer requests production deploy."""
    tenant_id: Optional[str] = None
    requested_by: str
    requested_role: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    environment: str = "production"
    config_snapshot: Optional[dict] = None


class ApprovalReview(BaseModel):
    """Posted by CSO/Admin to approve or reject."""
    review_notes: Optional[str] = None
    safety_report: Optional[dict] = None


class ApprovalResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    requested_by: str
    requested_role: str
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    environment: str
    status: str
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    safety_report: Optional[dict] = None
    config_snapshot: Optional[dict] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalListResponse(BaseModel):
    approvals: list[ApprovalResponse]
    total: int
