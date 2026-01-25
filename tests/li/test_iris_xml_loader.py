"""
Tests for IRIS XML Configuration Loader.

Tests loading of IRIS production XML files and .cls files.
"""

import pytest
from pathlib import Path

from hie.li.config import IRISXMLLoader, ProductionConfig, ItemConfig, SettingTarget


# Sample IRIS XML for testing
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Production Name="Test.Production" TestingEnabled="true" LogGeneralTraceEvents="false">
  <Description>Test Production for Unit Tests</Description>
  <ActorPoolSize>4</ActorPoolSize>
  <Item Name="HL7 from PAS" Category="Inbound" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="2" Enabled="true" Foreground="false" Comment="PAS ADT Feed" LogTraceEvents="true" Schedule="">
    <Setting Target="Adapter" Name="Port">35001</Setting>
    <Setting Target="Adapter" Name="SSLConfig">MySSL</Setting>
    <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
    <Setting Target="Host" Name="TargetConfigNames">ADT Router,Audit Logger</Setting>
    <Setting Target="Host" Name="AckMode">App</Setting>
    <Setting Target="Host" Name="ArchiveIO">1</Setting>
  </Item>
  <Item Name="ADT Router" Category="Process" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="Validation">d-z</Setting>
    <Setting Target="Host" Name="BusinessRuleName">Test.Router.ADTRules</Setting>
  </Item>
  <Item Name="HL7 to PACS" Category="Outbound" ClassName="EnsLib.HL7.Operation.TCPOperation" PoolSize="1" Enabled="false" Foreground="false" Comment="PACS System" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="IPAddress">10.0.0.100</Setting>
    <Setting Target="Adapter" Name="Port">2575</Setting>
    <Setting Target="Host" Name="ArchiveIO">0</Setting>
    <Setting Target="Host" Name="ReplyCodeActions">:?R=F,:?E=S,:~=S,:?A=C,:*=S</Setting>
  </Item>
  <Item Name="Audit Logger" Category="Process" ClassName="EnsLib.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">Test.Router.AuditRules</Setting>
  </Item>
</Production>
"""

# Sample .cls file content
SAMPLE_CLS = """Class Test.Productions.Sample Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="Test.Productions.Sample" TestingEnabled="false" LogGeneralTraceEvents="true">
  <Description>Sample from CLS file</Description>
  <ActorPoolSize>2</ActorPoolSize>
  <Item Name="SimpleService" Category="" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Adapter" Name="Port">8080</Setting>
    <Setting Target="Host" Name="TargetConfigNames">SimpleRouter</Setting>
  </Item>
  <Item Name="SimpleRouter" Category="" ClassName="EnsLib.HL7.MsgRouter.RoutingEngine" PoolSize="1" Enabled="true" Foreground="false" Comment="" LogTraceEvents="false" Schedule="">
    <Setting Target="Host" Name="BusinessRuleName">Test.Rules.Simple</Setting>
  </Item>
</Production>
}

}
"""


class TestIRISXMLLoader:
    """Tests for IRISXMLLoader class."""
    
    def test_load_from_xml_basic(self):
        """Test loading basic XML configuration."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        assert isinstance(config, ProductionConfig)
        assert config.name == "Test.Production"
        assert config.testing_enabled is True
        assert config.log_general_trace_events is False
        assert config.actor_pool_size == 4
        assert config.description == "Test Production for Unit Tests"
    
    def test_load_items(self):
        """Test that items are loaded correctly."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        assert len(config.items) == 4
        
        # Check service item
        service = config.get_item("HL7 from PAS")
        assert service is not None
        assert service.pool_size == 2
        assert service.enabled is True
        assert service.category == "Inbound"
        assert service.comment == "PAS ADT Feed"
        assert service.log_trace_events is True
    
    def test_class_name_mapping(self):
        """Test IRIS to LI class name mapping."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        assert service.class_name == "li.hosts.hl7.HL7TCPService"
        
        router = config.get_item("ADT Router")
        assert router.class_name == "li.hosts.routing.HL7RoutingEngine"
        
        operation = config.get_item("HL7 to PACS")
        assert operation.class_name == "li.hosts.hl7.HL7TCPOperation"
    
    def test_settings_parsing(self):
        """Test that settings are parsed correctly."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        
        # Adapter settings
        assert service.get_setting(SettingTarget.ADAPTER, "Port") == 35001
        assert service.get_setting(SettingTarget.ADAPTER, "SSLConfig") == "MySSL"
        
        # Host settings
        assert service.get_setting(SettingTarget.HOST, "MessageSchemaCategory") == "PKB"
        assert service.get_setting(SettingTarget.HOST, "AckMode") == "App"
        assert service.get_setting(SettingTarget.HOST, "ArchiveIO") == 1
    
    def test_host_settings_property(self):
        """Test host_settings property returns correct dict."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        host_settings = service.host_settings
        
        assert host_settings["MessageSchemaCategory"] == "PKB"
        assert host_settings["AckMode"] == "App"
        assert host_settings["ArchiveIO"] == 1
        assert "Port" not in host_settings  # Port is adapter setting
    
    def test_adapter_settings_property(self):
        """Test adapter_settings property returns correct dict."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        adapter_settings = service.adapter_settings
        
        assert adapter_settings["Port"] == 35001
        assert adapter_settings["SSLConfig"] == "MySSL"
        assert "MessageSchemaCategory" not in adapter_settings
    
    def test_target_config_names(self):
        """Test parsing of TargetConfigNames."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        targets = service.target_config_names
        
        assert len(targets) == 2
        assert "ADT Router" in targets
        assert "Audit Logger" in targets
    
    def test_item_type_detection(self):
        """Test automatic item type detection."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        service = config.get_item("HL7 from PAS")
        assert service.item_type == "service"
        
        router = config.get_item("ADT Router")
        assert router.item_type == "process"
        
        operation = config.get_item("HL7 to PACS")
        assert operation.item_type == "operation"
    
    def test_enabled_items(self):
        """Test filtering enabled items."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        enabled = config.enabled_items
        assert len(enabled) == 3  # One item is disabled
        
        names = [i.name for i in enabled]
        assert "HL7 to PACS" not in names  # This one is disabled
    
    def test_services_processes_operations(self):
        """Test filtering by item type."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        assert len(config.services) == 1
        assert len(config.processes) == 2
        assert len(config.operations) == 1
    
    def test_load_from_cls(self):
        """Test loading from .cls file content."""
        loader = IRISXMLLoader()
        config = loader.load_from_cls(SAMPLE_CLS)
        
        assert config.name == "Test.Productions.Sample"
        assert config.testing_enabled is False
        assert config.log_general_trace_events is True
        assert len(config.items) == 2
    
    def test_validate_targets(self):
        """Test target validation."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        errors = config.validate_targets()
        assert len(errors) == 0  # All targets exist
        
        # Add an item with invalid target
        from hie.li.config.item_config import ItemConfig, ItemSetting
        bad_item = ItemConfig(
            name="BadService",
            class_name="li.hosts.hl7.HL7TCPService",
            settings=[
                ItemSetting(target=SettingTarget.HOST, name="TargetConfigNames", value="NonExistent")
            ]
        )
        config.items.append(bad_item)
        
        errors = config.validate_targets()
        assert len(errors) == 1
        assert "NonExistent" in errors[0]
    
    def test_dependency_order(self):
        """Test dependency ordering for startup."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        order = config.get_dependency_order()
        
        # Operations should come before processes, processes before services
        op_idx = order.index("HL7 to PACS") if "HL7 to PACS" in order else -1
        router_idx = order.index("ADT Router")
        service_idx = order.index("HL7 from PAS")
        
        # Note: disabled items are excluded from dependency order
        assert router_idx < service_idx  # Process before service
    
    def test_to_xml_roundtrip(self):
        """Test XML serialization roundtrip."""
        loader = IRISXMLLoader()
        config = loader.load_from_xml(SAMPLE_XML)
        
        # Serialize back to XML
        xml_output = loader.to_xml(config)
        
        # Load again
        config2 = loader.load_from_xml(xml_output)
        
        # Verify key properties match
        assert config2.name == config.name
        assert len(config2.items) == len(config.items)
        
        for item1, item2 in zip(config.items, config2.items):
            assert item1.name == item2.name
            assert item1.enabled == item2.enabled
    
    def test_custom_class_mapping(self):
        """Test custom class name mapping."""
        loader = IRISXMLLoader()
        loader.register_class_mapping(
            "Custom.HL7.Service",
            "li.custom.MyHL7Service"
        )
        
        xml = """
        <Production Name="Test">
          <Item Name="Custom" ClassName="Custom.HL7.Service" PoolSize="1" Enabled="true">
          </Item>
        </Production>
        """
        
        config = loader.load_from_xml(xml)
        item = config.get_item("Custom")
        assert item.class_name == "li.custom.MyHL7Service"
    
    def test_unknown_enslib_class(self):
        """Test handling of unknown EnsLib classes."""
        loader = IRISXMLLoader()
        
        xml = """
        <Production Name="Test">
          <Item Name="Unknown" ClassName="EnsLib.Unknown.NewService" PoolSize="1" Enabled="true">
          </Item>
        </Production>
        """
        
        config = loader.load_from_xml(xml)
        item = config.get_item("Unknown")
        assert item.class_name.startswith("li.unknown.")
    
    def test_boolean_setting_conversion(self):
        """Test boolean setting value conversion."""
        loader = IRISXMLLoader()
        
        xml = """
        <Production Name="Test">
          <Item Name="Test" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
            <Setting Target="Host" Name="BoolTrue">true</Setting>
            <Setting Target="Host" Name="BoolFalse">false</Setting>
            <Setting Target="Host" Name="BoolOne">1</Setting>
            <Setting Target="Host" Name="BoolZero">0</Setting>
          </Item>
        </Production>
        """
        
        config = loader.load_from_xml(xml)
        item = config.get_item("Test")
        
        assert item.get_setting(SettingTarget.HOST, "BoolTrue") is True
        assert item.get_setting(SettingTarget.HOST, "BoolFalse") is False
        # Note: "1" and "0" are converted to int, not bool
        assert item.get_setting(SettingTarget.HOST, "BoolOne") == 1
        assert item.get_setting(SettingTarget.HOST, "BoolZero") == 0


class TestItemConfig:
    """Tests for ItemConfig class."""
    
    def test_set_setting(self):
        """Test setting a setting value."""
        item = ItemConfig(name="Test", class_name="li.hosts.hl7.HL7TCPService")
        
        item.set_setting(SettingTarget.HOST, "TestSetting", "TestValue")
        assert item.get_setting(SettingTarget.HOST, "TestSetting") == "TestValue"
        
        # Update existing
        item.set_setting(SettingTarget.HOST, "TestSetting", "NewValue")
        assert item.get_setting(SettingTarget.HOST, "TestSetting") == "NewValue"
    
    def test_set_setting_bool(self):
        """Test setting boolean values."""
        item = ItemConfig(name="Test", class_name="li.hosts.hl7.HL7TCPService")
        
        item.set_setting(SettingTarget.HOST, "Enabled", True)
        assert item.get_setting(SettingTarget.HOST, "Enabled") is True
        
        item.set_setting(SettingTarget.HOST, "Enabled", False)
        assert item.get_setting(SettingTarget.HOST, "Enabled") is False
    
    def test_is_hl7(self):
        """Test HL7 detection."""
        hl7_item = ItemConfig(name="Test", class_name="li.hosts.hl7.HL7TCPService")
        assert hl7_item.is_hl7 is True
        
        other_item = ItemConfig(name="Test", class_name="li.hosts.email.EmailOperation")
        assert other_item.is_hl7 is False
    
    def test_message_schema_category(self):
        """Test message_schema_category property."""
        item = ItemConfig(name="Test", class_name="li.hosts.hl7.HL7TCPService")
        assert item.message_schema_category is None
        
        item.set_setting(SettingTarget.HOST, "MessageSchemaCategory", "PKB")
        assert item.message_schema_category == "PKB"
    
    def test_business_rule_name(self):
        """Test business_rule_name property."""
        item = ItemConfig(name="Test", class_name="li.hosts.hl7.HL7RoutingEngine")
        assert item.business_rule_name is None
        
        item.set_setting(SettingTarget.HOST, "BusinessRuleName", "Test.Rules")
        assert item.business_rule_name == "Test.Rules"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
