"""
LI Schema Base Classes

Defines the base classes for schema-driven lazy parsing:
- Schema: Base class for message schemas
- ParsedView: Lazy parsed view of a message
- ValidationError: Schema validation error
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationError:
    """A schema validation error."""
    path: str
    message: str
    severity: str = "error"  # "error", "warning", "info"
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


class Schema(ABC):
    """
    Base class for message schemas.
    
    A Schema defines the structure of a message and provides:
    - Lazy parsing: Parse only when fields are accessed
    - Validation: Check message structure against schema
    - Field access: Get/set fields by path
    - ACK generation: Create acknowledgment messages
    
    Schemas support inheritance via base_schema attribute.
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0",
        base_schema: str | None = None,
    ):
        """
        Initialize a schema.
        
        Args:
            name: Schema name (e.g., "PKB", "2.4")
            version: Schema version
            base_schema: Name of parent schema for inheritance
        """
        self._name = name
        self._version = version
        self._base_schema = base_schema
        self._log = logger.bind(schema=name)
    
    @property
    def name(self) -> str:
        """Schema name."""
        return self._name
    
    @property
    def version(self) -> str:
        """Schema version."""
        return self._version
    
    @property
    def base_schema(self) -> str | None:
        """Parent schema name for inheritance."""
        return self._base_schema
    
    @abstractmethod
    def parse(self, raw: bytes) -> ParsedView:
        """
        Parse raw message bytes into a ParsedView.
        
        The parsing is lazy - only structure is parsed initially,
        field values are extracted on demand.
        
        Args:
            raw: Raw message bytes
            
        Returns:
            ParsedView for accessing message fields
        """
        ...
    
    @abstractmethod
    def validate(self, raw: bytes) -> list[ValidationError]:
        """
        Validate raw message against schema.
        
        Args:
            raw: Raw message bytes
            
        Returns:
            List of validation errors (empty if valid)
        """
        ...
    
    def is_valid(self, raw: bytes) -> bool:
        """
        Check if raw message is valid.
        
        Args:
            raw: Raw message bytes
            
        Returns:
            True if valid, False otherwise
        """
        errors = self.validate(raw)
        return len([e for e in errors if e.severity == "error"]) == 0


class ParsedView(ABC):
    """
    Lazy parsed view of a message.
    
    A ParsedView provides on-demand access to message fields.
    Fields are parsed only when accessed and cached for reuse.
    
    The raw bytes are always preserved - modifications create
    new raw bytes rather than mutating the original.
    """
    
    def __init__(self, raw: bytes, schema: Schema):
        """
        Initialize a parsed view.
        
        Args:
            raw: Raw message bytes
            schema: Schema used for parsing
        """
        self._raw = raw
        self._schema = schema
        self._cache: dict[str, Any] = {}
        self._parsed = False
    
    @property
    def raw(self) -> bytes:
        """Original raw message bytes."""
        return self._raw
    
    @property
    def schema(self) -> Schema:
        """Schema used for parsing."""
        return self._schema
    
    @abstractmethod
    def get_field(self, path: str, default: Any = None) -> Any:
        """
        Get a field value by path.
        
        The path format is schema-specific:
        - HL7: "MSH-9.1", "PID-3.1", "OBX(1)-5"
        - JSON: "$.patient.name", "$.observations[0].value"
        - XML: "/Message/Patient/Name"
        
        Args:
            path: Field path
            default: Default value if field not found
            
        Returns:
            Field value or default
        """
        ...
    
    @abstractmethod
    def set_field(self, path: str, value: Any) -> bytes:
        """
        Set a field value and return new raw bytes.
        
        Does NOT modify the original raw bytes.
        
        Args:
            path: Field path
            value: New field value
            
        Returns:
            New raw bytes with field updated
        """
        ...
    
    def has_field(self, path: str) -> bool:
        """
        Check if a field exists.
        
        Args:
            path: Field path
            
        Returns:
            True if field exists
        """
        return self.get_field(path) is not None
    
    def get_fields(self, paths: list[str]) -> dict[str, Any]:
        """
        Get multiple field values.
        
        Args:
            paths: List of field paths
            
        Returns:
            Dictionary of path -> value
        """
        return {path: self.get_field(path) for path in paths}
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert parsed view to dictionary.
        
        Returns:
            Dictionary representation of message
        """
        return {"raw": self._raw.decode("utf-8", errors="replace")}
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(schema={self._schema.name})"
