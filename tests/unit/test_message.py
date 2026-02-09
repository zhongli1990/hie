"""
Unit tests for HIE Message model.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from Engine.core.message import (
    Message,
    Envelope,
    Payload,
    Property,
    PropertyType,
    Priority,
    Sensitivity,
    DeliveryMode,
    MessageState,
    RoutingInfo,
    GovernanceInfo,
)


class TestProperty:
    """Tests for Property class."""
    
    def test_create_string_property(self):
        prop = Property(value="test", type=PropertyType.STRING)
        assert prop.value == "test"
        assert prop.type == PropertyType.STRING
    
    def test_create_int_property(self):
        prop = Property(value=42, type=PropertyType.INT)
        assert prop.value == 42
        assert prop.type == PropertyType.INT
    
    def test_property_max_size_enforced(self):
        with pytest.raises(ValueError, match="exceeds max_size"):
            Property(value="too long", type=PropertyType.STRING, max_size=3)
    
    def test_property_serialization(self):
        prop = Property(value="test", type=PropertyType.STRING)
        data = prop.to_dict()
        
        assert data["value"] == "test"
        assert data["type"] == "string"
        
        restored = Property.from_dict(data)
        assert restored.value == prop.value
        assert restored.type == prop.type
    
    def test_datetime_property_serialization(self):
        now = datetime.now(timezone.utc)
        prop = Property(value=now, type=PropertyType.DATETIME)
        
        data = prop.to_dict()
        restored = Property.from_dict(data)
        
        assert restored.value == now


class TestEnvelope:
    """Tests for Envelope class."""
    
    def test_create_default_envelope(self):
        env = Envelope()
        
        assert env.message_id is not None
        assert env.correlation_id is not None
        assert env.priority == Priority.NORMAL
        assert env.state == MessageState.CREATED
        assert env.delivery_mode == DeliveryMode.AT_LEAST_ONCE
    
    def test_envelope_with_custom_values(self):
        env = Envelope(
            message_type="ADT^A01",
            priority=Priority.URGENT,
            tags=("adt", "admission"),
        )
        
        assert env.message_type == "ADT^A01"
        assert env.priority == Priority.URGENT
        assert env.tags == ("adt", "admission")
    
    def test_envelope_immutability(self):
        env = Envelope()
        
        with pytest.raises(Exception):  # Pydantic frozen model
            env.priority = Priority.HIGH
    
    def test_envelope_with_updates(self):
        env = Envelope(priority=Priority.NORMAL)
        updated = env.with_updates(priority=Priority.HIGH)
        
        assert env.priority == Priority.NORMAL  # Original unchanged
        assert updated.priority == Priority.HIGH
        assert env.message_id == updated.message_id  # Same ID
    
    def test_envelope_increment_retry(self):
        env = Envelope(retry_count=0)
        updated = env.increment_retry()
        
        assert env.retry_count == 0
        assert updated.retry_count == 1
    
    def test_envelope_expiration_by_expires_at(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        env = Envelope(expires_at=past)
        
        assert env.is_expired() is True
    
    def test_envelope_expiration_by_ttl(self):
        env = Envelope(ttl=0)  # Expires immediately
        
        assert env.is_expired() is True
    
    def test_envelope_not_expired(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        env = Envelope(expires_at=future)
        
        assert env.is_expired() is False
    
    def test_envelope_can_retry(self):
        env = Envelope(retry_count=0, max_retries=3)
        assert env.can_retry() is True
        
        env2 = Envelope(retry_count=3, max_retries=3)
        assert env2.can_retry() is False


class TestPayload:
    """Tests for Payload class."""
    
    def test_create_payload(self):
        raw = b"MSH|^~\\&|TEST|TEST|TEST|TEST|20240101120000||ADT^A01|1|P|2.5"
        payload = Payload(raw=raw, content_type="x-application/hl7-v2+er7")
        
        assert payload.raw == raw
        assert payload.content_type == "x-application/hl7-v2+er7"
        assert payload.size == len(raw)
    
    def test_payload_as_text(self):
        raw = b"Hello, World!"
        payload = Payload(raw=raw, encoding="utf-8")
        
        assert payload.as_text() == "Hello, World!"
    
    def test_payload_checksum(self):
        payload = Payload(raw=b"test data")
        checksum = payload.checksum
        
        assert len(checksum) == 64  # SHA-256 hex
        assert checksum == payload.checksum  # Consistent
    
    def test_payload_with_raw(self):
        payload = Payload(raw=b"original")
        updated = payload.with_raw(b"modified")
        
        assert payload.raw == b"original"
        assert updated.raw == b"modified"
    
    def test_payload_with_property(self):
        payload = Payload(raw=b"test")
        prop = Property(value="NHS123", type=PropertyType.STRING)
        
        updated = payload.with_property("patient_id", prop)
        
        assert payload.get_property("patient_id") is None
        assert updated.get_property("patient_id") == prop
        assert updated.get_property_value("patient_id") == "NHS123"


class TestMessage:
    """Tests for Message class."""
    
    def test_create_message(self):
        msg = Message.create(
            raw=b"test content",
            content_type="text/plain",
            source="test_source",
            message_type="TEST",
        )
        
        assert msg.raw == b"test content"
        assert msg.payload.content_type == "text/plain"
        assert msg.envelope.routing.source == "test_source"
        assert msg.envelope.message_type == "TEST"
    
    def test_message_immutability(self):
        msg = Message.create(raw=b"test")
        
        # Message is a frozen dataclass
        with pytest.raises(Exception):
            msg.envelope = Envelope()
    
    def test_message_with_envelope(self):
        msg = Message.create(raw=b"test", priority=Priority.NORMAL)
        updated = msg.with_envelope(priority=Priority.URGENT)
        
        assert msg.envelope.priority == Priority.NORMAL
        assert updated.envelope.priority == Priority.URGENT
    
    def test_message_with_payload(self):
        msg = Message.create(raw=b"original")
        updated = msg.with_payload(b"modified")
        
        assert msg.raw == b"original"
        assert updated.raw == b"modified"
    
    def test_message_with_state(self):
        msg = Message.create(raw=b"test")
        updated = msg.with_state(MessageState.PROCESSING)
        
        assert msg.envelope.state == MessageState.CREATED
        assert updated.envelope.state == MessageState.PROCESSING
    
    def test_message_derive(self):
        original = Message.create(
            raw=b"original",
            source="source1",
            message_type="TYPE1",
        )
        
        derived = original.derive(
            raw=b"derived",
            message_type="TYPE2",
        )
        
        # New message ID
        assert derived.id != original.id
        
        # Same correlation ID
        assert derived.envelope.correlation_id == original.envelope.correlation_id
        
        # Causation chain
        assert derived.envelope.causation_id == original.id
        
        # Updated content
        assert derived.raw == b"derived"
        assert derived.envelope.message_type == "TYPE2"
    
    def test_message_serialization_msgpack(self):
        msg = Message.create(
            raw=b"test content",
            content_type="text/plain",
            source="test",
            message_type="TEST",
            priority=Priority.HIGH,
        )
        
        # Add a property
        msg = msg.with_property(
            "test_prop",
            Property(value="test_value", type=PropertyType.STRING)
        )
        
        # Serialize
        data = msg.serialize(format="msgpack")
        assert isinstance(data, bytes)
        
        # Deserialize
        restored = Message.deserialize(data, format="msgpack")
        
        assert restored.id == msg.id
        assert restored.raw == msg.raw
        assert restored.envelope.message_type == msg.envelope.message_type
        assert restored.payload.get_property_value("test_prop") == "test_value"
    
    def test_message_serialization_json(self):
        msg = Message.create(raw=b"test", source="test")
        
        data = msg.serialize(format="json")
        assert isinstance(data, bytes)
        
        restored = Message.deserialize(data, format="json")
        assert restored.id == msg.id
    
    def test_message_repr(self):
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        repr_str = repr(msg)
        
        assert "Message" in repr_str
        assert "ADT^A01" in repr_str


class TestRoutingInfo:
    """Tests for RoutingInfo class."""
    
    def test_create_routing_info(self):
        routing = RoutingInfo(source="item1")
        
        assert routing.source == "item1"
        assert routing.destination is None
        assert routing.hop_count == 0
    
    def test_increment_hop(self):
        routing = RoutingInfo(source="item1", hop_count=0)
        updated = routing.increment_hop()
        
        assert routing.hop_count == 0
        assert updated.hop_count == 1


class TestGovernanceInfo:
    """Tests for GovernanceInfo class."""
    
    def test_default_governance(self):
        gov = GovernanceInfo()
        
        assert gov.sensitivity == Sensitivity.INTERNAL
        assert gov.audit_id is None
        assert gov.tenant_id is None
    
    def test_custom_governance(self):
        gov = GovernanceInfo(
            sensitivity=Sensitivity.RESTRICTED,
            audit_id="AUDIT-001",
            tenant_id="TRUST-XYZ",
        )
        
        assert gov.sensitivity == Sensitivity.RESTRICTED
        assert gov.audit_id == "AUDIT-001"
        assert gov.tenant_id == "TRUST-XYZ"
