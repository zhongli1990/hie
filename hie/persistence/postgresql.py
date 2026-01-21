"""
PostgreSQL Storage - Durable storage for production environments.

Provides reliable, ACID-compliant message storage with full query capabilities.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg
import structlog

from hie.core.message import Message, MessageState
from hie.persistence.base import MessageStore, StateStore, MessageQuery

logger = structlog.get_logger(__name__)


# SQL for creating tables
CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS hie_messages (
    message_id UUID PRIMARY KEY,
    correlation_id UUID NOT NULL,
    causation_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    message_type VARCHAR(255),
    priority VARCHAR(20) NOT NULL,
    state VARCHAR(50) NOT NULL,
    route_id VARCHAR(255),
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(255),
    retry_count INTEGER NOT NULL DEFAULT 0,
    content_type VARCHAR(255) NOT NULL,
    encoding VARCHAR(50) NOT NULL,
    payload_size INTEGER NOT NULL,
    raw_payload BYTEA NOT NULL,
    envelope_json JSONB NOT NULL,
    properties_json JSONB,
    stored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_messages_correlation ON hie_messages(correlation_id);
CREATE INDEX IF NOT EXISTS idx_messages_route ON hie_messages(route_id);
CREATE INDEX IF NOT EXISTS idx_messages_source ON hie_messages(source);
CREATE INDEX IF NOT EXISTS idx_messages_state ON hie_messages(state);
CREATE INDEX IF NOT EXISTS idx_messages_type ON hie_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_created ON hie_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_expires ON hie_messages(expires_at) WHERE expires_at IS NOT NULL;
"""

CREATE_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS hie_state (
    key VARCHAR(512) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_state_expires ON hie_state(expires_at) WHERE expires_at IS NOT NULL;
"""


class PostgreSQLMessageStore(MessageStore):
    """
    PostgreSQL-backed message store.
    
    Features:
    - ACID transactions
    - Full-text search on message content
    - Efficient batch operations
    - Connection pooling
    """
    
    def __init__(
        self,
        dsn: str | None = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "hie",
        user: str = "hie",
        password: str = "",
        min_connections: int = 5,
        max_connections: int = 20,
    ) -> None:
        self._dsn = dsn
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._min_connections = min_connections
        self._max_connections = max_connections
        
        self._pool: asyncpg.Pool | None = None
        self._logger = logger.bind(component="postgresql_message_store")
    
    async def connect(self) -> None:
        """Establish connection pool and create tables."""
        if self._dsn:
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=self._min_connections,
                max_size=self._max_connections,
            )
        else:
            self._pool = await asyncpg.create_pool(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
                min_size=self._min_connections,
                max_size=self._max_connections,
            )
        
        # Create tables
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_MESSAGES_TABLE)
        
        self._logger.info("postgresql_connected", database=self._database)
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._logger.info("postgresql_disconnected")
    
    async def store(self, message: Message) -> None:
        """Store a message."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        env = message.envelope
        pay = message.payload
        
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO hie_messages (
                    message_id, correlation_id, causation_id, created_at, expires_at,
                    message_type, priority, state, route_id, source, destination,
                    retry_count, content_type, encoding, payload_size, raw_payload,
                    envelope_json, properties_json
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (message_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    retry_count = EXCLUDED.retry_count,
                    updated_at = NOW(),
                    version = hie_messages.version + 1
                """,
                env.message_id,
                env.correlation_id,
                env.causation_id,
                env.created_at,
                env.expires_at,
                env.message_type,
                env.priority.value,
                env.state.value,
                env.routing.route_id,
                env.routing.source,
                env.routing.destination,
                env.retry_count,
                pay.content_type,
                pay.encoding,
                pay.size,
                pay.raw,
                json.dumps(env.model_dump(mode="json")),
                json.dumps({k: v.to_dict() for k, v in pay.properties.items()}) if pay.properties else None,
            )
    
    async def store_batch(self, messages: list[Message]) -> None:
        """Store multiple messages in a batch."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        if not messages:
            return
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for message in messages:
                    await self.store(message)
    
    async def get(self, message_id: UUID) -> Message | None:
        """Get a message by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM hie_messages WHERE message_id = $1",
                message_id
            )
            
            if row is None:
                return None
            
            return self._row_to_message(row)
    
    async def get_batch(self, message_ids: list[UUID]) -> list[Message]:
        """Get multiple messages by ID."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        if not message_ids:
            return []
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM hie_messages WHERE message_id = ANY($1)",
                message_ids
            )
            
            return [self._row_to_message(row) for row in rows]
    
    async def query(self, query: MessageQuery) -> list[Message]:
        """Query messages by criteria."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        conditions = []
        params = []
        param_idx = 1
        
        if query.message_ids:
            conditions.append(f"message_id = ANY(${param_idx})")
            params.append(query.message_ids)
            param_idx += 1
        
        if query.correlation_id:
            conditions.append(f"correlation_id = ${param_idx}")
            params.append(query.correlation_id)
            param_idx += 1
        
        if query.route_id:
            conditions.append(f"route_id = ${param_idx}")
            params.append(query.route_id)
            param_idx += 1
        
        if query.source:
            conditions.append(f"source = ${param_idx}")
            params.append(query.source)
            param_idx += 1
        
        if query.message_type:
            conditions.append(f"message_type = ${param_idx}")
            params.append(query.message_type)
            param_idx += 1
        
        if query.state:
            conditions.append(f"state = ${param_idx}")
            params.append(query.state.value)
            param_idx += 1
        
        if query.created_after:
            conditions.append(f"created_at >= ${param_idx}")
            params.append(query.created_after)
            param_idx += 1
        
        if query.created_before:
            conditions.append(f"created_at <= ${param_idx}")
            params.append(query.created_before)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        order_dir = "DESC" if query.order_desc else "ASC"
        
        sql = f"""
            SELECT * FROM hie_messages
            WHERE {where_clause}
            ORDER BY {query.order_by} {order_dir}
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([query.limit, query.offset])
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [self._row_to_message(row) for row in rows]
    
    async def count(self, query: MessageQuery) -> int:
        """Count messages matching criteria."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        conditions = []
        params = []
        param_idx = 1
        
        if query.correlation_id:
            conditions.append(f"correlation_id = ${param_idx}")
            params.append(query.correlation_id)
            param_idx += 1
        
        if query.route_id:
            conditions.append(f"route_id = ${param_idx}")
            params.append(query.route_id)
            param_idx += 1
        
        if query.source:
            conditions.append(f"source = ${param_idx}")
            params.append(query.source)
            param_idx += 1
        
        if query.state:
            conditions.append(f"state = ${param_idx}")
            params.append(query.state.value)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT COUNT(*) FROM hie_messages WHERE {where_clause}",
                *params
            )
            return result or 0
    
    async def update_state(self, message_id: UUID, state: MessageState) -> bool:
        """Update message state."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE hie_messages
                SET state = $2, updated_at = NOW(), version = version + 1
                WHERE message_id = $1
                """,
                message_id,
                state.value
            )
            return result == "UPDATE 1"
    
    async def delete(self, message_id: UUID) -> bool:
        """Delete a message."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hie_messages WHERE message_id = $1",
                message_id
            )
            return result == "DELETE 1"
    
    async def delete_batch(self, message_ids: list[UUID]) -> int:
        """Delete multiple messages."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        if not message_ids:
            return 0
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hie_messages WHERE message_id = ANY($1)",
                message_ids
            )
            # Parse "DELETE N" to get count
            return int(result.split()[1]) if result else 0
    
    async def purge_expired(self) -> int:
        """Delete expired messages."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hie_messages WHERE expires_at IS NOT NULL AND expires_at < NOW()"
            )
            return int(result.split()[1]) if result else 0
    
    def _row_to_message(self, row: asyncpg.Record) -> Message:
        """Convert a database row to a Message."""
        from hie.core.message import Envelope, Payload, Property
        
        envelope_data = json.loads(row["envelope_json"])
        envelope = Envelope.model_validate(envelope_data)
        
        properties = {}
        if row["properties_json"]:
            props_data = json.loads(row["properties_json"])
            properties = {k: Property.from_dict(v) for k, v in props_data.items()}
        
        payload = Payload(
            raw=row["raw_payload"],
            content_type=row["content_type"],
            encoding=row["encoding"],
            properties=properties,
        )
        
        return Message(envelope=envelope, payload=payload)


class PostgreSQLStateStore(StateStore):
    """
    PostgreSQL-backed state store.
    
    Features:
    - ACID transactions
    - TTL support
    - Atomic operations
    """
    
    def __init__(
        self,
        dsn: str | None = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "hie",
        user: str = "hie",
        password: str = "",
        min_connections: int = 2,
        max_connections: int = 10,
    ) -> None:
        self._dsn = dsn
        self._host = host
        self._port = port
        self._database = database
        self._user = user
        self._password = password
        self._min_connections = min_connections
        self._max_connections = max_connections
        
        self._pool: asyncpg.Pool | None = None
        self._logger = logger.bind(component="postgresql_state_store")
    
    async def connect(self) -> None:
        """Establish connection pool and create tables."""
        if self._dsn:
            self._pool = await asyncpg.create_pool(
                self._dsn,
                min_size=self._min_connections,
                max_size=self._max_connections,
            )
        else:
            self._pool = await asyncpg.create_pool(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
                min_size=self._min_connections,
                max_size=self._max_connections,
            )
        
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_STATE_TABLE)
        
        self._logger.info("postgresql_state_connected")
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    async def get(self, key: str) -> Any | None:
        """Get a state value."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT value FROM hie_state
                WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key
            )
            
            if row is None:
                return None
            
            return json.loads(row["value"])
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a state value."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        expires_at = None
        if ttl:
            from datetime import timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO hie_state (key, value, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = NOW(),
                    version = hie_state.version + 1
                """,
                key,
                json.dumps(value),
                expires_at
            )
    
    async def delete(self, key: str) -> bool:
        """Delete a state value."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM hie_state WHERE key = $1",
                key
            )
            return result == "DELETE 1"
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT 1 FROM hie_state
                WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key
            )
            return result is not None
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        # Convert glob pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%").replace("?", "_")
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT key FROM hie_state
                WHERE key LIKE $1 AND (expires_at IS NULL OR expires_at > NOW())
                """,
                sql_pattern
            )
            return [row["key"] for row in rows]
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a numeric value."""
        if not self._pool:
            raise RuntimeError("Not connected")
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT value FROM hie_state WHERE key = $1 FOR UPDATE",
                    key
                )
                
                if row is None:
                    new_value = amount
                else:
                    current = json.loads(row["value"])
                    if not isinstance(current, (int, float)):
                        raise TypeError(f"Cannot increment non-numeric value")
                    new_value = current + amount
                
                await conn.execute(
                    """
                    INSERT INTO hie_state (key, value)
                    VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        updated_at = NOW(),
                        version = hie_state.version + 1
                    """,
                    key,
                    json.dumps(new_value)
                )
                
                return new_value
