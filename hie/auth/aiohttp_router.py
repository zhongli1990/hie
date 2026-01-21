"""Authentication API endpoints for aiohttp server."""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from aiohttp import web
import structlog

from .models import User, Role, UserStatus
from .security import (
    get_password_hash, verify_password, create_access_token, 
    validate_password, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,
    LOCKOUT_ATTEMPTS, LOCKOUT_DURATION_MINUTES
)

logger = structlog.get_logger(__name__)


def setup_auth_routes(app: web.Application, db_pool) -> None:
    """Setup authentication routes on the aiohttp app."""
    
    # Store db_pool in app for access in handlers
    app["db_pool"] = db_pool
    
    # Auth routes
    app.router.add_post("/api/auth/register", register)
    app.router.add_post("/api/auth/login", login)
    app.router.add_get("/api/auth/me", get_me)
    app.router.add_post("/api/auth/logout", logout)
    app.router.add_post("/api/auth/change-password", change_password)
    
    # Admin routes
    app.router.add_get("/api/admin/users", list_users)
    app.router.add_get("/api/admin/users/pending", list_pending_users)
    app.router.add_get("/api/admin/users/{user_id}", get_user)
    app.router.add_post("/api/admin/users/{user_id}/approve", approve_user)
    app.router.add_post("/api/admin/users/{user_id}/reject", reject_user)
    app.router.add_post("/api/admin/users/{user_id}/activate", activate_user)
    app.router.add_post("/api/admin/users/{user_id}/deactivate", deactivate_user)
    app.router.add_post("/api/admin/users/{user_id}/unlock", unlock_user)
    app.router.add_get("/api/admin/roles", list_roles)


async def get_current_user_from_request(request: web.Request) -> Optional[dict]:
    """Extract and validate user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    return payload


async def require_auth(request: web.Request) -> dict:
    """Require authentication, raise 401 if not authenticated."""
    payload = await get_current_user_from_request(request)
    if payload is None:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Not authenticated"}),
            content_type="application/json"
        )
    return payload


async def require_permission(request: web.Request, permission: str) -> dict:
    """Require specific permission."""
    payload = await require_auth(request)
    permissions = payload.get("permissions", [])
    if permission not in permissions:
        raise web.HTTPForbidden(
            text=json.dumps({"detail": f"Permission denied: {permission}"}),
            content_type="application/json"
        )
    return payload


# Auth handlers

async def register(request: web.Request) -> web.Response:
    """Register a new user."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "Invalid JSON"}), content_type="application/json")
    
    email = data.get("email")
    password = data.get("password")
    display_name = data.get("display_name")
    
    if not email or not password or not display_name:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "email, password, and display_name are required"}),
            content_type="application/json"
        )
    
    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        raise web.HTTPBadRequest(text=json.dumps({"detail": error_msg}), content_type="application/json")
    
    pool = request.app.get("db_pool")
    if pool is None:
        raise web.HTTPInternalServerError(text=json.dumps({"detail": "Database not configured"}), content_type="application/json")
    
    async with pool.acquire() as conn:
        # Check if email exists
        existing = await conn.fetchrow("SELECT id FROM hie_users WHERE email = $1", email)
        if existing:
            raise web.HTTPBadRequest(text=json.dumps({"detail": "Email already registered"}), content_type="application/json")
        
        # Get default role (viewer)
        role = await conn.fetchrow("SELECT id, display_name FROM hie_roles WHERE name = 'viewer' AND tenant_id IS NULL")
        if role is None:
            raise web.HTTPInternalServerError(text=json.dumps({"detail": "Default role not configured"}), content_type="application/json")
        
        # Create user
        user = await conn.fetchrow("""
            INSERT INTO hie_users (email, display_name, mobile, title, department, password_hash, status, role_id, password_changed_at)
            VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7, NOW())
            RETURNING id, tenant_id, email, display_name, mobile, title, department, status, role_id, created_at, approved_at, last_login_at, mfa_enabled
        """, email, display_name, data.get("mobile"), data.get("title"), data.get("department"), 
            get_password_hash(password), role["id"])
        
        return web.json_response({
            "id": str(user["id"]),
            "tenant_id": str(user["tenant_id"]) if user["tenant_id"] else None,
            "email": user["email"],
            "display_name": user["display_name"],
            "mobile": user["mobile"],
            "title": user["title"],
            "department": user["department"],
            "status": user["status"],
            "role_id": str(user["role_id"]),
            "role_name": role["display_name"],
            "created_at": user["created_at"].isoformat(),
            "approved_at": user["approved_at"].isoformat() if user["approved_at"] else None,
            "last_login_at": user["last_login_at"].isoformat() if user["last_login_at"] else None,
            "mfa_enabled": user["mfa_enabled"],
        }, status=201)


async def login(request: web.Request) -> web.Response:
    """Login and get JWT token."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "Invalid JSON"}), content_type="application/json")
    
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "email and password are required"}), content_type="application/json")
    
    pool = request.app.get("db_pool")
    if pool is None:
        raise web.HTTPInternalServerError(text=json.dumps({"detail": "Database not configured"}), content_type="application/json")
    
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT u.*, r.name as role_name, r.display_name as role_display_name, r.permissions
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.email = $1
        """, email)
        
        if user is None:
            raise web.HTTPUnauthorized(text=json.dumps({"detail": "Invalid email or password"}), content_type="application/json")
        
        # Check if locked
        if user["locked_until"] and user["locked_until"] > datetime.now(timezone.utc):
            remaining = (user["locked_until"] - datetime.now(timezone.utc)).seconds // 60
            raise web.HTTPForbidden(text=json.dumps({"detail": f"Account is locked. Try again in {remaining} minutes."}), content_type="application/json")
        
        # Verify password
        if not verify_password(password, user["password_hash"]):
            # Increment failed attempts
            new_attempts = user["failed_login_attempts"] + 1
            if new_attempts >= LOCKOUT_ATTEMPTS:
                await conn.execute("""
                    UPDATE hie_users SET failed_login_attempts = $1, locked_until = NOW() + INTERVAL '%s minutes', status = 'locked'
                    WHERE id = $2
                """ % LOCKOUT_DURATION_MINUTES, new_attempts, user["id"])
                raise web.HTTPForbidden(text=json.dumps({"detail": f"Account locked due to too many failed attempts."}), content_type="application/json")
            else:
                await conn.execute("UPDATE hie_users SET failed_login_attempts = $1 WHERE id = $2", new_attempts, user["id"])
            raise web.HTTPUnauthorized(text=json.dumps({"detail": "Invalid email or password"}), content_type="application/json")
        
        # Check status
        if user["status"] == "pending":
            raise web.HTTPForbidden(text=json.dumps({"detail": "Account pending approval"}), content_type="application/json")
        elif user["status"] == "rejected":
            raise web.HTTPForbidden(text=json.dumps({"detail": "Account has been rejected"}), content_type="application/json")
        elif user["status"] == "inactive":
            raise web.HTTPForbidden(text=json.dumps({"detail": "Account is inactive"}), content_type="application/json")
        elif user["status"] == "locked":
            if user["locked_until"] and user["locked_until"] <= datetime.now(timezone.utc):
                await conn.execute("UPDATE hie_users SET status = 'active', locked_until = NULL, failed_login_attempts = 0 WHERE id = $1", user["id"])
            else:
                raise web.HTTPForbidden(text=json.dumps({"detail": "Account is locked"}), content_type="application/json")
        
        # Reset failed attempts and update last login
        await conn.execute("UPDATE hie_users SET failed_login_attempts = 0, locked_until = NULL, last_login_at = NOW() WHERE id = $1", user["id"])
        
        # Parse permissions from JSONB
        permissions = user["permissions"] if isinstance(user["permissions"], list) else json.loads(user["permissions"]) if user["permissions"] else []
        
        # Create token
        access_token = create_access_token({
            "sub": str(user["id"]),
            "email": user["email"],
            "tenant_id": str(user["tenant_id"]) if user["tenant_id"] else None,
            "role": user["role_name"],
            "permissions": permissions,
        })
        
        return web.json_response({
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user["id"]),
                "tenant_id": str(user["tenant_id"]) if user["tenant_id"] else None,
                "email": user["email"],
                "display_name": user["display_name"],
                "mobile": user["mobile"],
                "title": user["title"],
                "department": user["department"],
                "status": user["status"],
                "role_id": str(user["role_id"]),
                "role_name": user["role_display_name"],
                "created_at": user["created_at"].isoformat(),
                "approved_at": user["approved_at"].isoformat() if user["approved_at"] else None,
                "last_login_at": datetime.now(timezone.utc).isoformat(),
                "mfa_enabled": user["mfa_enabled"],
            }
        })


async def get_me(request: web.Request) -> web.Response:
    """Get current user info."""
    payload = await require_auth(request)
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.id = $1
        """, UUID(payload["sub"]))
        
        if user is None:
            raise web.HTTPUnauthorized(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        return web.json_response({
            "id": str(user["id"]),
            "tenant_id": str(user["tenant_id"]) if user["tenant_id"] else None,
            "email": user["email"],
            "display_name": user["display_name"],
            "mobile": user["mobile"],
            "title": user["title"],
            "department": user["department"],
            "avatar_url": user["avatar_url"],
            "status": user["status"],
            "role_id": str(user["role_id"]),
            "role_name": user["role_display_name"],
            "created_at": user["created_at"].isoformat(),
            "approved_at": user["approved_at"].isoformat() if user["approved_at"] else None,
            "last_login_at": user["last_login_at"].isoformat() if user["last_login_at"] else None,
            "mfa_enabled": user["mfa_enabled"],
        })


async def logout(request: web.Request) -> web.Response:
    """Logout (client-side token deletion)."""
    return web.json_response({"message": "Logged out successfully"})


async def change_password(request: web.Request) -> web.Response:
    """Change current user's password."""
    payload = await require_auth(request)
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "Invalid JSON"}), content_type="application/json")
    
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    
    if not current_password or not new_password:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "current_password and new_password are required"}), content_type="application/json")
    
    # Validate new password
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        raise web.HTTPBadRequest(text=json.dumps({"detail": error_msg}), content_type="application/json")
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT password_hash FROM hie_users WHERE id = $1", UUID(payload["sub"]))
        
        if not verify_password(current_password, user["password_hash"]):
            raise web.HTTPBadRequest(text=json.dumps({"detail": "Current password is incorrect"}), content_type="application/json")
        
        if verify_password(new_password, user["password_hash"]):
            raise web.HTTPBadRequest(text=json.dumps({"detail": "New password must be different"}), content_type="application/json")
        
        await conn.execute("""
            UPDATE hie_users SET password_hash = $1, password_changed_at = NOW(), must_change_password = FALSE
            WHERE id = $2
        """, get_password_hash(new_password), UUID(payload["sub"]))
        
        return web.json_response({"message": "Password changed successfully"})


# Admin handlers

async def list_users(request: web.Request) -> web.Response:
    """List all users."""
    payload = await require_permission(request, "users:read")
    
    status_filter = request.query.get("status")
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        query = """
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
        """
        params = []
        
        # Apply tenant filter for non-super-admins
        tenant_id = payload.get("tenant_id")
        if tenant_id:
            query += " WHERE u.tenant_id = $1"
            params.append(UUID(tenant_id))
            if status_filter:
                query += " AND u.status = $2"
                params.append(status_filter)
        elif status_filter:
            query += " WHERE u.status = $1"
            params.append(status_filter)
        
        query += " ORDER BY u.created_at DESC"
        
        users = await conn.fetch(query, *params)
        
        return web.json_response([{
            "id": str(u["id"]),
            "tenant_id": str(u["tenant_id"]) if u["tenant_id"] else None,
            "email": u["email"],
            "display_name": u["display_name"],
            "mobile": u["mobile"],
            "title": u["title"],
            "department": u["department"],
            "status": u["status"],
            "role_id": str(u["role_id"]),
            "role_name": u["role_display_name"],
            "created_at": u["created_at"].isoformat(),
            "approved_at": u["approved_at"].isoformat() if u["approved_at"] else None,
            "last_login_at": u["last_login_at"].isoformat() if u["last_login_at"] else None,
            "mfa_enabled": u["mfa_enabled"],
        } for u in users])


async def list_pending_users(request: web.Request) -> web.Response:
    """List pending users."""
    payload = await require_permission(request, "users:approve")
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        query = """
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.status = 'pending'
        """
        params = []
        
        tenant_id = payload.get("tenant_id")
        if tenant_id:
            query += " AND u.tenant_id = $1"
            params.append(UUID(tenant_id))
        
        query += " ORDER BY u.created_at ASC"
        
        users = await conn.fetch(query, *params)
        
        return web.json_response([{
            "id": str(u["id"]),
            "tenant_id": str(u["tenant_id"]) if u["tenant_id"] else None,
            "email": u["email"],
            "display_name": u["display_name"],
            "mobile": u["mobile"],
            "title": u["title"],
            "department": u["department"],
            "status": u["status"],
            "role_id": str(u["role_id"]),
            "role_name": u["role_display_name"],
            "created_at": u["created_at"].isoformat(),
            "approved_at": u["approved_at"].isoformat() if u["approved_at"] else None,
            "last_login_at": u["last_login_at"].isoformat() if u["last_login_at"] else None,
            "mfa_enabled": u["mfa_enabled"],
        } for u in users])


async def get_user(request: web.Request) -> web.Response:
    """Get user by ID."""
    payload = await require_permission(request, "users:read")
    user_id = request.match_info["user_id"]
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.id = $1
        """, UUID(user_id))
        
        if user is None:
            raise web.HTTPNotFound(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        return web.json_response({
            "id": str(user["id"]),
            "tenant_id": str(user["tenant_id"]) if user["tenant_id"] else None,
            "email": user["email"],
            "display_name": user["display_name"],
            "mobile": user["mobile"],
            "title": user["title"],
            "department": user["department"],
            "status": user["status"],
            "role_id": str(user["role_id"]),
            "role_name": user["role_display_name"],
            "created_at": user["created_at"].isoformat(),
            "approved_at": user["approved_at"].isoformat() if user["approved_at"] else None,
            "last_login_at": user["last_login_at"].isoformat() if user["last_login_at"] else None,
            "mfa_enabled": user["mfa_enabled"],
        })


async def approve_user(request: web.Request) -> web.Response:
    """Approve a pending user."""
    payload = await require_permission(request, "users:approve")
    user_id = request.match_info["user_id"]
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT status FROM hie_users WHERE id = $1", UUID(user_id))
        
        if user is None:
            raise web.HTTPNotFound(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        if user["status"] != "pending":
            raise web.HTTPBadRequest(text=json.dumps({"detail": f"User is not pending (current status: {user['status']})"}), content_type="application/json")
        
        await conn.execute("""
            UPDATE hie_users SET status = 'active', approved_at = NOW(), approved_by = $1
            WHERE id = $2
        """, UUID(payload["sub"]), UUID(user_id))
        
        updated = await conn.fetchrow("""
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.id = $1
        """, UUID(user_id))
        
        return web.json_response({
            "id": str(updated["id"]),
            "tenant_id": str(updated["tenant_id"]) if updated["tenant_id"] else None,
            "email": updated["email"],
            "display_name": updated["display_name"],
            "status": updated["status"],
            "role_id": str(updated["role_id"]),
            "role_name": updated["role_display_name"],
            "created_at": updated["created_at"].isoformat(),
            "approved_at": updated["approved_at"].isoformat() if updated["approved_at"] else None,
            "last_login_at": updated["last_login_at"].isoformat() if updated["last_login_at"] else None,
            "mfa_enabled": updated["mfa_enabled"],
        })


async def reject_user(request: web.Request) -> web.Response:
    """Reject a pending user."""
    payload = await require_permission(request, "users:approve")
    user_id = request.match_info["user_id"]
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT status FROM hie_users WHERE id = $1", UUID(user_id))
        
        if user is None:
            raise web.HTTPNotFound(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        if user["status"] != "pending":
            raise web.HTTPBadRequest(text=json.dumps({"detail": f"User is not pending"}), content_type="application/json")
        
        await conn.execute("UPDATE hie_users SET status = 'rejected' WHERE id = $1", UUID(user_id))
        
        updated = await conn.fetchrow("""
            SELECT u.*, r.display_name as role_display_name
            FROM hie_users u
            JOIN hie_roles r ON u.role_id = r.id
            WHERE u.id = $1
        """, UUID(user_id))
        
        return web.json_response({
            "id": str(updated["id"]),
            "email": updated["email"],
            "display_name": updated["display_name"],
            "status": updated["status"],
            "role_name": updated["role_display_name"],
        })


async def activate_user(request: web.Request) -> web.Response:
    """Activate a user."""
    payload = await require_permission(request, "users:update")
    user_id = request.match_info["user_id"]
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT status, approved_at FROM hie_users WHERE id = $1", UUID(user_id))
        
        if user is None:
            raise web.HTTPNotFound(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        if user["status"] == "active":
            raise web.HTTPBadRequest(text=json.dumps({"detail": "User is already active"}), content_type="application/json")
        
        if user["approved_at"]:
            await conn.execute("UPDATE hie_users SET status = 'active', locked_until = NULL, failed_login_attempts = 0 WHERE id = $1", UUID(user_id))
        else:
            await conn.execute("""
                UPDATE hie_users SET status = 'active', locked_until = NULL, failed_login_attempts = 0, approved_at = NOW(), approved_by = $1
                WHERE id = $2
            """, UUID(payload["sub"]), UUID(user_id))
        
        return web.json_response({"message": "User activated"})


async def deactivate_user(request: web.Request) -> web.Response:
    """Deactivate a user."""
    payload = await require_permission(request, "users:update")
    user_id = request.match_info["user_id"]
    
    if user_id == payload["sub"]:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "Cannot deactivate yourself"}), content_type="application/json")
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE hie_users SET status = 'inactive' WHERE id = $1", UUID(user_id))
        return web.json_response({"message": "User deactivated"})


async def unlock_user(request: web.Request) -> web.Response:
    """Unlock a locked user."""
    payload = await require_permission(request, "users:update")
    user_id = request.match_info["user_id"]
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT status FROM hie_users WHERE id = $1", UUID(user_id))
        
        if user is None:
            raise web.HTTPNotFound(text=json.dumps({"detail": "User not found"}), content_type="application/json")
        
        if user["status"] != "locked":
            raise web.HTTPBadRequest(text=json.dumps({"detail": "User is not locked"}), content_type="application/json")
        
        await conn.execute("UPDATE hie_users SET status = 'active', locked_until = NULL, failed_login_attempts = 0 WHERE id = $1", UUID(user_id))
        return web.json_response({"message": "User unlocked"})


async def list_roles(request: web.Request) -> web.Response:
    """List all roles."""
    payload = await require_permission(request, "users:read")
    
    pool = request.app.get("db_pool")
    async with pool.acquire() as conn:
        query = "SELECT * FROM hie_roles WHERE tenant_id IS NULL"
        params = []
        
        tenant_id = payload.get("tenant_id")
        if tenant_id:
            query = "SELECT * FROM hie_roles WHERE tenant_id IS NULL OR tenant_id = $1"
            params.append(UUID(tenant_id))
        
        query += " ORDER BY is_system DESC, name"
        
        roles = await conn.fetch(query, *params)
        
        return web.json_response([{
            "id": str(r["id"]),
            "tenant_id": str(r["tenant_id"]) if r["tenant_id"] else None,
            "name": r["name"],
            "display_name": r["display_name"],
            "description": r["description"],
            "is_system": r["is_system"],
            "permissions": r["permissions"] if isinstance(r["permissions"], list) else json.loads(r["permissions"]) if r["permissions"] else [],
            "created_at": r["created_at"].isoformat(),
            "updated_at": r["updated_at"].isoformat(),
        } for r in roles])
