"""Authentication API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Role, UserStatus
from .schemas import (
    RegisterRequest, LoginRequest, LoginResponse, 
    ChangePasswordRequest, UserResponse
)
from .security import (
    get_password_hash, verify_password, create_access_token, 
    validate_password, ACCESS_TOKEN_EXPIRE_MINUTES,
    LOCKOUT_ATTEMPTS, LOCKOUT_DURATION_MINUTES
)
from .dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user. User will be in 'pending' status until admin approval."""
    # Validate password
    is_valid, error_msg = validate_password(request.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Get default role (viewer for self-registration)
    result = await db.execute(
        select(Role).where(Role.name == "viewer", Role.tenant_id.is_(None))
    )
    default_role = result.scalar_one_or_none()
    
    if default_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role not configured"
        )
    
    # Create user with pending status
    user = User(
        email=request.email,
        display_name=request.display_name,
        mobile=request.mobile,
        title=request.title,
        department=request.department,
        password_hash=get_password_hash(request.password),
        status=UserStatus.PENDING.value,
        role_id=default_role.id,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
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
        role_name=default_role.display_name,
        created_at=user.created_at,
        approved_at=user.approved_at,
        last_login_at=user.last_login_at,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Returns JWT token."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked. Try again in {remaining} minutes."
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        
        # Lock account if too many failures
        if user.failed_login_attempts >= LOCKOUT_ATTEMPTS:
            from datetime import timedelta
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            user.status = UserStatus.LOCKED.value
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked due to too many failed attempts. Try again in {LOCKOUT_DURATION_MINUTES} minutes."
            )
        
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check user status
    if user.status == UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval"
        )
    elif user.status == UserStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been rejected"
        )
    elif user.status == UserStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    elif user.status == UserStatus.LOCKED.value:
        # Clear lock if it has expired
        if user.locked_until and user.locked_until <= datetime.now(timezone.utc):
            user.status = UserStatus.ACTIVE.value
            user.locked_until = None
            user.failed_login_attempts = 0
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked"
            )
    
    # Get user's role
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    
    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "role": role.name if role else "viewer",
            "permissions": role.permissions if role else [],
        }
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
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
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user info."""
    # Get role name
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    
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


@router.post("/logout")
async def logout():
    """Logout (client-side token deletion)."""
    return {"message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change current user's password."""
    # Verify current password
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, error_msg = validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Check password is different
    if verify_password(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.must_change_password = False
    await db.commit()
    
    return {"message": "Password changed successfully"}
