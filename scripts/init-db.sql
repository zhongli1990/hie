-- HIE Database Initialization Script
-- Creates tables and indexes for PostgreSQL persistence

-- ============================================================================
-- User Management Tables
-- ============================================================================

-- Tenants table (NHS Trusts / Organizations)
CREATE TABLE IF NOT EXISTS hie_tenants (
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

CREATE INDEX IF NOT EXISTS idx_tenant_status ON hie_tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenant_code ON hie_tenants(code);

-- Roles table
CREATE TABLE IF NOT EXISTS hie_roles (
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

CREATE INDEX IF NOT EXISTS idx_role_tenant ON hie_roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_role_is_system ON hie_roles(is_system);

-- Users table
CREATE TABLE IF NOT EXISTS hie_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES hie_tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
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
    must_change_password BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_user_tenant ON hie_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_email ON hie_users(email);
CREATE INDEX IF NOT EXISTS idx_user_status ON hie_users(status);
CREATE INDEX IF NOT EXISTS idx_user_role ON hie_users(role_id);

-- Password history table
CREATE TABLE IF NOT EXISTS hie_password_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES hie_users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_history_user ON hie_password_history(user_id);

-- Sessions table (for refresh tokens)
CREATE TABLE IF NOT EXISTS hie_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES hie_users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_session_user ON hie_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_expires ON hie_sessions(expires_at);

-- ============================================================================
-- Insert System Roles
-- ============================================================================

INSERT INTO hie_roles (id, tenant_id, name, display_name, description, is_system, permissions) VALUES
    ('00000000-0000-0000-0000-000000000001', NULL, 'super_admin', 'Super Administrator', 'Full platform access, can manage all tenants and users', TRUE, 
     '["tenants:create","tenants:read","tenants:update","tenants:delete","users:create","users:read","users:update","users:delete","users:approve","productions:create","productions:read","productions:update","productions:delete","productions:start","productions:stop","messages:read","messages:resend","messages:delete","config:read","config:update","config:export","config:import","audit:read","settings:read","settings:update"]'),
    ('00000000-0000-0000-0000-000000000002', NULL, 'tenant_admin', 'Tenant Administrator', 'Full access within their tenant, can manage users', TRUE,
     '["users:create","users:read","users:update","users:delete","users:approve","productions:create","productions:read","productions:update","productions:delete","productions:start","productions:stop","messages:read","messages:resend","messages:delete","config:read","config:update","config:export","config:import","audit:read","settings:read","settings:update"]'),
    ('00000000-0000-0000-0000-000000000003', NULL, 'integration_engineer', 'Integration Engineer', 'Configure productions, items, and routes', TRUE,
     '["users:read","productions:create","productions:read","productions:update","productions:delete","productions:start","productions:stop","messages:read","messages:resend","config:read","config:update","config:export","config:import","settings:read"]'),
    ('00000000-0000-0000-0000-000000000004', NULL, 'operator', 'Operator', 'Start/stop productions, view and resend messages', TRUE,
     '["users:read","productions:read","productions:start","productions:stop","messages:read","messages:resend","config:read","settings:read"]'),
    ('00000000-0000-0000-0000-000000000005', NULL, 'viewer', 'Viewer', 'Read-only access to all resources', TRUE,
     '["users:read","productions:read","messages:read","config:read","settings:read"]'),
    ('00000000-0000-0000-0000-000000000006', NULL, 'auditor', 'Auditor', 'Read-only access plus audit log viewing', TRUE,
     '["users:read","productions:read","messages:read","config:read","settings:read","audit:read"]')
ON CONFLICT (tenant_id, name) DO NOTHING;

-- ============================================================================
-- Insert Default Super Admin User (password: Admin123!)
-- ============================================================================

INSERT INTO hie_users (id, tenant_id, email, display_name, password_hash, status, role_id, approved_at, password_changed_at) VALUES
    ('00000000-0000-0000-0000-000000000001', NULL, 'admin@hie.nhs.uk', 'System Administrator', 
     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYWWQIhXqK2G', 'active', 
     '00000000-0000-0000-0000-000000000001', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- Message Tables
-- ============================================================================

-- Messages table
CREATE TABLE IF NOT EXISTS hie_messages (
    message_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL,
    causation_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    message_type VARCHAR(255),
    priority VARCHAR(20) NOT NULL,
    state VARCHAR(50) NOT NULL,
    route_id VARCHAR(255),
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(255),
    retry_count INTEGER NOT NULL DEFAULT 0,
    content_type VARCHAR(255) NOT NULL,
    encoding VARCHAR(50) NOT NULL,
    payload_size INTEGER NOT NULL,
    raw_payload BYTEA NOT NULL,
    envelope_json JSONB NOT NULL,
    properties_json JSONB,
    stored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_messages_correlation ON hie_messages(correlation_id);
CREATE INDEX IF NOT EXISTS idx_messages_route ON hie_messages(route_id);
CREATE INDEX IF NOT EXISTS idx_messages_source ON hie_messages(source);
CREATE INDEX IF NOT EXISTS idx_messages_state ON hie_messages(state);
CREATE INDEX IF NOT EXISTS idx_messages_type ON hie_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_created ON hie_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_expires ON hie_messages(expires_at) WHERE expires_at IS NOT NULL;

-- State table for key-value storage
CREATE TABLE IF NOT EXISTS hie_state (
    key VARCHAR(512) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_state_expires ON hie_state(expires_at) WHERE expires_at IS NOT NULL;

-- Audit log table
CREATE TABLE IF NOT EXISTS hie_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(100) NOT NULL,
    message_id UUID,
    item_id VARCHAR(255),
    route_id VARCHAR(255),
    details JSONB,
    user_id VARCHAR(255),
    ip_address INET
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON hie_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_message ON hie_audit_log(message_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON hie_audit_log(event_type);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
DROP TRIGGER IF EXISTS update_messages_updated_at ON hie_messages;
CREATE TRIGGER update_messages_updated_at
    BEFORE UPDATE ON hie_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_state_updated_at ON hie_state;
CREATE TRIGGER update_state_updated_at
    BEFORE UPDATE ON hie_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hie;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hie;
