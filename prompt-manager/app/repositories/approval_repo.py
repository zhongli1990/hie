"""
OpenLI HIE Prompt Manager - Deployment Approval Repository

DB access layer for the production deployment approval workflow.
Developers request → CSO/Admin reviews → approve/reject.
"""
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeploymentApproval


class ApprovalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        requested_by: str,
        requested_role: str,
        tenant_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        project_name: Optional[str] = None,
        environment: str = "production",
        config_snapshot: Optional[dict] = None,
    ) -> DeploymentApproval:
        approval = DeploymentApproval(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            requested_by=requested_by,
            requested_role=requested_role,
            workspace_id=workspace_id,
            project_id=project_id,
            project_name=project_name,
            environment=environment,
            status="pending",
            config_snapshot=config_snapshot,
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def get_by_id(self, approval_id: str) -> Optional[DeploymentApproval]:
        result = await self.db.execute(
            select(DeploymentApproval).where(
                DeploymentApproval.id == uuid.UUID(approval_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_approvals(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DeploymentApproval], int]:
        query = select(DeploymentApproval)
        count_query = select(func.count()).select_from(DeploymentApproval)

        if tenant_id:
            tid = uuid.UUID(tenant_id)
            query = query.where(DeploymentApproval.tenant_id == tid)
            count_query = count_query.where(DeploymentApproval.tenant_id == tid)
        if status:
            query = query.where(DeploymentApproval.status == status)
            count_query = count_query.where(DeploymentApproval.status == status)

        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(DeploymentApproval.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def approve(
        self,
        approval_id: str,
        reviewed_by: str,
        review_notes: Optional[str] = None,
        safety_report: Optional[dict] = None,
    ) -> Optional[DeploymentApproval]:
        approval = await self.get_by_id(approval_id)
        if not approval or approval.status != "pending":
            return None
        approval.status = "approved"
        approval.reviewed_by = reviewed_by
        approval.review_notes = review_notes
        approval.safety_report = safety_report
        approval.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def reject(
        self,
        approval_id: str,
        reviewed_by: str,
        review_notes: Optional[str] = None,
    ) -> Optional[DeploymentApproval]:
        approval = await self.get_by_id(approval_id)
        if not approval or approval.status != "pending":
            return None
        approval.status = "rejected"
        approval.reviewed_by = reviewed_by
        approval.review_notes = review_notes
        approval.reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval
