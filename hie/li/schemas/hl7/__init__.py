"""
LI HL7 Schema Module

Provides HL7v2 schema support with lazy parsing.
"""

from hie.li.schemas.hl7.schema import HL7Schema
from hie.li.schemas.hl7.parsed_view import HL7ParsedView
from hie.li.schemas.hl7.definitions import (
    SegmentDefinition,
    FieldDefinition,
    MessageTypeDefinition,
)

__all__ = [
    "HL7Schema",
    "HL7ParsedView",
    "SegmentDefinition",
    "FieldDefinition",
    "MessageTypeDefinition",
]
