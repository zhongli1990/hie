"""
OpenLI HIE Prompt Manager - Skills Router

CRUD, publish, toggle, sync-from-files for DB-backed skills.
"""
import os
from typing import Optional
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser, get_current_user
from ..database import get_db
from ..repositories.skill_repo import SkillRepository
from ..schemas import SkillCreate, SkillUpdate, SkillResponse, SkillListResponse

router = APIRouter(prefix="/skills", tags=["skills"])

SKILLS_DIR = os.environ.get("SKILLS_DIR", "/app/skills")


def _to_response(skill) -> SkillResponse:
    return SkillResponse(
        id=str(skill.id),
        tenant_id=str(skill.tenant_id) if skill.tenant_id else None,
        owner_id=str(skill.owner_id) if skill.owner_id else None,
        name=skill.name,
        slug=skill.slug,
        category=skill.category,
        description=skill.description,
        scope=skill.scope,
        skill_content=skill.skill_content,
        allowed_tools=skill.allowed_tools,
        is_user_invocable=skill.is_user_invocable,
        version=skill.version,
        is_latest=skill.is_latest,
        is_published=skill.is_published,
        is_enabled=skill.is_enabled,
        source=skill.source,
        file_path=skill.file_path,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.get("", response_model=SkillListResponse)
async def list_skills(
    category: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skills, total = await repo.list_latest(
        tenant_id=user.tenant_id, category=category, scope=scope,
        search=search, offset=offset, limit=limit,
    )
    return SkillListResponse(
        skills=[_to_response(s) for s in skills],
        total=total,
    )


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.get_by_id(skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return _to_response(skill)


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    req: SkillCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.create(
        name=req.name,
        skill_content=req.skill_content,
        category=req.category,
        description=req.description,
        scope=req.scope,
        allowed_tools=req.allowed_tools,
        is_user_invocable=req.is_user_invocable,
        tenant_id=user.tenant_id,
        owner_id=user.user_id,
    )
    return _to_response(skill)


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    req: SkillUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.update_skill(
        skill_id,
        name=req.name,
        category=req.category,
        description=req.description,
        skill_content=req.skill_content,
        allowed_tools=req.allowed_tools,
        is_user_invocable=req.is_user_invocable,
    )
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return _to_response(skill)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    deleted = await repo.delete_skill(skill_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")


@router.post("/{skill_id}/publish", response_model=SkillResponse)
async def publish_skill(
    skill_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.publish(skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return _to_response(skill)


@router.post("/{skill_id}/toggle", response_model=SkillResponse)
async def toggle_skill(
    skill_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.toggle_enabled(skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return _to_response(skill)


@router.post("/sync-from-files")
async def sync_from_files(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync skills from the agent-runner skills directory into the DB."""
    repo = SkillRepository(db)
    skills_path = Path(SKILLS_DIR)
    synced = []

    if not skills_path.exists():
        return {"synced": [], "message": f"Skills directory not found: {SKILLS_DIR}"}

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text(encoding="utf-8")

        # Parse frontmatter
        name = skill_dir.name
        description = ""
        allowed_tools = None
        is_user_invocable = True
        category = "general"

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if fm:
                        name = fm.get("name", name)
                        description = fm.get("description", "")
                        allowed_tools = fm.get("allowed-tools")
                        is_user_invocable = fm.get("user-invocable", True)
                except yaml.YAMLError:
                    pass

        # Determine category from skill name for HIE skills
        if "hl7" in name.lower():
            category = "hl7"
        elif "fhir" in name.lower():
            category = "fhir"
        elif "clinical" in name.lower() or "safety" in name.lower():
            category = "clinical"
        elif "nhs" in name.lower() or "compliance" in name.lower():
            category = "compliance"
        elif "test" in name.lower() or "integration" in name.lower():
            category = "integration"

        skill = await repo.sync_from_file(
            name=name,
            skill_content=content,
            description=description,
            scope="platform",
            allowed_tools=allowed_tools,
            is_user_invocable=is_user_invocable,
            file_path=str(skill_md),
            category=category,
        )
        synced.append({"name": name, "id": str(skill.id), "version": skill.version})

    return {"synced": synced, "total": len(synced)}
