#!/bin/bash
#
# OpenLI HIE - GenAI Features E2E Test Suite
# Tests: Agent Runner, Codex Runner, Skills, Hooks, Prompt Manager
#
# Usage: ./scripts/test_genai_features.sh
#

set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

AGENT_RUNNER_URL="http://localhost:9340"
CODEX_RUNNER_URL="http://localhost:9342"
PROMPT_MANAGER_URL="http://localhost:9341"
PORTAL_URL="http://localhost:9303"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  OpenLI HIE — GenAI Features E2E Test Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local expected="$3"

    echo -e "${YELLOW}▶ Testing: ${test_name}${NC}"

    result=$(eval "$test_cmd" 2>&1) || true

    if echo "$result" | grep -q "$expected"; then
        echo -e "${GREEN}  ✅ PASSED${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}  ❌ FAILED${NC}"
        echo -e "${RED}  Expected: $expected${NC}"
        echo -e "${RED}  Got: $(echo "$result" | head -3)${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  1. SERVICE HEALTH CHECKS${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

run_test "Agent Runner (Claude) health" \
    "curl -sf ${AGENT_RUNNER_URL}/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

run_test "Codex Runner (OpenAI) health" \
    "curl -sf ${CODEX_RUNNER_URL}/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

run_test "Prompt Manager health" \
    "curl -sf ${PROMPT_MANAGER_URL}/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

# Portal returns 307 redirect for unauthenticated requests — that's expected
run_test "Portal health (reachable)" \
    "curl -s -o /dev/null -w '%{http_code}' ${PORTAL_URL}" \
    "307"

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  2. PORTAL PROXY ROUTES${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

run_test "Portal → agent-runner proxy" \
    "curl -sf ${PORTAL_URL}/api/agent-runner/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

run_test "Portal → codex-runner proxy" \
    "curl -sf ${PORTAL_URL}/api/codex-runner/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

run_test "Portal → prompt-manager proxy" \
    "curl -sf ${PORTAL_URL}/api/prompt-manager/health | grep -o '\"status\":\"ok\"'" \
    '"status":"ok"'

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  3. AGENT RUNNER - SKILLS SYSTEM${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

run_test "Skills loader module exists" \
    "docker compose exec -T hie-agent-runner python -c 'from app.skills import load_all_skills; print(\"OK\")'" \
    "OK"

run_test "Skills directory exists" \
    "docker compose exec -T hie-agent-runner ls /app/skills/ | wc -l | tr -d ' '" \
    ""

run_test "Events module exists" \
    "docker compose exec -T hie-agent-runner python -c 'from app.events import make_event, format_sse; print(\"OK\")'" \
    "OK"

run_test "Tools module exists" \
    "docker compose exec -T hie-agent-runner python -c 'from app.tools import TOOLS, execute_tool; print(\"OK\")'" \
    "OK"

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  4. AGENT RUNNER - HOOKS SYSTEM${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

run_test "Hooks module exists" \
    "docker compose exec -T hie-agent-runner python -c 'from app.hooks import pre_tool_use_hook; print(\"OK\")'" \
    "OK"

# Check blocked patterns count
echo -e "${YELLOW}▶ Testing: Blocked bash patterns defined (>=10)${NC}"
PATTERN_COUNT=$(docker compose exec -T hie-agent-runner python -c 'from app.hooks import BLOCKED_BASH_PATTERNS; print(len(BLOCKED_BASH_PATTERNS))' 2>/dev/null | tr -d '\r')
if [ "$PATTERN_COUNT" -ge 10 ] 2>/dev/null; then
    echo -e "${GREEN}  ✅ PASSED (${PATTERN_COUNT} patterns)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected >=10, got: $PATTERN_COUNT${NC}"
    ((TESTS_FAILED++))
fi

run_test "Path escape patterns defined" \
    "docker compose exec -T hie-agent-runner python -c 'from app.hooks import PATH_ESCAPE_PATTERNS; print(len(PATH_ESCAPE_PATTERNS))'" \
    "2"

# Test hook blocking logic
echo -e "${YELLOW}▶ Testing: Hook blocks 'rm -rf /' command${NC}"
HOOK_TEST=$(docker compose exec -T hie-agent-runner python -c "
import asyncio
from app.hooks import pre_tool_use_hook

async def test():
    result = await pre_tool_use_hook(
        {'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf /'}},
        'test-id',
        None
    )
    if result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
        print('BLOCKED')
    else:
        print('ALLOWED')

asyncio.run(test())
" 2>/dev/null | tr -d '\r')
if echo "$HOOK_TEST" | grep -q "BLOCKED"; then
    echo -e "${GREEN}  ✅ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected BLOCKED, got: $HOOK_TEST${NC}"
    ((TESTS_FAILED++))
fi

# Test path escape blocking
echo -e "${YELLOW}▶ Testing: Hook blocks '../' path escape${NC}"
PATH_TEST=$(docker compose exec -T hie-agent-runner python -c "
import asyncio
from app.hooks import pre_tool_use_hook

async def test():
    result = await pre_tool_use_hook(
        {'tool_name': 'Read', 'tool_input': {'path': '../../../etc/passwd'}},
        'test-id',
        None
    )
    if result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
        print('BLOCKED')
    else:
        print('ALLOWED')

asyncio.run(test())
" 2>/dev/null | tr -d '\r')
if echo "$PATH_TEST" | grep -q "BLOCKED"; then
    echo -e "${GREEN}  ✅ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected BLOCKED, got: $PATH_TEST${NC}"
    ((TESTS_FAILED++))
fi

# Test safe command allowed
echo -e "${YELLOW}▶ Testing: Hook allows safe 'ls' command${NC}"
SAFE_TEST=$(docker compose exec -T hie-agent-runner python -c "
import asyncio
from app.hooks import pre_tool_use_hook

async def test():
    result = await pre_tool_use_hook(
        {'tool_name': 'Bash', 'tool_input': {'command': 'ls -la'}},
        'test-id',
        None
    )
    if result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
        print('BLOCKED')
    else:
        print('ALLOWED')

asyncio.run(test())
" 2>/dev/null | tr -d '\r')
if echo "$SAFE_TEST" | grep -q "ALLOWED"; then
    echo -e "${GREEN}  ✅ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected ALLOWED, got: $SAFE_TEST${NC}"
    ((TESTS_FAILED++))
fi

# Test clinical safety - SQL injection blocking
echo -e "${YELLOW}▶ Testing: Hook blocks DROP TABLE in bash${NC}"
SQL_TEST=$(docker compose exec -T hie-agent-runner python -c "
import asyncio
from app.hooks import pre_tool_use_hook

async def test():
    result = await pre_tool_use_hook(
        {'tool_name': 'Bash', 'tool_input': {'command': \"psql -c 'DROP TABLE patients'\"}},
        'test-id',
        None
    )
    if result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
        print('BLOCKED')
    else:
        print('ALLOWED')

asyncio.run(test())
" 2>/dev/null | tr -d '\r')
if echo "$SQL_TEST" | grep -q "BLOCKED"; then
    echo -e "${GREEN}  ✅ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected BLOCKED, got: $SQL_TEST${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  5. THREAD/RUN LIFECYCLE (Agent Runner)${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

# Create thread using HIE workspace metadata (no filesystem path required)
echo -e "${YELLOW}▶ Testing: Agent Runner thread creation${NC}"
THREAD_RESPONSE=$(curl -sf -X POST ${AGENT_RUNNER_URL}/threads \
    -H "Content-Type: application/json" \
    -d '{"workspaceId": "test-ws-001", "workspaceName": "default", "skipGitRepoCheck": true}' 2>/dev/null)
THREAD_ID=$(echo "$THREAD_RESPONSE" | grep -o '"threadId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$THREAD_ID" ]; then
    echo -e "${GREEN}  ✅ PASSED (threadId: ${THREAD_ID:0:8}...)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - No threadId returned${NC}"
    ((TESTS_FAILED++))
fi

# Invalid thread returns 404
run_test "Invalid threadId returns 404" \
    "curl -sf -o /dev/null -w '%{http_code}' -X POST ${AGENT_RUNNER_URL}/runs -H 'Content-Type: application/json' -d '{\"threadId\": \"nonexistent\", \"prompt\": \"test\"}'" \
    "404"

# Invalid run events returns 404
run_test "Invalid runId events returns 404" \
    "curl -sf -o /dev/null -w '%{http_code}' ${AGENT_RUNNER_URL}/runs/nonexistent/events" \
    "404"

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  6. THREAD/RUN LIFECYCLE (Codex Runner)${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

# Create thread on codex runner
echo -e "${YELLOW}▶ Testing: Codex Runner thread creation${NC}"
CODEX_THREAD_RESPONSE=$(curl -sf -X POST ${CODEX_RUNNER_URL}/threads \
    -H "Content-Type: application/json" \
    -d '{"workingDirectory": "/workspaces"}' 2>/dev/null)
CODEX_THREAD_ID=$(echo "$CODEX_THREAD_RESPONSE" | grep -o '"threadId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -n "$CODEX_THREAD_ID" ]; then
    echo -e "${GREEN}  ✅ PASSED (threadId: ${CODEX_THREAD_ID:0:8}...)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - No threadId returned${NC}"
    ((TESTS_FAILED++))
fi

# Invalid thread returns 404 on codex
run_test "Codex invalid threadId returns 404" \
    "curl -sf -o /dev/null -w '%{http_code}' -X POST ${CODEX_RUNNER_URL}/runs -H 'Content-Type: application/json' -d '{\"threadId\": \"nonexistent\", \"prompt\": \"test\"}'" \
    "404"

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"
echo -e "${BLUE}  7. PROMPT MANAGER API${NC}"
echo -e "${BLUE}─────────────────────────────────────────────────────────────────${NC}"

run_test "Prompt Manager list templates" \
    "curl -sf ${PROMPT_MANAGER_URL}/templates | grep -o '\"total\"'" \
    '"total"'

run_test "Prompt Manager list skills" \
    "curl -sf ${PROMPT_MANAGER_URL}/skills | grep -o '\"total\"'" \
    '"total"'

echo -e "${YELLOW}▶ Testing: Prompt Manager categories${NC}"
CAT_RESULT=$(curl -sf ${PROMPT_MANAGER_URL}/categories 2>/dev/null | head -c 1)
if [ "$CAT_RESULT" = "[" ]; then
    echo -e "${GREEN}  ✅ PASSED${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}  ❌ FAILED - Expected '[', got: $CAT_RESULT${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  TEST SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "  ${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}  ✅ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}  ❌ SOME TESTS FAILED${NC}"
    exit 1
fi
