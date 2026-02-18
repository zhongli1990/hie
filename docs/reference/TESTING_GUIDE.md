# Testing Guide

This project is designed to be verified **inside Docker** using the primary `docker-compose.yml` stack.

## Test Suites

### `tests/unit/`

- Purpose: pure unit tests for core models and utilities.
- Characteristics:
  - no Docker service dependencies
  - no external network calls
  - should be fast and deterministic

Run:

```bash
docker compose -f docker-compose.yml exec -T hie-engine pytest -q tests/unit
```

### `tests/integration/`

- Purpose: in-process component integration tests.
- Example: starting a real `HTTPReceiver` aiohttp server on a test port, then posting a message.

Run:

```bash
docker compose -f docker-compose.yml exec -T hie-engine pytest -q tests/integration
```

### `tests/li/`

- Purpose: LI engine (IRIS-compatible) subsystem tests.
- Characteristics:
  - asyncio-heavy tests
  - may spin up ephemeral local servers/sockets inside the container

Run:

```bash
docker compose -f docker-compose.yml exec -T hie-engine pytest -q tests/li
```

### `tests/e2e/`

- Purpose: Docker-network E2E tests that hit **running services** in the compose stack.
- Characteristics:
  - Run inside Docker containers, NOT on the host macOS
  - Use compose DNS names (`hie-manager`, `hie-portal`, `hie-engine`, `hie-agent-runner`, `hie-prompt-manager`)
  - Tests communicate over the `hie_hie-network` Docker network

#### Smoke Tests (`test_api_smoke.py`)

- Coverage: `hie-manager` health + core read endpoints, `hie-portal` `/api/*` rewrite/proxy, `hie-engine` health
- 5 tests

#### v1.9.4 Feature Tests (`test_v194_rbac_audit_approvals.py`)

- Coverage: Comprehensive E2E validation of Unified RBAC, Audit Logging, and Approval Workflows
- 38 tests organised by feature requirements:

| Section | Tests | Coverage |
|---------|-------|----------|
| Health Checks | 3 | All services healthy, version = 1.9.4 |
| Demo Login (FR-5) | 7 | All 7 demo users login, receive valid JWT |
| Role Alignment (GR-1) | 8 | Each role resolves correctly via `/roles/me` |
| Audit Logging (GR-2) | 5 | Create entry, PII sanitisation, list with auth, stats |
| Approval Workflows (GR-3) | 7 | Create, list, approve, reject, role-gated access |
| RBAC Regression | 4 | Tool filtering, deploy blocked for dev, viewer read-only |
| Portal Pages | 3 | Audit + Approvals admin pages return 200 |
| Version Consistency | 1 | All services report version 1.9.4 |

Run individual suites:

```bash
# Ensure stack is running
docker compose up -d

# Run smoke tests only
make test-e2e-smoke

# Run v1.9.4 feature tests only
make test-e2e-v194

# Run all E2E tests
make test-e2e
```

#### v1.9.5 Feature Tests (`test_v195_snapshots_crud_envdeploy.py`)

- Coverage: Config Snapshots (GR-4), CRUD Tools (FR-3/FR-10), Environment Deploy, Rate Limiting
- ~22 tests organised by feature:

| Section | Tests | Coverage |
|---------|-------|----------|
| CRUD Tools | 6 | Update/delete item, connection, routing rule |
| Config Snapshots | 4 | Auto-snapshot on deploy, list versions, get version, rollback |
| Environment Deploy | 4 | Staging deploy (no approval), production deploy (approval), operator direct |
| Rate Limiting | 3 | Normal allowed, burst blocked, window reset |
| RBAC for New Tools | 4 | Developer CRUD, viewer blocked, operator rollback, auditor read-only |
| DEV_USER Disable | 1 | Auth required when flag set |

```bash
# Run v1.9.5 feature tests
make test-e2e-v195
```

#### E2E Test Runner (`scripts/run_e2e_tests.sh`)

The test runner:
1. Builds a test image from `Dockerfile.dev` (includes aiohttp, pytest, pytest-asyncio)
2. Mounts `tests/` directory read-only into the container
3. Connects the container to `hie_hie-network`
4. Sets service URL environment variables for container DNS names
5. Executes pytest inside the container

```bash
# Direct usage (if not using Makefile)
./scripts/run_e2e_tests.sh tests/e2e/test_v194_rbac_audit_approvals.py -v --tb=long
```

### `tests/genai/`

- Purpose: standalone prompt-manager API tests (httpx, sync).
- Can run directly without the full Docker stack if prompt-manager is available.

## Running All Tests

```bash
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml exec -T hie-engine pytest -q
```

## Running E2E Tests (Recommended)

```bash
# Start the full stack
docker compose up -d --build

# Run all E2E tests via the Docker test runner
make test-e2e

# Or run specific test files
make test-e2e-v194     # v1.9.4 RBAC/Audit/Approvals
make test-e2e-smoke    # Smoke tests
```

## Notes / Invariants

- Tests are mounted into the `hie-engine` container at `/app/tests` by `docker-compose.yml`.
- E2E tests use compose DNS names (`hie-manager`, `hie-portal`, `hie-engine`, `hie-agent-runner`, `hie-prompt-manager`) rather than `localhost`.
- E2E tests NEVER run on the host macOS — they always run inside Docker containers on the compose network.
- The E2E test runner (`scripts/run_e2e_tests.sh`) builds its own lightweight test image with the required dependencies.
- Test state is passed between sequential tests using module-level `_state: dict = {}` dictionaries (e.g., tokens from login tests used in subsequent auth tests).
