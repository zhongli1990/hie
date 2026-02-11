"""
E2E Tests: Agent Tools → HIE Manager API → Engine

Verifies the full pipeline that the GenAI agent uses to build integrations:
  1. Create workspace
  2. Create project
  3. Create items (service, process, operation)
  4. Create connections
  5. Create routing rules
  6. Deploy project
  7. Start project
  8. Check status
  9. Send test message
  10. Stop project
  11. Cleanup

Run inside Docker:
  docker compose exec test pytest tests/e2e/test_agent_tools_e2e.py -v

Or from host (if Manager API exposed on 9302):
  HIE_E2E_MANAGER_BASE=http://localhost:9302 pytest tests/e2e/test_agent_tools_e2e.py -v
"""
import os
import uuid

import aiohttp
import pytest

MANAGER_BASE = os.environ.get("HIE_E2E_MANAGER_BASE", "http://hie-manager:8081")

# Track IDs across tests (module-scoped fixtures)
_state: dict = {}


async def _api(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    json: dict | None = None,
) -> tuple[int, dict]:
    """Helper to call Manager API and return (status, body)."""
    url = f"{MANAGER_BASE}{path}"
    async with session.request(method, url, json=json) as resp:
        status = resp.status
        try:
            data = await resp.json(content_type=None)
        except Exception:
            data = {"raw": await resp.text()}
        return status, data


# ─── Health Check ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_00_manager_healthy():
    """Verify Manager API is reachable before running the pipeline."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", "/api/health")
        assert status == 200, f"Manager unhealthy: {data}"
        assert data.get("status") == "healthy"


# ─── Step 1: Create Workspace ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_01_create_workspace():
    """Agent tool: hie_create_workspace."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", "/api/workspaces", {
            "name": f"e2e_test_{uuid.uuid4().hex[:8]}",
            "display_name": "E2E Test Workspace",
            "description": "Created by agent tools E2E test",
        })
        assert status in (200, 201), f"Create workspace failed: {data}"
        ws = data.get("data") or data
        _state["workspace_id"] = str(ws["id"])


# ─── Step 2: List Workspaces ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_02_list_workspaces():
    """Agent tool: hie_list_workspaces."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", "/api/workspaces")
        assert status == 200
        workspaces = data if isinstance(data, list) else data.get("data", data.get("workspaces", []))
        assert len(workspaces) > 0, "No workspaces found"


# ─── Step 3: Create Project ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_03_create_project():
    """Agent tool: hie_create_project."""
    ws_id = _state["workspace_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/workspaces/{ws_id}/projects", {
            "name": "ADT_E2E_Test",
            "display_name": "ADT E2E Test Integration",
            "description": "E2E test: ADT route with service → process → operation",
        })
        assert status in (200, 201), f"Create project failed: {data}"
        proj = data.get("data") or data
        _state["project_id"] = str(proj["id"])


# ─── Step 4: Get Project ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_04_get_project():
    """Agent tool: hie_get_project."""
    ws_id = _state["workspace_id"]
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"/api/workspaces/{ws_id}/projects/{proj_id}")
        assert status == 200, f"Get project failed: {data}"


# ─── Step 5: List Item Types ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_05_list_item_types():
    """Agent tool: hie_list_item_types."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", "/api/item-types")
        assert status == 200, f"List item types failed: {data}"
        types = data if isinstance(data, list) else data.get("data", data.get("item_types", []))
        assert len(types) > 0, "No item types registered in ClassRegistry"


# ─── Step 6: Create Items ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_06_create_inbound_service():
    """Agent tool: hie_create_item (service)."""
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/items", {
            "name": "PAS.ADT.Receiver",
            "item_type": "service",
            "class_name": "li.hosts.hl7.HL7TCPService",
            "enabled": True,
            "pool_size": 1,
            "adapter_settings": {"Port": "12575", "IPAddress": "0.0.0.0"},
            "host_settings": {
                "MessageSchemaCategory": "2.4",
                "TargetConfigNames": "ADT.Router",
                "AckMode": "App",
            },
        })
        assert status in (200, 201), f"Create service failed: {data}"
        item = data.get("data") or data
        _state["service_id"] = str(item["id"])


@pytest.mark.asyncio
async def test_07_create_routing_process():
    """Agent tool: hie_create_item (process)."""
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/items", {
            "name": "ADT.Router",
            "item_type": "process",
            "class_name": "li.hosts.routing.HL7RoutingEngine",
            "enabled": True,
            "pool_size": 1,
            "host_settings": {"BusinessRuleName": "ADT_E2E_Rules"},
        })
        assert status in (200, 201), f"Create process failed: {data}"
        item = data.get("data") or data
        _state["process_id"] = str(item["id"])


@pytest.mark.asyncio
async def test_08_create_outbound_operation():
    """Agent tool: hie_create_item (operation)."""
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/items", {
            "name": "RIS.HL7.Sender",
            "item_type": "operation",
            "class_name": "li.hosts.hl7.HL7TCPOperation",
            "enabled": True,
            "pool_size": 1,
            "adapter_settings": {"IPAddress": "mllp-echo", "Port": "2575"},
            "host_settings": {"ReplyCodeActions": ":?R=F,:?E=S,:~=S,:?A=C,:*=S"},
        })
        assert status in (200, 201), f"Create operation failed: {data}"
        item = data.get("data") or data
        _state["operation_id"] = str(item["id"])


# ─── Step 7: Create Connections ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_09_create_connections():
    """Agent tool: hie_create_connection (service→process, process→operation)."""
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        # Service → Process
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/connections", {
            "source_item_id": _state["service_id"],
            "target_item_id": _state["process_id"],
            "connection_type": "standard",
        })
        assert status in (200, 201), f"Create connection 1 failed: {data}"

        # Process → Operation
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/connections", {
            "source_item_id": _state["process_id"],
            "target_item_id": _state["operation_id"],
            "connection_type": "standard",
        })
        assert status in (200, 201), f"Create connection 2 failed: {data}"


# ─── Step 8: Create Routing Rule ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_10_create_routing_rule():
    """Agent tool: hie_create_routing_rule."""
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/projects/{proj_id}/routing-rules", {
            "name": "Route ADT to RIS",
            "priority": 1,
            "enabled": True,
            "condition_expression": '{MSH-9.1} = "ADT"',
            "action": "send",
            "target_items": ["RIS.HL7.Sender"],
        })
        assert status in (200, 201), f"Create routing rule failed: {data}"


# ─── Step 9: Deploy Project ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_11_deploy_project():
    """Agent tool: hie_deploy_project."""
    ws_id = _state["workspace_id"]
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/deploy", {
            "start_after_deploy": False,
        })
        assert status in (200, 201, 202), f"Deploy failed: {data}"


# ─── Step 10: Start Project ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_12_start_project():
    """Agent tool: hie_start_project."""
    ws_id = _state["workspace_id"]
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/start")
        assert status in (200, 202), f"Start failed: {data}"


# ─── Step 11: Check Status ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_13_project_status():
    """Agent tool: hie_project_status."""
    ws_id = _state["workspace_id"]
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"/api/workspaces/{ws_id}/projects/{proj_id}/status")
        assert status == 200, f"Status check failed: {data}"


# ─── Step 12: Stop Project ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_14_stop_project():
    """Agent tool: hie_stop_project."""
    ws_id = _state["workspace_id"]
    proj_id = _state["project_id"]
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/stop")
        assert status in (200, 202), f"Stop failed: {data}"


# ─── Cleanup ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_99_cleanup():
    """Delete test workspace and all its contents."""
    ws_id = _state.get("workspace_id")
    if not ws_id:
        pytest.skip("No workspace to clean up")
    async with aiohttp.ClientSession() as s:
        status, _ = await _api(s, "DELETE", f"/api/workspaces/{ws_id}")
        assert status in (200, 204, 404), f"Cleanup failed with status {status}"
