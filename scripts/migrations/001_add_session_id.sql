-- Migration: Add session_id column to portal_messages
-- Date: 2026-02-12
-- Description: Adds session_id column for message session tracking and grouping

BEGIN;

-- Add session_id column
ALTER TABLE portal_messages
ADD COLUMN IF NOT EXISTS session_id VARCHAR(255);

-- Create index for session_id queries
CREATE INDEX IF NOT EXISTS idx_portal_messages_session ON portal_messages(session_id);

-- Populate session_id from correlation_id for existing messages
-- Messages with same correlation_id are part of the same session
UPDATE portal_messages
SET session_id = correlation_id
WHERE correlation_id IS NOT NULL AND session_id IS NULL;

-- For messages without correlation_id, generate session_id based on:
-- project + item + time window (5 second grouping)
UPDATE portal_messages
SET session_id =
    'SES-' ||
    substring(project_id::text, 1, 8) || '-' ||
    substring(md5(item_name), 1, 8) || '-' ||
    to_char(date_trunc('minute', received_at), 'YYYYMMDDHH24MI') || '-' ||
    to_char(extract(epoch from received_at)::integer % 60 / 5, 'FM00')
WHERE session_id IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN portal_messages.session_id IS 'Session identifier for grouping related messages in end-to-end flows';

COMMIT;

-- Verification query
SELECT
    'Total messages' as metric,
    COUNT(*) as count
FROM portal_messages
UNION ALL
SELECT
    'Messages with session_id' as metric,
    COUNT(*) as count
FROM portal_messages
WHERE session_id IS NOT NULL
UNION ALL
SELECT
    'Unique sessions' as metric,
    COUNT(DISTINCT session_id) as count
FROM portal_messages;
