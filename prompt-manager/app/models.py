"""
OpenLI HIE Prompt Manager - Database Models

Tables:
- prompt_templates: Versioned prompt templates with RBAC
- skills: DB-backed skills with versioning
- template_usage_log: Usage tracking for analytics
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
