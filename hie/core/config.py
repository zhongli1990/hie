"""
HIE Configuration System

Declarative configuration loading from YAML files.
The config file is the source of truth for all production settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from hie.core.item import ItemConfig, ItemType, ExecutionMode
from hie.core.production import ProductionConfig
from hie.core.route import RouteConfig, FilterConfig, FilterOperator


class ReceiverConfig(ItemConfig):
    """Configuration for receiver items."""
    item_type: ItemType = Field(default=ItemType.RECEIVER)


class ProcessorConfig(ItemConfig):
    """Configuration for processor items."""
    item_type: ItemType = Field(default=ItemType.PROCESSOR)


class SenderConfig(ItemConfig):
    """Configuration for sender items."""
    item_type: ItemType = Field(default=ItemType.SENDER)


class HTTPReceiverConfig(ReceiverConfig):
    """Configuration for HTTP receiver."""
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8080, ge=1, le=65535, description="Bind port")
    path: str = Field(default="/", description="URL path to listen on")
    methods: list[str] = Field(default=["POST"], description="Allowed HTTP methods")
    max_body_size: int = Field(default=10 * 1024 * 1024, description="Max request body size")
    content_types: list[str] = Field(
        default=["application/hl7-v2", "x-application/hl7-v2+er7", "text/plain"],
        description="Allowed content types"
    )


class FileReceiverConfig(ReceiverConfig):
    """Configuration for file receiver (directory watcher)."""
    watch_directory: str = Field(description="Directory to watch for files")
    patterns: list[str] = Field(
        default=["*.hl7", "*.txt", "*.csv"],
        description="File patterns to match"
    )
    poll_interval: float = Field(default=1.0, gt=0, description="Seconds between polls")
    move_to: str | None = Field(default=None, description="Move processed files here")
    delete_after: bool = Field(default=False, description="Delete files after processing")
    recursive: bool = Field(default=False, description="Watch subdirectories")


class MLLPSenderConfig(SenderConfig):
    """Configuration for MLLP sender."""
    host: str = Field(description="Target host")
    port: int = Field(ge=1, le=65535, description="Target port")
    timeout: float = Field(default=30.0, gt=0, description="Connection timeout")
    retry_connect: bool = Field(default=True, description="Retry on connection failure")
    max_connections: int = Field(default=5, ge=1, description="Connection pool size")
    keepalive: bool = Field(default=True, description="Use keepalive connections")


class FileSenderConfig(SenderConfig):
    """Configuration for file sender."""
    output_directory: str = Field(description="Directory to write files")
    filename_pattern: str = Field(
        default="{message_id}.hl7",
        description="Filename pattern (supports {message_id}, {timestamp}, {message_type})"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing files")
    create_directory: bool = Field(default=True, description="Create directory if missing")


class TransformProcessorConfig(ProcessorConfig):
    """Configuration for transform processor."""
    script: str | None = Field(default=None, description="Path to transform script")
    transform_class: str | None = Field(default=None, description="Transform class name")
    config: dict[str, Any] = Field(default_factory=dict, description="Transform-specific config")


class HIEConfig(BaseModel):
    """
    Root configuration for an HIE production.
    
    This is the schema for the YAML configuration file.
    """
    model_config = ConfigDict(extra="forbid")
    
    production: ProductionConfig = Field(description="Production settings")
    items: list[dict[str, Any]] = Field(default_factory=list, description="Item configurations")
    routes: list[RouteConfig] = Field(default_factory=list, description="Route configurations")
    
    # Global settings
    logging: dict[str, Any] = Field(
        default_factory=lambda: {
            "level": "INFO",
            "format": "json",
        },
        description="Logging configuration"
    )
    
    persistence: dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "memory",
        },
        description="Persistence configuration"
    )


# Item type registry for dynamic instantiation
ITEM_TYPE_REGISTRY: dict[str, type[ItemConfig]] = {
    "receiver.http": HTTPReceiverConfig,
    "receiver.file": FileReceiverConfig,
    "sender.mllp": MLLPSenderConfig,
    "sender.file": FileSenderConfig,
    "processor.transform": TransformProcessorConfig,
}


def parse_item_config(item_data: dict[str, Any]) -> ItemConfig:
    """
    Parse an item configuration dictionary into the appropriate config type.
    
    Args:
        item_data: Dictionary containing item configuration
        
    Returns:
        Typed ItemConfig instance
    """
    item_type = item_data.get("type", "")
    
    if item_type in ITEM_TYPE_REGISTRY:
        config_class = ITEM_TYPE_REGISTRY[item_type]
        return config_class.model_validate(item_data)
    
    # Fall back to generic config based on type prefix
    if item_type.startswith("receiver."):
        return ReceiverConfig.model_validate(item_data)
    elif item_type.startswith("processor."):
        return ProcessorConfig.model_validate(item_data)
    elif item_type.startswith("sender."):
        return SenderConfig.model_validate(item_data)
    
    # Default to generic ItemConfig
    return ItemConfig.model_validate(item_data)


def load_config(path: str | Path) -> HIEConfig:
    """
    Load HIE configuration from a YAML file.
    
    Args:
        path: Path to the YAML configuration file
        
    Returns:
        Parsed HIEConfig instance
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if data is None:
        raise ValueError(f"Empty configuration file: {path}")
    
    return HIEConfig.model_validate(data)


def load_config_from_string(yaml_content: str) -> HIEConfig:
    """
    Load HIE configuration from a YAML string.
    
    Args:
        yaml_content: YAML configuration as a string
        
    Returns:
        Parsed HIEConfig instance
    """
    data = yaml.safe_load(yaml_content)
    
    if data is None:
        raise ValueError("Empty configuration")
    
    return HIEConfig.model_validate(data)


def save_config(config: HIEConfig, path: str | Path) -> None:
    """
    Save HIE configuration to a YAML file.
    
    Args:
        config: HIEConfig instance to save
        path: Path to write the YAML file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = config.model_dump(mode="json", exclude_none=True)
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def validate_config(config: HIEConfig) -> list[str]:
    """
    Validate an HIE configuration for consistency.
    
    Args:
        config: HIEConfig instance to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []
    
    # Collect item IDs
    item_ids = set()
    for item_data in config.items:
        item_id = item_data.get("id")
        if not item_id:
            errors.append("Item missing 'id' field")
            continue
        if item_id in item_ids:
            errors.append(f"Duplicate item ID: {item_id}")
        item_ids.add(item_id)
    
    # Validate routes reference valid items
    for route in config.routes:
        for item_id in route.path:
            if item_id not in item_ids:
                errors.append(f"Route '{route.id}' references unknown item: {item_id}")
        
        if route.error_handler and route.error_handler not in item_ids:
            errors.append(f"Route '{route.id}' references unknown error handler: {route.error_handler}")
        
        if route.dead_letter and route.dead_letter not in item_ids:
            errors.append(f"Route '{route.id}' references unknown dead letter: {route.dead_letter}")
    
    return errors
