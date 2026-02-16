"""
OpenLI HIE Agent Runner - Role-Based Access Control

Defines the RBAC permission model for the GenAI-native development platform.
Each user role maps to a set of permitted tools and skills, enforcing the
product design principle that core classes (li.*) are protected and only
custom.* namespace is developer-extensible.

Class Namespace Enforcement (CRITICAL):
  PROTECTED (read-only):  li.*, Engine.li.*, EnsLib.*
  DEVELOPER (writable):   custom.*

Role Hierarchy:
  platform_admin  → full access, all tenants
  tenant_admin    → full access within own tenant
  developer       → build + test, staging deploy only, custom.* writes only
  clinical_safety_officer → read + test + review skills only
  viewer          → read-only monitoring
"""

from typing import Any


# =============================================================================
# CLASS NAMESPACE ENFORCEMENT — Product design principle
# =============================================================================

# Protected namespaces: core product classes, NEVER writable by non-admins
PROTECTED_CLASS_NAMESPACES = (
    "li.",           # Core LI product classes
    "Engine.li.",    # Fully-qualified core path
    "EnsLib.",       # IRIS compatibility aliases
)

# Developer namespace: the ONLY namespace where non-admin roles can write
DEVELOPER_CLASS_NAMESPACE = "custom."

# Protected file paths: core product directories that non-admins cannot write to
PROTECTED_FILE_PATHS = (
    "li/",           # Core class source files
    "Engine/",       # Engine internals
    "EnsLib/",       # IRIS compatibility layer
)


# =============================================================================
# ROLE → TOOL PERMISSIONS
# =============================================================================

ROLE_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "platform_admin": {"*"},  # All tools — unrestricted

    "tenant_admin": {
        # Workspace management
        "hie_list_workspaces", "hie_create_workspace",
        # Project management
        "hie_list_projects", "hie_create_project", "hie_get_project",
        # Items, connections, rules
        "hie_create_item", "hie_create_connection", "hie_create_routing_rule",
        # Production lifecycle — full access within tenant
        "hie_deploy_project", "hie_start_project", "hie_stop_project",
        "hie_project_status",
        # Testing and registry
        "hie_test_item", "hie_list_item_types", "hie_reload_custom_classes",
        # File tools — write restricted to custom.* by hooks
        "read_file", "write_file", "list_files", "bash",
    },

    "developer": {
        # Workspace — read only (no create)
        "hie_list_workspaces",
        # Project management — can create and read
        "hie_list_projects", "hie_create_project", "hie_get_project",
        # Items, connections, rules — full build access
        "hie_create_item", "hie_create_connection", "hie_create_routing_rule",
        # Production lifecycle — NO deploy/start/stop (staging only via approval)
        "hie_project_status",
        # Testing and registry
        "hie_test_item", "hie_list_item_types", "hie_reload_custom_classes",
        # File tools — write restricted to custom.* by hooks
        "read_file", "write_file", "list_files", "bash",
    },

    "clinical_safety_officer": {
        # Read-only workspace/project access
        "hie_list_workspaces", "hie_list_projects", "hie_get_project",
        # Status monitoring
        "hie_project_status",
        # Testing — CSO needs to test during safety review
        "hie_test_item", "hie_list_item_types",
        # Read-only file access
        "read_file", "list_files",
    },

    "viewer": {
        # Read-only monitoring
        "hie_list_workspaces", "hie_list_projects", "hie_get_project",
        "hie_project_status", "hie_list_item_types",
        "read_file", "list_files",
    },
}


# =============================================================================
# ROLE → SKILL PERMISSIONS
# =============================================================================

ROLE_SKILL_PERMISSIONS: dict[str, set[str]] = {
    "platform_admin": {"*"},  # All skills
    "tenant_admin": {"*"},    # All skills within tenant

    "developer": {
        "hl7-route-builder",
        "fhir-mapper",
        "integration-test",
        "nhs-compliance-check",
    },

    "clinical_safety_officer": {
        "clinical-safety-review",
        "nhs-compliance-check",
        "integration-test",
    },

    "viewer": set(),  # No skills — read-only
}


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================

def filter_tools(tools: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    """Filter tool definitions to only those permitted for the given role.

    This is Layer 1 (proactive): the AI model literally cannot see or call
    tools outside its role's permission set.
    """
    allowed = ROLE_TOOL_PERMISSIONS.get(role, ROLE_TOOL_PERMISSIONS["viewer"])
    if "*" in allowed:
        return tools
    return [t for t in tools if t["name"] in allowed]


def filter_skills(skills: list[dict[str, Any]], role: str) -> list[dict[str, Any]]:
    """Filter skills to only those permitted for the given role."""
    allowed = ROLE_SKILL_PERMISSIONS.get(role, set())
    if "*" in allowed:
        return skills
    return [s for s in skills if s["name"] in allowed]


def is_tool_permitted(tool_name: str, role: str) -> bool:
    """Check if a specific tool is permitted for the given role.

    This is Layer 2 (defensive): called by hooks even after tool filtering,
    as defense-in-depth against prompt injection or model hallucination.
    """
    allowed = ROLE_TOOL_PERMISSIONS.get(role, ROLE_TOOL_PERMISSIONS["viewer"])
    return "*" in allowed or tool_name in allowed


def is_class_name_writable(class_name: str, role: str) -> tuple[bool, str]:
    """Check if a class name is writable by the given role.

    Enforces the product design principle:
      - li.*, Engine.li.*, EnsLib.* → PROTECTED, read-only
      - custom.* → writable by developer and above

    Returns (allowed, reason).
    """
    if role == "platform_admin":
        return True, ""

    # Check if class is in a protected namespace
    for ns in PROTECTED_CLASS_NAMESPACES:
        if class_name.startswith(ns):
            return False, (
                f"Class '{class_name}' is in protected namespace '{ns}'. "
                f"Core product classes (li.*, Engine.li.*, EnsLib.*) are read-only. "
                f"Use the custom.* namespace for developer extensions "
                f"(e.g., custom.nhs.YourClassName)."
            )

    # For non-admin roles, class MUST be in custom.* namespace
    if role in ("tenant_admin", "developer"):
        if not class_name.startswith(DEVELOPER_CLASS_NAMESPACE):
            return False, (
                f"Class '{class_name}' is not in the custom.* namespace. "
                f"All developer-created classes must use the custom.* namespace "
                f"(e.g., custom.nhs.{class_name.split('.')[-1] if '.' in class_name else class_name})."
            )

    return True, ""


def is_file_path_writable(file_path: str, role: str) -> tuple[bool, str]:
    """Check if a file path is writable by the given role.

    Enforces namespace separation for file writes:
      - li/, Engine/, EnsLib/ → PROTECTED
      - custom/ → writable by developer and above

    Returns (allowed, reason).
    """
    if role == "platform_admin":
        return True, ""

    # Block writes to protected directories
    for protected in PROTECTED_FILE_PATHS:
        if file_path.startswith(protected) or f"/{protected}" in file_path:
            return False, (
                f"Cannot write to protected path '{file_path}'. "
                f"Core product files (li/, Engine/, EnsLib/) are read-only. "
                f"Place custom files under the custom/ directory."
            )

    return True, ""


# =============================================================================
# ROLE DISPLAY NAMES (for Portal UI)
# =============================================================================

ROLE_DISPLAY_NAMES: dict[str, str] = {
    "platform_admin": "Platform Admin",
    "tenant_admin": "Tenant Admin",
    "developer": "Integration Developer",
    "clinical_safety_officer": "Clinical Safety Officer",
    "viewer": "Viewer",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "platform_admin": "Full access to all tenants, tools, and skills.",
    "tenant_admin": "Full access within your tenant. Can deploy to production.",
    "developer": (
        "Build and test integrations using natural language. "
        "Write custom.* classes. Production deploy requires approval."
    ),
    "clinical_safety_officer": (
        "Review integrations for DCB0129/DCB0160 compliance. "
        "Run safety reviews and approve production deployments."
    ),
    "viewer": "Read-only access to project status and monitoring.",
}

ALL_ROLES = list(ROLE_TOOL_PERMISSIONS.keys())
