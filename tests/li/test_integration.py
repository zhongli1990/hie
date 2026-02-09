"""
Integration Tests for LI Engine.

Tests end-to-end message flow through the LI Engine components.
These tests use a mock MLLP echo server to simulate external systems.
"""

import asyncio
import pytest

from Engine.li.hosts import (
    HL7TCPService,
    HL7TCPOperation,
    HL7RoutingEngine,
    HL7Message,
    RoutingRule,
    RuleAction,
    create_message_type_rule,
)
from Engine.li.adapters import (
    mllp_wrap,
    mllp_unwrap,
    MLLP_START_BLOCK,
    MLLP_END_BLOCK,
    MLLP_CARRIAGE_RETURN,
)
from Engine.li.schemas.hl7 import HL7Schema
from Engine.li.config import IRISXMLLoader, ProductionConfig


# Sample HL7 messages
SAMPLE_ADT_A01 = b"MSH|^~\\&|SENDING|FAC|RECEIVING|FAC|20240115120000||ADT^A01|MSG001|P|2.4\rEVN|A01|20240115\rPID|1||12345||DOE^JOHN\rPV1|1|I|ICU\r"
SAMPLE_ORU_R01 = b"MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115||ORU^R01|MSG002|P|2.4\rPID|1||67890||SMITH^JANE\rOBR|1||FIL001|CBC\rOBX|1|NM|WBC||7.5|10*3/uL\r"


class MLLPEchoServer:
    """
    Simple MLLP echo server for testing.
    
    Receives HL7 messages and returns ACK responses.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.port = port
        self.server = None
        self.received_messages = []
        self.ack_code = "AA"  # Can be changed to test error scenarios
        self.schema = HL7Schema(name="2.4")
    
    async def start(self):
        """Start the echo server."""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        # Get actual port if 0 was specified
        self.port = self.server.sockets[0].getsockname()[1]
        return self
    
    async def stop(self):
        """Stop the echo server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
    
    async def _handle_client(self, reader, writer):
        """Handle a client connection."""
        try:
            while True:
                # Read MLLP message
                data = b""
                while True:
                    byte = await reader.read(1)
                    if not byte:
                        return
                    data += byte
                    if data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
                        break
                
                if data:
                    # Unwrap and store
                    message = mllp_unwrap(data)
                    self.received_messages.append(message)
                    
                    # Generate ACK
                    parsed = self.schema.parse(message)
                    ack = self.schema.create_ack(parsed, self.ack_code)
                    
                    # Send ACK
                    writer.write(mllp_wrap(ack))
                    await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, *args):
        await self.stop()


class TestMLLPEchoServer:
    """Tests for the MLLP echo server itself."""
    
    @pytest.mark.asyncio
    async def test_echo_server_basic(self):
        """Test echo server receives and ACKs messages."""
        async with MLLPEchoServer() as server:
            # Connect and send
            reader, writer = await asyncio.open_connection(server.host, server.port)
            
            writer.write(mllp_wrap(SAMPLE_ADT_A01))
            await writer.drain()
            
            # Read ACK
            ack_data = b""
            while True:
                byte = await reader.read(1)
                if not byte:
                    break
                ack_data += byte
                if ack_data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
                    break
            
            ack = mllp_unwrap(ack_data)
            
            assert len(server.received_messages) == 1
            assert server.received_messages[0] == SAMPLE_ADT_A01
            assert b"MSA|AA" in ack
            
            writer.close()
            await writer.wait_closed()


class TestHL7TCPServiceIntegration:
    """Integration tests for HL7TCPService."""
    
    @pytest.mark.asyncio
    async def test_service_receives_message(self):
        """Test service receives and processes HL7 message."""
        # Start service
        service = HL7TCPService(
            name="test-service",
            adapter_settings={"Port": 0},  # Let OS assign port
            host_settings={"MessageSchemaCategory": "2.4"},
        )
        
        await service.start()
        
        # Get actual port
        port = service._adapter._server.sockets[0].getsockname()[1]
        
        try:
            # Connect and send message
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            
            writer.write(mllp_wrap(SAMPLE_ADT_A01))
            await writer.drain()
            
            # Read ACK
            ack_data = b""
            while True:
                byte = await asyncio.wait_for(reader.read(1), timeout=5.0)
                if not byte:
                    break
                ack_data += byte
                if ack_data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
                    break
            
            ack = mllp_unwrap(ack_data)
            
            # Verify ACK
            assert b"MSA|AA" in ack
            assert b"MSG001" in ack  # Original message control ID
            
            writer.close()
            await writer.wait_closed()
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Verify metrics
            assert service.metrics.messages_received >= 1
        
        finally:
            await service.stop()


class TestHL7TCPOperationIntegration:
    """Integration tests for HL7TCPOperation."""
    
    @pytest.mark.asyncio
    async def test_operation_sends_message(self):
        """Test operation sends message and receives ACK."""
        async with MLLPEchoServer() as server:
            # Start operation
            operation = HL7TCPOperation(
                name="test-operation",
                adapter_settings={
                    "IPAddress": server.host,
                    "Port": server.port,
                },
                host_settings={"ReplyCodeActions": ":*=S"},
            )
            
            await operation.start()
            
            try:
                # Send message
                await operation.submit(SAMPLE_ADT_A01)
                
                # Wait for processing
                await asyncio.sleep(0.2)
                
                # Verify message was received by server
                assert len(server.received_messages) == 1
                assert server.received_messages[0] == SAMPLE_ADT_A01
                
                # Verify metrics
                assert operation.metrics.messages_sent >= 1
            
            finally:
                await operation.stop()
    
    @pytest.mark.asyncio
    async def test_operation_handles_error_ack(self):
        """Test operation handles error ACK according to ReplyCodeActions."""
        async with MLLPEchoServer() as server:
            server.ack_code = "AE"  # Application Error
            
            operation = HL7TCPOperation(
                name="test-operation",
                adapter_settings={
                    "IPAddress": server.host,
                    "Port": server.port,
                },
                host_settings={"ReplyCodeActions": ":?E=S,:*=S"},  # Errors = Success
            )
            
            await operation.start()
            
            try:
                # Send message - should succeed despite AE
                await operation.submit(SAMPLE_ADT_A01)
                await asyncio.sleep(0.2)
                
                assert len(server.received_messages) == 1
            
            finally:
                await operation.stop()


class TestRoutingEngineIntegration:
    """Integration tests for HL7RoutingEngine."""
    
    @pytest.mark.asyncio
    async def test_routing_engine_routes_by_message_type(self):
        """Test routing engine routes messages based on type."""
        engine = HL7RoutingEngine(name="test-router")
        
        # Add rules
        engine.add_rule(create_message_type_rule(
            name="ADT_Route",
            message_type="ADT",
            target="HL7.Out.PAS",
        ))
        engine.add_rule(create_message_type_rule(
            name="ORU_Route",
            message_type="ORU",
            target="HL7.Out.LAB",
        ))
        
        await engine.start()
        
        try:
            schema = HL7Schema(name="2.4")
            
            # Route ADT message
            adt_msg = HL7Message(raw=SAMPLE_ADT_A01, parsed=schema.parse(SAMPLE_ADT_A01))
            result = await engine.on_message(adt_msg)
            
            assert result.matched is True
            assert result.rule_name == "ADT_Route"
            assert "HL7.Out.PAS" in result.targets
            
            # Route ORU message
            oru_msg = HL7Message(raw=SAMPLE_ORU_R01, parsed=schema.parse(SAMPLE_ORU_R01))
            result = await engine.on_message(oru_msg)
            
            assert result.matched is True
            assert result.rule_name == "ORU_Route"
            assert "HL7.Out.LAB" in result.targets
        
        finally:
            await engine.stop()
    
    @pytest.mark.asyncio
    async def test_routing_engine_complex_rules(self):
        """Test routing engine with complex conditions using multiple ANDs."""
        engine = HL7RoutingEngine(name="test-router")
        
        # Add rule with multiple AND conditions on MSH fields
        engine.add_rule(RoutingRule(
            name="ADT_A01_From_SENDING",
            condition='{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01" AND {MSH-3} = "SENDING"',
            action=RuleAction.SEND,
            target="HL7.Out.Matched",
        ))
        
        await engine.start()
        
        try:
            schema = HL7Schema(name="2.4")
            
            # Message should match all three conditions
            msg = HL7Message(raw=SAMPLE_ADT_A01, parsed=schema.parse(SAMPLE_ADT_A01))
            result = await engine.on_message(msg)
            
            assert result.matched is True
            assert result.rule_name == "ADT_A01_From_SENDING"
            assert "HL7.Out.Matched" in result.targets
        
        finally:
            await engine.stop()


class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_service_to_operation_flow(self):
        """Test message flow from service through router to operation."""
        # This test simulates a complete message flow:
        # External System -> HL7TCPService -> HL7RoutingEngine -> HL7TCPOperation -> External System
        
        # Start echo server (simulates downstream system)
        async with MLLPEchoServer() as downstream:
            # Create components
            service = HL7TCPService(
                name="HL7.In.TCP",
                adapter_settings={"Port": 0},
                host_settings={"MessageSchemaCategory": "2.4"},
            )
            
            router = HL7RoutingEngine(name="HL7.Router")
            router.add_rule(create_message_type_rule(
                name="All_Messages",
                message_type="ADT",
                target="HL7.Out.TCP",
            ))
            
            operation = HL7TCPOperation(
                name="HL7.Out.TCP",
                adapter_settings={
                    "IPAddress": downstream.host,
                    "Port": downstream.port,
                },
            )
            
            # Start all components
            await service.start()
            await router.start()
            await operation.start()
            
            service_port = service._adapter._server.sockets[0].getsockname()[1]
            
            try:
                # Send message to service
                reader, writer = await asyncio.open_connection("127.0.0.1", service_port)
                
                writer.write(mllp_wrap(SAMPLE_ADT_A01))
                await writer.drain()
                
                # Read ACK from service
                ack_data = b""
                while True:
                    byte = await asyncio.wait_for(reader.read(1), timeout=5.0)
                    if not byte:
                        break
                    ack_data += byte
                    if ack_data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
                        break
                
                ack = mllp_unwrap(ack_data)
                assert b"MSA|AA" in ack
                
                writer.close()
                await writer.wait_closed()
                
                # Wait for processing
                await asyncio.sleep(0.2)
                
                # Verify service received message
                assert service.metrics.messages_received >= 1
            
            finally:
                await operation.stop()
                await router.stop()
                await service.stop()


class TestIRISConfigIntegration:
    """Tests for loading and using IRIS production configs."""
    
    def test_load_production_config(self):
        """Test loading a production configuration."""
        # Create a sample production XML
        xml_content = """<?xml version="1.0"?>
<Production Name="Test.Production" LogGeneralTraceEvents="false">
  <Description>Test Production for Integration Tests</Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="HL7.In.TCP" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
    <Setting Target="Adapter" Name="Port">2575</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
    <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
  </Item>
  <Item Name="HL7.Router" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true">
    <Setting Target="Host" Name="BusinessRuleName">Test.Router.Rules</Setting>
  </Item>
  <Item Name="HL7.Out.TCP" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true">
    <Setting Target="Adapter" Name="IPAddress">192.168.1.100</Setting>
    <Setting Target="Adapter" Name="Port">2575</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:*=S</Setting>
  </Item>
</Production>
"""
        
        loader = IRISXMLLoader()
        production = loader.load_from_string(xml_content)
        
        assert production.name == "Test.Production"
        assert len(production.items) == 3
        
        # Check service
        service_config = production.get_item("HL7.In.TCP")
        assert service_config is not None
        assert service_config.class_name == "li.hosts.hl7.HL7TCPService"
        assert str(service_config.get_setting("Adapter", "Port")) == "2575"
        
        # Check router
        router_config = production.get_item("HL7.Router")
        assert router_config is not None
        assert router_config.class_name == "li.hosts.routing.HL7RoutingEngine"
        
        # Check operation
        operation_config = production.get_item("HL7.Out.TCP")
        assert operation_config is not None
        assert operation_config.class_name == "li.hosts.hl7.HL7TCPOperation"
    
    def test_create_hosts_from_config(self):
        """Test creating host instances from production config."""
        xml_content = """<?xml version="1.0"?>
<Production Name="Test.Production">
  <Item Name="HL7.In.TCP" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="2" Enabled="true">
    <Setting Target="Adapter" Name="Port">2575</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
  </Item>
</Production>
"""
        
        loader = IRISXMLLoader()
        production = loader.load_from_string(xml_content)
        
        service_config = production.get_item("HL7.In.TCP")
        
        # Create host from config
        service = HL7TCPService(
            name=service_config.name,
            config=service_config,
        )
        
        assert service.name == "HL7.In.TCP"
        assert service.pool_size == 2
        assert service.message_schema_category == "PKB"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
