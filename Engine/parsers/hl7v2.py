"""
HL7v2 Parser

Parses HL7v2 messages to the canonical format.
"""

from __future__ import annotations

import re
from datetime import datetime, date
from typing import Any

from Engine.core.canonical import (
    CanonicalMessage,
    MessageHeader,
    MessageCategory,
    EventType,
    PatientSegment,
    EncounterSegment,
    ProviderSegment,
    LocationSegment,
    ObservationSegment,
    HumanName,
    Address,
    Telecom,
    Identifier,
    CodedValue,
    Period,
    Reference,
    Quantity,
    MessageParser,
    format_registry,
)


class HL7v2Parser(MessageParser):
    """Parser for HL7v2 messages."""
    
    # Message type to category mapping
    CATEGORY_MAP = {
        "ADT": MessageCategory.ADT,
        "ORM": MessageCategory.ORDER,
        "ORU": MessageCategory.RESULT,
        "MDM": MessageCategory.DOCUMENT,
        "DFT": MessageCategory.FINANCIAL,
        "MFN": MessageCategory.MASTER,
        "QRY": MessageCategory.QUERY,
        "RSP": MessageCategory.RESPONSE,
    }
    
    # Event type mapping
    EVENT_MAP = {
        "A01": EventType.ADMIT,
        "A02": EventType.TRANSFER,
        "A03": EventType.DISCHARGE,
        "A04": EventType.REGISTER,
        "A05": EventType.PRE_ADMIT,
        "A08": EventType.UPDATE_PATIENT,
        "A11": EventType.CANCEL_ADMIT,
        "A13": EventType.CANCEL_DISCHARGE,
        "A40": EventType.MERGE_PATIENT,
        "O01": EventType.NEW_ORDER,
        "O02": EventType.UPDATE_ORDER,
        "R01": EventType.NEW_RESULT,
    }
    
    def can_parse(self, content: bytes, content_type: str) -> bool:
        """Check if content is HL7v2."""
        if content_type in ("application/hl7-v2", "x-application/hl7-v2", "text/hl7v2"):
            return True
        # Check for MSH header
        try:
            text = content.decode("utf-8", errors="ignore")
            return text.strip().startswith("MSH|")
        except:
            return False
    
    def parse(self, content: bytes, content_type: str) -> CanonicalMessage:
        """Parse HL7v2 message to canonical format."""
        text = content.decode("utf-8", errors="replace")
        
        # Normalize line endings
        text = text.replace("\r\n", "\r").replace("\n", "\r")
        segments = [s for s in text.split("\r") if s.strip()]
        
        if not segments or not segments[0].startswith("MSH"):
            raise ValueError("Invalid HL7v2 message: missing MSH segment")
        
        # Parse MSH to get delimiters
        msh = segments[0]
        field_sep = msh[3]  # Usually |
        comp_sep = msh[4]   # Usually ^
        rep_sep = msh[5]    # Usually ~
        esc_char = msh[6]   # Usually \
        sub_sep = msh[7]    # Usually &
        
        # Parse all segments
        parsed_segments: dict[str, list[list[list[str]]]] = {}
        for seg in segments:
            seg_type = seg[:3]
            fields = seg.split(field_sep)
            
            # Parse each field into components
            parsed_fields = []
            for f in fields:
                if rep_sep in f:
                    # Handle repeating fields
                    reps = f.split(rep_sep)
                    parsed_fields.append([r.split(comp_sep) for r in reps])
                else:
                    parsed_fields.append([f.split(comp_sep)])
            
            if seg_type not in parsed_segments:
                parsed_segments[seg_type] = []
            parsed_segments[seg_type].append(parsed_fields)
        
        # Build canonical message
        header = self._parse_header(parsed_segments.get("MSH", [[]])[0], field_sep)
        patient = self._parse_patient(parsed_segments)
        encounter = self._parse_encounter(parsed_segments)
        providers = self._parse_providers(parsed_segments)
        locations = self._parse_locations(parsed_segments)
        observations = self._parse_observations(parsed_segments)
        
        return CanonicalMessage(
            header=header,
            patient=patient,
            encounter=encounter,
            providers=providers,
            locations=locations,
            observations=observations,
            raw_content=content,
            raw_content_type="application/hl7-v2",
        )
    
    def _get_field(self, fields: list, index: int, comp: int = 0, rep: int = 0) -> str:
        """Safely get a field value."""
        try:
            if index >= len(fields):
                return ""
            field = fields[index]
            if rep >= len(field):
                return ""
            components = field[rep]
            if comp >= len(components):
                return ""
            return components[comp] or ""
        except (IndexError, TypeError):
            return ""
    
    def _parse_header(self, msh: list, field_sep: str) -> MessageHeader:
        """Parse MSH segment to header."""
        # MSH-7: Message datetime
        timestamp_str = self._get_field(msh, 7)
        timestamp = self._parse_datetime(timestamp_str) or datetime.utcnow()
        
        # MSH-9: Message type (e.g., ADT^A01)
        msg_type = self._get_field(msh, 9, 0)
        event_code = self._get_field(msh, 9, 1)
        
        category = self.CATEGORY_MAP.get(msg_type, MessageCategory.OTHER)
        event_type = self.EVENT_MAP.get(event_code)
        
        return MessageHeader(
            timestamp=timestamp,
            category=category,
            event_type=event_type,
            source_format="hl7v2",
            source_version=self._get_field(msh, 12),
            source_message_type=f"{msg_type}^{event_code}" if event_code else msg_type,
            sending_application=self._get_field(msh, 3),
            sending_facility=self._get_field(msh, 4),
            receiving_application=self._get_field(msh, 5),
            receiving_facility=self._get_field(msh, 6),
            sequence_number=self._get_field(msh, 10),
            accept_ack_type=self._get_field(msh, 15),
            application_ack_type=self._get_field(msh, 16),
        )
    
    def _parse_patient(self, segments: dict) -> PatientSegment | None:
        """Parse PID segment to patient."""
        pid_list = segments.get("PID", [])
        if not pid_list:
            return None
        
        pid = pid_list[0]
        
        # PID-3: Patient identifiers (repeating)
        identifiers = []
        pid3 = pid[3] if len(pid) > 3 else []
        for rep in pid3:
            if rep and rep[0]:
                ident = Identifier(
                    value=rep[0],
                    type=rep[4] if len(rep) > 4 else None,
                    assigner=rep[3] if len(rep) > 3 else None,
                )
                identifiers.append(ident)
        
        # PID-5: Patient name
        name = self._parse_xpn(pid[5] if len(pid) > 5 else [])
        
        # PID-7: Date of birth
        dob_str = self._get_field(pid, 7)
        birth_date = self._parse_date(dob_str)
        
        # PID-8: Gender
        gender_code = self._get_field(pid, 8)
        gender = CodedValue(code=gender_code) if gender_code else None
        
        # PID-11: Address (repeating)
        addresses = []
        pid11 = pid[11] if len(pid) > 11 else []
        for rep in pid11:
            addr = self._parse_xad(rep)
            if addr:
                addresses.append(addr)
        
        # PID-13/14: Phone numbers
        telecoms = []
        for idx, use in [(13, "home"), (14, "work")]:
            if len(pid) > idx:
                for rep in pid[idx]:
                    if rep and rep[0]:
                        telecoms.append(Telecom(value=rep[0], use=use, system="phone"))
        
        # PID-30: Deceased indicator
        deceased = self._get_field(pid, 30).upper() == "Y"
        
        # Look for NHS number in identifiers
        nhs_number = None
        for ident in identifiers:
            if ident.type == "NHS" or ident.assigner == "NHS":
                nhs_number = ident.value
                break
        
        return PatientSegment(
            identifiers=identifiers,
            name=name,
            birth_date=birth_date,
            gender=gender,
            address=addresses,
            telecom=telecoms,
            deceased=deceased,
            nhs_number=nhs_number,
        )
    
    def _parse_encounter(self, segments: dict) -> EncounterSegment | None:
        """Parse PV1 segment to encounter."""
        pv1_list = segments.get("PV1", [])
        if not pv1_list:
            return None
        
        pv1 = pv1_list[0]
        
        # PV1-2: Patient class
        class_code = self._get_field(pv1, 2)
        
        # PV1-19: Visit number
        identifiers = []
        visit_num = self._get_field(pv1, 19)
        if visit_num:
            identifiers.append(Identifier(value=visit_num, type="VN"))
        
        # PV1-44/45: Admit/Discharge datetime
        admit_dt = self._parse_datetime(self._get_field(pv1, 44))
        discharge_dt = self._parse_datetime(self._get_field(pv1, 45))
        period = None
        if admit_dt or discharge_dt:
            period = Period(start=admit_dt, end=discharge_dt)
        
        # PV1-14: Admit source
        admit_source_code = self._get_field(pv1, 14)
        admit_source = CodedValue(code=admit_source_code) if admit_source_code else None
        
        # PV1-36: Discharge disposition
        discharge_code = self._get_field(pv1, 36)
        discharge_disp = CodedValue(code=discharge_code) if discharge_code else None
        
        return EncounterSegment(
            identifiers=identifiers,
            class_code=CodedValue(code=class_code) if class_code else None,
            period=period,
            admit_source=admit_source,
            discharge_disposition=discharge_disp,
        )
    
    def _parse_providers(self, segments: dict) -> list[ProviderSegment]:
        """Parse provider information from various segments."""
        providers = []
        
        # PV1-7: Attending doctor
        pv1_list = segments.get("PV1", [])
        if pv1_list:
            pv1 = pv1_list[0]
            if len(pv1) > 7:
                for rep in pv1[7]:
                    prov = self._parse_xcn(rep, "attending")
                    if prov:
                        providers.append(prov)
        
        return providers
    
    def _parse_locations(self, segments: dict) -> list[LocationSegment]:
        """Parse location information."""
        locations = []
        
        # PV1-3: Assigned patient location
        pv1_list = segments.get("PV1", [])
        if pv1_list:
            pv1 = pv1_list[0]
            if len(pv1) > 3 and pv1[3]:
                loc_data = pv1[3][0] if pv1[3] else []
                if loc_data:
                    loc = LocationSegment(
                        facility=loc_data[3] if len(loc_data) > 3 else None,
                        building=loc_data[6] if len(loc_data) > 6 else None,
                        floor=loc_data[7] if len(loc_data) > 7 else None,
                        room=loc_data[1] if len(loc_data) > 1 else None,
                        bed=loc_data[2] if len(loc_data) > 2 else None,
                    )
                    locations.append(loc)
        
        return locations
    
    def _parse_observations(self, segments: dict) -> list[ObservationSegment]:
        """Parse OBX segments to observations."""
        observations = []
        
        for obx in segments.get("OBX", []):
            # OBX-3: Observation identifier
            code = None
            if len(obx) > 3 and obx[3]:
                code_data = obx[3][0]
                code = CodedValue(
                    code=code_data[0] if code_data else "",
                    display=code_data[1] if len(code_data) > 1 else None,
                    system=code_data[2] if len(code_data) > 2 else None,
                )
            
            # OBX-2: Value type
            value_type = self._get_field(obx, 2)
            
            # OBX-5: Observation value
            value_str = self._get_field(obx, 5)
            value_quantity = None
            value_code = None
            
            if value_type in ("NM", "SN"):
                try:
                    from decimal import Decimal
                    unit = self._get_field(obx, 6)
                    value_quantity = Quantity(value=Decimal(value_str), unit=unit)
                except:
                    pass
            elif value_type == "CE":
                if len(obx) > 5 and obx[5]:
                    ce = obx[5][0]
                    value_code = CodedValue(
                        code=ce[0] if ce else "",
                        display=ce[1] if len(ce) > 1 else None,
                    )
            
            # OBX-11: Observation result status
            status_code = self._get_field(obx, 11)
            status = CodedValue(code=status_code) if status_code else None
            
            # OBX-14: Date/time of observation
            obs_dt = self._parse_datetime(self._get_field(obx, 14))
            
            obs = ObservationSegment(
                code=code,
                status=status,
                effective=obs_dt,
                value_quantity=value_quantity,
                value_string=value_str if not value_quantity and not value_code else None,
                value_code=value_code,
            )
            observations.append(obs)
        
        return observations
    
    def _parse_xpn(self, xpn_field: list) -> HumanName | None:
        """Parse XPN (Extended Person Name) field."""
        if not xpn_field:
            return None
        
        xpn = xpn_field[0] if xpn_field else []
        if not xpn:
            return None
        
        family = xpn[0] if xpn else None
        given = [xpn[1]] if len(xpn) > 1 and xpn[1] else []
        if len(xpn) > 2 and xpn[2]:  # Middle name
            given.append(xpn[2])
        
        prefix = [xpn[5]] if len(xpn) > 5 and xpn[5] else []
        suffix = [xpn[4]] if len(xpn) > 4 and xpn[4] else []
        
        return HumanName(
            family=family,
            given=given,
            prefix=prefix,
            suffix=suffix,
        )
    
    def _parse_xad(self, xad: list) -> Address | None:
        """Parse XAD (Extended Address) field."""
        if not xad or not any(xad):
            return None
        
        lines = []
        if xad[0]:
            lines.append(xad[0])
        if len(xad) > 1 and xad[1]:
            lines.append(xad[1])
        
        return Address(
            lines=lines,
            city=xad[2] if len(xad) > 2 else None,
            state=xad[3] if len(xad) > 3 else None,
            postal_code=xad[4] if len(xad) > 4 else None,
            country=xad[5] if len(xad) > 5 else None,
            type=xad[6] if len(xad) > 6 else None,
        )
    
    def _parse_xcn(self, xcn: list, role: str) -> ProviderSegment | None:
        """Parse XCN (Extended Composite ID Number and Name) field."""
        if not xcn or not any(xcn):
            return None
        
        identifiers = []
        if xcn[0]:
            identifiers.append(Identifier(value=xcn[0]))
        
        name = None
        if len(xcn) > 1:
            family = xcn[1] if len(xcn) > 1 else None
            given = [xcn[2]] if len(xcn) > 2 and xcn[2] else []
            name = HumanName(family=family, given=given)
        
        return ProviderSegment(
            identifiers=identifiers,
            name=name,
            role=CodedValue(code=role),
        )
    
    def _parse_datetime(self, dt_str: str) -> datetime | None:
        """Parse HL7v2 datetime string."""
        if not dt_str:
            return None
        
        # Remove timezone if present
        dt_str = dt_str.split("+")[0].split("-")[0]
        
        formats = [
            "%Y%m%d%H%M%S.%f",
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
            "%Y%m%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str[:len(fmt.replace("%", ""))], fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_date(self, dt_str: str) -> date | None:
        """Parse HL7v2 date string."""
        if not dt_str or len(dt_str) < 8:
            return None
        
        try:
            return datetime.strptime(dt_str[:8], "%Y%m%d").date()
        except ValueError:
            return None


# Register parser
format_registry.register_parser("hl7v2", HL7v2Parser())
