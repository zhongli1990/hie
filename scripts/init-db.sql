-- HIE Database Initialization Script
-- Creates tables and indexes for PostgreSQL persistence

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
