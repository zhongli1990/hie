"""
Tests for LI Host Hierarchy.

Tests the base Host classes and their lifecycle management.
"""

import asyncio
import pytest

from Engine.li.hosts import (
    Host,
    HostState,
    BusinessService,
    BusinessProcess,
    BusinessOperation,
)
from Engine.li.adapters import (
    Adapter,
    AdapterState,
    InboundAdapter,
    OutboundAdapter,
)
from Engine.li.config import ItemConfig, SettingTarget


# =============================================================================
# Test Fixtures
# =============================================================================

class MockInboundAdapter(InboundAdapter):
    """Mock inbound adapter for testing."""
    
    def __init__(self, host, settings=None):
        super().__init__(host, settings)
        self.listen_called = False
        self.data_received = []
    
    async def listen(self) -> None:
        self.listen_called = True
    
    async def simulate_receive(self, data: bytes) -> None:
        """Simulate receiving data."""
        self.data_received.append(data)
        await self.on_data_received(data)


class MockOutboundAdapter(OutboundAdapter):
    """Mock outbound adapter for testing."""
    
    def __init__(self, host, settings=None):
        super().__init__(host, settings)
        self.sent_messages = []
    
    async def send(self, message) -> bytes:
        self.sent_messages.append(message)
        await self.on_send(b"ACK")
        return b"MSH|^~\\&|ACK|..."


class MockService(BusinessService):
    """Mock service implementation for testing."""
    adapter_class = MockInboundAdapter
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_messages = []
    
    async def _process_message(self, message):
        self.received_messages.append(message)
        return message


class MockProcess(BusinessProcess):
    """Mock process implementation for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_messages = []
    
    async def on_message(self, message):
        self.processed_messages.append(message)
        # Transform: add prefix
        return f"PROCESSED:{message}"


class MockOperation(BusinessOperation):
    """Mock operation implementation for testing."""
    adapter_class = MockOutboundAdapter
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent_messages = []
    
    async def on_message(self, message):
        self.sent_messages.append(message)
        return await super().on_message(message)


# =============================================================================
# Host Base Tests
# =============================================================================

class TestHostBase:
    """Tests for Host base class."""
    
    def test_host_initialization(self):
        """Test host initialization with parameters."""
        host = MockService(
            name="test-service",
            pool_size=2,
            enabled=True,
            adapter_settings={"Port": 8080},
            host_settings={"TargetConfigNames": "Router1,Router2"},
        )
        
        assert host.name == "test-service"
        assert host.pool_size == 2
        assert host.enabled is True
        assert host.state == HostState.CREATED
        assert host.adapter_settings["Port"] == 8080
        assert host.host_settings["TargetConfigNames"] == "Router1,Router2"
    
    def test_host_initialization_from_config(self):
        """Test host initialization from ItemConfig."""
        config = ItemConfig(
            name="from-config",
            class_name="li.hosts.hl7.HL7TCPService",
            pool_size=3,
            enabled=True,
        )
        config.set_setting(SettingTarget.ADAPTER, "Port", 9000)
        config.set_setting(SettingTarget.HOST, "MessageSchemaCategory", "PKB")
        
        host = MockService(name=config.name, config=config)
        
        assert host.name == "from-config"
        assert host.pool_size == 3
        assert host.get_setting("Adapter", "Port") == 9000
        assert host.get_setting("Host", "MessageSchemaCategory") == "PKB"
    
    def test_get_setting(self):
        """Test get_setting method."""
        host = MockService(
            name="test",
            adapter_settings={"Port": 8080, "Host": "localhost"},
            host_settings={"Timeout": 30, "ArchiveIO": 1},
        )
        
        assert host.get_setting("Adapter", "Port") == 8080
        assert host.get_setting("Host", "Timeout") == 30
        assert host.get_setting("Host", "Missing", "default") == "default"
        assert host.get_setting("Invalid", "Key") is None
    
    @pytest.mark.asyncio
    async def test_host_lifecycle(self):
        """Test host start/stop lifecycle."""
        host = MockService(name="lifecycle-test")
        
        assert host.state == HostState.CREATED
        
        # Start
        await host.start()
        assert host.state == HostState.RUNNING
        assert host.metrics.started_at is not None
        
        # Stop
        await host.stop()
        assert host.state == HostState.STOPPED
        assert host.metrics.stopped_at is not None
    
    @pytest.mark.asyncio
    async def test_host_pause_resume(self):
        """Test host pause/resume."""
        host = MockService(name="pause-test")
        await host.start()
        
        assert host.state == HostState.RUNNING
        
        await host.pause()
        assert host.state == HostState.PAUSED
        
        await host.resume()
        assert host.state == HostState.RUNNING
        
        await host.stop()
    
    @pytest.mark.asyncio
    async def test_host_message_processing(self):
        """Test message submission and processing."""
        host = MockService(name="processing-test", pool_size=1)
        await host.start()
        
        # Submit message
        result = await host.submit("test-message")
        assert result is True
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        assert host.metrics.messages_received == 1
        assert len(host.received_messages) == 1
        
        await host.stop()
    
    @pytest.mark.asyncio
    async def test_host_cannot_start_when_running(self):
        """Test that host cannot be started when already running."""
        host = MockService(name="double-start-test")
        await host.start()
        
        with pytest.raises(RuntimeError, match="Cannot start host"):
            await host.start()
        
        await host.stop()


# =============================================================================
# BusinessService Tests
# =============================================================================

class TestBusinessService:
    """Tests for BusinessService class."""
    
    def test_target_config_names(self):
        """Test target_config_names property."""
        host = MockService(
            name="service-test",
            host_settings={"TargetConfigNames": "Router1, Router2, Operation1"},
        )
        
        targets = host.target_config_names
        assert len(targets) == 3
        assert "Router1" in targets
        assert "Router2" in targets
        assert "Operation1" in targets
    
    def test_target_config_names_empty(self):
        """Test target_config_names when empty."""
        host = MockService(name="service-test")
        assert host.target_config_names == []
    
    @pytest.mark.asyncio
    async def test_service_with_adapter(self):
        """Test service creates and starts adapter."""
        host = MockService(
            name="adapter-test",
            adapter_settings={"Port": 8080},
        )
        
        await host.start()
        
        assert host._adapter is not None
        assert isinstance(host._adapter, MockInboundAdapter)
        assert host._adapter.state == AdapterState.RUNNING
        
        await host.stop()
        assert host._adapter.state == AdapterState.STOPPED


# =============================================================================
# BusinessProcess Tests
# =============================================================================

class TestBusinessProcess:
    """Tests for BusinessProcess class."""
    
    def test_business_rule_name(self):
        """Test business_rule_name property."""
        host = MockProcess(
            name="process-test",
            host_settings={"BusinessRuleName": "Test.Router.Rules"},
        )
        
        assert host.business_rule_name == "Test.Router.Rules"
    
    def test_business_rule_name_none(self):
        """Test business_rule_name when not set."""
        host = MockProcess(name="process-test")
        assert host.business_rule_name is None
    
    @pytest.mark.asyncio
    async def test_process_transforms_message(self):
        """Test process transforms messages."""
        host = MockProcess(name="transform-test", pool_size=1)
        await host.start()
        
        await host.submit("original")
        await asyncio.sleep(0.1)
        
        assert len(host.processed_messages) == 1
        assert host.processed_messages[0] == "original"
        
        await host.stop()


# =============================================================================
# BusinessOperation Tests
# =============================================================================

class TestBusinessOperation:
    """Tests for BusinessOperation class."""
    
    def test_reply_code_actions(self):
        """Test reply_code_actions property."""
        host = MockOperation(
            name="operation-test",
            host_settings={"ReplyCodeActions": ":?R=F,:?E=S,:*=S"},
        )
        
        assert host.reply_code_actions == ":?R=F,:?E=S,:*=S"
    
    def test_archive_io(self):
        """Test archive_io property."""
        host1 = MockOperation(
            name="archive-test-1",
            host_settings={"ArchiveIO": 1},
        )
        assert host1.archive_io is True
        
        host2 = MockOperation(
            name="archive-test-2",
            host_settings={"ArchiveIO": 0},
        )
        assert host2.archive_io is False
        
        host3 = MockOperation(name="archive-test-3")
        assert host3.archive_io is False
    
    @pytest.mark.asyncio
    async def test_operation_sends_via_adapter(self):
        """Test operation sends messages via adapter."""
        host = MockOperation(
            name="send-test",
            adapter_settings={"IPAddress": "localhost", "Port": 2575},
        )
        await host.start()
        
        await host.submit("test-message")
        await asyncio.sleep(0.1)
        
        assert len(host._adapter.sent_messages) == 1
        assert host.metrics.messages_sent == 1
        
        await host.stop()


# =============================================================================
# Adapter Tests
# =============================================================================

class TestAdapters:
    """Tests for Adapter classes."""
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test adapter start/stop lifecycle."""
        host = MockService(name="adapter-lifecycle")
        adapter = MockInboundAdapter(host, {"Port": 8080})
        
        assert adapter.state == AdapterState.CREATED
        
        await adapter.start()
        assert adapter.state == AdapterState.RUNNING
        assert adapter.metrics.started_at is not None
        
        await adapter.stop()
        assert adapter.state == AdapterState.STOPPED
    
    def test_adapter_get_setting(self):
        """Test adapter get_setting method."""
        host = MockService(name="adapter-settings")
        adapter = MockInboundAdapter(host, {"Port": 8080, "Host": "0.0.0.0"})
        
        assert adapter.get_setting("Port") == 8080
        assert adapter.get_setting("Host") == "0.0.0.0"
        assert adapter.get_setting("Missing", "default") == "default"
    
    @pytest.mark.asyncio
    async def test_inbound_adapter_metrics(self):
        """Test inbound adapter updates metrics on receive."""
        host = MockService(name="inbound-metrics")
        await host.start()
        
        adapter = host._adapter
        initial_bytes = adapter.metrics.bytes_received
        
        await adapter.simulate_receive(b"test data")
        
        assert adapter.metrics.bytes_received == initial_bytes + 9
        assert adapter.metrics.last_activity_at is not None
        
        await host.stop()
    
    @pytest.mark.asyncio
    async def test_outbound_adapter_metrics(self):
        """Test outbound adapter updates metrics on send."""
        host = MockOperation(name="outbound-metrics")
        await host.start()
        
        adapter = host._adapter
        await adapter.send("test")
        
        assert adapter.metrics.bytes_sent == 3  # "ACK"
        assert adapter.metrics.last_activity_at is not None
        
        await host.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
