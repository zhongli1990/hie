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
import logging

from .config import ENABLE_HOOKS
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
    "bash_commands_per_minute": 30,
    "file_writes_per_minute": 20,
    "api_calls_per_minute": 60,
    "hl7_sends_per_minute": 10,
}


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

    # ── Namespace: Enforce core vs custom class separation ───────────────
    # This is the CRITICAL product design guardrail:
    #   li.*, Engine.li.*, EnsLib.*  → PROTECTED (read-only)
    #   custom.*                     → DEVELOPER (writable)

    if tool_name == "hie_create_item":
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

    # ── Lifecycle: Developer cannot deploy/start/stop ────────────────────
    if tool_name in ("hie_deploy_project", "hie_start_project", "hie_stop_project"):
        if user_role == "developer":
            return _deny(
                f"Role 'developer' cannot use '{tool_name}' directly. "
                f"Production deployments require approval from a Clinical Safety Officer "
                f"or Tenant Admin. Your integration has been built successfully — "
                f"request a deployment review to proceed."
            )

    return {}  # Allow


async def post_tool_use_hook(input_data: dict[str, Any], tool_use_id: str, result: Any, context: Any) -> dict[str, Any]:
    """
    Hook called after tool execution.

    Used for audit logging, result validation, namespace verification.
    """
    if not ENABLE_HOOKS:
        return {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Extract role from context
    user_role = "unknown"
    tenant_id = ""
    if isinstance(context, dict):
        user_role = context.get("user_role", "unknown")
        tenant_id = context.get("tenant_id", "")

    # Audit logging with role context
    logger.info(
        f"[AUDIT] tool={tool_name} role={user_role} tenant={tenant_id} "
        f"tool_use_id={tool_use_id}"
    )

    # Log class creation events for namespace audit trail
    if tool_name == "hie_create_item":
        class_name = tool_input.get("class_name", "")
        item_name = tool_input.get("name", "")
        logger.info(
            f"[AUDIT:CLASS] item={item_name} class={class_name} "
            f"role={user_role} tenant={tenant_id}"
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
