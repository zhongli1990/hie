"""
OpenLI HIE Prompt Manager - JWT Authentication

Shares JWT_SECRET_KEY with the HIE Engine backend for unified auth.
"""
import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "hie-dev-secret-change-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, tenant_id: Optional[str] = None, role: str = "user"):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


# Default dev user for when no auth header is provided
DEV_USER = CurrentUser(
    user_id="00000000-0000-0000-0000-000000000001",
    tenant_id="00000000-0000-0000-0000-000000000001",
    role="admin"
)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """Extract user from JWT token, or return dev user if no token."""
    if credentials is None:
        return DEV_USER

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: no user_id")

        return CurrentUser(
            user_id=str(user_id),
            tenant_id=str(payload.get("tenant_id", "")) or None,
            role=payload.get("role", "user"),
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
