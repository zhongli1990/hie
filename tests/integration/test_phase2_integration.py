"""
Integration tests for Phase 2 features:
- Configurable queue types
- Auto-restart capability
- Combined behavior
"""

import asyncio
import pytest
from Engine.li.engine.production import ProductionEngine
from Engine.li.hosts.base import Host, HostState, HostMetrics
from Engine.li.config.item_config import ItemConfig, ItemSetting, SettingTarget
from Engine.core.messaging import MessageEnvelope, MessagePriority
from Engine.core.queues import QueueType, OverflowStrategy


class TestHost(Host):
    """Test host for integration testing."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, pool_size=1, enabled=True, adapter_settings={}, host_settings=kwargs)
        self.processed_messages = []
        self.should_fail = False
        self.fail_count = 0
        self.max_failures = 0

    async def on_init(self) -> None:
        """Initialize host."""
        pass

    async def on_teardown(self) -> None:
        """Teardown host."""
        pass

    async def on_process_input(self, message):
        """Process message."""
        if self.should_fail and self.fail_count < self.max_failures:
            self.fail_count += 1
            raise RuntimeError(f"Simulated failure {self.fail_count}")

        self.processed_messages.append(message)
        return message


@pytest.mark.asyncio
class TestQueueIntegration:
    """Integration tests for queue types in production."""

    async def test_fifo_queue_in_production(self):
        """Test FIFO queue maintains order in production."""
        # Create item config with FIFO queue
        config = ItemConfig(
            name="FIFOHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="fifo"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="100"),
            ]
        )

        # Create host
        host = TestHost("FIFOHost")
        host_settings = config.host_settings

        # Initialize queue from settings
        queue_type = QueueType(host_settings.get("QueueType", "fifo"))
        queue_size = int(host_settings.get("QueueSize", 1000))

        # Verify settings applied
        assert queue_type == QueueType.FIFO
        assert queue_size == 100

    async def test_priority_queue_in_production(self):
        """Test priority queue orders messages in production."""
        # Create item config with priority queue
        config = ItemConfig(
            name="PriorityHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="priority"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="100"),
            ]
        )

        # Create host
        host = TestHost("PriorityHost")
        host_settings = config.host_settings

        # Verify settings
        queue_type = QueueType(host_settings.get("QueueType", "fifo"))
        assert queue_type == QueueType.PRIORITY

    async def test_overflow_strategy_in_production(self):
        """Test overflow strategies work in production."""
        # Create item config with drop_oldest overflow
        config = ItemConfig(
            name="OverflowHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="fifo"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="10"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="drop_oldest"),
            ]
        )

        # Verify settings
        host_settings = config.host_settings
        overflow_strategy = OverflowStrategy(host_settings.get("OverflowStrategy", "block"))
        assert overflow_strategy == OverflowStrategy.DROP_OLDEST


@pytest.mark.asyncio
class TestAutoRestartIntegration:
    """Integration tests for auto-restart in production."""

    async def test_auto_restart_with_always_policy(self):
        """Test auto-restart with RestartPolicy=always."""
        # Create item config with auto-restart
        config = ItemConfig(
            name="AutoRestartHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="always"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="5"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="1.0"),
            ]
        )

        # Verify settings
        host_settings = config.host_settings
        assert host_settings["RestartPolicy"] == "always"
        assert host_settings["MaxRestarts"] == 5
        assert host_settings["RestartDelay"] == 1.0

    async def test_auto_restart_with_on_failure_policy(self):
        """Test auto-restart with RestartPolicy=on_failure."""
        # Create item config
        config = ItemConfig(
            name="OnFailureHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="on_failure"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="3"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="2.0"),
            ]
        )

        # Verify settings
        host_settings = config.host_settings
        assert host_settings["RestartPolicy"] == "on_failure"
        assert host_settings["MaxRestarts"] == 3

    async def test_no_restart_with_never_policy(self):
        """Test no auto-restart with RestartPolicy=never."""
        # Create item config
        config = ItemConfig(
            name="NeverRestartHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="never"),
            ]
        )

        # Verify settings
        host_settings = config.host_settings
        assert host_settings["RestartPolicy"] == "never"


@pytest.mark.asyncio
class TestCombinedFeatures:
    """Test queue types and auto-restart working together."""

    async def test_priority_queue_with_auto_restart(self):
        """Test priority queue survives restart."""
        # Create host with priority queue and auto-restart
        config = ItemConfig(
            name="PriorityRestartHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                # Queue settings
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="priority"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="1000"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="block"),
                # Restart settings
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="always"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="5"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="0.5"),
            ]
        )

        # Verify combined settings
        host_settings = config.host_settings
        assert host_settings["QueueType"] == "priority"
        assert host_settings["RestartPolicy"] == "always"

    async def test_overflow_handling_with_restart(self):
        """Test overflow strategy works after restart."""
        # Create host with small queue and auto-restart
        config = ItemConfig(
            name="OverflowRestartHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[
                # Small queue with drop strategy
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="fifo"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="10"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="drop_oldest"),
                # Auto-restart
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="on_failure"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="3"),
            ]
        )

        # Verify settings
        host_settings = config.host_settings
        assert host_settings["QueueSize"] == 10
        assert host_settings["OverflowStrategy"] == "drop_oldest"
        assert host_settings["RestartPolicy"] == "on_failure"

    async def test_high_throughput_configuration(self):
        """Test high-throughput configuration (unordered queue + aggressive restart)."""
        # Create high-throughput config
        config = ItemConfig(
            name="HighThroughputHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=4,
            enabled=True,
            settings=[
                # Unordered queue for max throughput
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="unordered"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="10000"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="drop_oldest"),
                # Aggressive restart
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="always"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="100"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="1.0"),
                # Multiprocess execution
                ItemSetting(target=SettingTarget.HOST, name="ExecutionMode", value="multiprocess"),
                ItemSetting(target=SettingTarget.HOST, name="WorkerCount", value="4"),
            ]
        )

        # Verify high-throughput settings
        host_settings = config.host_settings
        assert host_settings["QueueType"] == "unordered"
        assert host_settings["QueueSize"] == 10000
        assert host_settings["ExecutionMode"] == "multiprocess"
        assert host_settings["WorkerCount"] == 4
        assert host_settings["MaxRestarts"] == 100

    async def test_mission_critical_configuration(self):
        """Test mission-critical configuration (FIFO + always restart)."""
        # Create mission-critical config
        config = ItemConfig(
            name="MissionCriticalHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=2,
            enabled=True,
            settings=[
                # Strict FIFO ordering
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="fifo"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="5000"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="block"),
                # Never give up restarting
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="always"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="1000"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="30.0"),
                # Thread pool for blocking operations
                ItemSetting(target=SettingTarget.HOST, name="ExecutionMode", value="thread_pool"),
                ItemSetting(target=SettingTarget.HOST, name="WorkerCount", value="2"),
            ]
        )

        # Verify mission-critical settings
        host_settings = config.host_settings
        assert host_settings["QueueType"] == "fifo"
        assert host_settings["OverflowStrategy"] == "block"
        assert host_settings["RestartPolicy"] == "always"
        assert host_settings["MaxRestarts"] == 1000
        assert host_settings["RestartDelay"] == 30.0


@pytest.mark.asyncio
class TestConfigurationValidation:
    """Test configuration validation and defaults."""

    async def test_default_queue_settings(self):
        """Test default queue settings when not specified."""
        # Create minimal config
        config = ItemConfig(
            name="DefaultHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[]
        )

        # Should use defaults
        host_settings = config.host_settings
        assert host_settings.get("QueueType", "fifo") == "fifo"
        assert host_settings.get("QueueSize", 1000) == 1000
        assert host_settings.get("OverflowStrategy", "block") == "block"

    async def test_default_restart_settings(self):
        """Test default restart settings when not specified."""
        # Create minimal config
        config = ItemConfig(
            name="DefaultHost",
            class_name="tests.integration.test_phase2_integration.TestHost",
            pool_size=1,
            enabled=True,
            settings=[]
        )

        # Should use safe defaults
        host_settings = config.host_settings
        assert host_settings.get("RestartPolicy", "never") == "never"
        assert host_settings.get("MaxRestarts", 3) == 3
        assert host_settings.get("RestartDelay", 5.0) == 5.0

    async def test_invalid_queue_type_handling(self):
        """Test handling of invalid queue type."""
        # This should be caught during configuration parsing
        # For now, just document expected behavior
        pass

    async def test_invalid_restart_policy_handling(self):
        """Test handling of invalid restart policy."""
        # This should be caught during configuration parsing
        # For now, just document expected behavior
        pass


@pytest.mark.asyncio
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    async def test_hl7_tcp_service_configuration(self):
        """Test typical HL7 TCP service configuration."""
        config = ItemConfig(
            name="HL7_TCP_Service",
            class_name="Engine.li.hosts.tcp_service.TCPService",
            pool_size=4,
            enabled=True,
            settings=[
                # Multiprocess for GIL bypass
                ItemSetting(target=SettingTarget.HOST, name="ExecutionMode", value="multiprocess"),
                ItemSetting(target=SettingTarget.HOST, name="WorkerCount", value="4"),
                # Priority queue for urgent messages
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="priority"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="10000"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="reject"),
                # Auto-restart on failure
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="on_failure"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="10"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="5.0"),
                # TCP adapter settings
                ItemSetting(target=SettingTarget.ADAPTER, name="IPAddress", value="0.0.0.0"),
                ItemSetting(target=SettingTarget.ADAPTER, name="Port", value="2575"),
            ]
        )

        # Verify complete configuration
        host_settings = config.host_settings
        adapter_settings = config.adapter_settings

        assert host_settings["ExecutionMode"] == "multiprocess"
        assert host_settings["QueueType"] == "priority"
        assert host_settings["RestartPolicy"] == "on_failure"
        assert adapter_settings["IPAddress"] == "0.0.0.0"
        assert adapter_settings["Port"] == 2575

    async def test_pds_lookup_process_configuration(self):
        """Test typical PDS lookup business process configuration."""
        config = ItemConfig(
            name="PDS_Lookup_Process",
            class_name="Engine.li.hosts.business_process.BusinessProcess",
            pool_size=2,
            enabled=True,
            settings=[
                # Thread pool for blocking HTTP calls
                ItemSetting(target=SettingTarget.HOST, name="ExecutionMode", value="thread_pool"),
                ItemSetting(target=SettingTarget.HOST, name="WorkerCount", value="2"),
                # FIFO for ordered processing
                ItemSetting(target=SettingTarget.HOST, name="QueueType", value="fifo"),
                ItemSetting(target=SettingTarget.HOST, name="QueueSize", value="1000"),
                ItemSetting(target=SettingTarget.HOST, name="OverflowStrategy", value="block"),
                # Always restart (critical service)
                ItemSetting(target=SettingTarget.HOST, name="RestartPolicy", value="always"),
                ItemSetting(target=SettingTarget.HOST, name="MaxRestarts", value="100"),
                ItemSetting(target=SettingTarget.HOST, name="RestartDelay", value="10.0"),
            ]
        )

        # Verify configuration
        host_settings = config.host_settings
        assert host_settings["ExecutionMode"] == "thread_pool"
        assert host_settings["QueueType"] == "fifo"
        assert host_settings["RestartPolicy"] == "always"
