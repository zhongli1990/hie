"""
HIE Factory - Creates production instances from configuration.

Handles dynamic instantiation of items, routes, and productions.
"""

from __future__ import annotations

from typing import Any

import structlog

from Engine.core.config import (
    HIEConfig,
    HTTPReceiverConfig,
    FileReceiverConfig,
    MLLPSenderConfig,
    FileSenderConfig,
    TransformProcessorConfig,
)
from Engine.core.item import Item, ItemConfig, ItemType
from Engine.core.production import Production, ProductionConfig
from Engine.core.route import Route, RouteConfig
from Engine.items.receivers import HTTPReceiver, FileReceiver
from Engine.items.senders import MLLPSender, FileSender
from Engine.items.processors import PassthroughProcessor, TransformProcessor

logger = structlog.get_logger(__name__)

# Registry of item types to their factory functions
ITEM_FACTORIES: dict[str, type] = {
    "receiver.http": HTTPReceiver,
    "receiver.file": FileReceiver,
    "sender.mllp": MLLPSender,
    "sender.file": FileSender,
    "processor.transform": TransformProcessor,
    "processor.passthrough": PassthroughProcessor,
}

# Registry of item types to their config classes
ITEM_CONFIGS: dict[str, type] = {
    "receiver.http": HTTPReceiverConfig,
    "receiver.file": FileReceiverConfig,
    "sender.mllp": MLLPSenderConfig,
    "sender.file": FileSenderConfig,
    "processor.transform": TransformProcessorConfig,
}


def create_item(item_data: dict[str, Any]) -> Item:
    """
    Create an item instance from configuration data.
    
    Args:
        item_data: Dictionary containing item configuration
        
    Returns:
        Configured Item instance
    """
    item_type_str = item_data.get("type", "")
    
    if item_type_str not in ITEM_FACTORIES:
        raise ValueError(f"Unknown item type: {item_type_str}")
    
    # Derive item_type (category) from the type string
    # e.g., "receiver.http" -> ItemType.RECEIVER
    if item_type_str.startswith("receiver."):
        item_category = ItemType.RECEIVER
    elif item_type_str.startswith("processor."):
        item_category = ItemType.PROCESSOR
    elif item_type_str.startswith("sender."):
        item_category = ItemType.SENDER
    else:
        item_category = ItemType.PROCESSOR  # Default
    
    # Add item_type to the data if not present
    config_data = item_data.copy()
    if "item_type" not in config_data:
        config_data["item_type"] = item_category.value
    
    # Get the appropriate config class
    config_class = ITEM_CONFIGS.get(item_type_str, ItemConfig)
    
    # Parse configuration
    config = config_class.model_validate(config_data)
    
    # Create item instance
    factory = ITEM_FACTORIES[item_type_str]
    
    if hasattr(factory, "from_config"):
        return factory.from_config(config)
    else:
        return factory(config)


def create_route(route_config: RouteConfig) -> Route:
    """
    Create a route instance from configuration.
    
    Args:
        route_config: Route configuration
        
    Returns:
        Configured Route instance
    """
    return Route(route_config)


def create_production_from_config(config: HIEConfig) -> Production:
    """
    Create a complete production from HIE configuration.
    
    Args:
        config: HIE configuration
        
    Returns:
        Configured Production instance with all items and routes
    """
    # Create production
    production = Production(config.production)
    
    # Create and register items
    for item_data in config.items:
        if not item_data.get("enabled", True):
            logger.info("skipping_disabled_item", item_id=item_data.get("id"))
            continue
        
        try:
            item = create_item(item_data)
            production.register_item(item)
            logger.debug("item_created", item_id=item.id, item_type=item_data.get("type"))
        except Exception as e:
            logger.error(
                "item_creation_failed",
                item_id=item_data.get("id"),
                error=str(e)
            )
            raise
    
    # Create and register routes
    for route_config in config.routes:
        if not route_config.enabled:
            logger.info("skipping_disabled_route", route_id=route_config.id)
            continue
        
        try:
            route = create_route(route_config)
            production.register_route(route)
            logger.debug("route_created", route_id=route.id, path=route_config.path)
        except Exception as e:
            logger.error(
                "route_creation_failed",
                route_id=route_config.id,
                error=str(e)
            )
            raise
    
    return production


def register_item_type(
    type_name: str,
    factory: type,
    config_class: type | None = None,
) -> None:
    """
    Register a custom item type.
    
    Args:
        type_name: Type identifier (e.g., "receiver.custom")
        factory: Item class or factory function
        config_class: Optional config class for the item
    """
    ITEM_FACTORIES[type_name] = factory
    if config_class:
        ITEM_CONFIGS[type_name] = config_class
    
    logger.info("item_type_registered", type_name=type_name)
