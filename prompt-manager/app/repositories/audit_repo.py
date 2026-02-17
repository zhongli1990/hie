"""
OpenLI HIE Prompt Manager - Audit Log Repository

DB access layer for NHS DCB0129/DCB0160 compliant audit logging.
Every AI agent tool call is recorded with who, what, when, result.
"""
import re
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditLog


# PII sanitisation patterns — strip before storing
_NHS_NUMBER_RE = re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b")
_UK_POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)


def sanitise_pii(text: Optional[str]) -> Optional[str]:
    """Remove NHS numbers and UK postcodes from text before audit storage."""
    if not text:
        return text
    text = _NHS_NUMBER_RE.sub("[NHS_NUMBER]", text)
    text = _UK_POSTCODE_RE.sub("[POSTCODE]", text)
    return text


class AuditRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        user_id: str,
        user_role: str,
        action: str,
        result_status: str,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        run_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        input_summary: Optional[str] = None,
        result_summary: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            run_id=run_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            input_summary=sanitise_pii(input_summary),
            result_status=result_status,
            result_summary=sanitise_pii(result_summary),
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def list_entries(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        result_status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        if tenant_id:
            tid = uuid.UUID(tenant_id)
            query = query.where(AuditLog.tenant_id == tid)
            count_query = count_query.where(AuditLog.tenant_id == tid)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
            count_query = count_query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if result_status:
            query = query.where(AuditLog.result_status == result_status)
            count_query = count_query.where(AuditLog.result_status == result_status)
        if from_date:
            query = query.where(AuditLog.created_at >= from_date)
            count_query = count_query.where(AuditLog.created_at >= from_date)
        if to_date:
            query = query.where(AuditLog.created_at <= to_date)
            count_query = count_query.where(AuditLog.created_at <= to_date)

        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
