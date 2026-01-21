"""
File Receiver - Watches directories for incoming files.

Supports consuming text, CSV, HL7, and other file types from watched directories.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from watchfiles import awatch, Change

from hie.core.item import Receiver
from hie.core.message import Message, Priority
from hie.core.config import FileReceiverConfig

logger = structlog.get_logger(__name__)


# Content type mapping based on file extension
EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".hl7": "x-application/hl7-v2+er7",
    ".hl7v2": "x-application/hl7-v2+er7",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xml": "application/xml",
    ".fhir": "application/fhir+json",
}


class FileReceiver(Receiver):
    """
    File receiver that watches directories for incoming files.
    
    Features:
    - Directory watching with configurable patterns
    - Automatic content type detection
    - Move or delete processed files
    - Recursive directory watching
    - Polling fallback for network filesystems
    """
    
    def __init__(self, config: FileReceiverConfig) -> None:
        super().__init__(config)
        self._file_config = config
        self._watch_path = Path(config.watch_directory)
        self._processed_files: set[str] = set()
        self._logger = logger.bind(item_id=self.id)
    
    @property
    def file_config(self) -> FileReceiverConfig:
        """File-specific configuration."""
        return self._file_config
    
    async def _on_start(self) -> None:
        """Validate watch directory exists."""
        if not self._watch_path.exists():
            raise FileNotFoundError(f"Watch directory not found: {self._watch_path}")
        
        if not self._watch_path.is_dir():
            raise NotADirectoryError(f"Watch path is not a directory: {self._watch_path}")
        
        # Create move_to directory if specified
        if self._file_config.move_to:
            move_path = Path(self._file_config.move_to)
            move_path.mkdir(parents=True, exist_ok=True)
        
        self._logger.info(
            "file_receiver_started",
            watch_directory=str(self._watch_path),
            patterns=self._file_config.patterns
        )
        
        # Process any existing files
        await self._process_existing_files()
    
    async def _receive_loop(self) -> None:
        """Watch directory for new files."""
        try:
            async for changes in awatch(
                self._watch_path,
                recursive=self._file_config.recursive,
                step=int(self._file_config.poll_interval * 1000),
                stop_event=self._shutdown_event,
            ):
                for change_type, path_str in changes:
                    if self._shutdown_event.is_set():
                        return
                    
                    if change_type == Change.added:
                        path = Path(path_str)
                        if self._matches_patterns(path):
                            await self._process_file(path)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error("watch_error", error=str(e))
            raise
    
    async def _process_existing_files(self) -> None:
        """Process any files that already exist in the watch directory."""
        patterns = self._file_config.patterns
        
        for pattern in patterns:
            if self._file_config.recursive:
                files = list(self._watch_path.rglob(pattern))
            else:
                files = list(self._watch_path.glob(pattern))
            
            for file_path in sorted(files):
                if file_path.is_file():
                    await self._process_file(file_path)
    
    def _matches_patterns(self, path: Path) -> bool:
        """Check if a file matches the configured patterns."""
        if not path.is_file():
            return False
        
        for pattern in self._file_config.patterns:
            if path.match(pattern):
                return True
        
        return False
    
    async def _process_file(self, path: Path) -> None:
        """Process a single file."""
        # Skip if already processed (handles duplicate events)
        path_str = str(path.absolute())
        if path_str in self._processed_files:
            return
        
        self._processed_files.add(path_str)
        
        try:
            # Wait briefly to ensure file is fully written
            await asyncio.sleep(0.1)
            
            # Check file still exists
            if not path.exists():
                self._logger.debug("file_disappeared", path=path_str)
                return
            
            # Read file content
            content = await asyncio.to_thread(path.read_bytes)
            
            if not content:
                self._logger.warning("empty_file", path=path_str)
                return
            
            # Record metrics
            self._metrics.record_received(len(content))
            
            # Determine content type from extension
            content_type = EXTENSION_CONTENT_TYPES.get(
                path.suffix.lower(),
                "application/octet-stream"
            )
            
            # Create message
            message = Message.create(
                raw=content,
                content_type=content_type,
                source=self.id,
                message_type=f"file:{path.suffix.lstrip('.')}",
            )
            
            # Add file metadata as properties
            from hie.core.message import Property, PropertyType
            message = message.with_property(
                "source_filename",
                Property(value=path.name, type=PropertyType.STRING)
            ).with_property(
                "source_path",
                Property(value=str(path.absolute()), type=PropertyType.STRING)
            )
            
            # Submit for processing
            await self.submit(message)
            
            self._logger.debug(
                "file_received",
                message_id=str(message.id),
                path=path_str,
                size=len(content)
            )
            
            # Handle processed file
            await self._handle_processed_file(path)
        
        except Exception as e:
            self._logger.error("file_processing_failed", path=path_str, error=str(e))
            self._metrics.record_failure(str(e))
        
        finally:
            # Allow reprocessing if file reappears
            self._processed_files.discard(path_str)
    
    async def _handle_processed_file(self, path: Path) -> None:
        """Handle a file after it has been processed (move or delete)."""
        try:
            if self._file_config.move_to:
                # Move to processed directory
                dest_dir = Path(self._file_config.move_to)
                dest_path = dest_dir / path.name
                
                # Handle name conflicts
                if dest_path.exists():
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                    dest_path = dest_dir / f"{path.stem}_{timestamp}{path.suffix}"
                
                await asyncio.to_thread(shutil.move, str(path), str(dest_path))
                self._logger.debug("file_moved", source=str(path), dest=str(dest_path))
            
            elif self._file_config.delete_after:
                # Delete the file
                await asyncio.to_thread(path.unlink)
                self._logger.debug("file_deleted", path=str(path))
        
        except Exception as e:
            self._logger.error(
                "file_cleanup_failed",
                path=str(path),
                error=str(e)
            )
    
    @classmethod
    def from_config(cls, config: dict[str, Any] | FileReceiverConfig) -> FileReceiver:
        """Create a FileReceiver from configuration."""
        if isinstance(config, dict):
            config = FileReceiverConfig.model_validate(config)
        return cls(config)
