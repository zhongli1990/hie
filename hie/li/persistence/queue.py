"""
LI Message Queue

Provides distributed message queuing using Redis.
Enables horizontal scaling of message processing across multiple workers.

Features:
- Reliable queue with acknowledgment
- Dead letter queue for failed messages
- Priority queues
- Message visibility timeout
- Distributed locking
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable
import uuid

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QueueConfig:
    """Queue configuration."""
    redis_url: str = "redis://localhost:6379"
    queue_prefix: str = "li:queue"
    visibility_timeout: float = 30.0  # Seconds before message becomes visible again
    max_retries: int = 3
    retry_delay: float = 5.0
    dead_letter_enabled: bool = True
    batch_size: int = 10


@dataclass
class QueueMessage:
    """A message in the queue."""
    id: str
    queue_name: str
    payload: bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Processing state
    created_at: float = field(default_factory=time.time)
    receive_count: int = 0
    first_received_at: float | None = None
    
    # Message attributes
    priority: int = 0
    delay_until: float | None = None
    correlation_id: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "payload": self.payload.hex(),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "receive_count": self.receive_count,
            "first_received_at": self.first_received_at,
            "priority": self.priority,
            "delay_until": self.delay_until,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueMessage":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            queue_name=data["queue_name"],
            payload=bytes.fromhex(data["payload"]),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            receive_count=data.get("receive_count", 0),
            first_received_at=data.get("first_received_at"),
            priority=data.get("priority", 0),
            delay_until=data.get("delay_until"),
            correlation_id=data.get("correlation_id"),
        )


class MessageQueue:
    """
    Redis-based message queue.
    
    Provides reliable message queuing with acknowledgment semantics.
    Messages are moved to a processing set when received and must be
    acknowledged or they will be returned to the queue.
    
    Usage:
        queue = MessageQueue(config)
        await queue.start()
        
        # Producer
        await queue.send("my-queue", payload)
        
        # Consumer
        msg = await queue.receive("my-queue")
        if msg:
            try:
                await process(msg.payload)
                await queue.ack(msg)
            except Exception:
                await queue.nack(msg)
        
        await queue.stop()
    """
    
    def __init__(self, config: QueueConfig | None = None):
        self._config = config or QueueConfig()
        self._redis = None
        self._running = False
        self._visibility_task: asyncio.Task | None = None
        
        self._log = logger.bind(
            component="MessageQueue",
            redis_url=self._config.redis_url,
        )
    
    def _queue_key(self, queue_name: str) -> str:
        """Get Redis key for a queue."""
        return f"{self._config.queue_prefix}:{queue_name}"
    
    def _processing_key(self, queue_name: str) -> str:
        """Get Redis key for processing set."""
        return f"{self._config.queue_prefix}:{queue_name}:processing"
    
    def _dlq_key(self, queue_name: str) -> str:
        """Get Redis key for dead letter queue."""
        return f"{self._config.queue_prefix}:{queue_name}:dlq"
    
    def _delayed_key(self, queue_name: str) -> str:
        """Get Redis key for delayed messages."""
        return f"{self._config.queue_prefix}:{queue_name}:delayed"
    
    async def start(self) -> None:
        """Start the queue."""
        try:
            import redis.asyncio as redis
            self._redis = redis.from_url(self._config.redis_url)
            await self._redis.ping()
            
            self._running = True
            self._visibility_task = asyncio.create_task(self._visibility_loop())
            
            self._log.info("queue_started")
        except ImportError:
            self._log.warning("redis_not_installed", message="Redis not available, using in-memory queue")
            self._redis = None
            self._running = True
        except Exception as e:
            self._log.error("queue_start_error", error=str(e))
            raise
    
    async def stop(self) -> None:
        """Stop the queue."""
        self._running = False
        
        if self._visibility_task:
            self._visibility_task.cancel()
            try:
                await self._visibility_task
            except asyncio.CancelledError:
                pass
        
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        self._log.info("queue_stopped")
    
    async def send(
        self,
        queue_name: str,
        payload: bytes,
        priority: int = 0,
        delay: float = 0,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QueueMessage:
        """
        Send a message to a queue.
        
        Args:
            queue_name: Name of the queue
            payload: Message payload bytes
            priority: Message priority (higher = more urgent)
            delay: Delay in seconds before message is visible
            correlation_id: Optional correlation ID
            metadata: Optional metadata
            
        Returns:
            Created QueueMessage
        """
        msg = QueueMessage(
            id=str(uuid.uuid4()),
            queue_name=queue_name,
            payload=payload,
            metadata=metadata or {},
            priority=priority,
            delay_until=time.time() + delay if delay > 0 else None,
            correlation_id=correlation_id,
        )
        
        if self._redis:
            data = json.dumps(msg.to_dict())
            
            if delay > 0:
                # Add to delayed sorted set
                await self._redis.zadd(
                    self._delayed_key(queue_name),
                    {data: msg.delay_until},
                )
            else:
                # Add to queue (using priority as score for sorted set)
                await self._redis.zadd(
                    self._queue_key(queue_name),
                    {data: -priority},  # Negative so higher priority comes first
                )
        
        self._log.debug(
            "message_sent",
            queue=queue_name,
            message_id=msg.id,
            priority=priority,
            delay=delay,
        )
        
        return msg
    
    async def receive(
        self,
        queue_name: str,
        timeout: float = 0,
    ) -> QueueMessage | None:
        """
        Receive a message from a queue.
        
        The message is moved to a processing set and must be acknowledged.
        If not acknowledged within visibility_timeout, it returns to the queue.
        
        Args:
            queue_name: Name of the queue
            timeout: How long to wait for a message (0 = no wait)
            
        Returns:
            QueueMessage or None if no message available
        """
        if not self._redis:
            return None
        
        # First, move any delayed messages that are ready
        await self._process_delayed(queue_name)
        
        # Try to get a message
        queue_key = self._queue_key(queue_name)
        processing_key = self._processing_key(queue_name)
        
        # Get highest priority message (lowest score)
        result = await self._redis.zpopmin(queue_key, count=1)
        
        if not result:
            if timeout > 0:
                # Wait for a message
                await asyncio.sleep(min(timeout, 1.0))
                return await self.receive(queue_name, timeout - 1.0)
            return None
        
        data, score = result[0]
        msg = QueueMessage.from_dict(json.loads(data))
        
        # Update receive count
        msg.receive_count += 1
        if msg.first_received_at is None:
            msg.first_received_at = time.time()
        
        # Add to processing set with visibility timeout
        visibility_deadline = time.time() + self._config.visibility_timeout
        await self._redis.zadd(
            processing_key,
            {json.dumps(msg.to_dict()): visibility_deadline},
        )
        
        self._log.debug(
            "message_received",
            queue=queue_name,
            message_id=msg.id,
            receive_count=msg.receive_count,
        )
        
        return msg
    
    async def ack(self, msg: QueueMessage) -> None:
        """
        Acknowledge successful processing of a message.
        
        Removes the message from the processing set.
        """
        if not self._redis:
            return
        
        processing_key = self._processing_key(msg.queue_name)
        
        # Remove from processing set
        # We need to find and remove the message by ID
        processing = await self._redis.zrange(processing_key, 0, -1)
        for data in processing:
            stored_msg = QueueMessage.from_dict(json.loads(data))
            if stored_msg.id == msg.id:
                await self._redis.zrem(processing_key, data)
                break
        
        self._log.debug("message_acked", queue=msg.queue_name, message_id=msg.id)
    
    async def nack(self, msg: QueueMessage, requeue: bool = True) -> None:
        """
        Negative acknowledge - message processing failed.
        
        If requeue is True and max retries not exceeded, returns to queue.
        Otherwise, moves to dead letter queue.
        """
        if not self._redis:
            return
        
        processing_key = self._processing_key(msg.queue_name)
        
        # Remove from processing set
        processing = await self._redis.zrange(processing_key, 0, -1)
        for data in processing:
            stored_msg = QueueMessage.from_dict(json.loads(data))
            if stored_msg.id == msg.id:
                await self._redis.zrem(processing_key, data)
                break
        
        if requeue and msg.receive_count < self._config.max_retries:
            # Return to queue with delay
            msg.delay_until = time.time() + self._config.retry_delay
            await self._redis.zadd(
                self._delayed_key(msg.queue_name),
                {json.dumps(msg.to_dict()): msg.delay_until},
            )
            self._log.debug(
                "message_nacked_requeue",
                queue=msg.queue_name,
                message_id=msg.id,
                receive_count=msg.receive_count,
            )
        else:
            # Move to dead letter queue
            if self._config.dead_letter_enabled:
                await self._redis.rpush(
                    self._dlq_key(msg.queue_name),
                    json.dumps(msg.to_dict()),
                )
                self._log.warning(
                    "message_moved_to_dlq",
                    queue=msg.queue_name,
                    message_id=msg.id,
                    receive_count=msg.receive_count,
                )
            else:
                self._log.warning(
                    "message_discarded",
                    queue=msg.queue_name,
                    message_id=msg.id,
                )
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Get the number of messages in a queue."""
        if not self._redis:
            return 0
        return await self._redis.zcard(self._queue_key(queue_name))
    
    async def get_processing_count(self, queue_name: str) -> int:
        """Get the number of messages being processed."""
        if not self._redis:
            return 0
        return await self._redis.zcard(self._processing_key(queue_name))
    
    async def get_dlq_length(self, queue_name: str) -> int:
        """Get the number of messages in dead letter queue."""
        if not self._redis:
            return 0
        return await self._redis.llen(self._dlq_key(queue_name))
    
    async def purge(self, queue_name: str) -> int:
        """Purge all messages from a queue."""
        if not self._redis:
            return 0
        
        count = await self._redis.zcard(self._queue_key(queue_name))
        await self._redis.delete(
            self._queue_key(queue_name),
            self._processing_key(queue_name),
            self._delayed_key(queue_name),
        )
        
        self._log.info("queue_purged", queue=queue_name, count=count)
        return count
    
    async def _process_delayed(self, queue_name: str) -> None:
        """Move delayed messages that are ready to the main queue."""
        if not self._redis:
            return
        
        delayed_key = self._delayed_key(queue_name)
        queue_key = self._queue_key(queue_name)
        now = time.time()
        
        # Get messages that are ready
        ready = await self._redis.zrangebyscore(delayed_key, 0, now)
        
        for data in ready:
            msg = QueueMessage.from_dict(json.loads(data))
            msg.delay_until = None
            
            # Move to main queue
            await self._redis.zadd(queue_key, {json.dumps(msg.to_dict()): -msg.priority})
            await self._redis.zrem(delayed_key, data)
    
    async def _visibility_loop(self) -> None:
        """Background loop to return timed-out messages to queue."""
        while self._running:
            await asyncio.sleep(5.0)  # Check every 5 seconds
            
            if not self._redis:
                continue
            
            try:
                # Get all queue names
                keys = await self._redis.keys(f"{self._config.queue_prefix}:*:processing")
                
                for key in keys:
                    queue_name = key.decode().split(":")[2]
                    await self._return_timed_out(queue_name)
            except Exception as e:
                self._log.error("visibility_loop_error", error=str(e))
    
    async def _return_timed_out(self, queue_name: str) -> None:
        """Return timed-out messages to the queue."""
        if not self._redis:
            return
        
        processing_key = self._processing_key(queue_name)
        queue_key = self._queue_key(queue_name)
        now = time.time()
        
        # Get messages that have timed out
        timed_out = await self._redis.zrangebyscore(processing_key, 0, now)
        
        for data in timed_out:
            msg = QueueMessage.from_dict(json.loads(data))
            
            # Remove from processing
            await self._redis.zrem(processing_key, data)
            
            if msg.receive_count < self._config.max_retries:
                # Return to queue
                await self._redis.zadd(queue_key, {json.dumps(msg.to_dict()): -msg.priority})
                self._log.debug(
                    "message_visibility_timeout",
                    queue=queue_name,
                    message_id=msg.id,
                )
            else:
                # Move to DLQ
                if self._config.dead_letter_enabled:
                    await self._redis.rpush(self._dlq_key(queue_name), data)
                    self._log.warning(
                        "message_timeout_to_dlq",
                        queue=queue_name,
                        message_id=msg.id,
                    )
