"""
Base classes for HIE persistence layer.

Defines abstract interfaces for message storage and state management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator
from uuid import UUID

from hie.core.message import Message, MessageState


class StorageBackend(str, Enum):
    """Available storage backends."""
    MEMORY = "memory"
    POSTGRESQL = "postgresql"
    REDIS = "redis"


@dataclass
class MessageQuery:
    """Query parameters for message retrieval."""
    message_ids: list[UUID] | None = None
    correlation_id: UUID | None = None
    route_id: str | None = None
    source: str | None = None
    message_type: str | None = None
    state: MessageState | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = 100
    offset: int = 0
    order_by: str = "created_at"
    order_desc: bool = True


@dataclass
class MessageRecord:
    """A stored message with metadata."""
    message: Message
    stored_at: datetime
    updated_at: datetime
    version: int = 1


class MessageStore(ABC):
    """
    Abstract base class for message storage.
    
    Message stores provide durable storage for messages with support for:
    - CRUD operations
    - Querying by various criteria
    - State management
    - Batch operations
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        ...
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the storage backend."""
        ...
    
    @abstractmethod
    async def store(self, message: Message) -> None:
        """
        Store a message.
        
        Args:
            message: Message to store
        """
        ...
    
    @abstractmethod
    async def store_batch(self, messages: list[Message]) -> None:
        """
        Store multiple messages in a batch.
        
        Args:
            messages: Messages to store
        """
        ...
    
    @abstractmethod
    async def get(self, message_id: UUID) -> Message | None:
        """
        Retrieve a message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            Message if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def get_batch(self, message_ids: list[UUID]) -> list[Message]:
        """
        Retrieve multiple messages by ID.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            List of found messages (may be shorter than input)
        """
        ...
    
    @abstractmethod
    async def query(self, query: MessageQuery) -> list[Message]:
        """
        Query messages by criteria.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching messages
        """
        ...
    
    @abstractmethod
    async def count(self, query: MessageQuery) -> int:
        """
        Count messages matching criteria.
        
        Args:
            query: Query parameters
            
        Returns:
            Count of matching messages
        """
        ...
    
    @abstractmethod
    async def update_state(self, message_id: UUID, state: MessageState) -> bool:
        """
        Update message state.
        
        Args:
            message_id: Message ID
            state: New state
            
        Returns:
            True if updated, False if not found
        """
        ...
    
    @abstractmethod
    async def delete(self, message_id: UUID) -> bool:
        """
        Delete a message.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def delete_batch(self, message_ids: list[UUID]) -> int:
        """
        Delete multiple messages.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            Number of messages deleted
        """
        ...
    
    @abstractmethod
    async def purge_expired(self) -> int:
        """
        Delete all expired messages.
        
        Returns:
            Number of messages deleted
        """
        ...
    
    async def stream(self, query: MessageQuery) -> AsyncIterator[Message]:
        """
        Stream messages matching criteria.
        
        Default implementation uses query() with pagination.
        Override for more efficient streaming.
        """
        offset = 0
        while True:
            query.offset = offset
            messages = await self.query(query)
            if not messages:
                break
            for message in messages:
                yield message
            offset += len(messages)
            if len(messages) < query.limit:
                break


@dataclass
class StateRecord:
    """A stored state value."""
    key: str
    value: Any
    updated_at: datetime
    version: int = 1


class StateStore(ABC):
    """
    Abstract base class for state storage.
    
    State stores provide key-value storage for:
    - Item state (offsets, checkpoints)
    - Route state
    - Production state
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the storage backend."""
        ...
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the storage backend."""
        ...
    
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Get a state value.
        
        Args:
            key: State key
            
        Returns:
            State value if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a state value.
        
        Args:
            key: State key
            value: State value (must be JSON-serializable)
            ttl: Optional time-to-live in seconds
        """
        ...
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a state value.
        
        Args:
            key: State key
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a state key exists.
        
        Args:
            key: State key
            
        Returns:
            True if exists, False otherwise
        """
        ...
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> list[str]:
        """
        List state keys matching a pattern.
        
        Args:
            pattern: Glob pattern (default: all keys)
            
        Returns:
            List of matching keys
        """
        ...
    
    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Atomically increment a numeric state value.
        
        Args:
            key: State key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        ...
    
    async def get_or_set(self, key: str, default: Any, ttl: int | None = None) -> Any:
        """
        Get a state value, setting default if not found.
        
        Args:
            key: State key
            default: Default value to set if not found
            ttl: Optional time-to-live for default
            
        Returns:
            Existing or default value
        """
        value = await self.get(key)
        if value is None:
            await self.set(key, default, ttl)
            return default
        return value
