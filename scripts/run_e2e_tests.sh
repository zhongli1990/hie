#!/usr/bin/env bash
# =============================================================================
# OpenLI HIE — Docker E2E Test Runner
#
# Runs pytest E2E tests INSIDE a Docker container against the live stack.
# No tests run on the host macOS — everything executes in Docker.
#
# Usage:
#   ./scripts/run_e2e_tests.sh                              # All E2E tests
#   ./scripts/run_e2e_tests.sh tests/e2e/test_v194*.py      # v1.9.4 only
#   ./scripts/run_e2e_tests.sh tests/e2e/test_api_smoke.py  # Smoke only
#
# Prerequisites:
#   docker compose up -d   (stack must be running)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default: run all E2E tests
TEST_PATH="${1:-tests/e2e/}"

# Docker network name (from docker-compose.yml)
NETWORK="hie_hie-network"

# Container image — reuse the Engine dev image which has all test deps,
# or fall back to building a lightweight test image
IMAGE_NAME="hie-e2e-test"

# ─── Check prerequisites ────────────────────────────────────────────────────

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
    echo "ERROR: Docker network '$NETWORK' not found."
    echo "Start the stack first: docker compose up -d"
    exit 1
fi

# ─── Build test image (cached, fast after first run) ────────────────────────

echo "Building test image..."
docker build -t "$IMAGE_NAME" -f "$PROJECT_ROOT/Dockerfile.dev" "$PROJECT_ROOT" \
    --quiet 2>/dev/null || {
    echo "Dockerfile.dev build failed, using python:3.11-slim with inline deps..."
    docker build -t "$IMAGE_NAME" - <<'DOCKERFILE'
FROM python:3.11-slim
RUN pip install --no-cache-dir aiohttp pytest pytest-asyncio
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
DOCKERFILE
}

# ─── Read platform version from VERSION file ─────────────────────────────────

HIE_VERSION="unknown"
if [ -f "$PROJECT_ROOT/VERSION" ]; then
    HIE_VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')
fi

# ─── Run tests ──────────────────────────────────────────────────────────────

echo ""
echo "━━━ Running E2E tests: $TEST_PATH (HIE_VERSION=$HIE_VERSION) ━━━"
echo "Network: $NETWORK"
echo ""

docker run --rm \
    --network "$NETWORK" \
    -v "$PROJECT_ROOT/tests:/app/tests:ro" \
    -e PYTHONPATH=/app \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PYTHONUNBUFFERED=1 \
    -e HIE_VERSION=$HIE_VERSION \
    -e HIE_E2E_MANAGER_BASE=http://hie-manager:8081 \
    -e HIE_E2E_AGENT_BASE=http://hie-agent-runner:8082 \
    -e HIE_E2E_PROMPT_MGR_BASE=http://hie-prompt-manager:8083 \
    -e HIE_E2E_PORTAL_BASE=http://hie-portal:3000 \
    "$IMAGE_NAME" \
    pytest "$TEST_PATH" -v --tb=short "$@"

echo ""
echo "━━━ E2E tests complete ━━━"
