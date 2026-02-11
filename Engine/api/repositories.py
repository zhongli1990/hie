"""
HIE API Repositories

Database access layer for workspaces, projects, items, and connections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


def _parse_jsonb_fields(row_dict: dict, fields: list[str]) -> dict:
    """Parse JSONB fields from string to dict if needed."""
    for field in fields:
        if field in row_dict and isinstance(row_dict[field], str):
            try:
                row_dict[field] = json.loads(row_dict[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return row_dict


class WorkspaceRepository:
    """Repository for workspace CRUD operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def list_all(self, tenant_id: Optional[UUID] = None) -> list[dict]:
        """List all workspaces, optionally filtered by tenant."""
        query = """
            SELECT w.*, 
                   (SELECT COUNT(*) FROM projects p WHERE p.workspace_id = w.id) as projects_count
            FROM workspaces w
            WHERE ($1::uuid IS NULL OR w.tenant_id = $1)
            ORDER BY w.display_name
        """
        rows = await self._pool.fetch(query, tenant_id)
        return [_parse_jsonb_fields(dict(r), ['settings']) for r in rows]
    
    async def get_by_id(self, workspace_id: UUID) -> Optional[dict]:
        """Get workspace by ID."""
        query = """
            SELECT w.*, 
                   (SELECT COUNT(*) FROM projects p WHERE p.workspace_id = w.id) as projects_count
            FROM workspaces w
            WHERE w.id = $1
        """
        row = await self._pool.fetchrow(query, workspace_id)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def get_by_name(self, name: str) -> Optional[dict]:
        """Get workspace by name."""
        query = """
            SELECT w.*, 
                   (SELECT COUNT(*) FROM projects p WHERE p.workspace_id = w.id) as projects_count
            FROM workspaces w
            WHERE w.name = $1
        """
        row = await self._pool.fetchrow(query, name)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def create(
        self,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        tenant_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
        settings: Optional[dict] = None,
    ) -> dict:
        """Create a new workspace."""
        query = """
            INSERT INTO workspaces (name, display_name, description, tenant_id, created_by, settings)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *, 0 as projects_count
        """
        row = await self._pool.fetchrow(
            query, name, display_name, description, tenant_id, created_by,
            json.dumps(settings or {})
        )
        return _parse_jsonb_fields(dict(row), ['settings'])
    
    async def update(self, workspace_id: UUID, **kwargs) -> Optional[dict]:
        """Update workspace fields."""
        if not kwargs:
            return await self.get_by_id(workspace_id)
        
        set_clauses = []
        values = [workspace_id]
        idx = 2
        
        for key, value in kwargs.items():
            if value is not None:
                if key == 'settings':
                    set_clauses.append(f"{key} = ${idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${idx}")
                    values.append(value)
                idx += 1
        
        if not set_clauses:
            return await self.get_by_id(workspace_id)
        
        query = f"""
            UPDATE workspaces
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *, (SELECT COUNT(*) FROM projects p WHERE p.workspace_id = workspaces.id) as projects_count
        """
        row = await self._pool.fetchrow(query, *values)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def delete(self, workspace_id: UUID) -> bool:
        """Delete workspace and all its projects."""
        query = "DELETE FROM workspaces WHERE id = $1"
        result = await self._pool.execute(query, workspace_id)
        return result == "DELETE 1"


class ProjectRepository:
    """Repository for project CRUD operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def list_by_workspace(self, workspace_id: UUID) -> list[dict]:
        """List all projects in a workspace."""
        query = """
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = p.id) as items_count,
                   (SELECT COUNT(*) FROM project_connections pc WHERE pc.project_id = p.id) as connections_count
            FROM projects p
            WHERE p.workspace_id = $1
            ORDER BY p.display_name
        """
        rows = await self._pool.fetch(query, workspace_id)
        return [_parse_jsonb_fields(dict(r), ['settings']) for r in rows]
    
    async def get_by_id(self, project_id: UUID) -> Optional[dict]:
        """Get project by ID."""
        query = """
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = p.id) as items_count,
                   (SELECT COUNT(*) FROM project_connections pc WHERE pc.project_id = p.id) as connections_count
            FROM projects p
            WHERE p.id = $1
        """
        row = await self._pool.fetchrow(query, project_id)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def get_by_name(self, workspace_id: UUID, name: str) -> Optional[dict]:
        """Get project by workspace and name."""
        query = """
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = p.id) as items_count,
                   (SELECT COUNT(*) FROM project_connections pc WHERE pc.project_id = p.id) as connections_count
            FROM projects p
            WHERE p.workspace_id = $1 AND p.name = $2
        """
        row = await self._pool.fetchrow(query, workspace_id, name)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def create(
        self,
        workspace_id: UUID,
        name: str,
        display_name: str,
        description: Optional[str] = None,
        enabled: bool = True,
        created_by: Optional[UUID] = None,
        settings: Optional[dict] = None,
    ) -> dict:
        """Create a new project."""
        query = """
            INSERT INTO projects (workspace_id, name, display_name, description, enabled, created_by, settings)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *, 0 as items_count, 0 as connections_count
        """
        row = await self._pool.fetchrow(
            query, workspace_id, name, display_name, description, enabled, created_by,
            json.dumps(settings or {})
        )
        return _parse_jsonb_fields(dict(row), ['settings'])
    
    async def update(self, project_id: UUID, **kwargs) -> Optional[dict]:
        """Update project fields."""
        if not kwargs:
            return await self.get_by_id(project_id)
        
        set_clauses = []
        values = [project_id]
        idx = 2
        
        for key, value in kwargs.items():
            if value is not None:
                if key == 'settings':
                    set_clauses.append(f"{key} = ${idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${idx}")
                    values.append(value)
                idx += 1
        
        if not set_clauses:
            return await self.get_by_id(project_id)
        
        query = f"""
            UPDATE projects
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *,
                (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = projects.id) as items_count,
                (SELECT COUNT(*) FROM project_connections pc WHERE pc.project_id = projects.id) as connections_count
        """
        row = await self._pool.fetchrow(query, *values)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def update_state(self, project_id: UUID, state: str) -> Optional[dict]:
        """Update project state."""
        return await self.update(project_id, state=state)
    
    async def increment_version(self, project_id: UUID) -> Optional[dict]:
        """Increment project version."""
        query = """
            UPDATE projects
            SET version = version + 1
            WHERE id = $1
            RETURNING *,
                (SELECT COUNT(*) FROM project_items pi WHERE pi.project_id = projects.id) as items_count,
                (SELECT COUNT(*) FROM project_connections pc WHERE pc.project_id = projects.id) as connections_count
        """
        row = await self._pool.fetchrow(query, project_id)
        return _parse_jsonb_fields(dict(row), ['settings']) if row else None
    
    async def delete(self, project_id: UUID) -> bool:
        """Delete project and all its items/connections."""
        query = "DELETE FROM projects WHERE id = $1"
        result = await self._pool.execute(query, project_id)
        return result == "DELETE 1"
    
    async def get_full_config(self, project_id: UUID) -> Optional[dict]:
        """Get project with all items, connections, and rules."""
        project = await self.get_by_id(project_id)
        if not project:
            return None
        
        items_query = "SELECT * FROM project_items WHERE project_id = $1 ORDER BY name"
        items = await self._pool.fetch(items_query, project_id)
        
        connections_query = "SELECT * FROM project_connections WHERE project_id = $1"
        connections = await self._pool.fetch(connections_query, project_id)
        
        rules_query = "SELECT * FROM project_routing_rules WHERE project_id = $1 ORDER BY priority"
        rules = await self._pool.fetch(rules_query, project_id)
        
        project['items'] = [_parse_jsonb_fields(dict(r), ['adapter_settings', 'host_settings']) for r in items]
        project['connections'] = [_parse_jsonb_fields(dict(r), ['settings']) for r in connections]
        project['routing_rules'] = [_parse_jsonb_fields(dict(r), ['target_items']) for r in rules]
        
        return project


class ItemRepository:
    """Repository for project item CRUD operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """List all items in a project."""
        query = """
            SELECT * FROM project_items
            WHERE project_id = $1
            ORDER BY name
        """
        rows = await self._pool.fetch(query, project_id)
        return [_parse_jsonb_fields(dict(r), ['adapter_settings', 'host_settings']) for r in rows]
    
    async def get_by_id(self, item_id: UUID) -> Optional[dict]:
        """Get item by ID."""
        query = "SELECT * FROM project_items WHERE id = $1"
        row = await self._pool.fetchrow(query, item_id)
        return _parse_jsonb_fields(dict(row), ['adapter_settings', 'host_settings']) if row else None
    
    async def get_by_name(self, project_id: UUID, name: str) -> Optional[dict]:
        """Get item by project and name."""
        query = "SELECT * FROM project_items WHERE project_id = $1 AND name = $2"
        row = await self._pool.fetchrow(query, project_id, name)
        return _parse_jsonb_fields(dict(row), ['adapter_settings', 'host_settings']) if row else None
    
    async def create(
        self,
        project_id: UUID,
        name: str,
        item_type: str,
        class_name: str,
        display_name: Optional[str] = None,
        category: Optional[str] = None,
        enabled: bool = True,
        pool_size: int = 1,
        position_x: int = 0,
        position_y: int = 0,
        adapter_settings: Optional[dict] = None,
        host_settings: Optional[dict] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """Create a new item."""
        query = """
            INSERT INTO project_items (
                project_id, name, display_name, item_type, class_name, category,
                enabled, pool_size, position_x, position_y,
                adapter_settings, host_settings, comment
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, project_id, name, display_name, item_type, class_name, category,
            enabled, pool_size, position_x, position_y,
            json.dumps(adapter_settings or {}),
            json.dumps(host_settings or {}),
            comment
        )
        return _parse_jsonb_fields(dict(row), ['adapter_settings', 'host_settings'])
    
    async def update(self, item_id: UUID, **kwargs) -> Optional[dict]:
        """Update item fields."""
        if not kwargs:
            return await self.get_by_id(item_id)
        
        set_clauses = []
        values = [item_id]
        idx = 2
        
        for key, value in kwargs.items():
            if value is not None:
                if key in ('adapter_settings', 'host_settings'):
                    set_clauses.append(f"{key} = ${idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${idx}")
                    values.append(value)
                idx += 1
        
        if not set_clauses:
            return await self.get_by_id(item_id)
        
        query = f"""
            UPDATE project_items
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """
        row = await self._pool.fetchrow(query, *values)
        return _parse_jsonb_fields(dict(row), ['adapter_settings', 'host_settings']) if row else None
    
    async def delete(self, item_id: UUID) -> bool:
        """Delete item."""
        query = "DELETE FROM project_items WHERE id = $1"
        result = await self._pool.execute(query, item_id)
        return result == "DELETE 1"
    
    async def bulk_create(self, project_id: UUID, items: list[dict]) -> list[dict]:
        """Create multiple items at once."""
        created = []
        for item in items:
            row = await self.create(
                project_id=project_id,
                name=item['name'],
                item_type=item['item_type'],
                class_name=item['class_name'],
                display_name=item.get('display_name'),
                category=item.get('category'),
                enabled=item.get('enabled', True),
                pool_size=item.get('pool_size', 1),
                position_x=item.get('position_x', 0),
                position_y=item.get('position_y', 0),
                adapter_settings=item.get('adapter_settings'),
                host_settings=item.get('host_settings'),
                comment=item.get('comment'),
            )
            created.append(row)
        return created


class ConnectionRepository:
    """Repository for project connection CRUD operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """List all connections in a project."""
        query = "SELECT * FROM project_connections WHERE project_id = $1"
        rows = await self._pool.fetch(query, project_id)
        return [dict(r) for r in rows]
    
    async def get_by_id(self, connection_id: UUID) -> Optional[dict]:
        """Get connection by ID."""
        query = "SELECT * FROM project_connections WHERE id = $1"
        row = await self._pool.fetchrow(query, connection_id)
        return dict(row) if row else None
    
    async def create(
        self,
        project_id: UUID,
        source_item_id: UUID,
        target_item_id: UUID,
        connection_type: str = "standard",
        enabled: bool = True,
        filter_expression: Optional[dict] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """Create a new connection."""
        query = """
            INSERT INTO project_connections (
                project_id, source_item_id, target_item_id,
                connection_type, enabled, filter_expression, comment
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, project_id, source_item_id, target_item_id,
            connection_type, enabled,
            json.dumps(filter_expression) if filter_expression else None,
            comment
        )
        return dict(row)
    
    async def update(self, connection_id: UUID, **kwargs) -> Optional[dict]:
        """Update connection fields."""
        if not kwargs:
            return await self.get_by_id(connection_id)
        
        set_clauses = []
        values = [connection_id]
        idx = 2
        
        for key, value in kwargs.items():
            if value is not None:
                if key == 'filter_expression':
                    set_clauses.append(f"{key} = ${idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${idx}")
                    values.append(value)
                idx += 1
        
        if not set_clauses:
            return await self.get_by_id(connection_id)
        
        query = f"""
            UPDATE project_connections
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """
        row = await self._pool.fetchrow(query, *values)
        return dict(row) if row else None
    
    async def delete(self, connection_id: UUID) -> bool:
        """Delete connection."""
        query = "DELETE FROM project_connections WHERE id = $1"
        result = await self._pool.execute(query, connection_id)
        return result == "DELETE 1"
    
    async def bulk_create(self, project_id: UUID, connections: list[dict]) -> list[dict]:
        """Create multiple connections at once."""
        created = []
        for conn in connections:
            row = await self.create(
                project_id=project_id,
                source_item_id=conn['source_item_id'],
                target_item_id=conn['target_item_id'],
                connection_type=conn.get('connection_type', 'standard'),
                enabled=conn.get('enabled', True),
                filter_expression=conn.get('filter_expression'),
                comment=conn.get('comment'),
            )
            created.append(row)
        return created


class RoutingRuleRepository:
    """Repository for routing rule CRUD operations."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def list_by_project(self, project_id: UUID) -> list[dict]:
        """List all routing rules in a project."""
        query = "SELECT * FROM project_routing_rules WHERE project_id = $1 ORDER BY priority"
        rows = await self._pool.fetch(query, project_id)
        return [_parse_jsonb_fields(dict(r), ['target_items']) for r in rows]
    
    async def get_by_id(self, rule_id: UUID) -> Optional[dict]:
        """Get routing rule by ID."""
        query = "SELECT * FROM project_routing_rules WHERE id = $1"
        row = await self._pool.fetchrow(query, rule_id)
        return _parse_jsonb_fields(dict(row), ['target_items']) if row else None
    
    async def create(
        self,
        project_id: UUID,
        name: str,
        action: str,
        enabled: bool = True,
        priority: int = 0,
        condition_expression: Optional[str] = None,
        target_items: Optional[list] = None,
        transform_name: Optional[str] = None,
    ) -> dict:
        """Create a new routing rule."""
        query = """
            INSERT INTO project_routing_rules (
                project_id, name, enabled, priority,
                condition_expression, action, target_items, transform_name
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, project_id, name, enabled, priority,
            condition_expression, action,
            json.dumps(target_items or []),
            transform_name
        )
        return _parse_jsonb_fields(dict(row), ['target_items'])
    
    async def update(self, rule_id: UUID, **kwargs) -> Optional[dict]:
        """Update routing rule fields."""
        if not kwargs:
            return await self.get_by_id(rule_id)
        
        set_clauses = []
        values = [rule_id]
        idx = 2
        
        for key, value in kwargs.items():
            if value is not None:
                if key == 'target_items':
                    set_clauses.append(f"{key} = ${idx}::jsonb")
                    values.append(json.dumps(value))
                else:
                    set_clauses.append(f"{key} = ${idx}")
                    values.append(value)
                idx += 1
        
        if not set_clauses:
            return await self.get_by_id(rule_id)
        
        query = f"""
            UPDATE project_routing_rules
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING *
        """
        row = await self._pool.fetchrow(query, *values)
        return _parse_jsonb_fields(dict(row), ['target_items']) if row else None
    
    async def delete(self, rule_id: UUID) -> bool:
        """Delete routing rule."""
        query = "DELETE FROM project_routing_rules WHERE id = $1"
        result = await self._pool.execute(query, rule_id)
        return result == "DELETE 1"


class PortalMessageRepository:
    """Repository for portal message tracking (Messages tab viewer)."""
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def create(
        self,
        project_id: UUID,
        item_name: str,
        item_type: str,
        direction: str,
        raw_content: bytes | None = None,
        message_type: str | None = None,
        correlation_id: str | None = None,
        status: str = "received",
        source_item: str | None = None,
        destination_item: str | None = None,
        remote_host: str | None = None,
        remote_port: int | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Create a new portal message record."""
        content_preview = None
        content_size = 0
        if raw_content:
            content_size = len(raw_content)
            # Create preview (first 500 chars, replace control chars)
            try:
                preview = raw_content.decode('utf-8', errors='replace')[:500]
                content_preview = preview.replace('\r', '\\r').replace('\n', '\\n')
            except:
                content_preview = f"[Binary data: {content_size} bytes]"
        
        query = """
            INSERT INTO portal_messages (
                project_id, item_name, item_type, direction, message_type,
                correlation_id, status, raw_content, content_preview, content_size,
                source_item, destination_item, remote_host, remote_port, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, project_id, item_name, item_type, direction, message_type,
            correlation_id, status, raw_content, content_preview, content_size,
            source_item, destination_item, remote_host, remote_port,
            json.dumps(metadata or {})
        )
        return dict(row) if row else {}
    
    async def update_status(
        self,
        message_id: UUID,
        status: str,
        ack_content: bytes | None = None,
        ack_type: str | None = None,
        error_message: str | None = None,
        latency_ms: int | None = None,
    ) -> Optional[dict]:
        """Update message status after processing."""
        completed_at = None
        if status in ('sent', 'completed', 'failed', 'error'):
            completed_at = datetime.now(timezone.utc)
        
        query = """
            UPDATE portal_messages
            SET status = $2, ack_content = $3, ack_type = $4, 
                error_message = $5, latency_ms = $6, completed_at = $7
            WHERE id = $1
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, message_id, status, ack_content, ack_type,
            error_message, latency_ms, completed_at
        )
        return dict(row) if row else None
    
    async def get_by_id(self, message_id: UUID) -> Optional[dict]:
        """Get message by ID."""
        query = "SELECT * FROM portal_messages WHERE id = $1"
        row = await self._pool.fetchrow(query, message_id)
        return dict(row) if row else None
    
    async def list_by_project(
        self,
        project_id: UUID,
        item_name: str | None = None,
        status: str | None = None,
        message_type: str | None = None,
        direction: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List messages for a project with filters."""
        conditions = ["project_id = $1"]
        params = [project_id]
        idx = 2
        
        if item_name:
            conditions.append(f"item_name = ${idx}")
            params.append(item_name)
            idx += 1
        
        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        
        if message_type:
            conditions.append(f"message_type ILIKE ${idx}")
            params.append(f"%{message_type}%")
            idx += 1
        
        if direction:
            conditions.append(f"direction = ${idx}")
            params.append(direction)
            idx += 1
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM portal_messages WHERE {where_clause}"
        total = await self._pool.fetchval(count_query, *params)
        
        # Get paginated results
        query = f"""
            SELECT id, project_id, item_name, item_type, direction, message_type,
                   correlation_id, status, content_preview, content_size,
                   source_item, destination_item, remote_host, remote_port,
                   ack_type, error_message, latency_ms, retry_count,
                   received_at, completed_at
            FROM portal_messages
            WHERE {where_clause}
            ORDER BY received_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([limit, offset])
        rows = await self._pool.fetch(query, *params)
        
        return [dict(r) for r in rows], total or 0
    
    async def get_content(self, message_id: UUID) -> Optional[dict]:
        """Get full message content including raw bytes."""
        query = """
            SELECT id, raw_content, ack_content, content_size
            FROM portal_messages WHERE id = $1
        """
        row = await self._pool.fetchrow(query, message_id)
        return dict(row) if row else None
    
    async def delete_old_messages(self, days: int = 30) -> int:
        """Delete messages older than specified days (housekeeping)."""
        query = """
            DELETE FROM portal_messages
            WHERE received_at < NOW() - INTERVAL '%s days'
        """ % days
        result = await self._pool.execute(query)
        return int(result.split()[1]) if result else 0
    
    async def get_stats(self, project_id: UUID) -> dict:
        """Get message statistics for a project."""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed' OR status = 'sent') as successful,
                COUNT(*) FILTER (WHERE status = 'failed' OR status = 'error') as failed,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE direction = 'inbound') as inbound,
                COUNT(*) FILTER (WHERE direction = 'outbound') as outbound,
                AVG(latency_ms) FILTER (WHERE latency_ms IS NOT NULL) as avg_latency_ms
            FROM portal_messages
            WHERE project_id = $1
        """
        row = await self._pool.fetchrow(query, project_id)
        return dict(row) if row else {}


class GenAISessionRepository:
    """Repository for GenAI session and message operations."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def list_sessions(self, workspace_id: UUID) -> list[dict]:
        """List all sessions for a workspace."""
        query = """
            SELECT s.*,
                   (SELECT COUNT(*) FROM genai_messages m WHERE m.session_id = s.session_id) as run_count
            FROM genai_sessions s
            WHERE s.workspace_id = $1
            ORDER BY s.created_at DESC
        """
        rows = await self._pool.fetch(query, workspace_id)
        return [dict(r) for r in rows]

    async def get_session(self, session_id: UUID) -> Optional[dict]:
        """Get session by ID."""
        query = """
            SELECT s.*,
                   (SELECT COUNT(*) FROM genai_messages m WHERE m.session_id = s.session_id) as run_count
            FROM genai_sessions s
            WHERE s.session_id = $1
        """
        row = await self._pool.fetchrow(query, session_id)
        return dict(row) if row else None

    async def create_session(
        self,
        workspace_id: UUID,
        project_id: Optional[UUID],
        runner_type: str,
        title: str,
    ) -> dict:
        """Create a new GenAI session."""
        query = """
            INSERT INTO genai_sessions (workspace_id, project_id, runner_type, title)
            VALUES ($1, $2, $3, $4)
            RETURNING *, 0 as run_count
        """
        row = await self._pool.fetchrow(query, workspace_id, project_id, runner_type, title)
        return dict(row)

    async def update_session_title(self, session_id: UUID, title: str) -> None:
        """Update session title."""
        query = """
            UPDATE genai_sessions
            SET title = $1, updated_at = NOW()
            WHERE session_id = $2
        """
        await self._pool.execute(query, title, session_id)

    async def list_messages(self, session_id: UUID) -> list[dict]:
        """List all messages in a session."""
        query = """
            SELECT *
            FROM genai_messages
            WHERE session_id = $1
            ORDER BY created_at ASC
        """
        rows = await self._pool.fetch(query, session_id)
        return [_parse_jsonb_fields(dict(r), ['metadata']) for r in rows]

    async def create_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        run_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a new message in a session."""
        query = """
            INSERT INTO genai_messages (session_id, role, content, run_id, metadata)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """
        row = await self._pool.fetchrow(
            query, session_id, role, content, run_id,
            json.dumps(metadata) if metadata else None
        )
        return _parse_jsonb_fields(dict(row), ['metadata'])
