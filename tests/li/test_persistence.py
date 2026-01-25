"""
Tests for LI Persistence Module.

Tests WAL, MessageStore, and Queue functionality.
"""

import asyncio
import os
import tempfile
import pytest
import time

from hie.li.persistence import (
    WAL,
    WALEntry,
    WALState,
    WALConfig,
    SyncMode,
    MessageStore,
    MessageRecord,
    MessageQuery,
    MessageState,
    FileStorageBackend,
)


class TestWAL:
    """Tests for Write-Ahead Log."""
    
    @pytest.fixture
    def wal_dir(self):
        """Create a temporary directory for WAL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.mark.asyncio
    async def test_wal_start_stop(self, wal_dir):
        """Test WAL start and stop."""
        config = WALConfig(directory=wal_dir, sync_mode=SyncMode.NONE)
        wal = WAL(config)
        
        await wal.start()
        assert wal._running is True
        
        await wal.stop()
        assert wal._running is False
    
    @pytest.mark.asyncio
    async def test_wal_append(self, wal_dir):
        """Test appending entries to WAL."""
        config = WALConfig(directory=wal_dir, sync_mode=SyncMode.NONE)
        wal = WAL(config)
        await wal.start()
        
        try:
            entry = await wal.append(
                host_name="test-host",
                message_id="msg-001",
                payload=b"test payload",
                message_type="ADT_A01",
            )
            
            assert entry.id is not None
            assert entry.host_name == "test-host"
            assert entry.message_id == "msg-001"
            assert entry.state == WALState.PENDING
            assert entry.payload == b"test payload"
            assert wal.pending_count == 1
        finally:
            await wal.stop()
    
    @pytest.mark.asyncio
    async def test_wal_complete(self, wal_dir):
        """Test completing a WAL entry."""
        config = WALConfig(directory=wal_dir, sync_mode=SyncMode.NONE)
        wal = WAL(config)
        await wal.start()
        
        try:
            entry = await wal.append("test-host", "msg-001", b"payload")
            assert wal.pending_count == 1
            
            await wal.complete(entry.id)
            assert wal.pending_count == 0
        finally:
            await wal.stop()
    
    @pytest.mark.asyncio
    async def test_wal_fail_retry(self, wal_dir):
        """Test failing and retrying a WAL entry."""
        config = WALConfig(
            directory=wal_dir,
            sync_mode=SyncMode.NONE,
            max_retries=3,
        )
        wal = WAL(config)
        await wal.start()
        
        try:
            entry = await wal.append("test-host", "msg-001", b"payload")
            
            # First failure - should retry
            should_retry = await wal.fail(entry.id, "Error 1")
            assert should_retry is True
            assert wal.pending_count == 1
            
            # Second failure - should retry
            should_retry = await wal.fail(entry.id, "Error 2")
            assert should_retry is True
            
            # Third failure - max retries exceeded
            should_retry = await wal.fail(entry.id, "Error 3")
            assert should_retry is False
            
            # Should be in failed state
            failed = await wal.get_failed()
            assert len(failed) == 1
        finally:
            await wal.stop()
    
    @pytest.mark.asyncio
    async def test_wal_recovery(self, wal_dir):
        """Test WAL recovery after restart."""
        config = WALConfig(directory=wal_dir, sync_mode=SyncMode.FSYNC)
        
        # First session - create entries
        wal1 = WAL(config)
        await wal1.start()
        
        entry1 = await wal1.append("test-host", "msg-001", b"payload1")
        entry2 = await wal1.append("test-host", "msg-002", b"payload2")
        await wal1.complete(entry1.id)  # Complete one
        
        await wal1.stop()
        
        # Second session - should recover pending entry
        wal2 = WAL(config)
        await wal2.start()
        
        try:
            pending = await wal2.get_pending()
            assert len(pending) == 1
            assert pending[0].message_id == "msg-002"
        finally:
            await wal2.stop()
    
    def test_wal_entry_serialization(self):
        """Test WAL entry serialization."""
        entry = WALEntry(
            id="test-id",
            sequence=1,
            timestamp=time.time(),
            state=WALState.PENDING,
            host_name="test-host",
            message_id="msg-001",
            message_type="ADT_A01",
            payload=b"test payload",
            metadata={"key": "value"},
        )
        
        data = entry.to_bytes()
        restored = WALEntry.from_bytes(data)
        
        assert restored.id == entry.id
        assert restored.host_name == entry.host_name
        assert restored.payload == entry.payload
        assert restored.metadata == entry.metadata


class TestMessageStore:
    """Tests for MessageStore."""
    
    @pytest.fixture
    def store_dir(self):
        """Create a temporary directory for store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.mark.asyncio
    async def test_store_start_stop(self, store_dir):
        """Test store start and stop."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        
        await store.start()
        await store.stop()
    
    @pytest.mark.asyncio
    async def test_store_message(self, store_dir):
        """Test storing a message."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        await store.start()
        
        try:
            record = await store.store(
                host_name="test-host",
                message_id="msg-001",
                payload=b"test payload",
                message_type="ADT_A01",
                source="external",
                correlation_id="corr-001",
            )
            
            assert record.id is not None
            assert record.message_id == "msg-001"
            assert record.state == MessageState.RECEIVED
            assert record.payload == b"test payload"
        finally:
            await store.stop()
    
    @pytest.mark.asyncio
    async def test_store_get(self, store_dir):
        """Test retrieving a stored message."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        await store.start()
        
        try:
            record = await store.store("test-host", "msg-001", b"payload")
            
            retrieved = await store.get(record.id)
            assert retrieved is not None
            assert retrieved.message_id == "msg-001"
        finally:
            await store.stop()
    
    @pytest.mark.asyncio
    async def test_store_update_state(self, store_dir):
        """Test updating message state."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        await store.start()
        
        try:
            record = await store.store("test-host", "msg-001", b"payload")
            
            await store.mark_processing(record.id)
            updated = await store.get(record.id)
            assert updated.state == MessageState.PROCESSING
            
            await store.mark_completed(record.id)
            updated = await store.get(record.id)
            assert updated.state == MessageState.COMPLETED
        finally:
            await store.stop()
    
    @pytest.mark.asyncio
    async def test_store_query(self, store_dir):
        """Test querying messages."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        await store.start()
        
        try:
            # Store multiple messages
            await store.store("host-1", "msg-001", b"payload1", message_type="ADT")
            await store.store("host-1", "msg-002", b"payload2", message_type="ORU")
            await store.store("host-2", "msg-003", b"payload3", message_type="ADT")
            
            # Query by host
            results = await store.query(MessageQuery(host_name="host-1"))
            assert len(results) == 2
            
            # Query by message type
            results = await store.query(MessageQuery(message_type="ADT"))
            assert len(results) == 2
        finally:
            await store.stop()
    
    @pytest.mark.asyncio
    async def test_store_get_failed(self, store_dir):
        """Test getting failed messages."""
        backend = FileStorageBackend(store_dir)
        store = MessageStore(backend)
        await store.start()
        
        try:
            record = await store.store("test-host", "msg-001", b"payload")
            await store.mark_failed(record.id, "Test error")
            
            failed = await store.get_failed()
            assert len(failed) == 1
            assert failed[0].error == "Test error"
        finally:
            await store.stop()
    
    def test_message_record_serialization(self):
        """Test MessageRecord serialization."""
        from datetime import datetime, timezone
        
        record = MessageRecord(
            id="test-id",
            message_id="msg-001",
            host_name="test-host",
            message_type="ADT_A01",
            state=MessageState.RECEIVED,
            payload=b"test payload",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata={"key": "value"},
        )
        
        data = record.to_dict()
        restored = MessageRecord.from_dict(data)
        
        assert restored.id == record.id
        assert restored.message_id == record.message_id
        assert restored.payload == record.payload


class TestMetrics:
    """Tests for Prometheus metrics."""
    
    def test_counter(self):
        """Test Counter metric."""
        from hie.li.metrics import Counter
        
        counter = Counter("test_counter", "Test counter", ["host"])
        
        counter.inc(host="host1")
        counter.inc(2, host="host1")
        counter.inc(host="host2")
        
        assert counter.get(host="host1") == 3
        assert counter.get(host="host2") == 1
    
    def test_gauge(self):
        """Test Gauge metric."""
        from hie.li.metrics import Gauge
        
        gauge = Gauge("test_gauge", "Test gauge", ["host"])
        
        gauge.set(10, host="host1")
        assert gauge.get(host="host1") == 10
        
        gauge.inc(5, host="host1")
        assert gauge.get(host="host1") == 15
        
        gauge.dec(3, host="host1")
        assert gauge.get(host="host1") == 12
    
    def test_histogram(self):
        """Test Histogram metric."""
        from hie.li.metrics import Histogram
        
        histogram = Histogram(
            "test_histogram",
            "Test histogram",
            ["host"],
            buckets=(0.1, 0.5, 1.0, float("inf")),
        )
        
        histogram.observe(0.05, host="host1")
        histogram.observe(0.3, host="host1")
        histogram.observe(0.8, host="host1")
        histogram.observe(2.0, host="host1")
        
        values = histogram.collect()
        assert len(values) > 0
    
    def test_metrics_registry(self):
        """Test MetricsRegistry."""
        from hie.li.metrics import MetricsRegistry
        
        registry = MetricsRegistry()
        
        # Default metrics should be registered
        assert registry.counter("messages_received_total") is not None
        assert registry.gauge("host_status") is not None
        assert registry.histogram("message_processing_seconds") is not None
    
    def test_metrics_export(self):
        """Test metrics export in Prometheus format."""
        from hie.li.metrics import MetricsRegistry
        
        registry = MetricsRegistry()
        
        # Record some metrics
        counter = registry.counter("messages_received_total")
        counter.inc(host="test-host", message_type="ADT")
        
        output = registry.export()
        
        assert "li_messages_received_total" in output
        assert "# HELP" in output
        assert "# TYPE" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
