-- Migration 004: Create message_bodies and message_headers tables
--
-- Architecture Decision:
--   Option C (Hybrid) — Single message_bodies table with protocol-specific
--   nullable columns + partial indexes. body_class_name discriminator for
--   polymorphic dispatch to Python classes.
--
-- IRIS Reference:
--   In IRIS, each body class (EnsLib.HL7.Message, Ens.StreamContainer, etc.)
--   has its OWN SQL table. Ens.MessageHeader.MessageBodyClassName tells you
--   WHICH table, and MessageBodyId tells you WHICH row.
--
--   We use a single table because PostgreSQL doesn't have IRIS's class-per-table
--   inheritance. Instead, body_class_name is a discriminator column, and
--   protocol-specific columns are nullable with partial indexes.
--
-- Future: SearchTable (EAV pattern) will be added as a separate table for
--   configurable per-field indexing (equivalent to EnsLib.HL7.SearchTable).
--
-- This replaces portal_messages as the primary trace data source.
-- portal_messages is kept for backward compatibility but will be deprecated.

BEGIN;

-- ============================================================================
-- message_bodies: Stores actual message content (one per unique message)
--
-- IRIS equivalents stored in this single table:
--   Ens.MessageBody          → body_class_name = 'Ens.MessageBody'
--   EnsLib.HL7.Message       → body_class_name = 'EnsLib.HL7.Message'
--   Ens.StreamContainer      → body_class_name = 'Ens.StreamContainer'
--   EnsLib.HTTP.GenericMessage→ body_class_name = 'EnsLib.HTTP.GenericMessage'
--
-- Multiple headers can reference the same body (no content duplication).
-- ============================================================================
CREATE TABLE IF NOT EXISTS message_bodies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Polymorphic discriminator (= IRIS class name that owns this body)
    -- Maps to Python class for parsing/display
    body_class_name     VARCHAR(255) NOT NULL DEFAULT 'Ens.MessageBody',

    -- Content storage (= IRIS %Stream.Object / raw VDoc content)
    content_type        VARCHAR(100) NOT NULL DEFAULT 'application/octet-stream',
    raw_content         BYTEA,
    content_preview     TEXT,           -- First 500 chars for UI display
    content_size        INTEGER NOT NULL DEFAULT 0,
    checksum            VARCHAR(64),    -- SHA-256 for dedup

    -- HL7v2-specific columns (NULL for non-HL7 messages)
    -- Populated when body_class_name = 'EnsLib.HL7.Message'
    hl7_version         VARCHAR(10),    -- "2.3", "2.4", "2.5.1"
    hl7_doc_type        VARCHAR(100),   -- Schema DocType e.g. "2.4:ADT_A01"
    hl7_message_type    VARCHAR(50),    -- MSH-9 e.g. "ADT^A01^ADT_A01"
    hl7_control_id      VARCHAR(100),   -- MSH-10
    hl7_sending_app     VARCHAR(100),   -- MSH-3
    hl7_sending_fac     VARCHAR(100),   -- MSH-4
    hl7_receiving_app   VARCHAR(100),   -- MSH-5
    hl7_receiving_fac   VARCHAR(100),   -- MSH-6

    -- FHIR-specific columns (NULL for non-FHIR messages)
    -- Populated when body_class_name = 'EnsLib.FHIR.Message' or similar
    fhir_version        VARCHAR(10),    -- "R4", "R5"
    fhir_resource_type  VARCHAR(100),   -- "Patient", "Bundle", "Observation"
    fhir_resource_id    VARCHAR(255),

    -- HTTP/Stream-specific columns (NULL for non-HTTP messages)
    -- Populated when body_class_name = 'Ens.StreamContainer' or 'EnsLib.HTTP.GenericMessage'
    http_method         VARCHAR(10),    -- "GET", "POST"
    http_url            TEXT,
    original_filename   VARCHAR(500),

    -- Generic extensibility (long-tail protocol fields go here)
    metadata            JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Core indexes
CREATE INDEX IF NOT EXISTS idx_mb_checksum ON message_bodies(checksum);
CREATE INDEX IF NOT EXISTS idx_mb_class ON message_bodies(body_class_name);
CREATE INDEX IF NOT EXISTS idx_mb_created ON message_bodies(created_at DESC);

-- HL7 partial indexes (only index rows where HL7 columns are populated)
CREATE INDEX IF NOT EXISTS idx_mb_hl7_type
    ON message_bodies(hl7_message_type)
    WHERE body_class_name = 'EnsLib.HL7.Message';
CREATE INDEX IF NOT EXISTS idx_mb_hl7_control
    ON message_bodies(hl7_control_id)
    WHERE body_class_name = 'EnsLib.HL7.Message';
CREATE INDEX IF NOT EXISTS idx_mb_hl7_sending
    ON message_bodies(hl7_sending_fac, hl7_sending_app)
    WHERE body_class_name = 'EnsLib.HL7.Message';

-- FHIR partial indexes
CREATE INDEX IF NOT EXISTS idx_mb_fhir_resource
    ON message_bodies(fhir_resource_type, fhir_resource_id)
    WHERE body_class_name LIKE 'EnsLib.FHIR.%';

-- ============================================================================
-- message_headers: One row per message leg (the core Visual Trace table)
--
-- Each row represents a message crossing from one item to another.
-- The Visual Trace draws one arrow per row.
-- Equivalent to IRIS Ens.MessageHeader (SQL: Ens.MessageHeader)
--
-- IRIS Ens.MessageHeaderBase properties mapped:
--   SessionId              → session_id
--   CorrespondingMessageId → corresponding_header_id
--   SourceConfigName       → source_config_name
--   TargetConfigName       → target_config_name
--   SourceBusinessType     → source_business_type
--   TargetBusinessType     → target_business_type
--   MessageBodyClassName   → body_class_name
--   MessageBodyId          → message_body_id
--   Type                   → type (Request/Response)
--   Invocation             → invocation (Queue/InProc)
--   Priority               → priority (Async/Sync/SimSync)
--   Status                 → status
--   IsError                → is_error
--   ErrorStatus            → error_status
--   TimeCreated            → time_created
--   TimeProcessed          → time_processed
--   SuperSession           → super_session_id
--   Description            → description
-- ============================================================================
CREATE TABLE IF NOT EXISTS message_headers (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_num            BIGSERIAL,      -- Global ordering (= IRIS auto-increment ID)
    project_id              UUID NOT NULL,

    -- Session & Lineage
    session_id              VARCHAR(255) NOT NULL,
    parent_header_id        UUID REFERENCES message_headers(id),
    corresponding_header_id UUID REFERENCES message_headers(id),
    super_session_id        VARCHAR(255),

    -- Routing: one source → one target per row
    source_config_name      VARCHAR(255) NOT NULL,
    target_config_name      VARCHAR(255) NOT NULL,
    source_business_type    VARCHAR(50) NOT NULL,  -- service/process/operation
    target_business_type    VARCHAR(50) NOT NULL,

    -- Message Classification (polymorphic body reference)
    message_type            VARCHAR(100),   -- e.g. "ADT^A01" for display
    body_class_name         VARCHAR(255) NOT NULL DEFAULT 'Ens.MessageBody',
    message_body_id         UUID REFERENCES message_bodies(id),

    -- Invocation
    type                    VARCHAR(20) NOT NULL DEFAULT 'Request',  -- Request/Response
    invocation              VARCHAR(20) NOT NULL DEFAULT 'Queue',    -- Queue/InProc
    priority                VARCHAR(20) NOT NULL DEFAULT 'Async',    -- Async/Sync/SimSync

    -- Status & Timing
    status                  VARCHAR(50) NOT NULL DEFAULT 'Created',
    is_error                BOOLEAN NOT NULL DEFAULT FALSE,
    error_status            TEXT,
    time_created            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_processed          TIMESTAMPTZ,

    -- Extensibility
    description             TEXT,
    correlation_id          VARCHAR(255),   -- HL7 MSH-10 or protocol correlation
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

COMMIT;
