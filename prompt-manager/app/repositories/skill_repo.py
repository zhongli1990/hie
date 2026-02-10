"""
OpenLI HIE Prompt Manager - Skill Repository

DB access layer for skills with versioning and RBAC.
"""
import re
import uuid
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Skill


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class SkillRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        skill_content: str,
        category: str = "general",
        description: Optional[str] = None,
        scope: str = "platform",
        allowed_tools: Optional[str] = None,
        is_user_invocable: bool = True,
        tenant_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        source: str = "db",
        file_path: Optional[str] = None,
    ) -> Skill:
        slug = slugify(name)
        skill = Skill(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            owner_id=uuid.UUID(owner_id) if owner_id else None,
            name=name,
            slug=slug,
            category=category,
            description=description,
            scope=scope,
            skill_content=skill_content,
            allowed_tools=allowed_tools,
            is_user_invocable=is_user_invocable,
            version=1,
            is_latest=True,
            is_published=False,
            is_enabled=True,
            source=source,
            file_path=file_path,
        )
        self.db.add(skill)
        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def get_by_id(self, skill_id: str) -> Optional[Skill]:
        result = await self.db.execute(
            select(Skill).where(Skill.id == uuid.UUID(skill_id))
        )
        return result.scalar_one_or_none()

    async def get_latest_by_slug(self, slug: str, tenant_id: Optional[str] = None) -> Optional[Skill]:
        query = select(Skill).where(Skill.slug == slug, Skill.is_latest == True)
        if tenant_id:
            query = query.where(Skill.tenant_id == uuid.UUID(tenant_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_latest(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        scope: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Skill], int]:
        query = select(Skill).where(Skill.is_latest == True)
        count_query = select(func.count()).select_from(Skill).where(Skill.is_latest == True)

        if tenant_id:
            tid = uuid.UUID(tenant_id)
            query = query.where(Skill.tenant_id == tid)
            count_query = count_query.where(Skill.tenant_id == tid)
        if category:
            query = query.where(Skill.category == category)
            count_query = count_query.where(Skill.category == category)
        if scope:
            query = query.where(Skill.scope == scope)
            count_query = count_query.where(Skill.scope == scope)
        if search:
            pattern = f"%{search}%"
            query = query.where(Skill.name.ilike(pattern))
            count_query = count_query.where(Skill.name.ilike(pattern))

        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(Skill.updated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        skill_content: Optional[str] = None,
        allowed_tools: Optional[str] = None,
        is_user_invocable: Optional[bool] = None,
    ) -> Optional[Skill]:
        existing = await self.get_by_id(skill_id)
        if not existing:
            return None

        # Mark old version as not latest
        await self.db.execute(
            update(Skill)
            .where(Skill.slug == existing.slug, Skill.is_latest == True)
            .values(is_latest=False)
        )

        new_skill = Skill(
            id=uuid.uuid4(),
            tenant_id=existing.tenant_id,
            owner_id=existing.owner_id,
            name=name or existing.name,
            slug=slugify(name) if name else existing.slug,
            category=category or existing.category,
            description=description if description is not None else existing.description,
            scope=existing.scope,
            skill_content=skill_content or existing.skill_content,
            allowed_tools=allowed_tools if allowed_tools is not None else existing.allowed_tools,
            is_user_invocable=is_user_invocable if is_user_invocable is not None else existing.is_user_invocable,
            version=existing.version + 1,
            is_latest=True,
            is_published=existing.is_published,
            is_enabled=existing.is_enabled,
            parent_id=existing.id,
            source=existing.source,
            file_path=existing.file_path,
        )
        self.db.add(new_skill)
        await self.db.commit()
        await self.db.refresh(new_skill)
        return new_skill

    async def delete_skill(self, skill_id: str) -> bool:
        skill = await self.get_by_id(skill_id)
        if not skill:
            return False
        result = await self.db.execute(
            select(Skill).where(Skill.slug == skill.slug)
        )
        for row in result.scalars().all():
            await self.db.delete(row)
        await self.db.commit()
        return True

    async def publish(self, skill_id: str) -> Optional[Skill]:
        skill = await self.get_by_id(skill_id)
        if not skill:
            return None
        skill.is_published = True
        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def toggle_enabled(self, skill_id: str) -> Optional[Skill]:
        skill = await self.get_by_id(skill_id)
        if not skill:
            return None
        skill.is_enabled = not skill.is_enabled
        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def sync_from_file(
        self,
        name: str,
        skill_content: str,
        description: str = "",
        scope: str = "platform",
        allowed_tools: Optional[str] = None,
        is_user_invocable: bool = True,
        file_path: Optional[str] = None,
        category: str = "general",
        tenant_id: Optional[str] = None,
    ) -> Skill:
        """Sync a skill from a file. Creates or updates as needed."""
        slug = slugify(name)
        existing = await self.get_latest_by_slug(slug, tenant_id)

        if existing:
            if existing.skill_content == skill_content:
                return existing
            return await self.update_skill(
                str(existing.id),
                description=description,
                skill_content=skill_content,
                allowed_tools=allowed_tools,
                is_user_invocable=is_user_invocable,
            )

        return await self.create(
            name=name,
            skill_content=skill_content,
            category=category,
            description=description,
            scope=scope,
            allowed_tools=allowed_tools,
            is_user_invocable=is_user_invocable,
            tenant_id=tenant_id,
            source="file",
            file_path=file_path,
        )
