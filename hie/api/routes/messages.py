"""
HIE API Routes - Portal Messages

Endpoints for viewing and managing messages in the Messages tab.
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Optional
from uuid import UUID

from aiohttp import web
import structlog

from hie.api.repositories import PortalMessageRepository

logger = structlog.get_logger(__name__)


def _serialize_message(msg: dict) -> dict:
    """Serialize message for JSON response."""
    result = {}
    for key, value in msg.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, UUID):
            result[key] = str(value)
        elif isinstance(value, bytes):
            # Don't include raw bytes in list responses
            continue
        elif isinstance(value, (int, float)) and value is not None:
            result[key] = value
        else:
            result[key] = value
    return result


async def list_messages(request: web.Request) -> web.Response:
    """List messages for a project with optional filters.
    
    GET /api/projects/{project_id}/messages
    Query params: item, status, type, direction, limit, offset
    """
    project_id = request.match_info.get("project_id")
    
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        return web.json_response({"error": "Invalid project ID"}, status=400)
    
    # Get query parameters
    item_name = request.query.get("item")
    status = request.query.get("status")
    message_type = request.query.get("type")
    direction = request.query.get("direction")
    
    try:
        limit = min(int(request.query.get("limit", 50)), 100)
        offset = int(request.query.get("offset", 0))
    except ValueError:
        limit, offset = 50, 0
    
    pool = request.app.get("db_pool")
    if not pool:
        return web.json_response({"error": "Database not available"}, status=503)
    
    repo = PortalMessageRepository(pool)
    
    try:
        messages, total = await repo.list_by_project(
            project_id=proj_uuid,
            item_name=item_name,
            status=status,
            message_type=message_type,
            direction=direction,
            limit=limit,
            offset=offset,
        )
        
        return web.json_response({
            "messages": [_serialize_message(m) for m in messages],
            "total": total,
            "limit": limit,
            "offset": offset,
        })
    except Exception as e:
        logger.error("list_messages_failed", error=str(e), project_id=project_id)
        return web.json_response({"error": str(e)}, status=500)


async def get_message(request: web.Request) -> web.Response:
    """Get message details including full content.
    
    GET /api/projects/{project_id}/messages/{message_id}
    """
    project_id = request.match_info.get("project_id")
    message_id = request.match_info.get("message_id")
    
    try:
        proj_uuid = UUID(project_id)
        msg_uuid = UUID(message_id)
    except ValueError:
        return web.json_response({"error": "Invalid ID"}, status=400)
    
    pool = request.app.get("db_pool")
    if not pool:
        return web.json_response({"error": "Database not available"}, status=503)
    
    repo = PortalMessageRepository(pool)
    
    try:
        message = await repo.get_by_id(msg_uuid)
        if not message:
            return web.json_response({"error": "Message not found"}, status=404)
        
        # Verify project ownership
        if message.get("project_id") != proj_uuid:
            return web.json_response({"error": "Message not found"}, status=404)
        
        # Serialize with content
        result = _serialize_message(message)
        
        # Add raw content as base64 if present
        if message.get("raw_content"):
            result["raw_content_base64"] = base64.b64encode(message["raw_content"]).decode()
            # Also provide decoded string for HL7
            try:
                result["raw_content_text"] = message["raw_content"].decode('utf-8', errors='replace')
            except:
                pass
        
        if message.get("ack_content"):
            result["ack_content_base64"] = base64.b64encode(message["ack_content"]).decode()
            try:
                result["ack_content_text"] = message["ack_content"].decode('utf-8', errors='replace')
            except:
                pass
        
        return web.json_response(result)
    except Exception as e:
        logger.error("get_message_failed", error=str(e), message_id=message_id)
        return web.json_response({"error": str(e)}, status=500)


async def get_message_stats(request: web.Request) -> web.Response:
    """Get message statistics for a project.
    
    GET /api/projects/{project_id}/messages/stats
    """
    project_id = request.match_info.get("project_id")
    
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        return web.json_response({"error": "Invalid project ID"}, status=400)
    
    pool = request.app.get("db_pool")
    if not pool:
        return web.json_response({"error": "Database not available"}, status=503)
    
    repo = PortalMessageRepository(pool)
    
    try:
        stats = await repo.get_stats(proj_uuid)
        # Convert Decimal to float for JSON
        result = {}
        for key, value in stats.items():
            if value is None:
                result[key] = 0
            elif hasattr(value, '__float__'):
                result[key] = float(value)
            else:
                result[key] = value
        return web.json_response(result)
    except Exception as e:
        logger.error("get_message_stats_failed", error=str(e), project_id=project_id)
        return web.json_response({"error": str(e)}, status=500)


async def resend_message(request: web.Request) -> web.Response:
    """Resend a failed message.
    
    POST /api/projects/{project_id}/messages/{message_id}/resend
    """
    project_id = request.match_info.get("project_id")
    message_id = request.match_info.get("message_id")
    
    try:
        proj_uuid = UUID(project_id)
        msg_uuid = UUID(message_id)
    except ValueError:
        return web.json_response({"error": "Invalid ID"}, status=400)
    
    pool = request.app.get("db_pool")
    if not pool:
        return web.json_response({"error": "Database not available"}, status=503)
    
    repo = PortalMessageRepository(pool)
    
    try:
        # Get the original message
        message = await repo.get_by_id(msg_uuid)
        if not message:
            return web.json_response({"error": "Message not found"}, status=404)
        
        if message.get("project_id") != proj_uuid:
            return web.json_response({"error": "Message not found"}, status=404)
        
        # Get the raw content
        content = await repo.get_content(msg_uuid)
        if not content or not content.get("raw_content"):
            return web.json_response({"error": "Message content not available"}, status=400)
        
        # Find the destination item and resend
        # This requires access to the running engine
        from hie.api.routes.projects import _engine_manager
        
        engine_id = f"li-engine-{project_id[:8]}"
        engine = _engine_manager.get(engine_id)
        
        if not engine:
            return web.json_response({"error": "Project engine not running"}, status=400)
        
        destination = message.get("destination_item")
        if not destination:
            return web.json_response({"error": "No destination item specified"}, status=400)
        
        # Get the destination host
        host = engine.get_host(destination)
        if not host:
            return web.json_response({"error": f"Destination item '{destination}' not found"}, status=404)
        
        # Send the message
        adapter = getattr(host, '_adapter', None)
        if adapter and hasattr(adapter, 'send'):
            ack = await adapter.send(content["raw_content"])
            
            # Update the original message status
            await repo.update_status(
                msg_uuid,
                status="sent",
                ack_content=ack if isinstance(ack, bytes) else ack.encode() if ack else None,
            )
            
            return web.json_response({
                "status": "resent",
                "message_id": str(msg_uuid),
                "ack": ack.decode() if isinstance(ack, bytes) else str(ack) if ack else None,
            })
        else:
            return web.json_response({"error": "Destination does not support sending"}, status=400)
        
    except Exception as e:
        logger.error("resend_message_failed", error=str(e), message_id=message_id)
        return web.json_response({"error": str(e)}, status=500)


async def delete_old_messages(request: web.Request) -> web.Response:
    """Delete old messages (housekeeping).
    
    DELETE /api/messages/housekeeping?days=30
    """
    try:
        days = int(request.query.get("days", 30))
        if days < 1:
            days = 30
    except ValueError:
        days = 30
    
    pool = request.app.get("db_pool")
    if not pool:
        return web.json_response({"error": "Database not available"}, status=503)
    
    repo = PortalMessageRepository(pool)
    
    try:
        deleted = await repo.delete_old_messages(days)
        return web.json_response({
            "status": "completed",
            "deleted_count": deleted,
            "older_than_days": days,
        })
    except Exception as e:
        logger.error("delete_old_messages_failed", error=str(e))
        return web.json_response({"error": str(e)}, status=500)


def register_routes(app: web.Application) -> None:
    """Register message routes.
    
    Note: Stats route must be registered before the generic {message_id} route
    to avoid pattern conflicts.
    """
    # Stats route first (more specific pattern)
    app.router.add_get("/api/projects/{project_id}/messages/stats", get_message_stats)
    # Then list and detail routes
    app.router.add_get("/api/projects/{project_id}/messages", list_messages)
    app.router.add_get("/api/projects/{project_id}/messages/{message_id}", get_message)
    app.router.add_post("/api/projects/{project_id}/messages/{message_id}/resend", resend_message)
    # Housekeeping
    app.router.add_delete("/api/messages/housekeeping", delete_old_messages)
