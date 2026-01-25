"""
Project API Routes

CRUD operations for projects (productions) with LI Engine integration.
"""

from __future__ import annotations

import io
from uuid import UUID

from aiohttp import web
import structlog

from hie.api.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectState,
    DeployRequest,
    DeployResponse,
    ProjectStatusResponse,
    ImportIRISResponse,
    ItemResponse,
    ConnectionResponse,
    RoutingRuleResponse,
)
from hie.api.repositories import (
    WorkspaceRepository,
    ProjectRepository,
    ItemRepository,
    ConnectionRepository,
    RoutingRuleRepository,
)

logger = structlog.get_logger(__name__)


class EngineManager:
    """Manages LI Engine instances for running projects."""
    
    def __init__(self):
        self._engines: dict[UUID, "ProductionEngine"] = {}
    
    async def deploy(self, project_id: UUID, config: dict) -> str:
        """Deploy a project configuration to a new engine instance."""
        from hie.li.engine import ProductionEngine, EngineConfig
        from hie.li.config import ProductionConfig, ItemConfig
        
        # Create production config from project data
        items = []
        for item_data in config.get('items', []):
            item_config = ItemConfig(
                name=item_data['name'],
                class_name=item_data['class_name'],
                enabled=item_data.get('enabled', True),
                pool_size=item_data.get('pool_size', 1),
                category=item_data.get('category'),
            )
            # Add settings
            for key, value in (item_data.get('adapter_settings') or {}).items():
                item_config.set_setting('Adapter', key, value)
            for key, value in (item_data.get('host_settings') or {}).items():
                item_config.set_setting('Host', key, value)
            items.append(item_config)
        
        production_config = ProductionConfig(
            name=config['name'],
            description=config.get('description'),
            items=items,
        )
        
        # Create engine with minimal infrastructure for now
        engine_config = EngineConfig(
            wal_enabled=False,
            store_enabled=False,
            metrics_enabled=True,
            health_enabled=True,
            startup_delay=0.1,
        )
        
        engine = ProductionEngine(engine_config)
        await engine.load_from_config(production_config)
        
        self._engines[project_id] = engine
        
        engine_id = f"li-engine-{project_id.hex[:8]}"
        logger.info("engine_deployed", project_id=str(project_id), engine_id=engine_id)
        
        return engine_id
    
    async def start(self, project_id: UUID) -> int:
        """Start the engine for a project."""
        engine = self._engines.get(project_id)
        if not engine:
            raise ValueError(f"No engine deployed for project {project_id}")
        
        await engine.start()
        return engine._metrics.items_started
    
    async def stop(self, project_id: UUID) -> None:
        """Stop the engine for a project."""
        engine = self._engines.get(project_id)
        if engine:
            await engine.stop()
    
    async def get_status(self, project_id: UUID) -> dict:
        """Get engine status for a project."""
        engine = self._engines.get(project_id)
        if not engine:
            return {"state": "stopped", "items": []}
        
        return engine.get_status()
    
    def is_running(self, project_id: UUID) -> bool:
        """Check if engine is running for a project."""
        engine = self._engines.get(project_id)
        if not engine:
            return False
        from hie.li.engine import ProductionState
        return engine.state == ProductionState.RUNNING


# Global engine manager
_engine_manager = EngineManager()


def setup_project_routes(app: web.Application, db_pool) -> None:
    """Set up project routes."""
    workspace_repo = WorkspaceRepository(db_pool)
    project_repo = ProjectRepository(db_pool)
    item_repo = ItemRepository(db_pool)
    connection_repo = ConnectionRepository(db_pool)
    rule_repo = RoutingRuleRepository(db_pool)
    
    async def list_projects(request: web.Request) -> web.Response:
        """List all projects in a workspace."""
        workspace_id = request.match_info["workspace_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)
        
        # Verify workspace exists
        workspace = await workspace_repo.get_by_id(ws_uuid)
        if not workspace:
            return web.json_response({"error": "Workspace not found"}, status=404)
        
        projects = await project_repo.list_by_workspace(ws_uuid)
        
        # Add runtime state
        for proj in projects:
            if _engine_manager.is_running(proj['id']):
                proj['state'] = 'running'
        
        response = ProjectListResponse(
            projects=[ProjectResponse(**p) for p in projects],
            total=len(projects)
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def create_project(request: web.Request) -> web.Response:
        """Create a new project."""
        workspace_id = request.match_info["workspace_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)
        
        # Verify workspace exists
        workspace = await workspace_repo.get_by_id(ws_uuid)
        if not workspace:
            return web.json_response({"error": "Workspace not found"}, status=404)
        
        try:
            data = await request.json()
            create_data = ProjectCreate.model_validate(data)
            
            # Check if name already exists in workspace
            existing = await project_repo.get_by_name(ws_uuid, create_data.name)
            if existing:
                return web.json_response(
                    {"error": f"Project '{create_data.name}' already exists in this workspace"},
                    status=409
                )
            
            user_id = request.get("user_id")
            
            project = await project_repo.create(
                workspace_id=ws_uuid,
                name=create_data.name,
                display_name=create_data.display_name,
                description=create_data.description,
                enabled=create_data.enabled,
                created_by=user_id,
                settings=create_data.settings.model_dump() if create_data.settings else {},
            )
            
            logger.info("project_created", name=create_data.name, workspace_id=workspace_id)
            
            response = ProjectResponse(**project)
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("create_project_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def get_project(request: web.Request) -> web.Response:
        """Get project details with items and connections."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        project = await project_repo.get_full_config(proj_uuid)
        if not project:
            return web.json_response({"error": "Project not found"}, status=404)
        
        # Verify workspace match
        if project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found in workspace"}, status=404)
        
        # Add runtime state
        if _engine_manager.is_running(proj_uuid):
            project['state'] = 'running'
            status = await _engine_manager.get_status(proj_uuid)
            # Update item states from engine (hosts dict is keyed by name)
            item_states = status.get('hosts', {})
            for item in project['items']:
                if item['name'] in item_states:
                    item['state'] = item_states[item['name']].get('state')
                    item['metrics'] = {
                        'messages_received': item_states[item['name']].get('messages_received', 0),
                        'messages_failed': item_states[item['name']].get('messages_failed', 0),
                    }
        
        response = ProjectDetailResponse(
            **{k: v for k, v in project.items() if k not in ('items', 'connections', 'routing_rules')},
            items=[ItemResponse(**i) for i in project.get('items', [])],
            connections=[ConnectionResponse(**c) for c in project.get('connections', [])],
            routing_rules=[RoutingRuleResponse(**r) for r in project.get('routing_rules', [])],
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def update_project(request: web.Request) -> web.Response:
        """Update project."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        try:
            data = await request.json()
            update_data = ProjectUpdate.model_validate(data)
            
            project = await project_repo.update(
                proj_uuid,
                display_name=update_data.display_name,
                description=update_data.description,
                enabled=update_data.enabled,
                settings=update_data.settings.model_dump() if update_data.settings else None,
            )
            
            if not project:
                return web.json_response({"error": "Project not found"}, status=404)
            
            # Verify workspace match
            if project['workspace_id'] != ws_uuid:
                return web.json_response({"error": "Project not found in workspace"}, status=404)
            
            logger.info("project_updated", project_id=project_id)
            
            response = ProjectResponse(**project)
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("update_project_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_project(request: web.Request) -> web.Response:
        """Delete project."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        # Check if project exists
        project = await project_repo.get_by_id(proj_uuid)
        if not project:
            return web.json_response({"error": "Project not found"}, status=404)
        
        # Verify workspace match
        if project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found in workspace"}, status=404)
        
        # Stop engine if running
        if _engine_manager.is_running(proj_uuid):
            await _engine_manager.stop(proj_uuid)
        
        deleted = await project_repo.delete(proj_uuid)
        if not deleted:
            return web.json_response({"error": "Failed to delete project"}, status=500)
        
        logger.info("project_deleted", project_id=project_id)
        
        return web.json_response({"status": "deleted", "project_id": project_id})
    
    async def deploy_project(request: web.Request) -> web.Response:
        """Deploy project to LI Engine."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        try:
            data = await request.json() if request.can_read_body else {}
            deploy_data = DeployRequest.model_validate(data)
        except:
            deploy_data = DeployRequest()
        
        # Get full project config
        project = await project_repo.get_full_config(proj_uuid)
        if not project:
            return web.json_response({"error": "Project not found"}, status=404)
        
        if project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found in workspace"}, status=404)
        
        try:
            # Stop existing engine if running
            if _engine_manager.is_running(proj_uuid):
                await _engine_manager.stop(proj_uuid)
            
            # Deploy new engine
            engine_id = await _engine_manager.deploy(proj_uuid, project)
            
            items_started = 0
            state = ProjectState.STOPPED
            
            if deploy_data.start_after_deploy:
                items_started = await _engine_manager.start(proj_uuid)
                state = ProjectState.RUNNING
                await project_repo.update_state(proj_uuid, 'running')
            
            logger.info("project_deployed", project_id=project_id, engine_id=engine_id)
            
            response = DeployResponse(
                status="deployed",
                engine_id=engine_id,
                state=state,
                items_started=items_started,
            )
            return web.json_response(response.model_dump(mode='json'))
            
        except Exception as e:
            logger.error("deploy_project_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def start_project(request: web.Request) -> web.Response:
        """Start project engine."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        project = await project_repo.get_by_id(proj_uuid)
        if not project or project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found"}, status=404)
        
        try:
            # Check if already running
            if _engine_manager.is_running(proj_uuid):
                return web.json_response({
                    "status": "already_running",
                    "project_id": project_id,
                    "state": "running",
                    "message": "Project is already running",
                })
            
            # Deploy if not already deployed
            if proj_uuid not in _engine_manager._engines:
                full_config = await project_repo.get_full_config(proj_uuid)
                await _engine_manager.deploy(proj_uuid, full_config)
            
            items_started = await _engine_manager.start(proj_uuid)
            await project_repo.update_state(proj_uuid, 'running')
            
            logger.info("project_started", project_id=project_id)
            
            return web.json_response({
                "status": "started",
                "project_id": project_id,
                "state": "running",
                "items_started": items_started,
            })
            
        except Exception as e:
            logger.error("start_project_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def stop_project(request: web.Request) -> web.Response:
        """Stop project engine."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        project = await project_repo.get_by_id(proj_uuid)
        if not project or project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found"}, status=404)
        
        try:
            await _engine_manager.stop(proj_uuid)
            await project_repo.update_state(proj_uuid, 'stopped')
            
            logger.info("project_stopped", project_id=project_id)
            
            return web.json_response({
                "status": "stopped",
                "project_id": project_id,
                "state": "stopped",
            })
            
        except Exception as e:
            logger.error("stop_project_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_project_status(request: web.Request) -> web.Response:
        """Get project runtime status."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        project = await project_repo.get_by_id(proj_uuid)
        if not project or project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found"}, status=404)
        
        status = await _engine_manager.get_status(proj_uuid)
        
        state = ProjectState.RUNNING if _engine_manager.is_running(proj_uuid) else ProjectState.STOPPED
        
        response = ProjectStatusResponse(
            project_id=proj_uuid,
            state=state,
            engine_id=status.get('engine_id'),
            started_at=status.get('started_at'),
            uptime_seconds=0,  # TODO: Calculate from started_at
            metrics=status.get('metrics', {}),
        )
        return web.json_response(response.model_dump(mode='json'))
    
    async def import_iris_config(request: web.Request) -> web.Response:
        """Import IRIS XML configuration."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info.get("project_id")
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id) if project_id else None
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        # Verify workspace exists
        workspace = await workspace_repo.get_by_id(ws_uuid)
        if not workspace:
            return web.json_response({"error": "Workspace not found"}, status=404)
        
        try:
            # Read multipart form data
            reader = await request.multipart()
            
            xml_content = None
            options = {}
            
            async for part in reader:
                if part.name == 'file':
                    xml_content = await part.read()
                elif part.name == 'options':
                    import json
                    options = json.loads(await part.text())
            
            if not xml_content:
                return web.json_response({"error": "No file provided"}, status=400)
            
            # Parse IRIS XML
            from hie.li.config import IRISXMLLoader
            loader = IRISXMLLoader()
            
            # Try to decode as string
            if isinstance(xml_content, bytes):
                xml_content = xml_content.decode('utf-8')
            
            production_config = loader.load_from_string(xml_content)
            
            # Create or update project
            if proj_uuid:
                project = await project_repo.get_by_id(proj_uuid)
                if not project:
                    return web.json_response({"error": "Project not found"}, status=404)
                
                # Clear existing items and connections
                items = await item_repo.list_by_project(proj_uuid)
                for item in items:
                    await item_repo.delete(item['id'])
            else:
                # Create new project
                project_name = options.get('project_name', production_config.name)
                
                # Check if name exists
                existing = await project_repo.get_by_name(ws_uuid, project_name)
                if existing:
                    if options.get('overwrite_existing'):
                        proj_uuid = existing['id']
                        # Clear existing items
                        items = await item_repo.list_by_project(proj_uuid)
                        for item in items:
                            await item_repo.delete(item['id'])
                    else:
                        return web.json_response(
                            {"error": f"Project '{project_name}' already exists"},
                            status=409
                        )
                else:
                    project = await project_repo.create(
                        workspace_id=ws_uuid,
                        name=project_name,
                        display_name=production_config.name,
                        description=production_config.description or f"Imported from IRIS",
                    )
                    proj_uuid = project['id']
            
            # Import items
            items_imported = 0
            item_id_map = {}  # Map item names to IDs for connections
            
            for item_config in production_config.items:
                # Determine item type from class name
                class_name = item_config.class_name
                if 'Service' in class_name:
                    item_type = 'service'
                elif 'Operation' in class_name:
                    item_type = 'operation'
                else:
                    item_type = 'process'
                
                # Extract settings
                adapter_settings = {}
                host_settings = {}
                for setting in item_config.settings:
                    if setting.target.value == 'Adapter':
                        adapter_settings[setting.name] = setting.value
                    else:
                        host_settings[setting.name] = setting.value
                
                item = await item_repo.create(
                    project_id=proj_uuid,
                    name=item_config.name,
                    display_name=item_config.name,
                    item_type=item_type,
                    class_name=class_name,
                    category=item_config.category,
                    enabled=item_config.enabled,
                    pool_size=item_config.pool_size,
                    adapter_settings=adapter_settings,
                    host_settings=host_settings,
                    comment=item_config.comment,
                )
                item_id_map[item_config.name] = item['id']
                items_imported += 1
            
            # Create connections based on TargetConfigNames
            connections_imported = 0
            for item_config in production_config.items:
                target_names = item_config.get_setting('Host', 'TargetConfigNames')
                if target_names:
                    source_id = item_id_map.get(item_config.name)
                    if source_id:
                        # Parse comma-separated targets
                        targets = [t.strip() for t in str(target_names).split(',')]
                        for target_name in targets:
                            target_id = item_id_map.get(target_name)
                            if target_id:
                                await connection_repo.create(
                                    project_id=proj_uuid,
                                    source_item_id=source_id,
                                    target_item_id=target_id,
                                )
                                connections_imported += 1
            
            logger.info(
                "iris_config_imported",
                project_id=str(proj_uuid),
                items=items_imported,
                connections=connections_imported,
            )
            
            response = ImportIRISResponse(
                status="imported",
                project_id=proj_uuid,
                project_name=production_config.name,
                items_imported=items_imported,
                connections_imported=connections_imported,
            )
            return web.json_response(response.model_dump(mode='json'), status=201)
            
        except Exception as e:
            logger.error("import_iris_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)
    
    async def export_project_config(request: web.Request) -> web.Response:
        """Export project configuration as JSON."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        project = await project_repo.get_full_config(proj_uuid)
        if not project or project['workspace_id'] != ws_uuid:
            return web.json_response({"error": "Project not found"}, status=404)
        
        # Convert UUIDs to strings for JSON serialization
        import json
        
        def serialize(obj):
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        from datetime import datetime
        
        return web.json_response(project, dumps=lambda x: json.dumps(x, default=serialize))
    
    async def send_test_message(request: web.Request) -> web.Response:
        """Send a test HL7 message through an outbound operation."""
        workspace_id = request.match_info["workspace_id"]
        project_id = request.match_info["project_id"]
        item_name = request.match_info["item_name"]
        
        try:
            ws_uuid = UUID(workspace_id)
            proj_uuid = UUID(project_id)
        except ValueError:
            return web.json_response({"error": "Invalid ID"}, status=400)
        
        # Check if engine is running
        if not _engine_manager.is_running(proj_uuid):
            return web.json_response({"error": "Project is not running"}, status=400)
        
        engine = _engine_manager._engines.get(proj_uuid)
        if not engine:
            return web.json_response({"error": "Engine not found"}, status=404)
        
        # Get the host (operation)
        host = engine.get_host(item_name)
        if not host:
            return web.json_response({"error": f"Item '{item_name}' not found"}, status=404)
        
        # Get message from request body or use default test message
        try:
            data = await request.json() if request.can_read_body else {}
        except:
            data = {}
        
        hl7_message = data.get('message')
        if not hl7_message:
            # Generate a default ADT^A01 test message
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            msg_id = f"TEST{timestamp}"
            hl7_message = (
                f"MSH|^~\\&|HIE|HIE|REMOTE|REMOTE|{timestamp}||ADT^A01|{msg_id}|P|2.4\r"
                f"EVN|A01|{timestamp}\r"
                f"PID|1||TEST123^^^MRN||Doe^John^Q||19800101|M|||123 Main St^^London^^SW1A 1AA^UK\r"
                f"PV1|1|I|WARD1^ROOM1^BED1||||12345^Smith^Jane|||MED||||||||V123456\r"
            )
        
        try:
            # Check if host has a send method (operations do)
            if hasattr(host, 'send_message'):
                result = await host.send_message(hl7_message.encode() if isinstance(hl7_message, str) else hl7_message)
                return web.json_response({
                    "status": "sent",
                    "item_name": item_name,
                    "message_id": data.get('message_id', 'TEST'),
                    "result": result.decode() if isinstance(result, bytes) else str(result) if result else "No ACK",
                })
            else:
                # For operations, we need to use the adapter directly
                adapter = host._adapter
                if adapter and hasattr(adapter, 'send'):
                    msg_bytes = hl7_message.encode() if isinstance(hl7_message, str) else hl7_message
                    ack = await adapter.send(msg_bytes)
                    return web.json_response({
                        "status": "sent",
                        "item_name": item_name,
                        "ack": ack.decode() if isinstance(ack, bytes) else str(ack) if ack else "No ACK",
                    })
                else:
                    return web.json_response({"error": "Item does not support sending messages"}, status=400)
        except Exception as e:
            logger.error("send_test_message_failed", item_name=item_name, error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    # Register routes
    app.router.add_get("/api/workspaces/{workspace_id}/projects", list_projects)
    app.router.add_post("/api/workspaces/{workspace_id}/projects", create_project)
    app.router.add_get("/api/workspaces/{workspace_id}/projects/{project_id}", get_project)
    app.router.add_put("/api/workspaces/{workspace_id}/projects/{project_id}", update_project)
    app.router.add_delete("/api/workspaces/{workspace_id}/projects/{project_id}", delete_project)
    
    # Engine control
    app.router.add_post("/api/workspaces/{workspace_id}/projects/{project_id}/deploy", deploy_project)
    app.router.add_post("/api/workspaces/{workspace_id}/projects/{project_id}/start", start_project)
    app.router.add_post("/api/workspaces/{workspace_id}/projects/{project_id}/stop", stop_project)
    app.router.add_get("/api/workspaces/{workspace_id}/projects/{project_id}/status", get_project_status)
    
    # Import/Export
    app.router.add_post("/api/workspaces/{workspace_id}/projects/import", import_iris_config)
    app.router.add_post("/api/workspaces/{workspace_id}/projects/{project_id}/import", import_iris_config)
    app.router.add_get("/api/workspaces/{workspace_id}/projects/{project_id}/export", export_project_config)
    
    # Testing
    app.router.add_post("/api/workspaces/{workspace_id}/projects/{project_id}/items/{item_name}/test", send_test_message)
