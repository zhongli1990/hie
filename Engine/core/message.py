"""
HIE Message Model

The message model is deliberately simple and strict:
- Envelope: routing, delivery, governance, and operational metadata
- Payload: raw message content with typed properties

Key principle: Raw-first, parse-on-demand. Messages are stored and transported
in raw form. Parsing occurs only when explicitly required.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Self
from uuid import UUID, uuid4

import msgpack
from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """Message processing priority."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Sensitivity(str, Enum):
    """Data sensitivity classification."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DeliveryMode(str, Enum):
    """Message delivery guarantees."""
    AT_LEAST_ONCE = "at_least_once"
    AT_MOST_ONCE = "at_most_once"


class MessageState(str, Enum):
    """Message lifecycle state."""
    CREATED = "created"
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class PropertyType(str, Enum):
    """Supported property types for payload properties."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    BYTES = "bytes"
    LIST = "list"
    DICT = "dict"


@dataclass(frozen=True, slots=True)
class Property:
    """
    A typed property value for payload properties.
    
    Properties are explicitly set, typed, and bounded.
    They are NOT a free-form property bag.
    """
    value: Any
    type: PropertyType
    max_size: int | None = None
    
    def __post_init__(self) -> None:
        if self.max_size is not None:
            if isinstance(self.value, (str, bytes, list, dict)):
                if len(self.value) > self.max_size:
                    raise ValueError(
                        f"Property value exceeds max_size: {len(self.value)} > {self.max_size}"
                    )
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize property to dictionary."""
        value = self.value
        if self.type == PropertyType.DATETIME and isinstance(value, datetime):
            value = value.isoformat()
        elif self.type == PropertyType.BYTES and isinstance(value, bytes):
            value = value.hex()
        return {
            "value": value,
            "type": self.type.value,
            "max_size": self.max_size,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Property:
        """Deserialize property from dictionary."""
        value = data["value"]
        prop_type = PropertyType(data["type"])
        if prop_type == PropertyType.DATETIME and isinstance(value, str):
            value = datetime.fromisoformat(value)
        elif prop_type == PropertyType.BYTES and isinstance(value, str):
            value = bytes.fromhex(value)
        return cls(
            value=value,
            type=prop_type,
            max_size=data.get("max_size"),
        )


class RoutingInfo(BaseModel):
    """Routing metadata for message delivery."""
    model_config = ConfigDict(frozen=True)
    
    source: str = Field(description="Item ID that created/received this message")
    destination: str | None = Field(default=None, description="Target item ID for direct routing")
    route_id: str | None = Field(default=None, description="Current route being traversed")
    hop_count: int = Field(default=0, ge=0, description="Number of items traversed")
    
    def increment_hop(self) -> RoutingInfo:
        """Return new RoutingInfo with incremented hop count."""
        return RoutingInfo(
            source=self.source,
            destination=self.destination,
            route_id=self.route_id,
            hop_count=self.hop_count + 1,
        )


class GovernanceInfo(BaseModel):
    """Governance and audit metadata."""
    model_config = ConfigDict(frozen=True)
    
    audit_id: str | None = Field(default=None, description="External audit/trace identifier")
    tenant_id: str | None = Field(default=None, description="Multi-tenant isolation")
    sensitivity: Sensitivity = Field(default=Sensitivity.INTERNAL, description="Data classification")


class Envelope(BaseModel):
    """
    Message envelope containing routing, delivery, and governance metadata.
    
    The envelope is structured, indexable, and carries all operational metadata.
    It is separate from the payload to allow efficient routing without parsing content.
    """
    model_config = ConfigDict(frozen=True)
    
    # Identity
    message_id: UUID = Field(default_factory=uuid4, description="Unique message identifier")
    correlation_id: UUID = Field(default_factory=uuid4, description="Groups related messages")
    causation_id: UUID | None = Field(default=None, description="ID of causing message")
    
    # Temporal
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Message creation timestamp (UTC)"
    )
    expires_at: datetime | None = Field(default=None, description="Message expiration time")
    ttl: int | None = Field(default=None, ge=0, description="Time-to-live in seconds")
    
    # Classification
    message_type: str = Field(default="", description="Logical message type (e.g., ADT^A01)")
    priority: Priority = Field(default=Priority.NORMAL, description="Processing priority")
    tags: tuple[str, ...] = Field(default=(), description="Arbitrary tags for filtering")
    
    # Delivery
    retry_count: int = Field(default=0, ge=0, description="Current retry attempt")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_delay: int = Field(default=5, ge=0, description="Seconds between retries")
    delivery_mode: DeliveryMode = Field(
        default=DeliveryMode.AT_LEAST_ONCE,
        description="Delivery guarantee"
    )
    
    # Routing
    routing: RoutingInfo = Field(
        default_factory=lambda: RoutingInfo(source="unknown"),
        description="Routing metadata"
    )
    
    # Governance
    governance: GovernanceInfo = Field(
        default_factory=GovernanceInfo,
        description="Governance metadata"
    )
    
    # State
    state: MessageState = Field(default=MessageState.CREATED, description="Lifecycle state")
    
    def with_updates(self, **kwargs: Any) -> Envelope:
        """Return a new Envelope with updated fields."""
        data = self.model_dump(mode="python")
        data.update(kwargs)
        return Envelope.model_validate(data)
    
    def increment_retry(self) -> Envelope:
        """Return new Envelope with incremented retry count."""
        return self.with_updates(retry_count=self.retry_count + 1)
    
    def with_state(self, state: MessageState) -> Envelope:
        """Return new Envelope with updated state."""
        return self.with_updates(state=state)
    
    def is_expired(self) -> bool:
        """Check if message has expired."""
        now = datetime.now(timezone.utc)
        if self.expires_at is not None:
            return now >= self.expires_at
        if self.ttl is not None:
            expiry = self.created_at.replace(tzinfo=timezone.utc)
            from datetime import timedelta
            return now >= expiry + timedelta(seconds=self.ttl)
        return False
    
    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return self.retry_count < self.max_retries


@dataclass(frozen=True, slots=True)
class Payload:
    """
    Message payload containing the raw content.
    
    Key principle: The raw bytes are AUTHORITATIVE. Any parsed representation
    is transient and disposable. The raw content is preserved end-to-end.
    """
    raw: bytes
    content_type: str = "application/octet-stream"
    encoding: str = "utf-8"
    _properties: dict[str, Property] = field(default_factory=dict)
    
    @property
    def size(self) -> int:
        """Size of raw content in bytes."""
        return len(self.raw)
    
    @property
    def properties(self) -> dict[str, Property]:
        """Typed properties attached to this payload."""
        return self._properties.copy()
    
    @property
    def checksum(self) -> str:
        """SHA-256 checksum of raw content."""
        return hashlib.sha256(self.raw).hexdigest()
    
    def as_text(self) -> str:
        """Decode raw content as text using the specified encoding."""
        return self.raw.decode(self.encoding)
    
    def with_raw(self, raw: bytes) -> Payload:
        """Return new Payload with updated raw content."""
        return Payload(
            raw=raw,
            content_type=self.content_type,
            encoding=self.encoding,
            _properties=self._properties.copy(),
        )
    
    def with_property(self, key: str, prop: Property) -> Payload:
        """Return new Payload with added/updated property."""
        new_props = self._properties.copy()
        new_props[key] = prop
        return Payload(
            raw=self.raw,
            content_type=self.content_type,
            encoding=self.encoding,
            _properties=new_props,
        )
    
    def with_properties(self, properties: dict[str, Property]) -> Payload:
        """Return new Payload with updated properties."""
        new_props = self._properties.copy()
        new_props.update(properties)
        return Payload(
            raw=self.raw,
            content_type=self.content_type,
            encoding=self.encoding,
            _properties=new_props,
        )
    
    def get_property(self, key: str) -> Property | None:
        """Get a property by key."""
        return self._properties.get(key)
    
    def get_property_value(self, key: str, default: Any = None) -> Any:
        """Get a property value by key."""
        prop = self._properties.get(key)
        return prop.value if prop is not None else default


@dataclass(frozen=True, slots=True)
class Message:
    """
    The core message type in HIE.
    
    A message consists of:
    - Envelope: routing, delivery, governance metadata
    - Payload: raw content with typed properties
    
    Messages are IMMUTABLE. Operations that "modify" a message create new instances.
    """
    envelope: Envelope
    payload: Payload
    
    @classmethod
    def create(
        cls,
        raw: bytes,
        *,
        content_type: str = "application/octet-stream",
        encoding: str = "utf-8",
        source: str = "unknown",
        message_type: str = "",
        priority: Priority = Priority.NORMAL,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
        properties: dict[str, Property] | None = None,
    ) -> Message:
        """
        Factory method to create a new message.
        
        This is the preferred way to create messages as it ensures
        all required fields are properly initialized.
        """
        envelope = Envelope(
            correlation_id=correlation_id or uuid4(),
            causation_id=causation_id,
            message_type=message_type,
            priority=priority,
            routing=RoutingInfo(source=source),
        )
        payload = Payload(
            raw=raw,
            content_type=content_type,
            encoding=encoding,
            _properties=properties or {},
        )
        return cls(envelope=envelope, payload=payload)
    
    @property
    def id(self) -> UUID:
        """Shortcut to message_id."""
        return self.envelope.message_id
    
    @property
    def raw(self) -> bytes:
        """Shortcut to raw payload content."""
        return self.payload.raw
    
    def with_envelope(self, **kwargs: Any) -> Message:
        """Return new Message with updated envelope fields."""
        return Message(
            envelope=self.envelope.with_updates(**kwargs),
            payload=self.payload,
        )
    
    def with_payload(self, raw: bytes) -> Message:
        """Return new Message with updated raw payload."""
        return Message(
            envelope=self.envelope,
            payload=self.payload.with_raw(raw),
        )
    
    def with_property(self, key: str, prop: Property) -> Message:
        """Return new Message with added/updated property."""
        return Message(
            envelope=self.envelope,
            payload=self.payload.with_property(key, prop),
        )
    
    def with_state(self, state: MessageState) -> Message:
        """Return new Message with updated state."""
        return Message(
            envelope=self.envelope.with_state(state),
            payload=self.payload,
        )
    
    def derive(
        self,
        raw: bytes,
        *,
        content_type: str | None = None,
        message_type: str | None = None,
    ) -> Message:
        """
        Create a new message derived from this one.
        
        The new message:
        - Has a new message_id
        - Shares the same correlation_id
        - Has causation_id set to this message's id
        - Inherits routing and governance info
        """
        new_envelope = Envelope(
            correlation_id=self.envelope.correlation_id,
            causation_id=self.envelope.message_id,
            message_type=message_type or self.envelope.message_type,
            priority=self.envelope.priority,
            routing=self.envelope.routing,
            governance=self.envelope.governance,
        )
        new_payload = Payload(
            raw=raw,
            content_type=content_type or self.payload.content_type,
            encoding=self.payload.encoding,
        )
        return Message(envelope=new_envelope, payload=new_payload)
    
    def serialize(self, format: str = "msgpack") -> bytes:
        """Serialize message to bytes."""
        data = {
            "envelope": self.envelope.model_dump(mode="json"),
            "payload": {
                "raw": self.payload.raw.hex(),
                "content_type": self.payload.content_type,
                "encoding": self.payload.encoding,
                "properties": {
                    k: v.to_dict() for k, v in self.payload.properties.items()
                },
            },
        }
        if format == "msgpack":
            return msgpack.packb(data, use_bin_type=True)
        elif format == "json":
            import json
            return json.dumps(data).encode("utf-8")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def deserialize(cls, data: bytes, format: str = "msgpack") -> Message:
        """Deserialize message from bytes."""
        if format == "msgpack":
            obj = msgpack.unpackb(data, raw=False)
        elif format == "json":
            import json
            obj = json.loads(data.decode("utf-8"))
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        envelope = Envelope.model_validate(obj["envelope"])
        payload_data = obj["payload"]
        properties = {
            k: Property.from_dict(v) for k, v in payload_data.get("properties", {}).items()
        }
        payload = Payload(
            raw=bytes.fromhex(payload_data["raw"]),
            content_type=payload_data["content_type"],
            encoding=payload_data["encoding"],
            _properties=properties,
        )
        return cls(envelope=envelope, payload=payload)
    
    def __repr__(self) -> str:
        return (
            f"Message(id={self.id}, type={self.envelope.message_type!r}, "
            f"size={self.payload.size}, state={self.envelope.state.value})"
        )
