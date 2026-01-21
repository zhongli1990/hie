"""Admin API endpoints for user and tenant management."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Role, Tenant, UserStatus, TenantStatus
from .schemas import (
    UserResponse, UserDetailResponse, UserCreate, UserAdminUpdate,
    RoleResponse, RoleCreate, RoleUpdate,
    TenantResponse, TenantCreate, TenantUpdate,
)
from .security import get_password_hash, validate_password
from .dependencies import (
    get_db, get_current_user, get_user_with_role, get_tenant_filter,
    require_permission, require_super_admin, require_tenant_admin
)
from .permissions import Permissions

router = APIRouter(prefix="/api/admin", tags=["admin"])


def generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================================
# User Management Endpoints
# ============================================================================

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    status_filter: Optional[str] = Query(None, alias="status"),
    role_filter: Optional[UUID] = Query(None, alias="role"),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    user: User = Depends(require_permission(Permissions.USERS_READ.code)),
    db: AsyncSession = Depends(get_db)
):
    """List users, optionally filtered by status, role, or search term."""
    query = select(User).order_by(User.created_at.desc())
    
    # Apply tenant filter for non-super-admins
    tenant_id = get_tenant_filter(user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    if status_filter:
        query = query.where(User.status == status_filter)
    
    if role_filter:
        query = query.where(User.role_id == role_filter)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_term)) |
            (User.display_name.ilike(search_term))
        )
    
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get role names
    role_ids = list(set(u.role_id for u in users))
    if role_ids:
        roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        roles = {r.id: r for r in roles_result.scalars().all()}
    else:
        roles = {}
    
    return [
        UserResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            email=u.email,
            display_name=u.display_name,
            mobile=u.mobile,
            title=u.title,
            department=u.department,
            avatar_url=u.avatar_url,
            status=u.status,
            role_id=u.role_id,
            role_name=roles.get(u.role_id, Role()).display_name if u.role_id in roles else None,
            created_at=u.created_at,
            approved_at=u.approved_at,
            last_login_at=u.last_login_at,
            mfa_enabled=u.mfa_enabled,
        )
        for u in users
    ]


@router.get("/users/pending", response_model=list[UserResponse])
async def list_pending_users(
    user: User = Depends(require_permission(Permissions.USERS_APPROVE.code)),
    db: AsyncSession = Depends(get_db)
):
    """List users pending approval."""
    query = select(User).where(User.status == UserStatus.PENDING.value).order_by(User.created_at.asc())
    
    # Apply tenant filter
    tenant_id = get_tenant_filter(user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get role names
    role_ids = list(set(u.role_id for u in users))
    if role_ids:
        roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        roles = {r.id: r for r in roles_result.scalars().all()}
    else:
        roles = {}
    
    return [
        UserResponse(
            id=u.id,
            tenant_id=u.tenant_id,
            email=u.email,
            display_name=u.display_name,
            mobile=u.mobile,
            title=u.title,
            department=u.department,
            status=u.status,
            role_id=u.role_id,
            role_name=roles.get(u.role_id, Role()).display_name if u.role_id in roles else None,
            created_at=u.created_at,
            approved_at=u.approved_at,
            last_login_at=u.last_login_at,
            mfa_enabled=u.mfa_enabled,
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_READ.code)),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user by ID."""
    query = select(User).where(User.id == user_id)
    
    # Apply tenant filter
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get role
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserDetailResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        avatar_url=user.avatar_url,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
        approved_at=user.approved_at,
        approved_by=user.approved_by,
        last_login_at=user.last_login_at,
        password_changed_at=user.password_changed_at,
        failed_login_attempts=user.failed_login_attempts,
        locked_until=user.locked_until,
        must_change_password=user.must_change_password,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    current_user: User = Depends(require_permission(Permissions.USERS_CREATE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (admin action)."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role exists
    role_result = await db.execute(select(Role).where(Role.id == request.role_id))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role ID"
        )
    
    # Generate or validate password
    if request.password:
        is_valid, error_msg = validate_password(request.password)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
        password = request.password
    else:
        password = generate_temp_password()
    
    # Determine tenant
    tenant_id = get_tenant_filter(current_user)
    
    # Create user
    user = User(
        tenant_id=tenant_id,
        email=request.email,
        display_name=request.display_name,
        mobile=request.mobile,
        title=request.title,
        department=request.department,
        password_hash=get_password_hash(password),
        status=request.status,
        role_id=request.role_id,
        must_change_password=request.must_change_password,
        approved_at=datetime.now(timezone.utc) if request.status == UserStatus.ACTIVE.value else None,
        approved_by=current_user.id if request.status == UserStatus.ACTIVE.value else None,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # TODO: Send welcome email if request.send_welcome_email
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserAdminUpdate,
    current_user: User = Depends(require_permission(Permissions.USERS_UPDATE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Update a user."""
    query = select(User).where(User.id == user_id)
    
    # Apply tenant filter
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update fields
    if request.email is not None:
        # Check uniqueness
        existing = await db.execute(select(User).where(User.email == request.email, User.id != user_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        user.email = request.email
    
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.mobile is not None:
        user.mobile = request.mobile
    if request.title is not None:
        user.title = request.title
    if request.department is not None:
        user.department = request.department
    if request.avatar_url is not None:
        user.avatar_url = request.avatar_url
    if request.role_id is not None:
        user.role_id = request.role_id
    if request.status is not None:
        user.status = request.status
    
    await db.commit()
    await db.refresh(user)
    
    # Get role name
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        avatar_url=user.avatar_url,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_DELETE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    query = select(User).where(User.id == user_id)
    
    # Apply tenant filter
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/approve", response_model=UserResponse)
async def approve_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_APPROVE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Approve a pending user registration."""
    query = select(User).where(User.id == user_id)
    
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.status != UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending (current status: {user.status})"
        )
    
    user.status = UserStatus.ACTIVE.value
    user.approved_at = datetime.now(timezone.utc)
    user.approved_by = current_user.id
    await db.commit()
    await db.refresh(user)
    
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/users/{user_id}/reject", response_model=UserResponse)
async def reject_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_APPROVE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Reject a pending user registration."""
    query = select(User).where(User.id == user_id)
    
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.status != UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not pending (current status: {user.status})"
        )
    
    user.status = UserStatus.REJECTED.value
    await db.commit()
    await db.refresh(user)
    
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_UPDATE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Activate an inactive, locked, or rejected user."""
    query = select(User).where(User.id == user_id)
    
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.status == UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active"
        )
    
    user.status = UserStatus.ACTIVE.value
    user.locked_until = None
    user.failed_login_attempts = 0
    if user.approved_at is None:
        user.approved_at = datetime.now(timezone.utc)
        user.approved_by = current_user.id
    await db.commit()
    await db.refresh(user)
    
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_UPDATE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate an active user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    query = select(User).where(User.id == user_id)
    
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user.status = UserStatus.INACTIVE.value
    await db.commit()
    await db.refresh(user)
    
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/users/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permissions.USERS_UPDATE.code)),
    db: AsyncSession = Depends(get_db)
):
    """Unlock a locked user account."""
    query = select(User).where(User.id == user_id)
    
    tenant_id = get_tenant_filter(current_user)
    if tenant_id:
        query = query.where(User.tenant_id == tenant_id)
    
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user.status != UserStatus.LOCKED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not locked"
        )
    
    user.status = UserStatus.ACTIVE.value
    user.locked_until = None
    user.failed_login_attempts = 0
    await db.commit()
    await db.refresh(user)
    
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()
    
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        display_name=user.display_name,
        mobile=user.mobile,
        title=user.title,
        department=user.department,
        status=user.status,
        role_id=user.role_id,
        role_name=role.display_name if role else None,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


# ============================================================================
# Role Management Endpoints
# ============================================================================

@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    user: User = Depends(require_permission(Permissions.USERS_READ.code)),
    db: AsyncSession = Depends(get_db)
):
    """List all available roles."""
    query = select(Role).order_by(Role.is_system.desc(), Role.name)
    
    # Include system roles (tenant_id is None) and tenant-specific roles
    tenant_id = get_tenant_filter(user)
    if tenant_id:
        query = query.where((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
    
    result = await db.execute(query)
    roles = result.scalars().all()
    
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    user: User = Depends(require_permission(Permissions.USERS_READ.code)),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific role by ID."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    
    return RoleResponse.model_validate(role)


# ============================================================================
# Tenant Management Endpoints (Super Admin Only)
# ============================================================================

@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all tenants (super admin only)."""
    query = select(Tenant).order_by(Tenant.name)
    
    if status_filter:
        query = query.where(Tenant.status == status_filter)
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific tenant by ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    return TenantResponse.model_validate(tenant)


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreate,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant."""
    # Check code uniqueness
    result = await db.execute(select(Tenant).where(Tenant.code == request.code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant code already exists"
        )
    
    tenant = Tenant(
        name=request.name,
        code=request.code,
        admin_email=request.admin_email,
        support_email=request.support_email,
        max_users=request.max_users,
        max_productions=request.max_productions,
        settings=request.settings or {},
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdate,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    if request.name is not None:
        tenant.name = request.name
    if request.admin_email is not None:
        tenant.admin_email = request.admin_email
    if request.support_email is not None:
        tenant.support_email = request.support_email
    if request.max_users is not None:
        tenant.max_users = request.max_users
    if request.max_productions is not None:
        tenant.max_productions = request.max_productions
    if request.settings is not None:
        tenant.settings = request.settings
    
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: UUID,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Suspend a tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    tenant.status = TenantStatus.SUSPENDED.value
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: UUID,
    user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """Activate a suspended tenant."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    tenant.status = TenantStatus.ACTIVE.value
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)
