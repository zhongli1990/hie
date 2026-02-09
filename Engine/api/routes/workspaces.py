"""
Workspace API Routes

CRUD operations for workspaces (namespaces).
"""

from __future__ import annotations

from uuid import UUID

from aiohttp import web
import structlog

from Engine.api.models import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceListResponse,
)
from Engine.api.repositories import WorkspaceRepository

logger = structlog.get_logger(__name__)


def setup_workspace_routes(app: web.Application, db_pool) -> None:
    """Set up workspace routes."""
    repo = WorkspaceRepository(db_pool)
    
    async def list_workspaces(request: web.Request) -> web.Response:
        """List all workspaces."""
        tenant_id = request.query.get("tenant_id")
        if tenant_id:
            tenant_id = UUID(tenant_id)
        
        workspaces = await repo.list_all(tenant_id)
        
        response = WorkspaceListResponse(
            workspaces=[WorkspaceResponse(**w) for w in workspaces],
            total=len(workspaces)
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def create_workspace(request: web.Request) -> web.Response:
        """Create a new workspace."""
        try:
            data = await request.json()
            create_data = WorkspaceCreate.model_validate(data)
            
            # Check if name already exists
            existing = await repo.get_by_name(create_data.name)
            if existing:
                return web.json_response(
                    {"error": f"Workspace '{create_data.name}' already exists"},
                    status=409
                )
            
            # Get user ID from auth context if available
            user_id = request.get("user_id")
            tenant_id = request.get("tenant_id")
            
            workspace = await repo.create(
                name=create_data.name,
                display_name=create_data.display_name,
                description=create_data.description,
                tenant_id=tenant_id,
                created_by=user_id,
                settings=create_data.settings,
            )
            
            logger.info("workspace_created", name=create_data.name)
            
            response = WorkspaceResponse(**workspace)
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("create_workspace_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def get_workspace(request: web.Request) -> web.Response:
        """Get workspace by ID."""
        workspace_id = request.match_info["workspace_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)
        
        workspace = await repo.get_by_id(ws_uuid)
        if not workspace:
            return web.json_response(
                {"error": f"Workspace not found"},
                status=404
            )
        
        response = WorkspaceResponse(**workspace)
        return web.json_response(response.model_dump(mode='json'))
    
    async def update_workspace(request: web.Request) -> web.Response:
        """Update workspace."""
        workspace_id = request.match_info["workspace_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)
        
        try:
            data = await request.json()
            update_data = WorkspaceUpdate.model_validate(data)
            
            workspace = await repo.update(
                ws_uuid,
                display_name=update_data.display_name,
                description=update_data.description,
                settings=update_data.settings,
            )
            
            if not workspace:
                return web.json_response({"error": "Workspace not found"}, status=404)
            
            logger.info("workspace_updated", workspace_id=workspace_id)
            
            response = WorkspaceResponse(**workspace)
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("update_workspace_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_workspace(request: web.Request) -> web.Response:
        """Delete workspace."""
        workspace_id = request.match_info["workspace_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)
        
        # Check if workspace exists
        workspace = await repo.get_by_id(ws_uuid)
        if not workspace:
            return web.json_response({"error": "Workspace not found"}, status=404)
        
        # Prevent deleting default workspace
        if workspace['name'] == 'default':
            return web.json_response(
                {"error": "Cannot delete default workspace"},
                status=403
            )
        
        deleted = await repo.delete(ws_uuid)
        if not deleted:
            return web.json_response({"error": "Failed to delete workspace"}, status=500)
        
        logger.info("workspace_deleted", workspace_id=workspace_id)
        
        return web.json_response({"status": "deleted", "workspace_id": workspace_id})
    
    # Register routes
    app.router.add_get("/api/workspaces", list_workspaces)
    app.router.add_post("/api/workspaces", create_workspace)
    app.router.add_get("/api/workspaces/{workspace_id}", get_workspace)
    app.router.add_put("/api/workspaces/{workspace_id}", update_workspace)
    app.router.add_delete("/api/workspaces/{workspace_id}", delete_workspace)
