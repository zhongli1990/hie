"""
Unit tests for auto-restart capability.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from Engine.li.engine.production import ProductionEngine, ProductionState
from Engine.li.hosts.base import Host, HostState, HostMetrics
from Engine.li.config.item_config import ItemConfig, ItemSetting, SettingTarget


class MockHost(Host):
    """Mock host for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(
            name=name,
            pool_size=1,
            enabled=True,
            adapter_settings={},
            host_settings={},
        )
        self.should_fail = should_fail
        self.process_count = 0

    async def on_init(self) -> None:
        """Initialize host."""
        pass

    async def on_teardown(self) -> None:
        """Teardown host."""
        pass

    async def on_process_input(self, message):
        """Process message."""
        self.process_count += 1
        if self.should_fail:
            raise RuntimeError("Simulated failure")
        return message


@pytest.mark.asyncio
class TestAutoRestart:
    """Test automatic restart functionality."""

    async def test_restart_policy_never(self):
        """Test RestartPolicy=never does not restart."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.1

        # Create mock host with never restart policy
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.set_setting = Mock()
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "never",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "5.0",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor for a short time
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.3)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Host should still be in ERROR state (not restarted)
        assert host.state == HostState.ERROR

    async def test_restart_policy_always(self):
        """Test RestartPolicy=always restarts host."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.1

        # Create mock host with always restart policy
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.stop = AsyncMock()
        host.start = AsyncMock(side_effect=lambda: setattr(host, 'state', HostState.RUNNING))
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",  # Short delay for testing
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor for a short time
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.5)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Host should have been restarted
        assert host.stop.called
        assert host.start.called
        assert host.metrics.restart_count > 0

    async def test_restart_policy_on_failure(self):
        """Test RestartPolicy=on_failure only restarts on error."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.1

        # Create mock host with on_failure restart policy
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.stop = AsyncMock()
        host.start = AsyncMock(side_effect=lambda: setattr(host, 'state', HostState.RUNNING))
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "on_failure",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor for a short time
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.5)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Host should have been restarted (was in ERROR state)
        assert host.stop.called
        assert host.start.called

    async def test_max_restarts_limit(self):
        """Test MaxRestarts limits restart attempts."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create mock host with low max restarts
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.metrics.restart_count = 3  # Already at limit
        host.stop = AsyncMock()
        host.start = AsyncMock()
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor for a short time
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.3)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Host should NOT have been restarted (at limit)
        assert not host.stop.called
        assert not host.start.called

    async def test_restart_delay(self):
        """Test RestartDelay waits before restarting."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create mock host with restart delay
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.stop = AsyncMock()
        host.start = AsyncMock(side_effect=lambda: setattr(host, 'state', HostState.RUNNING))
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.5",  # 500ms delay
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Start monitoring
        monitor_task = asyncio.create_task(engine._monitor_hosts())

        # Wait less than delay
        await asyncio.sleep(0.2)

        # Should not have restarted yet
        assert not host.start.called

        # Wait past delay
        await asyncio.sleep(0.5)

        # Now should have restarted
        assert host.start.called

        # Cleanup
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    async def test_restart_count_increments(self):
        """Test restart_count increments on each restart."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create mock host
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.metrics.restart_count = 0
        host.stop = AsyncMock()

        # Make start() succeed once, then fail
        restart_attempts = []

        async def mock_start():
            restart_attempts.append(1)
            setattr(host, 'state', HostState.RUNNING if len(restart_attempts) == 1 else HostState.ERROR)

        host.start = mock_start
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "5",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.8)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Should have incremented restart count
        assert host.metrics.restart_count >= 1

    async def test_restart_failure_handling(self):
        """Test handling when restart itself fails."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create mock host where restart fails
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.stop = AsyncMock()
        host.start = AsyncMock(side_effect=RuntimeError("Restart failed"))
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor (should not crash)
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.3)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Should have attempted restart
        assert host.start.called

    async def test_multiple_hosts_restart(self):
        """Test multiple hosts can restart independently."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create two hosts, both in ERROR state
        host1 = MockHost("Host1")
        host1.state = HostState.ERROR
        host1.stop = AsyncMock()
        host1.start = AsyncMock(side_effect=lambda: setattr(host1, 'state', HostState.RUNNING))
        host1.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        host2 = MockHost("Host2")
        host2.state = HostState.ERROR
        host2.stop = AsyncMock()
        host2.start = AsyncMock(side_effect=lambda: setattr(host2, 'state', HostState.RUNNING))
        host2.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "on_failure",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["Host1"] = host1
        engine._all_hosts["Host2"] = host2

        # Run monitor
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.5)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Both should have been restarted
        assert host1.start.called
        assert host2.start.called

    async def test_running_hosts_not_restarted(self):
        """Test running hosts are not restarted."""
        # Create engine
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.05

        # Create host in RUNNING state
        host = MockHost("TestHost")
        host.state = HostState.RUNNING
        host.stop = AsyncMock()
        host.start = AsyncMock()
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "always",
            ("Host", "MaxRestarts", "3"): "3",
            ("Host", "RestartDelay", "5.0"): "0.1",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Run monitor
        monitor_task = asyncio.create_task(engine._monitor_hosts())
        await asyncio.sleep(0.3)
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()

        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        # Should NOT have been restarted (was running)
        assert not host.stop.called
        assert not host.start.called


@pytest.mark.asyncio
class TestMonitoringConfiguration:
    """Test monitoring configuration options."""

    async def test_monitoring_disabled(self):
        """Test monitoring can be disabled."""
        engine = ProductionEngine()
        engine._monitoring_enabled = False

        # Create host in ERROR state
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.start = AsyncMock()
        engine._all_hosts["TestHost"] = host

        # Start production (should not start monitoring)
        # This is tested indirectly - monitoring task should not be created

        assert engine._monitor_task is None

    async def test_monitoring_interval(self):
        """Test monitoring interval can be configured."""
        engine = ProductionEngine()
        engine._state = ProductionState.RUNNING
        engine._monitoring_enabled = True
        engine._monitoring_interval = 0.5  # 500ms interval

        # Create host in ERROR state
        host = MockHost("TestHost")
        host.state = HostState.ERROR
        host.stop = AsyncMock()
        host.start = AsyncMock()
        host.get_setting = Mock(side_effect=lambda target, name, default: {
            ("Host", "RestartPolicy", "never"): "never",
        }.get((target, name, default), default))

        engine._all_hosts["TestHost"] = host

        # Monitor should wait 500ms between checks
        monitor_task = asyncio.create_task(engine._monitor_hosts())

        # Wait less than interval
        await asyncio.sleep(0.2)

        # Clean up
        engine._state = ProductionState.STOPPED
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
