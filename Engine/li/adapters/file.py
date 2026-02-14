"""
LI File Adapters

Implements file-based message transport for HL7v2 and other message formats.
Polls a directory for inbound files and writes outbound messages to files.

IRIS equivalents:
    - EnsLib.File.InboundAdapter  (polls FilePath for files matching FileSpec)
    - EnsLib.File.OutboundAdapter (writes to FilePath with configurable naming)

Rhapsody equivalent: File Communication Point (Input/Output modes)
Mirth equivalent:    File Reader / File Writer connectors
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

import structlog

from Engine.li.adapters.base import InboundAdapter, OutboundAdapter, AdapterState

if TYPE_CHECKING:
    from Engine.li.hosts.base import Host

logger = structlog.get_logger(__name__)

# Default settings
DEFAULT_POLL_INTERVAL = 5.0       # seconds between directory scans
DEFAULT_FILE_SPEC = "*.hl7"       # glob pattern for inbound files
DEFAULT_ARCHIVE_PATH = "archive"  # subdirectory for processed files
DEFAULT_WORK_PATH = "work"        # subdirectory for in-progress files


class FileAdapterError(Exception):
    """Error during file adapter operation."""
    pass


class InboundFileAdapter(InboundAdapter):
    """
    File Inbound Adapter — polls a directory for message files.

    Watches a configured directory for files matching a glob pattern.
    Each file is read, passed to the host for processing, then moved
    to an archive directory (or deleted, based on configuration).

    IRIS equivalent: EnsLib.File.InboundAdapter
    Rhapsody equivalent: File Communication Point (Input mode)
    Mirth equivalent: File Reader connector

    Settings:
        FilePath:       Directory to poll for inbound files (required)
        FileSpec:       Glob pattern for matching files (default: *.hl7)
        PollInterval:   Seconds between directory scans (default: 5)
        ArchivePath:    Directory for processed files (default: FilePath/archive)
                        Set to "" to delete files after processing.
        WorkPath:       Directory for in-progress files (default: FilePath/work)
        Charset:        Character encoding for reading files (default: utf-8)
        SemaphoreSpec:  Glob pattern for semaphore files (optional)
                        If set, only process data files when matching semaphore exists.
    """

    def __init__(self, host: Host, settings: dict[str, Any] | None = None):
        super().__init__(host, settings)

        # Configuration
        self._file_path = Path(self.get_setting("FilePath", "."))
        self._file_spec = self.get_setting("FileSpec", DEFAULT_FILE_SPEC)
        self._poll_interval = float(self.get_setting("PollInterval", DEFAULT_POLL_INTERVAL))
        self._archive_path_str = self.get_setting("ArchivePath", DEFAULT_ARCHIVE_PATH)
        self._work_path_str = self.get_setting("WorkPath", DEFAULT_WORK_PATH)
        self._charset = self.get_setting("Charset", "utf-8")
        self._semaphore_spec = self.get_setting("SemaphoreSpec", None)

        # Derived paths
        self._archive_path: Path | None = None
        self._work_path: Path | None = None

        # Runtime
        self._poll_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        self._log = logger.bind(
            adapter="InboundFileAdapter",
            host=host.name,
            file_path=str(self._file_path),
            file_spec=self._file_spec,
        )

    async def on_start(self) -> None:
        """Create directories and start polling."""
        self._shutdown_event.clear()

        # Ensure directories exist
        self._file_path.mkdir(parents=True, exist_ok=True)

        if self._archive_path_str:
            if os.path.isabs(self._archive_path_str):
                self._archive_path = Path(self._archive_path_str)
            else:
                self._archive_path = self._file_path / self._archive_path_str
            self._archive_path.mkdir(parents=True, exist_ok=True)

        if self._work_path_str:
            if os.path.isabs(self._work_path_str):
                self._work_path = Path(self._work_path_str)
            else:
                self._work_path = self._file_path / self._work_path_str
            self._work_path.mkdir(parents=True, exist_ok=True)

        self._log.info(
            "file_inbound_adapter_started",
            poll_interval=self._poll_interval,
            archive_path=str(self._archive_path) if self._archive_path else "(delete)",
        )

    async def on_stop(self) -> None:
        """Stop polling."""
        self._shutdown_event.set()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        self._log.info("file_inbound_adapter_stopped")

    async def listen(self) -> None:
        """
        Main polling loop — scans directory at configured interval.

        Called by the host after adapter start. Runs until stopped.
        """
        self._poll_task = asyncio.current_task()

        while not self._shutdown_event.is_set():
            try:
                await self._poll_directory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._log.error("file_poll_error", error=str(e))
                self._metrics.errors_total += 1

            # Wait for next poll interval (interruptible)
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._poll_interval,
                )
                break  # shutdown_event was set
            except asyncio.TimeoutError:
                continue  # normal timeout, poll again

    async def _poll_directory(self) -> None:
        """Scan directory for matching files and process each one."""
        # List matching files, sorted by modification time (oldest first)
        try:
            files = sorted(
                self._file_path.glob(self._file_spec),
                key=lambda f: f.stat().st_mtime,
            )
        except OSError as e:
            self._log.warning("file_list_error", error=str(e))
            return

        # Filter out directories, work/archive subdirs, and semaphore files
        files = [
            f for f in files
            if f.is_file()
            and f.parent == self._file_path  # only top-level
        ]

        if not files:
            return

        self._log.debug("files_found", count=len(files))

        for file_path in files:
            if self._shutdown_event.is_set():
                break

            # Check semaphore if configured
            if self._semaphore_spec:
                sem_name = file_path.stem + Path(self._semaphore_spec).suffix
                sem_path = self._file_path / sem_name
                if not sem_path.exists():
                    continue  # skip until semaphore appears

            await self._process_file(file_path)

    async def _process_file(self, file_path: Path) -> None:
        """
        Process a single inbound file.

        1. Move to work directory (atomic claim)
        2. Read contents
        3. Pass to host via on_data_received
        4. Move to archive (or delete)
        """
        work_file = None
        try:
            # Step 1: Move to work directory (prevents double-processing)
            if self._work_path:
                work_file = self._work_path / file_path.name
                shutil.move(str(file_path), str(work_file))
                read_path = work_file
            else:
                read_path = file_path

            # Step 2: Read file contents
            data = await asyncio.to_thread(read_path.read_bytes)

            self._metrics.bytes_received += len(data)
            self._metrics.last_activity_at = datetime.now(timezone.utc)

            self._log.debug(
                "file_message_received",
                filename=file_path.name,
                size=len(data),
            )

            # Step 3: Pass to host
            result = await self.on_data_received(data)

            # Step 4: Archive or delete
            if self._archive_path:
                # Add timestamp to avoid name collisions
                ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                archive_name = f"{file_path.stem}_{ts}{file_path.suffix}"
                archive_file = self._archive_path / archive_name
                source = work_file if work_file else file_path
                shutil.move(str(source), str(archive_file))
                self._log.debug("file_archived", filename=archive_name)
            else:
                # Delete after processing
                source = work_file if work_file else file_path
                source.unlink(missing_ok=True)

            # Clean up semaphore if it exists
            if self._semaphore_spec:
                sem_name = file_path.stem + Path(self._semaphore_spec).suffix
                sem_path = self._file_path / sem_name
                sem_path.unlink(missing_ok=True)

        except Exception as e:
            self._log.error(
                "file_processing_error",
                filename=file_path.name,
                error=str(e),
            )
            self._metrics.errors_total += 1

            # Move failed file back from work to original location
            if work_file and work_file.exists():
                try:
                    shutil.move(str(work_file), str(file_path))
                except Exception:
                    pass


class OutboundFileAdapter(OutboundAdapter):
    """
    File Outbound Adapter — writes messages to files.

    Writes each message to a file in the configured directory.
    Supports configurable file naming, overwrite modes, and
    optional temporary file + rename for atomic writes.

    IRIS equivalent: EnsLib.File.OutboundAdapter
    Rhapsody equivalent: File Communication Point (Output mode)
    Mirth equivalent: File Writer connector

    Settings:
        FilePath:       Directory to write outbound files (required)
        Filename:       Filename pattern (default: msg_%timestamp%_%id%.hl7)
                        Supports: %timestamp%, %id%, %type%, %date%, %time%
        Overwrite:      Overwrite mode: "error"|"overwrite"|"append" (default: error)
        Charset:        Character encoding for writing (default: utf-8)
        TempFileSuffix: Suffix for temp files during write (default: .tmp)
                        Set to "" to disable atomic write.
        OpenMode:       "write"|"append" (default: write)
    """

    def __init__(self, host: Host, settings: dict[str, Any] | None = None):
        super().__init__(host, settings)

        # Configuration
        self._file_path = Path(self.get_setting("FilePath", "."))
        self._filename_pattern = self.get_setting("Filename", "msg_%timestamp%_%id%.hl7")
        self._overwrite = self.get_setting("Overwrite", "error")
        self._charset = self.get_setting("Charset", "utf-8")
        self._temp_suffix = self.get_setting("TempFileSuffix", ".tmp")
        self._open_mode = self.get_setting("OpenMode", "write")

        self._log = logger.bind(
            adapter="OutboundFileAdapter",
            host=host.name,
            file_path=str(self._file_path),
        )

    async def on_start(self) -> None:
        """Ensure output directory exists."""
        self._file_path.mkdir(parents=True, exist_ok=True)
        self._log.info("file_outbound_adapter_started")

    async def on_stop(self) -> None:
        """Nothing to clean up."""
        self._log.info("file_outbound_adapter_stopped")

    def _resolve_filename(self, message: Any = None) -> str:
        """
        Resolve filename pattern with runtime values.

        Supports placeholders:
            %timestamp% — ISO timestamp (compact)
            %id%        — UUID
            %date%      — YYYYMMDD
            %time%      — HHMMSS
            %type%      — message type if available
        """
        now = datetime.now(timezone.utc)
        name = self._filename_pattern
        name = name.replace("%timestamp%", now.strftime("%Y%m%d_%H%M%S_%f"))
        name = name.replace("%date%", now.strftime("%Y%m%d"))
        name = name.replace("%time%", now.strftime("%H%M%S"))
        name = name.replace("%id%", str(uuid4())[:8])

        # Extract message type if available
        msg_type = "unknown"
        if hasattr(message, "parsed") and message.parsed:
            try:
                msg_type = message.parsed.get_message_type() or "unknown"
            except Exception:
                pass
        elif hasattr(message, "message_type"):
            msg_type = message.message_type or "unknown"
        name = name.replace("%type%", msg_type.replace("^", "_"))

        return name

    async def send(self, message: Any) -> Any:
        """
        Write a message to a file.

        Args:
            message: Message to write (bytes, or object with .raw attribute)

        Returns:
            Path to the written file (as string)

        Raises:
            FileAdapterError: If write fails
        """
        # Extract bytes
        if isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
        else:
            data = str(message).encode(self._charset)

        filename = self._resolve_filename(message)
        target_path = self._file_path / filename

        # Check overwrite policy
        if target_path.exists():
            if self._overwrite == "error":
                raise FileAdapterError(f"File already exists: {target_path}")
            elif self._overwrite == "append":
                return await self._append_to_file(target_path, data)

        try:
            if self._temp_suffix:
                # Atomic write: write to temp, then rename
                temp_path = target_path.with_suffix(target_path.suffix + self._temp_suffix)
                await asyncio.to_thread(temp_path.write_bytes, data)
                await asyncio.to_thread(temp_path.rename, target_path)
            else:
                await asyncio.to_thread(target_path.write_bytes, data)

            self._metrics.bytes_sent += len(data)
            self._metrics.last_activity_at = datetime.now(timezone.utc)
            await self.on_send(data)

            self._log.debug(
                "file_message_written",
                filename=filename,
                size=len(data),
            )

            return str(target_path)

        except Exception as e:
            self._metrics.errors_total += 1
            raise FileAdapterError(f"Failed to write file {filename}: {e}")

    async def _append_to_file(self, path: Path, data: bytes) -> str:
        """Append data to an existing file."""
        try:
            def _do_append():
                with open(path, "ab") as f:
                    f.write(data)

            await asyncio.to_thread(_do_append)

            self._metrics.bytes_sent += len(data)
            self._metrics.last_activity_at = datetime.now(timezone.utc)
            await self.on_send(data)

            self._log.debug("file_message_appended", filename=path.name, size=len(data))
            return str(path)

        except Exception as e:
            self._metrics.errors_total += 1
            raise FileAdapterError(f"Failed to append to {path.name}: {e}")
