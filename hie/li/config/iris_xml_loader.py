"""
IRIS XML Configuration Loader

Parses IRIS production XML configuration files and creates ProductionConfig objects.
Supports both standalone XML files and .cls files with embedded XData.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import structlog

from hie.li.config.item_config import ItemConfig, ItemSetting, SettingTarget
from hie.li.config.production_config import ProductionConfig

logger = structlog.get_logger(__name__)


class IRISXMLLoader:
    """
    Loads IRIS Production XML configuration.
    
    Supports two formats:
    1. Pure XML files containing <Production> element
    2. .cls files with XData ProductionDefinition containing XML
    
    Example IRIS XML:
    ```xml
    <Production Name="BHRUH.Production.ADTProduction" TestingEnabled="true">
      <Description>ADT Production</Description>
      <ActorPoolSize>2</ActorPoolSize>
      <Item Name="from.BHR.ADT1" ClassName="EnsLib.HL7.Service.TCPService" PoolSize="1" Enabled="true">
        <Setting Target="Adapter" Name="Port">35001</Setting>
        <Setting Target="Host" Name="MessageSchemaCategory">PKB</Setting>
        <Setting Target="Host" Name="TargetConfigNames">Main ADT Router</Setting>
      </Item>
    </Production>
    ```
    """
    
    def __init__(self):
        self._class_mapping: dict[str, str] = {}
        self._setup_default_class_mapping()
    
    def _setup_default_class_mapping(self) -> None:
        """
        Set up default IRIS to LI class name mapping.
        
        Maps IRIS class names to LI equivalents.
        """
        self._class_mapping = {
            # HL7 Services (Inbound)
            "EnsLib.HL7.Service.TCPService": "li.hosts.hl7.HL7TCPService",
            "EnsLib.HL7.Service.HTTPService": "li.hosts.hl7.HL7HTTPService",
            "EnsLib.HL7.Service.FileService": "li.hosts.hl7.HL7FileService",
            "EnsLib.HL7.Service.FTPService": "li.hosts.hl7.HL7FTPService",
            
            # HL7 Operations (Outbound)
            "EnsLib.HL7.Operation.TCPOperation": "li.hosts.hl7.HL7TCPOperation",
            "EnsLib.HL7.Operation.HTTPOperation": "li.hosts.hl7.HL7HTTPOperation",
            "EnsLib.HL7.Operation.FileOperation": "li.hosts.hl7.HL7FileOperation",
            "EnsLib.HL7.Operation.FTPOperation": "li.hosts.hl7.HL7FTPOperation",
            
            # HL7 Processes
            "EnsLib.HL7.MsgRouter.RoutingEngine": "li.hosts.hl7.HL7RoutingEngine",
            "EnsLib.HL7.SequenceManager": "li.hosts.hl7.HL7SequenceManager",
            
            # Generic Routing
            "EnsLib.MsgRouter.RoutingEngine": "li.hosts.routing.RoutingEngine",
            
            # Email
            "EnsLib.EMail.AlertOperation": "li.hosts.email.EmailAlertOperation",
            
            # SOAP/HTTP
            "EnsLib.SOAP.GenericOperation": "li.hosts.soap.SOAPOperation",
        }
    
    def register_class_mapping(self, iris_class: str, li_class: str) -> None:
        """
        Register a custom IRIS to LI class mapping.
        
        Args:
            iris_class: IRIS class name (e.g., "EnsLib.HL7.Service.TCPService")
            li_class: LI class name (e.g., "li.hosts.hl7.HL7TCPService")
        """
        self._class_mapping[iris_class] = li_class
    
    def map_class_name(self, iris_class: str) -> str:
        """
        Map IRIS class name to LI class name.
        
        If no mapping exists, returns the original class name with a prefix.
        Custom classes (not starting with EnsLib) are preserved.
        
        Args:
            iris_class: IRIS class name
            
        Returns:
            LI class name
        """
        if iris_class in self._class_mapping:
            return self._class_mapping[iris_class]
        
        # For custom classes, preserve the name but add li.custom prefix
        if not iris_class.startswith("EnsLib."):
            return f"li.custom.{iris_class}"
        
        # Unknown EnsLib class - log warning and use generic mapping
        logger.warning("unknown_iris_class", iris_class=iris_class)
        return f"li.unknown.{iris_class}"
    
    def load(self, path: str | Path) -> ProductionConfig:
        """
        Load production configuration from a file.
        
        Automatically detects file type (.xml or .cls).
        
        Args:
            path: Path to configuration file
            
        Returns:
            ProductionConfig object
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        content = path.read_text(encoding="utf-8")
        
        if path.suffix.lower() == ".cls":
            return self.load_from_cls(content)
        else:
            return self.load_from_xml(content)
    
    def load_from_cls(self, cls_content: str) -> ProductionConfig:
        """
        Load production from IRIS .cls file content.
        
        Extracts XML from XData ProductionDefinition block.
        
        Args:
            cls_content: Content of .cls file
            
        Returns:
            ProductionConfig object
        """
        # Extract XML from XData block
        # Pattern: XData ProductionDefinition { <Production>...</Production> }
        pattern = r'XData\s+ProductionDefinition\s*\{(.*?)\}'
        match = re.search(pattern, cls_content, re.DOTALL)
        
        if not match:
            raise ValueError("No XData ProductionDefinition found in .cls file")
        
        xml_content = match.group(1).strip()
        return self.load_from_xml(xml_content)
    
    def load_from_xml(self, xml_content: str) -> ProductionConfig:
        """
        Load production from XML string.
        
        Args:
            xml_content: XML string containing <Production> element
            
        Returns:
            ProductionConfig object
        """
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        
        # Handle both root <Production> and nested <Production>
        if root.tag != "Production":
            production_elem = root.find(".//Production")
            if production_elem is None:
                raise ValueError("No <Production> element found in XML")
            root = production_elem
        
        return self._parse_production(root)
    
    def _parse_production(self, elem: ET.Element) -> ProductionConfig:
        """Parse <Production> element into ProductionConfig."""
        # Extract attributes
        name = elem.get("Name", "Unknown")
        testing_enabled = self._parse_bool(elem.get("TestingEnabled", "false"))
        log_trace = self._parse_bool(elem.get("LogGeneralTraceEvents", "false"))
        
        # Extract child elements
        description = ""
        desc_elem = elem.find("Description")
        if desc_elem is not None and desc_elem.text:
            description = desc_elem.text.strip()
        
        actor_pool_size = 2
        pool_elem = elem.find("ActorPoolSize")
        if pool_elem is not None and pool_elem.text:
            try:
                actor_pool_size = int(pool_elem.text.strip())
            except ValueError:
                pass
        
        # Parse items
        items = []
        for item_elem in elem.findall("Item"):
            item = self._parse_item(item_elem)
            items.append(item)
        
        logger.info(
            "production_loaded",
            name=name,
            items_count=len(items),
            enabled_count=sum(1 for i in items if i.enabled),
        )
        
        return ProductionConfig(
            name=name,
            description=description,
            testing_enabled=testing_enabled,
            log_general_trace_events=log_trace,
            actor_pool_size=actor_pool_size,
            items=items,
        )
    
    def _parse_item(self, elem: ET.Element) -> ItemConfig:
        """Parse <Item> element into ItemConfig."""
        # Extract attributes
        name = elem.get("Name", "")
        class_name = elem.get("ClassName", "")
        pool_size = self._parse_int(elem.get("PoolSize", "1"), 1)
        enabled = self._parse_bool(elem.get("Enabled", "true"))
        foreground = self._parse_bool(elem.get("Foreground", "false"))
        category = elem.get("Category", "")
        comment = elem.get("Comment", "")
        log_trace = self._parse_bool(elem.get("LogTraceEvents", "false"))
        schedule = elem.get("Schedule", "")
        
        # Map class name to LI equivalent
        li_class_name = self.map_class_name(class_name)
        
        # Parse settings
        settings = []
        for setting_elem in elem.findall("Setting"):
            setting = self._parse_setting(setting_elem)
            if setting:
                settings.append(setting)
        
        return ItemConfig(
            name=name,
            class_name=li_class_name,
            pool_size=pool_size,
            enabled=enabled,
            foreground=foreground,
            category=category,
            comment=comment,
            log_trace_events=log_trace,
            schedule=schedule,
            settings=settings,
        )
    
    def _parse_setting(self, elem: ET.Element) -> ItemSetting | None:
        """Parse <Setting> element into ItemSetting."""
        target_str = elem.get("Target", "")
        name = elem.get("Name", "")
        value = elem.text or ""
        
        if not target_str or not name:
            return None
        
        try:
            target = SettingTarget(target_str)
        except ValueError:
            logger.warning("invalid_setting_target", target=target_str, name=name)
            return None
        
        return ItemSetting(target=target, name=name, value=value.strip())
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string to boolean."""
        return value.lower() in ("true", "1", "yes")
    
    def _parse_int(self, value: str, default: int = 0) -> int:
        """Parse string to integer with default."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def save_to_xml(self, config: ProductionConfig, path: str | Path) -> None:
        """
        Save production configuration to XML file.
        
        Args:
            config: ProductionConfig to save
            path: Output file path
        """
        xml_str = self.to_xml(config)
        Path(path).write_text(xml_str, encoding="utf-8")
    
    def to_xml(self, config: ProductionConfig) -> str:
        """
        Convert ProductionConfig to XML string.
        
        Args:
            config: ProductionConfig to convert
            
        Returns:
            XML string
        """
        root = ET.Element("Production")
        root.set("Name", config.name)
        root.set("TestingEnabled", str(config.testing_enabled).lower())
        root.set("LogGeneralTraceEvents", str(config.log_general_trace_events).lower())
        
        # Description
        if config.description:
            desc = ET.SubElement(root, "Description")
            desc.text = config.description
        
        # ActorPoolSize
        pool = ET.SubElement(root, "ActorPoolSize")
        pool.text = str(config.actor_pool_size)
        
        # Items
        for item in config.items:
            item_elem = ET.SubElement(root, "Item")
            item_elem.set("Name", item.name)
            item_elem.set("ClassName", item.class_name)
            item_elem.set("PoolSize", str(item.pool_size))
            item_elem.set("Enabled", str(item.enabled).lower())
            item_elem.set("Foreground", str(item.foreground).lower())
            
            if item.category:
                item_elem.set("Category", item.category)
            if item.comment:
                item_elem.set("Comment", item.comment)
            
            item_elem.set("LogTraceEvents", str(item.log_trace_events).lower())
            
            if item.schedule:
                item_elem.set("Schedule", item.schedule)
            
            # Settings
            for setting in item.settings:
                setting_elem = ET.SubElement(item_elem, "Setting")
                setting_elem.set("Target", setting.target.value)
                setting_elem.set("Name", setting.name)
                setting_elem.text = setting.value
        
        # Pretty print
        self._indent(root)
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
    
    def _indent(self, elem: ET.Element, level: int = 0) -> None:
        """Add indentation to XML element for pretty printing."""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
