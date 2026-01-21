"""
HIE Persistence - Message storage and state management.

Supports multiple backends:
- Memory: In-memory storage for development and testing
- PostgreSQL: Durable storage for production
- Redis: High-speed queue and cache
"""

from hie.persistence.base import MessageStore, StateStore
from hie.persistence.memory import InMemoryMessageStore, InMemoryStateStore

__all__ = [
    "MessageStore",
    "StateStore",
    "InMemoryMessageStore",
    "InMemoryStateStore",
]
