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
- Current coverage (smoke):
  - `hie-manager` health + core read endpoints
  - `hie-portal` `/api/*` rewrite/proxy to `hie-manager`
  - `hie-engine` health endpoint

Run:

```bash
# Ensure stack is running
docker compose -f docker-compose.yml up -d

# Execute E2E tests from inside the compose network
docker compose -f docker-compose.yml exec -T hie-engine pytest -q tests/e2e
```

## Running All Tests

```bash
docker compose -f docker-compose.yml up -d
docker compose -f docker-compose.yml exec -T hie-engine pytest -q
```

## Notes / Invariants

- Tests are mounted into the `hie-engine` container at `/app/tests` by `docker-compose.yml`.
- E2E tests use compose DNS names (`hie-manager`, `hie-portal`, `hie-engine`) rather than `localhost`.
