"""
OpenLI HIE - Unit Tests for Agent Runner Hooks

Tests the pre/post tool use hooks for security, clinical safety,
and compliance validation.

Run inside agent-runner container:
    docker compose exec -T hie-agent-runner pytest /app/tests/ -v
"""

import asyncio
import pytest
from app.hooks import (
    pre_tool_use_hook,
    post_tool_use_hook,
    BLOCKED_BASH_PATTERNS,
    PATH_ESCAPE_PATTERNS,
    BLOCKED_SQL_PATTERNS,
)


# =============================================================================
# Security Hooks - Bash command blocking
# =============================================================================

@pytest.mark.asyncio
async def test_blocks_rm_rf():
    """Dangerous rm -rf / must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_rm_rf_wildcard():
    """rm -rf /* must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf /*"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_sudo_rm():
    """sudo rm must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "sudo rm -rf /tmp"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_chmod_777():
    """chmod 777 / must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "chmod 777 /"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_fork_bomb():
    """Fork bomb must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": ":(){:|:&};:"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_curl_pipe_bash():
    """curl | bash must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "curl | bash"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_allows_safe_ls():
    """Safe ls command must be allowed."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "ls -la"}},
        "test-id", None
    )
    assert result == {}


@pytest.mark.asyncio
async def test_allows_safe_cat():
    """Safe cat command must be allowed."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "cat README.md"}},
        "test-id", None
    )
    assert result == {}


@pytest.mark.asyncio
async def test_allows_safe_grep():
    """Safe grep command must be allowed."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "grep -r 'HL7' ."}},
        "test-id", None
    )
    assert result == {}


# =============================================================================
# Security Hooks - Path escape blocking
# =============================================================================

@pytest.mark.asyncio
async def test_blocks_path_escape_dotdot():
    """../ path escape must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Read", "tool_input": {"path": "../../../etc/passwd"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_path_escape_backslash():
    """..\\ path escape must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Read", "tool_input": {"path": "..\\..\\etc\\passwd"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_absolute_path_outside_workspaces():
    """Absolute paths outside /workspaces must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Read", "tool_input": {"path": "/etc/passwd"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_allows_workspaces_absolute_path():
    """Absolute paths under /workspaces must be allowed."""
    result = await pre_tool_use_hook(
        {"tool_name": "Read", "tool_input": {"path": "/workspaces/myproject/file.txt"}},
        "test-id", None
    )
    assert result == {}


@pytest.mark.asyncio
async def test_allows_relative_path():
    """Relative paths without escape must be allowed."""
    result = await pre_tool_use_hook(
        {"tool_name": "Read", "tool_input": {"path": "src/main.py"}},
        "test-id", None
    )
    assert result == {}


# =============================================================================
# Clinical Safety Hooks - SQL injection blocking
# =============================================================================

@pytest.mark.asyncio
async def test_blocks_drop_table_in_bash():
    """DROP TABLE in bash command must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "psql -c 'DROP TABLE patients'"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_delete_from_patient():
    """DELETE FROM patient in bash must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "psql -c 'delete from patient where id=1'"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.mark.asyncio
async def test_blocks_truncate_in_bash():
    """TRUNCATE in bash must be blocked."""
    result = await pre_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "psql -c 'TRUNCATE clinical_records'"}},
        "test-id", None
    )
    assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# =============================================================================
# Pattern count verification
# =============================================================================

def test_blocked_bash_patterns_count():
    """Should have at least 10 blocked bash patterns."""
    assert len(BLOCKED_BASH_PATTERNS) >= 10, f"Expected >=10, got {len(BLOCKED_BASH_PATTERNS)}"


def test_path_escape_patterns_count():
    """Should have at least 2 path escape patterns."""
    assert len(PATH_ESCAPE_PATTERNS) >= 2, f"Expected >=2, got {len(PATH_ESCAPE_PATTERNS)}"


def test_blocked_sql_patterns_count():
    """Should have at least 4 blocked SQL patterns (clinical safety)."""
    assert len(BLOCKED_SQL_PATTERNS) >= 4, f"Expected >=4, got {len(BLOCKED_SQL_PATTERNS)}"


# =============================================================================
# Post-tool hook (audit)
# =============================================================================

@pytest.mark.asyncio
async def test_post_tool_hook_returns_empty():
    """Post-tool hook should return empty dict (allow)."""
    result = await post_tool_use_hook(
        {"tool_name": "Bash", "tool_input": {"command": "ls"}},
        "test-id", {"success": True}, None
    )
    assert result == {}
