"""
Tests for LI HL7 Hosts.

Tests HL7TCPService, HL7TCPOperation, and HL7RoutingEngine.
"""

import asyncio
import pytest

from hie.li.hosts import (
    HL7TCPService,
    HL7TCPOperation,
    HL7Message,
    SendResult,
    HL7SendError,
    HL7RoutingEngine,
    RoutingRule,
    RoutingResult,
    RuleAction,
    ConditionEvaluator,
    create_message_type_rule,
    create_facility_rule,
)
from hie.li.schemas.hl7 import HL7Schema
from hie.li.config import ItemConfig, SettingTarget


# Sample HL7 messages for testing
SAMPLE_ADT_A01 = b"MSH|^~\\&|SENDING|FAC|RECEIVING|FAC|20240115120000||ADT^A01|MSG001|P|2.4\rEVN|A01|20240115\rPID|1||12345||DOE^JOHN\rPV1|1|I|ICU\r"
SAMPLE_ADT_A08 = b"MSH|^~\\&|SENDING|FAC|RECEIVING|FAC|20240115120000||ADT^A08|MSG002|P|2.4\rEVN|A08|20240115\rPID|1||12345||DOE^JOHN\rPV1|1|I|ICU\r"
SAMPLE_ORU_R01 = b"MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115||ORU^R01|MSG003|P|2.4\rPID|1||67890||SMITH^JANE\rOBR|1||FIL001|CBC\rOBX|1|NM|WBC||7.5|10*3/uL\r"
SAMPLE_ACK_AA = b"MSH|^~\\&|RECEIVING|FAC|SENDING|FAC|20240115||ACK|MSG001|P|2.4\rMSA|AA|MSG001|Message Accepted\r"
SAMPLE_ACK_AE = b"MSH|^~\\&|RECEIVING|FAC|SENDING|FAC|20240115||ACK|MSG001|P|2.4\rMSA|AE|MSG001|Application Error\r"
SAMPLE_ACK_AR = b"MSH|^~\\&|RECEIVING|FAC|SENDING|FAC|20240115||ACK|MSG001|P|2.4\rMSA|AR|MSG001|Message Rejected\r"


class TestHL7Message:
    """Tests for HL7Message class."""
    
    def test_message_creation(self):
        """Test HL7Message creation."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        
        message = HL7Message(
            raw=SAMPLE_ADT_A01,
            parsed=parsed,
            source="test-service",
        )
        
        assert message.raw == SAMPLE_ADT_A01
        assert message.parsed is not None
        assert message.source == "test-service"
        assert message.is_valid is True
    
    def test_message_type_property(self):
        """Test message_type property."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        message = HL7Message(raw=SAMPLE_ADT_A01, parsed=parsed)
        
        assert message.message_type == "ADT_A01"
    
    def test_message_control_id_property(self):
        """Test message_control_id property."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        message = HL7Message(raw=SAMPLE_ADT_A01, parsed=parsed)
        
        assert message.message_control_id == "MSG001"
    
    def test_message_with_error(self):
        """Test message with error."""
        message = HL7Message(
            raw=b"INVALID",
            error="Parse error",
        )
        
        assert message.is_valid is False
        assert message.error == "Parse error"
    
    def test_message_get_field(self):
        """Test get_field method."""
        schema = HL7Schema(name="2.4")
        parsed = schema.parse(SAMPLE_ADT_A01)
        message = HL7Message(raw=SAMPLE_ADT_A01, parsed=parsed)
        
        assert message.get_field("MSH-9.1") == "ADT"
        assert message.get_field("PID-5.1") == "DOE"
        assert message.get_field("XXX-1", "default") == "default"


class TestHL7TCPService:
    """Tests for HL7TCPService."""
    
    def test_service_initialization(self):
        """Test service initialization."""
        service = HL7TCPService(
            name="test-service",
            adapter_settings={"Port": 2575},
            host_settings={
                "MessageSchemaCategory": "PKB",
                "TargetConfigNames": "Router1,Router2",
            },
        )
        
        assert service.name == "test-service"
        assert service.message_schema_category == "PKB"
        assert "Router1" in service.target_config_names
    
    def test_service_from_config(self):
        """Test service initialization from ItemConfig."""
        config = ItemConfig(
            name="HL7.In.TCP",
            class_name="EnsLib.HL7.Service.TCPService",
            pool_size=2,
            enabled=True,
        )
        config.set_setting(SettingTarget.ADAPTER, "Port", 2575)
        config.set_setting(SettingTarget.HOST, "MessageSchemaCategory", "2.4")
        config.set_setting(SettingTarget.HOST, "TargetConfigNames", "HL7.Router")
        
        service = HL7TCPService(name=config.name, config=config)
        
        assert service.name == "HL7.In.TCP"
        assert service.pool_size == 2
        assert str(service.message_schema_category) == "2.4"
    
    @pytest.mark.asyncio
    async def test_service_on_message_received(self):
        """Test on_message_received processing."""
        service = HL7TCPService(
            name="test-service",
            adapter_settings={"Port": 19010},
            host_settings={"MessageSchemaCategory": "2.4"},
        )
        
        # Process message without starting (just test the method)
        service._schema = HL7Schema(name="2.4")
        result = await service.on_message_received(SAMPLE_ADT_A01)
        
        assert isinstance(result, HL7Message)
        assert result.message_type == "ADT_A01"
        assert result.ack is not None
        assert b"MSA|AA" in result.ack
    
    @pytest.mark.asyncio
    async def test_service_generates_error_ack(self):
        """Test service generates error ACK for invalid message."""
        service = HL7TCPService(
            name="test-service",
            adapter_settings={"Port": 19011},
            host_settings={"MessageSchemaCategory": "2.4"},
        )
        
        service._schema = HL7Schema(name="2.4")
        
        # Message missing required segments
        invalid_msg = b"MSH|^~\\&|APP|FAC|||20240101||ADT^A01|1|P|2.4\r"
        result = await service.on_message_received(invalid_msg)
        
        assert isinstance(result, HL7Message)
        # Should still have an ACK (may be AE for validation errors)
        assert result.ack is not None


class TestHL7TCPOperation:
    """Tests for HL7TCPOperation."""
    
    def test_operation_initialization(self):
        """Test operation initialization."""
        operation = HL7TCPOperation(
            name="test-operation",
            adapter_settings={
                "IPAddress": "192.168.1.100",
                "Port": 2575,
            },
            host_settings={
                "ReplyCodeActions": ":?R=F,:?E=S,:*=S",
            },
        )
        
        assert operation.name == "test-operation"
        assert operation.get_setting("Adapter", "IPAddress") == "192.168.1.100"
    
    def test_reply_code_actions_parsing(self):
        """Test ReplyCodeActions parsing."""
        operation = HL7TCPOperation(
            name="test-operation",
            host_settings={"ReplyCodeActions": ":?R=F,:?E=S,:AA=S,:*=W"},
        )
        
        # Test evaluation
        assert operation._evaluate_ack_code("AR") == "F"  # ?R matches AR
        assert operation._evaluate_ack_code("AE") == "S"  # ?E matches AE
        assert operation._evaluate_ack_code("AA") == "S"  # Exact match
        assert operation._evaluate_ack_code("CA") == "W"  # * matches anything else
    
    def test_reply_code_actions_default(self):
        """Test default ReplyCodeActions."""
        operation = HL7TCPOperation(
            name="test-operation",
            host_settings={},
        )
        
        # Default is :*=S (success for all)
        assert operation._evaluate_ack_code("AA") == "S"
        assert operation._evaluate_ack_code("AE") == "S"
        assert operation._evaluate_ack_code("AR") == "S"


class TestConditionEvaluator:
    """Tests for ConditionEvaluator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ConditionEvaluator()
        self.schema = HL7Schema(name="2.4")
        self.adt_a01 = HL7Message(
            raw=SAMPLE_ADT_A01,
            parsed=self.schema.parse(SAMPLE_ADT_A01),
        )
        self.oru_r01 = HL7Message(
            raw=SAMPLE_ORU_R01,
            parsed=self.schema.parse(SAMPLE_ORU_R01),
        )
    
    def test_simple_equality(self):
        """Test simple equality condition."""
        assert self.evaluator.evaluate('{MSH-9.1} = "ADT"', self.adt_a01) is True
        assert self.evaluator.evaluate('{MSH-9.1} = "ORU"', self.adt_a01) is False
    
    def test_inequality(self):
        """Test inequality condition."""
        assert self.evaluator.evaluate('{MSH-9.1} != "ORU"', self.adt_a01) is True
        assert self.evaluator.evaluate('{MSH-9.1} != "ADT"', self.adt_a01) is False
    
    def test_and_condition(self):
        """Test AND condition."""
        condition = '{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"'
        assert self.evaluator.evaluate(condition, self.adt_a01) is True
        
        condition = '{MSH-9.1} = "ADT" AND {MSH-9.2} = "A08"'
        assert self.evaluator.evaluate(condition, self.adt_a01) is False
    
    def test_or_condition(self):
        """Test OR condition."""
        condition = '{MSH-9.1} = "ADT" OR {MSH-9.1} = "ORU"'
        assert self.evaluator.evaluate(condition, self.adt_a01) is True
        assert self.evaluator.evaluate(condition, self.oru_r01) is True
        
        condition = '{MSH-9.1} = "ORM" OR {MSH-9.1} = "SIU"'
        assert self.evaluator.evaluate(condition, self.adt_a01) is False
    
    def test_not_condition(self):
        """Test NOT condition."""
        assert self.evaluator.evaluate('NOT {MSH-9.1} = "ORU"', self.adt_a01) is True
        assert self.evaluator.evaluate('NOT {MSH-9.1} = "ADT"', self.adt_a01) is False
    
    def test_contains(self):
        """Test Contains operator."""
        assert self.evaluator.evaluate('{PID-5} Contains "DOE"', self.adt_a01) is True
        assert self.evaluator.evaluate('{PID-5} Contains "SMITH"', self.adt_a01) is False
    
    def test_startswith(self):
        """Test StartsWith operator."""
        assert self.evaluator.evaluate('{PID-5.1} StartsWith "DO"', self.adt_a01) is True
        assert self.evaluator.evaluate('{PID-5.1} StartsWith "SM"', self.adt_a01) is False
    
    def test_endswith(self):
        """Test EndsWith operator."""
        assert self.evaluator.evaluate('{PID-5.1} EndsWith "OE"', self.adt_a01) is True
        assert self.evaluator.evaluate('{PID-5.1} EndsWith "TH"', self.adt_a01) is False
    
    def test_in_operator(self):
        """Test IN operator."""
        condition = '{MSH-9.1} IN ("ADT", "ORM", "ORU")'
        assert self.evaluator.evaluate(condition, self.adt_a01) is True
        assert self.evaluator.evaluate(condition, self.oru_r01) is True
        
        condition = '{MSH-9.1} IN ("SIU", "MDM")'
        assert self.evaluator.evaluate(condition, self.adt_a01) is False
    
    def test_empty_condition(self):
        """Test empty condition always matches."""
        assert self.evaluator.evaluate("", self.adt_a01) is True
        assert self.evaluator.evaluate("   ", self.adt_a01) is True
    
    def test_complex_condition(self):
        """Test complex nested condition."""
        condition = '({MSH-9.1} = "ADT" AND {MSH-9.2} = "A01") OR {MSH-9.1} = "ORU"'
        assert self.evaluator.evaluate(condition, self.adt_a01) is True
        assert self.evaluator.evaluate(condition, self.oru_r01) is True


class TestHL7RoutingEngine:
    """Tests for HL7RoutingEngine."""
    
    def test_routing_engine_initialization(self):
        """Test routing engine initialization."""
        engine = HL7RoutingEngine(
            name="test-router",
            host_settings={
                "BusinessRuleName": "Test.Router.Rules",
                "Validation": "Warn",
            },
        )
        
        assert engine.name == "test-router"
        assert engine.business_rule_name == "Test.Router.Rules"
        assert engine._validation == "Warn"
    
    def test_add_rule(self):
        """Test adding routing rules."""
        engine = HL7RoutingEngine(name="test-router")
        
        rule = RoutingRule(
            name="ADT_Route",
            condition='{MSH-9.1} = "ADT"',
            action=RuleAction.SEND,
            target="HL7.Out.PAS",
        )
        
        engine.add_rule(rule)
        
        assert len(engine._rules) == 1
        assert engine._rules[0].name == "ADT_Route"
    
    def test_load_rules_from_config(self):
        """Test loading rules from configuration."""
        engine = HL7RoutingEngine(name="test-router")
        
        config = {
            "rules": [
                {
                    "name": "ADT_A01_Route",
                    "condition": '{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"',
                    "action": "send",
                    "target": "HL7.Out.PAS",
                },
                {
                    "name": "ORU_Route",
                    "condition": '{MSH-9.1} = "ORU"',
                    "action": "send",
                    "target": "HL7.Out.LAB",
                },
            ]
        }
        
        engine.load_rules_from_config(config)
        
        assert len(engine._rules) == 2
    
    @pytest.mark.asyncio
    async def test_routing_evaluation(self):
        """Test routing rule evaluation."""
        engine = HL7RoutingEngine(name="test-router")
        
        engine.add_rule(RoutingRule(
            name="ADT_A01_Route",
            condition='{MSH-9.1} = "ADT" AND {MSH-9.2} = "A01"',
            action=RuleAction.SEND,
            target="HL7.Out.PAS",
        ))
        engine.add_rule(RoutingRule(
            name="ORU_Route",
            condition='{MSH-9.1} = "ORU"',
            action=RuleAction.SEND,
            target="HL7.Out.LAB",
        ))
        
        await engine.on_start()
        
        # Test ADT_A01 routing
        schema = HL7Schema(name="2.4")
        adt_message = HL7Message(
            raw=SAMPLE_ADT_A01,
            parsed=schema.parse(SAMPLE_ADT_A01),
        )
        
        result = await engine.on_message(adt_message)
        
        assert isinstance(result, RoutingResult)
        assert result.matched is True
        assert result.rule_name == "ADT_A01_Route"
        assert "HL7.Out.PAS" in result.targets
        
        # Test ORU routing
        oru_message = HL7Message(
            raw=SAMPLE_ORU_R01,
            parsed=schema.parse(SAMPLE_ORU_R01),
        )
        
        result = await engine.on_message(oru_message)
        
        assert result.matched is True
        assert result.rule_name == "ORU_Route"
        assert "HL7.Out.LAB" in result.targets
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_routing_no_match(self):
        """Test routing when no rule matches."""
        engine = HL7RoutingEngine(name="test-router")
        
        engine.add_rule(RoutingRule(
            name="SIU_Route",
            condition='{MSH-9.1} = "SIU"',
            action=RuleAction.SEND,
            target="HL7.Out.Scheduling",
        ))
        
        await engine.on_start()
        
        schema = HL7Schema(name="2.4")
        message = HL7Message(
            raw=SAMPLE_ADT_A01,
            parsed=schema.parse(SAMPLE_ADT_A01),
        )
        
        result = await engine.on_message(message)
        
        assert result.matched is False
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_routing_with_default_target(self):
        """Test routing falls back to default target."""
        engine = HL7RoutingEngine(
            name="test-router",
            host_settings={"TargetConfigNames": "DefaultTarget"},
        )
        
        # No rules added
        await engine.on_start()
        
        schema = HL7Schema(name="2.4")
        message = HL7Message(
            raw=SAMPLE_ADT_A01,
            parsed=schema.parse(SAMPLE_ADT_A01),
        )
        
        result = await engine.on_message(message)
        
        assert result.matched is True
        assert result.rule_name == "default"
        assert "DefaultTarget" in result.targets
        
        await engine.stop()


class TestRoutingRuleHelpers:
    """Tests for routing rule helper functions."""
    
    def test_create_message_type_rule(self):
        """Test create_message_type_rule helper."""
        rule = create_message_type_rule(
            name="ADT_Route",
            message_type="ADT",
            target="HL7.Out.PAS",
        )
        
        assert rule.name == "ADT_Route"
        assert '{MSH-9.1} = "ADT"' in rule.condition
        assert rule.target == "HL7.Out.PAS"
    
    def test_create_message_type_rule_with_trigger(self):
        """Test create_message_type_rule with trigger event."""
        rule = create_message_type_rule(
            name="ADT_A01_Route",
            message_type="ADT",
            target="HL7.Out.PAS",
            trigger_event="A01",
        )
        
        assert '{MSH-9.1} = "ADT"' in rule.condition
        assert '{MSH-9.2} = "A01"' in rule.condition
        assert "AND" in rule.condition
    
    def test_create_facility_rule(self):
        """Test create_facility_rule helper."""
        rule = create_facility_rule(
            name="Hospital_Route",
            sending_facility="HOSPITAL",
            target="HL7.Out.External",
        )
        
        assert rule.name == "Hospital_Route"
        assert '{MSH-4} = "HOSPITAL"' in rule.condition
        assert rule.target == "HL7.Out.External"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
