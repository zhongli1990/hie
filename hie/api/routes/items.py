"""
Item API Routes

CRUD operations for project items (services, processes, operations).
"""

from __future__ import annotations

from uuid import UUID

from aiohttp import web
import structlog

from hie.api.models import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse,
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionResponse,
    ConnectionListResponse,
    RoutingRuleCreate,
    RoutingRuleUpdate,
    RoutingRuleResponse,
)
from hie.api.repositories import (
    ProjectRepository,
    ItemRepository,
    ConnectionRepository,
    RoutingRuleRepository,
)

logger = structlog.get_logger(__name__)


def setup_item_routes(app: web.Application, db_pool) -> None:
    """Set up item, connection, and routing rule routes."""
    project_repo = ProjectRepository(db_pool)
    item_repo = ItemRepository(db_pool)
    connection_repo = ConnectionRepository(db_pool)
    rule_repo = RoutingRuleRepository(db_pool)
    
    # ==================== Item Routes ====================
    
    async def list_items(request: web.Request) -> web.Response:
        """List all items in a project."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        # Verify project exists
        project = await project_repo.get_by_id(proj_uuid)
        if not project:
            return web.json_response({"error": "Project not found"}, status=404)
        
        items = await item_repo.list_by_project(proj_uuid)
        
        response = ItemListResponse(
            items=[ItemResponse(**i) for i in items],
            total=len(items)
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def create_item(request: web.Request) -> web.Response:
        """Create a new item."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        # Verify project exists
        project = await project_repo.get_by_id(proj_uuid)
        if not project:
            return web.json_response({"error": "Project not found"}, status=404)
        
        try:
            data = await request.json()
            create_data = ItemCreate.model_validate(data)
            
            # Check if name already exists in project
            existing = await item_repo.get_by_name(proj_uuid, create_data.name)
            if existing:
                return web.json_response(
                    {"error": f"Item '{create_data.name}' already exists in this project"},
                    status=409
                )
            
            item = await item_repo.create(
                project_id=proj_uuid,
                name=create_data.name,
                display_name=create_data.display_name,
                item_type=create_data.item_type.value,
                class_name=create_data.class_name,
                category=create_data.category,
                enabled=create_data.enabled,
                pool_size=create_data.pool_size,
                position_x=create_data.position.x if create_data.position else 0,
                position_y=create_data.position.y if create_data.position else 0,
                adapter_settings=create_data.adapter_settings,
                host_settings=create_data.host_settings,
                comment=create_data.comment,
            )
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("item_created", name=create_data.name, project_id=project_id)
            
            response = ItemResponse(**item)
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("create_item_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def get_item(request: web.Request) -> web.Response:
        """Get item by ID."""
        project_id = request.match_info["project_id"]
        item_id = request.match_info["item_id"]
        
        try:
            proj_uuid = UUID(project_id)
            item_uuid = UUID(item_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        item = await item_repo.get_by_id(item_uuid)
        if not item:
            return web.json_response({"error": "Item not found"}, status=404)
        
        # Verify item belongs to project
        if item['project_id'] != proj_uuid:
            return web.json_response({"error": "Item not found in project"}, status=404)
        
        response = ItemResponse(**item)
        return web.json_response(response.model_dump(mode='json'))
    
    async def update_item(request: web.Request) -> web.Response:
        """Update item."""
        project_id = request.match_info["project_id"]
        item_id = request.match_info["item_id"]
        
        try:
            proj_uuid = UUID(project_id)
            item_uuid = UUID(item_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        try:
            data = await request.json()
            update_data = ItemUpdate.model_validate(data)
            
            # Build update kwargs
            update_kwargs = {}
            if update_data.display_name is not None:
                update_kwargs['display_name'] = update_data.display_name
            if update_data.category is not None:
                update_kwargs['category'] = update_data.category
            if update_data.enabled is not None:
                update_kwargs['enabled'] = update_data.enabled
            if update_data.pool_size is not None:
                update_kwargs['pool_size'] = update_data.pool_size
            if update_data.position is not None:
                update_kwargs['position_x'] = update_data.position.x
                update_kwargs['position_y'] = update_data.position.y
            if update_data.adapter_settings is not None:
                update_kwargs['adapter_settings'] = update_data.adapter_settings
            if update_data.host_settings is not None:
                update_kwargs['host_settings'] = update_data.host_settings
            if update_data.comment is not None:
                update_kwargs['comment'] = update_data.comment
            
            item = await item_repo.update(item_uuid, **update_kwargs)
            
            if not item:
                return web.json_response({"error": "Item not found"}, status=404)
            
            # Verify item belongs to project
            if item['project_id'] != proj_uuid:
                return web.json_response({"error": "Item not found in project"}, status=404)
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("item_updated", item_id=item_id)
            
            response = ItemResponse(**item)
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("update_item_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_item(request: web.Request) -> web.Response:
        """Delete item."""
        project_id = request.match_info["project_id"]
        item_id = request.match_info["item_id"]
        
        try:
            proj_uuid = UUID(project_id)
            item_uuid = UUID(item_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        # Check if item exists and belongs to project
        item = await item_repo.get_by_id(item_uuid)
        if not item:
            return web.json_response({"error": "Item not found"}, status=404)
        if item['project_id'] != proj_uuid:
            return web.json_response({"error": "Item not found in project"}, status=404)
        
        deleted = await item_repo.delete(item_uuid)
        if not deleted:
            return web.json_response({"error": "Failed to delete item"}, status=500)
        
        # Increment project version
        await project_repo.increment_version(proj_uuid)
        
        logger.info("item_deleted", item_id=item_id)
        
        return web.json_response({"status": "deleted", "item_id": item_id})
    
    async def reload_item(request: web.Request) -> web.Response:
        """
        Hot reload item configuration in a running engine.
        
        This endpoint signals the running engine to reload the item's
        configuration without stopping the entire production. Messages
        in the queue are preserved during reload.
        
        Note: This requires the engine to be running and connected.
        If no engine is running, this returns success but with a note
        that changes will apply on next engine start.
        """
        project_id = request.match_info["project_id"]
        item_id = request.match_info["item_id"]
        
        try:
            proj_uuid = UUID(project_id)
            item_uuid = UUID(item_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        # Get item from database
        item = await item_repo.get_by_id(item_uuid)
        if not item:
            return web.json_response({"error": "Item not found"}, status=404)
        if item['project_id'] != proj_uuid:
            return web.json_response({"error": "Item not found in project"}, status=404)
        
        # Check if there's a running engine for this project
        # For now, we store engine references in app state
        engine = request.app.get('engines', {}).get(str(proj_uuid))
        
        if engine:
            try:
                # Hot reload the item in the running engine
                result = await engine.reload_host_config(
                    name=item['name'],
                    pool_size=item['pool_size'],
                    enabled=item['enabled'],
                    adapter_settings=item['adapter_settings'],
                    host_settings=item['host_settings'],
                )
                logger.info("item_reloaded", item_id=item_id, result=result)
                return web.json_response({
                    "status": "reloaded",
                    "item_id": item_id,
                    "engine_state": result,
                })
            except KeyError:
                # Host not found in engine (might be newly created)
                logger.warning("item_not_in_engine", item_id=item_id)
                return web.json_response({
                    "status": "pending",
                    "item_id": item_id,
                    "message": "Item not yet loaded in engine. Restart project to apply.",
                })
            except Exception as e:
                logger.error("item_reload_failed", item_id=item_id, error=str(e))
                return web.json_response({"error": str(e)}, status=500)
        else:
            # No running engine - changes will apply on next start
            logger.info("item_reload_no_engine", item_id=item_id)
            return web.json_response({
                "status": "saved",
                "item_id": item_id,
                "message": "Configuration saved. Changes will apply when project is started.",
            })
    
    # ==================== Connection Routes ====================
    
    async def list_connections(request: web.Request) -> web.Response:
        """List all connections in a project."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        connections = await connection_repo.list_by_project(proj_uuid)
        
        response = ConnectionListResponse(
            connections=[ConnectionResponse(**c) for c in connections],
            total=len(connections)
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def create_connection(request: web.Request) -> web.Response:
        """Create a new connection."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        try:
            data = await request.json()
            create_data = ConnectionCreate.model_validate(data)
            
            # Verify source and target items exist and belong to project
            source_item = await item_repo.get_by_id(create_data.source_item_id)
            if not source_item or source_item['project_id'] != proj_uuid:
                return web.json_response({"error": "Source item not found"}, status=404)
            
            target_item = await item_repo.get_by_id(create_data.target_item_id)
            if not target_item or target_item['project_id'] != proj_uuid:
                return web.json_response({"error": "Target item not found"}, status=404)
            
            connection = await connection_repo.create(
                project_id=proj_uuid,
                source_item_id=create_data.source_item_id,
                target_item_id=create_data.target_item_id,
                connection_type=create_data.connection_type.value,
                enabled=create_data.enabled,
                filter_expression=create_data.filter_expression,
                comment=create_data.comment,
            )
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("connection_created", project_id=project_id)
            
            response = ConnectionResponse(**connection)
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("create_connection_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def update_connection(request: web.Request) -> web.Response:
        """Update connection."""
        project_id = request.match_info["project_id"]
        connection_id = request.match_info["connection_id"]
        
        try:
            proj_uuid = UUID(project_id)
            conn_uuid = UUID(connection_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        try:
            data = await request.json()
            update_data = ConnectionUpdate.model_validate(data)
            
            update_kwargs = {}
            if update_data.connection_type is not None:
                update_kwargs['connection_type'] = update_data.connection_type.value
            if update_data.enabled is not None:
                update_kwargs['enabled'] = update_data.enabled
            if update_data.filter_expression is not None:
                update_kwargs['filter_expression'] = update_data.filter_expression
            if update_data.comment is not None:
                update_kwargs['comment'] = update_data.comment
            
            connection = await connection_repo.update(conn_uuid, **update_kwargs)
            
            if not connection:
                return web.json_response({"error": "Connection not found"}, status=404)
            
            if connection['project_id'] != proj_uuid:
                return web.json_response({"error": "Connection not found in project"}, status=404)
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("connection_updated", connection_id=connection_id)
            
            response = ConnectionResponse(**connection)
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("update_connection_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_connection(request: web.Request) -> web.Response:
        """Delete connection."""
        project_id = request.match_info["project_id"]
        connection_id = request.match_info["connection_id"]
        
        try:
            proj_uuid = UUID(project_id)
            conn_uuid = UUID(connection_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        connection = await connection_repo.get_by_id(conn_uuid)
        if not connection:
            return web.json_response({"error": "Connection not found"}, status=404)
        if connection['project_id'] != proj_uuid:
            return web.json_response({"error": "Connection not found in project"}, status=404)
        
        deleted = await connection_repo.delete(conn_uuid)
        if not deleted:
            return web.json_response({"error": "Failed to delete connection"}, status=500)
        
        # Increment project version
        await project_repo.increment_version(proj_uuid)
        
        logger.info("connection_deleted", connection_id=connection_id)
        
        return web.json_response({"status": "deleted", "connection_id": connection_id})
    
    # ==================== Routing Rule Routes ====================
    
    async def list_routing_rules(request: web.Request) -> web.Response:
        """List all routing rules in a project."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        rules = await rule_repo.list_by_project(proj_uuid)
        
        return web.json_response({
            "routing_rules": [RoutingRuleResponse(**r).model_dump(mode='json') for r in rules],
            "total": len(rules)
        })
    
    async def create_routing_rule(request: web.Request) -> web.Response:
        """Create a new routing rule."""
        project_id = request.match_info["project_id"]
        
        try:
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid project ID"}, status=400)
        
        try:
            data = await request.json()
            create_data = RoutingRuleCreate.model_validate(data)
            
            rule = await rule_repo.create(
                project_id=proj_uuid,
                name=create_data.name,
                action=create_data.action.value,
                enabled=create_data.enabled,
                priority=create_data.priority,
                condition_expression=create_data.condition_expression,
                target_items=[str(t) for t in create_data.target_items],
                transform_name=create_data.transform_name,
            )
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("routing_rule_created", name=create_data.name, project_id=project_id)
            
            response = RoutingRuleResponse(**rule)
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("create_routing_rule_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def update_routing_rule(request: web.Request) -> web.Response:
        """Update routing rule."""
        project_id = request.match_info["project_id"]
        rule_id = request.match_info["rule_id"]
        
        try:
            proj_uuid = UUID(project_id)
            rule_uuid = UUID(rule_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        try:
            data = await request.json()
            update_data = RoutingRuleUpdate.model_validate(data)
            
            update_kwargs = {}
            if update_data.name is not None:
                update_kwargs['name'] = update_data.name
            if update_data.enabled is not None:
                update_kwargs['enabled'] = update_data.enabled
            if update_data.priority is not None:
                update_kwargs['priority'] = update_data.priority
            if update_data.condition_expression is not None:
                update_kwargs['condition_expression'] = update_data.condition_expression
            if update_data.action is not None:
                update_kwargs['action'] = update_data.action.value
            if update_data.target_items is not None:
                update_kwargs['target_items'] = [str(t) for t in update_data.target_items]
            if update_data.transform_name is not None:
                update_kwargs['transform_name'] = update_data.transform_name
            
            rule = await rule_repo.update(rule_uuid, **update_kwargs)
            
            if not rule:
                return web.json_response({"error": "Routing rule not found"}, status=404)
            
            if rule['project_id'] != proj_uuid:
                return web.json_response({"error": "Routing rule not found in project"}, status=404)
            
            # Increment project version
            await project_repo.increment_version(proj_uuid)
            
            logger.info("routing_rule_updated", rule_id=rule_id)
            
            response = RoutingRuleResponse(**rule)
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("update_routing_rule_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_routing_rule(request: web.Request) -> web.Response:
        """Delete routing rule."""
        project_id = request.match_info["project_id"]
        rule_id = request.match_info["rule_id"]
        
        try:
            proj_uuid = UUID(project_id)
            rule_uuid = UUID(rule_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        rule = await rule_repo.get_by_id(rule_uuid)
        if not rule:
            return web.json_response({"error": "Routing rule not found"}, status=404)
        if rule['project_id'] != proj_uuid:
            return web.json_response({"error": "Routing rule not found in project"}, status=404)
        
        deleted = await rule_repo.delete(rule_uuid)
        if not deleted:
            return web.json_response({"error": "Failed to delete routing rule"}, status=500)
        
        # Increment project version
        await project_repo.increment_version(proj_uuid)
        
        logger.info("routing_rule_deleted", rule_id=rule_id)
        
        return web.json_response({"status": "deleted", "rule_id": rule_id})
    
    # Register item routes
    app.router.add_get("/api/projects/{project_id}/items", list_items)
    app.router.add_post("/api/projects/{project_id}/items", create_item)
    app.router.add_get("/api/projects/{project_id}/items/{item_id}", get_item)
    app.router.add_put("/api/projects/{project_id}/items/{item_id}", update_item)
    app.router.add_delete("/api/projects/{project_id}/items/{item_id}", delete_item)
    app.router.add_post("/api/projects/{project_id}/items/{item_id}/reload", reload_item)
    
    # Register connection routes
    app.router.add_get("/api/projects/{project_id}/connections", list_connections)
    app.router.add_post("/api/projects/{project_id}/connections", create_connection)
    app.router.add_put("/api/projects/{project_id}/connections/{connection_id}", update_connection)
    app.router.add_delete("/api/projects/{project_id}/connections/{connection_id}", delete_connection)
    
    # Register routing rule routes
    app.router.add_get("/api/projects/{project_id}/routing-rules", list_routing_rules)
    app.router.add_post("/api/projects/{project_id}/routing-rules", create_routing_rule)
    app.router.add_put("/api/projects/{project_id}/routing-rules/{rule_id}", update_routing_rule)
    app.router.add_delete("/api/projects/{project_id}/routing-rules/{rule_id}", delete_routing_rule)
