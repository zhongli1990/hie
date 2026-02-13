"""
Portal Message Storage Service

Provides a centralized service for storing messages in the portal_messages table.
This service can be called from adapters, hosts, or API endpoints.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import asyncpg
import structlog

logger = structlog.get_logger(__name__)

# Global database pool reference (set by API server)
_db_pool: asyncpg.Pool | None = None


def set_db_pool(pool: asyncpg.Pool) -> None:
    """Set the global database pool for message storage."""
    global _db_pool
    _db_pool = pool
    logger.info("message_store_pool_set")


def get_db_pool() -> asyncpg.Pool | None:
    """Get the global database pool."""
    return _db_pool


def extract_message_type(raw_content: bytes) -> str | None:
    """Extract HL7 message type from raw content."""
    try:
        content = raw_content.decode('utf-8', errors='replace')
        # Look for MSH segment and extract message type (field 9)
        match = re.search(r'MSH\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|([^|]+)', content)
        if match:
            return match.group(1).split('^')[0] + ('^' + match.group(1).split('^')[1] if '^' in match.group(1) else '')
        return None
    except:
        return None


def extract_ack_type(ack_content: bytes) -> str | None:
    """Extract ACK type from ACK message (MSA segment field 1)."""
    try:
        content = ack_content.decode('utf-8', errors='replace')
        # Look for MSA segment and extract acknowledgment code (field 1)
        match = re.search(r'MSA\|([A-Z]{2})', content)
        if match:
            return match.group(1)
        return None
    except:
        return None


async def store_message(
    project_id: UUID,
    item_name: str,
    item_type: str,
    direction: str,
    raw_content: bytes | None = None,
    message_type: str | None = None,
    correlation_id: str | None = None,
    session_id: str | None = None,
    body_class_name: str | None = None,
    schema_name: str | None = None,
    schema_namespace: str | None = None,
    status: str = "received",
    source_item: str | None = None,
    destination_item: str | None = None,
    remote_host: str | None = None,
    remote_port: int | None = None,
    metadata: dict | None = None,
) -> UUID | None:
    """
    Store a message in the portal_messages table.
    
    Returns the message ID if successful, None otherwise.
    """
    pool = get_db_pool()
    if not pool:
        logger.warning("message_store_no_pool", item_name=item_name)
        return None
    
    # Auto-detect message type if not provided
    if not message_type and raw_content:
        message_type = extract_message_type(raw_content)
    
    # Create content preview
    content_preview = None
    content_size = 0
    if raw_content:
        content_size = len(raw_content)
        try:
            preview = raw_content.decode('utf-8', errors='replace')[:500]
            content_preview = preview.replace('\r', '\\r').replace('\n', '\\n')
        except:
            content_preview = f"[Binary data: {content_size} bytes]"
    
    # Auto-populate body_class_name and schema_name if not provided
    if not body_class_name:
        body_class_name = "Engine.li.messages.hl7.HL7Message" if message_type else "Engine.core.message.GenericMessage"
    if not schema_name:
        schema_name = message_type or "GenericMessage"
    if not schema_namespace:
        schema_namespace = "urn:hl7-org:v2" if message_type and ("HL7" in message_type or "ADT" in message_type or "ORU" in message_type) else "urn:hie:generic"

    try:
        import json
        query = """
            INSERT INTO portal_messages (
                project_id, item_name, item_type, direction, message_type,
                correlation_id, session_id, body_class_name, schema_name, schema_namespace,
                status, raw_content, content_preview, content_size,
                source_item, destination_item, remote_host, remote_port, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            RETURNING id
        """
        row = await pool.fetchrow(
            query, project_id, item_name, item_type, direction, message_type,
            correlation_id, session_id, body_class_name, schema_name, schema_namespace,
            status, raw_content, content_preview, content_size,
            source_item, destination_item, remote_host, remote_port,
            json.dumps(metadata or {})
        )
        
        msg_id = row['id'] if row else None
        logger.debug("message_stored", message_id=str(msg_id), item_name=item_name, direction=direction)
        return msg_id
    
    except Exception as e:
        logger.error("message_store_failed", error=str(e), item_name=item_name)
        return None


async def update_message_status(
    message_id: UUID,
    status: str,
    ack_content: bytes | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
) -> bool:
    """
    Update message status after processing.
    
    Returns True if successful.
    """
    pool = get_db_pool()
    if not pool:
        return False
    
    # Extract ACK type if ACK content provided
    ack_type = None
    if ack_content:
        ack_type = extract_ack_type(ack_content)
    
    completed_at = None
    if status in ('sent', 'completed', 'failed', 'error'):
        completed_at = datetime.now(timezone.utc)
    
    try:
        query = """
            UPDATE portal_messages
            SET status = $2, ack_content = $3, ack_type = $4, 
                error_message = $5, latency_ms = $6, completed_at = $7
            WHERE id = $1
        """
        await pool.execute(
            query, message_id, status, ack_content, ack_type,
            error_message, latency_ms, completed_at
        )
        
        logger.debug("message_status_updated", message_id=str(message_id), status=status)
        return True
    
    except Exception as e:
        logger.error("message_status_update_failed", error=str(e), message_id=str(message_id))
        return False


async def store_and_complete_message(
    project_id: UUID,
    item_name: str,
    item_type: str,
    direction: str,
    raw_content: bytes,
    status: str,
    ack_content: bytes | None = None,
    error_message: str | None = None,
    latency_ms: int | None = None,
    source_item: str | None = None,
    destination_item: str | None = None,
    remote_host: str | None = None,
    remote_port: int | None = None,
    correlation_id: str | None = None,
    session_id: str | None = None,
    body_class_name: str | None = None,
    schema_name: str | None = None,
    schema_namespace: str | None = None,
) -> UUID | None:
    """
    Store a message and immediately set its final status.
    
    Convenience method for cases where the message is processed synchronously.
    """
    pool = get_db_pool()
    if not pool:
        return None
    
    # Auto-detect message type
    message_type = extract_message_type(raw_content) if raw_content else None
    
    # Extract ACK type
    ack_type = extract_ack_type(ack_content) if ack_content else None
    
    # Create content preview
    content_preview = None
    content_size = 0
    if raw_content:
        content_size = len(raw_content)
        try:
            preview = raw_content.decode('utf-8', errors='replace')[:500]
            content_preview = preview.replace('\r', '\\r').replace('\n', '\\n')
        except:
            content_preview = f"[Binary data: {content_size} bytes]"
    
    completed_at = datetime.now(timezone.utc) if status in ('sent', 'completed', 'failed', 'error') else None

    # Auto-populate body_class_name and schema_name if not provided
    if not body_class_name:
        body_class_name = "Engine.li.messages.hl7.HL7Message" if message_type else "Engine.core.message.GenericMessage"
    if not schema_name:
        schema_name = message_type or "GenericMessage"
    if not schema_namespace:
        schema_namespace = "urn:hl7-org:v2" if message_type and ("HL7" in message_type or "ADT" in message_type or "ORU" in message_type) else "urn:hie:generic"

    try:
        import json
        query = """
            INSERT INTO portal_messages (
                project_id, item_name, item_type, direction, message_type,
                correlation_id, session_id, body_class_name, schema_name, schema_namespace,
                status, raw_content, content_preview, content_size,
                source_item, destination_item, remote_host, remote_port,
                ack_content, ack_type, error_message, latency_ms, completed_at, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
            RETURNING id
        """
        row = await pool.fetchrow(
            query, project_id, item_name, item_type, direction, message_type,
            correlation_id, session_id, body_class_name, schema_name, schema_namespace,
            status, raw_content, content_preview, content_size,
            source_item, destination_item, remote_host, remote_port,
            ack_content, ack_type, error_message, latency_ms, completed_at,
            json.dumps({})
        )
        
        msg_id = row['id'] if row else None
        logger.debug("message_stored_complete", message_id=str(msg_id), item_name=item_name, status=status)
        return msg_id
    
    except Exception as e:
        logger.error("message_store_complete_failed", error=str(e), item_name=item_name)
        return None


# =============================================================================
# NEW: IRIS-Convention Message Storage (message_headers + message_bodies)
# =============================================================================


def _extract_hl7_fields(raw_content: bytes) -> dict:
    """Extract HL7v2 MSH fields from raw content for indexed columns."""
    result = {}
    try:
        text = raw_content.decode('utf-8', errors='replace')
        lines = re.split(r'[\r\n]+', text)
        for line in lines:
            if line.startswith('MSH|'):
                fields = line.split('|')
                if len(fields) > 2:
                    result['hl7_sending_app'] = fields[2][:100] if fields[2] else None
                if len(fields) > 3:
                    result['hl7_sending_fac'] = fields[3][:100] if fields[3] else None
                if len(fields) > 4:
                    result['hl7_receiving_app'] = fields[4][:100] if fields[4] else None
                if len(fields) > 5:
                    result['hl7_receiving_fac'] = fields[5][:100] if fields[5] else None
                if len(fields) > 8:
                    result['hl7_message_type'] = fields[8][:50] if fields[8] else None
                if len(fields) > 9:
                    result['hl7_control_id'] = fields[9][:100] if fields[9] else None
                if len(fields) > 11:
                    result['hl7_version'] = fields[11][:10] if fields[11] else None
                # Build doc_type like IRIS: "2.4:ADT_A01"
                if result.get('hl7_version') and result.get('hl7_message_type'):
                    msg_type = result['hl7_message_type'].replace('^', '_').split('_')
                    if len(msg_type) >= 2:
                        result['hl7_doc_type'] = f"{result['hl7_version']}:{msg_type[0]}_{msg_type[1]}"
                break
    except Exception:
        pass
    return result


def _make_content_preview(raw_content: bytes) -> str | None:
    """Create a text preview of raw content for UI display."""
    if not raw_content:
        return None
    try:
        preview = raw_content.decode('utf-8', errors='replace')[:500]
        return preview.replace('\r', '\\r').replace('\n', '\\n')
    except Exception:
        return f"[Binary data: {len(raw_content)} bytes]"


async def store_message_body(
    raw_content: bytes,
    body_class_name: str = 'Ens.MessageBody',
    content_type: str = 'application/octet-stream',
    **protocol_fields,
) -> UUID | None:
    """
    Store message content in message_bodies table.

    Returns the body_id. If a body with the same checksum already exists,
    returns the existing body_id (dedup).

    IRIS equivalent: Saving an Ens.MessageBody / EnsLib.HL7.Message object.
    """
    pool = get_db_pool()
    if not pool:
        logger.warning("message_body_store_no_pool")
        return None

    checksum = hashlib.sha256(raw_content).hexdigest()
    content_size = len(raw_content)
    content_preview = _make_content_preview(raw_content)

    # Auto-extract HL7 fields if this is an HL7 message
    hl7_fields = {}
    if body_class_name == 'EnsLib.HL7.Message':
        hl7_fields = _extract_hl7_fields(raw_content)

    # Merge explicit protocol_fields over auto-extracted
    hl7_fields.update({k: v for k, v in protocol_fields.items() if v is not None})

    try:
        # Dedup: check if body with same checksum exists
        existing = await pool.fetchval(
            "SELECT id FROM message_bodies WHERE checksum = $1 LIMIT 1",
            checksum,
        )
        if existing:
            logger.debug("message_body_dedup", checksum=checksum[:12], body_id=str(existing))
            return existing

        query = """
            INSERT INTO message_bodies (
                body_class_name, content_type, raw_content, content_preview,
                content_size, checksum,
                hl7_version, hl7_doc_type, hl7_message_type, hl7_control_id,
                hl7_sending_app, hl7_sending_fac, hl7_receiving_app, hl7_receiving_fac,
                fhir_version, fhir_resource_type, fhir_resource_id,
                http_method, http_url, original_filename,
                metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11, $12, $13, $14,
                $15, $16, $17,
                $18, $19, $20,
                $21
            ) RETURNING id
        """
        import json
        row = await pool.fetchrow(
            query,
            body_class_name, content_type, raw_content, content_preview,
            content_size, checksum,
            hl7_fields.get('hl7_version'),
            hl7_fields.get('hl7_doc_type'),
            hl7_fields.get('hl7_message_type'),
            hl7_fields.get('hl7_control_id'),
            hl7_fields.get('hl7_sending_app'),
            hl7_fields.get('hl7_sending_fac'),
            hl7_fields.get('hl7_receiving_app'),
            hl7_fields.get('hl7_receiving_fac'),
            protocol_fields.get('fhir_version'),
            protocol_fields.get('fhir_resource_type'),
            protocol_fields.get('fhir_resource_id'),
            protocol_fields.get('http_method'),
            protocol_fields.get('http_url'),
            protocol_fields.get('original_filename'),
            json.dumps(protocol_fields.get('metadata', {})),
        )

        body_id = row['id'] if row else None
        logger.debug("message_body_stored", body_id=str(body_id), cls=body_class_name, size=content_size)
        return body_id

    except Exception as e:
        logger.error("message_body_store_failed", error=str(e), cls=body_class_name)
        return None


async def store_message_header(
    project_id: UUID,
    session_id: str,
    source_config_name: str,
    target_config_name: str,
    source_business_type: str,
    target_business_type: str,
    message_body_id: UUID | None = None,
    parent_header_id: UUID | None = None,
    corresponding_header_id: UUID | None = None,
    super_session_id: str | None = None,
    message_type: str | None = None,
    body_class_name: str = 'Ens.MessageBody',
    type: str = 'Request',
    invocation: str = 'Queue',
    priority: str = 'Async',
    status: str = 'Created',
    is_error: bool = False,
    error_status: str | None = None,
    description: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> UUID | None:
    """
    Store one message leg in message_headers table.

    Returns the header_id. Each call = one arrow on the Visual Trace.

    IRIS equivalent: Creating an Ens.MessageHeader row when a message
    crosses from one config item to another.
    """
    pool = get_db_pool()
    if not pool:
        logger.warning("message_header_store_no_pool")
        return None

    try:
        import json
        query = """
            INSERT INTO message_headers (
                project_id, session_id, parent_header_id, corresponding_header_id,
                super_session_id,
                source_config_name, target_config_name,
                source_business_type, target_business_type,
                message_type, body_class_name, message_body_id,
                type, invocation, priority,
                status, is_error, error_status,
                description, correlation_id, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
            ) RETURNING id
        """
        row = await pool.fetchrow(
            query,
            project_id, session_id, parent_header_id, corresponding_header_id,
            super_session_id,
            source_config_name, target_config_name,
            source_business_type, target_business_type,
            message_type, body_class_name, message_body_id,
            type, invocation, priority,
            status, is_error, error_status,
            description, correlation_id, json.dumps(metadata or {}),
        )

        header_id = row['id'] if row else None
        logger.debug(
            "message_header_stored",
            header_id=str(header_id),
            session=session_id,
            source=source_config_name,
            target=target_config_name,
        )
        return header_id

    except Exception as e:
        logger.error(
            "message_header_store_failed", error=str(e),
            source=source_config_name, target=target_config_name,
        )
        return None


async def update_header_status(
    header_id: UUID,
    status: str,
    is_error: bool = False,
    error_status: str | None = None,
) -> bool:
    """
    Update a header's status and set time_processed.

    Called when a message leg completes (sent, completed, failed).
    """
    pool = get_db_pool()
    if not pool:
        return False

    try:
        await pool.execute(
            """
            UPDATE message_headers
            SET status = $2, is_error = $3, error_status = $4,
                time_processed = NOW()
            WHERE id = $1
            """,
            header_id, status, is_error, error_status,
        )
        logger.debug("header_status_updated", header_id=str(header_id), status=status)
        return True

    except Exception as e:
        logger.error("header_status_update_failed", error=str(e), header_id=str(header_id))
        return False


def get_business_type(host) -> str:
    """Determine the business type of a host (service/process/operation)."""
    from Engine.li.hosts.base import BusinessService, BusinessProcess, BusinessOperation
    if isinstance(host, BusinessService):
        return 'service'
    elif isinstance(host, BusinessProcess):
        return 'process'
    elif isinstance(host, BusinessOperation):
        return 'operation'
    return 'process'
