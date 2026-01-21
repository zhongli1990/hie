"""
HTTP Receiver - Accepts messages via HTTP endpoints.

Supports receiving HL7v2 messages and other content types over HTTP/REST.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from aiohttp import web

from hie.core.item import Receiver, ItemConfig
from hie.core.message import Message, Priority
from hie.core.config import HTTPReceiverConfig

logger = structlog.get_logger(__name__)


class HTTPReceiver(Receiver):
    """
    HTTP receiver that accepts messages via REST endpoints.
    
    Features:
    - Configurable host, port, and path
    - Content-type validation
    - Request size limits
    - Async request handling
    - Health endpoint
    """
    
    def __init__(self, config: HTTPReceiverConfig) -> None:
        super().__init__(config)
        self._http_config = config
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._logger = logger.bind(item_id=self.id)
    
    @property
    def http_config(self) -> HTTPReceiverConfig:
        """HTTP-specific configuration."""
        return self._http_config
    
    async def _on_start(self) -> None:
        """Start the HTTP server."""
        self._app = web.Application(
            client_max_size=self._http_config.max_body_size
        )
        
        # Add routes
        self._app.router.add_route(
            "*",
            self._http_config.path,
            self._handle_request
        )
        self._app.router.add_get("/health", self._handle_health)
        
        # Start server
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(
            self._runner,
            self._http_config.host,
            self._http_config.port
        )
        await self._site.start()
        
        self._logger.info(
            "http_server_started",
            host=self._http_config.host,
            port=self._http_config.port,
            path=self._http_config.path
        )
    
    async def _on_stop(self) -> None:
        """Stop the HTTP server."""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        
        self._logger.info("http_server_stopped")
    
    async def _receive_loop(self) -> None:
        """HTTP receiver doesn't need a receive loop - requests are handled via callbacks."""
        # Just wait for shutdown
        while not self._shutdown_event.is_set():
            await asyncio.sleep(1.0)
    
    async def _handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming HTTP request."""
        # Validate method
        if request.method not in self._http_config.methods:
            return web.Response(
                status=405,
                text=f"Method not allowed. Allowed: {self._http_config.methods}"
            )
        
        # Validate content type
        content_type = request.content_type or "application/octet-stream"
        if self._http_config.content_types:
            if not any(ct in content_type for ct in self._http_config.content_types):
                return web.Response(
                    status=415,
                    text=f"Unsupported content type: {content_type}"
                )
        
        try:
            # Read body
            body = await request.read()
            
            if not body:
                return web.Response(status=400, text="Empty request body")
            
            # Record metrics
            self._metrics.record_received(len(body))
            
            # Determine message type from headers or content
            message_type = request.headers.get("X-Message-Type", "")
            priority_str = request.headers.get("X-Priority", "normal").lower()
            priority = Priority(priority_str) if priority_str in Priority.__members__.values() else Priority.NORMAL
            
            # Create message
            message = Message.create(
                raw=body,
                content_type=content_type,
                encoding=request.charset or "utf-8",
                source=self.id,
                message_type=message_type,
                priority=priority,
            )
            
            # Submit for processing
            await self.submit(message)
            
            self._logger.debug(
                "message_received",
                message_id=str(message.id),
                size=len(body),
                content_type=content_type
            )
            
            # Return acknowledgment
            return web.Response(
                status=202,
                text=str(message.id),
                content_type="text/plain"
            )
        
        except asyncio.QueueFull:
            self._logger.warning("queue_full")
            return web.Response(
                status=503,
                text="Service temporarily unavailable - queue full"
            )
        
        except Exception as e:
            self._logger.error("request_failed", error=str(e))
            return web.Response(
                status=500,
                text=f"Internal server error: {str(e)}"
            )
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle health check request."""
        health = self.health_check()
        status = 200 if health["healthy"] else 503
        
        import json
        return web.Response(
            status=status,
            text=json.dumps(health),
            content_type="application/json"
        )
    
    @classmethod
    def from_config(cls, config: dict[str, Any] | HTTPReceiverConfig) -> HTTPReceiver:
        """Create an HTTPReceiver from configuration."""
        if isinstance(config, dict):
            config = HTTPReceiverConfig.model_validate(config)
        return cls(config)
