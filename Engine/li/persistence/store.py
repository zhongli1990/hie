"""
LI Message Store

Provides persistent message storage for audit, replay, and debugging.
Supports multiple storage backends (file, PostgreSQL, etc.).
"""

from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator
import hashlib
import uuid

import structlog

logger = structlog.get_logger(__name__)


class MessageState(str, Enum):
    """State of a stored message."""
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class MessageRecord:
    """A stored message record."""
    id: str
    message_id: str
    host_name: str
    message_type: str | None
    state: MessageState
    payload: bytes
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Processing info
    source: str | None = None
    target: str | None = None
    correlation_id: str | None = None
    
    # Error info
    error: str | None = None
    retry_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "host_name": self.host_name,
            "message_type": self.message_type,
            "state": self.state.value,
            "payload": self.payload.hex(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "source": self.source,
            "target": self.target,
            "correlation_id": self.correlation_id,
            "error": self.error,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            message_id=data["message_id"],
            host_name=data["host_name"],
            message_type=data.get("message_type"),
            state=MessageState(data["state"]),
            payload=bytes.fromhex(data["payload"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            source=data.get("source"),
            target=data.get("target"),
            correlation_id=data.get("correlation_id"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class MessageQuery:
    """Query parameters for message search."""
    host_name: str | None = None
    message_type: str | None = None
    state: MessageState | None = None
    source: str | None = None
    target: str | None = None
    correlation_id: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = 100
    offset: int = 0


class StorageBackend(ABC):
    """Abstract storage backend interface."""
    
    @abstractmethod
    async def start(self) -> None:
        """Initialize the storage backend."""
        ...
    
    @abstractmethod
    async def stop(self) -> None:
        """Shutdown the storage backend."""
        ...
    
    @abstractmethod
    async def save(self, record: MessageRecord) -> None:
        """Save a message record."""
        ...
    
    @abstractmethod
    async def get(self, record_id: str) -> MessageRecord | None:
        """Get a message record by ID."""
        ...
    
    @abstractmethod
    async def update(self, record: MessageRecord) -> None:
        """Update a message record."""
        ...
    
    @abstractmethod
    async def delete(self, record_id: str) -> None:
        """Delete a message record."""
        ...
    
    @abstractmethod
    async def query(self, query: MessageQuery) -> list[MessageRecord]:
        """Query message records."""
        ...
    
    @abstractmethod
    async def count(self, query: MessageQuery) -> int:
        """Count matching records."""
        ...


class FileStorageBackend(StorageBackend):
    """
    File-based storage backend.
    
    Stores messages as JSON files in a directory structure.
    Suitable for development and small deployments.
    """
    
    def __init__(self, directory: str = "./message_store"):
        self._directory = Path(directory)
        self._index: dict[str, str] = {}  # id -> file path
        self._lock = asyncio.Lock()
        self._log = logger.bind(backend="FileStorage", directory=str(self._directory))
    
    async def start(self) -> None:
        """Initialize the storage backend."""
        self._directory.mkdir(parents=True, exist_ok=True)
        
        # Build index from existing files
        for json_file in self._directory.rglob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    self._index[data["id"]] = str(json_file)
            except Exception as e:
                self._log.warning("index_build_error", file=str(json_file), error=str(e))
        
        self._log.info("file_storage_started", indexed=len(self._index))
    
    async def stop(self) -> None:
        """Shutdown the storage backend."""
        self._log.info("file_storage_stopped")
    
    def _get_file_path(self, record: MessageRecord) -> Path:
        """Get file path for a record."""
        # Organize by date and host
        date_dir = record.created_at.strftime("%Y/%m/%d")
        return self._directory / date_dir / record.host_name / f"{record.id}.json"
    
    async def save(self, record: MessageRecord) -> None:
        """Save a message record."""
        async with self._lock:
            file_path = self._get_file_path(record)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)
            
            self._index[record.id] = str(file_path)
    
    async def get(self, record_id: str) -> MessageRecord | None:
        """Get a message record by ID."""
        async with self._lock:
            if record_id not in self._index:
                return None
            
            file_path = self._index[record_id]
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    return MessageRecord.from_dict(data)
            except Exception as e:
                self._log.error("get_error", record_id=record_id, error=str(e))
                return None
    
    async def update(self, record: MessageRecord) -> None:
        """Update a message record."""
        await self.save(record)
    
    async def delete(self, record_id: str) -> None:
        """Delete a message record."""
        async with self._lock:
            if record_id not in self._index:
                return
            
            file_path = Path(self._index[record_id])
            try:
                file_path.unlink()
                del self._index[record_id]
            except Exception as e:
                self._log.error("delete_error", record_id=record_id, error=str(e))
    
    async def query(self, query: MessageQuery) -> list[MessageRecord]:
        """Query message records."""
        results = []
        
        async with self._lock:
            for record_id, file_path in list(self._index.items()):
                if len(results) >= query.limit:
                    break
                
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        record = MessageRecord.from_dict(data)
                        
                        if self._matches_query(record, query):
                            results.append(record)
                except Exception:
                    continue
        
        return results[query.offset:query.offset + query.limit]
    
    async def count(self, query: MessageQuery) -> int:
        """Count matching records."""
        count = 0
        
        async with self._lock:
            for record_id, file_path in self._index.items():
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        record = MessageRecord.from_dict(data)
                        
                        if self._matches_query(record, query):
                            count += 1
                except Exception:
                    continue
        
        return count
    
    def _matches_query(self, record: MessageRecord, query: MessageQuery) -> bool:
        """Check if a record matches a query."""
        if query.host_name and record.host_name != query.host_name:
            return False
        if query.message_type and record.message_type != query.message_type:
            return False
        if query.state and record.state != query.state:
            return False
        if query.source and record.source != query.source:
            return False
        if query.target and record.target != query.target:
            return False
        if query.correlation_id and record.correlation_id != query.correlation_id:
            return False
        if query.created_after and record.created_at < query.created_after:
            return False
        if query.created_before and record.created_at > query.created_before:
            return False
        return True


class MessageStore:
    """
    High-level message store interface.
    
    Provides convenient methods for storing and retrieving messages.
    Wraps a storage backend with additional functionality.
    """
    
    def __init__(self, backend: StorageBackend | None = None):
        self._backend = backend or FileStorageBackend()
        self._log = logger.bind(component="MessageStore")
    
    async def start(self) -> None:
        """Start the message store."""
        await self._backend.start()
        self._log.info("message_store_started")
    
    async def stop(self) -> None:
        """Stop the message store."""
        await self._backend.stop()
        self._log.info("message_store_stopped")
    
    async def store(
        self,
        host_name: str,
        message_id: str,
        payload: bytes,
        message_type: str | None = None,
        source: str | None = None,
        target: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageRecord:
        """
        Store a new message.
        
        Args:
            host_name: Name of the host processing the message
            message_id: Unique message identifier
            payload: Raw message bytes
            message_type: Optional message type
            source: Optional source identifier
            target: Optional target identifier
            correlation_id: Optional correlation ID for tracing
            metadata: Optional metadata
            
        Returns:
            Created MessageRecord
        """
        now = datetime.now(timezone.utc)
        
        record = MessageRecord(
            id=str(uuid.uuid4()),
            message_id=message_id,
            host_name=host_name,
            message_type=message_type,
            state=MessageState.RECEIVED,
            payload=payload,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            source=source,
            target=target,
            correlation_id=correlation_id,
        )
        
        await self._backend.save(record)
        
        self._log.debug(
            "message_stored",
            record_id=record.id,
            message_id=message_id,
            host=host_name,
        )
        
        return record
    
    async def get(self, record_id: str) -> MessageRecord | None:
        """Get a message record by ID."""
        return await self._backend.get(record_id)
    
    async def update_state(
        self,
        record_id: str,
        state: MessageState,
        error: str | None = None,
    ) -> None:
        """Update the state of a message record."""
        record = await self._backend.get(record_id)
        if not record:
            raise KeyError(f"Record not found: {record_id}")
        
        record.state = state
        record.updated_at = datetime.now(timezone.utc)
        if error:
            record.error = error
            record.retry_count += 1
        
        await self._backend.update(record)
    
    async def mark_processing(self, record_id: str) -> None:
        """Mark a message as being processed."""
        await self.update_state(record_id, MessageState.PROCESSING)
    
    async def mark_completed(self, record_id: str) -> None:
        """Mark a message as completed."""
        await self.update_state(record_id, MessageState.COMPLETED)
    
    async def mark_failed(self, record_id: str, error: str) -> None:
        """Mark a message as failed."""
        await self.update_state(record_id, MessageState.FAILED, error)
    
    async def query(self, query: MessageQuery) -> list[MessageRecord]:
        """Query message records."""
        return await self._backend.query(query)
    
    async def count(self, query: MessageQuery) -> int:
        """Count matching records."""
        return await self._backend.count(query)
    
    async def get_by_message_id(self, message_id: str) -> list[MessageRecord]:
        """Get all records for a message ID."""
        # This is a simple implementation; backends can optimize
        query = MessageQuery(limit=1000)
        records = await self._backend.query(query)
        return [r for r in records if r.message_id == message_id]
    
    async def get_by_correlation_id(self, correlation_id: str) -> list[MessageRecord]:
        """Get all records for a correlation ID."""
        return await self._backend.query(MessageQuery(correlation_id=correlation_id))
    
    async def get_failed(self, host_name: str | None = None) -> list[MessageRecord]:
        """Get all failed messages."""
        return await self._backend.query(MessageQuery(
            host_name=host_name,
            state=MessageState.FAILED,
        ))
    
    async def archive(self, record_id: str) -> None:
        """Archive a message record."""
        await self.update_state(record_id, MessageState.ARCHIVED)
    
    async def delete(self, record_id: str) -> None:
        """Delete a message record."""
        await self._backend.delete(record_id)
