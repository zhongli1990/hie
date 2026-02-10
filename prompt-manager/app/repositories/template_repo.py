"""
OpenLI HIE Prompt Manager - Template Repository

DB access layer for prompt templates with versioning and RBAC.
"""
import re
import uuid
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PromptTemplate


def slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class TemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        template_body: str,
        category: str = "general",
        description: Optional[str] = None,
        variables: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        tenant_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> PromptTemplate:
        slug = slugify(name)
        tpl = PromptTemplate(
            id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            owner_id=uuid.UUID(owner_id) if owner_id else None,
            name=name,
            slug=slug,
            category=category,
            description=description,
            template_body=template_body,
            variables=variables,
            tags=tags,
            version=1,
            is_latest=True,
            is_published=False,
        )
        self.db.add(tpl)
        await self.db.commit()
        await self.db.refresh(tpl)
        return tpl

    async def get_by_id(self, template_id: str) -> Optional[PromptTemplate]:
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.id == uuid.UUID(template_id))
        )
        return result.scalar_one_or_none()

    async def get_latest_by_slug(self, slug: str, tenant_id: Optional[str] = None) -> Optional[PromptTemplate]:
        query = (
            select(PromptTemplate)
            .where(PromptTemplate.slug == slug, PromptTemplate.is_latest == True)
        )
        if tenant_id:
            query = query.where(PromptTemplate.tenant_id == uuid.UUID(tenant_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_latest(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[PromptTemplate], int]:
        query = select(PromptTemplate).where(PromptTemplate.is_latest == True)
        count_query = select(func.count()).select_from(PromptTemplate).where(PromptTemplate.is_latest == True)

        if tenant_id:
            tid = uuid.UUID(tenant_id)
            from sqlalchemy import or_
            tenant_filter = or_(PromptTemplate.tenant_id == tid, PromptTemplate.tenant_id.is_(None))
            query = query.where(tenant_filter)
            count_query = count_query.where(tenant_filter)
        if category:
            query = query.where(PromptTemplate.category == category)
            count_query = count_query.where(PromptTemplate.category == category)
        if search:
            pattern = f"%{search}%"
            query = query.where(PromptTemplate.name.ilike(pattern))
            count_query = count_query.where(PromptTemplate.name.ilike(pattern))

        total = (await self.db.execute(count_query)).scalar() or 0
        query = query.order_by(PromptTemplate.updated_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        template_body: Optional[str] = None,
        variables: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> Optional[PromptTemplate]:
        """Create a new version of the template."""
        existing = await self.get_by_id(template_id)
        if not existing:
            return None

        # Mark old version as not latest
        await self.db.execute(
            update(PromptTemplate)
            .where(PromptTemplate.slug == existing.slug, PromptTemplate.is_latest == True)
            .values(is_latest=False)
        )

        new_tpl = PromptTemplate(
            id=uuid.uuid4(),
            tenant_id=existing.tenant_id,
            owner_id=existing.owner_id,
            name=name or existing.name,
            slug=slugify(name) if name else existing.slug,
            category=category or existing.category,
            description=description if description is not None else existing.description,
            template_body=template_body or existing.template_body,
            variables=variables if variables is not None else existing.variables,
            tags=tags if tags is not None else existing.tags,
            version=existing.version + 1,
            is_latest=True,
            is_published=existing.is_published,
            parent_id=existing.id,
        )
        self.db.add(new_tpl)
        await self.db.commit()
        await self.db.refresh(new_tpl)
        return new_tpl

    async def delete_template(self, template_id: str) -> bool:
        tpl = await self.get_by_id(template_id)
        if not tpl:
            return False
        # Delete all versions with same slug
        result = await self.db.execute(
            select(PromptTemplate).where(PromptTemplate.slug == tpl.slug)
        )
        for row in result.scalars().all():
            await self.db.delete(row)
        await self.db.commit()
        return True

    async def publish(self, template_id: str) -> Optional[PromptTemplate]:
        tpl = await self.get_by_id(template_id)
        if not tpl:
            return None
        tpl.is_published = True
        await self.db.commit()
        await self.db.refresh(tpl)
        return tpl

    async def render(self, template_id: str, variables: dict) -> Optional[str]:
        tpl = await self.get_by_id(template_id)
        if not tpl:
            return None
        rendered = tpl.template_body
        for key, value in variables.items():
            rendered = rendered.replace("{{" + key + "}}", str(value))
        return rendered
