"""
OpenLI HIE Prompt Manager - Audit Log Router

NHS DCB0129/DCB0160 compliant audit trail for all AI agent actions.

Endpoints:
- POST /audit       — Create audit entry (called by agent-runner)
- GET  /audit       — List audit entries with filters (admin/CSO)
- GET  /audit/stats — Aggregate audit statistics
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser, get_current_user
from ..database import get_db
from ..repositories.audit_repo import AuditRepository
from ..schemas import AuditLogCreate, AuditLogResponse, AuditLogListResponse

router = APIRouter(prefix="/audit", tags=["audit"])


def _to_response(entry) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(entry.id),
        tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
        user_id=entry.user_id,
        user_role=entry.user_role,
        session_id=entry.session_id,
        run_id=entry.run_id,
        action=entry.action,
        target_type=entry.target_type,
        target_id=entry.target_id,
        input_summary=entry.input_summary,
        result_status=entry.result_status,
        result_summary=entry.result_summary,
        created_at=entry.created_at,
    )


@router.post("", response_model=AuditLogResponse, status_code=201)
async def create_audit_entry(
    req: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an audit log entry. Called by agent-runner after tool execution."""
    repo = AuditRepository(db)
    entry = await repo.create(
        user_id=req.user_id,
        user_role=req.user_role,
        action=req.action,
        result_status=req.result_status,
        tenant_id=req.tenant_id,
        session_id=req.session_id,
        run_id=req.run_id,
        target_type=req.target_type,
        target_id=req.target_id,
        input_summary=req.input_summary,
        result_summary=req.result_summary,
    )
    return _to_response(entry)


@router.get("", response_model=AuditLogListResponse)
async def list_audit_entries(
    tenant_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    result_status: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries with filters. Admin and CSO access."""
    repo = AuditRepository(db)
    # Non-admin users can only see their own tenant's entries
    effective_tenant = tenant_id
    if user.role not in ("admin", "platform_admin") and user.tenant_id:
        effective_tenant = user.tenant_id

    entries, total = await repo.list_entries(
        tenant_id=effective_tenant,
        user_id=user_id,
        action=action,
        result_status=result_status,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )
    return AuditLogListResponse(
        entries=[_to_response(e) for e in entries],
        total=total,
    )


@router.get("/stats")
async def audit_stats(
    tenant_id: Optional[str] = Query(None),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate audit statistics."""
    repo = AuditRepository(db)
    effective_tenant = tenant_id
    if user.role not in ("admin", "platform_admin") and user.tenant_id:
        effective_tenant = user.tenant_id

    entries, total = await repo.list_entries(
        tenant_id=effective_tenant, limit=0,
    )
    # Get counts by status
    all_entries, total_count = await repo.list_entries(
        tenant_id=effective_tenant, limit=1000,
    )
    denied = sum(1 for e in all_entries if e.result_status == "denied")
    errors = sum(1 for e in all_entries if e.result_status == "error")
    success = sum(1 for e in all_entries if e.result_status == "success")

    return {
        "total": total_count,
        "success": success,
        "denied": denied,
        "errors": errors,
    }
