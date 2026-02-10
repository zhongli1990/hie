#!/usr/bin/env python3
"""
OpenLI HIE - E2E API Tests for Prompt & Skills Manager

Tests the full CRUD lifecycle for prompt templates and skills,
including rendering, publishing, and categories.

Usage (inside Docker or from host):
    python tests/genai/test_prompt_manager_api.py
    python tests/genai/test_prompt_manager_api.py -v

Requirements:
    - Docker services must be running (docker compose up)
    - prompt-manager service must be healthy
"""

import argparse
import json
import os
import sys
import uuid

import httpx

# Internal Docker URLs (override with env vars for host access)
PROMPT_MANAGER_URL = os.environ.get("PROMPT_MANAGER_URL", "http://hie-prompt-manager:8083")
PORTAL_URL = os.environ.get("PORTAL_URL", "http://hie-portal:3000")

VERBOSE = False


def log(msg: str, level: str = "INFO"):
    print(f"  [{level}] {msg}")


def log_verbose(msg: str):
    if VERBOSE:
        log(msg, "DEBUG")


# ─────────────────────────────────────────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────────────────────────────────────────

def test_health_check() -> bool:
    """Test prompt-manager health endpoint."""
    try:
        r = httpx.get(f"{PROMPT_MANAGER_URL}/health", timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            assert data["status"] == "ok", f"Expected ok, got {data['status']}"
            log(f"Health OK: {data}")
            return True
        else:
            log(f"Health check failed: {r.status_code}", "FAIL")
            return False
    except Exception as e:
        log(f"Health check error: {e}", "FAIL")
        return False


def test_health_via_portal() -> bool:
    """Test prompt-manager health via Portal proxy."""
    try:
        r = httpx.get(f"{PORTAL_URL}/api/prompt-manager/health", timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            log(f"Portal proxy health OK: {data}")
            return True
        else:
            log(f"Portal proxy health failed: {r.status_code}", "WARN")
            return False
    except Exception as e:
        log(f"Portal proxy not reachable: {e}", "WARN")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Template CRUD tests (no auth required for HIE prompt-manager)
# ─────────────────────────────────────────────────────────────────────────────

def test_list_templates() -> bool:
    """Test listing templates."""
    try:
        r = httpx.get(f"{PROMPT_MANAGER_URL}/templates", timeout=10.0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "items" in data, "Response missing 'items'"
        assert "total" in data, "Response missing 'total'"
        log(f"Listed {data['total']} templates ({len(data['items'])} returned)")

        if data["total"] > 0:
            t = data["items"][0]
            assert "id" in t, "Template missing 'id'"
            assert "name" in t, "Template missing 'name'"
            log_verbose(f"First template: {t['name']}")
        return True
    except AssertionError as e:
        log(f"List templates failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"List templates error: {e}", "FAIL")
        return False


def test_create_template() -> str | None:
    """Test creating a new template. Returns template ID."""
    try:
        payload = {
            "name": f"HIE E2E Test Template {uuid.uuid4().hex[:6]}",
            "description": "Created by HIE E2E test",
            "category": "testing",
            "template_body": "Hello {{name}}, your HIE project is {{project}}.",
            "variables": [
                {"name": "name", "type": "string", "description": "User name", "required": True},
                {"name": "project", "type": "string", "description": "Project name", "required": True},
            ],
            "sample_values": {"name": "Alice", "project": "FHIR Migration"},
            "visibility": "private",
            "status": "draft",
        }
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/templates",
            json=payload,
            timeout=10.0,
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["status"] == "draft"
        assert data["version"] == 1
        log(f"Created template: {data['id']} ({data['name']})")
        return data["id"]
    except AssertionError as e:
        log(f"Create template failed: {e}", "FAIL")
        return None
    except Exception as e:
        log(f"Create template error: {e}", "FAIL")
        return None


def test_get_template(template_id: str) -> bool:
    """Test getting a specific template by ID."""
    try:
        r = httpx.get(f"{PROMPT_MANAGER_URL}/templates/{template_id}", timeout=10.0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert data["id"] == template_id
        log(f"Get template OK: {data['name']} v{data['version']}")
        return True
    except AssertionError as e:
        log(f"Get template failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Get template error: {e}", "FAIL")
        return False


def test_update_template(template_id: str) -> str | None:
    """Test updating a template (creates new version). Returns new version ID."""
    try:
        payload = {
            "template_body": "Updated: Hello {{name}}, HIE project {{project}} is ready.",
            "change_summary": "Updated body text for E2E test",
        }
        r = httpx.put(
            f"{PROMPT_MANAGER_URL}/templates/{template_id}",
            json=payload,
            timeout=10.0,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["version"] == 2, f"Expected version 2, got {data['version']}"
        assert data["is_latest"] is True
        assert "Updated:" in data["template_body"]
        log(f"Updated template: new version {data['id']} (v{data['version']})")
        return data["id"]
    except AssertionError as e:
        log(f"Update template failed: {e}", "FAIL")
        return None
    except Exception as e:
        log(f"Update template error: {e}", "FAIL")
        return None


def test_publish_template(template_id: str) -> bool:
    """Test publishing a template."""
    try:
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/templates/{template_id}/publish",
            timeout=10.0,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["status"] == "published"
        log(f"Published template: {data['id']}")
        return True
    except AssertionError as e:
        log(f"Publish template failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Publish template error: {e}", "FAIL")
        return False


def test_render_template(template_id: str) -> bool:
    """Test rendering a template with variables."""
    try:
        payload = {"variables": {"name": "Bob", "project": "TIE Upgrade"}}
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/templates/{template_id}/render",
            json=payload,
            timeout=10.0,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "Bob" in data["rendered"], "Expected 'Bob' in rendered text"
        assert "TIE Upgrade" in data["rendered"], "Expected 'TIE Upgrade' in rendered text"
        assert "{{" not in data["rendered"], "Unresolved variables in rendered text"
        log(f"Rendered template OK: '{data['rendered'][:60]}...'")
        return True
    except AssertionError as e:
        log(f"Render template failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Render template error: {e}", "FAIL")
        return False


def test_clone_template(template_id: str) -> bool:
    """Test cloning a template."""
    try:
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/templates/{template_id}/clone",
            timeout=10.0,
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert "(Copy)" in data["name"]
        assert data["version"] == 1
        assert data["status"] == "draft"
        log(f"Cloned template: {data['id']} ({data['name']})")
        return True
    except AssertionError as e:
        log(f"Clone template failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Clone template error: {e}", "FAIL")
        return False


def test_delete_template(template_id: str) -> bool:
    """Test deleting (archiving) a template."""
    try:
        r = httpx.delete(
            f"{PROMPT_MANAGER_URL}/templates/{template_id}",
            timeout=10.0,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["status"] == "archived"
        log(f"Deleted (archived) template: {template_id}")
        return True
    except AssertionError as e:
        log(f"Delete template failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Delete template error: {e}", "FAIL")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Skills API tests
# ─────────────────────────────────────────────────────────────────────────────

def test_list_skills() -> bool:
    """Test listing skills."""
    try:
        r = httpx.get(f"{PROMPT_MANAGER_URL}/skills", timeout=10.0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert "items" in data
        assert "total" in data
        log(f"Listed {data['total']} skills")
        return True
    except AssertionError as e:
        log(f"List skills failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"List skills error: {e}", "FAIL")
        return False


def test_create_skill() -> str | None:
    """Test creating a new skill. Returns skill ID."""
    try:
        payload = {
            "name": f"HIE E2E Test Skill {uuid.uuid4().hex[:6]}",
            "description": "Created by HIE E2E test",
            "category": "testing",
            "scope": "platform",
            "skill_content": "# Test Skill\n\nYou are a testing assistant for HIE.",
            "visibility": "public",
            "status": "draft",
        }
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/skills",
            json=payload,
            timeout=10.0,
        )
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
        data = r.json()
        assert data["scope"] == "platform"
        assert data["version"] == 1
        log(f"Created skill: {data['id']} ({data['name']})")
        return data["id"]
    except AssertionError as e:
        log(f"Create skill failed: {e}", "FAIL")
        return None
    except Exception as e:
        log(f"Create skill error: {e}", "FAIL")
        return None


def test_toggle_skill(skill_id: str) -> bool:
    """Test toggling a skill's enabled state."""
    try:
        r = httpx.post(
            f"{PROMPT_MANAGER_URL}/skills/{skill_id}/toggle",
            timeout=10.0,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        log(f"Toggled skill enabled={data.get('enabled')}")
        return True
    except AssertionError as e:
        log(f"Toggle skill failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Toggle skill error: {e}", "FAIL")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────

def test_categories() -> bool:
    """Test categories endpoint."""
    try:
        r = httpx.get(f"{PROMPT_MANAGER_URL}/categories", timeout=10.0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()
        assert isinstance(data, list), "Expected list of categories"
        log(f"Categories: {len(data)} categories found")
        return True
    except AssertionError as e:
        log(f"Categories failed: {e}", "FAIL")
        return False
    except Exception as e:
        log(f"Categories error: {e}", "FAIL")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description="HIE Prompt Manager E2E API Tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    VERBOSE = args.verbose

    print("=" * 70)
    print("OpenLI HIE — Prompt & Skills Manager E2E API Tests")
    print("=" * 70)

    results = []

    # 1. Health checks
    print("\n--- Health Checks ---")
    results.append(("Health check (direct)", test_health_check()))
    results.append(("Health check (Portal proxy)", test_health_via_portal()))

    # 2. Template CRUD lifecycle
    print("\n--- Template CRUD Lifecycle ---")
    results.append(("List templates", test_list_templates()))

    template_id = test_create_template()
    results.append(("Create template", template_id is not None))

    if template_id:
        results.append(("Get template by ID", test_get_template(template_id)))

        new_version_id = test_update_template(template_id)
        results.append(("Update template (new version)", new_version_id is not None))

        if new_version_id:
            results.append(("Publish template", test_publish_template(new_version_id)))
            results.append(("Render template", test_render_template(new_version_id)))
            results.append(("Clone template", test_clone_template(new_version_id)))
            results.append(("Delete (archive) template", test_delete_template(new_version_id)))

    # 3. Skills
    print("\n--- Skills CRUD ---")
    results.append(("List skills", test_list_skills()))
    skill_id = test_create_skill()
    results.append(("Create skill", skill_id is not None))
    if skill_id:
        results.append(("Toggle skill", test_toggle_skill(skill_id)))

    # 4. Categories
    print("\n--- Categories ---")
    results.append(("Categories", test_categories()))

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
