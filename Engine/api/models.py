"""
HIE API Models

Pydantic models for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# Enums

class ItemType(str, Enum):
    SERVICE = "service"
    PROCESS = "process"
    OPERATION = "operation"


class ConnectionType(str, Enum):
    STANDARD = "standard"
    ERROR = "error"
    ASYNC = "async"


class ProjectState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class RuleAction(str, Enum):
    SEND = "send"
    TRANSFORM = "transform"
    STOP = "stop"
    DELETE = "delete"


# Base Models

class Position(BaseModel):
    x: int = 0
    y: int = 0


class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Workspace Models

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-z][a-z0-9_-]*$')
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)


class WorkspaceUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class WorkspaceResponse(TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    tenant_id: Optional[UUID] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    projects_count: int = 0


class WorkspaceListResponse(BaseModel):
    workspaces: list[WorkspaceResponse]
    total: int


# Project Models

class ProjectSettings(BaseModel):
    actor_pool_size: int = Field(default=2, ge=1, le=100)
    graceful_shutdown_timeout: int = Field(default=30, ge=5, le=300)
    health_check_interval: int = Field(default=10, ge=1, le=60)
    auto_start: bool = False
    testing_enabled: bool = False


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z][a-zA-Z0-9._-]*$')
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = True
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    settings: Optional[ProjectSettings] = None


class ProjectResponse(TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    workspace_id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    enabled: bool = True
    state: ProjectState = ProjectState.STOPPED
    version: int = 1
    settings: dict[str, Any] = Field(default_factory=dict)
    items_count: int = 0
    connections_count: int = 0


class ProjectDetailResponse(ProjectResponse):
    items: list["ItemResponse"] = Field(default_factory=list)
    connections: list["ConnectionResponse"] = Field(default_factory=list)
    routing_rules: list["RoutingRuleResponse"] = Field(default_factory=list)


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# Item Models

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z][a-zA-Z0-9._-]*$')
    display_name: Optional[str] = Field(None, max_length=255)
    item_type: ItemType
    class_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=255)
    enabled: bool = True
    pool_size: int = Field(default=1, ge=1, le=100)
    position: Position = Field(default_factory=Position)
    adapter_settings: dict[str, Any] = Field(default_factory=dict)
    host_settings: dict[str, Any] = Field(default_factory=dict)
    comment: Optional[str] = None


class ItemUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    pool_size: Optional[int] = Field(None, ge=1, le=100)
    position: Optional[Position] = None
    adapter_settings: Optional[dict[str, Any]] = None
    host_settings: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class ItemResponse(TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    name: str
    display_name: Optional[str] = None
    item_type: ItemType
    class_name: str
    category: Optional[str] = None
    enabled: bool = True
    pool_size: int = 1
    position_x: int = 0
    position_y: int = 0
    adapter_settings: dict[str, Any] = Field(default_factory=dict)
    host_settings: dict[str, Any] = Field(default_factory=dict)
    comment: Optional[str] = None
    # Runtime state (populated when engine is running)
    state: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int


# Connection Models

class ConnectionCreate(BaseModel):
    source_item_id: UUID
    target_item_id: UUID
    connection_type: ConnectionType = ConnectionType.STANDARD
    enabled: bool = True
    filter_expression: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class ConnectionUpdate(BaseModel):
    connection_type: Optional[ConnectionType] = None
    enabled: Optional[bool] = None
    filter_expression: Optional[dict[str, Any]] = None
    comment: Optional[str] = None


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    source_item_id: UUID
    target_item_id: UUID
    connection_type: ConnectionType = ConnectionType.STANDARD
    enabled: bool = True
    filter_expression: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionResponse]
    total: int


# Routing Rule Models

class RoutingRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=1000)
    condition_expression: Optional[str] = None
    action: RuleAction = RuleAction.SEND
    target_items: list[UUID] = Field(default_factory=list)
    transform_name: Optional[str] = None


class RoutingRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    condition_expression: Optional[str] = None
    action: Optional[RuleAction] = None
    target_items: Optional[list[UUID]] = None
    transform_name: Optional[str] = None


class RoutingRuleResponse(TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    name: str
    enabled: bool = True
    priority: int = 0
    condition_expression: Optional[str] = None
    action: RuleAction = RuleAction.SEND
    target_items: list[UUID] = Field(default_factory=list)
    transform_name: Optional[str] = None


# Engine/Runtime Models

class DeployRequest(BaseModel):
    start_after_deploy: bool = True


class DeployResponse(BaseModel):
    status: str
    engine_id: str
    state: ProjectState
    items_started: int = 0
    warnings: list[str] = Field(default_factory=list)


class ProjectStatusResponse(BaseModel):
    project_id: UUID
    state: ProjectState
    engine_id: Optional[str] = None
    started_at: Optional[datetime] = None
    uptime_seconds: int = 0
    items: list[ItemResponse] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


# Import Models

class ImportIRISRequest(BaseModel):
    create_new_project: bool = True
    project_name: Optional[str] = None
    overwrite_existing: bool = False


class ImportIRISResponse(BaseModel):
    status: str
    project_id: UUID
    project_name: str
    items_imported: int
    connections_imported: int
    warnings: list[str] = Field(default_factory=list)


# Item Type Registry Models

class SettingDefinition(BaseModel):
    key: str
    label: str
    type: str  # string, number, boolean, select, multiselect, textarea
    required: bool = False
    default: Optional[Any] = None
    options: Optional[list[dict[str, str]]] = None
    description: Optional[str] = None
    validation: Optional[dict[str, Any]] = None


class ItemTypeDefinition(BaseModel):
    type: str
    name: str
    description: str
    category: ItemType
    iris_class_name: str
    li_class_name: str
    adapter_settings: list[SettingDefinition] = Field(default_factory=list)
    host_settings: list[SettingDefinition] = Field(default_factory=list)


class ItemTypeRegistryResponse(BaseModel):
    item_types: list[ItemTypeDefinition]


# Update forward references
ProjectDetailResponse.model_rebuild()
