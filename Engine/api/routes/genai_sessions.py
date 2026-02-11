"""
GenAI Session API Routes

Session persistence for GenAI Agents and Chat pages.
"""

from __future__ import annotations

from uuid import UUID

from aiohttp import web
import structlog

from Engine.api.models import (
    GenAISessionCreate,
    GenAISessionResponse,
    GenAISessionListResponse,
    GenAIMessageCreate,
    GenAIMessageResponse,
    GenAIMessageListResponse,
)
from Engine.api.repositories import GenAISessionRepository

logger = structlog.get_logger(__name__)


def setup_genai_session_routes(app: web.Application, db_pool) -> None:
    """Set up GenAI session routes."""
    repo = GenAISessionRepository(db_pool)

    async def list_sessions(request: web.Request) -> web.Response:
        """List all sessions for a workspace."""
        workspace_id_str = request.query.get("workspace_id")
        if not workspace_id_str:
            return web.json_response({"error": "workspace_id query parameter required"}, status=400)

        try:
            workspace_id = UUID(workspace_id_str)
        except ValueError:
            return web.json_response({"error": "Invalid workspace ID"}, status=400)

        sessions = await repo.list_sessions(workspace_id)

        response = GenAISessionListResponse(
            sessions=[GenAISessionResponse(**s) for s in sessions],
            total=len(sessions)
        )
        return web.json_response(response.model_dump(mode='json'))

    async def create_session(request: web.Request) -> web.Response:
        """Create a new session."""
        try:
            data = await request.json()
            create_data = GenAISessionCreate.model_validate(data)

            session = await repo.create_session(
                workspace_id=create_data.workspace_id,
                project_id=create_data.project_id,
                runner_type=create_data.runner_type,
                title=create_data.title or f"{create_data.runner_type.capitalize()} Session",
            )

            logger.info("genai_session_created", session_id=session['session_id'])

            response = GenAISessionResponse(**session)
            return web.json_response(response.model_dump(mode='json'), status=201)

        except Exception as e:
            logger.error("create_session_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)

    async def get_session(request: web.Request) -> web.Response:
        """Get session by ID."""
        session_id = request.match_info["session_id"]

        try:
            sess_uuid = UUID(session_id)
        except ValueError:
            return web.json_response({"error": "Invalid session ID"}, status=400)

        session = await repo.get_session(sess_uuid)
        if not session:
            return web.json_response({"error": "Session not found"}, status=404)

        response = GenAISessionResponse(**session)
        return web.json_response(response.model_dump(mode='json'))

    async def list_messages(request: web.Request) -> web.Response:
        """List all messages in a session."""
        session_id = request.match_info["session_id"]

        try:
            sess_uuid = UUID(session_id)
        except ValueError:
            return web.json_response({"error": "Invalid session ID"}, status=400)

        messages = await repo.list_messages(sess_uuid)

        response = GenAIMessageListResponse(
            messages=[GenAIMessageResponse(**m) for m in messages],
            total=len(messages)
        )
        return web.json_response(response.model_dump(mode='json'))

    async def create_message(request: web.Request) -> web.Response:
        """Create a new message in a session."""
        session_id = request.match_info["session_id"]

        try:
            sess_uuid = UUID(session_id)
        except ValueError:
            return web.json_response({"error": "Invalid session ID"}, status=400)

        try:
            data = await request.json()
            create_data = GenAIMessageCreate.model_validate(data)

            message = await repo.create_message(
                session_id=sess_uuid,
                role=create_data.role,
                content=create_data.content,
                run_id=create_data.run_id,
                metadata=create_data.metadata,
            )

            # Update session title from first user message if not set
            if create_data.role == "user":
                session = await repo.get_session(sess_uuid)
                if session and (not session.get('title') or session['title'].endswith('Session')):
                    title = f"Question: {create_data.content[:50]}..."
                    await repo.update_session_title(sess_uuid, title)

            response = GenAIMessageResponse(**message)
            return web.json_response(response.model_dump(mode='json'), status=201)

        except Exception as e:
            logger.error("create_message_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=400)

    # Register routes
    app.router.add_get("/api/genai-sessions", list_sessions)
    app.router.add_post("/api/genai-sessions", create_session)
    app.router.add_get("/api/genai-sessions/{session_id}", get_session)
    app.router.add_get("/api/genai-sessions/{session_id}/messages", list_messages)
    app.router.add_post("/api/genai-sessions/{session_id}/messages", create_message)
