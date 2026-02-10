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

logger = logging.getLogger(__name__)


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

    Returns empty dict to allow, or dict with hookSpecificOutput to deny.
    """
    if not ENABLE_HOOKS:
        return {}

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check bash commands for dangerous patterns
    if tool_name == "Bash" or tool_name == "bash":
        command = tool_input.get("command", "")
        for pattern in BLOCKED_BASH_PATTERNS:
            if pattern in command:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Blocked dangerous pattern: {pattern}",
                    }
                }
        # Check for SQL injection in bash commands
        for pattern in BLOCKED_SQL_PATTERNS:
            if pattern.lower() in command.lower():
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Blocked clinical data manipulation: {pattern}",
                    }
                }

    # Check file operations for path escape attempts
    if tool_name in ["Read", "Write", "Edit", "read_file", "write_file"]:
        path = tool_input.get("path", "") or tool_input.get("file_path", "")
        for pattern in PATH_ESCAPE_PATTERNS:
            if pattern in path:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Path escape attempt blocked: {pattern}",
                    }
                }

        # Block absolute paths outside workspace
        if path.startswith("/") and not path.startswith("/workspaces"):
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Absolute paths outside /workspaces are not allowed",
                }
            }

    return {}  # Allow


async def post_tool_use_hook(input_data: dict[str, Any], tool_use_id: str, result: Any, context: Any) -> dict[str, Any]:
    """
    Hook called after tool execution.

    Used for audit logging, result validation, etc.
    """
    if not ENABLE_HOOKS:
        return {}

    tool_name = input_data.get("tool_name", "")

    # Audit logging
    logger.info(f"[AUDIT] Tool executed: {tool_name}, tool_use_id: {tool_use_id}")

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
