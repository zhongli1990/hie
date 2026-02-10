"""Create prompt_templates, skills, and template_usage_log tables

Revision ID: 001
Revises: None
Create Date: 2026-02-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'prompt_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('slug', sa.String(256), nullable=False, index=True),
        sa.Column('category', sa.String(64), nullable=False, server_default='general'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('template_body', sa.Text, nullable=False),
        sa.Column('variables', sa.JSON, nullable=True),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_latest', sa.Boolean, nullable=False, server_default='true', index=True),
        sa.Column('is_published', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('parent_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_prompt_templates_slug_version', 'prompt_templates', ['slug', 'version'])
    op.create_index('ix_prompt_templates_tenant_latest', 'prompt_templates', ['tenant_id', 'is_latest'])

    op.create_table(
        'skills',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('slug', sa.String(256), nullable=False, index=True),
        sa.Column('category', sa.String(64), nullable=False, server_default='general'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('scope', sa.String(32), nullable=False, server_default='platform'),
        sa.Column('skill_content', sa.Text, nullable=False),
        sa.Column('allowed_tools', sa.Text, nullable=True),
        sa.Column('is_user_invocable', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_latest', sa.Boolean, nullable=False, server_default='true', index=True),
        sa.Column('is_published', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('parent_id', UUID(as_uuid=True), nullable=True),
        sa.Column('source', sa.String(32), nullable=False, server_default='db'),
        sa.Column('file_path', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_skills_slug_version', 'skills', ['slug', 'version'])
    op.create_index('ix_skills_tenant_latest', 'skills', ['tenant_id', 'is_latest'])

    op.create_table(
        'template_usage_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('template_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('skill_id', UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('session_id', UUID(as_uuid=True), nullable=True),
        sa.Column('rendered_prompt', sa.Text, nullable=True),
        sa.Column('variables_used', sa.JSON, nullable=True),
        sa.Column('model_used', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('template_usage_log')
    op.drop_table('skills')
    op.drop_table('prompt_templates')
