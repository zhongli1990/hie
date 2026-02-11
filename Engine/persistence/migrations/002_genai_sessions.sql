-- Migration: 002_genai_sessions
-- Description: Create tables for GenAI session persistence (Agents & Chat pages)
-- Date: 2026-02-11

-- GenAI Sessions (Agent/Chat conversation sessions)
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

-- GenAI Messages (conversation messages within sessions)
CREATE TABLE IF NOT EXISTS genai_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES genai_sessions(session_id) ON DELETE CASCADE,
    run_id VARCHAR(255),
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_genai_sessions_workspace ON genai_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_genai_sessions_project ON genai_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_genai_sessions_created ON genai_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_genai_messages_session ON genai_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_genai_messages_created ON genai_messages(created_at ASC);

-- Trigger to update updated_at timestamp for genai_sessions
DROP TRIGGER IF EXISTS update_genai_sessions_updated_at ON genai_sessions;
CREATE TRIGGER update_genai_sessions_updated_at
    BEFORE UPDATE ON genai_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
