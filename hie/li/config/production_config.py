"""
LI Production Configuration

Defines the configuration model for a complete production.
Matches IRIS production structure.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hie.li.config.item_config import ItemConfig


class ProductionConfig(BaseModel):
    """
    Configuration for a complete LI production.
    
    Matches IRIS production structure:
    <Production Name="..." TestingEnabled="true" LogGeneralTraceEvents="true">
      <Description>...</Description>
      <ActorPoolSize>2</ActorPoolSize>
      <Item ...>...</Item>
      ...
    </Production>
    """
    model_config = ConfigDict(extra="allow")
    
    # Core attributes
    name: str = Field(description="Production name (e.g., BHRUH.Production.ADTProduction)")
    description: str = Field(default="", description="Production description")
    
    # Production settings
    testing_enabled: bool = Field(default=False, description="Enable testing mode")
    log_general_trace_events: bool = Field(default=False, description="Enable general trace logging")
    actor_pool_size: int = Field(default=2, ge=1, description="Default actor pool size")
    
    # Items
    items: list[ItemConfig] = Field(default_factory=list, description="Production items")
    
    @property
    def enabled_items(self) -> list[ItemConfig]:
        """Get only enabled items."""
        return [item for item in self.items if item.enabled]
    
    @property
    def services(self) -> list[ItemConfig]:
        """Get all service items (inbound)."""
        return [item for item in self.items if item.item_type == "service"]
    
    @property
    def processes(self) -> list[ItemConfig]:
        """Get all process items (routing, transform)."""
        return [item for item in self.items if item.item_type == "process"]
    
    @property
    def operations(self) -> list[ItemConfig]:
        """Get all operation items (outbound)."""
        return [item for item in self.items if item.item_type == "operation"]
    
    def get_item(self, name: str) -> ItemConfig | None:
        """Get an item by name."""
        for item in self.items:
            if item.name == name:
                return item
        return None
    
    def get_items_by_category(self, category: str) -> list[ItemConfig]:
        """Get items by category."""
        return [
            item for item in self.items
            if category.lower() in item.category.lower()
        ]
    
    def get_items_by_class(self, class_name: str) -> list[ItemConfig]:
        """Get items by class name (partial match)."""
        return [
            item for item in self.items
            if class_name.lower() in item.class_name.lower()
        ]
    
    def validate_targets(self) -> list[str]:
        """
        Validate that all TargetConfigNames reference existing items.
        
        Returns:
            List of error messages for invalid targets
        """
        errors = []
        item_names = {item.name for item in self.items}
        
        for item in self.items:
            for target in item.target_config_names:
                if target not in item_names:
                    errors.append(
                        f"Item '{item.name}' references unknown target '{target}'"
                    )
        
        return errors
    
    def get_dependency_order(self) -> list[str]:
        """
        Get items in dependency order (targets before sources).
        
        Operations first, then processes, then services.
        Within each category, items with no targets come first.
        
        Returns:
            List of item names in startup order
        """
        # Group by type
        operations = [i for i in self.enabled_items if i.item_type == "operation"]
        processes = [i for i in self.enabled_items if i.item_type == "process"]
        services = [i for i in self.enabled_items if i.item_type == "service"]
        
        # Simple ordering: operations -> processes -> services
        # This ensures targets exist before sources try to send to them
        order = []
        order.extend(op.name for op in operations)
        order.extend(proc.name for proc in processes)
        order.extend(svc.name for svc in services)
        
        return order
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductionConfig:
        """Create from dictionary."""
        return cls.model_validate(data)
