"""
OpenLI HIE Prompt Manager - Main FastAPI Application

Provides:
- Prompt template CRUD with versioning
- DB-backed skills management
- Usage analytics
- Category listing
- Seed API: POST /seed/templates and POST /seed/skills (loads from JSON files)
"""
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, async_session
from .models import Base
from .routers import templates, skills, usage, categories
from .repositories.template_repo import TemplateRepository
from .repositories.skill_repo import SkillRepository

logger = logging.getLogger(__name__)

SEED_DIR = os.environ.get("SEED_DIR", "/app/seeds")

app = FastAPI(title="OpenLI HIE Prompt Manager", version="1.8.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(templates.router)
app.include_router(skills.router)
app.include_router(usage.router)
app.include_router(categories.router)


@app.on_event("startup")
async def on_startup():
    """Create tables on startup. No auto-seeding — use /seed/* endpoints."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hie-prompt-manager", "version": "1.8.1"}


# ── Seed API ──────────────────────────────────────────────────────────────────
# Loads data from JSON files in SEED_DIR. Idempotent: skips templates/skills
# whose name already exists. Called from UI or scripts, never auto-runs.

@app.post("/seed/templates")
async def seed_templates_endpoint():
    """Load seed templates from seeds/templates.json into DB (skip existing)."""
    seed_file = Path(SEED_DIR) / "templates.json"
    if not seed_file.exists():
        raise HTTPException(status_code=404, detail=f"Seed file not found: {seed_file}")

    with open(seed_file, "r") as f:
        seed_data = json.load(f)

    created = []
    skipped = []
    async with async_session() as db:
        repo = TemplateRepository(db)
        for tpl in seed_data:
            existing = await db.execute(
                text("SELECT id FROM prompt_templates WHERE name = :name"),
                {"name": tpl["name"]},
            )
            if existing.first():
                skipped.append(tpl["name"])
                continue
            await repo.create(
                name=tpl["name"],
                template_body=tpl["template_body"],
                category=tpl.get("category", "general"),
                description=tpl.get("description"),
                variables=tpl.get("variables"),
                tags=tpl.get("tags"),
            )
            created.append(tpl["name"])
            logger.info(f"Seeded template: {tpl['name']}")

    return {"created": created, "skipped": skipped, "total_created": len(created)}


@app.post("/seed/skills")
async def seed_skills_endpoint():
    """Load seed skills from seeds/skills.json into DB (skip existing)."""
    seed_file = Path(SEED_DIR) / "skills.json"
    if not seed_file.exists():
        raise HTTPException(status_code=404, detail=f"Seed file not found: {seed_file}")

    with open(seed_file, "r") as f:
        seed_data = json.load(f)

    created = []
    skipped = []
    async with async_session() as db:
        repo = SkillRepository(db)
        for skill in seed_data:
            existing = await db.execute(
                text("SELECT id FROM skills WHERE name = :name"),
                {"name": skill["name"]},
            )
            if existing.first():
                skipped.append(skill["name"])
                continue
            await repo.create(
                name=skill["name"],
                skill_content=skill["skill_content"],
                category=skill.get("category", "general"),
                description=skill.get("description"),
                scope=skill.get("scope", "platform"),
                allowed_tools=skill.get("allowed_tools"),
                is_user_invocable=skill.get("is_user_invocable", True),
            )
            created.append(skill["name"])
            logger.info(f"Seeded skill: {skill['name']}")

    return {"created": created, "skipped": skipped, "total_created": len(created)}
