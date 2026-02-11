"""
OpenLI HIE — Example Custom Business Process
==============================================

Copy this file as a starting template for your own custom process.

Steps to create your own:
1. Copy this directory: cp -r Engine/custom/_example Engine/custom/myorg
2. Rename this file to match your class purpose
3. Update the @register_host decorator with your class name
4. Implement your on_message() logic
5. Configure via Portal or API using class_name="custom.myorg.MyProcess"

Namespace Rules:
    ✅ custom.myorg.MyProcess       — Correct
    ✅ custom.nhs.NHSValidation     — Correct
    ❌ li.hosts.myprocess.MyProcess — FORBIDDEN (protected namespace)
    ❌ Engine.li.hosts.MyProcess    — FORBIDDEN (protected namespace)
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import structlog

from Engine.li.hosts.base import BusinessProcess
from Engine.custom import register_host

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────
# IMPORTANT: Change "custom._example.ExampleProcess" to your own name
# e.g. "custom.myorg.PatientEnrichmentProcess"
# ──────────────────────────────────────────────────────────────────────
@register_host("custom._example.ExampleProcess")
class ExampleProcess(BusinessProcess):
    """
    Example custom business process.

    This process receives messages from upstream services/processes,
    applies custom logic, and forwards to downstream targets.

    Settings (Host):
        TargetConfigNames:  Comma-separated list of downstream items
        MyCustomSetting:    Your custom setting (default: "default_value")

    Configure via Portal:
        Name: My.Custom.Process
        Class: custom._example.ExampleProcess
        Host Settings:
            TargetConfigNames: Next.Item.Name
            MyCustomSetting: my_value
    """

    def __init__(
        self,
        name: str,
        config: "ItemConfig | None" = None,
        pool_size: int = 1,
        enabled: bool = True,
        adapter_settings: dict[str, Any] | None = None,
        host_settings: dict[str, Any] | None = None,
    ):
        super().__init__(
            name=name,
            config=config,
            pool_size=pool_size,
            enabled=enabled,
            adapter_settings=adapter_settings,
            host_settings=host_settings,
        )

        # Read your custom settings from host_settings
        self._my_setting = self.get_setting("Host", "MyCustomSetting", "default_value")

        self._log = logger.bind(host="ExampleProcess", name=name)

    async def on_start(self) -> None:
        """Called when the production starts this item."""
        await super().on_start()
        self._log.info("example_process_started", my_setting=self._my_setting)

    async def on_message(self, message: Any) -> Any:
        """
        Process an incoming message.

        This is where your custom business logic goes.

        Args:
            message: The message from the upstream item (typically HL7Message)

        Returns:
            The message (modified or unchanged) to forward to targets
        """
        self._log.debug("processing_message", message_type=type(message).__name__)

        # ── Your custom logic here ──
        # Example: inspect HL7 message fields
        #
        # from Engine.li.hosts.hl7 import HL7Message
        # if isinstance(message, HL7Message) and message.parsed:
        #     patient_id = message.parsed.get_field("PID-3.1", "")
        #     msg_type = message.parsed.get_message_type()
        #     self._log.info("processing", patient_id=patient_id, msg_type=msg_type)

        # Update metrics
        self._metrics.messages_processed += 1

        # Return the message to forward to TargetConfigNames
        return message

    async def on_stop(self) -> None:
        """Called when the production stops this item."""
        self._log.info("example_process_stopped")
        await super().on_stop()
