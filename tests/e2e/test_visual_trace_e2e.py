"""
End-to-End tests for Visual Trace with the new message model.

Tests the complete pipeline:
  1. Migration check — message_headers + message_bodies tables exist
  2. Send HL7 ADT^A01 via MLLP to a running HL7TCPService
  3. Verify message_headers rows created (per-leg)
  4. Verify message_bodies row created (HL7 body)
  5. Verify GET /api/sessions/{session_id}/trace returns v2 trace
  6. Verify trace structure: items sorted, messages are arrows, latency computed

Prerequisites:
  - Docker Compose stack running (hie-manager, hie-postgres, hie-mllp-echo)
  - ADT001 project deployed and started (PAS-In → ADT_Router → EPR_Out/RIS_Out/Testharness)
  - Migration 004 applied (message_headers + message_bodies tables)

Run from host:
  pytest tests/e2e/test_visual_trace_e2e.py -v

Run from Docker:
  docker compose exec hie-manager pytest tests/e2e/test_visual_trace_e2e.py -v

Environment variables:
  HIE_E2E_MANAGER_BASE  — Manager API base URL (default: http://localhost:9302)
  HIE_E2E_MLLP_HOST     — MLLP host for PAS-In service (default: localhost)
  HIE_E2E_MLLP_PORT     — MLLP port for PAS-In service (default: 10001)
  HIE_E2E_DB_DSN        — PostgreSQL DSN (default: postgresql://hie:hie_password@localhost:9310/hie)
"""

from __future__ import annotations

import asyncio
import os
import socket
import time
from datetime import datetime
from uuid import UUID

import aiohttp
import pytest

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
MANAGER_BASE = os.environ.get("HIE_E2E_MANAGER_BASE", "http://localhost:9302")
MLLP_HOST = os.environ.get("HIE_E2E_MLLP_HOST", "localhost")
MLLP_PORT = int(os.environ.get("HIE_E2E_MLLP_PORT", "10001"))

# Optional: direct DB verification (requires asyncpg)
DB_DSN = os.environ.get(
    "HIE_E2E_DB_DSN",
    "postgresql://hie:hie_password@localhost:9310/hie",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_hl7_adt_a01(control_id: str = "TESTMSG001") -> str:
    """Build a minimal HL7 v2.4 ADT^A01 message."""
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    segments = [
        f"MSH|^~\\&|PAS|BHR|EPR|BHR|{ts}||ADT^A01^ADT_A01|{control_id}|P|2.4",
        f"EVN|A01|{ts}",
        f"PID|||E2E-{control_id}^^^MRN||TestPatient^E2E^A||19900101|M|||1 Test St^^London^^E1 1AA^UK",
        f"PV1||I|WARD1^BED1^1|E|||9999^TestDoc^E2E|||MED||||||||9999^TestDoc^E2E|IP|||||||||||||||||||BHR|||||{ts}",
    ]
    return "\r".join(segments) + "\r"


def send_mllp(host: str, port: int, message: str, timeout: float = 10.0) -> str:
    """Send an HL7 message over MLLP and return the ACK."""
    frame = b"\x0b" + message.encode("ascii") + b"\x1c\x0d"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.sendall(frame)
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\x1c\x0d" in data:
                break
        return data.replace(b"\x0b", b"").replace(b"\x1c\x0d", b"").decode("ascii", errors="replace")
    finally:
        sock.close()


async def api_get_json(url: str) -> tuple[int, dict]:
    """GET a JSON endpoint and return (status, body)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            status = resp.status
            body = await resp.json(content_type=None)
            return status, body


# ---------------------------------------------------------------------------
# Optional asyncpg pool for direct DB checks
# ---------------------------------------------------------------------------
_pool = None


async def get_db_pool():
    """Lazy-init an asyncpg pool. Returns None if asyncpg not installed."""
    global _pool
    if _pool is not None:
        return _pool
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=2)
        return _pool
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manager_health():
    """Smoke: Manager API is reachable."""
    status, data = await api_get_json(f"{MANAGER_BASE}/api/health")
    assert status == 200, f"Manager unhealthy: {data}"
    assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_migration_tables_exist():
    """Verify message_headers and message_bodies tables exist in PostgreSQL."""
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    tables = await pool.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('message_headers', 'message_bodies')"
    )
    table_names = {r["tablename"] for r in tables}
    assert "message_headers" in table_names, "message_headers table missing — run migration 004"
    assert "message_bodies" in table_names, "message_bodies table missing — run migration 004"


@pytest.mark.asyncio
async def test_send_hl7_and_receive_ack():
    """Send an HL7 ADT^A01 via MLLP and verify we get an AA ACK back."""
    control_id = f"E2E-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)

    ack = send_mllp(MLLP_HOST, MLLP_PORT, msg)

    assert "MSA|" in ack, f"No MSA segment in ACK: {ack!r}"
    # Parse MSA-1 (acknowledgment code)
    msa_seg = [s for s in ack.split("\r") if s.startswith("MSA|")]
    assert len(msa_seg) == 1, f"Expected 1 MSA segment, got {len(msa_seg)}"
    ack_code = msa_seg[0].split("|")[1]
    assert ack_code in ("AA", "CA"), f"Expected AA or CA, got {ack_code}"


@pytest.mark.asyncio
async def test_message_headers_created_after_send():
    """Send HL7 and verify message_headers rows are created for each leg."""
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    control_id = f"E2E-HDR-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    # Allow async processing to complete
    await asyncio.sleep(1.0)

    # Find headers by correlation_id (= MSH-10 control ID)
    headers = await pool.fetch(
        "SELECT id, session_id, source_config_name, target_config_name, message_type, status "
        "FROM message_headers WHERE correlation_id = $1 ORDER BY sequence_num",
        control_id,
    )

    # Expect at least: PAS-In→ADT_Router (the inbound leg)
    assert len(headers) >= 1, f"No message_headers found for control_id={control_id}"

    # First leg should be service → process
    first = headers[0]
    assert first["source_config_name"] == "PAS-In"
    assert first["target_config_name"] == "ADT_Router"
    assert first["message_type"] is not None
    assert "ADT" in (first["message_type"] or "")

    # Session ID should have SES- prefix
    assert first["session_id"].startswith("SES-"), f"Bad session_id format: {first['session_id']}"


@pytest.mark.asyncio
async def test_message_bodies_created_after_send():
    """Send HL7 and verify a message_bodies row exists with HL7 metadata."""
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    control_id = f"E2E-BODY-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    await asyncio.sleep(1.0)

    # Find the body via the header's message_body_id
    body = await pool.fetchrow(
        """
        SELECT b.id, b.body_class_name, b.content_type, b.content_size,
               b.hl7_message_type, b.hl7_control_id, b.hl7_doc_type
        FROM message_bodies b
        JOIN message_headers h ON h.message_body_id = b.id
        WHERE h.correlation_id = $1
        LIMIT 1
        """,
        control_id,
    )

    assert body is not None, f"No message_bodies found for control_id={control_id}"
    assert body["body_class_name"] == "EnsLib.HL7.Message"
    assert body["content_size"] > 0
    assert body["hl7_control_id"] == control_id
    assert "ADT" in (body["hl7_message_type"] or "")


@pytest.mark.asyncio
async def test_trace_api_returns_v2():
    """Send HL7, then GET /api/sessions/{session_id}/trace and verify v2 structure."""
    pool = await get_db_pool()

    control_id = f"E2E-TRACE-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    await asyncio.sleep(1.0)

    # Get session_id — either from DB or by listing recent sessions
    session_id = None
    if pool:
        row = await pool.fetchrow(
            "SELECT session_id FROM message_headers WHERE correlation_id = $1 LIMIT 1",
            control_id,
        )
        if row:
            session_id = row["session_id"]

    if not session_id:
        # Fallback: list sessions from API and pick the most recent
        status, data = await api_get_json(f"{MANAGER_BASE}/api/sessions/recent")
        if status == 200 and data.get("sessions"):
            session_id = data["sessions"][0].get("session_id")

    assert session_id is not None, "Could not determine session_id for sent message"

    # GET trace
    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{session_id}/trace")

    assert status == 200, f"Trace API returned {status}: {trace}"
    assert trace["trace_version"] == "v2"
    assert trace["session_id"] == session_id


@pytest.mark.asyncio
async def test_trace_items_sorted_correctly():
    """Verify trace items are sorted: service → process → operation."""
    pool = await get_db_pool()

    control_id = f"E2E-SORT-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    await asyncio.sleep(1.0)

    session_id = None
    if pool:
        row = await pool.fetchrow(
            "SELECT session_id FROM message_headers WHERE correlation_id = $1 LIMIT 1",
            control_id,
        )
        if row:
            session_id = row["session_id"]

    assert session_id is not None, "Could not determine session_id"

    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{session_id}/trace")
    assert status == 200

    items = trace["items"]
    assert len(items) >= 2, f"Expected at least 2 items, got {len(items)}"

    # Verify ordering: all services before processes before operations
    type_order = {"service": 0, "process": 1, "operation": 2}
    orders = [type_order.get(i["item_type"], 3) for i in items]
    assert orders == sorted(orders), f"Items not sorted correctly: {[(i['item_name'], i['item_type']) for i in items]}"


@pytest.mark.asyncio
async def test_trace_messages_are_arrows():
    """Verify each trace message has source/target (= one arrow on diagram)."""
    pool = await get_db_pool()

    control_id = f"E2E-ARROW-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    await asyncio.sleep(1.0)

    session_id = None
    if pool:
        row = await pool.fetchrow(
            "SELECT session_id FROM message_headers WHERE correlation_id = $1 LIMIT 1",
            control_id,
        )
        if row:
            session_id = row["session_id"]

    assert session_id is not None, "Could not determine session_id"

    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{session_id}/trace")
    assert status == 200

    messages = trace["messages"]
    assert len(messages) >= 1, "No messages in trace"

    for m in messages:
        # Each message must have source and target (= arrow endpoints)
        assert m.get("source_config_name"), f"Message {m.get('id')} missing source_config_name"
        assert m.get("target_config_name"), f"Message {m.get('id')} missing target_config_name"
        # Must have a status
        assert m.get("status") in ("Created", "Queued", "Completed", "Error", "Discarded"), \
            f"Unexpected status: {m.get('status')}"
        # Must have time_created
        assert m.get("time_created") is not None


@pytest.mark.asyncio
async def test_trace_time_range():
    """Verify trace has valid started_at / ended_at time range."""
    pool = await get_db_pool()

    control_id = f"E2E-TIME-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    await asyncio.sleep(1.0)

    session_id = None
    if pool:
        row = await pool.fetchrow(
            "SELECT session_id FROM message_headers WHERE correlation_id = $1 LIMIT 1",
            control_id,
        )
        if row:
            session_id = row["session_id"]

    assert session_id is not None, "Could not determine session_id"

    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{session_id}/trace")
    assert status == 200

    assert trace["started_at"] is not None, "started_at is None"
    assert trace["ended_at"] is not None, "ended_at is None"

    started = datetime.fromisoformat(trace["started_at"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(trace["ended_at"].replace("Z", "+00:00"))
    assert ended >= started, f"ended_at ({ended}) < started_at ({started})"


@pytest.mark.asyncio
async def test_trace_v1_fallback_by_session_id():
    """Old portal_messages with SES- session_id should return v1 trace."""
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    # Find an old session that exists in portal_messages
    row = await pool.fetchrow(
        "SELECT session_id FROM portal_messages WHERE session_id IS NOT NULL LIMIT 1"
    )
    if not row:
        pytest.skip("No portal_messages with session_id found")

    old_session_id = row["session_id"]
    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{old_session_id}/trace")

    assert status == 200, f"V1 fallback failed for session_id={old_session_id}: {trace}"
    assert trace["trace_version"] == "v1"
    assert len(trace["messages"]) >= 1


@pytest.mark.asyncio
async def test_trace_v1_fallback_by_message_id():
    """Old portal_messages with NULL session_id should be found by message id."""
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    # Find an old message that has NULL session_id
    row = await pool.fetchrow(
        "SELECT id::text FROM portal_messages WHERE session_id IS NULL LIMIT 1"
    )
    if not row:
        pytest.skip("No portal_messages with NULL session_id found")

    msg_id = row["id"]
    status, trace = await api_get_json(f"{MANAGER_BASE}/api/sessions/{msg_id}/trace")

    assert status == 200, f"V1 id-fallback failed for msg_id={msg_id}: {trace}"
    assert trace["trace_version"] == "v1"
    assert len(trace["messages"]) >= 1


@pytest.mark.asyncio
async def test_trace_404_for_nonexistent_session():
    """GET /api/sessions/{bad_id}/trace returns 404, not 500."""
    status, data = await api_get_json(f"{MANAGER_BASE}/api/sessions/SES-00000000-0000-0000-0000-000000000000/trace")
    assert status == 404, f"Expected 404 for nonexistent session, got {status}: {data}"


@pytest.mark.asyncio
async def test_full_adt_pipeline_leg_count():
    """
    Full pipeline test: PAS-In → ADT_Router → [EPR_Out, RIS_Out, Testharness].

    Verifies the correct number of message_headers legs are created
    for a complete ADT routing pipeline.
    """
    pool = await get_db_pool()
    if pool is None:
        pytest.skip("asyncpg not available — skipping direct DB check")

    control_id = f"E2E-FULL-{int(time.time())}"
    msg = build_hl7_adt_a01(control_id)
    send_mllp(MLLP_HOST, MLLP_PORT, msg)

    # Give the full pipeline time to complete (routing + outbound sends)
    await asyncio.sleep(3.0)

    headers = await pool.fetch(
        """
        SELECT source_config_name, target_config_name, message_type, status
        FROM message_headers
        WHERE session_id = (
            SELECT session_id FROM message_headers WHERE correlation_id = $1 LIMIT 1
        )
        ORDER BY sequence_num
        """,
        control_id,
    )

    # Expected legs (depends on routing rules and which operations are reachable):
    #   1. PAS-In → ADT_Router (ADT_A01)
    #   2+ ADT_Router → each target operation (ADT_A01)
    #   ACK legs from operations that successfully connect
    assert len(headers) >= 2, (
        f"Expected at least 2 legs (service→router + router→operation), "
        f"got {len(headers)}: {[(h['source_config_name'], h['target_config_name'], h['message_type']) for h in headers]}"
    )

    # First leg is always PAS-In → ADT_Router
    assert headers[0]["source_config_name"] == "PAS-In"
    assert headers[0]["target_config_name"] == "ADT_Router"

    # All legs should be Completed or Error (not stuck in Created)
    for h in headers:
        assert h["status"] in ("Completed", "Error"), (
            f"Leg {h['source_config_name']}→{h['target_config_name']} stuck in status={h['status']}"
        )


# ---------------------------------------------------------------------------
# Cleanup helper (optional, for repeated test runs)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="session")
def _cleanup_info():
    """Print cleanup command after test session."""
    yield
    print(
        "\n[Cleanup] To remove E2E test messages:\n"
        f"  docker exec hie-postgres psql -U hie -d hie -c "
        "\"DELETE FROM message_headers WHERE correlation_id LIKE 'E2E-%'; "
        "DELETE FROM message_bodies WHERE hl7_control_id LIKE 'E2E-%';\""
    )
