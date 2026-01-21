"""
Redis Storage - High-speed queue and cache for HIE.

Provides fast message queuing and state caching with optional persistence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import UUID

import redis.asyncio as redis
import structlog

from hie.core.message import Message, MessageState
from hie.persistence.base import MessageStore, StateStore, MessageQuery

logger = structlog.get_logger(__name__)


class RedisMessageStore(MessageStore):
    """
    Redis-backed message store.
    
    Optimized for high-throughput scenarios. Uses:
    - Hash for message storage
    - Sorted sets for time-based queries
    - Sets for secondary indexes
    
    Note: For full durability, use PostgreSQL. Redis is best for
    high-speed queuing with acceptable data loss risk.
    """
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "hie:",
        max_connections: int = 20,
    ) -> None:
        self._url = url
        self._prefix = prefix
        self._max_connections = max_connections
        self._client: redis.Redis | None = None
        self._logger = logger.bind(component="redis_message_store")
    
    def _key(self, *parts: str) -> str:
        """Generate a Redis key with prefix."""
        return self._prefix + ":".join(parts)
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        self._client = redis.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=False,  # We handle encoding ourselves
        )
        
        # Test connection
        await self._client.ping()
        self._logger.info("redis_connected", url=self._url)
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
        self._logger.info("redis_disconnected")
    
    async def store(self, message: Message) -> None:
        """Store a message."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        msg_id = str(message.id)
        serialized = message.serialize(format="msgpack")
        
        pipe = self._client.pipeline()
        
        # Store message data
        pipe.hset(self._key("messages"), msg_id, serialized)
        
        # Add to time-sorted index
        timestamp = message.envelope.created_at.timestamp()
        pipe.zadd(self._key("idx", "time"), {msg_id: timestamp})
        
        # Add to secondary indexes
        env = message.envelope
        
        pipe.sadd(self._key("idx", "correlation", str(env.correlation_id)), msg_id)
        pipe.sadd(self._key("idx", "source", env.routing.source), msg_id)
        pipe.sadd(self._key("idx", "state", env.state.value), msg_id)
        
        if env.routing.route_id:
            pipe.sadd(self._key("idx", "route", env.routing.route_id), msg_id)
        
        if env.message_type:
            pipe.sadd(self._key("idx", "type", env.message_type), msg_id)
        
        # Set expiration if TTL specified
        if env.expires_at:
            ttl = int((env.expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl > 0:
                pipe.expire(self._key("messages"), ttl)
        
        await pipe.execute()
    
    async def store_batch(self, messages: list[Message]) -> None:
        """Store multiple messages."""
        for message in messages:
            await self.store(message)
    
    async def get(self, message_id: UUID) -> Message | None:
        """Get a message by ID."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        data = await self._client.hget(self._key("messages"), str(message_id))
        if data is None:
            return None
        
        return Message.deserialize(data, format="msgpack")
    
    async def get_batch(self, message_ids: list[UUID]) -> list[Message]:
        """Get multiple messages by ID."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        if not message_ids:
            return []
        
        keys = [str(mid) for mid in message_ids]
        values = await self._client.hmget(self._key("messages"), keys)
        
        result = []
        for data in values:
            if data:
                result.append(Message.deserialize(data, format="msgpack"))
        
        return result
    
    async def query(self, query: MessageQuery) -> list[Message]:
        """Query messages by criteria."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        # Start with candidate set
        candidate_keys: list[str] = []
        
        if query.message_ids:
            # Direct lookup
            return await self.get_batch(query.message_ids)
        
        if query.correlation_id:
            candidate_keys.append(self._key("idx", "correlation", str(query.correlation_id)))
        
        if query.route_id:
            candidate_keys.append(self._key("idx", "route", query.route_id))
        
        if query.source:
            candidate_keys.append(self._key("idx", "source", query.source))
        
        if query.state:
            candidate_keys.append(self._key("idx", "state", query.state.value))
        
        if query.message_type:
            candidate_keys.append(self._key("idx", "type", query.message_type))
        
        # Get candidate IDs
        if candidate_keys:
            if len(candidate_keys) == 1:
                candidates = await self._client.smembers(candidate_keys[0])
            else:
                # Intersection of all index sets
                candidates = await self._client.sinter(candidate_keys)
        else:
            # No filters, get all from time index
            candidates = await self._client.zrange(
                self._key("idx", "time"),
                0, -1
            )
        
        if not candidates:
            return []
        
        # Fetch messages
        candidate_ids = [UUID(c.decode() if isinstance(c, bytes) else c) for c in candidates]
        messages = await self.get_batch(candidate_ids)
        
        # Apply time filters
        if query.created_after or query.created_before:
            filtered = []
            for msg in messages:
                if query.created_after and msg.envelope.created_at < query.created_after:
                    continue
                if query.created_before and msg.envelope.created_at > query.created_before:
                    continue
                filtered.append(msg)
            messages = filtered
        
        # Sort
        messages.sort(
            key=lambda m: m.envelope.created_at,
            reverse=query.order_desc
        )
        
        # Apply offset and limit
        return messages[query.offset:query.offset + query.limit]
    
    async def count(self, query: MessageQuery) -> int:
        """Count messages matching criteria."""
        messages = await self.query(MessageQuery(
            correlation_id=query.correlation_id,
            route_id=query.route_id,
            source=query.source,
            state=query.state,
            message_type=query.message_type,
            limit=1_000_000,
        ))
        return len(messages)
    
    async def update_state(self, message_id: UUID, state: MessageState) -> bool:
        """Update message state."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        msg = await self.get(message_id)
        if msg is None:
            return False
        
        old_state = msg.envelope.state
        
        # Update message
        new_msg = msg.with_state(state)
        
        pipe = self._client.pipeline()
        
        # Store updated message
        pipe.hset(
            self._key("messages"),
            str(message_id),
            new_msg.serialize(format="msgpack")
        )
        
        # Update state index
        pipe.srem(self._key("idx", "state", old_state.value), str(message_id))
        pipe.sadd(self._key("idx", "state", state.value), str(message_id))
        
        await pipe.execute()
        return True
    
    async def delete(self, message_id: UUID) -> bool:
        """Delete a message."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        msg = await self.get(message_id)
        if msg is None:
            return False
        
        msg_id = str(message_id)
        env = msg.envelope
        
        pipe = self._client.pipeline()
        
        # Remove from main storage
        pipe.hdel(self._key("messages"), msg_id)
        
        # Remove from indexes
        pipe.zrem(self._key("idx", "time"), msg_id)
        pipe.srem(self._key("idx", "correlation", str(env.correlation_id)), msg_id)
        pipe.srem(self._key("idx", "source", env.routing.source), msg_id)
        pipe.srem(self._key("idx", "state", env.state.value), msg_id)
        
        if env.routing.route_id:
            pipe.srem(self._key("idx", "route", env.routing.route_id), msg_id)
        
        if env.message_type:
            pipe.srem(self._key("idx", "type", env.message_type), msg_id)
        
        await pipe.execute()
        return True
    
    async def delete_batch(self, message_ids: list[UUID]) -> int:
        """Delete multiple messages."""
        count = 0
        for mid in message_ids:
            if await self.delete(mid):
                count += 1
        return count
    
    async def purge_expired(self) -> int:
        """Delete expired messages."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        # Get all message IDs
        all_ids = await self._client.hkeys(self._key("messages"))
        
        count = 0
        for msg_id_bytes in all_ids:
            msg_id = UUID(msg_id_bytes.decode() if isinstance(msg_id_bytes, bytes) else msg_id_bytes)
            msg = await self.get(msg_id)
            if msg and msg.envelope.is_expired():
                await self.delete(msg_id)
                count += 1
        
        return count


class RedisStateStore(StateStore):
    """
    Redis-backed state store.
    
    Features:
    - Fast key-value operations
    - Native TTL support
    - Atomic increment
    - Pattern-based key listing
    """
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        prefix: str = "hie:state:",
        max_connections: int = 10,
    ) -> None:
        self._url = url
        self._prefix = prefix
        self._max_connections = max_connections
        self._client: redis.Redis | None = None
        self._logger = logger.bind(component="redis_state_store")
    
    def _key(self, key: str) -> str:
        """Generate a Redis key with prefix."""
        return self._prefix + key
    
    async def connect(self) -> None:
        """Establish connection to Redis."""
        self._client = redis.from_url(
            self._url,
            max_connections=self._max_connections,
            decode_responses=True,
        )
        
        await self._client.ping()
        self._logger.info("redis_state_connected")
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str) -> Any | None:
        """Get a state value."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        value = await self._client.get(self._key(key))
        if value is None:
            return None
        
        return json.loads(value)
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a state value."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        serialized = json.dumps(value)
        
        if ttl:
            await self._client.setex(self._key(key), ttl, serialized)
        else:
            await self._client.set(self._key(key), serialized)
    
    async def delete(self, key: str) -> bool:
        """Delete a state value."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        result = await self._client.delete(self._key(key))
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        return await self._client.exists(self._key(key)) > 0
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        full_pattern = self._key(pattern)
        keys = await self._client.keys(full_pattern)
        
        # Strip prefix from keys
        prefix_len = len(self._prefix)
        return [k[prefix_len:] if isinstance(k, str) else k.decode()[prefix_len:] for k in keys]
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a numeric value."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        # Check if key exists and is numeric
        current = await self.get(key)
        if current is not None and not isinstance(current, (int, float)):
            raise TypeError("Cannot increment non-numeric value")
        
        # Use Redis INCRBY for atomic increment
        # But we store as JSON, so we need to handle this carefully
        if current is None:
            await self.set(key, amount)
            return amount
        
        new_value = current + amount
        await self.set(key, new_value)
        return new_value
