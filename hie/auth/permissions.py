"""Permission definitions for RBAC."""

from enum import Enum
from typing import NamedTuple


class Permission(NamedTuple):
    """Permission definition."""
    code: str
    resource: str
    action: str
    description: str


# ============================================================================
# Permission Definitions
# ============================================================================

class Permissions:
    """All available permissions in the system."""
    
    # Tenant permissions (super admin only)
    TENANTS_CREATE = Permission("tenants:create", "tenants", "create", "Create new tenants")
    TENANTS_READ = Permission("tenants:read", "tenants", "read", "View tenant details")
    TENANTS_UPDATE = Permission("tenants:update", "tenants", "update", "Update tenant settings")
    TENANTS_DELETE = Permission("tenants:delete", "tenants", "delete", "Delete tenants")
    
    # User permissions
    USERS_CREATE = Permission("users:create", "users", "create", "Create new users")
    USERS_READ = Permission("users:read", "users", "read", "View user details")
    USERS_UPDATE = Permission("users:update", "users", "update", "Update user profiles")
    USERS_DELETE = Permission("users:delete", "users", "delete", "Delete users")
    USERS_APPROVE = Permission("users:approve", "users", "approve", "Approve/reject pending users")
    
    # Production permissions
    PRODUCTIONS_CREATE = Permission("productions:create", "productions", "create", "Create productions")
    PRODUCTIONS_READ = Permission("productions:read", "productions", "read", "View productions")
    PRODUCTIONS_UPDATE = Permission("productions:update", "productions", "update", "Update productions")
    PRODUCTIONS_DELETE = Permission("productions:delete", "productions", "delete", "Delete productions")
    PRODUCTIONS_START = Permission("productions:start", "productions", "start", "Start productions")
    PRODUCTIONS_STOP = Permission("productions:stop", "productions", "stop", "Stop productions")
    
    # Message permissions
    MESSAGES_READ = Permission("messages:read", "messages", "read", "View messages")
    MESSAGES_RESEND = Permission("messages:resend", "messages", "resend", "Resend messages")
    MESSAGES_DELETE = Permission("messages:delete", "messages", "delete", "Delete messages")
    
    # Configuration permissions
    CONFIG_READ = Permission("config:read", "config", "read", "View configuration")
    CONFIG_UPDATE = Permission("config:update", "config", "update", "Update configuration")
    CONFIG_EXPORT = Permission("config:export", "config", "export", "Export configuration")
    CONFIG_IMPORT = Permission("config:import", "config", "import", "Import configuration")
    
    # Audit permissions
    AUDIT_READ = Permission("audit:read", "audit", "read", "View audit logs")
    
    # Settings permissions
    SETTINGS_READ = Permission("settings:read", "settings", "read", "View system settings")
    SETTINGS_UPDATE = Permission("settings:update", "settings", "update", "Update system settings")


# ============================================================================
# Predefined Role Permissions
# ============================================================================

SUPER_ADMIN_PERMISSIONS = [
    # All tenant permissions
    Permissions.TENANTS_CREATE.code,
    Permissions.TENANTS_READ.code,
    Permissions.TENANTS_UPDATE.code,
    Permissions.TENANTS_DELETE.code,
    # All user permissions
    Permissions.USERS_CREATE.code,
    Permissions.USERS_READ.code,
    Permissions.USERS_UPDATE.code,
    Permissions.USERS_DELETE.code,
    Permissions.USERS_APPROVE.code,
    # All production permissions
    Permissions.PRODUCTIONS_CREATE.code,
    Permissions.PRODUCTIONS_READ.code,
    Permissions.PRODUCTIONS_UPDATE.code,
    Permissions.PRODUCTIONS_DELETE.code,
    Permissions.PRODUCTIONS_START.code,
    Permissions.PRODUCTIONS_STOP.code,
    # All message permissions
    Permissions.MESSAGES_READ.code,
    Permissions.MESSAGES_RESEND.code,
    Permissions.MESSAGES_DELETE.code,
    # All config permissions
    Permissions.CONFIG_READ.code,
    Permissions.CONFIG_UPDATE.code,
    Permissions.CONFIG_EXPORT.code,
    Permissions.CONFIG_IMPORT.code,
    # All audit permissions
    Permissions.AUDIT_READ.code,
    # All settings permissions
    Permissions.SETTINGS_READ.code,
    Permissions.SETTINGS_UPDATE.code,
]

TENANT_ADMIN_PERMISSIONS = [
    # User permissions (within tenant)
    Permissions.USERS_CREATE.code,
    Permissions.USERS_READ.code,
    Permissions.USERS_UPDATE.code,
    Permissions.USERS_DELETE.code,
    Permissions.USERS_APPROVE.code,
    # All production permissions
    Permissions.PRODUCTIONS_CREATE.code,
    Permissions.PRODUCTIONS_READ.code,
    Permissions.PRODUCTIONS_UPDATE.code,
    Permissions.PRODUCTIONS_DELETE.code,
    Permissions.PRODUCTIONS_START.code,
    Permissions.PRODUCTIONS_STOP.code,
    # All message permissions
    Permissions.MESSAGES_READ.code,
    Permissions.MESSAGES_RESEND.code,
    Permissions.MESSAGES_DELETE.code,
    # All config permissions
    Permissions.CONFIG_READ.code,
    Permissions.CONFIG_UPDATE.code,
    Permissions.CONFIG_EXPORT.code,
    Permissions.CONFIG_IMPORT.code,
    # Audit permissions
    Permissions.AUDIT_READ.code,
    # Settings permissions
    Permissions.SETTINGS_READ.code,
    Permissions.SETTINGS_UPDATE.code,
]

INTEGRATION_ENGINEER_PERMISSIONS = [
    # Limited user permissions
    Permissions.USERS_READ.code,
    # Production permissions (no delete)
    Permissions.PRODUCTIONS_CREATE.code,
    Permissions.PRODUCTIONS_READ.code,
    Permissions.PRODUCTIONS_UPDATE.code,
    Permissions.PRODUCTIONS_DELETE.code,
    Permissions.PRODUCTIONS_START.code,
    Permissions.PRODUCTIONS_STOP.code,
    # Message permissions
    Permissions.MESSAGES_READ.code,
    Permissions.MESSAGES_RESEND.code,
    # Config permissions
    Permissions.CONFIG_READ.code,
    Permissions.CONFIG_UPDATE.code,
    Permissions.CONFIG_EXPORT.code,
    Permissions.CONFIG_IMPORT.code,
    # Settings read only
    Permissions.SETTINGS_READ.code,
]

OPERATOR_PERMISSIONS = [
    # User read only
    Permissions.USERS_READ.code,
    # Production read and control
    Permissions.PRODUCTIONS_READ.code,
    Permissions.PRODUCTIONS_START.code,
    Permissions.PRODUCTIONS_STOP.code,
    # Message permissions
    Permissions.MESSAGES_READ.code,
    Permissions.MESSAGES_RESEND.code,
    # Config read only
    Permissions.CONFIG_READ.code,
    # Settings read only
    Permissions.SETTINGS_READ.code,
]

VIEWER_PERMISSIONS = [
    # Read-only access
    Permissions.USERS_READ.code,
    Permissions.PRODUCTIONS_READ.code,
    Permissions.MESSAGES_READ.code,
    Permissions.CONFIG_READ.code,
    Permissions.SETTINGS_READ.code,
]

AUDITOR_PERMISSIONS = [
    # Read-only access plus audit
    Permissions.USERS_READ.code,
    Permissions.PRODUCTIONS_READ.code,
    Permissions.MESSAGES_READ.code,
    Permissions.CONFIG_READ.code,
    Permissions.SETTINGS_READ.code,
    Permissions.AUDIT_READ.code,
]


# ============================================================================
# Predefined System Roles
# ============================================================================

SYSTEM_ROLES = [
    {
        "name": "super_admin",
        "display_name": "Super Administrator",
        "description": "Full platform access, can manage all tenants and users",
        "is_system": True,
        "permissions": SUPER_ADMIN_PERMISSIONS,
    },
    {
        "name": "tenant_admin",
        "display_name": "Tenant Administrator",
        "description": "Full access within their tenant, can manage users",
        "is_system": True,
        "permissions": TENANT_ADMIN_PERMISSIONS,
    },
    {
        "name": "integration_engineer",
        "display_name": "Integration Engineer",
        "description": "Configure productions, items, and routes",
        "is_system": True,
        "permissions": INTEGRATION_ENGINEER_PERMISSIONS,
    },
    {
        "name": "operator",
        "display_name": "Operator",
        "description": "Start/stop productions, view and resend messages",
        "is_system": True,
        "permissions": OPERATOR_PERMISSIONS,
    },
    {
        "name": "viewer",
        "display_name": "Viewer",
        "description": "Read-only access to all resources",
        "is_system": True,
        "permissions": VIEWER_PERMISSIONS,
    },
    {
        "name": "auditor",
        "display_name": "Auditor",
        "description": "Read-only access plus audit log viewing",
        "is_system": True,
        "permissions": AUDITOR_PERMISSIONS,
    },
]


def has_permission(user_permissions: list[str], required_permission: str) -> bool:
    """Check if user has a specific permission."""
    return required_permission in user_permissions


def has_any_permission(user_permissions: list[str], required_permissions: list[str]) -> bool:
    """Check if user has any of the required permissions."""
    return any(p in user_permissions for p in required_permissions)


def has_all_permissions(user_permissions: list[str], required_permissions: list[str]) -> bool:
    """Check if user has all of the required permissions."""
    return all(p in user_permissions for p in required_permissions)
