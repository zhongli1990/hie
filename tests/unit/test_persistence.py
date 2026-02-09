"""
Unit tests for HIE Persistence layer.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from Engine.core.message import Message, MessageState, Priority
from Engine.persistence.memory import InMemoryMessageStore, InMemoryStateStore
from Engine.persistence.base import MessageQuery


class TestInMemoryMessageStore:
    """Tests for InMemoryMessageStore."""
    
    @pytest.fixture
    def store(self):
        return InMemoryMessageStore(max_size=100)
    
    @pytest.fixture
    def sample_message(self):
        return Message.create(
            raw=b"MSH|^~\\&|TEST|TEST|TEST|TEST|20240101120000||ADT^A01|1|P|2.5",
            content_type="x-application/hl7-v2+er7",
            source="test_source",
            message_type="ADT^A01",
        )
    
    @pytest.mark.asyncio
    async def test_store_and_get(self, store, sample_message):
        await store.connect()
        
        await store.store(sample_message)
        
        retrieved = await store.get(sample_message.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_message.id
        assert retrieved.raw == sample_message.raw
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        await store.connect()
        
        result = await store.get(uuid4())
        
        assert result is None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_store_batch(self, store):
        await store.connect()
        
        messages = [
            Message.create(raw=f"msg{i}".encode(), source="test")
            for i in range(5)
        ]
        
        await store.store_batch(messages)
        
        for msg in messages:
            retrieved = await store.get(msg.id)
            assert retrieved is not None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_batch(self, store):
        await store.connect()
        
        messages = [
            Message.create(raw=f"msg{i}".encode(), source="test")
            for i in range(3)
        ]
        
        for msg in messages:
            await store.store(msg)
        
        ids = [msg.id for msg in messages]
        retrieved = await store.get_batch(ids)
        
        assert len(retrieved) == 3
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_query_by_source(self, store):
        await store.connect()
        
        msg1 = Message.create(raw=b"msg1", source="source_a")
        msg2 = Message.create(raw=b"msg2", source="source_b")
        msg3 = Message.create(raw=b"msg3", source="source_a")
        
        await store.store(msg1)
        await store.store(msg2)
        await store.store(msg3)
        
        query = MessageQuery(source="source_a")
        results = await store.query(query)
        
        assert len(results) == 2
        assert all(m.envelope.routing.source == "source_a" for m in results)
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_query_by_message_type(self, store):
        await store.connect()
        
        msg1 = Message.create(raw=b"msg1", source="test", message_type="ADT^A01")
        msg2 = Message.create(raw=b"msg2", source="test", message_type="ORU^R01")
        msg3 = Message.create(raw=b"msg3", source="test", message_type="ADT^A01")
        
        await store.store(msg1)
        await store.store(msg2)
        await store.store(msg3)
        
        query = MessageQuery(message_type="ADT^A01")
        results = await store.query(query)
        
        assert len(results) == 2
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_query_by_state(self, store):
        await store.connect()
        
        msg1 = Message.create(raw=b"msg1", source="test")
        msg2 = Message.create(raw=b"msg2", source="test").with_state(MessageState.PROCESSING)
        
        await store.store(msg1)
        await store.store(msg2)
        
        query = MessageQuery(state=MessageState.CREATED)
        results = await store.query(query)
        
        assert len(results) == 1
        assert results[0].envelope.state == MessageState.CREATED
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_query_with_limit_offset(self, store):
        await store.connect()
        
        messages = [
            Message.create(raw=f"msg{i}".encode(), source="test")
            for i in range(10)
        ]
        
        for msg in messages:
            await store.store(msg)
        
        query = MessageQuery(limit=3, offset=2)
        results = await store.query(query)
        
        assert len(results) == 3
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_count(self, store):
        await store.connect()
        
        for i in range(5):
            msg = Message.create(raw=f"msg{i}".encode(), source="test")
            await store.store(msg)
        
        query = MessageQuery()
        count = await store.count(query)
        
        assert count == 5
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_update_state(self, store, sample_message):
        await store.connect()
        
        await store.store(sample_message)
        
        result = await store.update_state(sample_message.id, MessageState.DELIVERED)
        
        assert result is True
        
        retrieved = await store.get(sample_message.id)
        assert retrieved.envelope.state == MessageState.DELIVERED
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_update_state_nonexistent(self, store):
        await store.connect()
        
        result = await store.update_state(uuid4(), MessageState.DELIVERED)
        
        assert result is False
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete(self, store, sample_message):
        await store.connect()
        
        await store.store(sample_message)
        
        result = await store.delete(sample_message.id)
        
        assert result is True
        assert await store.get(sample_message.id) is None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        await store.connect()
        
        result = await store.delete(uuid4())
        
        assert result is False
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete_batch(self, store):
        await store.connect()
        
        messages = [
            Message.create(raw=f"msg{i}".encode(), source="test")
            for i in range(5)
        ]
        
        for msg in messages:
            await store.store(msg)
        
        ids_to_delete = [messages[0].id, messages[2].id, messages[4].id]
        count = await store.delete_batch(ids_to_delete)
        
        assert count == 3
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_purge_expired(self, store):
        await store.connect()
        
        # Create expired message
        expired_msg = Message.create(raw=b"expired", source="test")
        expired_msg = expired_msg.with_envelope(ttl=0)  # Expires immediately
        
        # Create non-expired message
        valid_msg = Message.create(raw=b"valid", source="test")
        
        await store.store(expired_msg)
        await store.store(valid_msg)
        
        # Small delay to ensure expiration
        await asyncio.sleep(0.1)
        
        count = await store.purge_expired()
        
        assert count == 1
        assert await store.get(expired_msg.id) is None
        assert await store.get(valid_msg.id) is not None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        store = InMemoryMessageStore(max_size=3)
        await store.connect()
        
        messages = [
            Message.create(raw=f"msg{i}".encode(), source="test")
            for i in range(5)
        ]
        
        for msg in messages:
            await store.store(msg)
        
        # First two should be evicted
        assert await store.get(messages[0].id) is None
        assert await store.get(messages[1].id) is None
        
        # Last three should remain
        assert await store.get(messages[2].id) is not None
        assert await store.get(messages[3].id) is not None
        assert await store.get(messages[4].id) is not None
        
        await store.disconnect()


class TestInMemoryStateStore:
    """Tests for InMemoryStateStore."""
    
    @pytest.fixture
    def store(self):
        return InMemoryStateStore()
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, store):
        await store.connect()
        
        await store.set("key1", {"value": 42})
        
        result = await store.get("key1")
        
        assert result == {"value": 42}
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        await store.connect()
        
        result = await store.get("nonexistent")
        
        assert result is None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_set_with_ttl(self, store):
        await store.connect()
        
        await store.set("expiring", "value", ttl=1)
        
        # Should exist immediately
        assert await store.get("expiring") == "value"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be gone
        assert await store.get("expiring") is None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete(self, store):
        await store.connect()
        
        await store.set("key1", "value1")
        
        result = await store.delete("key1")
        
        assert result is True
        assert await store.get("key1") is None
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store):
        await store.connect()
        
        result = await store.delete("nonexistent")
        
        assert result is False
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_exists(self, store):
        await store.connect()
        
        await store.set("key1", "value1")
        
        assert await store.exists("key1") is True
        assert await store.exists("nonexistent") is False
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_keys_pattern(self, store):
        await store.connect()
        
        await store.set("user:1", "data1")
        await store.set("user:2", "data2")
        await store.set("item:1", "data3")
        
        user_keys = await store.keys("user:*")
        
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_increment(self, store):
        await store.connect()
        
        # Increment non-existent key
        result = await store.increment("counter")
        assert result == 1
        
        # Increment existing key
        result = await store.increment("counter", 5)
        assert result == 6
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_increment_non_numeric(self, store):
        await store.connect()
        
        await store.set("string_key", "not a number")
        
        with pytest.raises(TypeError):
            await store.increment("string_key")
        
        await store.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_or_set(self, store):
        await store.connect()
        
        # First call sets the default
        result = await store.get_or_set("new_key", "default_value")
        assert result == "default_value"
        
        # Second call returns existing value
        await store.set("new_key", "updated_value")
        result = await store.get_or_set("new_key", "different_default")
        assert result == "updated_value"
        
        await store.disconnect()
