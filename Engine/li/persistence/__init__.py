"""
LI Persistence Module

Provides message persistence and durability features:
- WAL: Write-Ahead Log for crash recovery
- MessageStore: Persistent message storage
- Queue: Distributed message queuing with Redis
"""

from Engine.li.persistence.wal import (
    WAL,
    WALEntry,
    WALState,
    WALConfig,
    SyncMode,
)
from Engine.li.persistence.store import (
    MessageStore,
    MessageRecord,
    MessageQuery,
    MessageState,
    StorageBackend,
    FileStorageBackend,
)
from Engine.li.persistence.queue import (
    MessageQueue,
    QueueMessage,
    QueueConfig,
)

__all__ = [
    # WAL
    "WAL",
    "WALEntry",
    "WALState",
    "WALConfig",
    "SyncMode",
    # Store
    "MessageStore",
    "MessageRecord",
    "MessageQuery",
    "MessageState",
    "StorageBackend",
    "FileStorageBackend",
    # Queue
    "MessageQueue",
    "QueueMessage",
    "QueueConfig",
]
