"""
NHS Validation Process

Custom business process demonstrating advanced validation, enrichment,
and conditional routing for NHS acute trust integration.

Features:
- NHS Number validation (check digit algorithm)
- PDS (Patient Demographic Service) lookup simulation
- Duplicate admission detection
- UK postcode validation
- Conditional routing based on validation results
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any

import structlog

from Engine.li.hosts.base import Host, HostState
from Engine.core.messaging import MessageBroker

logger = structlog.get_logger(__name__)


class NHSValidationProcess(Host, MessageBroker):
    """
    Custom NHS-specific validation and enrichment process.

    Performs comprehensive validation before routing to downstream systems:
    1. NHS Number validation (Modulus 11 check digit)
    2. PDS lookup for patient demographics (simulated)
    3. Duplicate admission detection
    4. UK postcode validation
    5. Conditional routing based on validation results
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        MessageBroker.__init__(self)
        self._duplicate_cache = set()  # Simple duplicate detection cache
        self._log = logger.bind(host=self.name)

    async def on_init(self) -> None:
        """Initialize the validation process."""
        self._log.info("nhs_validation_process_initialized",
                       validate_nhs_number=self.get_setting("Host", "ValidateNHSNumber", True),
                       enrich_from_pds=self.get_setting("Host", "EnrichFromPDS", False),
                       check_duplicates=self.get_setting("Host", "CheckDuplicates", True))

    async def on_teardown(self) -> None:
        """Cleanup validation process."""
        self._duplicate_cache.clear()

    async def on_process_input(self, message: Any) -> Any:
        """
        Process and validate HL7 message.

        Args:
            message: HL7 message object

        Returns:
            Validated and enriched message, or None if validation fails
        """
        self._log.info("processing_message",
                       message_type=str(message.MSH.MessageType) if hasattr(message, 'MSH') else "unknown")

        # Extract NHS Number from PID segment
        try:
            nhs_number = self._extract_nhs_number(message)
        except Exception as e:
            self._log.error("failed_to_extract_nhs_number", error=str(e))
            return await self._generate_nack(message, "Failed to extract NHS Number")

        # 1. Validate NHS Number
        if self.get_setting("Host", "ValidateNHSNumber", True):
            if not self._validate_nhs_number(nhs_number):
                self._log.error("invalid_nhs_number", nhs_number=nhs_number)
                return await self._generate_nack(message, f"Invalid NHS Number: {nhs_number}")
            self._log.debug("nhs_number_valid", nhs_number=nhs_number)

        # 2. Enrich from PDS (simulated)
        if self.get_setting("Host", "EnrichFromPDS", False):
            try:
                enriched_message = await self._enrich_from_pds(message, nhs_number)
                if enriched_message:
                    message = enriched_message
                    self._log.info("message_enriched_from_pds", nhs_number=nhs_number)
            except Exception as e:
                self._log.warning("pds_enrichment_failed", error=str(e))
                # Continue without enrichment

        # 3. Check for duplicates
        if self.get_setting("Host", "CheckDuplicates", True):
            admission_key = self._generate_admission_key(message)
            if admission_key in self._duplicate_cache:
                self._log.warning("duplicate_admission_detected",
                                  admission_key=admission_key,
                                  nhs_number=nhs_number)

                # Route to exception handler
                if self._service_registry:
                    await self.send_request_async("Exception_Handler", message)

                return None  # Don't route to normal flow

            # Add to cache
            self._duplicate_cache.add(admission_key)
            # Limit cache size
            if len(self._duplicate_cache) > 10000:
                self._duplicate_cache.pop()

        # 4. Validate postcode
        if self.get_setting("Host", "ValidatePostcode", True):
            postcode = self._extract_postcode(message)
            if postcode and not self._validate_uk_postcode(postcode):
                self._log.warning("invalid_postcode", postcode=postcode, nhs_number=nhs_number)
                # Add validation warning to message (Z-segment)
                # Continue processing but flag for review

        # 5. Route to downstream systems
        self._log.info("message_validated_successfully", nhs_number=nhs_number)

        # Send to ADT Router for downstream routing
        if self._service_registry:
            await self.send_request_async("ADT_Router", message)

        return message

    def _extract_nhs_number(self, message: Any) -> str:
        """Extract NHS Number from PID segment."""
        # HL7 PID-3: Patient Identifier List
        # Format: ID^Type^AssigningAuthority
        # NHS Number typically: 9876543210^^^NHS
        if hasattr(message, 'PID') and hasattr(message.PID, 'PatientIdentifierList'):
            identifiers = message.PID.PatientIdentifierList
            if isinstance(identifiers, list):
                for identifier in identifiers:
                    if 'NHS' in str(identifier):
                        # Extract just the number
                        nhs_number = str(identifier).split('^')[0]
                        return nhs_number.replace(' ', '')
            else:
                # Single identifier
                nhs_number = str(identifiers).split('^')[0]
                return nhs_number.replace(' ', '')

        raise ValueError("NHS Number not found in message")

    def _validate_nhs_number(self, nhs_number: str) -> bool:
        """
        Validate NHS Number using Modulus 11 check digit algorithm.

        NHS Number format: 10 digits, last digit is check digit
        Algorithm: https://www.datadictionary.nhs.uk/attributes/nhs_number.html
        """
        # Remove spaces and validate format
        nhs_number = nhs_number.replace(' ', '')

        if not nhs_number.isdigit() or len(nhs_number) != 10:
            return False

        # Modulus 11 algorithm
        multipliers = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        check_digit = int(nhs_number[9])

        total = sum(int(nhs_number[i]) * multipliers[i] for i in range(9))
        remainder = total % 11
        expected_check_digit = 11 - remainder

        # Special cases
        if expected_check_digit == 11:
            expected_check_digit = 0
        elif expected_check_digit == 10:
            # NHS Numbers with check digit 10 are invalid
            return False

        return check_digit == expected_check_digit

    async def _enrich_from_pds(self, message: Any, nhs_number: str) -> Any:
        """
        Enrich message with data from PDS (Patient Demographic Service).

        This is a simulation - in production, this would call actual PDS API.
        """
        # Simulate PDS lookup delay
        await asyncio.sleep(0.1)

        # Simulated PDS response
        pds_data = {
            "nhs_number": nhs_number,
            "verified": True,
            "family_name": "VERIFIED_BY_PDS",
            "given_name": "VERIFIED",
            "date_of_birth": "19800101",
            "gender": "M",
            "address": {
                "line1": "VERIFIED ADDRESS",
                "postcode": "SW1A 1AA"
            }
        }

        # In a real implementation, you would update the HL7 message
        # with the verified PDS data here

        self._log.debug("pds_lookup_completed", nhs_number=nhs_number, verified=pds_data["verified"])

        return message

    def _generate_admission_key(self, message: Any) -> str:
        """Generate unique key for duplicate detection."""
        try:
            nhs_number = self._extract_nhs_number(message)
            message_type = str(message.MSH.MessageType) if hasattr(message, 'MSH') else "unknown"
            # Simplified - in production would include visit number, timestamp window, etc.
            return f"{nhs_number}_{message_type}"
        except Exception:
            # Fallback to message control ID
            if hasattr(message, 'MSH') and hasattr(message.MSH, 'MessageControlID'):
                return str(message.MSH.MessageControlID)
            return f"unknown_{datetime.now().isoformat()}"

    def _extract_postcode(self, message: Any) -> str | None:
        """Extract postcode from PID segment."""
        try:
            if hasattr(message, 'PID') and hasattr(message.PID, 'PatientAddress'):
                address = message.PID.PatientAddress
                if hasattr(address, 'ZipOrPostalCode'):
                    return str(address.ZipOrPostalCode).strip()
        except Exception as e:
            self._log.debug("failed_to_extract_postcode", error=str(e))
        return None

    def _validate_uk_postcode(self, postcode: str) -> bool:
        """
        Validate UK postcode format.

        Format: Area(1-2) District(1-2) Sector(1) Unit(2)
        Examples: SW1A 1AA, M1 1AE, B33 8TH
        """
        # UK postcode regex
        # Source: https://ideal-postcodes.co.uk/guides/uk-postcode-format
        uk_postcode_pattern = re.compile(
            r'^([A-Z]{1,2}\d{1,2}[A-Z]?)\s*(\d[A-Z]{2})$',
            re.IGNORECASE
        )

        postcode = postcode.upper().strip()
        return bool(uk_postcode_pattern.match(postcode))

    async def _generate_nack(self, message: Any, error_message: str) -> Any:
        """Generate NACK (negative acknowledgment) for validation failure."""
        self._log.warning("generating_nack", error=error_message)

        # In a real implementation, you would construct proper HL7 ACK message
        # For now, return None to indicate validation failure

        return None
