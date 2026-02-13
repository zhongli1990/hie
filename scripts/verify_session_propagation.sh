#!/bin/bash
# Session ID Propagation Verification Script
# Run this after sending a test HL7 message to verify end-to-end session tracking

set -e

echo "========================================="
echo "Session ID Propagation Verification"
echo "========================================="
echo ""

# Check database connection
echo "[1/5] Checking database connection..."
docker exec hie-postgres psql -U hie -d hie -c "SELECT version();" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database connected"
else
    echo "❌ Database connection failed"
    exit 1
fi
echo ""

# Check hie-manager service
echo "[2/5] Checking hie-manager service..."
docker ps --filter "name=hie-manager" --format "{{.Status}}" | grep -q "Up"
if [ $? -eq 0 ]; then
    echo "✅ hie-manager is running"
else
    echo "❌ hie-manager is not running"
    exit 1
fi
echo ""

# Check message store pool
echo "[3/5] Checking message store initialization..."
docker logs hie-manager 2>&1 | grep -q "message_store_pool_set"
if [ $? -eq 0 ]; then
    echo "✅ Message store initialized"
else
    echo "⚠️  Message store may not be initialized"
fi
echo ""

# Show recent messages with session tracking
echo "[4/5] Recent messages with session tracking:"
echo "---------------------------------------------"
docker exec hie-postgres psql -U hie -d hie -c "
SELECT
    item_name,
    item_type,
    direction,
    session_id,
    correlation_id,
    status,
    TO_CHAR(received_at, 'HH24:MI:SS') as time
FROM portal_messages
WHERE received_at >= NOW() - INTERVAL '1 hour'
ORDER BY received_at DESC
LIMIT 20;
"
echo ""

# Analyze session chains
echo "[5/5] Session chain analysis:"
echo "------------------------------"
docker exec hie-postgres psql -U hie -d hie -c "
WITH session_stats AS (
    SELECT
        session_id,
        COUNT(*) as message_count,
        COUNT(DISTINCT item_name) as item_count,
        COUNT(DISTINCT item_type) as type_count,
        STRING_AGG(DISTINCT item_type, ', ' ORDER BY item_type) as types_involved,
        STRING_AGG(item_name, ' → ' ORDER BY received_at) as pipeline_flow,
        MIN(received_at) as started_at,
        MAX(received_at) as ended_at,
        EXTRACT(EPOCH FROM (MAX(received_at) - MIN(received_at))) * 1000 as duration_ms
    FROM portal_messages
    WHERE session_id IS NOT NULL
    GROUP BY session_id
)
SELECT
    session_id,
    message_count,
    item_count,
    types_involved,
    ROUND(duration_ms::NUMERIC, 2) as duration_ms,
    pipeline_flow
FROM session_stats
WHERE started_at >= NOW() - INTERVAL '1 hour'
ORDER BY started_at DESC
LIMIT 10;
"
echo ""

# Check for complete sessions (Service → Process → Operation)
echo "Checking for complete session chains:"
echo "---------------------------------------"
docker exec hie-postgres psql -U hie -d hie -c "
WITH session_types AS (
    SELECT
        session_id,
        BOOL_OR(item_type = 'service') as has_service,
        BOOL_OR(item_type = 'process') as has_process,
        BOOL_OR(item_type = 'operation') as has_operation,
        COUNT(*) as message_count
    FROM portal_messages
    WHERE session_id IS NOT NULL
      AND received_at >= NOW() - INTERVAL '1 hour'
    GROUP BY session_id
)
SELECT
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE has_service AND has_process AND has_operation) as complete_sessions,
    COUNT(*) FILTER (WHERE has_service AND has_process AND NOT has_operation) as incomplete_sessions,
    ROUND(
        COUNT(*) FILTER (WHERE has_service AND has_process AND has_operation)::NUMERIC /
        NULLIF(COUNT(*), 0) * 100,
        2
    ) as completion_rate_pct
FROM session_types;
"
echo ""

# Success criteria
echo "========================================="
echo "✅ SUCCESS CRITERIA FOR E2E PROPAGATION:"
echo "========================================="
echo "1. ✅ New messages should have session_id (not NULL)"
echo "2. ✅ All messages in same flow should share SAME session_id"
echo "3. ✅ Session should include Service, Process, AND Operation types"
echo "4. ✅ Pipeline flow should show: Service → Process → Operation(s)"
echo "5. ✅ Duration should be reasonable (< 5 seconds for typical flow)"
echo ""
echo "To test end-to-end:"
echo "  1. Ensure ADT001 project is started (PAS-In listening on port 10001)"
echo "  2. Send test HL7 message: echo -ne '<HL7_MESSAGE>' | nc localhost 10001"
echo "  3. Re-run this script to verify session propagation"
echo ""
