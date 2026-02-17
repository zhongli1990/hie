"""
OpenLI HIE Prompt Manager - Deployment Approvals Router

Human review gate for production deployments. Developers cannot deploy
to production directly — they must request approval from a Clinical
Safety Officer or Tenant Admin.

Endpoints:
- POST /approvals                — Create approval request (agent-runner)
- GET  /approvals                — List approvals with filters
- GET  /approvals/{id}           — Get approval detail
- POST /approvals/{id}/approve   — Approve deployment (CSO/Admin)
- POST /approvals/{id}/reject    — Reject deployment (CSO/Admin)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser, get_current_user
from ..database import get_db
from ..repositories.approval_repo import ApprovalRepository
from ..schemas import (
    ApprovalCreate, ApprovalReview, ApprovalResponse, ApprovalListResponse,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _to_response(approval) -> ApprovalResponse:
    return ApprovalResponse(
        id=str(approval.id),
        tenant_id=str(approval.tenant_id) if approval.tenant_id else None,
        requested_by=approval.requested_by,
        requested_role=approval.requested_role,
        workspace_id=approval.workspace_id,
        project_id=approval.project_id,
        project_name=approval.project_name,
        environment=approval.environment,
        status=approval.status,
        reviewed_by=approval.reviewed_by,
        review_notes=approval.review_notes,
        safety_report=approval.safety_report,
        config_snapshot=approval.config_snapshot,
        created_at=approval.created_at,
        reviewed_at=approval.reviewed_at,
    )


@router.post("", response_model=ApprovalResponse, status_code=201)
async def create_approval(
    req: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a deployment approval request. Called by agent-runner."""
    repo = ApprovalRepository(db)
    approval = await repo.create(
        requested_by=req.requested_by,
        requested_role=req.requested_role,
        tenant_id=req.tenant_id,
        workspace_id=req.workspace_id,
        project_id=req.project_id,
        project_name=req.project_name,
        environment=req.environment,
        config_snapshot=req.config_snapshot,
    )
    return _to_response(approval)


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List deployment approvals. Filtered by tenant for non-admin users."""
    repo = ApprovalRepository(db)
    effective_tenant = None
    if user.role not in ("admin", "platform_admin") and user.tenant_id:
        effective_tenant = user.tenant_id

    approvals, total = await repo.list_approvals(
        tenant_id=effective_tenant,
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    return ApprovalListResponse(
        approvals=[_to_response(a) for a in approvals],
        total=total,
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get approval detail including config snapshot."""
    repo = ApprovalRepository(db)
    approval = await repo.get_by_id(approval_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    return _to_response(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_deployment(
    approval_id: str,
    req: ApprovalReview,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending deployment. CSO or Admin only."""
    if user.role not in (
        "admin", "platform_admin", "tenant_admin", "clinical_safety_officer",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Clinical Safety Officers and Admins can approve deployments",
        )

    repo = ApprovalRepository(db)
    approval = await repo.approve(
        approval_id=approval_id,
        reviewed_by=user.user_id,
        review_notes=req.review_notes,
        safety_report=req.safety_report,
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or not in pending status",
        )
    return _to_response(approval)


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_deployment(
    approval_id: str,
    req: ApprovalReview,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending deployment. CSO or Admin only."""
    if user.role not in (
        "admin", "platform_admin", "tenant_admin", "clinical_safety_officer",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Clinical Safety Officers and Admins can reject deployments",
        )

    repo = ApprovalRepository(db)
    approval = await repo.reject(
        approval_id=approval_id,
        reviewed_by=user.user_id,
        review_notes=req.review_notes,
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or not in pending status",
        )
    return _to_response(approval)
