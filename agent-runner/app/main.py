"""
OpenLI HIE Agent Runner - Main FastAPI Application

Provides:
- Thread/Run management for agent sessions
- SSE streaming of agent events
- Skills management API
- Health check endpoint
"""

import asyncio
import json
import logging
import os
import pathlib
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import WORKSPACES_ROOT, PORT
from .agent import run_agent_loop
from .events import make_event, format_sse
from .api.skills_router import router as skills_router

logger = logging.getLogger(__name__)

HOOKS_CONFIG_PATH = os.environ.get("HOOKS_CONFIG_PATH", "/app/hooks_config.json")

# Default hooks configuration
DEFAULT_HOOKS_CONFIG: dict[str, Any] = {
    "platform": {
        "security": {
            "block_dangerous_commands": True,
            "block_path_traversal": True,
            "validate_hl7_structure": True,
            "enforce_tls": False,
            "blocked_patterns": [
                "rm -rf /", "sudo rm", "DROP TABLE", "DELETE FROM hie_",
                "curl | bash", "wget | sh", "chmod 777", "mkfs",
                "dd if=", ":(){:|:&};:", ">/dev/sda", "format c:",
                "curl | sh",
            ],
            "enabled": True,
        },
        "audit": {
            "log_all_agent_actions": True,
            "log_message_access": True,
            "log_config_changes": True,
            "enabled": True,
        },
    },
    "tenant": {
        "compliance": {
            "detect_nhs_numbers": True,
            "detect_pii": True,
            "block_external_data_transfer": False,
            "enforce_data_retention": True,
            "retention_days": 365,
            "enabled": True,
        },
        "clinical_safety": {
            "validate_message_integrity": True,
            "require_ack_confirmation": True,
            "alert_on_message_loss": True,
            "max_retry_attempts": 3,
            "enabled": True,
        },
    },
}


def _load_hooks_config() -> dict[str, Any]:
    """Load hooks config from file, falling back to defaults."""
    try:
        if os.path.exists(HOOKS_CONFIG_PATH):
            with open(HOOKS_CONFIG_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load hooks config: {e}")
    return DEFAULT_HOOKS_CONFIG.copy()


def _save_hooks_config(config: dict[str, Any]) -> None:
    """Persist hooks config to file."""
    os.makedirs(os.path.dirname(HOOKS_CONFIG_PATH) or ".", exist_ok=True)
    with open(HOOKS_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


app = FastAPI(title="OpenLI HIE Agent Runner", version="1.7.3")
app.include_router(skills_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class CreateThreadRequest(BaseModel):
    workspaceId: str | None = None
    projectId: str | None = None
    workspaceName: str | None = None
    runnerType: str | None = None
    workingDirectory: str | None = None
    skipGitRepoCheck: bool = False


class CreateThreadResponse(BaseModel):
    threadId: str


class CreateRunRequest(BaseModel):
    threadId: str
    prompt: str


class CreateRunResponse(BaseModel):
    runId: str


class ThreadRecord:
    def __init__(self, thread_id: str, working_directory: str,
                 workspace_id: str | None = None, project_id: str | None = None):
        self.thread_id = thread_id
        self.working_directory = working_directory
        self.workspace_id = workspace_id
        self.project_id = project_id


class RunRecord:
    def __init__(self, run_id: str, thread_id: str, prompt: str):
        self.run_id = run_id
        self.thread_id = thread_id
        self.prompt = prompt
        self.buffer: list[str] = []
        self.subscribers: set[asyncio.Queue[str | None]] = set()
        self.status: str = "running"


threads: dict[str, ThreadRecord] = {}
runs: dict[str, RunRecord] = {}


def must_resolve_workspace(path_str: str) -> str:
    """Ensure the path is under WORKSPACES_ROOT."""
    root = pathlib.Path(WORKSPACES_ROOT).resolve()
    path = pathlib.Path(path_str).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=400, detail="workingDirectory must be under WORKSPACES_ROOT")
    return str(path)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "hie-agent-runner", "version": "1.7.3"}


@app.post("/threads", response_model=CreateThreadResponse)
async def create_thread(req: CreateThreadRequest) -> CreateThreadResponse:
    # Derive working directory from HIE context or explicit path
    if req.workingDirectory:
        working_directory = must_resolve_workspace(req.workingDirectory)
    elif req.workspaceId:
        # Auto-provision from workspace/project IDs
        ws_name = req.workspaceName or req.workspaceId
        sub = ws_name
        if req.projectId:
            sub = f"{ws_name}/{req.projectId}"
        working_directory = must_resolve_workspace(f"{WORKSPACES_ROOT}/{sub}")
    else:
        working_directory = must_resolve_workspace(WORKSPACES_ROOT)

    os.makedirs(working_directory, exist_ok=True)

    thread_id = str(uuid.uuid4())
    threads[thread_id] = ThreadRecord(
        thread_id, working_directory,
        workspace_id=req.workspaceId,
        project_id=req.projectId
    )

    return CreateThreadResponse(threadId=thread_id)


@app.post("/runs", response_model=CreateRunResponse)
async def create_run(req: CreateRunRequest) -> CreateRunResponse:
    thread_record = threads.get(req.threadId)
    if not thread_record:
        raise HTTPException(status_code=404, detail="Thread not found")

    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    run_id = str(uuid.uuid4())
    run_record = RunRecord(run_id, req.threadId, req.prompt)
    runs[run_id] = run_record

    asyncio.create_task(_execute_run(run_record, thread_record))

    return CreateRunResponse(runId=run_id)


async def _execute_run(run_record: RunRecord, thread_record: ThreadRecord) -> None:
    """Execute the agent loop and publish events."""
    try:
        async for event_str in run_agent_loop(
            thread_record.thread_id,
            run_record.run_id,
            run_record.prompt,
            thread_record.working_directory
        ):
            run_record.buffer.append(event_str)
            for queue in run_record.subscribers:
                await queue.put(event_str)

        run_record.status = "completed"
    except Exception as e:
        error_event = format_sse(make_event(run_record.run_id, "error", {"message": str(e)}, len(run_record.buffer)))
        run_record.buffer.append(error_event)
        for queue in run_record.subscribers:
            await queue.put(error_event)
        run_record.status = "error"
    finally:
        for queue in run_record.subscribers:
            await queue.put(None)
        run_record.subscribers.clear()


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> StreamingResponse:
    run_record = runs.get(run_id)
    if not run_record:
        raise HTTPException(status_code=404, detail="Run not found")

    async def stream():
        yield ": connected\n\n"

        for event_str in run_record.buffer:
            yield event_str

        if run_record.status != "running":
            yield format_sse(make_event(
                run_id,
                "stream.closed",
                {"status": run_record.status},
                len(run_record.buffer)
            ))
            return

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        run_record.subscribers.add(queue)

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event_str = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event_str is None:
                        break
                    yield event_str
                except asyncio.TimeoutError:
                    continue
        finally:
            run_record.subscribers.discard(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ── Hooks Configuration API ──────────────────────────────────────────────────

@app.get("/hooks/config")
async def get_hooks_config() -> dict[str, Any]:
    return _load_hooks_config()


@app.post("/hooks/config")
async def save_hooks_config(request: Request) -> dict[str, Any]:
    body = await request.json()
    config = _load_hooks_config()
    if "platform" in body:
        config["platform"] = body["platform"]
    if "tenant" in body:
        config["tenant"] = body["tenant"]
    _save_hooks_config(config)
    logger.info("Hooks configuration saved")
    return {"status": "ok", "message": "Hooks configuration saved"}
