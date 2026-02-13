"""
Portal Message Storage Service

Provides a centralized service for storing messages in the portal_messages table.
This service can be called from adapters, hosts, or API endpoints.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

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
