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
        
        project['items'] = [dict(r) for r in items]
        project['connections'] = [dict(r) for r in connections]
        project['routing_rules'] = [dict(r) for r in rules]
        
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
        return [dict(r) for r in rows]
    
    async def get_by_id(self, rule_id: UUID) -> Optional[dict]:
        """Get routing rule by ID."""
        query = "SELECT * FROM project_routing_rules WHERE id = $1"
        row = await self._pool.fetchrow(query, rule_id)
        return dict(row) if row else None
    
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
        return dict(row)
    
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
        return dict(row) if row else None
    
    async def delete(self, rule_id: UUID) -> bool:
        """Delete routing rule."""
        query = "DELETE FROM project_routing_rules WHERE id = $1"
        result = await self._pool.execute(query, rule_id)
        return result == "DELETE 1"
