"""User, Tenant, and Role models for authentication and RBAC."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Index, UniqueConstraint, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..persistence.postgresql import Base


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class UserStatus(str, Enum):
    """User status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    REJECTED = "rejected"


class Tenant(Base):
    """NHS Trust or organization tenant."""
    __tablename__ = "hie_tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TenantStatus.ACTIVE.value)
    settings: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Limits
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_productions: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    
    # Contact
    admin_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    support_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    roles: Mapped[list["Role"]] = relationship("Role", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tenant_status", "status"),
        Index("ix_tenant_code", "code"),
    )


class Role(Base):
    """Role for RBAC with permissions."""
    __tablename__ = "hie_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_tenants.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="roles")
    users: Mapped[list["User"]] = relationship("User", back_populates="role")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
        Index("ix_role_tenant", "tenant_id"),
        Index("ix_role_is_system", "is_system"),
    )


class User(Base):
    """User account for authentication and RBAC."""
    __tablename__ = "hie_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_tenants.id", ondelete="CASCADE"), nullable=True)
    
    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Profile
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Authentication
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status & Role
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.PENDING.value)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_roles.id"), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    approved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_users.id"), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    approver: Mapped[Optional["User"]] = relationship("User", remote_side=[id], foreign_keys=[approved_by])

    __table_args__ = (
        Index("ix_user_tenant", "tenant_id"),
        Index("ix_user_status", "status"),
        Index("ix_user_role", "role_id"),
    )


class PasswordHistory(Base):
    """Password history for preventing reuse."""
    __tablename__ = "hie_password_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_users.id", ondelete="CASCADE"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_password_history_user", "user_id"),
    )


class Session(Base):
    """User session for refresh token management."""
    __tablename__ = "hie_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_session_user", "user_id"),
        Index("ix_session_expires", "expires_at"),
    )


class AuditLog(Base):
    """Audit log for tracking user actions."""
    __tablename__ = "hie_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_tenants.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("hie_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_audit_tenant", "tenant_id"),
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_action", "action"),
    )
