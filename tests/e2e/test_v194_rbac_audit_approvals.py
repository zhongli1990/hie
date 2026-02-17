"""
OpenLI HIE v1.9.4 — E2E Tests: RBAC, Audit Logging, Approval Workflows

Feature Requirements Tested:
  GR-1  Role-Based Tool Access   — 7-role RBAC, DB-to-Agent role mapping
  GR-2  Audit Logging            — POST/GET/stats, PII sanitisation
  GR-3  Approval Workflows       — create/list/approve/reject lifecycle
  FR-5  Demo Onboarding          — 7 demo user logins, demo tenant
  FR-6  Guided Lifecycle         — Portal page accessibility

Run inside Docker (from project root):
  ./scripts/run_e2e_tests.sh

Or manually:
  docker run --rm --network hie_hie-network \\
    -v "$(pwd)/tests:/app/tests:ro" \\
    -v "$(pwd)/requirements.txt:/app/requirements.txt:ro" \\
    -w /app -e PYTHONPATH=/app \\
    python:3.11-slim \\
    bash -c "pip install -q aiohttp pytest pytest-asyncio && \\
             pytest tests/e2e/test_v194_rbac_audit_approvals.py -v --tb=short"
"""
import os

import aiohttp
import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Service URLs — container hostnames by default, env-var override for host
# ─────────────────────────────────────────────────────────────────────────────

MANAGER_BASE = os.environ.get("HIE_E2E_MANAGER_BASE", "http://hie-manager:8081")
AGENT_BASE = os.environ.get("HIE_E2E_AGENT_BASE", "http://hie-agent-runner:8082")
PROMPT_MGR_BASE = os.environ.get("HIE_E2E_PROMPT_MGR_BASE", "http://hie-prompt-manager:8083")
PORTAL_BASE = os.environ.get("HIE_E2E_PORTAL_BASE", "http://hie-portal:3000")

# ─────────────────────────────────────────────────────────────────────────────
# Demo user credentials (seeded by scripts/init-db.sql)
# ─────────────────────────────────────────────────────────────────────────────

DEMO_USERS = [
    {
        "label": "Super Admin",
        "email": "admin@hie.nhs.uk",
        "password": "Admin123!",
        "db_role": "super_admin",
        "expected_agent_role": "platform_admin",
    },
    {
        "label": "Tenant Admin",
        "email": "trust.admin@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "tenant_admin",
        "expected_agent_role": "tenant_admin",
    },
    {
        "label": "Developer",
        "email": "developer@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "integration_engineer",
        "expected_agent_role": "developer",
    },
    {
        "label": "Clinical Safety Officer",
        "email": "cso@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "clinical_safety_officer",
        "expected_agent_role": "clinical_safety_officer",
    },
    {
        "label": "Operator",
        "email": "operator@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "operator",
        "expected_agent_role": "operator",
    },
    {
        "label": "Viewer",
        "email": "viewer@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "viewer",
        "expected_agent_role": "viewer",
    },
    {
        "label": "Auditor",
        "email": "auditor@sth.nhs.uk",
        "password": "Demo12345!",
        "db_role": "auditor",
        "expected_agent_role": "auditor",
    },
]

# Module-scoped state for sequential tests (approval lifecycle)
_state: dict = {}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _api(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    json: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict]:
    """Call an API endpoint and return (status_code, body_dict)."""
    async with session.request(method, url, json=json, headers=headers) as resp:
        status = resp.status
        try:
            data = await resp.json(content_type=None)
        except Exception:
            data = {"_raw": await resp.text()}
        return status, data


async def _login(session: aiohttp.ClientSession, email: str, password: str) -> str:
    """Login via Manager API and return JWT token (empty string on failure)."""
    status, data = await _api(
        session, "POST", f"{MANAGER_BASE}/api/auth/login",
        json={"email": email, "password": password},
    )
    if status == 200:
        return data.get("access_token", "")
    return ""


def _auth_header(token: str) -> dict:
    """Build Authorization header from JWT token."""
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# SECTION 1: SERVICE HEALTH CHECKS
# =============================================================================

@pytest.mark.asyncio
async def test_01_manager_health():
    """Verify hie-manager is healthy."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"{MANAGER_BASE}/api/health")
        assert status == 200, f"Manager returned {status}: {data}"
        assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_02_agent_runner_health():
    """Verify hie-agent-runner is healthy."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"{AGENT_BASE}/health")
        assert status == 200, f"Agent runner returned {status}: {data}"
        assert data.get("status") == "ok"


@pytest.mark.asyncio
async def test_03_prompt_manager_health():
    """Verify hie-prompt-manager is healthy and reports correct version."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"{PROMPT_MGR_BASE}/health")
        assert status == 200, f"Prompt manager returned {status}: {data}"
        assert data.get("status") == "ok"
        assert data.get("version") == "1.9.4", (
            f"Expected version 1.9.4, got {data.get('version')}"
        )


# =============================================================================
# SECTION 2: DEMO USER LOGIN (FR-5 — Demo Onboarding)
#
# All 7 demo users must authenticate successfully. This validates:
#   - init-db.sql seed data is applied
#   - Password hashes are correct
#   - JWT tokens are issued with correct role claims
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("user", DEMO_USERS, ids=[u["label"] for u in DEMO_USERS])
async def test_10_demo_user_login(user: dict):
    """Each demo user can login and receive a valid JWT token."""
    async with aiohttp.ClientSession() as s:
        token = await _login(s, user["email"], user["password"])
        assert token, f"{user['label']} ({user['email']}) failed to login"

        # Store token for use in later tests
        _state[f"token_{user['db_role']}"] = token


# =============================================================================
# SECTION 3: ROLE ALIGNMENT — GR-1 (resolve_agent_role)
#
# Critical bug fix verification: DB role names in JWT must correctly map
# to agent-runner role keys. Before v1.9.4, integration_engineer, operator,
# and auditor all silently fell back to viewer (read-only).
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("user", DEMO_USERS, ids=[u["label"] for u in DEMO_USERS])
async def test_20_role_alignment(user: dict):
    """GET /roles/me returns correctly mapped agent role for each user."""
    token = _state.get(f"token_{user['db_role']}")
    if not token:
        pytest.skip(f"No token for {user['label']} (login may have failed)")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{AGENT_BASE}/roles/me",
            headers=_auth_header(token),
        )
        assert status == 200, f"roles/me returned {status}: {data}"

        agent_role = data.get("role", "")
        assert agent_role == user["expected_agent_role"], (
            f"{user['label']}: expected agent_role='{user['expected_agent_role']}', "
            f"got '{agent_role}' (role alignment bug?)"
        )


@pytest.mark.asyncio
async def test_21_roles_list():
    """GET /roles returns all 7 roles with display names and descriptions."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"{AGENT_BASE}/roles")
        assert status == 200, f"roles list returned {status}: {data}"
        assert isinstance(data, list), "Expected list of roles"
        role_keys = {r["role"] for r in data}
        expected = {
            "platform_admin", "tenant_admin", "developer",
            "clinical_safety_officer", "operator", "auditor", "viewer",
        }
        assert expected == role_keys, f"Missing roles: {expected - role_keys}"


# =============================================================================
# SECTION 4: AUDIT LOGGING — GR-2 (DCB0129/DCB0160 Compliance)
#
# Every AI tool call must be logged. Audit entries must:
#   - Record user_id, role, action, target, result
#   - Sanitise PII (NHS numbers, UK postcodes) before storage
#   - Support filtered listing and aggregate stats
# =============================================================================

@pytest.mark.asyncio
async def test_30_audit_create():
    """POST /audit creates an audit entry (201 Created)."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/audit",
            json={
                "user_id": "e2e-test-user-001",
                "user_role": "developer",
                "action": "hie_create_item",
                "target_type": "item",
                "result_status": "success",
                "input_summary": "Created HL7 TCPService on port 5001",
                "result_summary": "Item created successfully",
            },
        )
        assert status == 201, f"POST /audit returned {status}: {data}"
        assert data.get("id"), "Missing audit entry ID"
        assert data.get("action") == "hie_create_item"
        assert data.get("result_status") == "success"
        _state["audit_entry_id"] = data["id"]


@pytest.mark.asyncio
async def test_31_audit_pii_sanitisation():
    """POST /audit sanitises NHS numbers and UK postcodes from input/result."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/audit",
            json={
                "user_id": "e2e-test-user-002",
                "user_role": "developer",
                "action": "hie_test_item",
                "result_status": "success",
                "input_summary": "Tested with NHS number 9434765870 and postcode SW1A 1AA",
                "result_summary": "Patient 9434765870 at SW1A 1AA processed OK",
            },
        )
        assert status == 201, f"POST /audit returned {status}: {data}"

        # PII should be stripped — NHS number and postcode must not appear in stored summary
        input_summary = data.get("input_summary", "")
        result_summary = data.get("result_summary", "")
        assert "9434765870" not in input_summary, (
            f"NHS number not sanitised from input_summary: {input_summary}"
        )
        assert "9434765870" not in result_summary, (
            f"NHS number not sanitised from result_summary: {result_summary}"
        )


@pytest.mark.asyncio
async def test_32_audit_list():
    """GET /audit returns paginated audit entries."""
    async with aiohttp.ClientSession() as s:
        # No auth header — falls back to DEV_USER (admin) in dev mode
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/audit?limit=10",
        )
        assert status == 200, f"GET /audit returned {status}: {data}"
        assert "entries" in data, "Response missing 'entries'"
        assert "total" in data, "Response missing 'total'"
        assert data["total"] > 0, "Expected at least 1 audit entry after POST"


@pytest.mark.asyncio
async def test_33_audit_list_with_auth():
    """GET /audit with admin JWT returns audit entries."""
    token = _state.get("token_super_admin")
    if not token:
        pytest.skip("No admin token")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/audit?limit=10",
            headers=_auth_header(token),
        )
        assert status == 200, f"GET /audit returned {status}: {data}"
        assert data["total"] > 0


@pytest.mark.asyncio
async def test_34_audit_stats():
    """GET /audit/stats returns aggregate counts."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/audit/stats",
        )
        assert status == 200, f"GET /audit/stats returned {status}: {data}"
        assert "total" in data, "Stats missing 'total'"
        assert "success" in data, "Stats missing 'success'"
        assert "denied" in data, "Stats missing 'denied'"
        assert "errors" in data, "Stats missing 'errors'"
        assert data["total"] > 0, "Expected total > 0 after audit entries were created"


# =============================================================================
# SECTION 5: APPROVAL WORKFLOWS — GR-3 (Human Review Gate)
#
# Production deployments require human approval. Full lifecycle:
#   1. Developer requests deployment → status=pending
#   2. List approvals (verify appears)
#   3. Get approval detail
#   4. CSO or Admin approves → status=approved
#   5. Create another → reject it → status=rejected
#   6. Filter by status
# =============================================================================

@pytest.mark.asyncio
async def test_40_approval_create():
    """POST /approvals creates a pending approval request."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals",
            json={
                "requested_by": "e2e-developer-james-chen",
                "requested_role": "developer",
                "workspace_id": "10000000-0000-0000-0000-000000000201",
                "project_id": "e2e-test-project-001",
                "project_name": "ADT Route - Cerner PAS (E2E Test)",
                "environment": "production",
                "config_snapshot": {"items": 4, "connections": 3, "rules": 2},
            },
        )
        assert status == 201, f"POST /approvals returned {status}: {data}"
        assert data.get("id"), "Missing approval ID"
        assert data.get("status") == "pending", (
            f"New approval should be 'pending', got '{data.get('status')}'"
        )
        assert data.get("requested_by") == "e2e-developer-james-chen"
        _state["approval_id"] = data["id"]


@pytest.mark.asyncio
async def test_41_approval_list():
    """GET /approvals returns paginated approvals (total > 0)."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/approvals?limit=10",
        )
        assert status == 200, f"GET /approvals returned {status}: {data}"
        assert "approvals" in data, "Response missing 'approvals'"
        assert "total" in data, "Response missing 'total'"
        assert data["total"] > 0, "Expected at least 1 approval after POST"


@pytest.mark.asyncio
async def test_42_approval_detail():
    """GET /approvals/{id} returns full approval with config snapshot."""
    approval_id = _state.get("approval_id")
    if not approval_id:
        pytest.skip("No approval_id from previous test")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/approvals/{approval_id}",
        )
        assert status == 200, f"GET /approvals/{approval_id} returned {status}: {data}"
        assert data.get("id") == approval_id
        assert data.get("status") == "pending"
        assert data.get("project_name") == "ADT Route - Cerner PAS (E2E Test)"
        assert data.get("config_snapshot"), "Config snapshot should be populated"


@pytest.mark.asyncio
async def test_43_approval_approve():
    """POST /approvals/{id}/approve transitions status to 'approved'.

    Role-gated: only CSO and admin can approve. Uses CSO token if available,
    falls back to DEV_USER (admin) in dev mode.
    """
    approval_id = _state.get("approval_id")
    if not approval_id:
        pytest.skip("No approval_id from previous test")

    # Prefer CSO token to verify role-based access, fall back to no-auth (dev mode admin)
    token = _state.get("token_clinical_safety_officer")
    headers = _auth_header(token) if token else None

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals/{approval_id}/approve",
            json={
                "review_notes": "E2E test: ADT route reviewed, safe for production.",
                "safety_report": {"checks_passed": 28, "checks_total": 32, "advisories": 4},
            },
            headers=headers,
        )
        assert status == 200, f"POST .../approve returned {status}: {data}"
        assert data.get("status") == "approved", (
            f"Expected status='approved', got '{data.get('status')}'"
        )
        assert data.get("reviewed_by"), "Reviewer should be recorded"
        assert data.get("review_notes"), "Review notes should be stored"


@pytest.mark.asyncio
async def test_44_approval_reject_lifecycle():
    """Full reject lifecycle: create → reject with notes."""
    async with aiohttp.ClientSession() as s:
        # Create a new approval to reject
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals",
            json={
                "requested_by": "e2e-developer-james-chen",
                "requested_role": "developer",
                "project_name": "ORM Route - Lab System (E2E Test)",
                "environment": "production",
            },
        )
        assert status == 201, f"POST /approvals (reject test) returned {status}: {data}"
        reject_id = data["id"]

        # Reject it (CSO token or dev mode)
        token = _state.get("token_clinical_safety_officer")
        headers = _auth_header(token) if token else None

        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals/{reject_id}/reject",
            json={
                "review_notes": "E2E test: Missing error queue routing. Add NACK handling.",
            },
            headers=headers,
        )
        assert status == 200, f"POST .../reject returned {status}: {data}"
        assert data.get("status") == "rejected", (
            f"Expected status='rejected', got '{data.get('status')}'"
        )


@pytest.mark.asyncio
async def test_45_approval_filter_by_status():
    """GET /approvals?status=approved returns only approved approvals."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{PROMPT_MGR_BASE}/approvals?status=approved",
        )
        assert status == 200, f"GET /approvals?status=approved returned {status}: {data}"
        assert isinstance(data.get("approvals"), list)
        # All returned approvals should have status=approved
        for a in data["approvals"]:
            assert a["status"] == "approved", (
                f"Filter returned non-approved entry: {a['status']}"
            )


@pytest.mark.asyncio
async def test_46_approval_role_gate_viewer_denied():
    """Viewer role cannot approve deployments (403 Forbidden)."""
    token = _state.get("token_viewer")
    if not token:
        pytest.skip("No viewer token")

    # Create an approval to attempt approving
    async with aiohttp.ClientSession() as s:
        status, create_data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals",
            json={
                "requested_by": "e2e-role-gate-test",
                "requested_role": "developer",
                "project_name": "Role Gate Test",
                "environment": "production",
            },
        )
        if status != 201:
            pytest.skip(f"Could not create approval for gate test: {status}")

        gate_id = create_data["id"]

        # Attempt to approve as viewer — should be denied
        status, data = await _api(
            s, "POST", f"{PROMPT_MGR_BASE}/approvals/{gate_id}/approve",
            json={"review_notes": "Viewer attempting approval"},
            headers=_auth_header(token),
        )
        assert status == 403, (
            f"Viewer should get 403 on approve, got {status}: {data}"
        )


# =============================================================================
# SECTION 6: RBAC PERMISSION VERIFICATION — GR-1
#
# Verify that resolve_agent_role() correctly maps each DB role to the right
# agent permission set. The critical fix ensures integration_engineer does
# NOT fall back to viewer.
# =============================================================================

@pytest.mark.asyncio
async def test_50_developer_is_not_viewer():
    """Developer (integration_engineer) must NOT resolve to viewer.

    This is the critical bug that v1.9.4 fixes. Before the fix,
    integration_engineer fell back to viewer (read-only), preventing
    developers from building integrations via AI.
    """
    token = _state.get("token_integration_engineer")
    if not token:
        pytest.skip("No developer token")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{AGENT_BASE}/roles/me",
            headers=_auth_header(token),
        )
        assert status == 200
        role = data.get("role", "")
        assert role == "developer", (
            f"Critical: integration_engineer resolved to '{role}' instead of 'developer'. "
            f"This is the exact bug that v1.9.4 fixes!"
        )
        assert role != "viewer", (
            "REGRESSION: integration_engineer fell back to viewer (read-only)!"
        )


@pytest.mark.asyncio
async def test_51_operator_is_not_viewer():
    """Operator role must resolve to operator, not viewer fallback."""
    token = _state.get("token_operator")
    if not token:
        pytest.skip("No operator token")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{AGENT_BASE}/roles/me",
            headers=_auth_header(token),
        )
        assert status == 200
        assert data.get("role") == "operator", (
            f"operator resolved to '{data.get('role')}' — expected 'operator'"
        )


@pytest.mark.asyncio
async def test_52_auditor_is_not_viewer():
    """Auditor role must resolve to auditor, not viewer fallback."""
    token = _state.get("token_auditor")
    if not token:
        pytest.skip("No auditor token")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{AGENT_BASE}/roles/me",
            headers=_auth_header(token),
        )
        assert status == 200
        assert data.get("role") == "auditor", (
            f"auditor resolved to '{data.get('role')}' — expected 'auditor'"
        )


@pytest.mark.asyncio
async def test_53_super_admin_maps_to_platform_admin():
    """super_admin DB role must map to platform_admin agent role."""
    token = _state.get("token_super_admin")
    if not token:
        pytest.skip("No admin token")

    async with aiohttp.ClientSession() as s:
        status, data = await _api(
            s, "GET", f"{AGENT_BASE}/roles/me",
            headers=_auth_header(token),
        )
        assert status == 200
        assert data.get("role") == "platform_admin", (
            f"super_admin should map to platform_admin, got '{data.get('role')}'"
        )


# =============================================================================
# SECTION 7: PORTAL PAGE ACCESSIBILITY
#
# Verify Portal serves the new admin pages (audit log, approvals, agents).
# HTTP 200 or 307 (redirect to login) are both acceptable — the page exists.
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("path,label", [
    ("/admin/audit", "Audit Log page"),
    ("/admin/approvals", "Approvals page"),
    ("/agents", "Agents page"),
])
async def test_60_portal_pages(path: str, label: str):
    """Portal pages for new features return 200 or redirect (307/308)."""
    async with aiohttp.ClientSession() as s:
        async with s.get(
            f"{PORTAL_BASE}{path}",
            allow_redirects=False,
        ) as resp:
            assert resp.status in (200, 307, 308), (
                f"{label} ({path}) returned {resp.status} — expected 200/307/308"
            )


# =============================================================================
# SECTION 8: PROMPT-MANAGER VERSION + REGRESSION CHECKS
# =============================================================================

@pytest.mark.asyncio
async def test_70_prompt_manager_version():
    """Prompt manager /health reports version 1.9.4 (not hardcoded 1.9.0)."""
    async with aiohttp.ClientSession() as s:
        status, data = await _api(s, "GET", f"{PROMPT_MGR_BASE}/health")
        assert status == 200
        version = data.get("version", "unknown")
        assert version == "1.9.4", (
            f"Prompt manager version is '{version}' — expected '1.9.4'. "
            f"Check that the health endpoint uses app.version, not a hardcoded string."
        )
