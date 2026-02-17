"""Add audit_log and deployment_approvals tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── audit_log ─────────────────────────────────────────────────────────
    op.create_table(
        'audit_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('user_id', sa.String(128), nullable=False, index=True),
        sa.Column('user_role', sa.String(32), nullable=False),
        sa.Column('session_id', sa.String(128), nullable=True, index=True),
        sa.Column('run_id', sa.String(128), nullable=True),
        sa.Column('action', sa.String(128), nullable=False, index=True),
        sa.Column('target_type', sa.String(64), nullable=True),
        sa.Column('target_id', sa.String(128), nullable=True),
        sa.Column('input_summary', sa.Text, nullable=True),
        sa.Column('result_status', sa.String(16), nullable=False, index=True),
        sa.Column('result_summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_audit_log_tenant_created', 'audit_log', ['tenant_id', 'created_at'],
    )
    op.create_index(
        'ix_audit_log_action_status', 'audit_log', ['action', 'result_status'],
    )

    # ── deployment_approvals ──────────────────────────────────────────────
    op.create_table(
        'deployment_approvals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('requested_by', sa.String(128), nullable=False, index=True),
        sa.Column('requested_role', sa.String(32), nullable=False),
        sa.Column('workspace_id', sa.String(128), nullable=True),
        sa.Column('project_id', sa.String(128), nullable=True),
        sa.Column('project_name', sa.String(256), nullable=True),
        sa.Column('environment', sa.String(32), nullable=False, server_default='production'),
        sa.Column('status', sa.String(16), nullable=False, server_default='pending', index=True),
        sa.Column('reviewed_by', sa.String(128), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('safety_report', sa.JSON, nullable=True),
        sa.Column('config_snapshot', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_deployment_approvals_tenant_status', 'deployment_approvals',
        ['tenant_id', 'status'],
    )


def downgrade() -> None:
    op.drop_table('deployment_approvals')
    op.drop_table('audit_log')
