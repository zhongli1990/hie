# HIE User Management Module Design

## Enterprise-Grade Identity & Access Management

**Version:** 1.0  
**Last Updated:** January 21, 2026  
**Status:** Design Phase  
**Branch:** `feature/user-management`

---

## 1. Executive Summary

This document outlines the design for HIE's enterprise-grade user management system, providing authentication, authorization, and multi-tenancy support for mission-critical healthcare integration environments.

### Key Capabilities

- **Multi-Tenancy** — Support for NHS Trusts as tenants with isolated data
- **Role-Based Access Control (RBAC)** — Granular permissions for healthcare environments
- **User Lifecycle Management** — Registration, approval, activation, deactivation
- **Audit Trail** — Complete logging of all authentication and authorization events
- **Enterprise Security** — JWT tokens, password policies, session management, MFA-ready

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HIE PLATFORM                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   Portal (UI)    │    │  Management API  │    │   HIE Engine     │      │
│  │                  │    │                  │    │                  │      │
│  │  - Login Page    │───▶│  - Auth Router   │───▶│  - Productions   │      │
│  │  - Register Page │    │  - Admin Router  │    │  - Items         │      │
│  │  - Users Page    │    │  - User Router   │    │  - Routes        │      │
│  │  - Profile Page  │    │                  │    │                  │      │
│  └──────────────────┘    └────────┬─────────┘    └──────────────────┘      │
│                                   │                                          │
│                          ┌────────▼─────────┐                               │
│                          │  Auth Middleware │                               │
│                          │  - JWT Validation│                               │
│                          │  - RBAC Check    │                               │
│                          │  - Tenant Filter │                               │
│                          └────────┬─────────┘                               │
│                                   │                                          │
│  ┌────────────────────────────────▼────────────────────────────────────┐   │
│  │                         PostgreSQL                                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │   │
│  │  │ tenants │  │  users  │  │  roles  │  │ perms   │  │ audit_log │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Multi-Tenancy Model

### 3.1 Tenant Hierarchy

HIE supports a hierarchical multi-tenancy model designed for NHS environments:

```
Platform Level (Super Admins)
    │
    ├── Tenant: NHS Trust A
    │   ├── Tenant Admin
    │   ├── Integration Engineer
    │   ├── Operator
    │   └── Viewer
    │
    ├── Tenant: NHS Trust B
    │   ├── Tenant Admin
    │   └── ...
    │
    └── Tenant: NHS Trust C
        └── ...
```

### 3.2 Tenant Entity

```python
class Tenant:
    id: UUID                    # Unique identifier
    name: str                   # Display name (e.g., "Royal London NHS Trust")
    code: str                   # Short code (e.g., "RLH")
    status: TenantStatus        # active, suspended, archived
    settings: dict              # Tenant-specific configuration
    created_at: datetime
    updated_at: datetime
    
    # Limits
    max_users: int              # Maximum users allowed
    max_productions: int        # Maximum productions allowed
    
    # Contact
    admin_email: str            # Primary admin contact
    support_email: str          # Support contact
```

### 3.3 Tenant Isolation

| Resource | Isolation Level | Implementation |
|----------|-----------------|----------------|
| Users | Full | `tenant_id` foreign key |
| Productions | Full | `tenant_id` foreign key |
| Messages | Full | Via production ownership |
| Configurations | Full | `tenant_id` foreign key |
| Audit Logs | Full | `tenant_id` foreign key |
| System Settings | Shared | Platform-level only |

---

## 4. User Model

### 4.1 User Entity

```python
class User:
    # Identity
    id: UUID                    # Unique identifier
    tenant_id: UUID | None      # Null for super admins
    email: str                  # Unique email address
    username: str | None        # Optional username
    
    # Profile
    display_name: str           # Full name
    title: str | None           # Job title
    department: str | None      # Department
    mobile: str | None          # Mobile number
    avatar_url: str | None      # Profile picture
    
    # Authentication
    password_hash: str          # bcrypt hash
    mfa_enabled: bool           # MFA status
    mfa_secret: str | None      # TOTP secret (encrypted)
    
    # Status & Lifecycle
    status: UserStatus          # pending, active, inactive, locked, rejected
    role_id: UUID               # Primary role
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    approved_by: UUID | None
    last_login_at: datetime | None
    password_changed_at: datetime | None
    
    # Security
    failed_login_attempts: int
    locked_until: datetime | None
    must_change_password: bool
```

### 4.2 User Status Lifecycle

```
                    ┌─────────────┐
                    │  REGISTER   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
              ┌─────│   PENDING   │─────┐
              │     └─────────────┘     │
              │                         │
         APPROVE                    REJECT
              │                         │
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │   ACTIVE    │          │  REJECTED   │
       └──────┬──────┘          └─────────────┘
              │                         │
    ┌─────────┼─────────┐               │
    │         │         │               │
DEACTIVATE  LOCK    REACTIVATE ◄────────┘
    │         │         │
    ▼         ▼         │
┌─────────┐ ┌─────────┐ │
│INACTIVE │ │ LOCKED  │─┘
└─────────┘ └─────────┘
```

### 4.3 User Statuses

| Status | Description | Can Login | Actions Available |
|--------|-------------|-----------|-------------------|
| `pending` | Awaiting admin approval | No | Approve, Reject |
| `active` | Normal active user | Yes | Deactivate, Lock, Edit |
| `inactive` | Manually deactivated | No | Activate |
| `locked` | Auto-locked (failed logins) | No | Unlock, Activate |
| `rejected` | Registration rejected | No | Activate (reconsider) |

---

## 5. Role-Based Access Control (RBAC)

### 5.1 Role Hierarchy

HIE implements a hierarchical RBAC system with predefined roles suitable for healthcare environments:

```
┌─────────────────────────────────────────────────────────────────┐
│                        SUPER_ADMIN                               │
│  Platform-level access, can manage all tenants                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        TENANT_ADMIN                              │
│  Full access within their tenant                                │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ INTEGRATION_ENG │ │    OPERATOR     │ │     VIEWER      │
│ Configure items │ │ Start/stop prod │ │ Read-only access│
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 5.2 Role Definitions

```python
class Role:
    id: UUID
    tenant_id: UUID | None      # Null for system roles
    name: str                   # Role name
    display_name: str           # Human-readable name
    description: str            # Role description
    is_system: bool             # System-defined (non-editable)
    permissions: list[str]      # List of permission codes
    created_at: datetime
    updated_at: datetime
```

### 5.3 Predefined Roles

| Role | Scope | Description |
|------|-------|-------------|
| `super_admin` | Platform | Full platform access, manage tenants |
| `tenant_admin` | Tenant | Full tenant access, manage users |
| `integration_engineer` | Tenant | Configure productions, items, routes |
| `operator` | Tenant | Start/stop productions, view messages |
| `viewer` | Tenant | Read-only access to all resources |
| `auditor` | Tenant | Read-only + audit log access |

### 5.4 Permission Model

Permissions follow the pattern: `resource:action`

```python
class Permission:
    code: str           # e.g., "productions:create"
    resource: str       # e.g., "productions"
    action: str         # e.g., "create"
    description: str    # Human-readable description
```

### 5.5 Permission Matrix

| Permission | Super Admin | Tenant Admin | Integration Eng | Operator | Viewer |
|------------|:-----------:|:------------:|:---------------:|:--------:|:------:|
| **Tenants** |
| `tenants:create` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `tenants:read` | ✅ | Own | ❌ | ❌ | ❌ |
| `tenants:update` | ✅ | Own | ❌ | ❌ | ❌ |
| `tenants:delete` | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Users** |
| `users:create` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `users:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `users:update` | ✅ | ✅ | Self | Self | Self |
| `users:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `users:approve` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Productions** |
| `productions:create` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `productions:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `productions:update` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `productions:delete` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `productions:start` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `productions:stop` | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Messages** |
| `messages:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `messages:resend` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `messages:delete` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Configuration** |
| `config:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `config:update` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `config:export` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `config:import` | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Audit** |
| `audit:read` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Settings** |
| `settings:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `settings:update` | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 6. Authentication

### 6.1 Authentication Flow

```
┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐
│  User   │         │ Portal  │         │   API   │         │   DB    │
└────┬────┘         └────┬────┘         └────┬────┘         └────┬────┘
     │                   │                   │                   │
     │  Enter Credentials│                   │                   │
     │──────────────────▶│                   │                   │
     │                   │                   │                   │
     │                   │  POST /auth/login │                   │
     │                   │──────────────────▶│                   │
     │                   │                   │                   │
     │                   │                   │  Verify Password  │
     │                   │                   │──────────────────▶│
     │                   │                   │◀──────────────────│
     │                   │                   │                   │
     │                   │                   │  Check Status     │
     │                   │                   │──────────────────▶│
     │                   │                   │◀──────────────────│
     │                   │                   │                   │
     │                   │  JWT Token + User │                   │
     │                   │◀──────────────────│                   │
     │                   │                   │                   │
     │  Store Token      │                   │                   │
     │◀──────────────────│                   │                   │
     │                   │                   │                   │
     │  Redirect to      │                   │                   │
     │  Dashboard        │                   │                   │
     │◀──────────────────│                   │                   │
```

### 6.2 JWT Token Structure

```json
{
  "sub": "user-uuid",
  "email": "user@nhs.uk",
  "tenant_id": "tenant-uuid",
  "role": "integration_engineer",
  "permissions": ["productions:read", "productions:create", ...],
  "iat": 1705845600,
  "exp": 1705932000
}
```

### 6.3 Token Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| Algorithm | HS256 | HMAC with SHA-256 |
| Access Token TTL | 24 hours | Short-lived access |
| Refresh Token TTL | 7 days | Long-lived refresh |
| Secret Key | Environment | `JWT_SECRET_KEY` |

### 6.4 Password Policy

```python
class PasswordPolicy:
    min_length: int = 12           # Minimum 12 characters
    require_uppercase: bool = True  # At least 1 uppercase
    require_lowercase: bool = True  # At least 1 lowercase
    require_digit: bool = True      # At least 1 number
    require_special: bool = True    # At least 1 special char
    max_age_days: int = 90          # Force change every 90 days
    history_count: int = 5          # Cannot reuse last 5 passwords
    lockout_attempts: int = 5       # Lock after 5 failed attempts
    lockout_duration_minutes: int = 30  # Lock for 30 minutes
```

---

## 7. API Endpoints

### 7.1 Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register` | Register new user | No |
| POST | `/api/auth/login` | Login and get token | No |
| POST | `/api/auth/logout` | Logout (invalidate token) | Yes |
| POST | `/api/auth/refresh` | Refresh access token | Yes (refresh) |
| GET | `/api/auth/me` | Get current user | Yes |
| PUT | `/api/auth/me` | Update current user profile | Yes |
| POST | `/api/auth/change-password` | Change password | Yes |
| POST | `/api/auth/forgot-password` | Request password reset | No |
| POST | `/api/auth/reset-password` | Reset password with token | No |

### 7.2 User Management Endpoints (Admin)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/admin/users` | List users | `users:read` |
| GET | `/api/admin/users/{id}` | Get user details | `users:read` |
| POST | `/api/admin/users` | Create user | `users:create` |
| PUT | `/api/admin/users/{id}` | Update user | `users:update` |
| DELETE | `/api/admin/users/{id}` | Delete user | `users:delete` |
| POST | `/api/admin/users/{id}/approve` | Approve pending user | `users:approve` |
| POST | `/api/admin/users/{id}/reject` | Reject pending user | `users:approve` |
| POST | `/api/admin/users/{id}/activate` | Activate user | `users:update` |
| POST | `/api/admin/users/{id}/deactivate` | Deactivate user | `users:update` |
| POST | `/api/admin/users/{id}/unlock` | Unlock locked user | `users:update` |
| POST | `/api/admin/users/{id}/reset-password` | Admin reset password | `users:update` |

### 7.3 Tenant Management Endpoints (Super Admin)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/admin/tenants` | List tenants | `tenants:read` |
| GET | `/api/admin/tenants/{id}` | Get tenant details | `tenants:read` |
| POST | `/api/admin/tenants` | Create tenant | `tenants:create` |
| PUT | `/api/admin/tenants/{id}` | Update tenant | `tenants:update` |
| DELETE | `/api/admin/tenants/{id}` | Delete tenant | `tenants:delete` |
| POST | `/api/admin/tenants/{id}/suspend` | Suspend tenant | `tenants:update` |
| POST | `/api/admin/tenants/{id}/activate` | Activate tenant | `tenants:update` |

### 7.4 Role Management Endpoints

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/api/admin/roles` | List roles | `users:read` |
| GET | `/api/admin/roles/{id}` | Get role details | `users:read` |
| POST | `/api/admin/roles` | Create custom role | `users:create` |
| PUT | `/api/admin/roles/{id}` | Update role | `users:update` |
| DELETE | `/api/admin/roles/{id}` | Delete role | `users:delete` |

---

## 8. Portal UI Components

### 8.1 New Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | User authentication |
| Register | `/register` | New user registration |
| Pending | `/pending` | Pending approval message |
| Users | `/admin/users` | User management table |
| User Detail | `/admin/users/[id]` | User profile and actions |
| Roles | `/admin/roles` | Role management |
| Tenants | `/admin/tenants` | Tenant management (super admin) |
| Profile | `/profile` | Current user profile |

### 8.2 Users Page Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Users                                                           [+ Add User]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [All ▼] [Pending (3)] [Active] [Inactive]     🔍 Search users...           │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ User                  │ Role              │ Status  │ Last Login │ Actions││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ 👤 John Smith         │ Integration Eng   │ 🟢 Active│ 2h ago    │ ⋮     ││
│  │    john@nhs.uk        │                   │         │           │       ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ 👤 Jane Doe           │ Operator          │ 🟡 Pending│ Never    │ ✓ ✗   ││
│  │    jane@nhs.uk        │                   │         │           │       ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ 👤 Bob Wilson         │ Viewer            │ 🔴 Locked│ 5d ago   │ 🔓    ││
│  │    bob@nhs.uk         │                   │         │           │       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  Showing 1-10 of 45 users                              [< 1 2 3 4 5 >]      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 User Actions

| Status | Available Actions |
|--------|-------------------|
| Pending | Approve, Reject, View |
| Active | Edit, Deactivate, Reset Password, View |
| Inactive | Activate, Delete, View |
| Locked | Unlock, Deactivate, View |
| Rejected | Activate (reconsider), Delete, View |

### 8.4 Add/Edit User Modal

```
┌─────────────────────────────────────────────────────────────────┐
│  Add New User                                              [×]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Email *                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ user@nhs.uk                                                 ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Display Name *                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ John Smith                                                  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Role *                                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Integration Engineer                                    [▼] ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Department                                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ IT Integration                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  Mobile                                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ +44 7700 900000                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ☑ Send welcome email with temporary password                   │
│  ☐ Require password change on first login                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                    [Cancel]  [Create User]  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Database Schema

### 9.1 Tables

```sql
-- Tenants table
CREATE TABLE hie_tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    max_users INTEGER DEFAULT 100,
    max_productions INTEGER DEFAULT 50,
    admin_email VARCHAR(255),
    support_email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Roles table
CREATE TABLE hie_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES hie_tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    permissions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- Users table
CREATE TABLE hie_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES hie_tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100),
    display_name VARCHAR(255) NOT NULL,
    title VARCHAR(100),
    department VARCHAR(100),
    mobile VARCHAR(50),
    avatar_url TEXT,
    password_hash VARCHAR(255) NOT NULL,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    role_id UUID NOT NULL REFERENCES hie_roles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    approved_by UUID REFERENCES hie_users(id),
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    must_change_password BOOLEAN DEFAULT FALSE,
    UNIQUE(email)
);

-- Password history table
CREATE TABLE hie_password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES hie_users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sessions table (for refresh tokens)
CREATE TABLE hie_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES hie_users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

-- Audit log table
CREATE TABLE hie_audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES hie_tenants(id),
    user_id UUID REFERENCES hie_users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_users_tenant ON hie_users(tenant_id);
CREATE INDEX idx_users_email ON hie_users(email);
CREATE INDEX idx_users_status ON hie_users(status);
CREATE INDEX idx_users_role ON hie_users(role_id);
CREATE INDEX idx_audit_tenant ON hie_audit_log(tenant_id);
CREATE INDEX idx_audit_user ON hie_audit_log(user_id);
CREATE INDEX idx_audit_created ON hie_audit_log(created_at);
CREATE INDEX idx_sessions_user ON hie_sessions(user_id);
CREATE INDEX idx_sessions_expires ON hie_sessions(expires_at);
```

---

## 10. Security Considerations

### 10.1 Authentication Security

| Measure | Implementation |
|---------|----------------|
| Password Hashing | bcrypt with cost factor 12 |
| Token Storage | httpOnly cookies (preferred) or localStorage |
| Token Validation | Signature + expiry + user status check |
| Brute Force Protection | Account lockout after 5 failed attempts |
| Session Management | Refresh token rotation, revocation support |

### 10.2 Authorization Security

| Measure | Implementation |
|---------|----------------|
| Tenant Isolation | All queries filtered by tenant_id |
| Permission Checks | Middleware validates permissions per endpoint |
| Role Hierarchy | Permissions inherited from role definition |
| Audit Logging | All admin actions logged with details |

### 10.3 Data Protection

| Measure | Implementation |
|---------|----------------|
| TLS | All API traffic over HTTPS |
| Sensitive Data | MFA secrets encrypted at rest |
| Password History | Hashed, not plaintext |
| PII Handling | Minimal data collection, GDPR compliant |

---

## 11. Implementation Plan

### Phase 1: Core Authentication (Week 1)

- [ ] Database schema and migrations
- [ ] User model and repository
- [ ] Password hashing and validation
- [ ] JWT token generation and validation
- [ ] Login/logout endpoints
- [ ] Registration endpoint
- [ ] Auth middleware

### Phase 2: User Management (Week 2)

- [ ] Admin user endpoints (CRUD)
- [ ] User approval workflow
- [ ] Status transitions (activate/deactivate/lock)
- [ ] Password reset flow
- [ ] Portal login page
- [ ] Portal register page
- [ ] Portal pending page

### Phase 3: RBAC (Week 3)

- [ ] Role model and predefined roles
- [ ] Permission definitions
- [ ] Permission checking middleware
- [ ] Role assignment to users
- [ ] Portal users page
- [ ] Portal user detail page

### Phase 4: Multi-Tenancy (Week 4)

- [ ] Tenant model and endpoints
- [ ] Tenant isolation in queries
- [ ] Tenant admin role
- [ ] Portal tenant management (super admin)
- [ ] Tenant-scoped user management

### Phase 5: Enterprise Features (Week 5)

- [ ] Refresh token rotation
- [ ] Session management
- [ ] Audit logging
- [ ] Password history
- [ ] Account lockout
- [ ] MFA preparation (TOTP)

---

## 12. Testing Strategy

### 12.1 Unit Tests

- Password validation
- Token generation/validation
- Permission checking
- Status transitions

### 12.2 Integration Tests

- Full authentication flow
- User CRUD operations
- Role assignment
- Tenant isolation

### 12.3 Security Tests

- SQL injection prevention
- XSS prevention
- CSRF protection
- Token expiry handling
- Brute force protection

---

## 13. Configuration

### 13.1 Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# Password Policy
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
PASSWORD_MAX_AGE_DAYS=90
PASSWORD_HISTORY_COUNT=5

# Security
LOCKOUT_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true

# Initial Super Admin
SUPER_ADMIN_EMAIL=admin@hie.nhs.uk
SUPER_ADMIN_PASSWORD=change-me-immediately
```

---

## 14. Migration from saas-codex

### 14.1 Components to Reuse

| Component | Source | Adaptation |
|-----------|--------|------------|
| User Model | `backend/app/models.py` | Add tenant_id, role_id, enterprise fields |
| Auth Router | `backend/app/auth/router.py` | Add tenant context, RBAC |
| Security Utils | `backend/app/auth/security.py` | Enhance password policy |
| Admin Router | `backend/app/admin/router.py` | Add tenant filtering, more actions |
| Auth Context | `frontend/src/contexts/AuthContext.tsx` | Add tenant, permissions |
| Login Page | `frontend/src/app/(auth)/login/page.tsx` | NHS branding |
| Register Page | `frontend/src/app/(auth)/register/page.tsx` | Add department, title |
| Users Page | `frontend/src/app/(app)/admin/users/page.tsx` | Add roles, tenants, more actions |

### 14.2 New Components

| Component | Description |
|-----------|-------------|
| Tenant Model | Multi-tenancy support |
| Role Model | RBAC with permissions |
| Permission Middleware | Endpoint protection |
| Tenant Context | Frontend tenant awareness |
| Roles Page | Role management UI |
| Tenants Page | Tenant management UI |

---

*This document is maintained by the HIE Core Team and updated with each sprint.*
