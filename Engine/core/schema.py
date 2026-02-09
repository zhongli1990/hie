"""
HIE Configuration Schema

Defines the JSON schema for production configuration, enabling:
- Visual editor compatibility
- Flexible routing (not just linear paths)
- Dynamic item/route creation via API
- Import/export with IRIS compatibility
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator


# =============================================================================
# Enums
# =============================================================================

class ItemCategory(str, Enum):
    """Category of business host."""
    SERVICE = "service"      # Inbound (receivers)
    PROCESS = "process"      # Processing (transformers, routers)
    OPERATION = "operation"  # Outbound (senders)


class ConnectionType(str, Enum):
    """Type of connection between items."""
    STANDARD = "standard"    # Normal message flow
    ERROR = "error"          # Error handling path
    ASYNC = "async"          # Asynchronous/fire-and-forget


class FilterOperator(str, Enum):
    """Operators for routing filters."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"      # Regex
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class ConditionLogic(str, Enum):
    """Logic for combining multiple conditions."""
    AND = "and"
    OR = "or"


# =============================================================================
# Settings Schemas
# =============================================================================

class BaseSettings(BaseModel):
    """Base settings for all items."""
    model_config = ConfigDict(extra="allow")
    
    pool_size: int = Field(default=1, ge=1, description="Number of worker instances")
    queue_size: int = Field(default=1000, ge=1, description="Maximum pending messages")
    timeout_seconds: float = Field(default=30.0, gt=0, description="Processing timeout")
    retry_count: int = Field(default=3, ge=0, description="Max retry attempts")
    retry_interval: float = Field(default=5.0, ge=0, description="Seconds between retries")
    inactivity_timeout: int = Field(default=0, ge=0, description="Seconds before idle shutdown (0=never)")


class HTTPReceiverSettings(BaseSettings):
    """Settings for HTTP receiver."""
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8080, ge=1, le=65535, description="Bind port")
    path: str = Field(default="/", description="URL path")
    methods: list[str] = Field(default=["POST"], description="Allowed HTTP methods")
    content_types: list[str] = Field(
        default=["application/hl7-v2", "text/plain"],
        description="Allowed content types"
    )
    max_body_size: int = Field(default=10485760, description="Max request body (bytes)")
    ssl_enabled: bool = Field(default=False, description="Enable HTTPS")
    ssl_cert: str | None = Field(default=None, description="SSL certificate path")
    ssl_key: str | None = Field(default=None, description="SSL key path")


class FileReceiverSettings(BaseSettings):
    """Settings for file receiver."""
    directory: str = Field(description="Directory to watch")
    patterns: list[str] = Field(default=["*"], description="File patterns to match")
    poll_interval: float = Field(default=1.0, gt=0, description="Poll interval (seconds)")
    recursive: bool = Field(default=False, description="Watch subdirectories")
    move_to: str | None = Field(default=None, description="Move processed files here")
    delete_after: bool = Field(default=False, description="Delete after processing")
    archive_days: int = Field(default=0, ge=0, description="Days to keep in archive (0=forever)")


class MLLPReceiverSettings(BaseSettings):
    """Settings for MLLP receiver."""
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(ge=1, le=65535, description="Bind port")
    ack_mode: str = Field(default="auto", description="ACK mode: auto, manual, none")
    ssl_enabled: bool = Field(default=False, description="Enable TLS")


class MLLPSenderSettings(BaseSettings):
    """Settings for MLLP sender."""
    host: str = Field(description="Target host")
    port: int = Field(ge=1, le=65535, description="Target port")
    connection_timeout: float = Field(default=30.0, gt=0, description="Connection timeout")
    max_connections: int = Field(default=5, ge=1, description="Connection pool size")
    keepalive: bool = Field(default=True, description="Use keepalive")
    ssl_enabled: bool = Field(default=False, description="Enable TLS")
    ack_timeout: float = Field(default=30.0, gt=0, description="ACK wait timeout")


class FileSenderSettings(BaseSettings):
    """Settings for file sender."""
    directory: str = Field(description="Output directory")
    filename_pattern: str = Field(
        default="{message_id}.dat",
        description="Filename pattern"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing files")
    create_directory: bool = Field(default=True, description="Create directory if missing")
    temp_extension: str = Field(default=".tmp", description="Temp file extension during write")


class HTTPSenderSettings(BaseSettings):
    """Settings for HTTP sender."""
    url: str = Field(description="Target URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    timeout: float = Field(default=30.0, gt=0, description="Request timeout")
    retry_on_status: list[int] = Field(default=[500, 502, 503, 504], description="Retry on these status codes")
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")


class RouterSettings(BaseSettings):
    """Settings for message router."""
    default_target: str | None = Field(default=None, description="Default target if no rules match")
    stop_on_match: bool = Field(default=True, description="Stop after first matching rule")


class TransformSettings(BaseSettings):
    """Settings for transform processor."""
    script_path: str | None = Field(default=None, description="Path to transform script")
    transform_class: str | None = Field(default=None, description="Transform class name")
    config: dict[str, Any] = Field(default_factory=dict, description="Transform-specific config")


# =============================================================================
# Filter & Routing Schemas
# =============================================================================

class FilterCondition(BaseModel):
    """A single filter condition."""
    model_config = ConfigDict(frozen=True)
    
    field: str = Field(description="Field path (dot notation, e.g., 'envelope.message_type')")
    operator: FilterOperator = Field(description="Comparison operator")
    value: Any = Field(description="Value to compare against")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }


class FilterGroup(BaseModel):
    """A group of filter conditions with logic."""
    model_config = ConfigDict(frozen=True)
    
    logic: ConditionLogic = Field(default=ConditionLogic.AND, description="How to combine conditions")
    conditions: list[FilterCondition | FilterGroup] = Field(
        default_factory=list,
        description="Conditions or nested groups"
    )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "logic": self.logic.value,
            "conditions": [
                c.to_dict() if hasattr(c, "to_dict") else c.model_dump()
                for c in self.conditions
            ],
        }


class RoutingRule(BaseModel):
    """A routing rule that directs messages to targets based on conditions."""
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4())[:8], description="Rule identifier")
    name: str = Field(default="", description="Human-readable name")
    enabled: bool = Field(default=True, description="Whether rule is active")
    priority: int = Field(default=0, description="Rule priority (higher = evaluated first)")
    filter: FilterGroup | None = Field(default=None, description="Filter conditions")
    targets: list[str] = Field(description="Target item IDs when rule matches")
    transform: str | None = Field(default=None, description="Optional transform to apply")
    stop_processing: bool = Field(default=True, description="Stop evaluating rules after match")


# =============================================================================
# Item Schema
# =============================================================================

class ItemSchema(BaseModel):
    """
    Schema for a business host (item) in the production.
    
    Equivalent to IRIS <Item> element in ProductionDefinition.
    """
    model_config = ConfigDict(extra="allow")
    
    # Identity
    id: str = Field(description="Unique item identifier within production")
    name: str = Field(default="", description="Human-readable display name")
    
    # Classification
    type: str = Field(description="Item type (e.g., 'receiver.http', 'sender.mllp')")
    category: ItemCategory = Field(description="Item category")
    class_name: str | None = Field(default=None, alias="className", description="Custom class name")
    
    # State
    enabled: bool = Field(default=True, description="Whether item is enabled")
    
    # Organization
    display_category: str = Field(default="", alias="displayCategory", description="UI grouping category")
    comment: str = Field(default="", description="Description/notes")
    
    # Settings
    settings: dict[str, Any] = Field(default_factory=dict, description="Item-specific settings")
    
    # Visual position (for editor)
    position: dict[str, float] | None = Field(
        default=None,
        description="Visual position {x, y} in editor"
    )
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("Item ID must be at least 1 character")
        invalid_chars = set('|;,:[<>\\/&"')
        if any(c in v for c in invalid_chars):
            raise ValueError(f"Item ID contains invalid characters: {invalid_chars}")
        return v


# =============================================================================
# Connection Schema
# =============================================================================

class ConnectionSchema(BaseModel):
    """
    Schema for a connection between items.
    
    Connections define message flow paths, replacing the simple linear 'path' array.
    This enables visual editing and complex routing topologies.
    """
    model_config = ConfigDict(extra="forbid")
    
    id: str = Field(default_factory=lambda: str(uuid4())[:8], description="Connection identifier")
    
    # Endpoints
    source: str = Field(description="Source item ID")
    target: str = Field(description="Target item ID")
    
    # Type
    connection_type: ConnectionType = Field(
        default=ConnectionType.STANDARD,
        alias="type",
        description="Connection type"
    )
    
    # Filtering
    filter: FilterGroup | None = Field(default=None, description="Optional filter for this connection")
    
    # Metadata
    enabled: bool = Field(default=True, description="Whether connection is active")
    comment: str = Field(default="", description="Description/notes")
    
    # Visual (for editor)
    waypoints: list[dict[str, float]] | None = Field(
        default=None,
        description="Visual waypoints [{x, y}, ...] for curved lines"
    )


# =============================================================================
# Production Schema
# =============================================================================

class ProductionSettings(BaseModel):
    """Production-level settings."""
    model_config = ConfigDict(extra="allow")
    
    actor_pool_size: int = Field(default=2, ge=1, alias="actorPoolSize", description="Global actor pool size")
    graceful_shutdown_timeout: float = Field(default=30.0, gt=0, description="Shutdown timeout (seconds)")
    health_check_interval: float = Field(default=10.0, gt=0, description="Health check interval (seconds)")
    auto_start: bool = Field(default=True, description="Start production automatically")
    testing_enabled: bool = Field(default=False, description="Enable testing mode")


class ProductionSchema(BaseModel):
    """
    Complete production configuration schema.
    
    This is the root schema for JSON configuration files, equivalent to
    IRIS XData ProductionDefinition but in JSON format.
    """
    model_config = ConfigDict(extra="forbid")
    
    # Schema version
    schema_version: str = Field(default="1.0", alias="$schema", description="Schema version")
    
    # Production identity
    name: str = Field(description="Production name")
    description: str = Field(default="", description="Production description")
    
    # State
    enabled: bool = Field(default=True, description="Whether production is enabled")
    
    # Settings
    settings: ProductionSettings = Field(
        default_factory=ProductionSettings,
        description="Production-level settings"
    )
    
    # Items (business hosts)
    items: list[ItemSchema] = Field(default_factory=list, description="Business hosts")
    
    # Connections (message flow)
    connections: list[ConnectionSchema] = Field(
        default_factory=list,
        description="Connections between items"
    )
    
    # Routing rules (optional, for complex routing)
    routing_rules: list[RoutingRule] = Field(
        default_factory=list,
        alias="routingRules",
        description="Global routing rules"
    )
    
    # Metadata
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    created_by: str | None = Field(default=None, alias="createdBy")
    version: int = Field(default=1, description="Configuration version")
    
    def get_item(self, item_id: str) -> ItemSchema | None:
        """Get an item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def get_connections_from(self, item_id: str) -> list[ConnectionSchema]:
        """Get all connections originating from an item."""
        return [c for c in self.connections if c.source == item_id and c.enabled]
    
    def get_connections_to(self, item_id: str) -> list[ConnectionSchema]:
        """Get all connections targeting an item."""
        return [c for c in self.connections if c.target == item_id and c.enabled]
    
    def get_items_by_category(self, category: ItemCategory) -> list[ItemSchema]:
        """Get all items in a category."""
        return [i for i in self.items if i.category == category]
    
    def validate_connections(self) -> list[str]:
        """Validate all connections reference valid items."""
        errors = []
        item_ids = {i.id for i in self.items}
        
        for conn in self.connections:
            if conn.source not in item_ids:
                errors.append(f"Connection {conn.id}: source '{conn.source}' not found")
            if conn.target not in item_ids:
                errors.append(f"Connection {conn.id}: target '{conn.target}' not found")
        
        return errors
    
    def to_mermaid(self) -> str:
        """Generate Mermaid diagram of the production."""
        lines = ["graph LR"]
        
        # Add items
        for item in self.items:
            shape = {
                ItemCategory.SERVICE: f"[/{item.name or item.id}/]",
                ItemCategory.PROCESS: f"[{item.name or item.id}]",
                ItemCategory.OPERATION: f"[\\{item.name or item.id}\\]",
            }.get(item.category, f"[{item.name or item.id}]")
            lines.append(f"    {item.id}{shape}")
        
        # Add connections
        for conn in self.connections:
            arrow = {
                ConnectionType.STANDARD: "-->",
                ConnectionType.ERROR: "-.->",
                ConnectionType.ASYNC: "==>",
            }.get(conn.connection_type, "-->")
            lines.append(f"    {conn.source} {arrow} {conn.target}")
        
        return "\n".join(lines)


# =============================================================================
# Item Type Registry
# =============================================================================

ITEM_TYPE_SETTINGS: dict[str, type[BaseSettings]] = {
    "receiver.http": HTTPReceiverSettings,
    "receiver.file": FileReceiverSettings,
    "receiver.mllp": MLLPReceiverSettings,
    "sender.mllp": MLLPSenderSettings,
    "sender.file": FileSenderSettings,
    "sender.http": HTTPSenderSettings,
    "processor.router": RouterSettings,
    "processor.transform": TransformSettings,
    "processor.passthrough": BaseSettings,
}

ITEM_TYPE_CATEGORIES: dict[str, ItemCategory] = {
    "receiver.http": ItemCategory.SERVICE,
    "receiver.file": ItemCategory.SERVICE,
    "receiver.mllp": ItemCategory.SERVICE,
    "sender.mllp": ItemCategory.OPERATION,
    "sender.file": ItemCategory.OPERATION,
    "sender.http": ItemCategory.OPERATION,
    "processor.router": ItemCategory.PROCESS,
    "processor.transform": ItemCategory.PROCESS,
    "processor.passthrough": ItemCategory.PROCESS,
}


def get_settings_schema(item_type: str) -> type[BaseSettings]:
    """Get the settings schema for an item type."""
    return ITEM_TYPE_SETTINGS.get(item_type, BaseSettings)


def get_item_category(item_type: str) -> ItemCategory:
    """Get the category for an item type."""
    if item_type in ITEM_TYPE_CATEGORIES:
        return ITEM_TYPE_CATEGORIES[item_type]
    
    # Infer from type prefix
    if item_type.startswith("receiver."):
        return ItemCategory.SERVICE
    elif item_type.startswith("sender."):
        return ItemCategory.OPERATION
    else:
        return ItemCategory.PROCESS
