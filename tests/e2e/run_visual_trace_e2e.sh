#!/usr/bin/env bash
# =============================================================================
# Visual Trace E2E Quick Test — run from host machine
#
# Usage:
#   bash tests/e2e/run_visual_trace_e2e.sh
#
# Prerequisites:
#   - Docker Compose stack running
#   - ADT001 project started
#   - Migration 004 applied
# =============================================================================
set -euo pipefail

MANAGER_BASE="${HIE_E2E_MANAGER_BASE:-http://localhost:9302}"
MLLP_HOST="${HIE_E2E_MLLP_HOST:-localhost}"
MLLP_PORT="${HIE_E2E_MLLP_PORT:-10001}"
PASS=0
FAIL=0
SKIP=0

green()  { printf "\033[32m%s\033[0m\n" "$*"; }
red()    { printf "\033[31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

pass() { PASS=$((PASS+1)); green "  ✅ PASS: $1"; }
fail() { FAIL=$((FAIL+1)); red   "  ❌ FAIL: $1"; }
skip() { SKIP=$((SKIP+1)); yellow "  ⚠️  SKIP: $1"; }

echo "============================================"
echo " Visual Trace E2E Test Suite"
echo " Manager: $MANAGER_BASE"
echo " MLLP:    $MLLP_HOST:$MLLP_PORT"
echo "============================================"
echo ""

# -------------------------------------------------------
# Test 1: Manager health
# -------------------------------------------------------
echo "Test 1: Manager API health"
HEALTH=$(curl -sf "$MANAGER_BASE/api/health" 2>/dev/null || echo '{}')
if echo "$HEALTH" | python3 -c "import sys,json; assert json.load(sys.stdin).get('status')=='healthy'" 2>/dev/null; then
    pass "Manager is healthy"
else
    fail "Manager not healthy: $HEALTH"
fi

# -------------------------------------------------------
# Test 2: Migration tables exist
# -------------------------------------------------------
echo "Test 2: Migration 004 tables exist"
TABLE_COUNT=$(docker exec hie-postgres psql -U hie -d hie -t -c \
    "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND tablename IN ('message_headers','message_bodies');" \
    2>/dev/null | tr -d ' ')
if [ "$TABLE_COUNT" = "2" ]; then
    pass "message_headers + message_bodies tables exist"
else
    fail "Expected 2 tables, found $TABLE_COUNT — run migration 004"
fi

# -------------------------------------------------------
# Test 3: Send HL7 via MLLP and check ACK
# -------------------------------------------------------
echo "Test 3: Send HL7 ADT^A01 via MLLP"
CONTROL_ID="E2E-SH-$(date +%s)"
TS=$(date -u +%Y%m%d%H%M%S)
HL7_MSG="MSH|^~\\&|PAS|BHR|EPR|BHR|${TS}||ADT^A01^ADT_A01|${CONTROL_ID}|P|2.4\rEVN|A01|${TS}\rPID|||E2E-${CONTROL_ID}^^^MRN||ShellTest^E2E||19900101|M\rPV1||I|WARD1^BED1^1|E|||9999^Doc^E2E|||MED||||||||9999^Doc^E2E|IP|||||||||||||||||||BHR|||||${TS}\r"

ACK=$(python3 -c "
import socket
msg = '''${HL7_MSG}'''
frame = b'\x0b' + msg.encode('ascii') + b'\x1c\x0d'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
s.connect(('${MLLP_HOST}', ${MLLP_PORT}))
s.sendall(frame)
data = b''
while b'\x1c\x0d' not in data:
    chunk = s.recv(4096)
    if not chunk: break
    data += chunk
s.close()
print(data.replace(b'\x0b',b'').replace(b'\x1c\x0d',b'').decode('ascii',errors='replace'))
" 2>&1)

if echo "$ACK" | grep -q "MSA|AA"; then
    pass "Received ACK: MSA|AA"
elif echo "$ACK" | grep -q "MSA|CA"; then
    pass "Received ACK: MSA|CA"
else
    fail "Bad ACK: $ACK"
fi

# Wait for async processing
sleep 2

# -------------------------------------------------------
# Test 4: message_headers rows created
# -------------------------------------------------------
echo "Test 4: message_headers rows created"
HDR_COUNT=$(docker exec hie-postgres psql -U hie -d hie -t -c \
    "SELECT COUNT(*) FROM message_headers WHERE correlation_id = '${CONTROL_ID}';" \
    2>/dev/null | tr -d ' ')
if [ "$HDR_COUNT" -ge 1 ] 2>/dev/null; then
    pass "Found $HDR_COUNT message_headers rows for control_id=$CONTROL_ID"
else
    fail "No message_headers found for control_id=$CONTROL_ID"
fi

# -------------------------------------------------------
# Test 5: message_bodies row created
# -------------------------------------------------------
echo "Test 5: message_bodies row created with HL7 metadata"
BODY_CLASS=$(docker exec hie-postgres psql -U hie -d hie -t -c \
    "SELECT b.body_class_name FROM message_bodies b
     JOIN message_headers h ON h.message_body_id = b.id
     WHERE h.correlation_id = '${CONTROL_ID}' LIMIT 1;" \
    2>/dev/null | tr -d ' ')
if [ "$BODY_CLASS" = "EnsLib.HL7.Message" ]; then
    pass "Body class = EnsLib.HL7.Message"
elif [ -n "$BODY_CLASS" ]; then
    pass "Body class = $BODY_CLASS (non-empty)"
else
    fail "No message_bodies found for control_id=$CONTROL_ID"
fi

# -------------------------------------------------------
# Test 6: Trace API returns v2
# -------------------------------------------------------
echo "Test 6: GET /api/sessions/{session_id}/trace returns v2"
SESSION_ID=$(docker exec hie-postgres psql -U hie -d hie -t -c \
    "SELECT session_id FROM message_headers WHERE correlation_id = '${CONTROL_ID}' LIMIT 1;" \
    2>/dev/null | tr -d ' ')

if [ -z "$SESSION_ID" ]; then
    fail "Could not find session_id for control_id=$CONTROL_ID"
else
    TRACE=$(curl -sf "$MANAGER_BASE/api/sessions/${SESSION_ID}/trace" 2>/dev/null || echo '{}')
    TRACE_VER=$(echo "$TRACE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('trace_version',''))" 2>/dev/null)
    if [ "$TRACE_VER" = "v2" ]; then
        pass "trace_version = v2"
    else
        fail "trace_version = '$TRACE_VER' (expected v2)"
    fi
fi

# -------------------------------------------------------
# Test 7: Trace items sorted correctly
# -------------------------------------------------------
echo "Test 7: Trace items sorted (service → process → operation)"
if [ -n "$SESSION_ID" ]; then
    SORTED=$(echo "$TRACE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('items', [])
order = {'service': 0, 'process': 1, 'operation': 2}
orders = [order.get(i['item_type'], 3) for i in items]
print('sorted' if orders == sorted(orders) else 'unsorted')
" 2>/dev/null)
    if [ "$SORTED" = "sorted" ]; then
        pass "Items sorted correctly"
    else
        fail "Items not sorted"
    fi
else
    skip "No session_id available"
fi

# -------------------------------------------------------
# Test 8: Trace messages have source/target
# -------------------------------------------------------
echo "Test 8: Trace messages have source + target (arrows)"
if [ -n "$SESSION_ID" ]; then
    ARROWS_OK=$(echo "$TRACE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
msgs = d.get('messages', [])
ok = all(m.get('source_config_name') and m.get('target_config_name') for m in msgs)
print('ok' if ok and len(msgs) > 0 else 'fail')
" 2>/dev/null)
    if [ "$ARROWS_OK" = "ok" ]; then
        MSG_COUNT=$(echo "$TRACE" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('messages',[])))" 2>/dev/null)
        pass "All $MSG_COUNT messages have source + target"
    else
        fail "Some messages missing source/target"
    fi
else
    skip "No session_id available"
fi

# -------------------------------------------------------
# Test 9: Nonexistent session returns 404
# -------------------------------------------------------
echo "Test 9: Nonexistent session returns 404"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$MANAGER_BASE/api/sessions/SES-00000000-0000-0000-0000-000000000000/trace")
if [ "$HTTP_CODE" = "404" ]; then
    pass "Nonexistent session returns 404"
else
    fail "Expected 404, got $HTTP_CODE"
fi

# -------------------------------------------------------
# Summary
# -------------------------------------------------------
echo ""
echo "============================================"
TOTAL=$((PASS + FAIL + SKIP))
echo " Results: $PASS passed, $FAIL failed, $SKIP skipped / $TOTAL total"
echo "============================================"

# Cleanup hint
echo ""
echo "Cleanup E2E test data:"
echo "  docker exec hie-postgres psql -U hie -d hie -c \\"
echo "    \"DELETE FROM message_headers WHERE correlation_id LIKE 'E2E-%';\""

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
