"""
OpenLI HIE Agent Runner - Skills Management API

Admin CRUD operations for file-based skills.
Skills are stored as SKILL.md files with YAML frontmatter.
"""

import os
import re
import shutil
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/skills", tags=["skills"])

# Skills directories
PLATFORM_SKILLS_DIR = Path("/app/skills")
WORKSPACE_SKILLS_BASE = Path("/workspaces")


class SkillMetadata(BaseModel):
    name: str
    description: str
    allowed_tools: Optional[str] = Field(None, alias="allowed-tools")
    user_invocable: bool = Field(True, alias="user-invocable")
    version: str = "1.0"
    last_modified: Optional[str] = Field(None, alias="last-modified")
    modified_by: Optional[str] = Field(None, alias="modified-by")

    class Config:
        populate_by_name = True


class SkillFile(BaseModel):
    path: str
    content: str


class SkillResponse(BaseModel):
    name: str
    description: str
    scope: str
    content: str
    version: str
    last_modified: Optional[str] = None
    modified_by: Optional[str] = None
    files: List[SkillFile] = []


class SkillListItem(BaseModel):
    name: str
    description: str
    scope: str
    version: str
    last_modified: Optional[str] = None
    modified_by: Optional[str] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None


class CreateSkillRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9-]+$", max_length=64)
    description: str = Field(..., max_length=1024)
    content: str
    scope: str = "platform"
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    allowed_tools: Optional[str] = None
    user_invocable: bool = True


class UpdateSkillRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=1024)
    content: Optional[str] = None
    allowed_tools: Optional[str] = None
    user_invocable: Optional[bool] = None
    change_summary: str = "Updated skill"


def parse_skill_frontmatter(content: str) -> tuple[dict, str]:
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].strip()
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def build_skill_content(metadata: dict, body: str) -> str:
    frontmatter = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
    return f"---\n{frontmatter}---\n\n{body}"


def get_skill_dir(name: str, scope: str, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> Path:
    if scope == "platform":
        return PLATFORM_SKILLS_DIR / name
    elif scope == "tenant" and tenant_id:
        return WORKSPACE_SKILLS_BASE / tenant_id / ".claude" / "skills" / name
    elif scope == "project" and tenant_id and project_id:
        return WORKSPACE_SKILLS_BASE / tenant_id / project_id / ".claude" / "skills" / name
    else:
        raise ValueError(f"Invalid scope or missing IDs: scope={scope}")


def load_skill(skill_dir: Path, scope: str, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> Optional[SkillResponse]:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None

    content = skill_file.read_text()
    frontmatter, body = parse_skill_frontmatter(content)

    files = []
    for root, dirs, filenames in os.walk(skill_dir):
        for filename in filenames:
            if filename == "SKILL.md" and root == str(skill_dir):
                continue
            file_path = Path(root) / filename
            rel_path = file_path.relative_to(skill_dir)
            try:
                files.append(SkillFile(path=str(rel_path), content=file_path.read_text()))
            except Exception:
                pass

    return SkillResponse(
        name=frontmatter.get("name", skill_dir.name),
        description=frontmatter.get("description", ""),
        scope=scope,
        content=content,
        version=str(frontmatter.get("version", "1.0")),
        last_modified=frontmatter.get("last-modified"),
        modified_by=frontmatter.get("modified-by"),
        files=files
    )


def list_skills_in_dir(base_dir: Path, scope: str, tenant_id: Optional[str] = None, project_id: Optional[str] = None) -> List[SkillListItem]:
    skills = []
    if not base_dir.exists():
        return skills

    for skill_dir in base_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text()
        frontmatter, _ = parse_skill_frontmatter(content)

        skills.append(SkillListItem(
            name=frontmatter.get("name", skill_dir.name),
            description=frontmatter.get("description", ""),
            scope=scope,
            version=str(frontmatter.get("version", "1.0")),
            last_modified=frontmatter.get("last-modified"),
            modified_by=frontmatter.get("modified-by"),
            tenant_id=tenant_id,
            project_id=project_id
        ))

    return skills


@router.get("", response_model=List[SkillListItem])
async def list_skills(
    scope: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    skills = []
    if scope is None or scope == "platform":
        skills.extend(list_skills_in_dir(PLATFORM_SKILLS_DIR, "platform"))
    if (scope is None or scope == "tenant") and tenant_id:
        tenant_skills_dir = WORKSPACE_SKILLS_BASE / tenant_id / ".claude" / "skills"
        skills.extend(list_skills_in_dir(tenant_skills_dir, "tenant", tenant_id=tenant_id))
    if (scope is None or scope == "project") and tenant_id and project_id:
        project_skills_dir = WORKSPACE_SKILLS_BASE / tenant_id / project_id / ".claude" / "skills"
        skills.extend(list_skills_in_dir(project_skills_dir, "project", tenant_id=tenant_id, project_id=project_id))
    return skills


@router.get("/{name}", response_model=SkillResponse)
async def get_skill(
    name: str,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    skill = load_skill(skill_dir, scope, tenant_id, project_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")
    return skill


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(request: CreateSkillRequest):
    if not re.match(r"^[a-z0-9-]+$", request.name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Skill name must contain only lowercase letters, numbers, and hyphens")

    try:
        skill_dir = get_skill_dir(request.name, request.scope, request.tenant_id, request.project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if skill_dir.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Skill '{request.name}' already exists")

    skill_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "name": request.name,
        "description": request.description,
        "user-invocable": request.user_invocable,
        "version": "1.0",
        "last-modified": now,
        "modified-by": "admin",
        "changelog": [{"version": "1.0", "date": now[:10], "author": "admin", "changes": "Initial version"}]
    }
    if request.allowed_tools:
        metadata["allowed-tools"] = request.allowed_tools

    content = build_skill_content(metadata, request.content)
    (skill_dir / "SKILL.md").write_text(content)

    return load_skill(skill_dir, request.scope, request.tenant_id, request.project_id)


@router.put("/{name}", response_model=SkillResponse)
async def update_skill(
    name: str,
    request: UpdateSkillRequest,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")

    existing_content = skill_file.read_text()
    frontmatter, body = parse_skill_frontmatter(existing_content)

    now = datetime.now(timezone.utc).isoformat()
    old_version = frontmatter.get("version", "1.0")
    try:
        major, minor = old_version.split(".")
        new_version = f"{major}.{int(minor) + 1}"
    except Exception:
        new_version = "1.1"

    if request.description:
        frontmatter["description"] = request.description
    if request.allowed_tools is not None:
        frontmatter["allowed-tools"] = request.allowed_tools
    if request.user_invocable is not None:
        frontmatter["user-invocable"] = request.user_invocable

    frontmatter["version"] = new_version
    frontmatter["last-modified"] = now
    frontmatter["modified-by"] = "admin"

    changelog = frontmatter.get("changelog", [])
    changelog.insert(0, {"version": new_version, "date": now[:10], "author": "admin", "changes": request.change_summary})
    frontmatter["changelog"] = changelog[:10]

    if request.content is not None:
        body = request.content

    content = build_skill_content(frontmatter, body)
    skill_file.write_text(content)

    return load_skill(skill_dir, scope, tenant_id, project_id)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    name: str,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not skill_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")

    shutil.rmtree(skill_dir)


@router.post("/{name}/reload", status_code=status.HTTP_200_OK)
async def reload_skill(
    name: str,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not skill_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")

    return {"status": "ok", "message": f"Skill '{name}' will be reloaded on next agent run"}


@router.post("/{name}/files", response_model=SkillFile, status_code=status.HTTP_201_CREATED)
async def add_skill_file(
    name: str,
    file: SkillFile,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not skill_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")

    if ".." in file.path or file.path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")

    file_path = skill_dir / file.path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(file.content)

    return file


@router.delete("/{name}/files/{file_path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_file(
    name: str,
    file_path: str,
    scope: str = Query("platform"),
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None)
):
    try:
        skill_dir = get_skill_dir(name, scope, tenant_id, project_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not skill_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill '{name}' not found")

    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")

    full_path = skill_dir / file_path
    if not full_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{file_path}' not found")

    full_path.unlink()
