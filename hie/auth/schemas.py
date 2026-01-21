"""Pydantic schemas for authentication and user management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Auth Schemas
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=255)
    mobile: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    """Reset password with token."""
    token: str
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    display_name: str
    mobile: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


class UserCreate(UserBase):
    """Create user request (admin)."""
    password: Optional[str] = None  # If None, generate temp password
    role_id: UUID
    status: str = "active"  # Admin can create active users directly
    send_welcome_email: bool = True
    must_change_password: bool = True


class UserUpdate(BaseModel):
    """Update user request."""
    display_name: Optional[str] = None
    mobile: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None


class UserAdminUpdate(UserUpdate):
    """Admin update user request."""
    email: Optional[EmailStr] = None
    role_id: Optional[UUID] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    """User response (public fields)."""
    id: UUID
    tenant_id: Optional[UUID] = None
    email: str
    display_name: str
    mobile: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str
    role_id: UUID
    role_name: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    mfa_enabled: bool = False

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response for admin."""
    username: Optional[str] = None
    approved_by: Optional[UUID] = None
    updated_at: datetime
    password_changed_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    must_change_password: bool = False


# ============================================================================
# Role Schemas
# ============================================================================

class RoleBase(BaseModel):
    """Base role fields."""
    name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    permissions: list[str] = []


class RoleCreate(RoleBase):
    """Create role request."""
    pass


class RoleUpdate(BaseModel):
    """Update role request."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None


class RoleResponse(BaseModel):
    """Role response."""
    id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: bool
    permissions: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Tenant Schemas
# ============================================================================

class TenantBase(BaseModel):
    """Base tenant fields."""
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    admin_email: Optional[str] = None
    support_email: Optional[str] = None
    max_users: int = 100
    max_productions: int = 50


class TenantCreate(TenantBase):
    """Create tenant request."""
    settings: Optional[dict] = None


class TenantUpdate(BaseModel):
    """Update tenant request."""
    name: Optional[str] = None
    admin_email: Optional[str] = None
    support_email: Optional[str] = None
    max_users: Optional[int] = None
    max_productions: Optional[int] = None
    settings: Optional[dict] = None


class TenantResponse(BaseModel):
    """Tenant response."""
    id: UUID
    name: str
    code: str
    status: str
    admin_email: Optional[str] = None
    support_email: Optional[str] = None
    max_users: int
    max_productions: int
    settings: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogResponse(BaseModel):
    """Audit log entry response."""
    id: int
    tenant_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Update forward references
LoginResponse.model_rebuild()
