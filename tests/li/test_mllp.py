"""
Tests for LI MLLP Adapters.

Tests MLLP framing, connection handling, and message transport.
"""

import asyncio
import pytest

from hie.li.adapters import (
    MLLPInboundAdapter,
    MLLPOutboundAdapter,
    MLLPFrameError,
    MLLPConnectionError,
    MLLPTimeoutError,
    mllp_wrap,
    mllp_unwrap,
    MLLP_START_BLOCK,
    MLLP_END_BLOCK,
    MLLP_CARRIAGE_RETURN,
)
from hie.li.hosts import BusinessService, BusinessOperation


# Sample HL7 message for testing
SAMPLE_HL7 = b"MSH|^~\\&|SENDING|FAC|RECEIVING|FAC|20240115||ADT^A01|123|P|2.4\rPID|1||12345||DOE^JOHN\r"
SAMPLE_ACK = b"MSH|^~\\&|RECEIVING|FAC|SENDING|FAC|20240115||ACK|123|P|2.4\rMSA|AA|123\r"


class MockHost(BusinessService):
    """Mock host for testing adapters."""
    
    def __init__(self, name="test-host"):
        super().__init__(name=name)
        self.received_messages = []
    
    async def _process_message(self, message):
        self.received_messages.append(message)
        return message


class TestMLLPFraming:
    """Tests for MLLP framing functions."""
    
    def test_mllp_wrap(self):
        """Test MLLP message wrapping."""
        wrapped = mllp_wrap(SAMPLE_HL7)
        
        assert wrapped.startswith(MLLP_START_BLOCK)
        assert wrapped.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN)
        assert SAMPLE_HL7 in wrapped
    
    def test_mllp_unwrap(self):
        """Test MLLP message unwrapping."""
        wrapped = mllp_wrap(SAMPLE_HL7)
        unwrapped = mllp_unwrap(wrapped)
        
        assert unwrapped == SAMPLE_HL7
    
    def test_mllp_unwrap_without_cr(self):
        """Test unwrapping message without trailing CR."""
        wrapped = MLLP_START_BLOCK + SAMPLE_HL7 + MLLP_END_BLOCK
        unwrapped = mllp_unwrap(wrapped)
        
        assert unwrapped == SAMPLE_HL7
    
    def test_mllp_unwrap_missing_start(self):
        """Test unwrapping fails without start block."""
        with pytest.raises(MLLPFrameError, match="start block"):
            mllp_unwrap(SAMPLE_HL7 + MLLP_END_BLOCK)
    
    def test_mllp_unwrap_missing_end(self):
        """Test unwrapping fails without end block."""
        with pytest.raises(MLLPFrameError, match="end block"):
            mllp_unwrap(MLLP_START_BLOCK + SAMPLE_HL7)
    
    def test_mllp_roundtrip(self):
        """Test wrap/unwrap roundtrip."""
        original = b"MSH|^~\\&|TEST|||20240101||ADT^A01|1|P|2.4\r"
        wrapped = mllp_wrap(original)
        unwrapped = mllp_unwrap(wrapped)
        
        assert unwrapped == original


class TestMLLPInboundAdapter:
    """Tests for MLLPInboundAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization with settings."""
        host = MockHost()
        adapter = MLLPInboundAdapter(host, {
            "Port": 2575,
            "Host": "0.0.0.0",
            "MaxConnections": 50,
            "ReadTimeout": 60,
        })
        
        assert adapter._port == 2575
        assert adapter._bind_host == "0.0.0.0"
        assert adapter._max_connections == 50
        assert adapter._read_timeout == 60.0
    
    def test_adapter_default_settings(self):
        """Test adapter uses default settings."""
        host = MockHost()
        adapter = MLLPInboundAdapter(host, {})
        
        assert adapter._port == 2575
        assert adapter._bind_host == "0.0.0.0"
        assert adapter._max_connections == 100
        assert adapter._read_timeout == 30.0
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test adapter start/stop lifecycle."""
        host = MockHost()
        adapter = MLLPInboundAdapter(host, {"Port": 19001})
        
        await adapter.start()
        assert adapter._server is not None
        
        await adapter.stop()
        assert adapter._server is None


class TestMLLPOutboundAdapter:
    """Tests for MLLPOutboundAdapter."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization with settings."""
        host = MockHost()
        adapter = MLLPOutboundAdapter(host, {
            "IPAddress": "192.168.1.100",
            "Port": 2575,
            "ConnectTimeout": 15,
            "AckTimeout": 45,
            "MaxRetries": 5,
        })
        
        assert adapter._remote_host == "192.168.1.100"
        assert adapter._remote_port == 2575
        assert adapter._connect_timeout == 15.0
        assert adapter._ack_timeout == 45.0
        assert adapter._max_retries == 5
    
    def test_adapter_default_settings(self):
        """Test adapter uses default settings."""
        host = MockHost()
        adapter = MLLPOutboundAdapter(host, {})
        
        assert adapter._remote_host == "localhost"
        assert adapter._remote_port == 2575
        assert adapter._connect_timeout == 10.0
        assert adapter._max_retries == 3
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self):
        """Test adapter start/stop lifecycle."""
        host = MockHost()
        adapter = MLLPOutboundAdapter(host, {"IPAddress": "localhost", "Port": 19002})
        
        await adapter.start()
        assert adapter._connected is False  # Lazy connection
        
        await adapter.stop()
        assert adapter._connected is False


class TestMLLPIntegration:
    """Integration tests for MLLP communication."""
    
    @pytest.mark.asyncio
    async def test_send_receive_message(self):
        """Test sending and receiving a message via MLLP."""
        # Create a simple echo server
        received_messages = []
        
        async def handle_client(reader, writer):
            try:
                # Read MLLP message
                data = b""
                while True:
                    byte = await reader.read(1)
                    if not byte:
                        break
                    data += byte
                    if data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
                        break
                
                if data:
                    # Unwrap and store
                    message = mllp_unwrap(data)
                    received_messages.append(message)
                    
                    # Send ACK
                    ack = mllp_wrap(SAMPLE_ACK)
                    writer.write(ack)
                    await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
        
        # Start server
        server = await asyncio.start_server(handle_client, "127.0.0.1", 19003)
        
        try:
            # Create outbound adapter and send
            host = MockHost()
            adapter = MLLPOutboundAdapter(host, {
                "IPAddress": "127.0.0.1",
                "Port": 19003,
            })
            
            await adapter.start()
            
            # Send message
            ack = await adapter.send(SAMPLE_HL7)
            
            # Verify
            assert len(received_messages) == 1
            assert received_messages[0] == SAMPLE_HL7
            assert b"MSA|AA" in ack
            
            await adapter.stop()
        
        finally:
            server.close()
            await server.wait_closed()
    
    @pytest.mark.asyncio
    async def test_connection_retry(self):
        """Test connection retry on failure."""
        host = MockHost()
        adapter = MLLPOutboundAdapter(host, {
            "IPAddress": "127.0.0.1",
            "Port": 19999,  # Non-existent port
            "MaxRetries": 2,
            "ReconnectDelay": 0.1,
            "ConnectTimeout": 0.5,
        })
        
        await adapter.start()
        
        with pytest.raises(MLLPConnectionError):
            await adapter.send(SAMPLE_HL7)
        
        # Should have tried MaxRetries times
        assert adapter._metrics.errors_total >= 1
        
        await adapter.stop()


class TestMLLPStreamReading:
    """Tests for MLLP stream reading."""
    
    @pytest.mark.asyncio
    async def test_read_mllp_message(self):
        """Test reading MLLP message from stream."""
        from hie.li.adapters.mllp import read_mllp_message
        
        # Create a mock reader with MLLP data
        wrapped = mllp_wrap(SAMPLE_HL7)
        reader = asyncio.StreamReader()
        reader.feed_data(wrapped)
        reader.feed_eof()
        
        message = await read_mllp_message(reader, timeout=1.0)
        
        assert message == SAMPLE_HL7
    
    @pytest.mark.asyncio
    async def test_read_mllp_message_with_garbage(self):
        """Test reading MLLP message with leading garbage."""
        from hie.li.adapters.mllp import read_mllp_message
        
        # Add garbage before the message
        garbage = b"some garbage data"
        wrapped = mllp_wrap(SAMPLE_HL7)
        
        reader = asyncio.StreamReader()
        reader.feed_data(garbage + wrapped)
        reader.feed_eof()
        
        message = await read_mllp_message(reader, timeout=1.0)
        
        assert message == SAMPLE_HL7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
