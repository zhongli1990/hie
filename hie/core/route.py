"""
HIE Route Model

Routes define message flow paths through items. A route is a sequence of
items that messages traverse, with support for:
- Linear paths (A → B → C)
- Error handling (redirect failures)
- Filtering (conditional routing)
- Branching (content-based routing to multiple paths)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from hie.core.item import Item
    from hie.core.message import Message


class RouteState(str, Enum):
    """Route lifecycle state."""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class FilterOperator(str, Enum):
    """Operators for route filters."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # Regex
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    IN = "in"
    NOT_IN = "not_in"


class FilterConfig(BaseModel):
    """Configuration for a route filter."""
    model_config = ConfigDict(frozen=True)
    
    field: str = Field(description="Field to filter on (e.g., 'envelope.message_type')")
    operator: FilterOperator = Field(description="Comparison operator")
    value: Any = Field(description="Value to compare against")
    
    def evaluate(self, message: Message) -> bool:
        """Evaluate the filter against a message."""
        import re
        
        # Get field value from message
        actual = self._get_field_value(message)
        if actual is None:
            return False
        
        # Apply operator
        match self.operator:
            case FilterOperator.EQUALS:
                return actual == self.value
            case FilterOperator.NOT_EQUALS:
                return actual != self.value
            case FilterOperator.CONTAINS:
                return self.value in actual if isinstance(actual, str) else False
            case FilterOperator.STARTS_WITH:
                return actual.startswith(self.value) if isinstance(actual, str) else False
            case FilterOperator.ENDS_WITH:
                return actual.endswith(self.value) if isinstance(actual, str) else False
            case FilterOperator.MATCHES:
                return bool(re.match(self.value, actual)) if isinstance(actual, str) else False
            case FilterOperator.GREATER_THAN:
                return actual > self.value
            case FilterOperator.LESS_THAN:
                return actual < self.value
            case FilterOperator.IN:
                return actual in self.value
            case FilterOperator.NOT_IN:
                return actual not in self.value
            case _:
                return False
    
    def _get_field_value(self, message: Message) -> Any:
        """Extract field value from message using dot notation."""
        parts = self.field.split(".")
        obj: Any = message
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        
        return obj


class RouteConfig(BaseModel):
    """Configuration for a route."""
    model_config = ConfigDict(extra="allow")
    
    id: str = Field(description="Unique route identifier")
    name: str = Field(default="", description="Human-readable name")
    enabled: bool = Field(default=True, description="Whether route is enabled")
    
    # Path configuration
    path: list[str] = Field(
        description="Ordered list of item IDs in the route"
    )
    
    # Error handling
    error_handler: str | None = Field(
        default=None,
        description="Item ID to handle failed messages"
    )
    dead_letter: str | None = Field(
        default=None,
        description="Item ID for messages that exceed retries"
    )
    
    # Filtering
    filters: list[FilterConfig] = Field(
        default_factory=list,
        description="Filters to apply before routing"
    )
    filter_mode: str = Field(
        default="all",
        description="'all' = AND, 'any' = OR for multiple filters"
    )
    
    # Ordering
    ordered: bool = Field(
        default=False,
        description="Maintain message order (reduces throughput)"
    )
    
    # Timeout
    timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        description="Total route timeout"
    )


@dataclass
class RouteMetrics:
    """Runtime metrics for a route."""
    messages_entered: int = 0
    messages_completed: int = 0
    messages_failed: int = 0
    messages_filtered: int = 0
    messages_dead_lettered: int = 0
    messages_in_flight: int = 0
    
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    last_message_at: datetime | None = None
    last_error_at: datetime | None = None
    
    def record_entered(self) -> None:
        """Record a message entering the route."""
        self.messages_entered += 1
        self.messages_in_flight += 1
        self.last_message_at = datetime.now(timezone.utc)
    
    def record_completed(self, latency_ms: float) -> None:
        """Record a message completing the route."""
        self.messages_completed += 1
        self.messages_in_flight -= 1
        
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.messages_completed
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
    
    def record_failed(self) -> None:
        """Record a message failing in the route."""
        self.messages_failed += 1
        self.messages_in_flight -= 1
        self.last_error_at = datetime.now(timezone.utc)
    
    def record_filtered(self) -> None:
        """Record a message being filtered out."""
        self.messages_filtered += 1
    
    def record_dead_lettered(self) -> None:
        """Record a message being dead-lettered."""
        self.messages_dead_lettered += 1
        self.messages_in_flight -= 1


@dataclass
class RouteContext:
    """Context passed through a route with a message."""
    route_id: str
    entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_hop: int = 0
    total_hops: int = 0
    errors: list[str] = field(default_factory=list)
    
    @property
    def latency_ms(self) -> float:
        """Calculate current latency in milliseconds."""
        delta = datetime.now(timezone.utc) - self.entered_at
        return delta.total_seconds() * 1000


class Route:
    """
    A message flow path through items.
    
    Routes connect items in sequence and manage message flow,
    including error handling, filtering, and metrics.
    """
    
    def __init__(self, config: RouteConfig) -> None:
        self._config = config
        self._state = RouteState.CREATED
        self._metrics = RouteMetrics()
        self._items: list[Item] = []
        self._error_handler: Item | None = None
        self._dead_letter: Item | None = None
        self._lock = asyncio.Lock()
    
    @property
    def id(self) -> str:
        """Unique route identifier."""
        return self._config.id
    
    @property
    def name(self) -> str:
        """Human-readable name."""
        return self._config.name or self._config.id
    
    @property
    def state(self) -> RouteState:
        """Current lifecycle state."""
        return self._state
    
    @property
    def config(self) -> RouteConfig:
        """Route configuration."""
        return self._config
    
    @property
    def metrics(self) -> RouteMetrics:
        """Runtime metrics."""
        return self._metrics
    
    @property
    def is_running(self) -> bool:
        """Check if route is running."""
        return self._state == RouteState.RUNNING
    
    def bind_items(
        self,
        items: dict[str, Item],
        error_handler: Item | None = None,
        dead_letter: Item | None = None,
    ) -> None:
        """
        Bind item instances to the route.
        
        Args:
            items: Dictionary of item_id -> Item instances
            error_handler: Optional error handler item
            dead_letter: Optional dead letter item
        """
        self._items = []
        for item_id in self._config.path:
            if item_id not in items:
                raise ValueError(f"Item not found: {item_id}")
            self._items.append(items[item_id])
        
        self._error_handler = error_handler
        self._dead_letter = dead_letter
        
        # Wire up items in sequence
        for i, item in enumerate(self._items[:-1]):
            next_item = self._items[i + 1]
            item.set_message_handler(self._create_forward_handler(next_item, i + 1))
            item.set_error_handler(self._create_error_handler())
        
        # Last item completes the route
        if self._items:
            self._items[-1].set_message_handler(self._create_completion_handler())
            self._items[-1].set_error_handler(self._create_error_handler())
    
    def _create_forward_handler(
        self, next_item: Item, hop: int
    ) -> Callable[[Message], Coroutine[Any, Any, Message | None]]:
        """Create a handler that forwards messages to the next item."""
        async def handler(message: Message) -> Message | None:
            # Update routing info
            updated = message.with_envelope(
                routing=message.envelope.routing.increment_hop()
            )
            await next_item.submit(updated)
            return None
        return handler
    
    def _create_completion_handler(
        self,
    ) -> Callable[[Message], Coroutine[Any, Any, Message | None]]:
        """Create a handler for route completion."""
        async def handler(message: Message) -> Message | None:
            # Calculate latency from message creation
            latency_ms = (
                datetime.now(timezone.utc) - message.envelope.created_at
            ).total_seconds() * 1000
            self._metrics.record_completed(latency_ms)
            return message
        return handler
    
    def _create_error_handler(
        self,
    ) -> Callable[[Exception, Message | None], Coroutine[Any, Any, None]]:
        """Create an error handler for the route."""
        async def handler(error: Exception, message: Message | None) -> None:
            self._metrics.record_failed()
            
            if message is None:
                return
            
            # Check if we can retry
            if message.envelope.can_retry():
                # Increment retry and resubmit to first item
                updated = message.with_envelope(
                    retry_count=message.envelope.retry_count + 1
                )
                if self._error_handler:
                    await self._error_handler.submit(updated)
                elif self._items:
                    await self._items[0].submit(updated)
            else:
                # Dead letter
                self._metrics.record_dead_lettered()
                if self._dead_letter:
                    await self._dead_letter.submit(message)
        
        return handler
    
    def accepts(self, message: Message) -> bool:
        """Check if this route accepts the message based on filters."""
        if not self._config.filters:
            return True
        
        if self._config.filter_mode == "all":
            return all(f.evaluate(message) for f in self._config.filters)
        else:  # "any"
            return any(f.evaluate(message) for f in self._config.filters)
    
    async def submit(self, message: Message) -> bool:
        """
        Submit a message to the route.
        
        Returns True if accepted, False if filtered out.
        """
        if self._state != RouteState.RUNNING:
            raise RuntimeError(f"Cannot submit to route in state: {self._state}")
        
        # Check filters
        if not self.accepts(message):
            self._metrics.record_filtered()
            return False
        
        # Update message with route info
        from hie.core.message import RoutingInfo
        updated = message.with_envelope(
            routing=RoutingInfo(
                source=message.envelope.routing.source,
                destination=message.envelope.routing.destination,
                route_id=self.id,
                hop_count=message.envelope.routing.hop_count,
            )
        )
        
        self._metrics.record_entered()
        
        # Submit to first item
        if self._items:
            if self._config.ordered:
                async with self._lock:
                    await self._items[0].submit(updated)
            else:
                await self._items[0].submit(updated)
        
        return True
    
    async def start(self) -> None:
        """Start the route (items must be started separately)."""
        if self._state not in (RouteState.CREATED, RouteState.STOPPED):
            raise RuntimeError(f"Cannot start route in state: {self._state}")
        
        self._state = RouteState.STARTING
        
        # Verify all items are bound
        if not self._items:
            raise RuntimeError("No items bound to route")
        
        self._state = RouteState.RUNNING
    
    async def stop(self) -> None:
        """Stop the route."""
        if self._state not in (RouteState.RUNNING, RouteState.PAUSED):
            return
        
        self._state = RouteState.STOPPING
        self._state = RouteState.STOPPED
    
    async def pause(self) -> None:
        """Pause the route."""
        if self._state != RouteState.RUNNING:
            raise RuntimeError(f"Cannot pause route in state: {self._state}")
        self._state = RouteState.PAUSED
    
    async def resume(self) -> None:
        """Resume the route."""
        if self._state != RouteState.PAUSED:
            raise RuntimeError(f"Cannot resume route in state: {self._state}")
        self._state = RouteState.RUNNING
    
    def health_check(self) -> dict[str, Any]:
        """Return health status."""
        return {
            "id": self.id,
            "name": self.name,
            "state": self._state.value,
            "path": self._config.path,
            "metrics": {
                "messages_entered": self._metrics.messages_entered,
                "messages_completed": self._metrics.messages_completed,
                "messages_failed": self._metrics.messages_failed,
                "messages_filtered": self._metrics.messages_filtered,
                "messages_in_flight": self._metrics.messages_in_flight,
                "avg_latency_ms": round(self._metrics.avg_latency_ms, 2),
            },
        }
    
    def __repr__(self) -> str:
        return f"Route(id={self.id!r}, path={self._config.path}, state={self._state.value})"
