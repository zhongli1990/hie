"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Role, UserStatus
from .security import decode_access_token
from .permissions import has_permission

security = HTTPBearer(auto_error=False)


async def get_db():
    """Get database session - to be overridden by application."""
    raise NotImplementedError("Database session provider not configured")


def set_db_provider(provider):
    """Set the database session provider."""
    global get_db
    get_db = provider


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id = payload.get("sub")
    if user_id is None:
        return None
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return None
    
    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if user is None or user.status != UserStatus.ACTIVE.value:
        return None
    
    # Store user in request state for later use
    request.state.user = user
    
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user. Raises 401 if not authenticated."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.status == UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval",
        )
    elif user.status == UserStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been rejected",
        )
    elif user.status == UserStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    elif user.status == UserStatus.LOCKED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked",
        )
    
    # Store user in request state
    request.state.user = user
    
    return user


async def get_user_with_role(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, Role]:
    """Get current user with their role loaded."""
    result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = result.scalar_one_or_none()
    
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User role not found",
        )
    
    return user, role


def require_permission(permission: str):
    """Dependency factory to require a specific permission."""
    async def check_permission(
        user_role: tuple[User, Role] = Depends(get_user_with_role)
    ) -> User:
        user, role = user_role
        if not has_permission(role.permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user
    return check_permission


def require_any_permission(*permissions: str):
    """Dependency factory to require any of the specified permissions."""
    async def check_permissions(
        user_role: tuple[User, Role] = Depends(get_user_with_role)
    ) -> User:
        user, role = user_role
        if not any(has_permission(role.permissions, p) for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {permissions}",
            )
        return user
    return check_permissions


async def require_super_admin(
    user_role: tuple[User, Role] = Depends(get_user_with_role)
) -> User:
    """Require super admin role (no tenant_id)."""
    user, role = user_role
    if user.tenant_id is not None or role.name != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return user


async def require_tenant_admin(
    user_role: tuple[User, Role] = Depends(get_user_with_role)
) -> User:
    """Require tenant admin or super admin role."""
    user, role = user_role
    if role.name not in ("super_admin", "tenant_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def get_tenant_filter(user: User) -> Optional[UUID]:
    """Get tenant filter for queries. Returns None for super admins (no filter)."""
    if user.tenant_id is None:
        # Super admin - no tenant filter
        return None
    return user.tenant_id
