"""
OpenLI HIE Prompt Manager - Templates Router

CRUD, render, publish for prompt templates.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser, get_current_user
from ..database import get_db
from ..repositories.template_repo import TemplateRepository
from ..schemas import (
    TemplateCreate, TemplateUpdate, TemplateResponse, TemplateListResponse,
    RenderTemplateRequest, RenderTemplateResponse,
)

router = APIRouter(prefix="/templates", tags=["templates"])


def _to_response(tpl) -> TemplateResponse:
    return TemplateResponse(
        id=str(tpl.id),
        tenant_id=str(tpl.tenant_id) if tpl.tenant_id else None,
        owner_id=str(tpl.owner_id) if tpl.owner_id else None,
        name=tpl.name,
        slug=tpl.slug,
        category=tpl.category,
        description=tpl.description,
        template_body=tpl.template_body,
        variables=tpl.variables,
        tags=tpl.tags,
        version=tpl.version,
        is_latest=tpl.is_latest,
        is_published=tpl.is_published,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
    )


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    templates, total = await repo.list_latest(
        tenant_id=user.tenant_id, category=category, search=search,
        offset=offset, limit=limit,
    )
    return TemplateListResponse(
        templates=[_to_response(t) for t in templates],
        total=total,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    tpl = await repo.get_by_id(template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return _to_response(tpl)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    req: TemplateCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    tpl = await repo.create(
        name=req.name,
        template_body=req.template_body,
        category=req.category,
        description=req.description,
        variables=req.variables,
        tags=req.tags,
        tenant_id=user.tenant_id,
        owner_id=user.user_id,
    )
    return _to_response(tpl)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    req: TemplateUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    tpl = await repo.update_template(
        template_id,
        name=req.name,
        category=req.category,
        description=req.description,
        template_body=req.template_body,
        variables=req.variables,
        tags=req.tags,
    )
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return _to_response(tpl)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    deleted = await repo.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")


@router.post("/{template_id}/publish", response_model=TemplateResponse)
async def publish_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    tpl = await repo.publish(template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return _to_response(tpl)


@router.post("/{template_id}/render", response_model=RenderTemplateResponse)
async def render_template(
    template_id: str,
    req: RenderTemplateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    tpl = await repo.get_by_id(template_id)
    if not tpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    rendered = await repo.render(template_id, req.variables)
    return RenderTemplateResponse(
        rendered=rendered,
        template_id=str(tpl.id),
        template_name=tpl.name,
    )
