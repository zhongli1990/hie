-- Migration: Fix Session ID Chains for Existing Messages
-- Date: 2026-02-10
-- Purpose: Backfill session_id for existing messages by chaining them using source/destination relationships

-- Strategy:
-- 1. Find all inbound messages (entry points - no source_item)
-- 2. For each entry point, recursively chain messages using destination_item → source_item links
-- 3. Generate one session_id per chain and update all messages in that chain

-- Step 1: Create temporary table to hold session chains
CREATE TEMPORARY TABLE session_chains (
    message_id UUID,
    session_id VARCHAR(255),
    chain_position INTEGER,
    entry_point_id UUID
);

-- Step 2: Build chains using recursive CTE
WITH RECURSIVE message_chain AS (
    -- Base case: Entry points (inbound messages with no source_item)
    SELECT
        id AS message_id,
        'SES-' || gen_random_uuid()::text AS session_id,
        1 AS chain_position,
        id AS entry_point_id,
        item_name,
        destination_item,
        received_at
    FROM portal_messages
    WHERE direction = 'inbound'
      AND (source_item IS NULL OR source_item = '')
      AND session_id IS NULL

    UNION ALL

    -- Recursive case: Follow destination_item → source_item links
    SELECT
        pm.id AS message_id,
        mc.session_id,
        mc.chain_position + 1 AS chain_position,
        mc.entry_point_id,
        pm.item_name,
        pm.destination_item,
        pm.received_at
    FROM portal_messages pm
    INNER JOIN message_chain mc
        ON pm.source_item = mc.item_name
        AND pm.received_at >= mc.received_at
        AND pm.received_at <= mc.received_at + INTERVAL '30 seconds'
    WHERE pm.session_id IS NULL
      AND mc.chain_position < 20  -- Prevent infinite loops
)
INSERT INTO session_chains (message_id, session_id, chain_position, entry_point_id)
SELECT message_id, session_id, chain_position, entry_point_id
FROM message_chain;

-- Step 3: Update portal_messages with generated session_ids
UPDATE portal_messages pm
SET session_id = sc.session_id
FROM session_chains sc
WHERE pm.id = sc.message_id;

-- Step 4: Report results
DO $$
DECLARE
    chains_created INTEGER;
    messages_updated INTEGER;
BEGIN
    SELECT COUNT(DISTINCT session_id) INTO chains_created FROM session_chains;
    SELECT COUNT(*) INTO messages_updated FROM session_chains;

    RAISE NOTICE 'Session ID backfill complete:';
    RAISE NOTICE '  - Chains created: %', chains_created;
    RAISE NOTICE '  - Messages updated: %', messages_updated;
END $$;

-- Step 5: Verify results
SELECT
    'Verification' AS stage,
    COUNT(*) AS total_messages,
    COUNT(session_id) AS messages_with_session,
    COUNT(DISTINCT session_id) AS unique_sessions,
    ROUND(COUNT(session_id)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS coverage_pct
FROM portal_messages;

-- Step 6: Show sample chains
SELECT
    sc.session_id,
    COUNT(*) AS message_count,
    STRING_AGG(pm.item_name, ' → ' ORDER BY sc.chain_position) AS pipeline_flow,
    MIN(pm.received_at) AS started_at,
    MAX(pm.received_at) AS ended_at
FROM session_chains sc
INNER JOIN portal_messages pm ON pm.id = sc.message_id
GROUP BY sc.session_id
ORDER BY MIN(pm.received_at) DESC
LIMIT 10;

-- Step 7: Drop temporary table
DROP TABLE session_chains;
