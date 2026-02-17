"""
OpenLI HIE Prompt Manager - Database Models

Tables:
- prompt_templates: Versioned prompt templates with RBAC
- skills: DB-backed skills with versioning
- template_usage_log: Usage tracking for analytics
- audit_log: Every AI agent tool call recorded for NHS compliance
- deployment_approvals: Human review gate for production deployments
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String(256), nullable=False)
    slug = Column(String(256), nullable=False, index=True)
    category = Column(String(64), nullable=False, default="general", index=True)
    description = Column(Text, nullable=True)
    template_body = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True, index=True)
    is_published = Column(Boolean, nullable=False, default=False)
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_prompt_templates_slug_version", "slug", "version"),
        Index("ix_prompt_templates_tenant_latest", "tenant_id", "is_latest"),
    )


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String(256), nullable=False)
    slug = Column(String(256), nullable=False, index=True)
    category = Column(String(64), nullable=False, default="general", index=True)
    description = Column(Text, nullable=True)
    scope = Column(String(32), nullable=False, default="platform")
    skill_content = Column(Text, nullable=False)
    allowed_tools = Column(Text, nullable=True)
    is_user_invocable = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True, index=True)
    is_published = Column(Boolean, nullable=False, default=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    source = Column(String(32), nullable=False, default="db")
    file_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_skills_slug_version", "slug", "version"),
        Index("ix_skills_tenant_latest", "tenant_id", "is_latest"),
    )


class TemplateUsageLog(Base):
    __tablename__ = "template_usage_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    template_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    skill_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    rendered_prompt = Column(Text, nullable=True)
    variables_used = Column(JSON, nullable=True)
    model_used = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    """Every AI agent tool call — who, what, when, result.

    NHS DCB0129/DCB0160 compliance: all AI-driven actions must be auditable.
    Input/output fields are PII-sanitised before storage.
    """
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    user_role = Column(String(32), nullable=False)
    session_id = Column(String(128), nullable=True, index=True)
    run_id = Column(String(128), nullable=True)
    action = Column(String(128), nullable=False, index=True)        # tool name
    target_type = Column(String(64), nullable=True)                 # workspace/project/item
    target_id = Column(String(128), nullable=True)
    input_summary = Column(Text, nullable=True)                     # sanitised (no PII)
    result_status = Column(String(16), nullable=False, index=True)  # success/denied/error
    result_summary = Column(Text, nullable=True)                    # sanitised
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_log_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_log_action_status", "action", "result_status"),
    )


class DeploymentApproval(Base):
    """Human review gate for production deployments.

    When a developer requests production deploy, a record is created here.
    A Clinical Safety Officer or Tenant Admin must approve before the
    deployment executes.
    """
    __tablename__ = "deployment_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    requested_by = Column(String(128), nullable=False, index=True)
    requested_role = Column(String(32), nullable=False)
    workspace_id = Column(String(128), nullable=True)
    project_id = Column(String(128), nullable=True)
    project_name = Column(String(256), nullable=True)
    environment = Column(String(32), nullable=False, default="production")
    status = Column(String(16), nullable=False, default="pending", index=True)
    reviewed_by = Column(String(128), nullable=True)
    review_notes = Column(Text, nullable=True)
    safety_report = Column(JSON, nullable=True)
    config_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_deployment_approvals_tenant_status", "tenant_id", "status"),
    )
