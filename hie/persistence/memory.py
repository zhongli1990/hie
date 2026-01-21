"""
In-Memory Storage - Fast storage for development and testing.

Also useful for ultra-low-latency scenarios where durability is not required.
"""

from __future__ import annotations

import asyncio
import fnmatch
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from hie.core.message import Message, MessageState
from hie.persistence.base import MessageStore, StateStore, MessageQuery, MessageRecord


class InMemoryMessageStore(MessageStore):
    """
    In-memory message store.
    
    Features:
    - Fast O(1) lookups by message ID
    - Secondary indexes for common queries
    - Configurable max size with LRU eviction
    - Thread-safe with asyncio locks
    """
    
    def __init__(self, max_size: int = 100_000) -> None:
        self._max_size = max_size
        self._messages: OrderedDict[UUID, MessageRecord] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # Secondary indexes
        self._by_correlation: dict[UUID, set[UUID]] = {}
        self._by_route: dict[str, set[UUID]] = {}
        self._by_source: dict[str, set[UUID]] = {}
        self._by_state: dict[MessageState, set[UUID]] = {}
        self._by_type: dict[str, set[UUID]] = {}
    
    async def connect(self) -> None:
        """No-op for in-memory store."""
        pass
    
    async def disconnect(self) -> None:
        """Clear all data."""
        async with self._lock:
            self._messages.clear()
            self._by_correlation.clear()
            self._by_route.clear()
            self._by_source.clear()
            self._by_state.clear()
            self._by_type.clear()
    
    async def store(self, message: Message) -> None:
        """Store a message."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            record = MessageRecord(
                message=message,
                stored_at=now,
                updated_at=now,
            )
            
            # Evict if at capacity
            while len(self._messages) >= self._max_size:
                oldest_id, oldest_record = self._messages.popitem(last=False)
                self._remove_from_indexes(oldest_id, oldest_record.message)
            
            # Store message
            self._messages[message.id] = record
            self._add_to_indexes(message)
    
    async def store_batch(self, messages: list[Message]) -> None:
        """Store multiple messages."""
        for message in messages:
            await self.store(message)
    
    async def get(self, message_id: UUID) -> Message | None:
        """Get a message by ID."""
        async with self._lock:
            record = self._messages.get(message_id)
            return record.message if record else None
    
    async def get_batch(self, message_ids: list[UUID]) -> list[Message]:
        """Get multiple messages by ID."""
        async with self._lock:
            result = []
            for mid in message_ids:
                record = self._messages.get(mid)
                if record:
                    result.append(record.message)
            return result
    
    async def query(self, query: MessageQuery) -> list[Message]:
        """Query messages by criteria."""
        async with self._lock:
            # Start with candidate set
            candidates: set[UUID] | None = None
            
            # Apply index filters
            if query.message_ids:
                candidates = set(query.message_ids)
            
            if query.correlation_id:
                corr_set = self._by_correlation.get(query.correlation_id, set())
                candidates = corr_set if candidates is None else candidates & corr_set
            
            if query.route_id:
                route_set = self._by_route.get(query.route_id, set())
                candidates = route_set if candidates is None else candidates & route_set
            
            if query.source:
                source_set = self._by_source.get(query.source, set())
                candidates = source_set if candidates is None else candidates & source_set
            
            if query.state:
                state_set = self._by_state.get(query.state, set())
                candidates = state_set if candidates is None else candidates & state_set
            
            if query.message_type:
                type_set = self._by_type.get(query.message_type, set())
                candidates = type_set if candidates is None else candidates & type_set
            
            # If no index filters, use all messages
            if candidates is None:
                candidates = set(self._messages.keys())
            
            # Apply time filters and collect results
            results: list[tuple[datetime, Message]] = []
            for mid in candidates:
                record = self._messages.get(mid)
                if not record:
                    continue
                
                msg = record.message
                
                # Time filters
                if query.created_after and msg.envelope.created_at < query.created_after:
                    continue
                if query.created_before and msg.envelope.created_at > query.created_before:
                    continue
                
                results.append((msg.envelope.created_at, msg))
            
            # Sort
            results.sort(key=lambda x: x[0], reverse=query.order_desc)
            
            # Apply offset and limit
            start = query.offset
            end = start + query.limit
            return [msg for _, msg in results[start:end]]
    
    async def count(self, query: MessageQuery) -> int:
        """Count messages matching criteria."""
        # Reuse query logic but don't apply limit
        query.limit = self._max_size
        query.offset = 0
        messages = await self.query(query)
        return len(messages)
    
    async def update_state(self, message_id: UUID, state: MessageState) -> bool:
        """Update message state."""
        async with self._lock:
            record = self._messages.get(message_id)
            if not record:
                return False
            
            old_state = record.message.envelope.state
            
            # Remove from old state index
            if old_state in self._by_state:
                self._by_state[old_state].discard(message_id)
            
            # Update message
            new_message = record.message.with_state(state)
            record = MessageRecord(
                message=new_message,
                stored_at=record.stored_at,
                updated_at=datetime.now(timezone.utc),
                version=record.version + 1,
            )
            self._messages[message_id] = record
            
            # Add to new state index
            if state not in self._by_state:
                self._by_state[state] = set()
            self._by_state[state].add(message_id)
            
            return True
    
    async def delete(self, message_id: UUID) -> bool:
        """Delete a message."""
        async with self._lock:
            record = self._messages.pop(message_id, None)
            if record:
                self._remove_from_indexes(message_id, record.message)
                return True
            return False
    
    async def delete_batch(self, message_ids: list[UUID]) -> int:
        """Delete multiple messages."""
        count = 0
        for mid in message_ids:
            if await self.delete(mid):
                count += 1
        return count
    
    async def purge_expired(self) -> int:
        """Delete expired messages."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            expired: list[UUID] = []
            
            for mid, record in self._messages.items():
                if record.message.envelope.is_expired():
                    expired.append(mid)
            
            for mid in expired:
                record = self._messages.pop(mid)
                self._remove_from_indexes(mid, record.message)
            
            return len(expired)
    
    def _add_to_indexes(self, message: Message) -> None:
        """Add message to secondary indexes."""
        mid = message.id
        env = message.envelope
        
        # Correlation index
        if env.correlation_id not in self._by_correlation:
            self._by_correlation[env.correlation_id] = set()
        self._by_correlation[env.correlation_id].add(mid)
        
        # Route index
        if env.routing.route_id:
            if env.routing.route_id not in self._by_route:
                self._by_route[env.routing.route_id] = set()
            self._by_route[env.routing.route_id].add(mid)
        
        # Source index
        if env.routing.source not in self._by_source:
            self._by_source[env.routing.source] = set()
        self._by_source[env.routing.source].add(mid)
        
        # State index
        if env.state not in self._by_state:
            self._by_state[env.state] = set()
        self._by_state[env.state].add(mid)
        
        # Type index
        if env.message_type:
            if env.message_type not in self._by_type:
                self._by_type[env.message_type] = set()
            self._by_type[env.message_type].add(mid)
    
    def _remove_from_indexes(self, message_id: UUID, message: Message) -> None:
        """Remove message from secondary indexes."""
        env = message.envelope
        
        if env.correlation_id in self._by_correlation:
            self._by_correlation[env.correlation_id].discard(message_id)
        
        if env.routing.route_id and env.routing.route_id in self._by_route:
            self._by_route[env.routing.route_id].discard(message_id)
        
        if env.routing.source in self._by_source:
            self._by_source[env.routing.source].discard(message_id)
        
        if env.state in self._by_state:
            self._by_state[env.state].discard(message_id)
        
        if env.message_type and env.message_type in self._by_type:
            self._by_type[env.message_type].discard(message_id)


class InMemoryStateStore(StateStore):
    """
    In-memory state store.
    
    Features:
    - Fast key-value storage
    - TTL support
    - Atomic increment
    - Pattern matching for keys
    """
    
    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, datetime | None]] = {}  # key -> (value, expires_at)
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """No-op for in-memory store."""
        pass
    
    async def disconnect(self) -> None:
        """Clear all data."""
        async with self._lock:
            self._data.clear()
    
    async def get(self, key: str) -> Any | None:
        """Get a state value."""
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            
            value, expires_at = entry
            
            # Check expiration
            if expires_at and datetime.now(timezone.utc) >= expires_at:
                del self._data[key]
                return None
            
            return value
    
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a state value."""
        async with self._lock:
            expires_at = None
            if ttl:
                from datetime import timedelta
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            
            self._data[key] = (value, expires_at)
    
    async def delete(self, key: str) -> bool:
        """Delete a state value."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        value = await self.get(key)
        return value is not None
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching a pattern."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            result = []
            
            for key, (value, expires_at) in list(self._data.items()):
                # Skip expired
                if expires_at and now >= expires_at:
                    del self._data[key]
                    continue
                
                # Match pattern
                if fnmatch.fnmatch(key, pattern):
                    result.append(key)
            
            return result
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a numeric value."""
        async with self._lock:
            entry = self._data.get(key)
            
            if entry is None:
                new_value = amount
                expires_at = None
            else:
                value, expires_at = entry
                
                # Check expiration
                if expires_at and datetime.now(timezone.utc) >= expires_at:
                    new_value = amount
                    expires_at = None
                else:
                    if not isinstance(value, (int, float)):
                        raise TypeError(f"Cannot increment non-numeric value: {type(value)}")
                    new_value = value + amount
            
            self._data[key] = (new_value, expires_at)
            return new_value
