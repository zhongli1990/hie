"""
Transform Processor - Applies transformations to messages.

Supports pluggable transform functions for message modification.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable, Coroutine

import structlog

from hie.core.item import Processor, ItemConfig
from hie.core.message import Message
from hie.core.config import TransformProcessorConfig

logger = structlog.get_logger(__name__)

# Type alias for transform functions
TransformFunc = Callable[[Message, dict[str, Any]], Coroutine[Any, Any, Message | list[Message] | None]]


class Transform:
    """
    Base class for message transforms.
    
    Subclass this to create custom transforms.
    """
    
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
    
    async def transform(self, message: Message) -> Message | list[Message] | None:
        """
        Transform a message.
        
        Args:
            message: Input message
            
        Returns:
            - Transformed message
            - List of messages (fan-out)
            - None to drop the message
        """
        raise NotImplementedError("Subclasses must implement transform()")
    
    async def setup(self) -> None:
        """Called when the processor starts. Override for initialization."""
        pass
    
    async def teardown(self) -> None:
        """Called when the processor stops. Override for cleanup."""
        pass


class TransformProcessor(Processor):
    """
    Processor that applies transforms to messages.
    
    Transforms can be:
    - A Python script with a transform() function
    - A Transform subclass
    - A callable
    
    Features:
    - Dynamic transform loading
    - Transform configuration
    - Error handling with fallback
    """
    
    def __init__(self, config: TransformProcessorConfig) -> None:
        super().__init__(config)
        self._transform_config = config
        self._transform: Transform | None = None
        self._transform_func: TransformFunc | None = None
        self._logger = logger.bind(item_id=self.id)
    
    @property
    def transform_config(self) -> TransformProcessorConfig:
        """Transform-specific configuration."""
        return self._transform_config
    
    async def _on_start(self) -> None:
        """Load and initialize the transform."""
        if self._transform_config.script:
            await self._load_script_transform()
        elif self._transform_config.transform_class:
            await self._load_class_transform()
        else:
            self._logger.warning("no_transform_configured")
        
        if self._transform:
            await self._transform.setup()
        
        self._logger.info("transform_processor_started")
    
    async def _on_stop(self) -> None:
        """Cleanup transform."""
        if self._transform:
            await self._transform.teardown()
        self._logger.info("transform_processor_stopped")
    
    async def _load_script_transform(self) -> None:
        """Load transform from a Python script."""
        script_path = Path(self._transform_config.script)
        
        if not script_path.exists():
            raise FileNotFoundError(f"Transform script not found: {script_path}")
        
        # Load the module
        spec = importlib.util.spec_from_file_location("transform_module", script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load transform script: {script_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for transform function or class
        if hasattr(module, "Transform"):
            # It's a Transform class
            transform_class = getattr(module, "Transform")
            self._transform = transform_class(self._transform_config.config)
        elif hasattr(module, "transform"):
            # It's a transform function
            func = getattr(module, "transform")
            self._transform_func = func
        else:
            raise ImportError(
                f"Transform script must define 'Transform' class or 'transform' function: {script_path}"
            )
        
        self._logger.info("transform_loaded", script=str(script_path))
    
    async def _load_class_transform(self) -> None:
        """Load transform from a class name."""
        class_path = self._transform_config.transform_class
        
        # Parse module.ClassName format
        if "." not in class_path:
            raise ValueError(f"Transform class must be fully qualified: {class_path}")
        
        module_path, class_name = class_path.rsplit(".", 1)
        
        try:
            module = importlib.import_module(module_path)
            transform_class = getattr(module, class_name)
            self._transform = transform_class(self._transform_config.config)
            self._logger.info("transform_loaded", class_name=class_path)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot load transform class '{class_path}': {e}")
    
    async def _process(self, message: Message) -> Message | list[Message] | None:
        """Apply transform to message."""
        try:
            if self._transform:
                result = await self._transform.transform(message)
            elif self._transform_func:
                result = await self._transform_func(message, self._transform_config.config)
            else:
                # No transform configured, pass through
                result = message
            
            self._logger.debug(
                "message_transformed",
                message_id=str(message.id),
                result_type=type(result).__name__ if result else "None"
            )
            
            return result
        
        except Exception as e:
            self._logger.error(
                "transform_failed",
                message_id=str(message.id),
                error=str(e)
            )
            raise
    
    @classmethod
    def from_config(cls, config: dict[str, Any] | TransformProcessorConfig) -> TransformProcessor:
        """Create a TransformProcessor from configuration."""
        if isinstance(config, dict):
            config = TransformProcessorConfig.model_validate(config)
        return cls(config)


class IdentityTransform(Transform):
    """Transform that returns the message unchanged."""
    
    async def transform(self, message: Message) -> Message:
        return message


class DropTransform(Transform):
    """Transform that drops all messages."""
    
    async def transform(self, message: Message) -> None:
        return None


class FilterTransform(Transform):
    """
    Transform that filters messages based on criteria.
    
    Config:
        field: Field to check (dot notation, e.g., "envelope.message_type")
        operator: Comparison operator (eq, ne, contains, starts_with, etc.)
        value: Value to compare against
        drop_on_match: If True, drop matching messages; if False, drop non-matching
    """
    
    async def transform(self, message: Message) -> Message | None:
        field = self.config.get("field", "")
        operator = self.config.get("operator", "eq")
        value = self.config.get("value")
        drop_on_match = self.config.get("drop_on_match", False)
        
        # Get field value
        actual = self._get_field_value(message, field)
        
        # Evaluate condition
        match = self._evaluate(actual, operator, value)
        
        if drop_on_match:
            return None if match else message
        else:
            return message if match else None
    
    def _get_field_value(self, message: Message, field: str) -> Any:
        """Extract field value using dot notation."""
        parts = field.split(".")
        obj: Any = message
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None
        
        return obj
    
    def _evaluate(self, actual: Any, operator: str, value: Any) -> bool:
        """Evaluate comparison."""
        if actual is None:
            return False
        
        match operator:
            case "eq":
                return actual == value
            case "ne":
                return actual != value
            case "contains":
                return value in actual if isinstance(actual, str) else False
            case "starts_with":
                return actual.startswith(value) if isinstance(actual, str) else False
            case "ends_with":
                return actual.endswith(value) if isinstance(actual, str) else False
            case "gt":
                return actual > value
            case "lt":
                return actual < value
            case "in":
                return actual in value
            case _:
                return False
