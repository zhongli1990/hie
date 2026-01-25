"""
Tests for LI Production Engine.

Tests the main orchestrator that manages production lifecycle.
"""

import asyncio
import tempfile
import pytest

from hie.li.engine import ProductionEngine, ProductionState, EngineConfig
from hie.li.config import IRISXMLLoader, ProductionConfig, ItemConfig, SettingTarget
from hie.li.hosts import HostState


# Sample production XML for testing
SAMPLE_PRODUCTION_XML = """<?xml version="1.0"?>
<Production Name="Test.Production" LogGeneralTraceEvents="false">
  <Description>Test Production</Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="HL7.In.TCP" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
    <Setting Target="Adapter" Name="Port">19100</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
    <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
  </Item>
  <Item Name="HL7.Router" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true">
    <Setting Target="Host" Name="BusinessRuleName">Test.Router.Rules</Setting>
  </Item>
  <Item Name="HL7.Out.TCP" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false">
    <Setting Target="Adapter" Name="IPAddress">localhost</Setting>
    <Setting Target="Adapter" Name="Port">19101</Setting>
  </Item>
</Production>
"""


class TestProductionEngine:
    """Tests for ProductionEngine."""
    
    @pytest.fixture
    def config_file(self):
        """Create a temporary config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(SAMPLE_PRODUCTION_XML)
            return f.name
    
    @pytest.fixture
    def engine_config(self):
        """Create engine config with disabled infrastructure."""
        return EngineConfig(
            wal_enabled=False,
            store_enabled=False,
            metrics_enabled=False,
            health_enabled=False,
            startup_delay=0,
        )
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = ProductionEngine()
        
        assert engine.state == ProductionState.CREATED
        assert engine.production_name is None
        assert len(engine.hosts) == 0
    
    def test_engine_with_config(self):
        """Test engine with custom config."""
        config = EngineConfig(
            wal_enabled=True,
            wal_directory="/tmp/wal",
            shutdown_timeout=60.0,
        )
        
        engine = ProductionEngine(config)
        
        assert engine._config.wal_enabled is True
        assert engine._config.shutdown_timeout == 60.0
    
    @pytest.mark.asyncio
    async def test_load_production(self, config_file, engine_config):
        """Test loading production from file."""
        engine = ProductionEngine(engine_config)
        
        await engine.load(config_file)
        
        assert engine.production_name == "Test.Production"
        assert len(engine.hosts) == 3
        assert len(engine.services) == 1
        assert len(engine.processes) == 1
        assert len(engine.operations) == 1
    
    @pytest.mark.asyncio
    async def test_load_from_config(self, engine_config):
        """Test loading from ProductionConfig object."""
        loader = IRISXMLLoader()
        production_config = loader.load_from_string(SAMPLE_PRODUCTION_XML)
        
        engine = ProductionEngine(engine_config)
        await engine.load_from_config(production_config)
        
        assert engine.production_name == "Test.Production"
        assert len(engine.hosts) == 3
    
    @pytest.mark.asyncio
    async def test_get_host(self, config_file, engine_config):
        """Test getting a host by name."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        
        host = engine.get_host("HL7.In.TCP")
        assert host is not None
        assert host.name == "HL7.In.TCP"
        
        host = engine.get_host("NonExistent")
        assert host is None
    
    @pytest.mark.asyncio
    async def test_start_production(self, config_file, engine_config):
        """Test starting production."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        
        await engine.start()
        
        assert engine.state == ProductionState.RUNNING
        
        # Check enabled hosts are running
        service = engine.get_host("HL7.In.TCP")
        assert service.state == HostState.RUNNING
        
        router = engine.get_host("HL7.Router")
        assert router.state == HostState.RUNNING
        
        # Check disabled host is not running
        operation = engine.get_host("HL7.Out.TCP")
        assert operation.state != HostState.RUNNING
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_stop_production(self, config_file, engine_config):
        """Test stopping production."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        await engine.start()
        
        await engine.stop()
        
        assert engine.state == ProductionState.STOPPED
        
        # All hosts should be stopped
        for host in engine.hosts.values():
            assert host.state in (HostState.STOPPED, HostState.CREATED)
    
    @pytest.mark.asyncio
    async def test_get_status(self, config_file, engine_config):
        """Test getting production status."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        await engine.start()
        
        status = engine.get_status()
        
        assert status["name"] == "Test.Production"
        assert status["state"] == "running"
        assert status["items"]["total"] == 3
        assert status["items"]["services"] == 1
        assert "HL7.In.TCP" in status["hosts"]
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_restart_host(self, config_file, engine_config):
        """Test restarting a specific host."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        await engine.start()
        
        host = engine.get_host("HL7.In.TCP")
        original_started_at = host.metrics.started_at
        
        await engine.restart_host("HL7.In.TCP")
        
        # Host should be running again
        assert host.state == HostState.RUNNING
        # Started time should be different
        assert host.metrics.started_at != original_started_at
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_enable_disable_host(self, config_file, engine_config):
        """Test enabling and disabling hosts."""
        engine = ProductionEngine(engine_config)
        await engine.load(config_file)
        await engine.start()
        
        # Disable a running host
        await engine.disable_host("HL7.In.TCP")
        host = engine.get_host("HL7.In.TCP")
        assert host.enabled is False
        assert host.state != HostState.RUNNING
        
        # Enable it again
        await engine.enable_host("HL7.In.TCP")
        assert host.enabled is True
        assert host.state == HostState.RUNNING
        
        await engine.stop()


class TestProductionEngineWithInfrastructure:
    """Tests for ProductionEngine with infrastructure enabled."""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        import tempfile
        wal_dir = tempfile.mkdtemp()
        store_dir = tempfile.mkdtemp()
        return wal_dir, store_dir
    
    @pytest.mark.asyncio
    async def test_engine_with_wal(self, temp_dirs):
        """Test engine with WAL enabled."""
        wal_dir, store_dir = temp_dirs
        
        config = EngineConfig(
            wal_enabled=True,
            wal_directory=wal_dir,
            store_enabled=False,
            metrics_enabled=False,
            health_enabled=False,
            startup_delay=0,
        )
        
        engine = ProductionEngine(config)
        
        # Create a simple production config
        production_config = ProductionConfig(name="Test.WAL")
        
        await engine.load_from_config(production_config)
        await engine.start()
        
        assert engine._wal is not None
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_with_store(self, temp_dirs):
        """Test engine with message store enabled."""
        wal_dir, store_dir = temp_dirs
        
        config = EngineConfig(
            wal_enabled=False,
            store_enabled=True,
            store_directory=store_dir,
            metrics_enabled=False,
            health_enabled=False,
            startup_delay=0,
        )
        
        engine = ProductionEngine(config)
        
        production_config = ProductionConfig(name="Test.Store")
        
        await engine.load_from_config(production_config)
        await engine.start()
        
        assert engine._store is not None
        
        await engine.stop()


class TestProductionEngineEdgeCases:
    """Edge case tests for ProductionEngine."""
    
    @pytest.mark.asyncio
    async def test_load_twice_fails(self):
        """Test that loading twice fails."""
        config = EngineConfig(
            wal_enabled=False,
            store_enabled=False,
            metrics_enabled=False,
            health_enabled=False,
        )
        engine = ProductionEngine(config)
        
        production_config = ProductionConfig(name="Test")
        await engine.load_from_config(production_config)
        await engine.start()
        
        with pytest.raises(RuntimeError):
            await engine.load_from_config(production_config)
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_start_without_load(self):
        """Test that starting without loading works (empty production)."""
        config = EngineConfig(
            wal_enabled=False,
            store_enabled=False,
            metrics_enabled=False,
            health_enabled=False,
        )
        engine = ProductionEngine(config)
        
        # Load empty production
        production_config = ProductionConfig(name="Empty")
        await engine.load_from_config(production_config)
        
        await engine.start()
        
        assert engine.state == ProductionState.RUNNING
        assert len(engine.hosts) == 0
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stopping when not running is a no-op."""
        config = EngineConfig(
            wal_enabled=False,
            store_enabled=False,
            metrics_enabled=False,
            health_enabled=False,
        )
        engine = ProductionEngine(config)
        
        # Stop without starting
        await engine.stop()
        
        # Should still be in created state
        assert engine.state == ProductionState.CREATED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
