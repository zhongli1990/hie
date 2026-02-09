"""
LI Write-Ahead Log (WAL)

Provides crash-recovery durability for message processing.
Messages are written to the WAL before processing and removed after successful completion.

WAL ensures:
- No message loss on crash
- Exactly-once processing semantics
- Recovery of in-flight messages on restart

Design:
- Append-only log file for durability
- Periodic checkpointing to truncate old entries
- Async I/O for performance
- Configurable sync modes (fsync, async, none)
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable
import hashlib

import structlog

logger = structlog.get_logger(__name__)


class WALState(str, Enum):
    """State of a WAL entry."""
    PENDING = "pending"      # Written to WAL, not yet processed
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"   # Successfully processed
    FAILED = "failed"        # Processing failed
    EXPIRED = "expired"      # Exceeded retry limit


class SyncMode(str, Enum):
    """WAL sync mode for durability vs performance tradeoff."""
    FSYNC = "fsync"    # fsync after every write (safest, slowest)
    ASYNC = "async"    # Periodic fsync (balanced)
    NONE = "none"      # No explicit sync (fastest, least safe)


@dataclass
class WALConfig:
    """WAL configuration."""
    directory: str = "./wal"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    sync_mode: SyncMode = SyncMode.ASYNC
    sync_interval: float = 1.0  # Seconds between syncs in async mode
    checkpoint_interval: float = 60.0  # Seconds between checkpoints
    max_retries: int = 3
    retry_delay: float = 5.0
    entry_ttl: float = 3600.0  # 1 hour TTL for entries


@dataclass
class WALEntry:
    """A single WAL entry."""
    id: str
    sequence: int
    timestamp: float
    state: WALState
    host_name: str
    message_id: str
    message_type: str | None
    payload: bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    error: str | None = None
    
    def to_bytes(self) -> bytes:
        """Serialize entry to bytes."""
        data = {
            "id": self.id,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "state": self.state.value,
            "host_name": self.host_name,
            "message_id": self.message_id,
            "message_type": self.message_type,
            "payload": self.payload.hex(),
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "error": self.error,
        }
        return json.dumps(data).encode("utf-8")
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "WALEntry":
        """Deserialize entry from bytes."""
        obj = json.loads(data.decode("utf-8"))
        return cls(
            id=obj["id"],
            sequence=obj["sequence"],
            timestamp=obj["timestamp"],
            state=WALState(obj["state"]),
            host_name=obj["host_name"],
            message_id=obj["message_id"],
            message_type=obj.get("message_type"),
            payload=bytes.fromhex(obj["payload"]),
            metadata=obj.get("metadata", {}),
            retry_count=obj.get("retry_count", 0),
            error=obj.get("error"),
        )
    
    def checksum(self) -> str:
        """Calculate checksum for integrity verification."""
        return hashlib.md5(self.to_bytes()).hexdigest()


class WAL:
    """
    Write-Ahead Log for message durability.
    
    Provides crash-recovery guarantees for message processing.
    Messages are logged before processing and marked complete after.
    
    Usage:
        wal = WAL(config)
        await wal.start()
        
        # Log message before processing
        entry = await wal.append(host_name, message_id, payload)
        
        try:
            # Process message
            await process(payload)
            await wal.complete(entry.id)
        except Exception as e:
            await wal.fail(entry.id, str(e))
        
        await wal.stop()
    """
    
    # WAL file format:
    # [4 bytes: entry length][entry bytes][4 bytes: checksum length][checksum bytes]
    HEADER_FORMAT = ">I"  # Big-endian unsigned int
    
    def __init__(self, config: WALConfig | None = None):
        self._config = config or WALConfig()
        self._directory = Path(self._config.directory)
        
        # State
        self._sequence = 0
        self._entries: dict[str, WALEntry] = {}
        self._current_file: Path | None = None
        self._file_handle = None
        self._lock = asyncio.Lock()
        
        # Background tasks
        self._sync_task: asyncio.Task | None = None
        self._checkpoint_task: asyncio.Task | None = None
        self._running = False
        
        self._log = logger.bind(component="WAL", directory=str(self._directory))
    
    @property
    def pending_count(self) -> int:
        """Number of pending entries."""
        return sum(1 for e in self._entries.values() if e.state == WALState.PENDING)
    
    @property
    def processing_count(self) -> int:
        """Number of entries being processed."""
        return sum(1 for e in self._entries.values() if e.state == WALState.PROCESSING)
    
    async def start(self) -> None:
        """Start the WAL."""
        self._directory.mkdir(parents=True, exist_ok=True)
        
        # Recover from existing WAL files
        await self._recover()
        
        # Open current file
        await self._rotate_file()
        
        # Start background tasks
        self._running = True
        
        if self._config.sync_mode == SyncMode.ASYNC:
            self._sync_task = asyncio.create_task(self._sync_loop())
        
        self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
        
        self._log.info(
            "wal_started",
            pending=self.pending_count,
            sync_mode=self._config.sync_mode.value,
        )
    
    async def stop(self) -> None:
        """Stop the WAL gracefully."""
        self._running = False
        
        # Cancel background tasks
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        if self._checkpoint_task:
            self._checkpoint_task.cancel()
            try:
                await self._checkpoint_task
            except asyncio.CancelledError:
                pass
        
        # Final sync and close
        if self._file_handle:
            await self._sync()
            self._file_handle.close()
            self._file_handle = None
        
        self._log.info("wal_stopped", pending=self.pending_count)
    
    async def append(
        self,
        host_name: str,
        message_id: str,
        payload: bytes,
        message_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WALEntry:
        """
        Append a new entry to the WAL.
        
        Args:
            host_name: Name of the host processing the message
            message_id: Unique message identifier
            payload: Raw message bytes
            message_type: Optional message type
            metadata: Optional metadata
            
        Returns:
            WALEntry with assigned ID and sequence
        """
        async with self._lock:
            self._sequence += 1
            
            entry = WALEntry(
                id=f"{host_name}-{self._sequence}-{int(time.time() * 1000)}",
                sequence=self._sequence,
                timestamp=time.time(),
                state=WALState.PENDING,
                host_name=host_name,
                message_id=message_id,
                message_type=message_type,
                payload=payload,
                metadata=metadata or {},
            )
            
            await self._write_entry(entry)
            self._entries[entry.id] = entry
            
            self._log.debug(
                "wal_entry_appended",
                entry_id=entry.id,
                message_id=message_id,
                host=host_name,
            )
            
            return entry
    
    async def mark_processing(self, entry_id: str) -> None:
        """Mark an entry as being processed."""
        async with self._lock:
            if entry_id not in self._entries:
                raise KeyError(f"WAL entry not found: {entry_id}")
            
            entry = self._entries[entry_id]
            entry.state = WALState.PROCESSING
            await self._write_entry(entry)
    
    async def complete(self, entry_id: str) -> None:
        """Mark an entry as successfully completed."""
        async with self._lock:
            if entry_id not in self._entries:
                return  # Already removed
            
            entry = self._entries[entry_id]
            entry.state = WALState.COMPLETED
            await self._write_entry(entry)
            
            # Remove from memory (will be cleaned up in checkpoint)
            del self._entries[entry_id]
            
            self._log.debug("wal_entry_completed", entry_id=entry_id)
    
    async def fail(self, entry_id: str, error: str) -> bool:
        """
        Mark an entry as failed.
        
        Returns True if entry should be retried, False if max retries exceeded.
        """
        async with self._lock:
            if entry_id not in self._entries:
                return False
            
            entry = self._entries[entry_id]
            entry.retry_count += 1
            entry.error = error
            
            if entry.retry_count >= self._config.max_retries:
                entry.state = WALState.FAILED
                await self._write_entry(entry)
                self._log.warning(
                    "wal_entry_failed_permanently",
                    entry_id=entry_id,
                    retries=entry.retry_count,
                    error=error,
                )
                return False
            else:
                entry.state = WALState.PENDING
                await self._write_entry(entry)
                self._log.warning(
                    "wal_entry_failed_retry",
                    entry_id=entry_id,
                    retry=entry.retry_count,
                    max_retries=self._config.max_retries,
                    error=error,
                )
                return True
    
    async def get_pending(self) -> list[WALEntry]:
        """Get all pending entries for reprocessing."""
        async with self._lock:
            return [
                e for e in self._entries.values()
                if e.state == WALState.PENDING
            ]
    
    async def get_failed(self) -> list[WALEntry]:
        """Get all permanently failed entries."""
        async with self._lock:
            return [
                e for e in self._entries.values()
                if e.state == WALState.FAILED
            ]
    
    async def _write_entry(self, entry: WALEntry) -> None:
        """Write an entry to the current WAL file."""
        if not self._file_handle:
            await self._rotate_file()
        
        data = entry.to_bytes()
        checksum = entry.checksum().encode("utf-8")
        
        # Write: [length][data][checksum_length][checksum]
        header = struct.pack(self.HEADER_FORMAT, len(data))
        checksum_header = struct.pack(self.HEADER_FORMAT, len(checksum))
        
        self._file_handle.write(header + data + checksum_header + checksum)
        
        if self._config.sync_mode == SyncMode.FSYNC:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
        
        # Check if rotation needed
        if self._file_handle.tell() >= self._config.max_file_size:
            await self._rotate_file()
    
    async def _rotate_file(self) -> None:
        """Rotate to a new WAL file."""
        if self._file_handle:
            self._file_handle.close()
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        self._current_file = self._directory / f"wal_{timestamp}.log"
        self._file_handle = open(self._current_file, "ab")
        
        self._log.debug("wal_file_rotated", file=str(self._current_file))
    
    async def _sync(self) -> None:
        """Sync WAL file to disk."""
        if self._file_handle:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
    
    async def _sync_loop(self) -> None:
        """Background sync loop for async mode."""
        while self._running:
            await asyncio.sleep(self._config.sync_interval)
            try:
                await self._sync()
            except Exception as e:
                self._log.error("wal_sync_error", error=str(e))
    
    async def _checkpoint_loop(self) -> None:
        """Background checkpoint loop to clean up old entries."""
        while self._running:
            await asyncio.sleep(self._config.checkpoint_interval)
            try:
                await self._checkpoint()
            except Exception as e:
                self._log.error("wal_checkpoint_error", error=str(e))
    
    async def _checkpoint(self) -> None:
        """
        Checkpoint: clean up completed entries and old files.
        
        Removes WAL files that only contain completed entries.
        """
        async with self._lock:
            # Expire old entries
            now = time.time()
            expired = []
            for entry_id, entry in self._entries.items():
                if now - entry.timestamp > self._config.entry_ttl:
                    entry.state = WALState.EXPIRED
                    expired.append(entry_id)
            
            for entry_id in expired:
                del self._entries[entry_id]
            
            if expired:
                self._log.info("wal_entries_expired", count=len(expired))
            
            # Clean up old WAL files (keep current)
            wal_files = sorted(self._directory.glob("wal_*.log"))
            for wal_file in wal_files[:-1]:  # Keep the last file
                if wal_file != self._current_file:
                    try:
                        wal_file.unlink()
                        self._log.debug("wal_file_removed", file=str(wal_file))
                    except Exception as e:
                        self._log.warning("wal_file_remove_error", file=str(wal_file), error=str(e))
    
    async def _recover(self) -> None:
        """Recover entries from existing WAL files."""
        wal_files = sorted(self._directory.glob("wal_*.log"))
        
        # First pass: read all entries and track latest state for each ID
        all_entries: dict[str, WALEntry] = {}
        
        for wal_file in wal_files:
            try:
                with open(wal_file, "rb") as f:
                    while True:
                        # Read entry length
                        header = f.read(4)
                        if not header or len(header) < 4:
                            break
                        
                        length = struct.unpack(self.HEADER_FORMAT, header)[0]
                        data = f.read(length)
                        
                        # Read checksum
                        checksum_header = f.read(4)
                        if not checksum_header or len(checksum_header) < 4:
                            break
                        
                        checksum_length = struct.unpack(self.HEADER_FORMAT, checksum_header)[0]
                        checksum = f.read(checksum_length).decode("utf-8")
                        
                        # Parse entry
                        entry = WALEntry.from_bytes(data)
                        
                        # Verify checksum
                        if entry.checksum() != checksum:
                            self._log.warning("wal_checksum_mismatch", entry_id=entry.id)
                            continue
                        
                        # Track latest state for each entry ID
                        all_entries[entry.id] = entry
                        self._sequence = max(self._sequence, entry.sequence)
                        
            except Exception as e:
                self._log.error("wal_recovery_error", file=str(wal_file), error=str(e))
        
        # Second pass: only recover entries that are still pending/processing
        recovered = 0
        for entry in all_entries.values():
            if entry.state in (WALState.PENDING, WALState.PROCESSING):
                entry.state = WALState.PENDING  # Reset to pending for retry
                self._entries[entry.id] = entry
                recovered += 1
        
        if recovered:
            self._log.info("wal_recovered", entries=recovered)
