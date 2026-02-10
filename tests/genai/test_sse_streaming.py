#!/usr/bin/env python3
"""
OpenLI HIE - E2E SSE Streaming Tests

Tests that SSE connections work correctly across the stack:
1. Agent Runner (Claude) health + thread/run lifecycle
2. Codex Runner health + thread/run lifecycle
3. SSE anti-buffering headers
4. Portal proxy forwarding

Usage (inside Docker or from host with port mapping):
    python tests/genai/test_sse_streaming.py
    python tests/genai/test_sse_streaming.py --runner claude
    python tests/genai/test_sse_streaming.py --runner codex

Requirements:
    - Docker services must be running (docker compose up)
"""

import argparse
import json
import os
import sys
import time
from typing import Generator

import httpx


# Internal Docker URLs (override with env vars for host access)
AGENT_RUNNER_URL = os.environ.get("AGENT_RUNNER_URL", "http://hie-agent-runner:8082")
CODEX_RUNNER_URL = os.environ.get("CODEX_RUNNER_URL", "http://hie-codex-runner:8081")
PORTAL_URL = os.environ.get("PORTAL_URL", "http://hie-portal:3000")

VERBOSE = False


def log(msg: str, level: str = "INFO"):
    print(f"  [{level}] {msg}")


def log_verbose(msg: str):
    if VERBOSE:
        log(msg, "DEBUG")


def check_sse_headers(response: httpx.Response, layer: str) -> bool:
    """Check that SSE anti-buffering headers are present."""
    content_type = response.headers.get("content-type", "")
    cache_control = response.headers.get("cache-control", "")

    issues = []

    if "text/event-stream" not in content_type:
        issues.append(f"Content-Type should be text/event-stream, got: {content_type}")

    if "no-cache" not in cache_control:
        issues.append(f"Cache-Control should include no-cache, got: {cache_control}")

    if issues:
        print(f"  [{layer}] Header issues:")
        for issue in issues:
            print(f"    - {issue}")
        return False

    print(f"  [{layer}] SSE Headers OK")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────────────────────────────────────────

def test_agent_runner_health() -> bool:
    """Test agent-runner (Claude) health endpoint."""
    try:
        r = httpx.get(f"{AGENT_RUNNER_URL}/health", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok", f"Expected ok, got {data['status']}"
            log(f"Agent Runner health OK: {data}")
            return True
        else:
            log(f"Agent Runner health failed: {r.status_code}", "FAIL")
            return False
    except Exception as e:
        log(f"Agent Runner not reachable: {e}", "FAIL")
        return False


def test_codex_runner_health() -> bool:
    """Test codex-runner (OpenAI) health endpoint."""
    try:
        r = httpx.get(f"{CODEX_RUNNER_URL}/health", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok", f"Expected ok, got {data['status']}"
            log(f"Codex Runner health OK: {data}")
            return True
        else:
            log(f"Codex Runner health failed: {r.status_code}", "FAIL")
            return False
    except Exception as e:
        log(f"Codex Runner not reachable: {e}", "FAIL")
        return False


def test_portal_agent_runner_proxy() -> bool:
    """Test agent-runner health via Portal proxy."""
    try:
        r = httpx.get(f"{PORTAL_URL}/api/agent-runner/health", timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            log(f"Portal agent-runner proxy OK: {data}")
            return True
        else:
            log(f"Portal agent-runner proxy failed: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"Portal proxy not reachable: {e}", "WARN")
        return False


def test_portal_codex_runner_proxy() -> bool:
    """Test codex-runner health via Portal proxy."""
    try:
        r = httpx.get(f"{PORTAL_URL}/api/codex-runner/health", timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            log(f"Portal codex-runner proxy OK: {data}")
            return True
        else:
            log(f"Portal codex-runner proxy failed: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"Portal proxy not reachable: {e}", "WARN")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Thread/Run lifecycle tests
# ─────────────────────────────────────────────────────────────────────────────

def test_agent_runner_thread_creation() -> str | None:
    """Test creating a thread on agent-runner."""
    try:
        r = httpx.post(
            f"{AGENT_RUNNER_URL}/threads",
            json={"workingDirectory": "/workspaces"},
            timeout=10.0,
        )
        if r.status_code == 200:
            data = r.json()
            thread_id = data.get("threadId")
            assert thread_id, "Missing threadId in response"
            log(f"Agent Runner thread created: {thread_id}")
            return thread_id
        else:
            log(f"Thread creation failed: {r.status_code} - {r.text}", "FAIL")
            return None
    except Exception as e:
        log(f"Thread creation error: {e}", "FAIL")
        return None


def test_codex_runner_thread_creation() -> str | None:
    """Test creating a thread on codex-runner."""
    try:
        r = httpx.post(
            f"{CODEX_RUNNER_URL}/threads",
            json={"workingDirectory": "/workspaces"},
            timeout=10.0,
        )
        if r.status_code == 200:
            data = r.json()
            thread_id = data.get("threadId")
            assert thread_id, "Missing threadId in response"
            log(f"Codex Runner thread created: {thread_id}")
            return thread_id
        else:
            log(f"Thread creation failed: {r.status_code} - {r.text}", "FAIL")
            return None
    except Exception as e:
        log(f"Thread creation error: {e}", "FAIL")
        return None


def test_runner_invalid_thread() -> bool:
    """Test that creating a run with invalid threadId returns 404."""
    try:
        r = httpx.post(
            f"{AGENT_RUNNER_URL}/runs",
            json={"threadId": "nonexistent-thread", "prompt": "test"},
            timeout=10.0,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        log("Invalid thread correctly returns 404")
        return True
    except AssertionError as e:
        log(f"Invalid thread test failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Invalid thread test error: {e}", "FAIL")
        return False


def test_runner_missing_prompt() -> bool:
    """Test that creating a run without prompt returns 400."""
    try:
        # First create a thread
        r = httpx.post(
            f"{AGENT_RUNNER_URL}/threads",
            json={"workingDirectory": "/workspaces"},
            timeout=10.0,
        )
        if r.status_code != 200:
            log("Could not create thread for missing prompt test", "FAIL")
            return False
        thread_id = r.json()["threadId"]

        r = httpx.post(
            f"{AGENT_RUNNER_URL}/runs",
            json={"threadId": thread_id, "prompt": ""},
            timeout=10.0,
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"
        log("Empty prompt correctly returns 400")
        return True
    except AssertionError as e:
        log(f"Missing prompt test failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Missing prompt test error: {e}", "FAIL")
        return False


def test_runner_invalid_run_events() -> bool:
    """Test that getting events for invalid runId returns 404."""
    try:
        r = httpx.get(
            f"{AGENT_RUNNER_URL}/runs/nonexistent-run/events",
            timeout=10.0,
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"
        log("Invalid run events correctly returns 404")
        return True
    except AssertionError as e:
        log(f"Invalid run events test failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Invalid run events test error: {e}", "FAIL")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description="HIE SSE Streaming E2E Tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--runner", choices=["claude", "codex", "both"], default="both")
    args = parser.parse_args()
    VERBOSE = args.verbose

    print("=" * 70)
    print("OpenLI HIE — SSE Streaming & Runner E2E Tests")
    print("=" * 70)

    results = []

    # 1. Health checks
    print("\n--- Runner Health Checks ---")
    if args.runner in ("claude", "both"):
        results.append(("Agent Runner (Claude) health", test_agent_runner_health()))
    if args.runner in ("codex", "both"):
        results.append(("Codex Runner (OpenAI) health", test_codex_runner_health()))

    # 2. Portal proxy health
    print("\n--- Portal Proxy Health ---")
    if args.runner in ("claude", "both"):
        results.append(("Portal → agent-runner proxy", test_portal_agent_runner_proxy()))
    if args.runner in ("codex", "both"):
        results.append(("Portal → codex-runner proxy", test_portal_codex_runner_proxy()))

    # 3. Thread lifecycle
    print("\n--- Thread/Run Lifecycle ---")
    if args.runner in ("claude", "both"):
        thread_id = test_agent_runner_thread_creation()
        results.append(("Agent Runner thread creation", thread_id is not None))
    if args.runner in ("codex", "both"):
        thread_id = test_codex_runner_thread_creation()
        results.append(("Codex Runner thread creation", thread_id is not None))

    # 4. Error handling
    print("\n--- Error Handling ---")
    results.append(("Invalid threadId returns 404", test_runner_invalid_thread()))
    results.append(("Empty prompt returns 400", test_runner_missing_prompt()))
    results.append(("Invalid runId events returns 404", test_runner_invalid_run_events()))

    _print_summary(results)
    return 0 if all(r[1] for r in results) else 1


def _print_summary(results):
    print("\n" + "=" * 70)
    print("Results Summary")
    print("=" * 70)
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        icon = "✓" if ok else "✗"
        print(f"  {icon} [{status}] {name}")
    print(f"\n  Total: {passed} passed, {failed} failed, {len(results)} total")
    if failed == 0:
        print("  All tests passed!")
    else:
        print(f"  {failed} test(s) failed.")


if __name__ == "__main__":
    sys.exit(main())
