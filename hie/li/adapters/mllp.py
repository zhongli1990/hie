"""
LI MLLP Adapters

Implements Minimal Lower Layer Protocol (MLLP) for HL7v2 message transport.
MLLP wraps HL7 messages with start/end block characters for reliable TCP transmission.

MLLP Frame Format:
    <SB>message<EB><CR>
    
Where:
    SB = Start Block (0x0B, vertical tab)
    EB = End Block (0x1C, file separator)
    CR = Carriage Return (0x0D)

This is the standard transport protocol for HL7v2 in healthcare environments
including NHS acute hospital trusts.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, TYPE_CHECKING

import structlog

from hie.li.adapters.base import InboundAdapter, OutboundAdapter, AdapterState

if TYPE_CHECKING:
    from hie.li.hosts.base import Host

logger = structlog.get_logger(__name__)

# MLLP framing characters
MLLP_START_BLOCK = b"\x0b"  # Vertical Tab (VT)
MLLP_END_BLOCK = b"\x1c"    # File Separator (FS)
MLLP_CARRIAGE_RETURN = b"\x0d"  # Carriage Return (CR)

# Default timeouts (in seconds)
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_WRITE_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_ACK_TIMEOUT = 30.0


@dataclass
class MLLPConnectionMetrics:
    """Metrics for a single MLLP connection."""
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages_received: int = 0
    messages_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    errors: int = 0
    last_activity_at: datetime | None = None


class MLLPFrameError(Exception):
    """Error parsing MLLP frame."""
    pass


class MLLPConnectionError(Exception):
    """Error with MLLP connection."""
    pass


class MLLPTimeoutError(Exception):
    """Timeout during MLLP operation."""
    pass


def mllp_wrap(message: bytes) -> bytes:
    """
    Wrap a message in MLLP framing.
    
    Args:
        message: Raw HL7 message bytes
        
    Returns:
        MLLP-framed message
    """
    return MLLP_START_BLOCK + message + MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN


def mllp_unwrap(data: bytes) -> bytes:
    """
    Unwrap a message from MLLP framing.
    
    Args:
        data: MLLP-framed data
        
    Returns:
        Raw HL7 message bytes
        
    Raises:
        MLLPFrameError: If framing is invalid
    """
    if not data.startswith(MLLP_START_BLOCK):
        raise MLLPFrameError("Missing MLLP start block (0x0B)")
    
    if not data.endswith(MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN):
        # Try without CR (some systems omit it)
        if not data.endswith(MLLP_END_BLOCK):
            raise MLLPFrameError("Missing MLLP end block (0x1C)")
        return data[1:-1]
    
    return data[1:-2]


async def read_mllp_message(
    reader: asyncio.StreamReader,
    timeout: float = DEFAULT_READ_TIMEOUT,
    max_size: int = 10 * 1024 * 1024,  # 10MB default max
) -> bytes:
    """
    Read a complete MLLP-framed message from a stream.
    
    Args:
        reader: Async stream reader
        timeout: Read timeout in seconds
        max_size: Maximum message size in bytes
        
    Returns:
        Raw HL7 message bytes (unwrapped)
        
    Raises:
        MLLPFrameError: If framing is invalid
        MLLPTimeoutError: If read times out
        MLLPConnectionError: If connection is closed
    """
    buffer = bytearray()
    
    try:
        # Read until start block
        while True:
            byte = await asyncio.wait_for(reader.read(1), timeout=timeout)
            if not byte:
                raise MLLPConnectionError("Connection closed while waiting for start block")
            if byte == MLLP_START_BLOCK:
                break
            # Ignore any bytes before start block (common with keepalives)
        
        # Read until end block + CR
        while True:
            byte = await asyncio.wait_for(reader.read(1), timeout=timeout)
            if not byte:
                raise MLLPConnectionError("Connection closed while reading message")
            
            buffer.extend(byte)
            
            if len(buffer) > max_size:
                raise MLLPFrameError(f"Message exceeds maximum size: {max_size} bytes")
            
            # Check for end sequence
            if len(buffer) >= 2 and buffer[-2:] == MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN:
                return bytes(buffer[:-2])
            
            # Some systems omit the CR
            if len(buffer) >= 1 and buffer[-1:] == MLLP_END_BLOCK:
                # Peek to see if CR follows
                try:
                    next_byte = await asyncio.wait_for(reader.read(1), timeout=0.1)
                    if next_byte == MLLP_CARRIAGE_RETURN:
                        return bytes(buffer[:-1])
                    else:
                        # Not CR, put it back in buffer
                        buffer.extend(next_byte)
                except asyncio.TimeoutError:
                    # No CR, return message
                    return bytes(buffer[:-1])
    
    except asyncio.TimeoutError:
        raise MLLPTimeoutError(f"Read timeout after {timeout} seconds")


async def write_mllp_message(
    writer: asyncio.StreamWriter,
    message: bytes,
    timeout: float = DEFAULT_WRITE_TIMEOUT,
) -> None:
    """
    Write an MLLP-framed message to a stream.
    
    Args:
        writer: Async stream writer
        message: Raw HL7 message bytes
        timeout: Write timeout in seconds
        
    Raises:
        MLLPTimeoutError: If write times out
        MLLPConnectionError: If connection fails
    """
    try:
        framed = mllp_wrap(message)
        writer.write(framed)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
    except asyncio.TimeoutError:
        raise MLLPTimeoutError(f"Write timeout after {timeout} seconds")
    except (ConnectionError, OSError) as e:
        raise MLLPConnectionError(f"Connection error: {e}")


class MLLPInboundAdapter(InboundAdapter):
    """
    MLLP Inbound Adapter for receiving HL7v2 messages over TCP.
    
    Listens on a configured port and accepts connections from external systems.
    Each connection is handled in a separate task, allowing concurrent connections.
    
    Settings:
        Port: TCP port to listen on (required)
        Host: IP address to bind to (default: 0.0.0.0)
        MaxConnections: Maximum concurrent connections (default: 100)
        ReadTimeout: Read timeout in seconds (default: 30)
        AckTimeout: ACK generation timeout in seconds (default: 30)
        MaxMessageSize: Maximum message size in bytes (default: 10MB)
    """
    
    def __init__(self, host: "Host", settings: dict[str, Any] | None = None):
        super().__init__(host, settings)
        
        # Server state
        self._server: asyncio.Server | None = None
        self._connections: dict[str, asyncio.Task] = {}
        self._connection_metrics: dict[str, MLLPConnectionMetrics] = {}
        self._shutdown_event = asyncio.Event()
        
        # Configuration
        self._port = int(self.get_setting("Port", 2575))
        self._bind_host = self.get_setting("Host", "0.0.0.0")
        self._max_connections = int(self.get_setting("MaxConnections", 100))
        self._read_timeout = float(self.get_setting("ReadTimeout", DEFAULT_READ_TIMEOUT))
        self._ack_timeout = float(self.get_setting("AckTimeout", DEFAULT_ACK_TIMEOUT))
        self._max_message_size = int(self.get_setting("MaxMessageSize", 10 * 1024 * 1024))
        
        self._log = logger.bind(
            adapter="MLLPInboundAdapter",
            host=host.name,
            port=self._port,
        )
    
    async def on_start(self) -> None:
        """Start the MLLP server."""
        self._shutdown_event.clear()
        
        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self._bind_host,
            port=self._port,
            reuse_address=True,
        )
        
        self._log.info(
            "mllp_server_started",
            bind_host=self._bind_host,
            port=self._port,
            max_connections=self._max_connections,
        )
    
    async def on_stop(self) -> None:
        """Stop the MLLP server and close all connections."""
        self._shutdown_event.set()
        
        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        
        # Cancel all connection handlers
        for conn_id, task in list(self._connections.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._connections.clear()
        self._connection_metrics.clear()
        
        self._log.info("mllp_server_stopped")
    
    async def listen(self) -> None:
        """
        Start listening for connections.
        
        This is called by the host after the adapter is started.
        The server runs until stopped.
        """
        if self._server:
            await self._server.serve_forever()
    
    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single MLLP connection."""
        # Get connection info
        peername = writer.get_extra_info("peername")
        conn_id = f"{peername[0]}:{peername[1]}" if peername else "unknown"
        
        # Check connection limit
        if len(self._connections) >= self._max_connections:
            self._log.warning("mllp_connection_rejected", reason="max_connections", conn_id=conn_id)
            writer.close()
            await writer.wait_closed()
            return
        
        # Track connection
        metrics = MLLPConnectionMetrics()
        self._connection_metrics[conn_id] = metrics
        self._metrics.connections_total += 1
        self._metrics.connections_active += 1
        
        self._log.info("mllp_connection_accepted", conn_id=conn_id)
        
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Read message
                    message = await read_mllp_message(
                        reader,
                        timeout=self._read_timeout,
                        max_size=self._max_message_size,
                    )
                    
                    metrics.messages_received += 1
                    metrics.bytes_received += len(message)
                    metrics.last_activity_at = datetime.now(timezone.utc)
                    self._metrics.bytes_received += len(message)
                    
                    self._log.debug(
                        "mllp_message_received",
                        conn_id=conn_id,
                        size=len(message),
                    )
                    
                    # Process message and get ACK
                    ack = await self._process_message(message, conn_id)
                    
                    # Send ACK
                    if ack:
                        await write_mllp_message(writer, ack, timeout=self._ack_timeout)
                        metrics.messages_sent += 1
                        metrics.bytes_sent += len(ack)
                        self._metrics.bytes_sent += len(ack)
                        
                        self._log.debug(
                            "mllp_ack_sent",
                            conn_id=conn_id,
                            size=len(ack),
                        )
                
                except MLLPTimeoutError:
                    # Timeout is normal for idle connections
                    continue
                
                except MLLPConnectionError as e:
                    self._log.info("mllp_connection_closed", conn_id=conn_id, reason=str(e))
                    break
                
                except MLLPFrameError as e:
                    self._log.warning("mllp_frame_error", conn_id=conn_id, error=str(e))
                    metrics.errors += 1
                    self._metrics.errors_total += 1
                    # Continue to try reading next message
                
                except Exception as e:
                    self._log.error("mllp_processing_error", conn_id=conn_id, error=str(e))
                    metrics.errors += 1
                    self._metrics.errors_total += 1
                    # Continue to try reading next message
        
        finally:
            # Cleanup
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            
            self._metrics.connections_active -= 1
            del self._connection_metrics[conn_id]
            
            self._log.info(
                "mllp_connection_ended",
                conn_id=conn_id,
                messages_received=metrics.messages_received,
                messages_sent=metrics.messages_sent,
            )
    
    async def _process_message(self, message: bytes, conn_id: str) -> bytes | None:
        """
        Process a received message and return ACK.
        
        Passes message to host for processing and returns the ACK.
        
        Args:
            message: Raw HL7 message bytes
            conn_id: Connection identifier for logging
            
        Returns:
            ACK message bytes, or None if no ACK should be sent
        """
        try:
            # Pass to host via on_data_received
            result = await self.on_data_received(message)
            
            # If host returns an ACK, use it
            if isinstance(result, bytes):
                return result
            elif hasattr(result, "ack"):
                return result.ack
            
            # Generate default ACK if host doesn't provide one
            return None
        
        except Exception as e:
            self._log.error("mllp_message_processing_failed", conn_id=conn_id, error=str(e))
            raise


class MLLPOutboundAdapter(OutboundAdapter):
    """
    MLLP Outbound Adapter for sending HL7v2 messages over TCP.
    
    Connects to a remote system and sends messages, waiting for ACK responses.
    Supports connection pooling and automatic reconnection.
    
    Settings:
        IPAddress: Remote host IP or hostname (required)
        Port: Remote TCP port (required)
        ConnectTimeout: Connection timeout in seconds (default: 10)
        WriteTimeout: Write timeout in seconds (default: 30)
        AckTimeout: ACK wait timeout in seconds (default: 30)
        ReconnectDelay: Delay before reconnection attempt in seconds (default: 5)
        MaxRetries: Maximum send retries (default: 3)
        KeepAlive: Enable TCP keepalive (default: true)
    """
    
    def __init__(self, host: "Host", settings: dict[str, Any] | None = None):
        super().__init__(host, settings)
        
        # Connection state
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connection_lock = asyncio.Lock()
        self._connected = False
        
        # Configuration
        self._remote_host = self.get_setting("IPAddress", "localhost")
        self._remote_port = int(self.get_setting("Port", 2575))
        self._connect_timeout = float(self.get_setting("ConnectTimeout", DEFAULT_CONNECT_TIMEOUT))
        self._write_timeout = float(self.get_setting("WriteTimeout", DEFAULT_WRITE_TIMEOUT))
        self._ack_timeout = float(self.get_setting("AckTimeout", DEFAULT_ACK_TIMEOUT))
        self._reconnect_delay = float(self.get_setting("ReconnectDelay", 5.0))
        self._max_retries = int(self.get_setting("MaxRetries", 3))
        self._keepalive = self.get_setting("KeepAlive", True)
        
        self._log = logger.bind(
            adapter="MLLPOutboundAdapter",
            host=host.name,
            remote=f"{self._remote_host}:{self._remote_port}",
        )
    
    async def on_start(self) -> None:
        """Initialize the adapter (connection is lazy)."""
        self._log.info("mllp_outbound_adapter_started")
    
    async def on_stop(self) -> None:
        """Close the connection."""
        await self._disconnect()
        self._log.info("mllp_outbound_adapter_stopped")
    
    async def _connect(self) -> None:
        """Establish connection to remote system."""
        async with self._connection_lock:
            if self._connected:
                return
            
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        host=self._remote_host,
                        port=self._remote_port,
                    ),
                    timeout=self._connect_timeout,
                )
                
                # Enable keepalive if configured
                if self._keepalive:
                    sock = self._writer.get_extra_info("socket")
                    if sock:
                        import socket
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                self._connected = True
                self._metrics.connections_total += 1
                self._metrics.connections_active = 1
                
                self._log.info(
                    "mllp_connected",
                    remote_host=self._remote_host,
                    remote_port=self._remote_port,
                )
            
            except asyncio.TimeoutError:
                raise MLLPTimeoutError(f"Connection timeout after {self._connect_timeout}s")
            except (ConnectionError, OSError) as e:
                raise MLLPConnectionError(f"Failed to connect: {e}")
    
    async def _disconnect(self) -> None:
        """Close the connection."""
        async with self._connection_lock:
            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
                self._writer = None
                self._reader = None
            
            self._connected = False
            self._metrics.connections_active = 0
    
    async def _ensure_connected(self) -> None:
        """Ensure connection is established, reconnecting if needed."""
        if not self._connected:
            await self._connect()
    
    async def send(self, message: Any) -> bytes:
        """
        Send a message and wait for ACK.
        
        Args:
            message: HL7 message (bytes or object with .raw attribute)
            
        Returns:
            ACK message bytes
            
        Raises:
            MLLPConnectionError: If connection fails
            MLLPTimeoutError: If operation times out
        """
        # Extract bytes from message
        if isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
        else:
            data = str(message).encode("utf-8")
        
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                await self._ensure_connected()
                
                # Send message
                await write_mllp_message(self._writer, data, timeout=self._write_timeout)
                self._metrics.bytes_sent += len(data)
                
                self._log.debug("mllp_message_sent", size=len(data), attempt=attempt + 1)
                
                # Wait for ACK
                ack = await read_mllp_message(
                    self._reader,
                    timeout=self._ack_timeout,
                )
                
                self._metrics.bytes_received += len(ack)
                await self.on_send(data)
                
                self._log.debug("mllp_ack_received", size=len(ack))
                
                return ack
            
            except (MLLPConnectionError, MLLPTimeoutError) as e:
                last_error = e
                self._metrics.errors_total += 1
                
                self._log.warning(
                    "mllp_send_failed",
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                    error=str(e),
                )
                
                # Disconnect and retry
                await self._disconnect()
                
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._reconnect_delay)
        
        raise MLLPConnectionError(f"Failed after {self._max_retries} attempts: {last_error}")
    
    async def send_no_ack(self, message: Any) -> None:
        """
        Send a message without waiting for ACK.
        
        Used for fire-and-forget scenarios.
        
        Args:
            message: HL7 message (bytes or object with .raw attribute)
        """
        # Extract bytes from message
        if isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
        else:
            data = str(message).encode("utf-8")
        
        await self._ensure_connected()
        await write_mllp_message(self._writer, data, timeout=self._write_timeout)
        self._metrics.bytes_sent += len(data)
        await self.on_send(data)
        
        self._log.debug("mllp_message_sent_no_ack", size=len(data))
