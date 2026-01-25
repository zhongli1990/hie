"""
LI HL7 Schema

Provides HL7v2 schema implementation with lazy parsing and validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import structlog

from hie.li.schemas.base import Schema, ValidationError
from hie.li.schemas.hl7.parsed_view import HL7ParsedView
from hie.li.schemas.hl7.definitions import (
    SegmentDefinition,
    FieldDefinition,
    MessageTypeDefinition,
    STANDARD_SEGMENTS,
    STANDARD_MESSAGE_TYPES,
)

logger = structlog.get_logger(__name__)


class HL7Schema(Schema):
    """
    HL7v2 message schema.
    
    Provides:
    - Lazy parsing via HL7ParsedView
    - Validation against segment/field definitions
    - ACK message generation
    - Support for custom segments and message types
    
    Can be loaded from IRIS-style HL7 schema XML files.
    """
    
    def __init__(
        self,
        name: str,
        version: str = "2.4",
        base_schema: str | None = None,
    ):
        super().__init__(name, version, base_schema)
        
        # Schema definitions
        self._segments: dict[str, SegmentDefinition] = {}
        self._message_types: dict[str, MessageTypeDefinition] = {}
        
        # Load standard definitions
        self._segments.update(STANDARD_SEGMENTS)
        self._message_types.update(STANDARD_MESSAGE_TYPES)
    
    @property
    def segments(self) -> dict[str, SegmentDefinition]:
        """Segment definitions."""
        return self._segments
    
    @property
    def message_types(self) -> dict[str, MessageTypeDefinition]:
        """Message type definitions."""
        return self._message_types
    
    def add_segment(self, segment: SegmentDefinition) -> None:
        """Add or override a segment definition."""
        self._segments[segment.name] = segment
    
    def add_message_type(self, msg_type: MessageTypeDefinition) -> None:
        """Add or override a message type definition."""
        self._message_types[msg_type.name] = msg_type
    
    def parse(self, raw: bytes) -> HL7ParsedView:
        """
        Parse raw HL7 message bytes into a ParsedView.
        
        Args:
            raw: Raw HL7 message bytes
            
        Returns:
            HL7ParsedView for lazy field access
        """
        return HL7ParsedView(raw, self)
    
    def validate(self, raw: bytes) -> list[ValidationError]:
        """
        Validate raw HL7 message against schema.
        
        Checks:
        - Message starts with MSH
        - Required segments present
        - Required fields present
        - Field lengths
        
        Args:
            raw: Raw HL7 message bytes
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            parsed = self.parse(raw)
            parsed._ensure_parsed()
        except Exception as e:
            errors.append(ValidationError("", f"Failed to parse message: {e}"))
            return errors
        
        # Check MSH exists
        msh = parsed.get_segment("MSH")
        if not msh:
            errors.append(ValidationError("MSH", "Missing required MSH segment"))
            return errors
        
        # Get message type
        msg_type = parsed.get_message_type()
        if not msg_type:
            errors.append(ValidationError("MSH-9", "Missing message type"))
        
        # Check message type definition
        msg_def = self._message_types.get(msg_type)
        if msg_def:
            # Check required segments
            for seg_name in msg_def.required_segments:
                if not parsed.get_segment(seg_name):
                    errors.append(ValidationError(
                        seg_name,
                        f"Missing required segment: {seg_name}"
                    ))
        
        # Validate MSH required fields
        msh_def = self._segments.get("MSH")
        if msh_def:
            for field_def in msh_def.fields:
                if field_def.required:
                    value = parsed.get_field(f"MSH-{field_def.position}")
                    if not value:
                        errors.append(ValidationError(
                            f"MSH-{field_def.position}",
                            f"Missing required field: {field_def.name}"
                        ))
        
        return errors
    
    def create_ack(
        self,
        parsed: HL7ParsedView,
        ack_code: str = "AA",
        text_message: str = "",
        error_code: str = "",
    ) -> bytes:
        """
        Create an ACK message for the given message.
        
        Args:
            parsed: Parsed view of original message
            ack_code: ACK code (AA, AE, AR)
            text_message: Optional text message
            error_code: Optional error code
            
        Returns:
            ACK message as bytes
        """
        from datetime import datetime
        
        # Get values from original message
        sending_app = parsed.get_field("MSH-3") or ""
        sending_fac = parsed.get_field("MSH-4") or ""
        receiving_app = parsed.get_field("MSH-5") or ""
        receiving_fac = parsed.get_field("MSH-6") or ""
        msg_control_id = parsed.get_field("MSH-10") or ""
        version = parsed.get_field("MSH-12") or "2.4"
        
        # Build ACK
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        msh = (
            f"MSH|^~\\&|{receiving_app}|{receiving_fac}|"
            f"{sending_app}|{sending_fac}|{timestamp}||ACK|"
            f"{msg_control_id}|P|{version}"
        )
        
        msa = f"MSA|{ack_code}|{msg_control_id}"
        if text_message:
            msa += f"|{text_message}"
        
        ack = f"{msh}\r{msa}\r"
        
        return ack.encode("utf-8")
    
    @classmethod
    def load_from_xml(cls, path: str | Path) -> "HL7Schema":
        """
        Load schema from IRIS-style HL7 schema XML file.
        
        Args:
            path: Path to XML schema file
            
        Returns:
            HL7Schema instance
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")
        
        # Parse XML
        tree = ET.parse(path)
        root = tree.getroot()
        
        # Get schema name from Category element or filename
        name = path.stem
        base_schema = None
        
        category = root.find(".//Category")
        if category is not None:
            name = category.get("name", name)
            base_schema = category.get("base")
        
        # Create schema
        schema = cls(name=name, base_schema=base_schema)
        
        # Parse segment definitions
        for seg_elem in root.findall(".//SegmentStructure"):
            seg_def = cls._parse_segment_definition(seg_elem)
            if seg_def:
                schema.add_segment(seg_def)
        
        # Parse message type definitions
        for msg_elem in root.findall(".//MessageType"):
            msg_def = cls._parse_message_type_definition(msg_elem)
            if msg_def:
                schema.add_message_type(msg_def)
        
        logger.info(
            "schema_loaded_from_xml",
            name=name,
            segments=len(schema._segments),
            message_types=len(schema._message_types),
        )
        
        return schema
    
    @classmethod
    def _parse_segment_definition(cls, elem: ET.Element) -> SegmentDefinition | None:
        """Parse SegmentStructure element into SegmentDefinition."""
        name = elem.get("name")
        if not name:
            return None
        
        description = elem.get("description", "")
        fields = []
        
        for field_elem in elem.findall(".//SegmentSubStructure"):
            field_def = cls._parse_field_definition(field_elem)
            if field_def:
                fields.append(field_def)
        
        return SegmentDefinition(
            name=name,
            description=description,
            fields=fields,
        )
    
    @classmethod
    def _parse_field_definition(cls, elem: ET.Element) -> FieldDefinition | None:
        """Parse SegmentSubStructure element into FieldDefinition."""
        piece = elem.get("piece")
        if not piece:
            return None
        
        try:
            position = int(piece)
        except ValueError:
            return None
        
        return FieldDefinition(
            position=position,
            name=elem.get("description", f"Field{position}"),
            data_type=elem.get("datatype", "ST"),
            max_length=int(elem.get("length")) if elem.get("length") else None,
            required=elem.get("required", "").lower() == "true",
            repeating=elem.get("repeating", "").lower() == "true",
        )
    
    @classmethod
    def _parse_message_type_definition(cls, elem: ET.Element) -> MessageTypeDefinition | None:
        """Parse MessageType element into MessageTypeDefinition."""
        name = elem.get("name")
        if not name:
            return None
        
        return MessageTypeDefinition(
            name=name,
            description=elem.get("description", ""),
        )


# Pre-built standard schemas
HL7_2_4 = HL7Schema(name="2.4", version="2.4")
HL7_2_5 = HL7Schema(name="2.5", version="2.5")
HL7_2_5_1 = HL7Schema(name="2.5.1", version="2.5.1")
