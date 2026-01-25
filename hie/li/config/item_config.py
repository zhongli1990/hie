"""
LI Item Configuration

Defines the configuration model for production items (hosts).
Matches IRIS production item structure with Adapter and Host settings separation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SettingTarget(str, Enum):
    """Target for a setting - either the Host or its Adapter."""
    HOST = "Host"
    ADAPTER = "Adapter"


class ItemSetting(BaseModel):
    """A single setting for an item."""
    model_config = ConfigDict(extra="forbid")
    
    target: SettingTarget = Field(description="Whether setting applies to Host or Adapter")
    name: str = Field(description="Setting name")
    value: str = Field(description="Setting value as string")
    
    def get_typed_value(self) -> Any:
        """
        Convert string value to appropriate Python type.
        
        Handles common conversions:
        - "true"/"false" -> bool
        - numeric strings -> int/float
        - empty string -> None
        """
        if self.value == "":
            return None
        if self.value.lower() == "true":
            return True
        if self.value.lower() == "false":
            return False
        
        # Try integer
        try:
            return int(self.value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(self.value)
        except ValueError:
            pass
        
        return self.value


class ItemConfig(BaseModel):
    """
    Configuration for a production item (host).
    
    Matches IRIS production item structure:
    <Item Name="..." ClassName="..." PoolSize="1" Enabled="true" ...>
      <Setting Target="Host" Name="...">value</Setting>
      <Setting Target="Adapter" Name="...">value</Setting>
    </Item>
    """
    model_config = ConfigDict(extra="allow")
    
    # Core attributes (from XML attributes)
    name: str = Field(description="Unique item name within production")
    class_name: str = Field(description="Full class name (e.g., EnsLib.HL7.Service.TCPService)")
    pool_size: int = Field(default=1, ge=1, description="Number of worker instances")
    enabled: bool = Field(default=True, description="Whether item is enabled")
    foreground: bool = Field(default=False, description="Run in foreground (blocking)")
    
    # Optional attributes
    category: str | None = Field(default="", description="Category for grouping in UI")
    comment: str | None = Field(default="", description="Human-readable comment")
    log_trace_events: bool = Field(default=False, description="Enable trace logging")
    schedule: str = Field(default="", description="Schedule specification")
    
    # Settings (from child Setting elements)
    settings: list[ItemSetting] = Field(default_factory=list, description="Item settings")
    
    @property
    def host_settings(self) -> dict[str, Any]:
        """Get all Host-targeted settings as a dictionary."""
        return {
            s.name: s.get_typed_value()
            for s in self.settings
            if s.target == SettingTarget.HOST
        }
    
    @property
    def adapter_settings(self) -> dict[str, Any]:
        """Get all Adapter-targeted settings as a dictionary."""
        return {
            s.name: s.get_typed_value()
            for s in self.settings
            if s.target == SettingTarget.ADAPTER
        }
    
    def get_setting(self, target: SettingTarget | str, name: str, default: Any = None) -> Any:
        """
        Get a specific setting value.
        
        Args:
            target: SettingTarget.HOST or SettingTarget.ADAPTER (or string)
            name: Setting name
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        if isinstance(target, str):
            target = SettingTarget(target)
        
        for setting in self.settings:
            if setting.target == target and setting.name == name:
                return setting.get_typed_value()
        return default
    
    def set_setting(self, target: SettingTarget | str, name: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            target: SettingTarget.HOST or SettingTarget.ADAPTER (or string)
            name: Setting name
            value: Setting value (will be converted to string)
        """
        if isinstance(target, str):
            target = SettingTarget(target)
        
        # Convert value to string
        str_value = "" if value is None else str(value)
        if isinstance(value, bool):
            str_value = str(value).lower()
        
        # Update existing or add new
        for setting in self.settings:
            if setting.target == target and setting.name == name:
                setting.value = str_value
                return
        
        self.settings.append(ItemSetting(target=target, name=name, value=str_value))
    
    @property
    def item_type(self) -> str:
        """
        Determine item type from class name.
        
        Returns:
            "service", "process", or "operation"
        """
        class_lower = self.class_name.lower()
        if ".service." in class_lower or class_lower.endswith("service"):
            return "service"
        elif ".operation." in class_lower or class_lower.endswith("operation"):
            return "operation"
        else:
            return "process"
    
    @property
    def is_hl7(self) -> bool:
        """Check if this is an HL7-related item."""
        return ".hl7." in self.class_name.lower()
    
    @property
    def target_config_names(self) -> list[str]:
        """Get list of target config names (for services/processes)."""
        targets = self.get_setting(SettingTarget.HOST, "TargetConfigNames", "")
        if not targets:
            return []
        return [t.strip() for t in targets.split(",") if t.strip()]
    
    @property
    def message_schema_category(self) -> str | None:
        """Get the message schema category (for HL7 items)."""
        return self.get_setting(SettingTarget.HOST, "MessageSchemaCategory")
    
    @property
    def business_rule_name(self) -> str | None:
        """Get the business rule name (for routing engines)."""
        return self.get_setting(SettingTarget.HOST, "BusinessRuleName")
