"""
LI HL7 Schema Definitions

Defines the structure classes for HL7v2 schemas:
- FieldDefinition: Definition of a field within a segment
- SegmentDefinition: Definition of a segment (e.g., MSH, PID)
- MessageTypeDefinition: Definition of a message type (e.g., ADT_A01)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDefinition:
    """
    Definition of a field within an HL7 segment.
    
    Matches IRIS HL7 schema SegmentSubStructure.
    """
    position: int  # 1-indexed field position
    name: str
    data_type: str = "ST"  # Default to string
    max_length: int | None = None
    required: bool = False
    repeating: bool = False
    
    # Component definitions (for composite fields)
    components: list[FieldDefinition] = field(default_factory=list)
    
    def __post_init__(self):
        if self.components is None:
            self.components = []


@dataclass
class SegmentDefinition:
    """
    Definition of an HL7 segment.
    
    Matches IRIS HL7 schema SegmentStructure.
    """
    name: str  # e.g., "MSH", "PID", "OBX"
    description: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)
    
    def get_field(self, position: int) -> FieldDefinition | None:
        """Get field definition by position (1-indexed)."""
        for f in self.fields:
            if f.position == position:
                return f
        return None
    
    def __post_init__(self):
        if self.fields is None:
            self.fields = []


@dataclass
class MessageTypeDefinition:
    """
    Definition of an HL7 message type.
    
    Matches IRIS HL7 schema MessageType.
    """
    name: str  # e.g., "ADT_A01", "ORM_O01"
    description: str = ""
    
    # Segment order and requirements
    segments: list[str] = field(default_factory=list)  # Ordered list of segment names
    required_segments: set[str] = field(default_factory=set)
    repeating_segments: set[str] = field(default_factory=set)
    
    def __post_init__(self):
        if self.segments is None:
            self.segments = []
        if self.required_segments is None:
            self.required_segments = set()
        if self.repeating_segments is None:
            self.repeating_segments = set()


# Standard HL7 v2.4 segment definitions
STANDARD_SEGMENTS: dict[str, SegmentDefinition] = {
    "MSH": SegmentDefinition(
        name="MSH",
        description="Message Header",
        fields=[
            FieldDefinition(1, "FieldSeparator", "ST", 1, True),
            FieldDefinition(2, "EncodingCharacters", "ST", 4, True),
            FieldDefinition(3, "SendingApplication", "HD"),
            FieldDefinition(4, "SendingFacility", "HD"),
            FieldDefinition(5, "ReceivingApplication", "HD"),
            FieldDefinition(6, "ReceivingFacility", "HD"),
            FieldDefinition(7, "DateTimeOfMessage", "TS", required=True),
            FieldDefinition(8, "Security", "ST"),
            FieldDefinition(9, "MessageType", "MSG", required=True),
            FieldDefinition(10, "MessageControlID", "ST", required=True),
            FieldDefinition(11, "ProcessingID", "PT", required=True),
            FieldDefinition(12, "VersionID", "VID", required=True),
        ]
    ),
    "PID": SegmentDefinition(
        name="PID",
        description="Patient Identification",
        fields=[
            FieldDefinition(1, "SetID", "SI"),
            FieldDefinition(2, "PatientID", "CX"),
            FieldDefinition(3, "PatientIdentifierList", "CX", repeating=True),
            FieldDefinition(4, "AlternatePatientID", "CX"),
            FieldDefinition(5, "PatientName", "XPN", repeating=True),
            FieldDefinition(6, "MothersMaidenName", "XPN"),
            FieldDefinition(7, "DateTimeOfBirth", "TS"),
            FieldDefinition(8, "AdministrativeSex", "IS"),
            FieldDefinition(9, "PatientAlias", "XPN", repeating=True),
            FieldDefinition(10, "Race", "CE", repeating=True),
            FieldDefinition(11, "PatientAddress", "XAD", repeating=True),
            FieldDefinition(12, "CountyCode", "IS"),
            FieldDefinition(13, "PhoneNumberHome", "XTN", repeating=True),
            FieldDefinition(14, "PhoneNumberBusiness", "XTN", repeating=True),
            FieldDefinition(15, "PrimaryLanguage", "CE"),
            FieldDefinition(16, "MaritalStatus", "CE"),
            FieldDefinition(17, "Religion", "CE"),
            FieldDefinition(18, "PatientAccountNumber", "CX"),
            FieldDefinition(19, "SSNNumber", "ST"),
        ]
    ),
    "PV1": SegmentDefinition(
        name="PV1",
        description="Patient Visit",
        fields=[
            FieldDefinition(1, "SetID", "SI"),
            FieldDefinition(2, "PatientClass", "IS", required=True),
            FieldDefinition(3, "AssignedPatientLocation", "PL"),
            FieldDefinition(4, "AdmissionType", "IS"),
            FieldDefinition(5, "PreadmitNumber", "CX"),
            FieldDefinition(6, "PriorPatientLocation", "PL"),
            FieldDefinition(7, "AttendingDoctor", "XCN", repeating=True),
            FieldDefinition(8, "ReferringDoctor", "XCN", repeating=True),
            FieldDefinition(9, "ConsultingDoctor", "XCN", repeating=True),
            FieldDefinition(10, "HospitalService", "IS"),
            FieldDefinition(19, "VisitNumber", "CX"),
            FieldDefinition(44, "AdmitDateTime", "TS"),
            FieldDefinition(45, "DischargeDateTime", "TS"),
        ]
    ),
    "OBR": SegmentDefinition(
        name="OBR",
        description="Observation Request",
        fields=[
            FieldDefinition(1, "SetID", "SI"),
            FieldDefinition(2, "PlacerOrderNumber", "EI"),
            FieldDefinition(3, "FillerOrderNumber", "EI"),
            FieldDefinition(4, "UniversalServiceIdentifier", "CE", required=True),
        ]
    ),
    "OBX": SegmentDefinition(
        name="OBX",
        description="Observation/Result",
        fields=[
            FieldDefinition(1, "SetID", "SI"),
            FieldDefinition(2, "ValueType", "ID"),
            FieldDefinition(3, "ObservationIdentifier", "CE", required=True),
            FieldDefinition(4, "ObservationSubID", "ST"),
            FieldDefinition(5, "ObservationValue", "varies", repeating=True),
            FieldDefinition(6, "Units", "CE"),
            FieldDefinition(7, "ReferencesRange", "ST"),
            FieldDefinition(8, "AbnormalFlags", "IS", repeating=True),
            FieldDefinition(11, "ObservationResultStatus", "ID", required=True),
        ]
    ),
    "MSA": SegmentDefinition(
        name="MSA",
        description="Message Acknowledgment",
        fields=[
            FieldDefinition(1, "AcknowledgmentCode", "ID", required=True),
            FieldDefinition(2, "MessageControlID", "ST", required=True),
            FieldDefinition(3, "TextMessage", "ST"),
        ]
    ),
    "EVN": SegmentDefinition(
        name="EVN",
        description="Event Type",
        fields=[
            FieldDefinition(1, "EventTypeCode", "ID"),
            FieldDefinition(2, "RecordedDateTime", "TS"),
            FieldDefinition(3, "DateTimePlannedEvent", "TS"),
            FieldDefinition(4, "EventReasonCode", "IS"),
            FieldDefinition(5, "OperatorID", "XCN", repeating=True),
            FieldDefinition(6, "EventOccurred", "TS"),
        ]
    ),
}


# Standard HL7 v2.4 message type definitions
STANDARD_MESSAGE_TYPES: dict[str, MessageTypeDefinition] = {
    "ADT_A01": MessageTypeDefinition(
        name="ADT_A01",
        description="Admit/Visit Notification",
        segments=["MSH", "EVN", "PID", "PV1"],
        required_segments={"MSH", "EVN", "PID", "PV1"},
    ),
    "ADT_A02": MessageTypeDefinition(
        name="ADT_A02",
        description="Transfer a Patient",
        segments=["MSH", "EVN", "PID", "PV1"],
        required_segments={"MSH", "EVN", "PID", "PV1"},
    ),
    "ADT_A03": MessageTypeDefinition(
        name="ADT_A03",
        description="Discharge/End Visit",
        segments=["MSH", "EVN", "PID", "PV1"],
        required_segments={"MSH", "EVN", "PID", "PV1"},
    ),
    "ADT_A04": MessageTypeDefinition(
        name="ADT_A04",
        description="Register a Patient",
        segments=["MSH", "EVN", "PID", "PV1"],
        required_segments={"MSH", "EVN", "PID", "PV1"},
    ),
    "ADT_A08": MessageTypeDefinition(
        name="ADT_A08",
        description="Update Patient Information",
        segments=["MSH", "EVN", "PID", "PV1"],
        required_segments={"MSH", "EVN", "PID", "PV1"},
    ),
    "ORU_R01": MessageTypeDefinition(
        name="ORU_R01",
        description="Unsolicited Observation Result",
        segments=["MSH", "PID", "PV1", "OBR", "OBX"],
        required_segments={"MSH"},
        repeating_segments={"OBR", "OBX"},
    ),
    "ORM_O01": MessageTypeDefinition(
        name="ORM_O01",
        description="Order Message",
        segments=["MSH", "PID", "PV1", "OBR"],
        required_segments={"MSH"},
    ),
    "ACK": MessageTypeDefinition(
        name="ACK",
        description="General Acknowledgment",
        segments=["MSH", "MSA"],
        required_segments={"MSH", "MSA"},
    ),
}
