-- Migration: Add Message Model Metadata Columns
-- Date: 2026-02-10
-- Purpose: Add session_id, body_class_name, and schema_name to support meta message model

-- Step 1: Add session_id column (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'portal_messages' AND column_name = 'session_id'
    ) THEN
        ALTER TABLE portal_messages
        ADD COLUMN session_id VARCHAR(255);

        CREATE INDEX IF NOT EXISTS idx_portal_messages_session
        ON portal_messages(session_id)
        WHERE session_id IS NOT NULL;

        RAISE NOTICE 'Added session_id column and index';
    ELSE
        RAISE NOTICE 'session_id column already exists';
    END IF;
END $$;

-- Step 2: Add body_class_name column (meta class for processing intelligence)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'portal_messages' AND column_name = 'body_class_name'
    ) THEN
        ALTER TABLE portal_messages
        ADD COLUMN body_class_name VARCHAR(500) DEFAULT 'Engine.core.message.GenericMessage';

        CREATE INDEX IF NOT EXISTS idx_portal_messages_body_class
        ON portal_messages(body_class_name);

        RAISE NOTICE 'Added body_class_name column and index';
    ELSE
        RAISE NOTICE 'body_class_name column already exists';
    END IF;
END $$;

-- Step 3: Add schema_name column (payload schema type)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'portal_messages' AND column_name = 'schema_name'
    ) THEN
        ALTER TABLE portal_messages
        ADD COLUMN schema_name VARCHAR(255) DEFAULT 'GenericMessage';

        CREATE INDEX IF NOT EXISTS idx_portal_messages_schema
        ON portal_messages(schema_name);

        RAISE NOTICE 'Added schema_name column and index';
    ELSE
        RAISE NOTICE 'schema_name column already exists';
    END IF;
END $$;

-- Step 4: Add schema_namespace column (schema URI/namespace)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'portal_messages' AND column_name = 'schema_namespace'
    ) THEN
        ALTER TABLE portal_messages
        ADD COLUMN schema_namespace VARCHAR(500) DEFAULT 'urn:hie:generic';

        RAISE NOTICE 'Added schema_namespace column';
    ELSE
        RAISE NOTICE 'schema_namespace column already exists';
    END IF;
END $$;

-- Step 5: Populate body_class_name based on content_type (for existing messages)
UPDATE portal_messages
SET body_class_name = CASE
    WHEN message_type LIKE '%HL7%' OR message_type LIKE 'ADT%' OR message_type LIKE 'ORU%' OR message_type LIKE 'ORM%'
        THEN 'Engine.li.messages.hl7.HL7Message'
    WHEN message_type LIKE '%FHIR%' OR message_type LIKE 'Patient%' OR message_type LIKE 'Observation%'
        THEN 'Engine.li.messages.fhir.FHIRResource'
    ELSE 'Engine.core.message.GenericMessage'
END
WHERE body_class_name = 'Engine.core.message.GenericMessage';

-- Step 6: Populate schema_name from message_type (for existing messages)
UPDATE portal_messages
SET schema_name = CASE
    WHEN message_type IS NOT NULL AND message_type != ''
        THEN message_type
    ELSE 'GenericMessage'
END
WHERE schema_name = 'GenericMessage' AND message_type IS NOT NULL AND message_type != '';

-- Step 7: Populate schema_namespace based on body_class_name
UPDATE portal_messages
SET schema_namespace = CASE
    WHEN body_class_name LIKE '%hl7%'
        THEN 'urn:hl7-org:v2'
    WHEN body_class_name LIKE '%fhir%'
        THEN 'http://hl7.org/fhir'
    ELSE 'urn:hie:generic'
END
WHERE schema_namespace = 'urn:hie:generic';

-- Step 8: Verification Report
SELECT
    'Migration Complete' AS status,
    COUNT(*) AS total_messages,
    COUNT(session_id) AS messages_with_session,
    COUNT(DISTINCT body_class_name) AS distinct_body_classes,
    COUNT(DISTINCT schema_name) AS distinct_schemas
FROM portal_messages;

-- Step 9: Show sample data
SELECT
    id,
    session_id,
    body_class_name,
    schema_name,
    schema_namespace,
    message_type,
    item_name,
    direction
FROM portal_messages
ORDER BY received_at DESC
LIMIT 10;
