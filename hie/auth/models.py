"""User, Tenant, and Role models for authentication and RBAC.

Note: These are simple enums and dataclasses for use with raw asyncpg queries.
The actual database schema is defined in scripts/init-db.sql.
"""

from enum import Enum


class TenantStatus(str, Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class UserStatus(str, Enum):
    """User status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    REJECTED = "rejected"


# Note: We use raw asyncpg queries instead of ORM models.
# The database schema is defined in scripts/init-db.sql.
# These enums are used for type-safe status values.
