"""
OpenLI HIE Agent Runner - Skill File Loader

Loads skills from:
1. Global skills: /app/skills/<skill-name>/SKILL.md
2. Workspace skills: /workspaces/<id>/.claude/skills/<skill-name>/SKILL.md

Workspace skills override global skills with the same name.
Skills are customized for healthcare integration context.
"""

import os
from pathlib import Path
from typing import Any

import yaml

from .config import GLOBAL_SKILLS_PATH


def load_skill(skill_path: Path) -> dict[str, Any] | None:
    """Load a single skill from a directory containing SKILL.md."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None

    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception:
        return None

    # Parse YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                instructions = parts[2].strip()

                allowed_tools_raw = frontmatter.get("allowed-tools", "")
                if isinstance(allowed_tools_raw, str):
                    allowed_tools = [t.strip() for t in allowed_tools_raw.split(",") if t.strip()]
                else:
                    allowed_tools = list(allowed_tools_raw) if allowed_tools_raw else []

                return {
                    "name": frontmatter.get("name", skill_path.name),
                    "description": frontmatter.get("description", ""),
                    "allowed_tools": allowed_tools,
                    "disable_model_invocation": frontmatter.get("disable-model-invocation", False),
                    "user_invocable": frontmatter.get("user-invocable", True),
                    "instructions": instructions,
                    "path": str(skill_path),
                }
            except yaml.YAMLError:
                pass

    # No frontmatter, treat entire content as instructions
    return {
        "name": skill_path.name,
        "description": "",
        "allowed_tools": [],
        "disable_model_invocation": False,
        "user_invocable": True,
        "instructions": content,
        "path": str(skill_path),
    }


def load_skills_from_directory(skills_dir: Path, scope: str) -> list[dict[str, Any]]:
    """Load all skills from a directory."""
    skills = []
    if not skills_dir.exists() or not skills_dir.is_dir():
        return skills

    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill = load_skill(skill_dir)
            if skill:
                skill["scope"] = scope
                skills.append(skill)

    return skills


def load_all_skills(workspace_path: str) -> list[dict[str, Any]]:
    """
    Load all skills for a workspace.

    Order of precedence (later overrides earlier):
    1. Global skills from GLOBAL_SKILLS_PATH
    2. Workspace skills from <workspace>/.claude/skills/
    """
    skills_by_name: dict[str, dict[str, Any]] = {}

    # 1. Load global skills
    global_skills_dir = Path(GLOBAL_SKILLS_PATH)
    for skill in load_skills_from_directory(global_skills_dir, "global"):
        skills_by_name[skill["name"]] = skill

    # 2. Load workspace skills (override global)
    workspace_skills_dir = Path(workspace_path) / ".claude" / "skills"
    for skill in load_skills_from_directory(workspace_skills_dir, "workspace"):
        skills_by_name[skill["name"]] = skill

    return list(skills_by_name.values())


def build_system_prompt(skills: list[dict[str, Any]]) -> str:
    """Build system prompt incorporating loaded skills for HIE context."""
    base_prompt = """You are an AI assistant for OpenLI HIE (Healthcare Integration Engine). You help configure, deploy, and manage healthcare integration routes.

OpenLI HIE uses a hierarchy of: Workspaces → Projects → Items (Services, Processes, Operations) connected by Connections and governed by Routing Rules.

## Architecture (IRIS-Aligned)

| IRIS Concept | HIE Equivalent |
|-------------|---------------|
| Namespace | Workspace |
| Production | Project |
| Business Service | Service (inbound) |
| Business Process | Process (routing/transform) |
| Business Operation | Operation (outbound) |
| TargetConfigNames | TargetConfigNames (identical) |
| ReplyCodeActions | ReplyCodeActions (identical syntax) |

## Class Namespace Convention (CRITICAL)

**PROTECTED namespaces — DO NOT create or modify classes here:**
- `li.*` — Core LI product classes (HL7TCPService, RoutingEngine, FileService, etc.)
- `Engine.li.*` — Same classes via fully-qualified path
- `EnsLib.*` — IRIS compatibility aliases (read-only)

**DEVELOPER namespace — ALL custom classes go here:**
- `custom.*` — Organisation-specific extensions
  - `custom.nhs.NHSValidationProcess`
  - `custom.sth.PatientLookupProcess`
  - `custom.myorg.FHIRBridgeService`

When creating items, use:
- Core classes for standard items: `li.hosts.hl7.HL7TCPService`
- Custom classes for extensions: `custom.nhs.NHSValidationProcess`
- IRIS aliases also work: `EnsLib.HL7.Service.TCPService` (auto-resolved)

## Available Core Classes

**Services (inbound):**
- `li.hosts.hl7.HL7TCPService` — HL7 v2.x MLLP receiver (IRIS: EnsLib.HL7.Service.TCPService)
- `li.hosts.hl7.HL7FileService` — HL7 file watcher
- `li.hosts.http.HTTPService` — HTTP/REST inbound

**Processes (routing/transform):**
- `li.hosts.routing.HL7RoutingEngine` — Content-based router (IRIS: EnsLib.HL7.MsgRouter.RoutingEngine)

**Operations (outbound):**
- `li.hosts.hl7.HL7TCPOperation` — HL7 v2.x MLLP sender (IRIS: EnsLib.HL7.Operation.TCPOperation)
- `li.hosts.file.FileOperation` — File writer

## Available HIE Tools

**Workspace & Project:**
- `hie_list_workspaces` / `hie_create_workspace` — Manage workspaces
- `hie_list_projects` / `hie_create_project` / `hie_get_project` — Manage projects

**Items & Connections:**
- `hie_create_item` — Create services, processes, or operations
- `hie_create_connection` — Wire items together
- `hie_create_routing_rule` — Add routing rules to a routing engine

**Lifecycle:**
- `hie_deploy_project` — Deploy config to engine (optionally start)
- `hie_start_project` / `hie_stop_project` — Start/stop production
- `hie_project_status` — Get runtime status, queue depths, metrics

**Testing & Registry:**
- `hie_test_item` — Send test messages
- `hie_list_item_types` — List available classes from registry

## End-to-End Route Creation Workflow

When asked to build an integration, follow this sequence:

1. **Create workspace** (if needed): `hie_create_workspace`
2. **Create project**: `hie_create_project`
3. **Add inbound services**: `hie_create_item` with item_type="service"
   - Set adapter_settings (Port, IPAddress, FilePath, etc.)
   - Set host_settings (TargetConfigNames, MessageSchemaCategory, AckMode)
4. **Add business processes**: `hie_create_item` with item_type="process"
   - For routing: use class `li.hosts.routing.HL7RoutingEngine`
   - For custom validation: use class `custom.*.YourProcess`
5. **Add outbound operations**: `hie_create_item` with item_type="operation"
   - Set adapter_settings (IPAddress, Port for MLLP; FilePath for file)
   - Set host_settings (ReplyCodeActions for MLLP senders)
6. **Wire connections**: `hie_create_connection` for each link
7. **Add routing rules**: `hie_create_routing_rule` for content-based routing
8. **Deploy & start**: `hie_deploy_project` with start_after_deploy=true
9. **Test**: `hie_test_item` with sample HL7/FHIR messages
10. **Verify**: `hie_project_status` to confirm all items running

## Healthcare Context
- Follow NHS data handling standards
- Ensure HL7 v2.x message integrity
- Validate FHIR resource conformance
- Log all configuration changes for audit
- Never expose patient identifiable data (PID) in logs
- Use ReplyCodeActions syntax: `:?R=F,:?E=S,:~=S,:?A=C,:*=S`"""

    if not skills:
        return base_prompt

    skill_section = "\n\n## Available Skills\n\n"
    skill_section += "The following skills are available to help with specific tasks:\n\n"

    for skill in skills:
        skill_section += f"### {skill['name']}\n"
        if skill["description"]:
            skill_section += f"**Description**: {skill['description']}\n\n"
        if skill["instructions"]:
            skill_section += f"{skill['instructions']}\n\n"
        skill_section += "---\n\n"

    return base_prompt + skill_section


def get_skill_names(skills: list[dict[str, Any]]) -> list[str]:
    """Get list of skill names."""
    return [skill["name"] for skill in skills]
