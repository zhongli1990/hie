"""
File Sender - Writes messages to files in a directory.

Supports exporting transformed HL7v2, CSV, and other file types.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from hie.core.item import Sender
from hie.core.message import Message
from hie.core.config import FileSenderConfig

logger = structlog.get_logger(__name__)


class FileSender(Sender):
    """
    File sender that writes messages to a directory.
    
    Features:
    - Configurable filename patterns
    - Automatic directory creation
    - Overwrite protection
    - Atomic writes (write to temp, then rename)
    """
    
    def __init__(self, config: FileSenderConfig) -> None:
        super().__init__(config)
        self._file_config = config
        self._output_path = Path(config.output_directory)
        self._logger = logger.bind(item_id=self.id)
    
    @property
    def file_config(self) -> FileSenderConfig:
        """File-specific configuration."""
        return self._file_config
    
    async def _on_start(self) -> None:
        """Ensure output directory exists."""
        if self._file_config.create_directory:
            self._output_path.mkdir(parents=True, exist_ok=True)
        
        if not self._output_path.exists():
            raise FileNotFoundError(f"Output directory not found: {self._output_path}")
        
        if not self._output_path.is_dir():
            raise NotADirectoryError(f"Output path is not a directory: {self._output_path}")
        
        self._logger.info(
            "file_sender_started",
            output_directory=str(self._output_path)
        )
    
    async def _on_stop(self) -> None:
        """Cleanup on stop."""
        self._logger.info("file_sender_stopped")
    
    async def _send(self, message: Message) -> bool:
        """Write message to file."""
        try:
            # Generate filename
            filename = self._generate_filename(message)
            file_path = self._output_path / filename
            
            # Check for existing file
            if file_path.exists() and not self._file_config.overwrite:
                # Add timestamp to make unique
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                stem = file_path.stem
                suffix = file_path.suffix
                file_path = self._output_path / f"{stem}_{timestamp}{suffix}"
            
            # Write atomically (to temp file, then rename)
            temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
            
            await asyncio.to_thread(temp_path.write_bytes, message.raw)
            await asyncio.to_thread(temp_path.rename, file_path)
            
            self._logger.debug(
                "file_written",
                message_id=str(message.id),
                path=str(file_path),
                size=message.payload.size
            )
            
            return True
        
        except Exception as e:
            self._logger.error(
                "file_write_failed",
                message_id=str(message.id),
                error=str(e)
            )
            raise
    
    def _generate_filename(self, message: Message) -> str:
        """Generate filename from pattern and message properties."""
        pattern = self._file_config.filename_pattern
        
        # Available substitutions
        now = datetime.now(timezone.utc)
        substitutions = {
            "message_id": str(message.id),
            "timestamp": now.strftime("%Y%m%d_%H%M%S"),
            "timestamp_ms": now.strftime("%Y%m%d_%H%M%S_%f"),
            "date": now.strftime("%Y%m%d"),
            "time": now.strftime("%H%M%S"),
            "message_type": message.envelope.message_type.replace("^", "_").replace(":", "_"),
            "correlation_id": str(message.envelope.correlation_id),
        }
        
        # Add any string properties from the message
        for key, prop in message.payload.properties.items():
            if hasattr(prop, "value") and isinstance(prop.value, str):
                # Sanitize for filename
                safe_value = "".join(
                    c if c.isalnum() or c in "-_." else "_"
                    for c in prop.value
                )
                substitutions[key] = safe_value
        
        # Apply substitutions
        filename = pattern
        for key, value in substitutions.items():
            filename = filename.replace(f"{{{key}}}", value)
        
        # Sanitize final filename
        filename = "".join(
            c if c.isalnum() or c in "-_." else "_"
            for c in filename
        )
        
        return filename
    
    @classmethod
    def from_config(cls, config: dict[str, Any] | FileSenderConfig) -> FileSender:
        """Create a FileSender from configuration."""
        if isinstance(config, dict):
            config = FileSenderConfig.model_validate(config)
        return cls(config)
