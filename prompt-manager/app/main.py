"""
OpenLI HIE Prompt Manager - Main FastAPI Application

Provides:
- Prompt template CRUD with versioning
- DB-backed skills management
- Usage analytics
- Category listing
- Auto-seeding of HIE-specific templates on startup
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import engine, async_session
from .models import Base
from .routers import templates, skills, usage, categories

logger = logging.getLogger(__name__)

app = FastAPI(title="OpenLI HIE Prompt Manager", version="1.6.0")
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


# ── HIE-specific seed templates ────────────────────────────────────────────

SEED_TEMPLATES = [
    {
        "name": "HL7 ADT Route Configuration",
        "category": "hl7",
        "description": "Configure an ADT (Admit/Discharge/Transfer) message route with inbound receiver, routing engine, and outbound sender",
        "template_body": """Configure an HL7 ADT route for {{facility_name}} with the following requirements:

**Inbound Service:**
- Protocol: MLLP/TCP on port {{inbound_port}}
- Character encoding: {{encoding}}
- Auto-acknowledge: {{auto_ack}}

**Routing Rules:**
- Route ADT^A01 (Admit) to {{admit_target}}
- Route ADT^A02 (Transfer) to {{transfer_target}}
- Route ADT^A03 (Discharge) to {{discharge_target}}
- Default: {{default_target}}

**Outbound Operations:**
- Target host: {{target_host}}
- Target port: {{target_port}}
- Retry count: {{retry_count}}
- Retry interval: {{retry_interval_ms}}ms

**Error Handling:**
- Dead letter queue for failed messages
- Alert on consecutive failures > {{alert_threshold}}""",
        "variables": {
            "facility_name": {"type": "string", "default": "Hospital A"},
            "inbound_port": {"type": "number", "default": 10001},
            "encoding": {"type": "string", "default": "UTF-8"},
            "auto_ack": {"type": "boolean", "default": True},
            "admit_target": {"type": "string", "default": "PAS"},
            "transfer_target": {"type": "string", "default": "PAS"},
            "discharge_target": {"type": "string", "default": "PAS"},
            "default_target": {"type": "string", "default": "archive"},
            "target_host": {"type": "string", "default": "pas-server"},
            "target_port": {"type": "number", "default": 2575},
            "retry_count": {"type": "number", "default": 3},
            "retry_interval_ms": {"type": "number", "default": 5000},
            "alert_threshold": {"type": "number", "default": 5},
        },
        "tags": ["hl7", "adt", "routing"],
    },
    {
        "name": "FHIR Resource Mapping",
        "category": "fhir",
        "description": "Map HL7 v2.x segments to FHIR R4 resources for interoperability",
        "template_body": """Create a FHIR mapping for {{resource_type}} from HL7 v2.x {{source_segment}} segment.

**Source System:** {{source_system}}
**Target FHIR Server:** {{fhir_server_url}}
**FHIR Profile:** {{fhir_profile}}

**Field Mappings:**
{{field_mappings}}

**Validation Rules:**
- Validate against UK Core profile: {{use_uk_core}}
- NHS Number system: https://fhir.nhs.uk/Id/nhs-number
- ODS Code system: https://fhir.nhs.uk/Id/ods-organization-code

**Error Handling:**
- On validation failure: {{on_validation_failure}}
- Log unmapped fields: {{log_unmapped}}""",
        "variables": {
            "resource_type": {"type": "string", "default": "Patient"},
            "source_segment": {"type": "string", "default": "PID"},
            "source_system": {"type": "string", "default": "PAS"},
            "fhir_server_url": {"type": "string", "default": "http://fhir-server:8080/fhir"},
            "fhir_profile": {"type": "string", "default": "UKCore-Patient"},
            "field_mappings": {"type": "text", "default": "PID.3 -> Patient.identifier\nPID.5 -> Patient.name\nPID.7 -> Patient.birthDate"},
            "use_uk_core": {"type": "boolean", "default": True},
            "on_validation_failure": {"type": "string", "default": "reject"},
            "log_unmapped": {"type": "boolean", "default": True},
        },
        "tags": ["fhir", "mapping", "interoperability"],
    },
    {
        "name": "Clinical Safety Review",
        "category": "clinical",
        "description": "Perform a clinical safety review of an HIE integration configuration per DCB0129",
        "template_body": """Perform a clinical safety review of the integration route for {{project_name}}.

**Review Scope:**
- Route type: {{route_type}}
- Message types: {{message_types}}
- Clinical risk level: {{risk_level}}

**DCB0129 Checklist:**
1. Message integrity - verify no data loss in transformation
2. Patient identification - verify PID handling
3. Error handling - verify clinical safety of failure modes
4. Audit trail - verify all messages are logged
5. Data quality - verify validation rules

**Specific Concerns:**
{{specific_concerns}}

**Output Required:**
- Risk assessment with severity ratings
- Recommended mitigations
- Sign-off requirements""",
        "variables": {
            "project_name": {"type": "string", "default": "ADT Integration"},
            "route_type": {"type": "string", "default": "ADT"},
            "message_types": {"type": "string", "default": "ADT^A01, ADT^A02, ADT^A03"},
            "risk_level": {"type": "string", "default": "medium"},
            "specific_concerns": {"type": "text", "default": "None identified"},
        },
        "tags": ["clinical", "safety", "dcb0129"],
    },
    {
        "name": "Integration Test Plan",
        "category": "integration",
        "description": "Generate a comprehensive integration test plan for an HIE route",
        "template_body": """Generate an integration test plan for {{project_name}}.

**Route Under Test:**
- Inbound: {{inbound_type}} on port {{inbound_port}}
- Processing: {{processing_type}}
- Outbound: {{outbound_type}} to {{outbound_target}}

**Test Scenarios:**
1. Happy path - valid {{message_type}} message
2. Invalid message structure
3. Missing required segments
4. Target system unavailable (retry behaviour)
5. High volume ({{volume_messages}} messages in {{volume_duration}})
6. Character encoding edge cases

**Test Data:**
- Use synthetic patient data only
- NHS Number range: 900 000 0000 - 999 999 9999 (test range)
- Facility: {{test_facility}}

**Acceptance Criteria:**
- All messages acknowledged within {{ack_timeout_ms}}ms
- Zero message loss
- Error handling per specification
- Audit log complete""",
        "variables": {
            "project_name": {"type": "string", "default": "ADT Route"},
            "inbound_type": {"type": "string", "default": "MLLP/TCP"},
            "inbound_port": {"type": "number", "default": 10001},
            "processing_type": {"type": "string", "default": "Routing Engine"},
            "outbound_type": {"type": "string", "default": "MLLP/TCP"},
            "outbound_target": {"type": "string", "default": "PAS"},
            "message_type": {"type": "string", "default": "ADT^A01"},
            "volume_messages": {"type": "number", "default": 1000},
            "volume_duration": {"type": "string", "default": "5 minutes"},
            "test_facility": {"type": "string", "default": "TEST_FACILITY"},
            "ack_timeout_ms": {"type": "number", "default": 500},
        },
        "tags": ["testing", "integration", "qa"],
    },
]


async def seed_templates():
    """Seed default HIE templates if the DB is empty."""
    async with async_session() as db:
        from .models import PromptTemplate
        from .repositories.template_repo import TemplateRepository

        result = await db.execute(
            text("SELECT COUNT(*) FROM prompt_templates")
        )
        count = result.scalar()
        if count and count > 0:
            logger.info(f"Templates table has {count} rows, skipping seed")
            return

        repo = TemplateRepository(db)
        for tpl_data in SEED_TEMPLATES:
            await repo.create(
                name=tpl_data["name"],
                template_body=tpl_data["template_body"],
                category=tpl_data["category"],
                description=tpl_data["description"],
                variables=tpl_data.get("variables"),
                tags=tpl_data.get("tags"),
            )
            logger.info(f"Seeded template: {tpl_data['name']}")

        logger.info(f"Seeded {len(SEED_TEMPLATES)} default templates")


@app.on_event("startup")
async def on_startup():
    """Create tables and seed data on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    try:
        await seed_templates()
    except Exception as e:
        logger.warning(f"Template seeding failed (may be first run): {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hie-prompt-manager", "version": "1.6.0"}
