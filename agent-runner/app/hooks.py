"""
OpenLI HIE Agent Runner - Pre/Post Tool Use Hooks

Hooks provide validation and security controls for tool execution
in the healthcare integration context.

Hook Categories:
1. Security Hooks - Block dangerous operations
2. Clinical Safety Hooks - Protect patient data and clinical systems
3. Compliance Hooks - NHS/healthcare data handling policies
4. Audit Hooks - Log tool usage for compliance
5. Rate Limit Hooks - Prevent resource abuse (placeholder)
"""

from typing import Any
import json
import logging
import re
import traceback

import httpx

from .config import ENABLE_HOOKS, PROMPT_MANAGER_URL, REDIS_URL
from .roles import is_tool_permitted, is_class_name_writable, is_file_path_writable

logger = logging.getLogger(__name__)


def _deny(reason: str) -> dict[str, Any]:
    """Helper to construct a hook denial response."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


# =============================================================================
# SECURITY PATTERNS - Block dangerous operations
# =============================================================================

BLOCKED_BASH_PATTERNS = [
    # Destructive file operations
    "rm -rf /",
    "rm -rf /*",
    "sudo rm",
    # Permission escalation
    "chmod 777 /",
    "chown root",
    # Disk operations
    "> /dev/sda",
    "mkfs.",
    "dd if=",
    # Fork bomb
    ":(){:|:&};:",
    # Remote code execution
    "curl | bash",
    "wget | bash",
    "curl | sh",
    "wget | sh",
]

# Patterns that indicate path escape attempts
PATH_ESCAPE_PATTERNS = [
    "../",
    "..\\",
]

# =============================================================================
# CLINICAL SAFETY PATTERNS - Healthcare-specific protections
# =============================================================================

# Block direct database manipulation of clinical data
BLOCKED_SQL_PATTERNS = [
    "DROP TABLE",
    "TRUNCATE",
    "DELETE FROM patient",
    "DELETE FROM clinical",
    "UPDATE patient SET",
    "ALTER TABLE patient",
]

# NHS Number format detection (10-digit with check digit)
NHS_NUMBER_PATTERN = r"\b\d{3}\s?\d{3}\s?\d{4}\b"

# HL7 message safety - block modification of certain segments
PROTECTED_HL7_SEGMENTS = [
    "PID",  # Patient identification - requires clinical safety review
    "NK1",  # Next of kin
    "PV1",  # Patient visit (admission/discharge)
]

# =============================================================================
# COMPLIANCE PATTERNS - NHS Data Handling
# =============================================================================

SENSITIVE_DATA_PATTERNS = [
    # NHS Number
    r"\d{3}\s?\d{3}\s?\d{4}",
    # UK postcode (partial - first part)
    r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}",
]

# =============================================================================
# RATE LIMIT CONFIG
# =============================================================================

RATE_LIMITS = {
    "bash": 30,         # bash commands per minute
    "file_writes": 20,  # file write operations per minute
    "api_calls": 60,    # HIE API calls per minute
    "hl7_sends": 10,    # HL7 test sends per minute
}

# Map tool names to rate limit categories
TOOL_RATE_CATEGORY: dict[str, str] = {
    "bash": "bash",
    "write_file": "file_writes",
    "hie_test_item": "hl7_sends",
}
# All hie_* tools default to "api_calls" category

# Delete tools that require extra audit logging
DELETE_TOOLS = {"hie_delete_item", "hie_delete_connection", "hie_delete_routing_rule"}

# Lazy-loaded rate limiter instance
_rate_limiter = None


def _get_rate_limiter():
    """Get or create the rate limiter instance (lazy init)."""
    global _rate_limiter
    if _rate_limiter is None:
        try:
            from .rate_limiter import RateLimiter
            _rate_limiter = RateLimiter(REDIS_URL)
        except Exception as e:
            logger.warning(f"Rate limiter init failed (rate limiting disabled): {e}")
    return _rate_limiter


# =============================================================================
# PII SANITISATION & AUDIT HELPERS
# =============================================================================

_NHS_RE = re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b")
_POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE)


def _sanitise(text: str | None) -> str | None:
    """Strip NHS numbers and UK postcodes from text before audit storage."""
    if not text:
        return text
    text = _NHS_RE.sub("[NHS_NUMBER]", text)
    text = _POSTCODE_RE.sub("[POSTCODE]", text)
    return text[:2000]  # Cap length for storage


def _summarise_input(tool_input: dict) -> str:
    """Create a short, PII-free summary of tool input for audit."""
    try:
        raw = json.dumps(tool_input, default=str)
    except Exception:
        raw = str(tool_input)
    return _sanitise(raw) or ""


def _summarise_result(result: Any) -> str:
    """Create a short, PII-free summary of tool result for audit."""
    try:
        if isinstance(result, dict):
            raw = json.dumps(result, default=str)
        else:
            raw = str(result)
    except Exception:
        raw = str(result)
    return _sanitise(raw[:1000]) or ""


async def _post_audit_entry(
    user_id: str,
    user_role: str,
    action: str,
    result_status: str,
    tenant_id: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    input_summary: str | None = None,
    result_summary: str | None = None,
) -> None:
    """Fire-and-forget POST to prompt-manager /audit endpoint."""
    try:
        payload = {
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "result_status": result_status,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "run_id": run_id,
            "target_type": target_type,
            "target_id": target_id,
            "input_summary": input_summary,
            "result_summary": result_summary,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{PROMPT_MANAGER_URL}/audit", json=payload)
            if resp.status_code != 201:
                logger.warning(f"Audit POST failed ({resp.status_code}): {resp.text[:200]}")
    except Exception:
        logger.warning(f"Audit POST error: {traceback.format_exc()}")


async def _post_approval_request(
    requested_by: str,
    requested_role: str,
    tenant_id: str | None,
    workspace_id: str | None,
    project_id: str | None,
    project_name: str | None,
    environment: str,
    config_snapshot: dict | None = None,
) -> dict | None:
    """POST to prompt-manager /approvals endpoint. Returns approval record or None."""
    try:
        payload = {
            "requested_by": requested_by,
            "requested_role": requested_role,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "project_id": project_id,
            "project_name": project_name,
            "environment": environment,
            "config_snapshot": config_snapshot,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{PROMPT_MANAGER_URL}/approvals", json=payload)
            if resp.status_code == 201:
                return resp.json()
            logger.warning(f"Approval POST failed ({resp.status_code}): {resp.text[:200]}")
    except Exception:
        logger.warning(f"Approval POST error: {traceback.format_exc()}")
    return None


async def pre_tool_use_hook(input_data: dict[str, Any], tool_use_id: str, context: Any) -> dict[str, Any]:
    """
    Hook called before tool execution.

    Enforcement layers:
    1. RBAC — role-based tool permission check (defense-in-depth)
    2. Security — block dangerous bash/SQL patterns
    3. Namespace — enforce core (li.*) vs custom (custom.*) separation
    4. Tenant isolation — workspace must belong to user's tenant

    Returns empty dict to allow, or dict with hookSpecificOutput to deny.
    """
    if not ENABLE_HOOKS:
        return {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Extract role from context (passed by agent.py)
    user_role = "viewer"
    if isinstance(context, dict):
        user_role = context.get("user_role", "viewer")

    # ── RBAC: Role-based tool permission (Layer 2 — defense-in-depth) ────
    if not is_tool_permitted(tool_name, user_role):
        return _deny(
            f"Role '{user_role}' does not have permission to use '{tool_name}'. "
            f"Contact your Tenant Admin for access."
        )

    # ── Security: Block dangerous bash patterns ──────────────────────────
    if tool_name == "Bash" or tool_name == "bash":
        command = tool_input.get("command", "")
        for pattern in BLOCKED_BASH_PATTERNS:
            if pattern in command:
                return _deny(f"Blocked dangerous pattern: {pattern}")
        for pattern in BLOCKED_SQL_PATTERNS:
            if pattern.lower() in command.lower():
                return _deny(f"Blocked clinical data manipulation: {pattern}")

    # ── Security: Block file path escape attempts ────────────────────────
    if tool_name in ["Read", "Write", "Edit", "read_file", "write_file"]:
        path = tool_input.get("path", "") or tool_input.get("file_path", "")
        for pattern in PATH_ESCAPE_PATTERNS:
            if pattern in path:
                return _deny(f"Path escape attempt blocked: {pattern}")
        if path.startswith("/") and not path.startswith("/workspaces"):
            return _deny("Absolute paths outside /workspaces are not allowed")

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limiter = _get_rate_limiter()
    if rate_limiter:
        user_id_rl = "anonymous"
        if isinstance(context, dict):
            user_id_rl = context.get("user_id", "anonymous")
        category = TOOL_RATE_CATEGORY.get(tool_name)
        if category is None and tool_name.startswith("hie_"):
            category = "api_calls"
        if category and category in RATE_LIMITS:
            try:
                allowed = await rate_limiter.check(user_id_rl, category, RATE_LIMITS[category])
                if not allowed:
                    return _deny(
                        f"Rate limit exceeded for '{category}' ({RATE_LIMITS[category]}/min). "
                        f"Please wait before retrying."
                    )
            except Exception as e:
                logger.warning(f"Rate limit check failed (allowing): {e}")

    # ── Namespace: Enforce core vs custom class separation ───────────────
    # This is the CRITICAL product design guardrail:
    #   li.*, Engine.li.*, EnsLib.*  → PROTECTED (read-only)
    #   custom.*                     → DEVELOPER (writable)

    if tool_name in ("hie_create_item", "hie_update_item"):
        class_name = tool_input.get("class_name", "")
        if class_name:
            allowed, reason = is_class_name_writable(class_name, user_role)
            if not allowed:
                return _deny(reason)

    if tool_name in ["write_file", "Write"]:
        path = tool_input.get("path", "") or tool_input.get("file_path", "")
        if path:
            allowed, reason = is_file_path_writable(path, user_role)
            if not allowed:
                return _deny(reason)

    # ── Lifecycle: Environment-aware deploy gating ───────────────────────
    # Developers can deploy to staging directly.
    # Production deploys by developers create an approval request.
    # Operators, admins can deploy to any environment.
    if tool_name == "hie_deploy_project" and user_role == "developer":
        environment = tool_input.get("environment", "staging")
        if environment == "production":
            tenant_id_ctx = context.get("tenant_id", "") if isinstance(context, dict) else ""
            user_id = context.get("user_id", "unknown") if isinstance(context, dict) else "unknown"
            approval = await _post_approval_request(
                requested_by=user_id,
                requested_role=user_role,
                tenant_id=tenant_id_ctx or None,
                workspace_id=tool_input.get("workspace_id") or tool_input.get("workspace"),
                project_id=tool_input.get("project_id") or tool_input.get("project"),
                project_name=tool_input.get("project_name") or tool_input.get("name"),
                environment=environment,
                config_snapshot=tool_input,
            )
            approval_id = approval.get("id", "unknown") if approval else "unknown"
            return _deny(
                f"Production deployment requires approval. "
                f"Approval request #{approval_id} has been created. "
                f"A Clinical Safety Officer or Tenant Admin must review and approve "
                f"before the production deployment can proceed. "
                f"You can deploy to staging without approval using environment='staging'."
            )

    # Developers still cannot start/stop productions directly
    if tool_name in ("hie_start_project", "hie_stop_project"):
        if user_role == "developer":
            return _deny(
                f"Role 'developer' cannot use '{tool_name}' directly. "
                f"Contact an Operator or Tenant Admin to manage production lifecycle."
            )

    return {}  # Allow


async def post_tool_use_hook(input_data: dict[str, Any], tool_use_id: str, result: Any, context: Any) -> dict[str, Any]:
    """
    Hook called after tool execution.

    Responsibilities:
    1. POST audit entry to prompt-manager /audit API (NHS compliance)
    2. Log locally for immediate debugging
    3. Track namespace events (class creation)
    """
    if not ENABLE_HOOKS:
        return {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Extract context
    user_role = "unknown"
    user_id = "unknown"
    tenant_id = None
    session_id = None
    run_id = None
    if isinstance(context, dict):
        user_role = context.get("user_role", "unknown")
        user_id = context.get("user_id", "unknown")
        tenant_id = context.get("tenant_id") or None
        session_id = context.get("session_id")
        run_id = context.get("run_id")

    # Determine result status
    result_status = "success"
    if isinstance(result, dict):
        if result.get("error") or result.get("is_error"):
            result_status = "error"

    # Determine target type/id for HIE tools
    target_type = None
    target_id = None
    if tool_name.startswith("hie_"):
        if "project" in tool_name:
            target_type = "project"
            target_id = tool_input.get("project_id") or tool_input.get("project")
        elif "workspace" in tool_name:
            target_type = "workspace"
            target_id = tool_input.get("workspace_id") or tool_input.get("workspace")
        elif "item" in tool_name:
            target_type = "item"
            target_id = tool_input.get("name") or tool_input.get("item_id")

    # Local log (always)
    logger.info(
        f"[AUDIT] tool={tool_name} role={user_role} tenant={tenant_id} "
        f"status={result_status} tool_use_id={tool_use_id}"
    )

    # POST to prompt-manager audit API (fire-and-forget, non-blocking)
    await _post_audit_entry(
        user_id=user_id,
        user_role=user_role,
        action=tool_name,
        result_status=result_status,
        tenant_id=tenant_id,
        session_id=session_id,
        run_id=run_id,
        target_type=target_type,
        target_id=target_id,
        input_summary=_summarise_input(tool_input),
        result_summary=_summarise_result(result),
    )

    return {}


def get_hook_matchers() -> dict[str, list[dict[str, Any]]]:
    """
    Get hook matchers for agent SDK integration.
    """
    if not ENABLE_HOOKS:
        return {}

    return {
        "PreToolUse": [
            {"matcher": "*", "hooks": [pre_tool_use_hook]},
        ],
        "PostToolUse": [
            {"matcher": "*", "hooks": [post_tool_use_hook]},
        ],
    }
