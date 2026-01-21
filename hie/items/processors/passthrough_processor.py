"""
Passthrough Processor - Forwards messages without modification.

Useful for testing, logging, or as a placeholder in routes.
"""

from __future__ import annotations

import structlog

from hie.core.item import Processor, ItemConfig
from hie.core.message import Message

logger = structlog.get_logger(__name__)


class PassthroughProcessor(Processor):
    """
    A processor that forwards messages unchanged.
    
    Useful for:
    - Testing route configurations
    - Adding logging/monitoring points
    - Placeholder during development
    """
    
    def __init__(self, config: ItemConfig) -> None:
        super().__init__(config)
        self._logger = logger.bind(item_id=self.id)
    
    async def _process(self, message: Message) -> Message:
        """Forward message unchanged."""
        self._logger.debug(
            "message_passthrough",
            message_id=str(message.id),
            message_type=message.envelope.message_type
        )
        return message
