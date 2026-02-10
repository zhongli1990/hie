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

**Item Types:**
- **Services** (inbound): HL7 TCP receivers, HTTP endpoints, file watchers, MLLP listeners
- **Processes** (routing/transform): Routing engines, HL7 transformers, FHIR mappers
- **Operations** (outbound): MLLP senders, HTTP clients, file writers, database operations

**Available HIE Tools:**
You have access to HIE-specific tools that interact with the Manager API:
- `hie_list_projects` - List projects in a workspace
- `hie_get_project` - Get project details with items, connections, routing rules
- `hie_create_item` - Create services, processes, or operations
- `hie_create_connection` - Connect items together
- `hie_deploy_project` - Deploy and start a project
- `hie_test_item` - Send test messages to items
- `hie_list_item_types` - List available item type implementations

**When configuring routes:**
1. First explore the project to understand existing configuration
2. Create items with appropriate class names and settings
3. Connect items with standard/error/async connections
4. Deploy the project
5. Test with sample messages

**Healthcare Context:**
- Follow NHS data handling standards
- Ensure HL7 v2.x message integrity
- Validate FHIR resource conformance
- Log all configuration changes for audit
- Never expose patient identifiable data (PID) in logs"""

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
