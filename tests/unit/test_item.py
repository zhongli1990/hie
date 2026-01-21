"""
Unit tests for HIE Item model.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from hie.core.item import (
    Item,
    ItemConfig,
    ItemState,
    ItemType,
    ExecutionMode,
    Receiver,
    Processor,
    Sender,
    ItemMetrics,
)
from hie.core.message import Message


class ConcreteItem(Item):
    """Concrete implementation for testing."""
    
    def __init__(self, config: ItemConfig):
        super().__init__(config)
        self.processed_messages = []
    
    async def _process(self, message: Message) -> Message | None:
        self.processed_messages.append(message)
        return message


class ConcreteReceiver(Receiver):
    """Concrete receiver for testing."""
    
    def __init__(self, config: ItemConfig):
        super().__init__(config)
        self.receive_called = False
    
    async def _receive_loop(self) -> None:
        self.receive_called = True
        while not self._shutdown_event.is_set():
            await asyncio.sleep(0.1)


class ConcreteSender(Sender):
    """Concrete sender for testing."""
    
    def __init__(self, config: ItemConfig):
        super().__init__(config)
        self.sent_messages = []
    
    async def _send(self, message: Message) -> bool:
        self.sent_messages.append(message)
        return True


class TestItemConfig:
    """Tests for ItemConfig."""
    
    def test_default_config(self):
        config = ItemConfig(id="test", item_type=ItemType.PROCESSOR)
        
        assert config.id == "test"
        assert config.item_type == ItemType.PROCESSOR
        assert config.enabled is True
        assert config.execution_mode == ExecutionMode.ASYNC
        assert config.concurrency == 1
        assert config.queue_size == 1000
    
    def test_custom_config(self):
        config = ItemConfig(
            id="custom",
            name="Custom Item",
            item_type=ItemType.RECEIVER,
            execution_mode=ExecutionMode.MULTI_PROCESS,
            concurrency=4,
            queue_size=5000,
            timeout_seconds=60.0,
        )
        
        assert config.name == "Custom Item"
        assert config.execution_mode == ExecutionMode.MULTI_PROCESS
        assert config.concurrency == 4
        assert config.queue_size == 5000
        assert config.timeout_seconds == 60.0


class TestItemMetrics:
    """Tests for ItemMetrics."""
    
    def test_record_success(self):
        metrics = ItemMetrics()
        
        metrics.record_success(100.0, 1024)
        
        assert metrics.messages_processed == 1
        assert metrics.bytes_sent == 1024
        assert metrics.processing_time_avg_ms == 100.0
        assert metrics.consecutive_errors == 0
    
    def test_record_failure(self):
        metrics = ItemMetrics()
        
        metrics.record_failure("Test error")
        
        assert metrics.messages_failed == 1
        assert metrics.consecutive_errors == 1
        assert metrics.last_error_message == "Test error"
    
    def test_record_received(self):
        metrics = ItemMetrics()
        
        metrics.record_received(2048)
        
        assert metrics.messages_received == 1
        assert metrics.bytes_received == 2048
    
    def test_consecutive_errors_reset_on_success(self):
        metrics = ItemMetrics()
        
        metrics.record_failure("Error 1")
        metrics.record_failure("Error 2")
        assert metrics.consecutive_errors == 2
        
        metrics.record_success(50.0)
        assert metrics.consecutive_errors == 0


class TestItem:
    """Tests for Item base class."""
    
    @pytest.fixture
    def item_config(self):
        return ItemConfig(
            id="test_item",
            name="Test Item",
            item_type=ItemType.PROCESSOR,
            queue_size=100,
        )
    
    @pytest.fixture
    def item(self, item_config):
        return ConcreteItem(item_config)
    
    def test_item_properties(self, item, item_config):
        assert item.id == "test_item"
        assert item.name == "Test Item"
        assert item.item_type == ItemType.PROCESSOR
        assert item.state == ItemState.CREATED
        assert item.config == item_config
    
    def test_item_initial_state(self, item):
        assert item.state == ItemState.CREATED
        assert item.is_running is False
        assert item.is_healthy is False  # Not running
    
    @pytest.mark.asyncio
    async def test_item_start_stop(self, item):
        await item.start()
        assert item.state == ItemState.RUNNING
        assert item.is_running is True
        
        await item.stop()
        assert item.state == ItemState.STOPPED
        assert item.is_running is False
    
    @pytest.mark.asyncio
    async def test_item_pause_resume(self, item):
        await item.start()
        
        await item.pause()
        assert item.state == ItemState.PAUSED
        
        await item.resume()
        assert item.state == ItemState.RUNNING
        
        await item.stop()
    
    @pytest.mark.asyncio
    async def test_item_submit_message(self, item):
        await item.start()
        
        msg = Message.create(raw=b"test", source="test")
        await item.submit(msg)
        
        # Give worker time to process
        await asyncio.sleep(0.2)
        
        assert len(item.processed_messages) == 1
        assert item.processed_messages[0].id == msg.id
        
        await item.stop()
    
    @pytest.mark.asyncio
    async def test_item_submit_nowait(self, item):
        await item.start()
        
        msg = Message.create(raw=b"test", source="test")
        result = item.submit_nowait(msg)
        
        assert result is True
        
        await item.stop()
    
    @pytest.mark.asyncio
    async def test_item_submit_nowait_queue_full(self, item_config):
        item_config.queue_size = 1
        item = ConcreteItem(item_config)
        
        await item.start()
        await item.pause()  # Pause to prevent processing
        
        msg1 = Message.create(raw=b"test1", source="test")
        msg2 = Message.create(raw=b"test2", source="test")
        
        result1 = item.submit_nowait(msg1)
        result2 = item.submit_nowait(msg2)
        
        assert result1 is True
        assert result2 is False  # Queue full
        
        await item.stop()
    
    @pytest.mark.asyncio
    async def test_item_cannot_start_when_running(self, item):
        await item.start()
        
        with pytest.raises(RuntimeError, match="Cannot start"):
            await item.start()
        
        await item.stop()
    
    @pytest.mark.asyncio
    async def test_item_cannot_submit_when_stopped(self, item):
        msg = Message.create(raw=b"test", source="test")
        
        with pytest.raises(RuntimeError, match="Cannot submit"):
            await item.submit(msg)
    
    def test_item_health_check(self, item):
        health = item.health_check()
        
        assert health["id"] == "test_item"
        assert health["name"] == "Test Item"
        assert health["type"] == "processor"
        assert health["state"] == "created"
        assert "metrics" in health
    
    @pytest.mark.asyncio
    async def test_item_message_handler(self, item):
        received_messages = []
        
        async def handler(msg: Message) -> Message | None:
            received_messages.append(msg)
            return msg
        
        item.set_message_handler(handler)
        
        await item.start()
        
        msg = Message.create(raw=b"test", source="test")
        await item.submit(msg)
        
        await asyncio.sleep(0.2)
        
        assert len(received_messages) == 1
        
        await item.stop()


class TestReceiver:
    """Tests for Receiver base class."""
    
    @pytest.fixture
    def receiver_config(self):
        return ItemConfig(id="test_receiver", item_type=ItemType.RECEIVER)
    
    @pytest.fixture
    def receiver(self, receiver_config):
        return ConcreteReceiver(receiver_config)
    
    def test_receiver_type(self, receiver):
        assert receiver.item_type == ItemType.RECEIVER
    
    @pytest.mark.asyncio
    async def test_receiver_starts_receive_loop(self, receiver):
        await receiver.start()
        
        await asyncio.sleep(0.2)
        
        assert receiver.receive_called is True
        
        await receiver.stop()


class TestSender:
    """Tests for Sender base class."""
    
    @pytest.fixture
    def sender_config(self):
        return ItemConfig(id="test_sender", item_type=ItemType.SENDER)
    
    @pytest.fixture
    def sender(self, sender_config):
        return ConcreteSender(sender_config)
    
    def test_sender_type(self, sender):
        assert sender.item_type == ItemType.SENDER
    
    @pytest.mark.asyncio
    async def test_sender_sends_message(self, sender):
        await sender.start()
        
        msg = Message.create(raw=b"test", source="test")
        await sender.submit(msg)
        
        await asyncio.sleep(0.2)
        
        assert len(sender.sent_messages) == 1
        
        await sender.stop()
