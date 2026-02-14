"""
LI FHIR Hosts

Implements FHIR R4/R5 service, operation, and message classes for the
OpenLI HIE integration engine.

Class Hierarchy (mirrors IRIS HS.FHIR.* + EnsLib.* pattern):

    FHIRMessage            — In-memory FHIR resource container (like HL7Message)
    FHIRRESTService        — Inbound FHIR REST service (BusinessService + InboundHTTPAdapter)
    FHIRRESTOperation      — Outbound FHIR REST client  (BusinessOperation + OutboundHTTPAdapter)

All hosts run as standalone async worker loops with configurable pool_size,
queue-based message reception, and full callback support (on_init, on_start,
on_stop, on_teardown, on_before_process, on_after_process, on_process_error).
They can receive/respond to any FHIR or arbitrary message event, and call any
other service items via send_to_targets / send_request_async / send_request_sync
using the already-defined interaction patterns (reliable, sync, async).

IRIS equivalents:
    FHIRRESTService   ≈ HS.FHIRServer.Interop.Service
    FHIRRESTOperation ≈ HS.FHIR.REST.Operation

Rhapsody equivalent: HTTP Communication Point + FHIR Message Definition
Mirth equivalent:    FHIR Listener / FHIR Sender connectors
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

from Engine.li.hosts.base import BusinessService, BusinessOperation, HostMetrics
from Engine.li.adapters.http import (
    InboundHTTPAdapter, OutboundHTTPAdapter,
    HTTPRequest, HTTPResponse,
)
from Engine.li.registry import ClassRegistry

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


# =========================================================================
# FHIR Constants
# =========================================================================

FHIR_JSON_CONTENT_TYPE = "application/fhir+json"
FHIR_XML_CONTENT_TYPE = "application/fhir+xml"
FHIR_JSON_PATCH_CONTENT_TYPE = "application/json-patch+json"

# Standard FHIR resource types (R4 subset — extensible)
FHIR_RESOURCE_TYPES = frozenset({
    "Patient", "Practitioner", "PractitionerRole", "Organization", "Location",
    "Encounter", "EpisodeOfCare", "Condition", "Procedure", "Observation",
    "DiagnosticReport", "AllergyIntolerance", "MedicationRequest",
    "MedicationAdministration", "MedicationStatement", "Medication",
    "Immunization", "CarePlan", "CareTeam", "Goal", "ServiceRequest",
    "DocumentReference", "Composition", "Bundle", "MessageHeader",
    "OperationOutcome", "Consent", "Coverage", "Claim", "ExplanationOfBenefit",
    "Appointment", "Schedule", "Slot", "Task", "Communication",
    "CommunicationRequest", "QuestionnaireResponse", "Questionnaire",
    "ValueSet", "CodeSystem", "StructureDefinition", "CapabilityStatement",
    "SubscriptionTopic", "Subscription", "AuditEvent", "Provenance",
    "Binary", "Parameters",
})

# FHIR interaction types
FHIR_INTERACTIONS = frozenset({
    "read", "vread", "update", "patch", "delete", "history",
    "create", "search", "capabilities", "batch", "transaction",
})


# =========================================================================
# FHIR Message — In-Memory Container
# =========================================================================

class FHIRMessage:
    """
    FHIR resource container — the in-memory message object.

    Holds raw JSON/XML bytes, parsed resource dict, and metadata.
    Equivalent to HL7Message but for FHIR resources.

    IRIS equivalent: HS.FHIRServer.Interop.Request (the in-memory message).
    The header_id and body_id fields link to the persisted trace tables
    (message_headers / message_bodies) for Visual Trace support.
    """

    def __init__(
        self,
        raw: bytes,
        parsed: dict | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        fhir_version: str = "R4",
        interaction: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        content_type: str = FHIR_JSON_CONTENT_TYPE,
        response_status: int | None = None,
        received_at: datetime | None = None,
        source: str | None = None,
        validation_errors: list | None = None,
        error: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        header_id: UUID | None = None,
        body_id: UUID | None = None,
    ):
        self.raw = raw
        self.parsed = parsed
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.fhir_version = fhir_version
        self.interaction = interaction
        self.http_method = http_method
        self.http_path = http_path
        self.content_type = content_type
        self.response_status = response_status
        self.received_at = received_at or datetime.now(timezone.utc)
        self.source = source
        self.validation_errors = validation_errors or []
        self.error = error
        self.session_id = session_id
        self.correlation_id = correlation_id
        self.header_id = header_id
        self.body_id = body_id

    @property
    def message_type(self) -> str | None:
        """Get message type string for trace display (e.g., 'Patient/create')."""
        parts = []
        if self.resource_type:
            parts.append(self.resource_type)
        if self.interaction:
            parts.append(self.interaction)
        return "/".join(parts) if parts else None

    @property
    def is_valid(self) -> bool:
        """Check if message is valid."""
        return self.error is None and len(self.validation_errors) == 0

    @property
    def is_bundle(self) -> bool:
        """Check if this is a Bundle resource."""
        return self.resource_type == "Bundle"

    @property
    def bundle_type(self) -> str | None:
        """Get Bundle type if this is a Bundle."""
        if self.parsed and self.resource_type == "Bundle":
            return self.parsed.get("type")
        return None

    def get_field(self, path: str, default: Any = None) -> Any:
        """
        Get a field value from the parsed FHIR resource using dot notation.

        Supports simple FHIRPath-like access:
            "resourceType"           → "Patient"
            "name.0.family"          → "Smith"
            "identifier.0.value"     → "NHS1234567890"
            "meta.versionId"         → "1"

        Args:
            path: Dot-separated field path
            default: Default value if not found

        Returns:
            Field value or default
        """
        if not self.parsed:
            return default

        current = self.parsed
        for part in path.split("."):
            if current is None:
                return default
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return default
            else:
                return default

        return current if current is not None else default

    def with_header_id(self, header_id: UUID) -> FHIRMessage:
        """Return a copy with updated header_id for downstream propagation."""
        return FHIRMessage(
            raw=self.raw,
            parsed=self.parsed,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            fhir_version=self.fhir_version,
            interaction=self.interaction,
            http_method=self.http_method,
            http_path=self.http_path,
            content_type=self.content_type,
            response_status=self.response_status,
            received_at=self.received_at,
            source=self.source,
            validation_errors=self.validation_errors,
            error=self.error,
            session_id=self.session_id,
            correlation_id=self.correlation_id,
            header_id=header_id,
            body_id=self.body_id,
        )

    def __repr__(self) -> str:
        return (
            f"FHIRMessage(type={self.resource_type}, "
            f"interaction={self.interaction}, "
            f"id={self.resource_id}, "
            f"valid={self.is_valid})"
        )


# =========================================================================
# FHIR REST URL Parser
# =========================================================================

def parse_fhir_url(path: str, method: str) -> dict[str, str | None]:
    """
    Parse a FHIR REST URL into resource type, id, and interaction.

    Supports:
        GET    /Patient/123              → read
        GET    /Patient/123/_history/2   → vread
        GET    /Patient/123/_history     → history (instance)
        GET    /Patient                  → search
        GET    /Patient?name=Smith       → search
        GET    /metadata                 → capabilities
        POST   /Patient                  → create
        POST   /                         → transaction/batch (Bundle)
        PUT    /Patient/123              → update
        PATCH  /Patient/123              → patch
        DELETE /Patient/123              → delete

    Returns:
        Dict with keys: resource_type, resource_id, interaction, vid
    """
    # Strip leading slash and base path segments like /fhir/r4
    path = path.strip("/")

    # Remove common base path prefixes
    for prefix in ("fhir/r4", "fhir/r5", "fhir", "r4", "r5"):
        if path.lower().startswith(prefix + "/"):
            path = path[len(prefix) + 1:]
        elif path.lower() == prefix:
            path = ""

    parts = [p for p in path.split("/") if p]

    result: dict[str, str | None] = {
        "resource_type": None,
        "resource_id": None,
        "interaction": None,
        "vid": None,
    }

    # GET /metadata → capabilities
    if len(parts) == 1 and parts[0] == "metadata":
        result["interaction"] = "capabilities"
        return result

    # POST / (empty path) → transaction/batch
    if not parts and method == "POST":
        result["interaction"] = "transaction"
        result["resource_type"] = "Bundle"
        return result

    if len(parts) >= 1:
        resource_type = parts[0]
        # Validate it looks like a resource type (capitalized)
        if resource_type[0].isupper():
            result["resource_type"] = resource_type

    if len(parts) >= 2:
        second = parts[1]
        if second == "_history":
            # GET /Patient/_history → history (type-level)
            result["interaction"] = "history"
            return result
        elif second.startswith("$"):
            # POST /Patient/$validate → operation
            result["interaction"] = second
            return result
        else:
            result["resource_id"] = second

    if len(parts) >= 3:
        third = parts[2]
        if third == "_history":
            if len(parts) >= 4:
                # GET /Patient/123/_history/2 → vread
                result["vid"] = parts[3]
                result["interaction"] = "vread"
            else:
                # GET /Patient/123/_history → history (instance)
                result["interaction"] = "history"
            return result
        elif third.startswith("$"):
            result["interaction"] = third
            return result

    # Determine interaction from method + what we have
    if result["interaction"] is None:
        if result["resource_id"]:
            method_map = {
                "GET": "read",
                "PUT": "update",
                "PATCH": "patch",
                "DELETE": "delete",
            }
            result["interaction"] = method_map.get(method, "read")
        elif result["resource_type"]:
            if method == "POST":
                result["interaction"] = "create"
            elif method == "GET":
                result["interaction"] = "search"

    return result


# =========================================================================
# FHIR OperationOutcome Builder
# =========================================================================

def build_operation_outcome(
    severity: str = "error",
    code: str = "processing",
    diagnostics: str = "",
    http_status: int = 400,
) -> tuple[bytes, int]:
    """
    Build a FHIR OperationOutcome resource.

    Args:
        severity: "fatal", "error", "warning", "information"
        code: Issue type code (e.g., "processing", "not-found", "invalid")
        diagnostics: Human-readable diagnostic message
        http_status: HTTP status code to return

    Returns:
        Tuple of (JSON bytes, HTTP status code)
    """
    outcome = {
        "resourceType": "OperationOutcome",
        "issue": [
            {
                "severity": severity,
                "code": code,
                "diagnostics": diagnostics,
            }
        ],
    }
    return json.dumps(outcome, separators=(",", ":")).encode("utf-8"), http_status


# =========================================================================
# Trace Storage Helpers (IRIS-convention per-leg model)
# =========================================================================

async def _store_inbound_fhir(
    project_id: UUID,
    item_name: str,
    raw_content: bytes,
    resource_type: str | None,
    interaction: str | None,
    status: str,
    fhir_version: str = "R4",
    content_type: str = FHIR_JSON_CONTENT_TYPE,
    target_config_names: list[str] | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
    session_id: str | None = None,
    correlation_id: str | None = None,
) -> tuple[str, UUID | None, UUID | None]:
    """
    Store inbound FHIR message using IRIS-convention per-leg trace model.

    1. Stores body once in message_bodies (body_class_name='FHIRMessageBody')
    2. Creates one message_header per target (one arrow per target)

    Returns (session_id, header_id, body_id).
    """
    if not session_id:
        session_id = f"SES-{uuid4()}"

    header_id = None
    body_id = None

    try:
        from Engine.api.services.message_store import (
            store_message_body, store_message_header,
        )

        # Build message_type string for trace display
        message_type = None
        if resource_type and interaction:
            message_type = f"{resource_type}/{interaction}"
        elif resource_type:
            message_type = resource_type

        # Step 1: Store body once
        body_id = await store_message_body(
            raw_content=raw_content,
            body_class_name='FHIRMessageBody',
            content_type=content_type,
            fhir_version=fhir_version,
            resource_type=resource_type,
        )

        # Step 2: Create one header per target
        targets = target_config_names or []
        is_err = status in ('error', 'failed')

        if targets:
            for target_name in targets:
                header_id = await store_message_header(
                    project_id=project_id,
                    session_id=session_id,
                    source_config_name=item_name,
                    target_config_name=target_name,
                    source_business_type='service',
                    target_business_type='process',
                    message_body_id=body_id,
                    message_type=message_type,
                    body_class_name='FHIRMessageBody',
                    status='Completed' if not is_err else 'Error',
                    is_error=is_err,
                    error_status=error_message,
                    correlation_id=correlation_id,
                )
        else:
            header_id = await store_message_header(
                project_id=project_id,
                session_id=session_id,
                source_config_name=item_name,
                target_config_name=item_name,
                source_business_type='service',
                target_business_type='service',
                message_body_id=body_id,
                message_type=message_type,
                body_class_name='FHIRMessageBody',
                status='Completed' if not is_err else 'Error',
                is_error=is_err,
                error_status=error_message,
                correlation_id=correlation_id,
            )

    except Exception as e:
        logger.warning("fhir_inbound_storage_failed", error=str(e))

    return session_id, header_id, body_id


async def _store_outbound_fhir(
    project_id: UUID,
    item_name: str,
    raw_content: bytes,
    response_content: bytes | None,
    status: str,
    resource_type: str | None = None,
    interaction: str | None = None,
    fhir_version: str = "R4",
    content_type: str = FHIR_JSON_CONTENT_TYPE,
    error_message: str | None = None,
    session_id: str | None = None,
    correlation_id: str | None = None,
    header_id: UUID | None = None,
) -> None:
    """
    Store outbound FHIR message using IRIS-convention per-leg trace model.

    1. Updates the existing header status (the leg that caused this send)
    2. If response received, creates a Response header linking back
    """
    try:
        from Engine.api.services.message_store import (
            store_message_body, store_message_header, update_header_status,
        )

        is_err = status in ('failed', 'error')

        # Step 1: Update the header that caused this leg
        if header_id:
            await update_header_status(
                header_id=header_id,
                status='Completed' if not is_err else 'Error',
                is_error=is_err,
                error_status=error_message,
            )

        # Step 2: If response received, create a Response header
        if response_content and session_id:
            resp_body_id = await store_message_body(
                raw_content=response_content,
                body_class_name='FHIRMessageBody',
                content_type=content_type,
                fhir_version=fhir_version,
                resource_type=resource_type,
            )

            message_type = None
            if resource_type and interaction:
                message_type = f"{resource_type}/{interaction}/response"
            elif resource_type:
                message_type = f"{resource_type}/response"

            await store_message_header(
                project_id=project_id,
                session_id=session_id,
                source_config_name=item_name,
                target_config_name=item_name,
                source_business_type='operation',
                target_business_type='process',
                message_body_id=resp_body_id,
                parent_header_id=header_id,
                corresponding_header_id=header_id,
                message_type=message_type,
                body_class_name='FHIRMessageBody',
                type='Response',
                status='Completed',
                correlation_id=correlation_id,
            )

    except Exception as e:
        logger.warning("fhir_outbound_storage_failed", error=str(e))


# =========================================================================
# FHIR REST Service — IRIS HS.FHIRServer.Interop.Service
# =========================================================================

class FHIRRESTService(BusinessService):
    """
    FHIR R4/R5 REST Service — receives FHIR requests via HTTP.

    Listens for FHIR REST requests (GET/POST/PUT/DELETE/PATCH), parses
    the resource, validates it, stores the message trace, and routes
    to configured targets.

    Runs as a standalone async worker loop with configurable pool_size.
    Full callback support: on_init, on_start, on_stop, on_teardown,
    on_before_process, on_after_process, on_process_error.
    Can call any other service item via send_to_targets, send_request_async,
    send_request_sync using reliable/sync/async interaction patterns.

    IRIS equivalent: HS.FHIRServer.Interop.Service
    Rhapsody equivalent: HTTP Communication Point (Input) + FHIR parser
    Mirth equivalent: FHIR Listener connector

    Settings (Host):
        FHIRVersion:         FHIR version (default: R4)
        TargetConfigNames:   Comma-separated list of target hosts
        ValidateResources:   Validate FHIR resources (default: false)
        BadMessageHandler:   Target for invalid messages
        AlertOnError:        Send alert on errors (default: true)
        AcceptedFormats:     Accepted content types (default: json)
                             Options: "json", "xml", "both"

    Settings (Adapter):
        Port:           HTTP port to listen on (required)
        Host:           IP address to bind to (default: 0.0.0.0)
        BasePath:       URL base path (default: /fhir/r4)
        AllowedMethods: HTTP methods (default: GET,POST,PUT,DELETE,PATCH)
        EnableCORS:     Enable CORS (default: true, required for SMART on FHIR)
        SSLCertFile:    Path to SSL certificate (optional)
        SSLKeyFile:     Path to SSL key (optional)

    Example Config:
        <Item Name="FHIR.In.REST" ClassName="li.hosts.fhir.FHIRRESTService" PoolSize="2" Enabled="true">
            <Setting Target="Adapter" Name="Port">9380</Setting>
            <Setting Target="Adapter" Name="BasePath">/fhir/r4</Setting>
            <Setting Target="Adapter" Name="AllowedMethods">GET,POST,PUT,DELETE,PATCH</Setting>
            <Setting Target="Adapter" Name="EnableCORS">true</Setting>
            <Setting Target="Host" Name="FHIRVersion">R4</Setting>
            <Setting Target="Host" Name="TargetConfigNames">FHIR.Router</Setting>
        </Item>
    """

    adapter_class = InboundHTTPAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        # Set sensible defaults for FHIR REST
        adapter_settings = adapter_settings or {}
        adapter_settings.setdefault("AllowedMethods", "GET,POST,PUT,DELETE,PATCH")
        adapter_settings.setdefault("EnableCORS", "true")
        adapter_settings.setdefault("BasePath", "/fhir/r4")

        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        # FHIR-specific state
        self._fhir_version = self.get_setting("Host", "FHIRVersion", "R4")
        self._validate_resources = str(
            self.get_setting("Host", "ValidateResources", "false")
        ).lower() == "true"
        self._bad_message_handler = self.get_setting("Host", "BadMessageHandler")
        self._alert_on_error = self.get_setting("Host", "AlertOnError", True)
        self._accepted_formats = self.get_setting("Host", "AcceptedFormats", "json")

        self._log = logger.bind(
            host="FHIRRESTService",
            name=name,
            fhir_version=self._fhir_version,
        )

    async def on_start(self) -> None:
        """Initialize and set up HTTP request handler."""
        await super().on_start()

        # Wire the HTTP adapter to our FHIR request handler
        if isinstance(self._adapter, InboundHTTPAdapter):
            self._adapter.set_request_handler(self._handle_fhir_request)

        self._log.info(
            "fhir_rest_service_started",
            port=self.get_setting("Adapter", "Port"),
            fhir_version=self._fhir_version,
            targets=self.target_config_names,
        )

    async def on_message_received(self, data: bytes) -> Any:
        """
        Process received FHIR data (called from adapter fallback path).

        For HTTP, the primary path is _handle_fhir_request which has
        full HTTP context. This method handles the raw-bytes fallback.
        """
        return await self._parse_fhir_body(data, "POST", "/")

    async def _handle_fhir_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Handle an inbound FHIR REST request.

        Full FHIR REST pipeline:
        1. Parse URL → resource_type, id, interaction
        2. Parse body (JSON/XML)
        3. Validate resource (if configured)
        4. Create FHIRMessage
        5. Store message trace
        6. Route to targets
        7. Return FHIR-compliant HTTP response
        """
        start_time = time.time()
        received_at = datetime.now(timezone.utc)

        # Step 1: Parse FHIR REST URL
        url_info = parse_fhir_url(request.path, request.method)
        resource_type = url_info["resource_type"]
        resource_id = url_info["resource_id"]
        interaction = url_info["interaction"]

        self._log.debug(
            "fhir_request_received",
            method=request.method,
            path=request.path,
            resource_type=resource_type,
            interaction=interaction,
            content_type=request.content_type,
        )

        # Step 2: Handle capabilities request (no body needed)
        if interaction == "capabilities":
            return self._build_capability_statement()

        # Step 3: Parse body for write operations
        parsed = None
        validation_errors: list[str] = []

        if request.body and request.method in ("POST", "PUT", "PATCH"):
            try:
                parsed = self._parse_body(request.body, request.content_type)

                # Extract resource type from body if not in URL
                if parsed and not resource_type:
                    resource_type = parsed.get("resourceType")

                # Extract resource ID from body if not in URL
                if parsed and not resource_id:
                    resource_id = parsed.get("id")

                # Validate resource
                if self._validate_resources and parsed:
                    validation_errors = self._validate_fhir_resource(parsed)

            except Exception as e:
                self._log.warning("fhir_parse_error", error=str(e))
                body, status = build_operation_outcome(
                    severity="error",
                    code="invalid",
                    diagnostics=f"Failed to parse request body: {e}",
                    http_status=400,
                )
                return HTTPResponse(
                    status_code=status,
                    body=body,
                    content_type=FHIR_JSON_CONTENT_TYPE,
                )

        # Step 4: Validation errors → return OperationOutcome
        if validation_errors:
            body, status = build_operation_outcome(
                severity="error",
                code="invalid",
                diagnostics="; ".join(validation_errors[:5]),
                http_status=422,
            )
            # Still store the trace for visibility
            latency_ms = int((time.time() - start_time) * 1000)
            await self._store_and_create_message(
                raw=request.body or b"",
                parsed=parsed,
                resource_type=resource_type,
                resource_id=resource_id,
                interaction=interaction,
                http_method=request.method,
                http_path=request.path,
                content_type=request.content_type or FHIR_JSON_CONTENT_TYPE,
                received_at=received_at,
                validation_errors=validation_errors,
                error="; ".join(validation_errors[:3]),
                status="error",
                latency_ms=latency_ms,
            )
            return HTTPResponse(
                status_code=status,
                body=body,
                content_type=FHIR_JSON_CONTENT_TYPE,
            )

        # Step 5: Create FHIRMessage, store trace, route
        latency_ms = int((time.time() - start_time) * 1000)
        correlation_id = str(uuid4())[:8]

        message = await self._store_and_create_message(
            raw=request.body or b"",
            parsed=parsed,
            resource_type=resource_type,
            resource_id=resource_id,
            interaction=interaction,
            http_method=request.method,
            http_path=request.path,
            content_type=request.content_type or FHIR_JSON_CONTENT_TYPE,
            received_at=received_at,
            validation_errors=[],
            error=None,
            status="completed",
            latency_ms=latency_ms,
            correlation_id=correlation_id,
        )

        # Step 6: Submit to queue for downstream processing
        if message:
            await self.submit(message)

        # Step 7: Return FHIR-compliant response
        return self._build_fhir_response(interaction, resource_type, resource_id, parsed)

    async def _store_and_create_message(
        self,
        raw: bytes,
        parsed: dict | None,
        resource_type: str | None,
        resource_id: str | None,
        interaction: str | None,
        http_method: str,
        http_path: str,
        content_type: str,
        received_at: datetime,
        validation_errors: list[str],
        error: str | None,
        status: str,
        latency_ms: int,
        correlation_id: str | None = None,
    ) -> FHIRMessage | None:
        """Create FHIRMessage and store trace in one step."""
        session_id = None
        header_id = None
        body_id = None

        project_id = getattr(self, 'project_id', None)
        if project_id:
            session_id, header_id, body_id = await _store_inbound_fhir(
                project_id=project_id,
                item_name=self.name,
                raw_content=raw,
                resource_type=resource_type,
                interaction=interaction,
                status=status,
                fhir_version=self._fhir_version,
                content_type=content_type,
                target_config_names=self.target_config_names,
                latency_ms=latency_ms,
                error_message=error,
                session_id=None,
                correlation_id=correlation_id,
            )

        return FHIRMessage(
            raw=raw,
            parsed=parsed,
            resource_type=resource_type,
            resource_id=resource_id,
            fhir_version=self._fhir_version,
            interaction=interaction,
            http_method=http_method,
            http_path=http_path,
            content_type=content_type,
            received_at=received_at,
            source=self.name,
            validation_errors=validation_errors,
            error=error,
            session_id=session_id,
            correlation_id=correlation_id,
            header_id=header_id,
            body_id=body_id,
        )

    def _parse_body(self, body: bytes, content_type: str) -> dict | None:
        """Parse FHIR request body based on content type."""
        if not body:
            return None

        ct = (content_type or "").lower()

        if "json" in ct or "fhir+json" in ct or not ct:
            return json.loads(body)
        elif "xml" in ct or "fhir+xml" in ct:
            # XML parsing — placeholder for future implementation
            # For now, store raw and return minimal parsed info
            self._log.debug("fhir_xml_body_stored_raw")
            return {"resourceType": "Binary", "_raw_xml": True}
        else:
            # Unknown content type — try JSON
            try:
                return json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None

    async def _parse_fhir_body(
        self, data: bytes, method: str, path: str
    ) -> FHIRMessage:
        """Parse raw bytes into a FHIRMessage (fallback path)."""
        parsed = None
        resource_type = None
        resource_id = None

        try:
            parsed = json.loads(data)
            resource_type = parsed.get("resourceType")
            resource_id = parsed.get("id")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        url_info = parse_fhir_url(path, method)

        return FHIRMessage(
            raw=data,
            parsed=parsed,
            resource_type=resource_type or url_info.get("resource_type"),
            resource_id=resource_id or url_info.get("resource_id"),
            fhir_version=self._fhir_version,
            interaction=url_info.get("interaction"),
            http_method=method,
            http_path=path,
            source=self.name,
        )

    def _validate_fhir_resource(self, resource: dict) -> list[str]:
        """
        Validate a FHIR resource.

        Basic structural validation. Override for profile-specific validation.

        Args:
            resource: Parsed FHIR resource dict

        Returns:
            List of validation error strings (empty if valid)
        """
        errors: list[str] = []

        if not isinstance(resource, dict):
            errors.append("Resource must be a JSON object")
            return errors

        rt = resource.get("resourceType")
        if not rt:
            errors.append("Missing required field: resourceType")
        elif rt not in FHIR_RESOURCE_TYPES:
            errors.append(f"Unknown resource type: {rt}")

        return errors

    def _build_fhir_response(
        self,
        interaction: str | None,
        resource_type: str | None,
        resource_id: str | None,
        parsed: dict | None,
    ) -> HTTPResponse:
        """Build a FHIR-compliant HTTP response."""
        headers: dict[str, str] = {}

        if interaction == "create":
            # 201 Created with Location header
            if resource_id:
                headers["Location"] = f"/{resource_type}/{resource_id}"
            body = json.dumps(parsed, separators=(",", ":")).encode() if parsed else b""
            return HTTPResponse(
                status_code=201,
                body=body,
                content_type=FHIR_JSON_CONTENT_TYPE,
                headers=headers,
            )

        elif interaction == "delete":
            return HTTPResponse(
                status_code=204,
                body=b"",
                content_type=FHIR_JSON_CONTENT_TYPE,
            )

        elif interaction in ("read", "vread", "update", "patch"):
            body = json.dumps(parsed, separators=(",", ":")).encode() if parsed else b""
            return HTTPResponse(
                status_code=200,
                body=body,
                content_type=FHIR_JSON_CONTENT_TYPE,
            )

        elif interaction == "search":
            # Return a Bundle searchset
            bundle = {
                "resourceType": "Bundle",
                "type": "searchset",
                "total": 0,
                "entry": [],
            }
            return HTTPResponse(
                status_code=200,
                body=json.dumps(bundle, separators=(",", ":")).encode(),
                content_type=FHIR_JSON_CONTENT_TYPE,
            )

        else:
            # Default 200 OK
            body = json.dumps(parsed, separators=(",", ":")).encode() if parsed else b'{"status":"accepted"}'
            return HTTPResponse(
                status_code=200,
                body=body,
                content_type=FHIR_JSON_CONTENT_TYPE,
            )

    def _build_capability_statement(self) -> HTTPResponse:
        """Build a minimal FHIR CapabilityStatement."""
        cap = {
            "resourceType": "CapabilityStatement",
            "status": "active",
            "kind": "instance",
            "fhirVersion": "4.0.1" if self._fhir_version == "R4" else "5.0.0",
            "format": ["json"],
            "rest": [
                {
                    "mode": "server",
                    "resource": [
                        {
                            "type": rt,
                            "interaction": [
                                {"code": "read"},
                                {"code": "create"},
                                {"code": "update"},
                                {"code": "delete"},
                                {"code": "search-type"},
                            ],
                        }
                        for rt in sorted(FHIR_RESOURCE_TYPES)[:20]  # Top 20 for brevity
                    ],
                }
            ],
        }
        return HTTPResponse(
            status_code=200,
            body=json.dumps(cap, indent=2).encode(),
            content_type=FHIR_JSON_CONTENT_TYPE,
        )

    async def _process_message(self, message: Any) -> Any:
        """Process a FHIR message — route to targets."""
        if isinstance(message, FHIRMessage) and message.error:
            if self._bad_message_handler:
                self._log.warning(
                    "fhir_bad_message",
                    error=message.error,
                    handler=self._bad_message_handler,
                )
            return message

        targets = self.target_config_names
        if targets:
            self._log.debug(
                "fhir_routing_message",
                resource_type=getattr(message, 'resource_type', None),
                interaction=getattr(message, 'interaction', None),
                targets=targets,
            )
            await self.send_to_targets(message)

        return message


# =========================================================================
# FHIR REST Operation — IRIS HS.FHIR.REST.Operation
# =========================================================================

class FHIRRESTOperation(BusinessOperation):
    """
    FHIR R4/R5 REST Operation — sends FHIR requests to remote FHIR servers.

    Makes HTTP requests to a configured FHIR server URL and processes
    the response. Supports all FHIR interactions (read, create, update,
    delete, search, transaction).

    Runs as a standalone async worker loop with configurable pool_size.
    Full callback support: on_init, on_start, on_stop, on_teardown,
    on_before_process, on_after_process, on_process_error.
    Can call any other service item via send_request_async / send_request_sync.

    IRIS equivalent: HS.FHIR.REST.Operation
    Rhapsody equivalent: HTTP Communication Point (Output) + FHIR
    Mirth equivalent: FHIR Sender connector

    Settings (Host):
        FHIRVersion:         FHIR version (default: R4)
        AlertOnError:        Send alert on errors (default: true)
        FailureTimeout:      Timeout before marking as failed (default: -1)
        RetryInterval:       Interval between retries (default: 5)

    Settings (Adapter):
        URL:             Base URL of remote FHIR server (required, e.g., http://fhir:8080/fhir/r4)
        ContentType:     Content-Type header (default: application/fhir+json)
        HTTPMethod:      Default HTTP method (default: POST)
        ConnectTimeout:  Connection timeout (default: 10)
        ResponseTimeout: Response timeout (default: 30)
        MaxRetries:      Maximum retries (default: 3)
        SSLVerify:       Verify SSL certificates (default: true)
        CustomHeaders:   JSON string of additional headers (optional)

    Example Config:
        <Item Name="FHIR.Out.REST" ClassName="li.hosts.fhir.FHIRRESTOperation" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="URL">http://fhir-server:8080/fhir/r4</Setting>
            <Setting Target="Adapter" Name="ContentType">application/fhir+json</Setting>
            <Setting Target="Host" Name="FHIRVersion">R4</Setting>
        </Item>
    """

    adapter_class = OutboundHTTPAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        # Set sensible defaults for FHIR REST
        adapter_settings = adapter_settings or {}
        adapter_settings.setdefault("ContentType", FHIR_JSON_CONTENT_TYPE)

        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        # FHIR-specific state
        self._fhir_version = self.get_setting("Host", "FHIRVersion", "R4")
        self._base_url = self.get_setting("Adapter", "URL", "http://localhost:8080/fhir/r4")

        self._log = logger.bind(
            host="FHIRRESTOperation",
            name=name,
            fhir_version=self._fhir_version,
            url=self._base_url,
        )

    async def on_start(self) -> None:
        """Initialize the FHIR operation."""
        await super().on_start()
        self._log.info(
            "fhir_rest_operation_started",
            url=self._base_url,
            fhir_version=self._fhir_version,
        )

    async def on_message(self, message: Any) -> Any:
        """
        Send a FHIR message to the remote server.

        Accepts FHIRMessage or raw bytes. Extracts the appropriate
        HTTP method and path from the FHIRMessage metadata, or
        defaults to POST for raw bytes.

        Args:
            message: FHIRMessage or raw bytes

        Returns:
            FHIRSendResult with response details
        """
        session_id = None
        correlation_id = None
        header_id = None
        resource_type = None
        interaction = None

        if isinstance(message, FHIRMessage):
            data = message.raw
            session_id = message.session_id
            correlation_id = message.correlation_id
            header_id = message.header_id
            resource_type = message.resource_type
            interaction = message.interaction
        elif isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
            session_id = getattr(message, 'session_id', None)
            correlation_id = getattr(message, 'correlation_id', None)
            header_id = getattr(message, 'header_id', None)
            resource_type = getattr(message, 'resource_type', None)
            interaction = getattr(message, 'interaction', None)
        else:
            data = str(message).encode("utf-8")

        try:
            # Send via adapter
            response_bytes = await self._adapter.send(data)

            # Parse response
            response_parsed = None
            response_resource_type = None
            try:
                response_parsed = json.loads(response_bytes)
                response_resource_type = response_parsed.get("resourceType")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

            self._log.debug(
                "fhir_message_sent",
                resource_type=resource_type,
                interaction=interaction,
                response_type=response_resource_type,
                response_size=len(response_bytes),
            )

            # Check for OperationOutcome errors
            is_error = (
                response_resource_type == "OperationOutcome"
                and response_parsed
                and any(
                    issue.get("severity") in ("error", "fatal")
                    for issue in response_parsed.get("issue", [])
                )
            )

            # Store outbound trace
            project_id = getattr(self, 'project_id', None)
            if project_id:
                asyncio.create_task(_store_outbound_fhir(
                    project_id=project_id,
                    item_name=self.name,
                    raw_content=data,
                    response_content=response_bytes,
                    status="error" if is_error else "sent",
                    resource_type=resource_type,
                    interaction=interaction,
                    fhir_version=self._fhir_version,
                    error_message=self._extract_error(response_parsed) if is_error else None,
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))

            return FHIRSendResult(
                success=not is_error,
                response_raw=response_bytes,
                response_parsed=response_parsed,
                response_resource_type=response_resource_type,
                error=self._extract_error(response_parsed) if is_error else None,
            )

        except Exception as e:
            self._log.error("fhir_send_error", error=str(e))

            # Store failed trace
            project_id = getattr(self, 'project_id', None)
            if project_id:
                asyncio.create_task(_store_outbound_fhir(
                    project_id=project_id,
                    item_name=self.name,
                    raw_content=data,
                    response_content=None,
                    status="failed",
                    resource_type=resource_type,
                    interaction=interaction,
                    fhir_version=self._fhir_version,
                    error_message=str(e),
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))

            raise FHIRSendError(f"FHIR send failed: {e}")

    def _extract_error(self, parsed: dict | None) -> str | None:
        """Extract error message from an OperationOutcome."""
        if not parsed:
            return None
        issues = parsed.get("issue", [])
        errors = [
            issue.get("diagnostics", issue.get("code", "unknown"))
            for issue in issues
            if issue.get("severity") in ("error", "fatal")
        ]
        return "; ".join(errors) if errors else None


# =========================================================================
# FHIR Send Result
# =========================================================================

class FHIRSendResult:
    """Result of sending a FHIR message."""

    def __init__(
        self,
        success: bool,
        response_raw: bytes | None = None,
        response_parsed: dict | None = None,
        response_resource_type: str | None = None,
        http_status: int | None = None,
        error: str | None = None,
    ):
        self.success = success
        self.response_raw = response_raw
        self.response_parsed = response_parsed
        self.response_resource_type = response_resource_type
        self.http_status = http_status
        self.error = error

    def __repr__(self) -> str:
        return (
            f"FHIRSendResult(success={self.success}, "
            f"type={self.response_resource_type}, "
            f"error={self.error})"
        )


class FHIRSendError(Exception):
    """Error sending FHIR message."""
    pass


# =========================================================================
# ClassRegistry Registration
# =========================================================================

# Register core classes (internal — protected namespace)
ClassRegistry._register_internal("li.hosts.fhir.FHIRRESTService", FHIRRESTService)
ClassRegistry._register_internal("li.hosts.fhir.FHIRRESTOperation", FHIRRESTOperation)

# IRIS compatibility aliases
ClassRegistry.register_alias("HS.FHIRServer.Interop.Service", "li.hosts.fhir.FHIRRESTService")
ClassRegistry.register_alias("HS.FHIR.REST.Operation", "li.hosts.fhir.FHIRRESTOperation")
