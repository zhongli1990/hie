"""
Tests for LI Schema System.

Tests the schema-driven lazy parsing for HL7v2 messages.
"""

import pytest

from Engine.li.schemas import Schema, ParsedView, ValidationError
from Engine.li.schemas.hl7 import HL7Schema, HL7ParsedView


# Sample HL7 messages for testing
SAMPLE_ADT_A01 = b"""MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20240115120000||ADT^A01|MSG00001|P|2.4
EVN|A01|20240115120000
PID|1||12345^^^MRN||DOE^JOHN^Q||19800101|M|||123 MAIN ST^^ANYTOWN^CA^12345||555-1234
PV1|1|I|ICU^101^A|||||||||||||||V123456
"""

SAMPLE_ORU_R01 = b"""MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115130000||ORU^R01|MSG00002|P|2.4
PID|1||67890^^^MRN||SMITH^JANE||19750515|F
OBR|1|ORD001|FIL001|CBC^Complete Blood Count
OBX|1|NM|WBC^White Blood Cell Count||7.5|10*3/uL|4.5-11.0|N|||F
OBX|2|NM|RBC^Red Blood Cell Count||4.8|10*6/uL|4.0-5.5|N|||F
"""

SAMPLE_ACK = b"""MSH|^~\\&|RECEIVING_APP|RECEIVING_FAC|SENDING_APP|SENDING_FAC|20240115120001||ACK|MSG00001|P|2.4
MSA|AA|MSG00001|Message Accepted
"""

SAMPLE_MINIMAL = b"MSH|^~\\&|APP|FAC|||20240101||ADT^A01|1|P|2.4\r"


class TestHL7Schema:
    """Tests for HL7Schema class."""
    
    def test_schema_initialization(self):
        """Test schema initialization."""
        schema = HL7Schema(name="TestSchema", version="2.4")
        
        assert schema.name == "TestSchema"
        assert schema.version == "2.4"
        assert schema.base_schema is None
        
        # Should have standard segments loaded
        assert "MSH" in schema.segments
        assert "PID" in schema.segments
        assert "PV1" in schema.segments
    
    def test_schema_with_base(self):
        """Test schema with base schema."""
        schema = HL7Schema(name="PKB", version="2.4", base_schema="2.4")
        
        assert schema.name == "PKB"
        assert schema.base_schema == "2.4"
    
    def test_parse_returns_parsed_view(self):
        """Test parse returns HL7ParsedView."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        assert isinstance(parsed, HL7ParsedView)
        assert parsed.schema == schema
        assert parsed.raw == SAMPLE_ADT_A01
    
    def test_validate_valid_message(self):
        """Test validation of valid message."""
        schema = HL7Schema(name="2.4")
        errors = schema.validate(SAMPLE_ADT_A01)
        
        # Should have no errors for required fields
        error_msgs = [e.message for e in errors if e.severity == "error"]
        assert len(error_msgs) == 0, f"Unexpected errors: {error_msgs}"
    
    def test_validate_missing_msh(self):
        """Test validation catches missing MSH."""
        schema = HL7Schema(name="2.4")
        errors = schema.validate(b"PID|1||12345")
        
        assert len(errors) > 0
        assert any("MSH" in e.message for e in errors)
    
    def test_is_valid(self):
        """Test is_valid convenience method."""
        schema = HL7Schema(name="2.4")
        
        assert schema.is_valid(SAMPLE_ADT_A01) is True
        assert schema.is_valid(b"INVALID") is False
    
    def test_create_ack(self):
        """Test ACK message generation."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        ack = schema.create_ack(parsed, "AA", "Message Accepted")
        ack_str = ack.decode("utf-8")
        
        assert "MSH|" in ack_str
        assert "MSA|AA|MSG00001" in ack_str
        assert "Message Accepted" in ack_str
    
    def test_create_ack_error(self):
        """Test ACK message generation for error."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        ack = schema.create_ack(parsed, "AE", "Validation Error")
        ack_str = ack.decode("utf-8")
        
        assert "MSA|AE|MSG00001" in ack_str
        assert "Validation Error" in ack_str


class TestHL7ParsedView:
    """Tests for HL7ParsedView class."""
    
    def test_get_field_simple(self):
        """Test simple field access."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # MSH fields
        assert parsed.get_field("MSH-1") == "|"
        assert parsed.get_field("MSH-2") == "^~\\&"
        assert parsed.get_field("MSH-3") == "SENDING_APP"
        assert parsed.get_field("MSH-4") == "SENDING_FAC"
        assert parsed.get_field("MSH-10") == "MSG00001"
    
    def test_get_field_component(self):
        """Test component access."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # MSH-9 is ADT^A01
        assert parsed.get_field("MSH-9.1") == "ADT"
        assert parsed.get_field("MSH-9.2") == "A01"
        
        # PID-5 is DOE^JOHN^Q
        assert parsed.get_field("PID-5.1") == "DOE"
        assert parsed.get_field("PID-5.2") == "JOHN"
        assert parsed.get_field("PID-5.3") == "Q"
    
    def test_get_field_with_default(self):
        """Test field access with default value."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        assert parsed.get_field("MSH-99", "default") == "default"
        assert parsed.get_field("XXX-1", None) is None
    
    def test_get_field_caching(self):
        """Test that field values are cached."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # First access
        value1 = parsed.get_field("MSH-10")
        # Second access should use cache
        value2 = parsed.get_field("MSH-10")
        
        assert value1 == value2
        assert "MSH-10" in parsed._cache
    
    def test_get_segment(self):
        """Test segment access."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        msh = parsed.get_segment("MSH")
        assert msh is not None
        assert msh.startswith("MSH|")
        
        pid = parsed.get_segment("PID")
        assert pid is not None
        assert "DOE^JOHN" in pid
    
    def test_get_segments_repeating(self):
        """Test access to repeating segments."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ORU_R01)
        
        obx_segments = parsed.get_segments("OBX")
        assert len(obx_segments) == 2
        assert "WBC" in obx_segments[0]
        assert "RBC" in obx_segments[1]
    
    def test_get_field_segment_repetition(self):
        """Test field access with segment repetition."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ORU_R01)
        
        # First OBX
        assert parsed.get_field("OBX(1)-3.1") == "WBC"
        assert parsed.get_field("OBX(1)-5") == "7.5"
        
        # Second OBX
        assert parsed.get_field("OBX(2)-3.1") == "RBC"
        assert parsed.get_field("OBX(2)-5") == "4.8"
    
    def test_get_message_type(self):
        """Test get_message_type convenience method."""
        schema = HL7Schema(name="2.4")
        
        parsed1 = schema.parse(SAMPLE_ADT_A01)
        assert parsed1.get_message_type() == "ADT_A01"
        
        parsed2 = schema.parse(SAMPLE_ORU_R01)
        assert parsed2.get_message_type() == "ORU_R01"
    
    def test_get_message_control_id(self):
        """Test get_message_control_id convenience method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        assert parsed.get_message_control_id() == "MSG00001"
    
    def test_get_patient_id(self):
        """Test get_patient_id convenience method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        assert parsed.get_patient_id() == "12345"
    
    def test_get_patient_name(self):
        """Test get_patient_name convenience method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # Returns full field value
        name = parsed.get_patient_name()
        assert "DOE" in name
        assert "JOHN" in name
    
    def test_set_field(self):
        """Test setting a field value."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # Set a new value
        new_raw = parsed.set_field("MSH-10", "NEWID001")
        
        # Original should be unchanged
        assert parsed.get_field("MSH-10") == "MSG00001"
        
        # New message should have updated value
        new_parsed = schema.parse(new_raw)
        assert new_parsed.get_field("MSH-10") == "NEWID001"
    
    def test_set_field_component(self):
        """Test setting a component value."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # Change patient last name
        new_raw = parsed.set_field("PID-5.1", "SMITH")
        
        new_parsed = schema.parse(new_raw)
        assert new_parsed.get_field("PID-5.1") == "SMITH"
        assert new_parsed.get_field("PID-5.2") == "JOHN"  # Unchanged
    
    def test_has_field(self):
        """Test has_field method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        assert parsed.has_field("MSH-10") is True
        assert parsed.has_field("MSH-99") is False
        assert parsed.has_field("XXX-1") is False
    
    def test_get_fields_multiple(self):
        """Test getting multiple fields at once."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        fields = parsed.get_fields(["MSH-9.1", "MSH-9.2", "MSH-10"])
        
        assert fields["MSH-9.1"] == "ADT"
        assert fields["MSH-9.2"] == "A01"
        assert fields["MSH-10"] == "MSG00001"
    
    def test_to_dict(self):
        """Test to_dict method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        d = parsed.to_dict()
        
        assert d["message_type"] == "ADT_A01"
        assert d["message_control_id"] == "MSG00001"
        assert "MSH" in d["segments"]
        assert "PID" in d["segments"]
    
    def test_lazy_parsing(self):
        """Test that parsing is lazy."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        # Before any field access, segments should not be parsed
        assert parsed._segments is None
        
        # Access a field
        _ = parsed.get_field("MSH-10")
        
        # Now segments should be parsed
        assert parsed._segments is not None
    
    def test_different_delimiters(self):
        """Test handling of non-standard delimiters."""
        # Message with different encoding characters
        msg = b"MSH|#~\\&|APP|FAC|||20240101||ADT#A01|1|P|2.4\r"
        
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(msg)
        
        # Should detect # as component separator
        assert parsed.get_field("MSH-9.1") == "ADT"
        assert parsed.get_field("MSH-9.2") == "A01"


class TestSchemaRegistry:
    """Tests for SchemaRegistry integration."""
    
    def test_registry_register_and_get(self):
        """Test registering and retrieving schemas."""
        from Engine.li.registry import SchemaRegistry
        
        # Clear registry
        SchemaRegistry.clear()
        
        # Register a schema
        schema = HL7Schema(name="TestSchema", version="2.4")
        SchemaRegistry.register(schema)
        
        # Retrieve it
        retrieved = SchemaRegistry.get("TestSchema")
        assert retrieved is schema
    
    def test_registry_list_schemas(self):
        """Test listing schemas."""
        from Engine.li.registry import SchemaRegistry
        
        SchemaRegistry.clear()
        
        SchemaRegistry.register(HL7Schema(name="Schema1"))
        SchemaRegistry.register(HL7Schema(name="Schema2"))
        
        schemas = SchemaRegistry.list_schemas()
        assert "Schema1" in schemas
        assert "Schema2" in schemas
    
    def test_registry_get_nonexistent(self):
        """Test getting non-existent schema."""
        from Engine.li.registry import SchemaRegistry
        
        SchemaRegistry.clear()
        
        result = SchemaRegistry.get("NonExistent")
        assert result is None


class TestValidationError:
    """Tests for ValidationError class."""
    
    def test_validation_error_str(self):
        """Test ValidationError string representation."""
        error = ValidationError(
            path="MSH-10",
            message="Missing required field",
            severity="error"
        )
        
        assert "[ERROR]" in str(error)
        assert "MSH-10" in str(error)
        assert "Missing required field" in str(error)
    
    def test_validation_error_warning(self):
        """Test ValidationError with warning severity."""
        error = ValidationError(
            path="PID-5",
            message="Field exceeds recommended length",
            severity="warning"
        )
        
        assert "[WARNING]" in str(error)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
