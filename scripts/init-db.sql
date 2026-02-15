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
     '$2b$12$v0ffmoq9NEa5B.Kh8ZpgWeZx343uT4NC3d7YNgZJTnzCaWiipf2qm', 'active', 
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

-- ============================================================================
-- Workspaces and Projects Tables (Full-Stack Integration)
-- ============================================================================

-- Workspaces (Namespaces for multi-tenancy)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    tenant_id UUID REFERENCES hie_tenants(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Projects (Productions)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    state VARCHAR(50) DEFAULT 'stopped',
    version INTEGER DEFAULT 1,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    UNIQUE(workspace_id, name)
);

-- Project Items (Services, Processes, Operations)
CREATE TABLE IF NOT EXISTS project_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('service', 'process', 'operation')),
    class_name VARCHAR(255) NOT NULL,
    category VARCHAR(255),
    enabled BOOLEAN DEFAULT true,
    pool_size INTEGER DEFAULT 1,
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    adapter_settings JSONB DEFAULT '{}'::jsonb,
    host_settings JSONB DEFAULT '{}'::jsonb,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, name)
);

-- Project Connections (Routes between items)
CREATE TABLE IF NOT EXISTS project_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_item_id UUID NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    target_item_id UUID NOT NULL REFERENCES project_items(id) ON DELETE CASCADE,
    connection_type VARCHAR(50) DEFAULT 'standard' CHECK (connection_type IN ('standard', 'error', 'async')),
    enabled BOOLEAN DEFAULT true,
    filter_expression JSONB,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Routing Rules
CREATE TABLE IF NOT EXISTS project_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    condition_expression TEXT,
    action VARCHAR(50) NOT NULL CHECK (action IN ('send', 'transform', 'stop', 'delete')),
    target_items JSONB DEFAULT '[]'::jsonb,
    transform_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Versions (for config history)
CREATE TABLE IF NOT EXISTS project_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    comment TEXT,
    UNIQUE(project_id, version)
);

-- Engine Instances (running productions)
CREATE TABLE IF NOT EXISTS engine_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    engine_id VARCHAR(255) NOT NULL UNIQUE,
    state VARCHAR(50) DEFAULT 'stopped',
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    host_name VARCHAR(255),
    pid INTEGER,
    metrics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for workspace/project tables
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_state ON projects(state);
CREATE INDEX IF NOT EXISTS idx_project_items_project ON project_items(project_id);
CREATE INDEX IF NOT EXISTS idx_project_items_type ON project_items(item_type);
CREATE INDEX IF NOT EXISTS idx_project_connections_project ON project_connections(project_id);
CREATE INDEX IF NOT EXISTS idx_project_connections_source ON project_connections(source_item_id);
CREATE INDEX IF NOT EXISTS idx_project_connections_target ON project_connections(target_item_id);
CREATE INDEX IF NOT EXISTS idx_project_routing_rules_project ON project_routing_rules(project_id);
CREATE INDEX IF NOT EXISTS idx_project_versions_project ON project_versions(project_id);
CREATE INDEX IF NOT EXISTS idx_engine_instances_project ON engine_instances(project_id);

-- Create default workspace
INSERT INTO workspaces (id, name, display_name, description, settings)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'default',
    'Default Workspace',
    'Default workspace for HIE projects',
    '{"actorPoolSize": 2, "gracefulShutdownTimeout": 30}'::jsonb
) ON CONFLICT (name) DO NOTHING;

-- Triggers for workspace/project tables
DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_project_items_updated_at ON project_items;
CREATE TRIGGER update_project_items_updated_at
    BEFORE UPDATE ON project_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_project_routing_rules_updated_at ON project_routing_rules;
CREATE TRIGGER update_project_routing_rules_updated_at
    BEFORE UPDATE ON project_routing_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_engine_instances_updated_at ON engine_instances;
CREATE TRIGGER update_engine_instances_updated_at
    BEFORE UPDATE ON engine_instances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Portal Message Tracking (for Messages Tab viewer)
-- ============================================================================

-- Tracks messages flowing through the LI Engine with project/item context
CREATE TABLE IF NOT EXISTS portal_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('service', 'process', 'operation')),
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('inbound', 'outbound', 'internal')),
    message_type VARCHAR(100),
    correlation_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'processing', 'sent', 'completed', 'failed', 'error')),
    raw_content BYTEA,
    content_preview TEXT,
    content_size INTEGER DEFAULT 0,
    source_item VARCHAR(255),
    destination_item VARCHAR(255),
    remote_host VARCHAR(255),
    remote_port INTEGER,
    ack_content BYTEA,
    ack_type VARCHAR(20),
    error_message TEXT,
    latency_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- v1.8.2+ columns (session tracking & message model metadata)
    session_id VARCHAR(255),
    body_class_name VARCHAR(500) DEFAULT 'Engine.core.message.GenericMessage',
    schema_name VARCHAR(255) DEFAULT 'GenericMessage',
    schema_namespace VARCHAR(500) DEFAULT 'urn:hie:generic'
);

-- Indexes for portal message queries
CREATE INDEX IF NOT EXISTS idx_portal_messages_project ON portal_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_portal_messages_item ON portal_messages(item_name);
CREATE INDEX IF NOT EXISTS idx_portal_messages_status ON portal_messages(status);
CREATE INDEX IF NOT EXISTS idx_portal_messages_type ON portal_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_portal_messages_direction ON portal_messages(direction);
CREATE INDEX IF NOT EXISTS idx_portal_messages_received ON portal_messages(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_portal_messages_correlation ON portal_messages(correlation_id);
CREATE INDEX IF NOT EXISTS idx_portal_messages_session ON portal_messages(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_portal_messages_body_class ON portal_messages(body_class_name);
CREATE INDEX IF NOT EXISTS idx_portal_messages_schema ON portal_messages(schema_name);

-- Trigger for auto-updating timestamps
DROP TRIGGER IF EXISTS update_portal_messages_updated_at ON portal_messages;
CREATE TRIGGER update_portal_messages_updated_at
    BEFORE UPDATE ON portal_messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- GenAI Agent Tables (v1.6.0)
-- ============================================================================

-- Agent chat sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES hie_tenants(id) ON DELETE SET NULL,
    runner_type VARCHAR(50) NOT NULL DEFAULT 'claude',
    runner_thread_id VARCHAR(255),
    title VARCHAR(512),
    working_directory TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_workspace ON agent_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_project ON agent_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_created ON agent_sessions(created_at DESC);

-- Agent runs (each prompt submission within a session)
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    runner_run_id VARCHAR(255),
    prompt TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'error', 'cancelled')),
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_session ON agent_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

-- Agent run events (SSE events stored for replay)
CREATE TABLE IF NOT EXISTS agent_run_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL DEFAULT 0,
    event_type VARCHAR(100) NOT NULL,
    raw_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_run_events_run ON agent_run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_run_events_seq ON agent_run_events(run_id, seq);

-- Agent messages (user/assistant message pairs for chat persistence)
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_created ON agent_messages(session_id, created_at ASC);

-- Hooks configuration (admin-managed hook rules)
CREATE TABLE IF NOT EXISTS hooks_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(50) NOT NULL DEFAULT 'global' CHECK (scope IN ('global', 'workspace', 'project')),
    scope_id UUID,
    hook_type VARCHAR(50) NOT NULL CHECK (hook_type IN ('pre_tool_use', 'post_tool_use', 'pre_message', 'post_message')),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hooks_config_scope ON hooks_config(scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_hooks_config_type ON hooks_config(hook_type);
CREATE INDEX IF NOT EXISTS idx_hooks_config_enabled ON hooks_config(enabled);

-- Triggers for GenAI tables
DROP TRIGGER IF EXISTS update_agent_sessions_updated_at ON agent_sessions;
CREATE TRIGGER update_agent_sessions_updated_at
    BEFORE UPDATE ON agent_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_hooks_config_updated_at ON hooks_config;
CREATE TRIGGER update_hooks_config_updated_at
    BEFORE UPDATE ON hooks_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Seed default hooks
INSERT INTO hooks_config (id, scope, hook_type, name, description, config_json, enabled, priority) VALUES
    ('00000000-0000-0000-0000-000000000101', 'global', 'pre_tool_use', 'Security: Block Dangerous Commands',
     'Blocks rm -rf, sudo, fork bombs, and other dangerous bash patterns',
     '{"patterns": ["rm -rf /", "sudo rm", "chmod 777 /", ":(){:|:&};:", "curl | bash", "wget | bash"]}'::jsonb,
     true, 100),
    ('00000000-0000-0000-0000-000000000102', 'global', 'pre_tool_use', 'Security: Path Escape Prevention',
     'Blocks path traversal attempts (../) and absolute paths outside /workspaces',
     '{"blocked_patterns": ["../", "..\\\\"], "allowed_roots": ["/workspaces"]}'::jsonb,
     true, 99),
    ('00000000-0000-0000-0000-000000000103', 'global', 'pre_tool_use', 'Clinical: Protect Patient Data',
     'Blocks direct SQL manipulation of patient/clinical tables',
     '{"blocked_sql": ["DROP TABLE", "TRUNCATE", "DELETE FROM patient", "UPDATE patient SET"]}'::jsonb,
     true, 98),
    ('00000000-0000-0000-0000-000000000104', 'global', 'post_tool_use', 'Audit: Tool Usage Logging',
     'Logs all tool executions for compliance audit trail',
     '{"log_level": "info", "include_input": false, "include_output_summary": true}'::jsonb,
     true, 50),
    ('00000000-0000-0000-0000-000000000105', 'global', 'pre_tool_use', 'Compliance: NHS Data Handling',
     'Ensures NHS Number and PID data are not exposed in logs or error messages',
     '{"sensitive_patterns": ["\\\\d{3}\\\\s?\\\\d{3}\\\\s?\\\\d{4}"], "action": "redact"}'::jsonb,
     true, 97)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Prompt Manager Tables (v1.6.0)
-- Note: These are also created by prompt-manager alembic migration,
-- but included here for single-script DB init convenience.
-- ============================================================================

CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    owner_id UUID,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(256) NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'general',
    description TEXT,
    template_body TEXT NOT NULL,
    variables JSONB,
    tags JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT true,
    is_published BOOLEAN NOT NULL DEFAULT false,
    parent_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_slug ON prompt_templates(slug);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_latest ON prompt_templates(is_latest);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_slug_version ON prompt_templates(slug, version);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_tenant_latest ON prompt_templates(tenant_id, is_latest);

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    owner_id UUID,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(256) NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT 'general',
    description TEXT,
    scope VARCHAR(32) NOT NULL DEFAULT 'platform',
    skill_content TEXT NOT NULL,
    allowed_tools TEXT,
    is_user_invocable BOOLEAN NOT NULL DEFAULT true,
    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT true,
    is_published BOOLEAN NOT NULL DEFAULT false,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    parent_id UUID,
    source VARCHAR(32) NOT NULL DEFAULT 'db',
    file_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_slug ON skills(slug);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skills_latest ON skills(is_latest);
CREATE INDEX IF NOT EXISTS idx_skills_slug_version ON skills(slug, version);
CREATE INDEX IF NOT EXISTS idx_skills_tenant_latest ON skills(tenant_id, is_latest);

CREATE TABLE IF NOT EXISTS template_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID,
    template_id UUID,
    skill_id UUID,
    session_id UUID,
    rendered_prompt TEXT,
    variables_used JSONB,
    model_used VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_template_usage_user ON template_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_tenant ON template_usage_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_template ON template_usage_log(template_id);
CREATE INDEX IF NOT EXISTS idx_template_usage_skill ON template_usage_log(skill_id);

-- ============================================================================
-- GenAI Session Tables (v1.8.0 — Agents & Chat pages)
-- These are the tables actually used by GenAISessionRepository.
-- The older agent_sessions/agent_runs/agent_messages tables above are from
-- the v1.6.0 agent-runner integration and remain for backward compatibility.
-- ============================================================================

CREATE TABLE IF NOT EXISTS genai_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    runner_type VARCHAR(50) NOT NULL CHECK (runner_type IN ('claude', 'codex', 'gemini', 'azure', 'bedrock', 'openli', 'custom')),
    thread_id VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genai_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES genai_sessions(session_id) ON DELETE CASCADE,
    run_id VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_genai_sessions_workspace ON genai_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_genai_sessions_project ON genai_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_genai_sessions_created ON genai_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_genai_messages_session ON genai_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_genai_messages_created ON genai_messages(created_at ASC);

DROP TRIGGER IF EXISTS update_genai_sessions_updated_at ON genai_sessions;
CREATE TRIGGER update_genai_sessions_updated_at
    BEFORE UPDATE ON genai_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- IRIS Message Model Tables (v1.9.0 — Visual Trace per-leg tracing)
-- message_bodies: stores actual message content (one per unique message)
-- message_headers: one row per message leg (source→target), the core Visual Trace table
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_bodies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    body_class_name     VARCHAR(255) NOT NULL DEFAULT 'Ens.MessageBody',
    content_type        VARCHAR(100) NOT NULL DEFAULT 'application/octet-stream',
    raw_content         BYTEA,
    content_preview     TEXT,
    content_size        INTEGER NOT NULL DEFAULT 0,
    checksum            VARCHAR(64),
    -- HL7v2-specific columns (NULL for non-HL7 messages)
    hl7_version         VARCHAR(10),
    hl7_doc_type        VARCHAR(100),
    hl7_message_type    VARCHAR(50),
    hl7_control_id      VARCHAR(100),
    hl7_sending_app     VARCHAR(100),
    hl7_sending_fac     VARCHAR(100),
    hl7_receiving_app   VARCHAR(100),
    hl7_receiving_fac   VARCHAR(100),
    -- FHIR-specific columns (NULL for non-FHIR messages)
    fhir_version        VARCHAR(10),
    fhir_resource_type  VARCHAR(100),
    fhir_resource_id    VARCHAR(255),
    -- HTTP/Stream-specific columns (NULL for non-HTTP messages)
    http_method         VARCHAR(10),
    http_url            TEXT,
    original_filename   VARCHAR(500),
    -- Extensibility
    metadata            JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mb_checksum ON message_bodies(checksum);
CREATE INDEX IF NOT EXISTS idx_mb_class ON message_bodies(body_class_name);
CREATE INDEX IF NOT EXISTS idx_mb_created ON message_bodies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mb_hl7_type ON message_bodies(hl7_message_type) WHERE body_class_name = 'EnsLib.HL7.Message';
CREATE INDEX IF NOT EXISTS idx_mb_hl7_control ON message_bodies(hl7_control_id) WHERE body_class_name = 'EnsLib.HL7.Message';
CREATE INDEX IF NOT EXISTS idx_mb_hl7_sending ON message_bodies(hl7_sending_fac, hl7_sending_app) WHERE body_class_name = 'EnsLib.HL7.Message';
CREATE INDEX IF NOT EXISTS idx_mb_fhir_resource ON message_bodies(fhir_resource_type, fhir_resource_id) WHERE body_class_name LIKE 'EnsLib.FHIR.%';

CREATE TABLE IF NOT EXISTS message_headers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_num            BIGSERIAL,
    project_id              UUID NOT NULL,
    -- Session & Lineage
    session_id              VARCHAR(255) NOT NULL,
    parent_header_id        UUID REFERENCES message_headers(id),
    corresponding_header_id UUID REFERENCES message_headers(id),
    super_session_id        VARCHAR(255),
    -- Routing: one source → one target per row
    source_config_name      VARCHAR(255) NOT NULL,
    target_config_name      VARCHAR(255) NOT NULL,
    source_business_type    VARCHAR(50) NOT NULL,
    target_business_type    VARCHAR(50) NOT NULL,
    -- Message Classification
    message_type            VARCHAR(100),
    body_class_name         VARCHAR(255) NOT NULL DEFAULT 'Ens.MessageBody',
    message_body_id         UUID REFERENCES message_bodies(id),
    -- Invocation
    type                    VARCHAR(20) NOT NULL DEFAULT 'Request',
    invocation              VARCHAR(20) NOT NULL DEFAULT 'Queue',
    priority                VARCHAR(20) NOT NULL DEFAULT 'Async',
    -- Status & Timing
    status                  VARCHAR(50) NOT NULL DEFAULT 'Created',
    is_error                BOOLEAN NOT NULL DEFAULT FALSE,
    error_status            TEXT,
    time_created            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_processed          TIMESTAMPTZ,
    -- Extensibility
    description             TEXT,
    correlation_id          VARCHAR(255),
    metadata                JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_mh_session ON message_headers(session_id);
CREATE INDEX IF NOT EXISTS idx_mh_project ON message_headers(project_id);
CREATE INDEX IF NOT EXISTS idx_mh_sequence ON message_headers(sequence_num);
CREATE INDEX IF NOT EXISTS idx_mh_parent ON message_headers(parent_header_id);
CREATE INDEX IF NOT EXISTS idx_mh_corresponding ON message_headers(corresponding_header_id);
CREATE INDEX IF NOT EXISTS idx_mh_time ON message_headers(time_created DESC);
CREATE INDEX IF NOT EXISTS idx_mh_body ON message_headers(message_body_id);
CREATE INDEX IF NOT EXISTS idx_mh_source ON message_headers(source_config_name);
CREATE INDEX IF NOT EXISTS idx_mh_target ON message_headers(target_config_name);
CREATE INDEX IF NOT EXISTS idx_mh_status ON message_headers(status);
CREATE INDEX IF NOT EXISTS idx_mh_project_session ON message_headers(project_id, session_id);
CREATE INDEX IF NOT EXISTS idx_mh_type ON message_headers(message_type);
