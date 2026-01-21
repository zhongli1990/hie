"""
MLLP Sender - Sends HL7v2 messages over MLLP (Minimal Lower Layer Protocol).

MLLP is the standard transport protocol for HL7v2 messages over TCP.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from hie.core.item import Sender
from hie.core.message import Message, MessageState
from hie.core.config import MLLPSenderConfig

logger = structlog.get_logger(__name__)

# MLLP framing characters
MLLP_START_BLOCK = b"\x0b"  # VT (vertical tab)
MLLP_END_BLOCK = b"\x1c"    # FS (file separator)
MLLP_CARRIAGE_RETURN = b"\x0d"  # CR


class MLLPConnection:
    """
    A single MLLP connection to a remote host.
    
    Handles connection lifecycle, framing, and acknowledgment parsing.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 30.0,
        keepalive: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.keepalive = keepalive
        
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._logger = logger.bind(host=host, port=port)
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._connected and self._writer is not None
    
    async def connect(self) -> None:
        """Establish connection to remote host."""
        if self.is_connected:
            return
        
        async with self._lock:
            if self.is_connected:
                return
            
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout
                )
                self._connected = True
                self._logger.debug("mllp_connected")
            
            except asyncio.TimeoutError:
                raise ConnectionError(f"Connection timeout to {self.host}:{self.port}")
            except OSError as e:
                raise ConnectionError(f"Connection failed to {self.host}:{self.port}: {e}")
    
    async def disconnect(self) -> None:
        """Close the connection."""
        async with self._lock:
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
            
            self._reader = None
            self._writer = None
            self._connected = False
            self._logger.debug("mllp_disconnected")
    
    async def send(self, message: bytes) -> bytes:
        """
        Send a message and wait for acknowledgment.
        
        Args:
            message: Raw HL7v2 message bytes (without MLLP framing)
            
        Returns:
            Raw acknowledgment message bytes (without MLLP framing)
        """
        if not self.is_connected:
            await self.connect()
        
        async with self._lock:
            try:
                # Frame the message with MLLP
                framed = MLLP_START_BLOCK + message + MLLP_END_BLOCK + MLLP_CARRIAGE_RETURN
                
                # Send
                self._writer.write(framed)
                await self._writer.drain()
                
                # Read acknowledgment
                ack = await self._read_mllp_message()
                
                return ack
            
            except Exception as e:
                # Connection may be broken, mark as disconnected
                self._connected = False
                raise
    
    async def _read_mllp_message(self) -> bytes:
        """Read a complete MLLP-framed message."""
        buffer = b""
        
        # Read until we find the start block
        while True:
            byte = await asyncio.wait_for(
                self._reader.read(1),
                timeout=self.timeout
            )
            if not byte:
                raise ConnectionError("Connection closed while reading")
            if byte == MLLP_START_BLOCK:
                break
        
        # Read until we find the end block
        while True:
            byte = await asyncio.wait_for(
                self._reader.read(1),
                timeout=self.timeout
            )
            if not byte:
                raise ConnectionError("Connection closed while reading")
            if byte == MLLP_END_BLOCK:
                # Read the trailing CR
                await self._reader.read(1)
                break
            buffer += byte
        
        return buffer


class MLLPConnectionPool:
    """
    Pool of MLLP connections for concurrent sending.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        max_connections: int = 5,
        timeout: float = 30.0,
        keepalive: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.timeout = timeout
        self.keepalive = keepalive
        
        self._pool: asyncio.Queue[MLLPConnection] = asyncio.Queue(maxsize=max_connections)
        self._created = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> MLLPConnection:
        """Acquire a connection from the pool."""
        # Try to get an existing connection
        try:
            conn = self._pool.get_nowait()
            if conn.is_connected:
                return conn
            # Connection is stale, create a new one
        except asyncio.QueueEmpty:
            pass
        
        # Create a new connection if under limit
        async with self._lock:
            if self._created < self.max_connections:
                conn = MLLPConnection(
                    self.host,
                    self.port,
                    self.timeout,
                    self.keepalive,
                )
                self._created += 1
                return conn
        
        # Wait for a connection to be released
        conn = await self._pool.get()
        return conn
    
    async def release(self, conn: MLLPConnection) -> None:
        """Release a connection back to the pool."""
        if self.keepalive and conn.is_connected:
            try:
                self._pool.put_nowait(conn)
                return
            except asyncio.QueueFull:
                pass
        
        # Close the connection
        await conn.disconnect()
        async with self._lock:
            self._created -= 1
    
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        while True:
            try:
                conn = self._pool.get_nowait()
                await conn.disconnect()
            except asyncio.QueueEmpty:
                break
        
        async with self._lock:
            self._created = 0


class MLLPSender(Sender):
    """
    MLLP sender for HL7v2 messages.
    
    Features:
    - Connection pooling
    - Automatic reconnection
    - ACK/NAK handling
    - Configurable timeouts
    """
    
    def __init__(self, config: MLLPSenderConfig) -> None:
        super().__init__(config)
        self._mllp_config = config
        self._pool: MLLPConnectionPool | None = None
        self._logger = logger.bind(
            item_id=self.id,
            host=config.host,
            port=config.port
        )
    
    @property
    def mllp_config(self) -> MLLPSenderConfig:
        """MLLP-specific configuration."""
        return self._mllp_config
    
    async def _on_start(self) -> None:
        """Initialize connection pool."""
        self._pool = MLLPConnectionPool(
            host=self._mllp_config.host,
            port=self._mllp_config.port,
            max_connections=self._mllp_config.max_connections,
            timeout=self._mllp_config.timeout,
            keepalive=self._mllp_config.keepalive,
        )
        self._logger.info("mllp_sender_started")
    
    async def _on_stop(self) -> None:
        """Close all connections."""
        if self._pool:
            await self._pool.close_all()
        self._logger.info("mllp_sender_stopped")
    
    async def _send(self, message: Message) -> bool:
        """Send a message via MLLP."""
        if not self._pool:
            raise RuntimeError("MLLP sender not started")
        
        conn = await self._pool.acquire()
        try:
            # Send and get acknowledgment
            ack_bytes = await conn.send(message.raw)
            
            # Parse ACK to check for success
            ack_success = self._parse_ack(ack_bytes)
            
            if ack_success:
                self._logger.debug(
                    "message_sent",
                    message_id=str(message.id),
                    size=message.payload.size
                )
                return True
            else:
                self._logger.warning(
                    "message_nacked",
                    message_id=str(message.id),
                    ack=ack_bytes.decode("utf-8", errors="replace")[:200]
                )
                return False
        
        except Exception as e:
            self._logger.error(
                "send_failed",
                message_id=str(message.id),
                error=str(e)
            )
            # Mark connection as broken
            await conn.disconnect()
            raise
        
        finally:
            await self._pool.release(conn)
    
    def _parse_ack(self, ack_bytes: bytes) -> bool:
        """
        Parse an HL7v2 ACK message to determine success.
        
        Returns True for AA (Application Accept) or CA (Commit Accept).
        Returns False for AE (Application Error), AR (Application Reject),
        CE (Commit Error), or CR (Commit Reject).
        """
        try:
            ack_text = ack_bytes.decode("utf-8", errors="replace")
            
            # Look for MSA segment
            for line in ack_text.split("\r"):
                if line.startswith("MSA"):
                    fields = line.split("|")
                    if len(fields) >= 2:
                        ack_code = fields[1].strip()
                        return ack_code in ("AA", "CA")
            
            # If no MSA found, assume success (some systems don't send proper ACKs)
            self._logger.warning("no_msa_segment", ack=ack_text[:200])
            return True
        
        except Exception as e:
            self._logger.error("ack_parse_failed", error=str(e))
            return False
    
    @classmethod
    def from_config(cls, config: dict[str, Any] | MLLPSenderConfig) -> MLLPSender:
        """Create an MLLPSender from configuration."""
        if isinstance(config, dict):
            config = MLLPSenderConfig.model_validate(config)
        return cls(config)
