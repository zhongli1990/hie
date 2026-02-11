"""
OpenLI HIE — NHS Validation Business Process

Custom business process that validates and enriches HL7 messages
according to NHS standards before routing to downstream systems.

Registered as: custom.nhs.NHSValidationProcess

This is a DEVELOPER extension class — it lives in the custom.* namespace
and subclasses the core BusinessProcess base class. Developers should
use this as a reference for building their own custom processes.

IRIS Equivalent: A custom Ens.BusinessProcessBPL subclass with
NHS-specific validation logic.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import structlog

from Engine.li.hosts.base import BusinessProcess
from Engine.custom import register_host

if TYPE_CHECKING:
    from Engine.li.config import ItemConfig

logger = structlog.get_logger(__name__)


# NHS Number Modulus 11 check digit weights
_NHS_WEIGHTS = [10, 9, 8, 7, 6, 5, 4, 3, 2]

# UK postcode regex (simplified but covers standard formats)
_UK_POSTCODE_RE = re.compile(
    r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$',
    re.IGNORECASE,
)


def validate_nhs_number(nhs_number: str) -> tuple[bool, str]:
    """
    Validate an NHS Number using the Modulus 11 algorithm.

    The NHS Number is a 10-digit number where the last digit is a
    check digit calculated using a weighted Modulus 11 algorithm.

    Args:
        nhs_number: The NHS Number string (digits only, 10 chars)

    Returns:
        Tuple of (is_valid, reason)
    """
    # Strip whitespace and dashes
    cleaned = nhs_number.replace(" ", "").replace("-", "")

    if not cleaned.isdigit():
        return False, f"NHS Number contains non-numeric characters: '{nhs_number}'"

    if len(cleaned) != 10:
        return False, f"NHS Number must be 10 digits, got {len(cleaned)}: '{nhs_number}'"

    # Calculate check digit
    total = sum(int(cleaned[i]) * _NHS_WEIGHTS[i] for i in range(9))
    remainder = total % 11
    check_digit = 11 - remainder

    if check_digit == 11:
        check_digit = 0
    elif check_digit == 10:
        return False, f"NHS Number has invalid check digit (remainder=10): '{nhs_number}'"

    if check_digit != int(cleaned[9]):
        return False, (
            f"NHS Number check digit mismatch: expected {check_digit}, "
            f"got {cleaned[9]} in '{nhs_number}'"
        )

    return True, "Valid"


def validate_uk_postcode(postcode: str) -> tuple[bool, str]:
    """
    Validate a UK postcode format.

    Args:
        postcode: The postcode string

    Returns:
        Tuple of (is_valid, reason)
    """
    if not postcode or not postcode.strip():
        return False, "Postcode is empty"

    if _UK_POSTCODE_RE.match(postcode.strip()):
        return True, "Valid"

    return False, f"Invalid UK postcode format: '{postcode}'"


@register_host("custom.nhs.NHSValidationProcess")
class NHSValidationProcess(BusinessProcess):
    """
    NHS Validation, Enrichment & Normalisation Process.

    Validates HL7 messages against NHS standards:
    - NHS Number validation (Modulus 11 check digit)
    - PDS demographic lookup & enrichment (optional)
    - Duplicate admission detection (sliding window)
    - UK postcode validation
    - FHIR→HL7 normalisation (for messages from FHIR inbound)

    Settings (Host):
        ValidateNHSNumber:  Validate NHS Number in PID-3 (default: true)
        EnrichFromPDS:      Enrich demographics from PDS (default: false)
        PDSEndpoint:        PDS FHIR API endpoint URL
        PDSTimeout:         PDS lookup timeout in seconds (default: 5.0)
        CheckDuplicates:    Check for duplicate messages (default: true)
        DuplicateWindow:    Duplicate detection window in seconds (default: 60)
        ValidatePostcode:   Validate UK postcode in PID-11 (default: true)
        FHIRNormalisation:  Normalise FHIR-origin messages to HL7 (default: true)
        TargetConfigNames:  Next item(s) in the route
        OnValidationFail:   Action on failure: 'nack_and_exception_queue' or 'warn_and_continue'

    Example configuration via Portal:
        Name: NHS.Validation.Process
        Class: custom.nhs.NHSValidationProcess
        Pool Size: 4
        Host Settings:
            ValidateNHSNumber: true
            EnrichFromPDS: true
            PDSEndpoint: https://pds.spine.nhs.uk/api
            CheckDuplicates: true
            DuplicateWindow: 60
            ValidatePostcode: true
            TargetConfigNames: ADT.Content.Router

    IRIS Equivalent:
        A custom Ens.BusinessProcessBPL subclass with:
        - Call to PDS FHIR API via EnsLib.HTTP.OutboundAdapter
        - NHS Number validation in ObjectScript
        - Duplicate detection via ^CacheTemp globals
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

        # Configuration from host_settings
        self._validate_nhs = self._bool_setting("ValidateNHSNumber", True)
        self._enrich_pds = self._bool_setting("EnrichFromPDS", False)
        self._pds_endpoint = self.get_setting("Host", "PDSEndpoint", "")
        self._pds_timeout = float(self.get_setting("Host", "PDSTimeout", 5.0))
        self._check_duplicates = self._bool_setting("CheckDuplicates", True)
        self._duplicate_window = int(self.get_setting("Host", "DuplicateWindow", 60))
        self._validate_postcode = self._bool_setting("ValidatePostcode", True)
        self._fhir_normalisation = self._bool_setting("FHIRNormalisation", True)
        self._on_fail = self.get_setting("Host", "OnValidationFail", "nack_and_exception_queue")

        # Duplicate detection state (in-memory sliding window)
        self._recent_messages: dict[str, float] = {}

        self._log = logger.bind(
            host="NHSValidationProcess",
            name=name,
        )

    def _bool_setting(self, key: str, default: bool) -> bool:
        """Get a boolean host setting."""
        val = self.get_setting("Host", key, str(default))
        return str(val).lower() in ("true", "1", "yes")

    async def on_start(self) -> None:
        """Initialize the validation process."""
        await super().on_start()
        self._log.info(
            "nhs_validation_started",
            validate_nhs=self._validate_nhs,
            enrich_pds=self._enrich_pds,
            check_duplicates=self._check_duplicates,
            validate_postcode=self._validate_postcode,
            fhir_normalisation=self._fhir_normalisation,
        )

    async def on_message(self, message: Any) -> Any:
        """
        Validate and enrich an HL7 message.

        Processing pipeline:
        1. FHIR normalisation (if message originated from FHIR inbound)
        2. NHS Number validation (PID-3, Modulus 11)
        3. PDS demographic enrichment (optional)
        4. Duplicate detection (sliding window)
        5. UK postcode validation (PID-11)
        6. Forward to target or reject

        Args:
            message: HL7Message from an inbound service

        Returns:
            Validated/enriched message, or raises on hard failure
        """
        start_time = time.time()
        warnings: list[str] = []
        errors: list[str] = []

        # Import here to avoid circular imports at module level
        from Engine.li.hosts.hl7 import HL7Message

        if not isinstance(message, HL7Message):
            self._log.warning("non_hl7_message_received", type=type(message).__name__)
            return message

        parsed = message.parsed
        if not parsed:
            errors.append("Message has no parsed view — cannot validate")
            return self._handle_result(message, errors, warnings, start_time)

        # ── Step 1: FHIR normalisation ──
        sending_app = parsed.get_field("MSH-3", "")
        if self._fhir_normalisation and "FHIR" in str(sending_app).upper():
            self._log.debug("fhir_origin_detected", sending_app=sending_app)
            # FHIR-origin messages are already normalised to HL7 by the
            # FHIRHTTPService — we just tag them for routing rules
            # (actual FHIR→HL7 conversion happens in the inbound service)

        # ── Step 2: NHS Number validation ──
        if self._validate_nhs:
            nhs_number = str(parsed.get_field("PID-3.1", ""))
            if nhs_number:
                is_valid, reason = validate_nhs_number(nhs_number)
                if not is_valid:
                    errors.append(f"NHS Number validation failed: {reason}")
                    self._log.warning("nhs_number_invalid", nhs_number=nhs_number[:4] + "******", reason=reason)
                else:
                    self._log.debug("nhs_number_valid", nhs_number=nhs_number[:4] + "******")
            else:
                warnings.append("No NHS Number found in PID-3.1")

        # ── Step 3: PDS enrichment ──
        if self._enrich_pds and self._pds_endpoint:
            nhs_number = str(parsed.get_field("PID-3.1", ""))
            if nhs_number:
                pds_result = await self._lookup_pds(nhs_number)
                if pds_result:
                    self._log.debug("pds_enrichment_applied", nhs_number=nhs_number[:4] + "******")
                else:
                    warnings.append("PDS lookup returned no data — continuing with original demographics")

        # ── Step 4: Duplicate detection ──
        if self._check_duplicates:
            is_dup, dup_key = self._check_duplicate(message)
            if is_dup:
                errors.append(f"Duplicate message detected (key: {dup_key})")
                self._log.warning("duplicate_detected", key=dup_key)

        # ── Step 5: UK postcode validation ──
        if self._validate_postcode:
            postcode = str(parsed.get_field("PID-11.5", ""))
            if postcode:
                is_valid, reason = validate_uk_postcode(postcode)
                if not is_valid:
                    # Postcode failure is a warning, not a hard error
                    warnings.append(f"Postcode validation: {reason}")
                    self._log.debug("postcode_warning", postcode=postcode, reason=reason)

        return self._handle_result(message, errors, warnings, start_time)

    def _handle_result(
        self,
        message: Any,
        errors: list[str],
        warnings: list[str],
        start_time: float,
    ) -> Any:
        """Handle validation result — forward or reject."""
        latency_ms = int((time.time() - start_time) * 1000)

        if errors:
            self._metrics.errors += 1
            if self._on_fail == "nack_and_exception_queue":
                self._log.error(
                    "validation_failed",
                    errors=errors,
                    warnings=warnings,
                    latency_ms=latency_ms,
                )
                # In production, this would NACK the sender and queue
                # the message for manual review
                raise ValidationError("; ".join(errors))
            else:
                # warn_and_continue — log but forward anyway
                self._log.warning(
                    "validation_warnings",
                    errors=errors,
                    warnings=warnings,
                    latency_ms=latency_ms,
                )

        if warnings:
            self._log.info("validation_passed_with_warnings", warnings=warnings, latency_ms=latency_ms)
        else:
            self._log.debug("validation_passed", latency_ms=latency_ms)

        self._metrics.messages_processed += 1
        return message

    def _check_duplicate(self, message: Any) -> tuple[bool, str]:
        """
        Check if this message is a duplicate within the sliding window.

        Key: NHS Number + Message Type + Sending Application
        """
        parsed = message.parsed
        if not parsed:
            return False, ""

        nhs_number = str(parsed.get_field("PID-3.1", ""))
        msg_type = str(parsed.get_field("MSH-9", ""))
        sending_app = str(parsed.get_field("MSH-3", ""))
        key = f"{nhs_number}|{msg_type}|{sending_app}"

        now = time.time()

        # Purge expired entries
        cutoff = now - self._duplicate_window
        expired = [k for k, t in self._recent_messages.items() if t < cutoff]
        for k in expired:
            del self._recent_messages[k]

        # Check for duplicate
        if key in self._recent_messages:
            return True, key

        # Record this message
        self._recent_messages[key] = now
        return False, key

    async def _lookup_pds(self, nhs_number: str) -> dict[str, Any] | None:
        """
        Look up patient demographics from PDS (Personal Demographics Service).

        In production, this calls the NHS Spine PDS FHIR API.
        Currently returns None (stub for future implementation).

        Args:
            nhs_number: The NHS Number to look up

        Returns:
            PDS demographics dict, or None if not found/timeout
        """
        # TODO: Implement actual PDS FHIR API call
        # GET {self._pds_endpoint}/Patient/{nhs_number}
        # Headers: Authorization: Bearer {spine_token}
        self._log.debug("pds_lookup_stub", nhs_number=nhs_number[:4] + "******")
        return None


class ValidationError(Exception):
    """Raised when message validation fails with hard errors."""
    pass
