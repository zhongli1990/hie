import os

import aiohttp
import pytest


MANAGER_BASE = os.environ.get("HIE_E2E_MANAGER_BASE", "http://hie-manager:8081")
PORTAL_BASE = os.environ.get("HIE_E2E_PORTAL_BASE", "http://hie-portal:3000")
ENGINE_BASE = os.environ.get("HIE_E2E_ENGINE_BASE", "http://hie-engine:8080")


async def _get_json(session: aiohttp.ClientSession, url: str) -> tuple[int, dict]:
    async with session.get(url) as resp:
        status = resp.status
        data = await resp.json(content_type=None)
        return status, data


@pytest.mark.asyncio
async def test_manager_health() -> None:
    async with aiohttp.ClientSession() as session:
        status, data = await _get_json(session, f"{MANAGER_BASE}/api/health")
        assert status == 200
        assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_manager_core_endpoints() -> None:
    async with aiohttp.ClientSession() as session:
        for path in [
            "/api/health/services",
            "/api/stats/dashboard",
        ]:
            async with session.get(f"{MANAGER_BASE}{path}") as resp:
                assert resp.status == 200


@pytest.mark.asyncio
async def test_manager_catalog_endpoints_smoke() -> None:
    async with aiohttp.ClientSession() as session:
        for path in [
            "/api/item-types",
            "/api/workspaces",
        ]:
            async with session.get(f"{MANAGER_BASE}{path}") as resp:
                assert resp.status in {200, 401, 403}


@pytest.mark.asyncio
async def test_portal_proxy_to_manager() -> None:
    async with aiohttp.ClientSession() as session:
        status, data = await _get_json(session, f"{PORTAL_BASE}/api/health")
        assert status == 200
        assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_engine_health() -> None:
    async with aiohttp.ClientSession() as session:
        status, data = await _get_json(session, f"{ENGINE_BASE}/health")
        assert status == 200
        assert data.get("healthy") is True
