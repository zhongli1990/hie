"""
HIE Management API Server

Provides REST endpoints for managing the HIE engine.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any, Optional

from aiohttp import web
import structlog
import asyncpg

from hie.core.production import Production
from hie.core.schema import ProductionSchema

logger = structlog.get_logger(__name__)


class APIServer:
    """Management API server for HIE."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8081,
        db_pool: Optional[asyncpg.Pool] = None,
    ):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.productions: dict[str, Production] = {}
        self.db_pool = db_pool
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Configure API routes."""
        self.app.router.add_get("/api/health", self.health_check)
        self.app.router.add_get("/api/stats/dashboard", self.get_dashboard_stats)
        self.app.router.add_get("/api/health/services", self.get_service_health)
        
        # Productions
        self.app.router.add_get("/api/productions", self.list_productions)
        self.app.router.add_post("/api/productions", self.create_production)
        self.app.router.add_get("/api/productions/{name}", self.get_production)
        self.app.router.add_put("/api/productions/{name}", self.update_production)
        self.app.router.add_delete("/api/productions/{name}", self.delete_production)
        
        # Production actions
        self.app.router.add_post("/api/productions/{name}/start", self.start_production)
        self.app.router.add_post("/api/productions/{name}/stop", self.stop_production)
        self.app.router.add_post("/api/productions/{name}/pause", self.pause_production)
        self.app.router.add_post("/api/productions/{name}/resume", self.resume_production)
        
        # Items
        self.app.router.add_get("/api/productions/{name}/items", self.list_items)
        self.app.router.add_get("/api/productions/{name}/items/{item_id}", self.get_item)
        self.app.router.add_post("/api/productions/{name}/items/{item_id}/start", self.start_item)
        self.app.router.add_post("/api/productions/{name}/items/{item_id}/stop", self.stop_item)
        
        # Messages
        self.app.router.add_get("/api/messages", self.search_messages)
        self.app.router.add_get("/api/messages/{message_id}", self.get_message)
        self.app.router.add_post("/api/messages/{message_id}/resend", self.resend_message)
        
        # Configuration
        self.app.router.add_get("/api/productions/{name}/config", self.export_config)
        self.app.router.add_post("/api/productions/{name}/config", self.import_config)
        
        # Auth routes (if db_pool is available)
        if self.db_pool:
            from hie.auth.aiohttp_router import setup_auth_routes
            setup_auth_routes(self.app, self.db_pool)
            logger.info("auth_routes_registered")
        
        # Add CORS middleware
        self.app.middlewares.append(self._cors_middleware)
    
    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler) -> web.Response:
        """Add CORS headers to responses."""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)
        
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
    
    def register_production(self, production: Production) -> None:
        """Register a production with the API server."""
        self.productions[production.name] = production
        logger.info("production_registered", name=production.name)
    
    # Health endpoints
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.2.0",
        })
    
    async def get_service_health(self, request: web.Request) -> web.Response:
        """Get health status of all services."""
        services = [
            {"service": "HIE Engine", "status": "healthy", "latency_ms": 1},
            {"service": "Management API", "status": "healthy", "latency_ms": 1},
        ]
        
        # TODO: Check actual database connections
        services.append({"service": "PostgreSQL", "status": "healthy", "latency_ms": 2})
        services.append({"service": "Redis", "status": "healthy", "latency_ms": 1})
        
        return web.json_response({"services": services})
    
    async def get_dashboard_stats(self, request: web.Request) -> web.Response:
        """Get dashboard statistics."""
        total_received = 0
        total_processed = 0
        total_failed = 0
        
        for prod in self.productions.values():
            metrics = prod.get_metrics()
            total_received += metrics.get("messages_received", 0)
            total_processed += metrics.get("messages_processed", 0)
            total_failed += metrics.get("messages_failed", 0)
        
        return web.json_response({
            "productions_count": len(self.productions),
            "items_count": sum(len(p.items) for p in self.productions.values()),
            "messages_processed_today": total_processed,
            "messages_processed_total": total_processed,
            "error_rate": total_failed / max(total_processed, 1),
            "recent_activity": [],
        })
    
    # Production endpoints
    
    async def list_productions(self, request: web.Request) -> web.Response:
        """List all productions."""
        productions = []
        for name, prod in self.productions.items():
            productions.append({
                "name": name,
                "description": prod.config.description,
                "enabled": prod.config.enabled,
                "state": prod.state.value,
                "items_count": len(prod.items),
                "routes_count": len(prod.routes),
                "metrics": prod.get_metrics(),
            })
        return web.json_response(productions)
    
    async def create_production(self, request: web.Request) -> web.Response:
        """Create a new production."""
        try:
            data = await request.json()
            schema = ProductionSchema.model_validate(data)
            
            # TODO: Create production from schema
            
            return web.json_response(
                {"status": "created", "name": schema.name},
                status=201
            )
        except Exception as e:
            logger.error("create_production_failed", error=str(e))
            return web.json_response(
                {"error": str(e)},
                status=400
            )
    
    async def get_production(self, request: web.Request) -> web.Response:
        """Get production details."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        
        items = []
        for item_id, item in prod.items.items():
            items.append({
                "id": item.id,
                "name": item.name,
                "type": item.config.type if hasattr(item.config, 'type') else str(item.item_type.value),
                "category": item.item_type.value,
                "enabled": item.config.enabled,
                "state": item.state.value,
                "metrics": {
                    "messages_received": item.metrics.messages_received,
                    "messages_processed": item.metrics.messages_processed,
                    "messages_failed": item.metrics.messages_failed,
                    "messages_in_queue": item._queue.qsize() if hasattr(item, '_queue') else 0,
                    "avg_latency_ms": item.metrics.processing_time_avg_ms,
                },
            })
        
        return web.json_response({
            "name": name,
            "description": prod.config.description,
            "enabled": prod.config.enabled,
            "state": prod.state.value,
            "settings": {
                "graceful_shutdown_timeout": prod.config.graceful_shutdown_timeout,
                "health_check_interval": prod.config.health_check_interval,
                "auto_start_items": prod.config.auto_start_items,
            },
            "items": items,
            "routes": [
                {
                    "id": r.id,
                    "name": r.name,
                    "enabled": r.config.enabled,
                    "state": r.state.value,
                }
                for r in prod.routes.values()
            ],
            "metrics": prod.get_metrics(),
        })
    
    async def update_production(self, request: web.Request) -> web.Response:
        """Update production configuration."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        try:
            data = await request.json()
            # TODO: Apply updates to production
            return web.json_response({"status": "updated", "name": name})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def delete_production(self, request: web.Request) -> web.Response:
        """Delete a production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        if prod.is_running:
            await prod.stop()
        
        del self.productions[name]
        return web.json_response({"status": "deleted", "name": name})
    
    # Production actions
    
    async def start_production(self, request: web.Request) -> web.Response:
        """Start a production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        await prod.start()
        
        return web.json_response({
            "status": "started",
            "name": name,
            "state": prod.state.value,
        })
    
    async def stop_production(self, request: web.Request) -> web.Response:
        """Stop a production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        await prod.stop()
        
        return web.json_response({
            "status": "stopped",
            "name": name,
            "state": prod.state.value,
        })
    
    async def pause_production(self, request: web.Request) -> web.Response:
        """Pause a production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        await prod.pause()
        
        return web.json_response({
            "status": "paused",
            "name": name,
            "state": prod.state.value,
        })
    
    async def resume_production(self, request: web.Request) -> web.Response:
        """Resume a paused production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        await prod.resume()
        
        return web.json_response({
            "status": "resumed",
            "name": name,
            "state": prod.state.value,
        })
    
    # Item endpoints
    
    async def list_items(self, request: web.Request) -> web.Response:
        """List items in a production."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        items = []
        
        for item_id, item in prod.items.items():
            items.append({
                "id": item.id,
                "name": item.name,
                "type": item.item_type.value,
                "state": item.state.value,
                "enabled": item.config.enabled,
            })
        
        return web.json_response(items)
    
    async def get_item(self, request: web.Request) -> web.Response:
        """Get item details."""
        name = request.match_info["name"]
        item_id = request.match_info["item_id"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        
        if item_id not in prod.items:
            return web.json_response(
                {"error": f"Item '{item_id}' not found"},
                status=404
            )
        
        item = prod.items[item_id]
        return web.json_response(item.health_check())
    
    async def start_item(self, request: web.Request) -> web.Response:
        """Start an item."""
        name = request.match_info["name"]
        item_id = request.match_info["item_id"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        
        if item_id not in prod.items:
            return web.json_response(
                {"error": f"Item '{item_id}' not found"},
                status=404
            )
        
        item = prod.items[item_id]
        await item.start()
        
        return web.json_response({
            "status": "started",
            "item_id": item_id,
            "state": item.state.value,
        })
    
    async def stop_item(self, request: web.Request) -> web.Response:
        """Stop an item."""
        name = request.match_info["name"]
        item_id = request.match_info["item_id"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        prod = self.productions[name]
        
        if item_id not in prod.items:
            return web.json_response(
                {"error": f"Item '{item_id}' not found"},
                status=404
            )
        
        item = prod.items[item_id]
        await item.stop()
        
        return web.json_response({
            "status": "stopped",
            "item_id": item_id,
            "state": item.state.value,
        })
    
    # Message endpoints
    
    async def search_messages(self, request: web.Request) -> web.Response:
        """Search messages."""
        # TODO: Implement message search
        return web.json_response([])
    
    async def get_message(self, request: web.Request) -> web.Response:
        """Get message details."""
        message_id = request.match_info["message_id"]
        # TODO: Implement message retrieval
        return web.json_response(
            {"error": f"Message '{message_id}' not found"},
            status=404
        )
    
    async def resend_message(self, request: web.Request) -> web.Response:
        """Resend a message."""
        message_id = request.match_info["message_id"]
        # TODO: Implement message resend
        return web.json_response(
            {"error": f"Message '{message_id}' not found"},
            status=404
        )
    
    # Configuration endpoints
    
    async def export_config(self, request: web.Request) -> web.Response:
        """Export production configuration."""
        name = request.match_info["name"]
        
        if name not in self.productions:
            return web.json_response(
                {"error": f"Production '{name}' not found"},
                status=404
            )
        
        # TODO: Export full configuration
        return web.json_response({
            "name": name,
            "items": [],
            "connections": [],
        })
    
    async def import_config(self, request: web.Request) -> web.Response:
        """Import production configuration."""
        name = request.match_info["name"]
        
        try:
            data = await request.json()
            # TODO: Apply configuration
            return web.json_response({"status": "imported", "name": name})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def start(self) -> None:
        """Start the API server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info("api_server_started", host=self.host, port=self.port)
    
    async def run_forever(self) -> None:
        """Run the API server until interrupted."""
        await self.start()
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass


async def create_db_pool() -> Optional[asyncpg.Pool]:
    """Create database connection pool."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Try to construct from individual vars
        db_host = os.environ.get("POSTGRES_HOST", "localhost")
        db_port = os.environ.get("POSTGRES_PORT", "5432")
        db_name = os.environ.get("POSTGRES_DB", "hie")
        db_user = os.environ.get("POSTGRES_USER", "hie")
        db_pass = os.environ.get("POSTGRES_PASSWORD", "hie")
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        logger.info("database_pool_created", host=os.environ.get("POSTGRES_HOST", "localhost"))
        return pool
    except Exception as e:
        logger.warning("database_pool_failed", error=str(e))
        return None


def create_app() -> web.Application:
    """Create the API application."""
    server = APIServer()
    return server.app


async def run_server(
    host: str = "0.0.0.0",
    port: int = 8081,
    productions: dict[str, Production] | None = None,
) -> None:
    """Run the API server."""
    # Create database pool for auth
    db_pool = await create_db_pool()
    
    server = APIServer(host=host, port=port, db_pool=db_pool)
    
    if productions:
        for name, prod in productions.items():
            server.register_production(prod)
    
    await server.run_forever()
