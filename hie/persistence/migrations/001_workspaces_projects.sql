-- Migration: 001_workspaces_projects
-- Description: Create workspaces, projects, items, connections tables for full-stack integration
-- Date: 2026-01-25

-- Workspaces (Namespaces for multi-tenancy)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
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

-- Indexes for performance
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

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
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
