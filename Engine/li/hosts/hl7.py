"""
LI HL7 Hosts

Provides HL7-specific host implementations for NHS acute hospital integration:
- HL7TCPService: Receives HL7v2 messages via MLLP/TCP
- HL7TCPOperation: Sends HL7v2 messages via MLLP/TCP

These hosts integrate with the HL7Schema system for message parsing,
validation, and ACK generation.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import UUID

import structlog

from Engine.li.hosts.base import BusinessService, BusinessOperation, HostMetrics
from Engine.li.adapters.mllp import MLLPInboundAdapter, MLLPOutboundAdapter
from Engine.li.adapters.file import InboundFileAdapter, OutboundFileAdapter
from Engine.li.adapters.http import (
    InboundHTTPAdapter, OutboundHTTPAdapter,
    HTTPRequest, HTTPResponse,
)
from Engine.li.schemas.hl7 import HL7Schema, HL7ParsedView
from Engine.li.registry import SchemaRegistry, ClassRegistry

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


async def _store_inbound_message(
    project_id: UUID,
    item_name: str,
    raw_content: bytes,
    ack_content: bytes | None,
    message_type: str | None,
    status: str,
    target_config_names: list[str] | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
    remote_host: str | None = None,
    remote_port: int | None = None,
    session_id: str | None = None,
    correlation_id: str | None = None,
) -> tuple[str, "UUID | None", "UUID | None"]:
    """
    Store inbound message using IRIS-convention per-leg trace model.

    1. Stores body once in message_bodies (with dedup)
    2. Creates one message_header per target (one arrow per target)

    Returns (session_id, header_id, body_id).
    """
    from uuid import uuid4

    if not session_id:
        session_id = f"SES-{uuid4()}"

    header_id = None
    body_id = None

    try:
        from Engine.api.services.message_store import (
            store_message_body, store_message_header, update_header_status,
        )

        # Step 1: Store body once
        body_id = await store_message_body(
            raw_content=raw_content,
            body_class_name='EnsLib.HL7.Message',
            content_type='application/hl7-v2+er7',
        )

        # Step 2: Create one header per target
        targets = target_config_names or []
        is_err = status in ('error', 'failed')

        if targets:
            for target_name in targets:
                header_id = await store_message_header(
                    project_id=project_id,
                    session_id=session_id,
                    source_config_name=item_name,
                    target_config_name=target_name,
                    source_business_type='service',
                    target_business_type='process',
                    message_body_id=body_id,
                    message_type=message_type,
                    body_class_name='EnsLib.HL7.Message',
                    status='Completed' if not is_err else 'Error',
                    is_error=is_err,
                    error_status=error_message,
                    correlation_id=correlation_id,
                )
        else:
            # No targets configured — store a self-referencing header for visibility
            header_id = await store_message_header(
                project_id=project_id,
                session_id=session_id,
                source_config_name=item_name,
                target_config_name=item_name,
                source_business_type='service',
                target_business_type='service',
                message_body_id=body_id,
                message_type=message_type,
                body_class_name='EnsLib.HL7.Message',
                status='Completed' if not is_err else 'Error',
                is_error=is_err,
                error_status=error_message,
                correlation_id=correlation_id,
            )

        # Also store ACK body if present
        if ack_content and header_id:
            ack_body_id = await store_message_body(
                raw_content=ack_content,
                body_class_name='EnsLib.HL7.Message',
                content_type='application/hl7-v2+er7',
            )

    except Exception as e:
        logger.warning("inbound_message_storage_failed", error=str(e))

    return session_id, header_id, body_id


class HL7TCPService(BusinessService):
    """
    HL7v2 TCP Service using MLLP protocol.
    
    Receives HL7v2 messages via MLLP/TCP, validates them against the configured
    schema, generates appropriate ACK responses, and routes messages to
    configured targets.
    
    This is the LI equivalent of IRIS EnsLib.HL7.Service.TCPService.
    
    Settings (Host):
        MessageSchemaCategory: Schema category for validation (e.g., "2.4", "PKB")
        TargetConfigNames: Comma-separated list of target hosts
        AckMode: ACK generation mode ("Immediate", "Application", "Never")
        BadMessageHandler: Target for invalid messages
        SearchTableClass: Class for message indexing (future)
        AlertOnError: Send alert on processing errors (default: true)
    
    Settings (Adapter):
        Port: TCP port to listen on (required)
        Host: IP address to bind to (default: 0.0.0.0)
        MaxConnections: Maximum concurrent connections (default: 100)
        ReadTimeout: Read timeout in seconds (default: 30)
    
    Example IRIS Config:
        <Item Name="HL7.In.TCP" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="Port">2575</Setting>
            <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
            <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
        </Item>
    """
    
    adapter_class = MLLPInboundAdapter
    
    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )
        
        # HL7-specific state
        self._schema: HL7Schema | None = None
        self._ack_mode = self.get_setting("Host", "AckMode", "Immediate")
        self._bad_message_handler = self.get_setting("Host", "BadMessageHandler")
        self._alert_on_error = self.get_setting("Host", "AlertOnError", True)
        
        self._log = logger.bind(
            host="HL7TCPService",
            name=name,
            schema=self.message_schema_category,
        )
    
    @property
    def message_schema_category(self) -> str | None:
        """Get the configured message schema category."""
        return self.get_setting("Host", "MessageSchemaCategory")
    
    async def on_start(self) -> None:
        """Initialize schema and start adapter."""
        # Load schema
        schema_name = self.message_schema_category
        if schema_name:
            self._schema = SchemaRegistry.get(schema_name)
            if not self._schema:
                # Create default HL7 schema
                self._schema = HL7Schema(name=schema_name)
                SchemaRegistry.register(self._schema)
                self._log.info("schema_created", schema=schema_name)
        else:
            # Default to 2.4
            self._schema = HL7Schema(name="2.4")
        
        await super().on_start()
        
        self._log.info(
            "hl7_tcp_service_started",
            port=self.get_setting("Adapter", "Port"),
            schema=self._schema.name if self._schema else None,
            targets=self.target_config_names,
        )
    
    async def on_message_received(self, data: bytes) -> Any:
        """
        Process received HL7 message data.
        
        Parses the message, validates it, and creates an appropriate response.
        
        Args:
            data: Raw HL7 message bytes
            
        Returns:
            Message object with parsed view and ACK
        """
        start_time = time.time()
        received_at = datetime.now(timezone.utc)
        
        # Parse message
        parsed: HL7ParsedView | None = None
        ack: bytes | None = None
        validation_errors = []
        message_type: str | None = None
        
        try:
            if self._schema:
                parsed = self._schema.parse(data)
                message_type = parsed.get_message_type() if parsed else None
                
                # Validate
                validation_errors = self._schema.validate(data)
                
                # Generate ACK based on mode
                if self._ack_mode != "Never":
                    if validation_errors:
                        # Generate negative ACK
                        error_msg = "; ".join(str(e) for e in validation_errors[:3])
                        ack = self._schema.create_ack(parsed, "AE", error_msg)
                    else:
                        # Generate positive ACK
                        ack = self._schema.create_ack(parsed, "AA", "Message accepted")
            
            latency_ms = int((time.time() - start_time) * 1000)

            self._log.debug(
                "hl7_message_received",
                message_type=message_type,
                control_id=parsed.get_message_control_id() if parsed else None,
                valid=len(validation_errors) == 0,
            )

            # Store inbound message and get session_id + trace IDs
            session_id = None
            header_id = None
            body_id = None
            correlation_id = parsed.get_message_control_id() if parsed else None
            project_id = getattr(self, 'project_id', None)
            if project_id:
                status = "completed" if not validation_errors else "error"
                error_msg = "; ".join(str(e) for e in validation_errors[:3]) if validation_errors else None
                session_id, header_id, body_id = await _store_inbound_message(
                    project_id=project_id,
                    item_name=self.name,
                    raw_content=data,
                    ack_content=ack,
                    message_type=message_type,
                    status=status,
                    target_config_names=self.target_config_names,
                    latency_ms=latency_ms,
                    error_message=error_msg,
                    correlation_id=correlation_id,
                )

            # Create message envelope with session_id and trace IDs
            message = HL7Message(
                raw=data,
                parsed=parsed,
                ack=ack,
                received_at=received_at,
                source=self.name,
                validation_errors=validation_errors,
                session_id=session_id,
                correlation_id=correlation_id,
                header_id=header_id,
                body_id=body_id,
            )

            return message
        
        except Exception as e:
            self._log.error("hl7_message_parse_error", error=str(e))
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Generate error ACK if possible
            if self._schema and self._ack_mode != "Never":
                try:
                    # Try to create a minimal parsed view for ACK
                    parsed = self._schema.parse(data)
                    ack = self._schema.create_ack(parsed, "AR", f"Parse error: {e}")
                except Exception:
                    pass
            
            # Store error message and get session_id + trace IDs
            session_id = None
            header_id = None
            body_id = None
            project_id = getattr(self, 'project_id', None)
            if project_id:
                session_id, header_id, body_id = await _store_inbound_message(
                    project_id=project_id,
                    item_name=self.name,
                    raw_content=data,
                    ack_content=ack,
                    message_type=None,
                    status="error",
                    target_config_names=self.target_config_names,
                    latency_ms=latency_ms,
                    error_message=str(e),
                )

            # Create error message with session_id and trace IDs
            message = HL7Message(
                raw=data,
                parsed=None,
                ack=ack,
                received_at=received_at,
                source=self.name,
                error=str(e),
                session_id=session_id,
                header_id=header_id,
                body_id=body_id,
            )

            return message
    
    async def _process_message(self, message: Any) -> Any:
        """
        Process an HL7 message.
        
        Routes the message to configured targets.
        
        Args:
            message: HL7Message object
            
        Returns:
            Processing result
        """
        if not isinstance(message, HL7Message):
            return message
        
        # Check for errors
        if message.error:
            if self._bad_message_handler:
                # Route to bad message handler
                self._log.warning(
                    "hl7_bad_message",
                    error=message.error,
                    handler=self._bad_message_handler,
                )
                # TODO: Route to bad message handler
            return message
        
        # Route to targets
        targets = self.target_config_names
        if targets:
            self._log.debug(
                "hl7_routing_message",
                message_type=message.message_type,
                targets=targets,
            )
            await self.send_to_targets(message)
        
        return message


class HL7TCPOperation(BusinessOperation):
    """
    HL7v2 TCP Operation using MLLP protocol.
    
    Sends HL7v2 messages via MLLP/TCP to external systems and processes
    ACK responses according to configured ReplyCodeActions.
    
    This is the LI equivalent of IRIS EnsLib.HL7.Operation.TCPOperation.
    
    Settings (Host):
        MessageSchemaCategory: Schema category for validation (e.g., "2.4", "PKB")
        ReplyCodeActions: ACK code handling rules (e.g., ":?R=F,:?E=S,:*=S")
        ArchiveIO: Archive messages for debugging (default: false)
        AlertOnError: Send alert on errors (default: true)
        FailureTimeout: Timeout before marking as failed (default: -1, disabled)
        RetryInterval: Interval between retries in seconds (default: 5)
        AlertRetryGracePeriod: Grace period before alerting on retries (default: 0)
    
    Settings (Adapter):
        IPAddress: Remote host IP or hostname (required)
        Port: Remote TCP port (required)
        ConnectTimeout: Connection timeout in seconds (default: 10)
        AckTimeout: ACK wait timeout in seconds (default: 30)
        MaxRetries: Maximum send retries (default: 3)
    
    ReplyCodeActions Format:
        Pattern=Action pairs separated by commas
        Patterns: :AA, :AE, :AR, :?E (any error), :?R (any reject), :* (any)
        Actions: S (success), F (fail), R (retry), W (warning)
        
        Example: ":?R=F,:?E=S,:*=S"
            - Any reject (AR) = Fail
            - Any error (AE) = Success (log and continue)
            - Any other = Success
    
    Example IRIS Config:
        <Item Name="HL7.Out.TCP" Category="" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="IPAddress">192.168.1.100</Setting>
            <Setting Target="Adapter" Name="Port">2575</Setting>
            <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:*=S</Setting>
        </Item>
    """
    
    adapter_class = MLLPOutboundAdapter
    
    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )
        
        # HL7-specific state
        self._schema: HL7Schema | None = None
        self._reply_code_actions = self._parse_reply_code_actions(
            self.get_setting("Host", "ReplyCodeActions", ":*=S")
        )
        self._retry_interval = float(self.get_setting("Host", "RetryInterval", 5.0))
        self._failure_timeout = float(self.get_setting("Host", "FailureTimeout", -1))
        
        self._log = logger.bind(
            host="HL7TCPOperation",
            name=name,
            remote=f"{self.get_setting('Adapter', 'IPAddress')}:{self.get_setting('Adapter', 'Port')}",
        )
    
    def _parse_reply_code_actions(self, actions_str: str) -> list[tuple[str, str]]:
        """
        Parse ReplyCodeActions string into pattern-action pairs.
        
        Args:
            actions_str: ReplyCodeActions setting value
            
        Returns:
            List of (pattern, action) tuples
        """
        if not actions_str:
            return [("*", "S")]
        
        result = []
        for pair in actions_str.split(","):
            pair = pair.strip()
            if "=" in pair:
                pattern, action = pair.split("=", 1)
                pattern = pattern.strip().lstrip(":")
                action = action.strip().upper()
                result.append((pattern, action))
        
        return result if result else [("*", "S")]
    
    def _evaluate_ack_code(self, ack_code: str) -> str:
        """
        Evaluate ACK code against ReplyCodeActions.
        
        Args:
            ack_code: ACK code from response (AA, AE, AR, etc.)
            
        Returns:
            Action to take: S (success), F (fail), R (retry), W (warning)
        """
        for pattern, action in self._reply_code_actions:
            if pattern == "*":
                return action
            elif pattern == "?E" and ack_code in ("AE", "CE"):
                return action
            elif pattern == "?R" and ack_code in ("AR", "CR"):
                return action
            elif pattern == ack_code:
                return action
        
        return "S"  # Default to success
    
    async def on_start(self) -> None:
        """Initialize schema and start adapter."""
        # Load schema
        schema_name = self.get_setting("Host", "MessageSchemaCategory")
        if schema_name:
            self._schema = SchemaRegistry.get(schema_name)
            if not self._schema:
                self._schema = HL7Schema(name=schema_name)
                SchemaRegistry.register(self._schema)
        else:
            self._schema = HL7Schema(name="2.4")
        
        await super().on_start()
        
        self._log.info(
            "hl7_tcp_operation_started",
            remote_host=self.get_setting("Adapter", "IPAddress"),
            remote_port=self.get_setting("Adapter", "Port"),
            reply_code_actions=self._reply_code_actions,
        )
    
    async def on_message(self, message: Any) -> Any:
        """
        Send an HL7 message to the remote system.

        Args:
            message: HL7Message or raw bytes

        Returns:
            SendResult with ACK and action taken
        """
        # Extract raw bytes and session tracking IDs
        session_id = None
        correlation_id = None
        header_id = None

        if isinstance(message, HL7Message):
            data = message.raw
            session_id = getattr(message, 'session_id', None)
            correlation_id = getattr(message, 'correlation_id', None)
            header_id = getattr(message, 'header_id', None)
        elif isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
            session_id = getattr(message, 'session_id', None)
            correlation_id = getattr(message, 'correlation_id', None)
            header_id = getattr(message, 'header_id', None)
        else:
            data = str(message).encode("utf-8")
        
        # Send via adapter
        try:
            ack_bytes = await self._adapter.send(data)
            
            # Parse ACK
            ack_parsed = None
            ack_code = "AA"
            
            if self._schema and ack_bytes:
                try:
                    ack_parsed = self._schema.parse(ack_bytes)
                    ack_code = ack_parsed.get_field("MSA-1", "AA")
                except Exception as e:
                    self._log.warning("hl7_ack_parse_error", error=str(e))
            
            # Evaluate action
            action = self._evaluate_ack_code(ack_code)
            
            self._log.debug(
                "hl7_message_sent",
                ack_code=ack_code,
                action=action,
            )
            
            # Handle action
            if action == "F":
                raise HL7SendError(f"ACK code {ack_code} mapped to FAIL")
            elif action == "R":
                # Retry logic would be handled by the host's retry mechanism
                raise HL7RetryError(f"ACK code {ack_code} mapped to RETRY")
            elif action == "W":
                self._log.warning("hl7_ack_warning", ack_code=ack_code)
            
            # Store outbound message trace
            project_id = getattr(self, 'project_id', None)
            if project_id:
                import asyncio as _asyncio
                _asyncio.create_task(self._store_outbound_message(
                    project_id=project_id,
                    raw_content=data,
                    ack_content=ack_bytes,
                    status="sent",
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))
            
            return SendResult(
                success=True,
                ack_code=ack_code,
                ack_raw=ack_bytes,
                ack_parsed=ack_parsed,
                action=action,
            )
        
        except (HL7SendError, HL7RetryError) as e:
            # Store failed message trace
            project_id = getattr(self, 'project_id', None)
            if project_id:
                import asyncio as _asyncio
                _asyncio.create_task(self._store_outbound_message(
                    project_id=project_id,
                    raw_content=data,
                    ack_content=None,
                    status="failed",
                    error_message=str(e),
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))
            raise
        
        except Exception as e:
            self._log.error("hl7_send_error", error=str(e))
            # Store failed message trace
            project_id = getattr(self, 'project_id', None)
            if project_id:
                import asyncio as _asyncio
                _asyncio.create_task(self._store_outbound_message(
                    project_id=project_id,
                    raw_content=data,
                    ack_content=None,
                    status="failed",
                    error_message=str(e),
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))
            raise HL7SendError(f"Send failed: {e}")
    
    async def _store_outbound_message(
        self,
        project_id: UUID,
        raw_content: bytes,
        ack_content: bytes | None,
        status: str,
        error_message: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        header_id: "UUID | None" = None,
    ) -> None:
        """
        Store outbound message using IRIS-convention per-leg trace model.

        1. Updates the existing header status (the leg that caused this send)
        2. If ACK received, creates a Response header linking back
        """
        try:
            from Engine.api.services.message_store import (
                store_message_body, store_message_header, update_header_status,
            )

            is_err = status in ('failed', 'error')

            # Step 1: Update the header that caused this leg
            if header_id:
                await update_header_status(
                    header_id=header_id,
                    status='Completed' if not is_err else 'Error',
                    is_error=is_err,
                    error_status=error_message,
                )

            # Step 2: If ACK received, create a Response header
            if ack_content and session_id:
                ack_body_id = await store_message_body(
                    raw_content=ack_content,
                    body_class_name='EnsLib.HL7.Message',
                    content_type='application/hl7-v2+er7',
                )
                await store_message_header(
                    project_id=project_id,
                    session_id=session_id,
                    source_config_name=self.name,
                    target_config_name=getattr(self, '_source_for_response', self.name),
                    source_business_type='operation',
                    target_business_type='process',
                    message_body_id=ack_body_id,
                    parent_header_id=header_id,
                    corresponding_header_id=header_id,
                    message_type='ACK',
                    body_class_name='EnsLib.HL7.Message',
                    type='Response',
                    status='Completed',
                    correlation_id=correlation_id,
                )

        except Exception as e:
            self._log.warning("outbound_message_storage_failed", error=str(e))


class HL7Message:
    """
    HL7 message container.
    
    Holds raw bytes, parsed view, ACK, and metadata.
    
    IRIS equivalent: EnsLib.HL7.Message (the in-memory message object).
    The header_id and body_id fields link to the persisted trace tables
    (message_headers / message_bodies) for Visual Trace support.
    """
    
    def __init__(
        self,
        raw: bytes,
        parsed: HL7ParsedView | None = None,
        ack: bytes | None = None,
        received_at: datetime | None = None,
        source: str | None = None,
        validation_errors: list | None = None,
        error: str | None = None,
        session_id: str | None = None,
        correlation_id: str | None = None,
        header_id: "UUID | None" = None,
        body_id: "UUID | None" = None,
    ):
        self.raw = raw
        self.parsed = parsed
        self.ack = ack
        self.received_at = received_at or datetime.now(timezone.utc)
        self.source = source
        self.validation_errors = validation_errors or []
        self.error = error
        self.session_id = session_id  # Session tracking for message flow
        self.correlation_id = correlation_id  # Correlation for ACKs/responses
        self.header_id = header_id  # Persisted header ID for parent chain
        self.body_id = body_id  # Persisted body ID for content sharing
    
    @property
    def message_type(self) -> str | None:
        """Get message type (e.g., ADT_A01)."""
        if self.parsed:
            return self.parsed.get_message_type()
        return None
    
    @property
    def message_control_id(self) -> str | None:
        """Get message control ID."""
        if self.parsed:
            return self.parsed.get_message_control_id()
        return None
    
    @property
    def is_valid(self) -> bool:
        """Check if message is valid."""
        return self.error is None and len(self.validation_errors) == 0
    
    def get_field(self, path: str, default: Any = None) -> Any:
        """Get a field value from the parsed message."""
        if self.parsed:
            return self.parsed.get_field(path, default)
        return default
    
    def with_header_id(self, header_id: "UUID") -> "HL7Message":
        """Return a copy with updated header_id for downstream propagation."""
        return HL7Message(
            raw=self.raw,
            parsed=self.parsed,
            ack=self.ack,
            received_at=self.received_at,
            source=self.source,
            validation_errors=self.validation_errors,
            error=self.error,
            session_id=self.session_id,
            correlation_id=self.correlation_id,
            header_id=header_id,
            body_id=self.body_id,
        )

    def __repr__(self) -> str:
        return f"HL7Message(type={self.message_type}, id={self.message_control_id}, valid={self.is_valid})"


class SendResult:
    """
    Result of sending an HL7 message.
    """
    
    def __init__(
        self,
        success: bool,
        ack_code: str | None = None,
        ack_raw: bytes | None = None,
        ack_parsed: HL7ParsedView | None = None,
        action: str = "S",
        error: str | None = None,
    ):
        self.success = success
        self.ack_code = ack_code
        self.ack_raw = ack_raw
        self.ack_parsed = ack_parsed
        self.action = action
        self.error = error
    
    def __repr__(self) -> str:
        return f"SendResult(success={self.success}, ack_code={self.ack_code}, action={self.action})"


class HL7SendError(Exception):
    """Error sending HL7 message."""
    pass


class HL7RetryError(Exception):
    """HL7 message should be retried."""
    pass


# =========================================================================
# HL7 File Service — IRIS EnsLib.HL7.Service.FileService
# =========================================================================

class HL7FileService(HL7TCPService):
    """
    HL7v2 File Service — polls a directory for HL7 message files.

    Inherits all HL7 parsing, validation, ACK generation, and message trace
    logic from HL7TCPService. Only the adapter is different: InboundFileAdapter
    instead of MLLPInboundAdapter.

    IRIS equivalent: EnsLib.HL7.Service.FileService
        extends EnsLib.HL7.Service.Standard (shared HL7 logic)
        uses EnsLib.File.InboundAdapter (file polling)

    Rhapsody equivalent: File Communication Point (Input) + HL7 parser
    Mirth equivalent: File Reader connector + HL7v2 data type

    Settings (Host):
        MessageSchemaCategory: Schema category for validation (e.g., "2.4")
        TargetConfigNames: Comma-separated list of target hosts
        AckMode: ACK generation mode ("Never" recommended for file — no one to ACK to)
        BadMessageHandler: Target for invalid messages

    Settings (Adapter):
        FilePath:     Directory to poll for inbound HL7 files (required)
        FileSpec:     Glob pattern (default: *.hl7)
        PollInterval: Seconds between scans (default: 5)
        ArchivePath:  Directory for processed files (default: archive)

    Example IRIS Config:
        <Item Name="HL7.In.File" ClassName="EnsLib.HL7.Service.FileService" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="FilePath">/data/hl7/inbound</Setting>
            <Setting Target="Adapter" Name="FileSpec">*.hl7</Setting>
            <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
            <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
        </Item>
    """

    adapter_class = InboundFileAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        # Default AckMode to "Never" for file services (no TCP peer to ACK)
        if host_settings and "AckMode" not in host_settings:
            host_settings["AckMode"] = "Never"
        elif not host_settings:
            host_settings = {"AckMode": "Never"}

        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        self._log = logger.bind(
            host="HL7FileService",
            name=name,
            schema=self.message_schema_category,
        )


# =========================================================================
# HL7 File Operation — IRIS EnsLib.HL7.Operation.FileOperation
# =========================================================================

class HL7FileOperation(HL7TCPOperation):
    """
    HL7v2 File Operation — writes HL7 messages to files.

    Inherits all HL7 schema loading, ACK evaluation, and message trace
    logic from HL7TCPOperation. Only the adapter is different: OutboundFileAdapter
    instead of MLLPOutboundAdapter.

    Note: File operations do NOT receive ACKs (no TCP peer). The send()
    returns the file path as bytes. The operation marks the header as
    Completed on successful write.

    IRIS equivalent: EnsLib.HL7.Operation.FileOperation
        extends EnsLib.HL7.Operation.BatchStandard
        uses EnsLib.File.OutboundAdapter

    Settings (Host):
        MessageSchemaCategory: Schema category (e.g., "2.4")
        ReplyCodeActions: Not applicable for file (no ACK)

    Settings (Adapter):
        FilePath: Directory to write outbound HL7 files (required)
        Filename: Filename pattern (default: msg_%timestamp%_%id%.hl7)
        Overwrite: "error"|"overwrite"|"append" (default: error)

    Example IRIS Config:
        <Item Name="HL7.Out.File" ClassName="EnsLib.HL7.Operation.FileOperation" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="FilePath">/data/hl7/outbound</Setting>
            <Setting Target="Adapter" Name="Filename">%type%_%timestamp%.hl7</Setting>
        </Item>
    """

    adapter_class = OutboundFileAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        self._log = logger.bind(
            host="HL7FileOperation",
            name=name,
        )

    async def on_message(self, message: Any) -> Any:
        """
        Send HL7 message to file.

        File operations don't receive ACKs, so we write the file
        and mark the header as Completed.
        """
        session_id = None
        correlation_id = None
        header_id = None

        if isinstance(message, HL7Message):
            data = message.raw
            session_id = getattr(message, 'session_id', None)
            correlation_id = getattr(message, 'correlation_id', None)
            header_id = getattr(message, 'header_id', None)
        elif isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
            session_id = getattr(message, 'session_id', None)
            correlation_id = getattr(message, 'correlation_id', None)
            header_id = getattr(message, 'header_id', None)
        else:
            data = str(message).encode("utf-8")

        try:
            # Write to file via adapter
            file_path = await self._adapter.send(message)

            self._log.debug("hl7_file_written", file_path=file_path)

            # Store outbound trace (no ACK for file)
            project_id = getattr(self, 'project_id', None)
            if project_id:
                import asyncio as _asyncio
                _asyncio.create_task(self._store_outbound_message(
                    project_id=project_id,
                    raw_content=data,
                    ack_content=None,
                    status="sent",
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))

            return SendResult(
                success=True,
                ack_code=None,
                ack_raw=None,
                action="S",
            )

        except Exception as e:
            self._log.error("hl7_file_write_error", error=str(e))

            project_id = getattr(self, 'project_id', None)
            if project_id:
                import asyncio as _asyncio
                _asyncio.create_task(self._store_outbound_message(
                    project_id=project_id,
                    raw_content=data,
                    ack_content=None,
                    status="failed",
                    error_message=str(e),
                    session_id=session_id,
                    correlation_id=correlation_id,
                    header_id=header_id,
                ))
            raise HL7SendError(f"File write failed: {e}")


# =========================================================================
# HL7 HTTP Service — IRIS EnsLib.HL7.Service.HTTPService
# =========================================================================

class HL7HTTPService(HL7TCPService):
    """
    HL7v2 HTTP Service — receives HL7 messages via HTTP POST.

    Inherits all HL7 parsing, validation, ACK generation, and message trace
    logic from HL7TCPService. Uses InboundHTTPAdapter instead of MLLP.

    The HTTP response body contains the HL7 ACK message.
    Content-Type is application/hl7-v2+er7.

    IRIS equivalent: EnsLib.HL7.Service.HTTPService
        extends EnsLib.HTTP.Service + EnsLib.HL7.Service.Standard
        uses EnsLib.HTTP.InboundAdapter

    Rhapsody equivalent: HTTP Communication Point (Input) + HL7 parser
    Mirth equivalent: HTTP Listener connector + HL7v2 data type

    Settings (Host):
        MessageSchemaCategory: Schema category for validation (e.g., "2.4")
        TargetConfigNames: Comma-separated list of target hosts
        AckMode: ACK generation mode (default: "Immediate")
        BadMessageHandler: Target for invalid messages

    Settings (Adapter):
        Port: HTTP port to listen on (required)
        Host: IP address to bind to (default: 0.0.0.0)
        AllowedMethods: HTTP methods (default: POST)
        SSLCertFile: Path to SSL certificate (optional)
        SSLKeyFile: Path to SSL key (optional)

    Example IRIS Config:
        <Item Name="HL7.In.HTTP" ClassName="EnsLib.HL7.Service.HTTPService" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="Port">9380</Setting>
            <Setting Target="Host" Name="MessageSchemaCategory">2.4</Setting>
            <Setting Target="Host" Name="TargetConfigNames">HL7.Router</Setting>
        </Item>
    """

    adapter_class = InboundHTTPAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        self._log = logger.bind(
            host="HL7HTTPService",
            name=name,
            schema=self.message_schema_category,
        )

    async def on_start(self) -> None:
        """Initialize schema and set up HTTP request handler."""
        await super().on_start()

        # Set up the HTTP adapter to use our custom request handler
        if isinstance(self._adapter, InboundHTTPAdapter):
            self._adapter.set_request_handler(self._handle_http_request)

    async def _handle_http_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Handle an inbound HTTP request containing an HL7 message.

        Extracts the HL7 message from the HTTP body, processes it
        using the standard HL7 pipeline, and returns the ACK as
        the HTTP response body.
        """
        data = request.body

        if not data:
            return HTTPResponse(
                status_code=400,
                body=b"Empty request body",
                content_type="text/plain",
            )

        # Process through standard HL7 pipeline
        try:
            message = await self.on_message_received(data)

            # Submit to queue for downstream routing
            await self.submit(message)

            # Return ACK as HTTP response
            if isinstance(message, HL7Message) and message.ack:
                return HTTPResponse(
                    status_code=200,
                    body=message.ack,
                    content_type="application/hl7-v2+er7",
                )
            else:
                return HTTPResponse(
                    status_code=200,
                    body=b"OK",
                    content_type="text/plain",
                )

        except Exception as e:
            self._log.error("hl7_http_processing_error", error=str(e))
            return HTTPResponse(
                status_code=500,
                body=f"Processing error: {e}".encode(),
                content_type="text/plain",
            )


# =========================================================================
# HL7 HTTP Operation — IRIS EnsLib.HL7.Operation.HTTPOperation
# =========================================================================

class HL7HTTPOperation(HL7TCPOperation):
    """
    HL7v2 HTTP Operation — sends HL7 messages via HTTP POST.

    Inherits all HL7 schema loading, ACK evaluation, and message trace
    logic from HL7TCPOperation. Uses OutboundHTTPAdapter instead of MLLP.

    The HTTP request body contains the HL7 message.
    The HTTP response body is expected to contain the HL7 ACK.

    IRIS equivalent: EnsLib.HL7.Operation.HTTPOperation
        extends EnsLib.HL7.Operation.Standard
        uses EnsLib.HTTP.OutboundAdapter

    Settings (Host):
        MessageSchemaCategory: Schema category (e.g., "2.4")
        ReplyCodeActions: ACK code handling rules

    Settings (Adapter):
        URL: Target URL for HTTP POST (required)
        ContentType: Content-Type header (default: application/hl7-v2+er7)
        ConnectTimeout: Connection timeout (default: 10)
        ResponseTimeout: Response timeout (default: 30)
        MaxRetries: Maximum retries (default: 3)

    Example IRIS Config:
        <Item Name="HL7.Out.HTTP" ClassName="EnsLib.HL7.Operation.HTTPOperation" PoolSize="1" Enabled="true">
            <Setting Target="Adapter" Name="URL">http://remote:8080/hl7</Setting>
            <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:*=S</Setting>
        </Item>
    """

    adapter_class = OutboundHTTPAdapter

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        # Default ContentType for HL7 over HTTP
        if adapter_settings and "ContentType" not in adapter_settings:
            adapter_settings["ContentType"] = "application/hl7-v2+er7"
        elif not adapter_settings:
            adapter_settings = {"ContentType": "application/hl7-v2+er7"}

        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        self._log = logger.bind(
            host="HL7HTTPOperation",
            name=name,
            url=self.get_setting("Adapter", "URL"),
        )


# =========================================================================
# ClassRegistry Registration
# =========================================================================

# Register core classes with ClassRegistry (internal — protected namespace)
ClassRegistry._register_internal("li.hosts.hl7.HL7TCPService", HL7TCPService)
ClassRegistry._register_internal("li.hosts.hl7.HL7TCPOperation", HL7TCPOperation)
ClassRegistry._register_internal("li.hosts.hl7.HL7FileService", HL7FileService)
ClassRegistry._register_internal("li.hosts.hl7.HL7FileOperation", HL7FileOperation)
ClassRegistry._register_internal("li.hosts.hl7.HL7HTTPService", HL7HTTPService)
ClassRegistry._register_internal("li.hosts.hl7.HL7HTTPOperation", HL7HTTPOperation)

# IRIS compatibility aliases
ClassRegistry.register_alias("EnsLib.HL7.Service.TCPService", "li.hosts.hl7.HL7TCPService")
ClassRegistry.register_alias("EnsLib.HL7.Operation.TCPOperation", "li.hosts.hl7.HL7TCPOperation")
ClassRegistry.register_alias("EnsLib.HL7.Service.FileService", "li.hosts.hl7.HL7FileService")
ClassRegistry.register_alias("EnsLib.HL7.Operation.FileOperation", "li.hosts.hl7.HL7FileOperation")
ClassRegistry.register_alias("EnsLib.HL7.Service.HTTPService", "li.hosts.hl7.HL7HTTPService")
ClassRegistry.register_alias("EnsLib.HL7.Operation.HTTPOperation", "li.hosts.hl7.HL7HTTPOperation")
