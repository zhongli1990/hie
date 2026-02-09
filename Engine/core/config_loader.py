"""
HIE Production Configuration Loader

Loads production configurations from JSON files and creates fully configured
Production instances with all items, connections, and routing rules.

This enables:
1. Fully configurable routes via JSON (no hardcoded Python)
2. Visual editor compatibility
3. Runtime configuration changes via API
4. Import/export of configurations
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Type

import structlog

from Engine.core.schema import (
    ProductionSchema,
    ItemSchema,
    ConnectionSchema,
    RoutingRule,
    FilterGroup,
    FilterCondition,
    ItemCategory,
    ItemType,
)
from Engine.core.production import Production, ProductionConfig
from Engine.core.route import Route, RouteConfig
from Engine.core.item import Item, ItemConfig

logger = structlog.get_logger(__name__)


# Item type registry - maps type strings to item classes
_item_registry: dict[str, Type[Item]] = {}


def register_item_type(type_name: str, item_class: Type[Item]) -> None:
    """Register an item type for configuration loading."""
    _item_registry[type_name] = item_class
    logger.debug("item_type_registered", type_name=type_name, class_name=item_class.__name__)


def get_item_class(type_name: str) -> Type[Item] | None:
    """Get the item class for a type name."""
    return _item_registry.get(type_name)


class ConfigurationLoader:
    """Loads and validates production configurations."""
    
    def __init__(self):
        self._register_default_items()
    
    def _register_default_items(self) -> None:
        """Register built-in item types."""
        # Import here to avoid circular imports
        try:
            from Engine.items.receivers.http import HTTPReceiver
            from Engine.items.receivers.file import FileReceiver
            from Engine.items.senders.mllp import MLLPSender
            from Engine.items.senders.file import FileSender
            from Engine.items.processors.passthrough import PassthroughProcessor
            from Engine.items.processors.transform import TransformProcessor
            
            register_item_type("receiver.http", HTTPReceiver)
            register_item_type("receiver.file", FileReceiver)
            register_item_type("sender.mllp", MLLPSender)
            register_item_type("sender.file", FileSender)
            register_item_type("processor.passthrough", PassthroughProcessor)
            register_item_type("processor.transform", TransformProcessor)
        except ImportError as e:
            logger.warning("failed_to_register_default_items", error=str(e))
    
    def load_from_file(self, path: str | Path) -> ProductionSchema:
        """Load production configuration from a JSON file."""
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, "r") as f:
            data = json.load(f)
        
        return self.load_from_dict(data)
    
    def load_from_dict(self, data: dict[str, Any]) -> ProductionSchema:
        """Load production configuration from a dictionary."""
        return ProductionSchema.model_validate(data)
    
    def load_from_json(self, json_str: str) -> ProductionSchema:
        """Load production configuration from a JSON string."""
        data = json.loads(json_str)
        return self.load_from_dict(data)
    
    def create_production(self, schema: ProductionSchema) -> Production:
        """Create a Production instance from a schema."""
        # Create production config
        prod_config = ProductionConfig(
            name=schema.name,
            description=schema.description,
            enabled=schema.enabled,
            graceful_shutdown_timeout=schema.settings.graceful_shutdown_timeout,
            health_check_interval=schema.settings.health_check_interval,
            auto_start_items=schema.settings.auto_start,
        )
        
        production = Production(prod_config)
        
        # Create and register items
        items_by_id: dict[str, Item] = {}
        for item_schema in schema.items:
            if not item_schema.enabled:
                logger.debug("skipping_disabled_item", item_id=item_schema.id)
                continue
            
            item = self._create_item(item_schema)
            if item:
                production.register_item(item)
                items_by_id[item_schema.id] = item
        
        # Create routes from connections and routing rules
        self._create_routes(production, schema, items_by_id)
        
        logger.info(
            "production_created_from_config",
            name=schema.name,
            items=len(items_by_id),
            connections=len(schema.connections),
            routing_rules=len(schema.routing_rules),
        )
        
        return production
    
    def _create_item(self, schema: ItemSchema) -> Item | None:
        """Create an Item instance from a schema."""
        item_class = get_item_class(schema.type)
        
        if not item_class:
            logger.error("unknown_item_type", type=schema.type, item_id=schema.id)
            return None
        
        # Build item config from schema settings
        config_data = {
            "id": schema.id,
            "name": schema.name or schema.id,
            "enabled": schema.enabled,
            **schema.settings,
        }
        
        try:
            # Try to create with the item's specific config class
            if hasattr(item_class, "Config"):
                config = item_class.Config(**config_data)
            else:
                config = ItemConfig(**config_data)
            
            item = item_class(config)
            logger.debug("item_created", item_id=schema.id, type=schema.type)
            return item
        except Exception as e:
            logger.error("failed_to_create_item", item_id=schema.id, error=str(e))
            return None
    
    def _create_routes(
        self,
        production: Production,
        schema: ProductionSchema,
        items: dict[str, Item],
    ) -> None:
        """Create routes from connections and routing rules."""
        # Group connections by source
        connections_by_source: dict[str, list[ConnectionSchema]] = {}
        for conn in schema.connections:
            if conn.source_id not in connections_by_source:
                connections_by_source[conn.source_id] = []
            connections_by_source[conn.source_id].append(conn)
        
        # Create a route for each source item with connections
        for source_id, connections in connections_by_source.items():
            if source_id not in items:
                logger.warning("connection_source_not_found", source_id=source_id)
                continue
            
            # Get routing rules that apply to this source
            applicable_rules = [
                r for r in schema.routing_rules
                if r.source_item_id == source_id or r.source_item_id is None
            ]
            
            # Create route config
            route_config = RouteConfig(
                id=f"route_{source_id}",
                name=f"Route from {source_id}",
                enabled=True,
                source=source_id,
                targets=[c.target_id for c in connections if c.enabled],
            )
            
            route = Route(route_config)
            
            # Add filter logic based on routing rules
            for rule in applicable_rules:
                # Store rule in route for runtime evaluation
                route.add_routing_rule(rule)
            
            production.register_route(route)
            logger.debug(
                "route_created",
                route_id=route_config.id,
                source=source_id,
                targets=route_config.targets,
            )
    
    def export_to_dict(self, production: Production) -> dict[str, Any]:
        """Export a Production to a configuration dictionary."""
        items = []
        for item_id, item in production.items.items():
            item_schema = ItemSchema(
                id=item.id,
                name=item.name,
                type=self._get_item_type_name(item),
                category=self._get_item_category(item),
                enabled=item.config.enabled,
                settings=self._get_item_settings(item),
            )
            items.append(item_schema.model_dump())
        
        connections = []
        for route in production.routes.values():
            for target in route.config.targets:
                conn = ConnectionSchema(
                    id=f"{route.config.source}_to_{target}",
                    source_id=route.config.source,
                    target_id=target,
                    enabled=True,
                )
                connections.append(conn.model_dump())
        
        schema = ProductionSchema(
            name=production.name,
            description=production.config.description,
            enabled=production.config.enabled,
            items=[ItemSchema.model_validate(i) for i in items],
            connections=[ConnectionSchema.model_validate(c) for c in connections],
            routing_rules=[],
        )
        
        return schema.model_dump()
    
    def export_to_json(self, production: Production, indent: int = 2) -> str:
        """Export a Production to a JSON string."""
        data = self.export_to_dict(production)
        return json.dumps(data, indent=indent)
    
    def export_to_file(self, production: Production, path: str | Path) -> None:
        """Export a Production to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            f.write(self.export_to_json(production))
        
        logger.info("production_exported", path=str(path))
    
    def _get_item_type_name(self, item: Item) -> str:
        """Get the type name for an item."""
        for type_name, item_class in _item_registry.items():
            if isinstance(item, item_class):
                return type_name
        return "unknown"
    
    def _get_item_category(self, item: Item) -> ItemCategory:
        """Get the category for an item."""
        type_name = self._get_item_type_name(item)
        if type_name.startswith("receiver"):
            return ItemCategory.SERVICE
        elif type_name.startswith("processor"):
            return ItemCategory.PROCESS
        elif type_name.startswith("sender"):
            return ItemCategory.OPERATION
        return ItemCategory.SERVICE
    
    def _get_item_settings(self, item: Item) -> dict[str, Any]:
        """Extract settings from an item's config."""
        if hasattr(item.config, "model_dump"):
            data = item.config.model_dump()
        else:
            data = vars(item.config).copy()
        
        # Remove standard fields
        for key in ["id", "name", "enabled"]:
            data.pop(key, None)
        
        return data


# Global loader instance
config_loader = ConfigurationLoader()


def load_production_from_json(path: str | Path) -> Production:
    """Convenience function to load a production from a JSON file."""
    schema = config_loader.load_from_file(path)
    return config_loader.create_production(schema)


def load_production_from_dict(data: dict[str, Any]) -> Production:
    """Convenience function to load a production from a dictionary."""
    schema = config_loader.load_from_dict(data)
    return config_loader.create_production(schema)
