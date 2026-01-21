"""
HIE Canonical Message Format

The canonical message format is the internal representation that all external
message formats (HL7v2, FHIR, CSV, XML, etc.) can be converted to and from.

This enables:
1. Protocol-agnostic processing and routing
2. Unified transformation logic
3. Format conversion between any supported protocols
4. Consistent validation and enrichment

Architecture:
    External Format → Parser → CanonicalMessage → Serializer → External Format
    
    HL7v2 ADT^A01 → HL7v2Parser → CanonicalMessage → FHIRSerializer → FHIR Bundle
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class DataType(str, Enum):
    """Supported data types for canonical fields."""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    BINARY = "binary"
    CODE = "code"           # Coded value with system
    IDENTIFIER = "identifier"  # ID with system/type
    REFERENCE = "reference"    # Reference to another resource
    QUANTITY = "quantity"      # Value with unit
    ADDRESS = "address"
    NAME = "name"
    TELECOM = "telecom"
    PERIOD = "period"
    COMPOSITE = "composite"    # Nested structure


class MessageCategory(str, Enum):
    """High-level message categories."""
    ADT = "adt"              # Admission/Discharge/Transfer
    ORDER = "order"          # Orders (lab, radiology, etc.)
    RESULT = "result"        # Results (lab, radiology, etc.)
    DOCUMENT = "document"    # Clinical documents
    FINANCIAL = "financial"  # Billing/financial
    MASTER = "master"        # Master file updates
    QUERY = "query"          # Query messages
    RESPONSE = "response"    # Query responses
    NOTIFICATION = "notification"  # Notifications/alerts
    OTHER = "other"


class EventType(str, Enum):
    """Specific event types within categories."""
    # ADT Events
    ADMIT = "admit"
    DISCHARGE = "discharge"
    TRANSFER = "transfer"
    REGISTER = "register"
    PRE_ADMIT = "pre_admit"
    CANCEL_ADMIT = "cancel_admit"
    CANCEL_DISCHARGE = "cancel_discharge"
    UPDATE_PATIENT = "update_patient"
    MERGE_PATIENT = "merge_patient"
    
    # Order Events
    NEW_ORDER = "new_order"
    UPDATE_ORDER = "update_order"
    CANCEL_ORDER = "cancel_order"
    
    # Result Events
    NEW_RESULT = "new_result"
    UPDATE_RESULT = "update_result"
    FINAL_RESULT = "final_result"
    
    # Generic
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    RESPONSE = "response"


# ============================================================================
# Canonical Data Types
# ============================================================================

class CodedValue(BaseModel):
    """A coded value with coding system reference."""
    model_config = ConfigDict(frozen=True)
    
    code: str = Field(description="The code value")
    system: str | None = Field(default=None, description="Coding system URI/OID")
    display: str | None = Field(default=None, description="Human-readable display")
    version: str | None = Field(default=None, description="Code system version")


class Identifier(BaseModel):
    """An identifier with type and assigning authority."""
    model_config = ConfigDict(frozen=True)
    
    value: str = Field(description="The identifier value")
    system: str | None = Field(default=None, description="Namespace URI")
    type: str | None = Field(default=None, description="Identifier type code")
    assigner: str | None = Field(default=None, description="Assigning authority")


class Quantity(BaseModel):
    """A measured quantity with unit."""
    model_config = ConfigDict(frozen=True)
    
    value: Decimal = Field(description="Numeric value")
    unit: str | None = Field(default=None, description="Unit of measure")
    system: str | None = Field(default=None, description="Unit system (e.g., UCUM)")
    code: str | None = Field(default=None, description="Coded unit")


class Period(BaseModel):
    """A time period with start and end."""
    model_config = ConfigDict(frozen=True)
    
    start: datetime | None = Field(default=None)
    end: datetime | None = Field(default=None)


class HumanName(BaseModel):
    """A human name with components."""
    model_config = ConfigDict(frozen=True)
    
    family: str | None = Field(default=None, description="Family/surname")
    given: list[str] = Field(default_factory=list, description="Given names")
    prefix: list[str] = Field(default_factory=list, description="Name prefixes (Dr., Mr.)")
    suffix: list[str] = Field(default_factory=list, description="Name suffixes (Jr., PhD)")
    use: str | None = Field(default=None, description="Use code (official, nickname)")
    
    @property
    def full_name(self) -> str:
        """Get full formatted name."""
        parts = []
        if self.prefix:
            parts.extend(self.prefix)
        if self.given:
            parts.extend(self.given)
        if self.family:
            parts.append(self.family)
        if self.suffix:
            parts.extend(self.suffix)
        return " ".join(parts)


class Address(BaseModel):
    """A postal address."""
    model_config = ConfigDict(frozen=True)
    
    lines: list[str] = Field(default_factory=list, description="Street address lines")
    city: str | None = Field(default=None)
    state: str | None = Field(default=None, description="State/province/region")
    postal_code: str | None = Field(default=None)
    country: str | None = Field(default=None)
    use: str | None = Field(default=None, description="Use code (home, work)")
    type: str | None = Field(default=None, description="Type (postal, physical)")


class Telecom(BaseModel):
    """A contact point (phone, email, etc.)."""
    model_config = ConfigDict(frozen=True)
    
    value: str = Field(description="The contact value")
    system: str | None = Field(default=None, description="phone, email, fax, etc.")
    use: str | None = Field(default=None, description="home, work, mobile")
    rank: int | None = Field(default=None, description="Preference order")


class Reference(BaseModel):
    """A reference to another resource/segment."""
    model_config = ConfigDict(frozen=True)
    
    type: str = Field(description="Resource type being referenced")
    id: str | None = Field(default=None, description="Resource ID")
    identifier: Identifier | None = Field(default=None, description="Logical identifier")
    display: str | None = Field(default=None, description="Display text")


# ============================================================================
# Canonical Segments (Common Healthcare Data Structures)
# ============================================================================

class PatientSegment(BaseModel):
    """Canonical patient information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    name: HumanName | None = Field(default=None)
    birth_date: date | None = Field(default=None)
    gender: CodedValue | None = Field(default=None)
    address: list[Address] = Field(default_factory=list)
    telecom: list[Telecom] = Field(default_factory=list)
    deceased: bool | None = Field(default=None)
    deceased_datetime: datetime | None = Field(default=None)
    marital_status: CodedValue | None = Field(default=None)
    language: CodedValue | None = Field(default=None)
    
    # NHS-specific
    nhs_number: str | None = Field(default=None)
    gp_practice: str | None = Field(default=None)


class EncounterSegment(BaseModel):
    """Canonical encounter/visit information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    status: CodedValue | None = Field(default=None)
    class_code: CodedValue | None = Field(default=None, description="inpatient, outpatient, emergency")
    type: list[CodedValue] = Field(default_factory=list)
    period: Period | None = Field(default=None)
    reason: list[CodedValue] = Field(default_factory=list)
    location: Reference | None = Field(default=None)
    service_provider: Reference | None = Field(default=None)
    
    # Admission details
    admit_source: CodedValue | None = Field(default=None)
    discharge_disposition: CodedValue | None = Field(default=None)


class ProviderSegment(BaseModel):
    """Canonical provider/practitioner information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    name: HumanName | None = Field(default=None)
    role: CodedValue | None = Field(default=None)
    specialty: list[CodedValue] = Field(default_factory=list)
    organization: Reference | None = Field(default=None)
    telecom: list[Telecom] = Field(default_factory=list)


class LocationSegment(BaseModel):
    """Canonical location information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    name: str | None = Field(default=None)
    type: CodedValue | None = Field(default=None)
    address: Address | None = Field(default=None)
    
    # Bed/room details
    facility: str | None = Field(default=None)
    building: str | None = Field(default=None)
    floor: str | None = Field(default=None)
    room: str | None = Field(default=None)
    bed: str | None = Field(default=None)


class OrderSegment(BaseModel):
    """Canonical order information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    status: CodedValue | None = Field(default=None)
    intent: CodedValue | None = Field(default=None)
    category: list[CodedValue] = Field(default_factory=list)
    code: CodedValue | None = Field(default=None)
    priority: CodedValue | None = Field(default=None)
    quantity: Quantity | None = Field(default=None)
    occurrence: datetime | Period | None = Field(default=None)
    requester: Reference | None = Field(default=None)
    performer: Reference | None = Field(default=None)
    reason: list[CodedValue] = Field(default_factory=list)
    note: list[str] = Field(default_factory=list)


class ObservationSegment(BaseModel):
    """Canonical observation/result information."""
    model_config = ConfigDict(frozen=True)
    
    identifiers: list[Identifier] = Field(default_factory=list)
    status: CodedValue | None = Field(default=None)
    category: list[CodedValue] = Field(default_factory=list)
    code: CodedValue | None = Field(default=None)
    effective: datetime | Period | None = Field(default=None)
    issued: datetime | None = Field(default=None)
    
    # Value (one of these)
    value_quantity: Quantity | None = Field(default=None)
    value_string: str | None = Field(default=None)
    value_code: CodedValue | None = Field(default=None)
    value_boolean: bool | None = Field(default=None)
    value_datetime: datetime | None = Field(default=None)
    
    # Reference ranges
    reference_range_low: Quantity | None = Field(default=None)
    reference_range_high: Quantity | None = Field(default=None)
    reference_range_text: str | None = Field(default=None)
    
    interpretation: CodedValue | None = Field(default=None)
    note: list[str] = Field(default_factory=list)
    performer: list[Reference] = Field(default_factory=list)


# ============================================================================
# Canonical Message
# ============================================================================

class MessageHeader(BaseModel):
    """Canonical message header."""
    model_config = ConfigDict(frozen=True)
    
    # Identity
    message_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Classification
    category: MessageCategory = Field(default=MessageCategory.OTHER)
    event_type: EventType | None = Field(default=None)
    
    # Source format info (for round-trip conversion)
    source_format: str | None = Field(default=None, description="Original format (hl7v2, fhir, csv)")
    source_version: str | None = Field(default=None, description="Format version (2.5, R4)")
    source_message_type: str | None = Field(default=None, description="Original message type (ADT^A01)")
    
    # Sending/Receiving
    sending_application: str | None = Field(default=None)
    sending_facility: str | None = Field(default=None)
    receiving_application: str | None = Field(default=None)
    receiving_facility: str | None = Field(default=None)
    
    # Control
    sequence_number: str | None = Field(default=None)
    continuation_pointer: str | None = Field(default=None)
    accept_ack_type: str | None = Field(default=None)
    application_ack_type: str | None = Field(default=None)


class CanonicalMessage(BaseModel):
    """
    The canonical message format for HIE.
    
    All external message formats are converted to this internal representation
    for processing, routing, and transformation. This enables:
    
    1. Protocol-agnostic business logic
    2. Unified routing rules
    3. Format conversion between any supported protocols
    4. Consistent validation
    
    Structure:
    - header: Message metadata and classification
    - patient: Patient demographics (if applicable)
    - encounter: Visit/encounter info (if applicable)
    - providers: Healthcare providers involved
    - locations: Relevant locations
    - orders: Order information (if applicable)
    - observations: Results/observations (if applicable)
    - extensions: Custom/unmapped data
    - raw: Original message preserved
    """
    model_config = ConfigDict(frozen=True)
    
    # Header
    header: MessageHeader = Field(default_factory=MessageHeader)
    
    # Core segments (all optional, populated based on message type)
    patient: PatientSegment | None = Field(default=None)
    encounter: EncounterSegment | None = Field(default=None)
    providers: list[ProviderSegment] = Field(default_factory=list)
    locations: list[LocationSegment] = Field(default_factory=list)
    orders: list[OrderSegment] = Field(default_factory=list)
    observations: list[ObservationSegment] = Field(default_factory=list)
    
    # Extensions for custom/unmapped data
    extensions: dict[str, Any] = Field(default_factory=dict)
    
    # Original message preserved for audit/debugging
    raw_content: bytes | None = Field(default=None)
    raw_content_type: str | None = Field(default=None)
    
    def with_updates(self, **kwargs: Any) -> CanonicalMessage:
        """Return a new CanonicalMessage with updated fields."""
        data = self.model_dump()
        data.update(kwargs)
        return CanonicalMessage.model_validate(data)
    
    def get_patient_id(self, system: str | None = None) -> str | None:
        """Get patient identifier, optionally filtered by system."""
        if not self.patient:
            return None
        for ident in self.patient.identifiers:
            if system is None or ident.system == system:
                return ident.value
        return None
    
    def get_nhs_number(self) -> str | None:
        """Get NHS number if available."""
        if self.patient and self.patient.nhs_number:
            return self.patient.nhs_number
        return self.get_patient_id("https://fhir.nhs.uk/Id/nhs-number")


# ============================================================================
# Protocol Converters (Abstract Base)
# ============================================================================

class MessageParser:
    """Base class for parsing external formats to canonical."""
    
    def can_parse(self, content: bytes, content_type: str) -> bool:
        """Check if this parser can handle the content."""
        raise NotImplementedError
    
    def parse(self, content: bytes, content_type: str) -> CanonicalMessage:
        """Parse external format to canonical message."""
        raise NotImplementedError


class MessageSerializer:
    """Base class for serializing canonical to external formats."""
    
    def serialize(self, message: CanonicalMessage) -> tuple[bytes, str]:
        """Serialize canonical message to external format.
        
        Returns:
            Tuple of (content_bytes, content_type)
        """
        raise NotImplementedError


# ============================================================================
# Format Registry
# ============================================================================

class FormatRegistry:
    """Registry for message format parsers and serializers."""
    
    def __init__(self):
        self._parsers: dict[str, MessageParser] = {}
        self._serializers: dict[str, MessageSerializer] = {}
    
    def register_parser(self, format_name: str, parser: MessageParser) -> None:
        """Register a parser for a format."""
        self._parsers[format_name] = parser
    
    def register_serializer(self, format_name: str, serializer: MessageSerializer) -> None:
        """Register a serializer for a format."""
        self._serializers[format_name] = serializer
    
    def get_parser(self, format_name: str) -> MessageParser | None:
        """Get parser for a format."""
        return self._parsers.get(format_name)
    
    def get_serializer(self, format_name: str) -> MessageSerializer | None:
        """Get serializer for a format."""
        return self._serializers.get(format_name)
    
    def parse(self, content: bytes, content_type: str) -> CanonicalMessage:
        """Parse content using appropriate parser."""
        # Try to find parser by content type
        for name, parser in self._parsers.items():
            if parser.can_parse(content, content_type):
                return parser.parse(content, content_type)
        raise ValueError(f"No parser found for content type: {content_type}")
    
    def convert(
        self,
        content: bytes,
        source_type: str,
        target_format: str,
    ) -> tuple[bytes, str]:
        """Convert from one format to another via canonical."""
        canonical = self.parse(content, source_type)
        serializer = self.get_serializer(target_format)
        if not serializer:
            raise ValueError(f"No serializer found for format: {target_format}")
        return serializer.serialize(canonical)
    
    @property
    def supported_formats(self) -> list[str]:
        """List all supported formats."""
        return list(set(self._parsers.keys()) | set(self._serializers.keys()))


# Global registry instance
format_registry = FormatRegistry()
