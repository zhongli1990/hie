"""
LI Schema Registry

Provides global registry for message schemas.
Enables lazy loading and lookup of schemas by name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Type, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from hie.li.schemas.base import Schema

logger = structlog.get_logger(__name__)


class SchemaRegistry:
    """
    Global registry for message schemas.
    
    Schemas are loaded lazily on first access and cached.
    Supports schema inheritance (e.g., PKB extends CANCERREG2.4 extends 2.4).
    
    Usage:
        # Register a schema
        SchemaRegistry.register(hl7_schema)
        
        # Get a schema by name
        schema = SchemaRegistry.get("PKB")
        
        # Load schemas from directory
        SchemaRegistry.load_from_directory("/schemas/hl7")
    """
    
    # Schema storage
    _schemas: dict[str, Any] = {}  # name -> Schema instance
    _schema_paths: dict[str, Path] = {}  # name -> file path (for lazy loading)
    _loaders: dict[str, Type[Any]] = {}  # extension -> loader class
    
    @classmethod
    def register(cls, schema: Any) -> None:
        """
        Register a schema instance.
        
        Args:
            schema: Schema instance with 'name' attribute
        """
        name = getattr(schema, "name", None)
        if not name:
            raise ValueError("Schema must have a 'name' attribute")
        
        cls._schemas[name] = schema
        logger.debug("schema_registered", name=name)
    
    @classmethod
    def register_path(cls, name: str, path: Path | str) -> None:
        """
        Register a schema file path for lazy loading.
        
        The schema will be loaded on first access.
        
        Args:
            name: Schema name
            path: Path to schema file
        """
        cls._schema_paths[name] = Path(path)
        logger.debug("schema_path_registered", name=name, path=str(path))
    
    @classmethod
    def register_loader(cls, extension: str, loader_class: Type[Any]) -> None:
        """
        Register a schema loader for a file extension.
        
        Args:
            extension: File extension (e.g., ".hl7", ".xml")
            loader_class: Loader class with load(path) method
        """
        cls._loaders[extension.lower()] = loader_class
        logger.debug("schema_loader_registered", extension=extension)
    
    @classmethod
    def get(cls, name: str) -> Any | None:
        """
        Get a schema by name.
        
        If the schema is not loaded but has a registered path,
        it will be loaded lazily.
        
        Args:
            name: Schema name
            
        Returns:
            Schema instance or None if not found
        """
        # Check if already loaded
        if name in cls._schemas:
            return cls._schemas[name]
        
        # Try lazy loading
        if name in cls._schema_paths:
            schema = cls._load_schema(name, cls._schema_paths[name])
            if schema:
                cls._schemas[name] = schema
                return schema
        
        # Not found
        logger.warning("schema_not_found", name=name)
        return None
    
    @classmethod
    def _load_schema(cls, name: str, path: Path) -> Any | None:
        """
        Load a schema from file.
        
        Args:
            name: Schema name
            path: Path to schema file
            
        Returns:
            Schema instance or None if loading failed
        """
        if not path.exists():
            logger.error("schema_file_not_found", name=name, path=str(path))
            return None
        
        extension = path.suffix.lower()
        loader_class = cls._loaders.get(extension)
        
        if not loader_class:
            logger.error("no_loader_for_extension", extension=extension, name=name)
            return None
        
        try:
            loader = loader_class()
            schema = loader.load(path)
            logger.info("schema_loaded", name=name, path=str(path))
            return schema
        except Exception as e:
            logger.error("schema_load_failed", name=name, path=str(path), error=str(e))
            return None
    
    @classmethod
    def load_from_directory(cls, directory: str | Path, recursive: bool = True) -> int:
        """
        Load all schemas from a directory.
        
        Registers paths for lazy loading based on filename.
        
        Args:
            directory: Directory containing schema files
            recursive: Whether to search subdirectories
            
        Returns:
            Number of schemas registered
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning("schema_directory_not_found", directory=str(directory))
            return 0
        
        count = 0
        pattern = "**/*" if recursive else "*"
        
        for path in directory.glob(pattern):
            if path.is_file() and path.suffix.lower() in cls._loaders:
                # Use filename without extension as schema name
                name = path.stem
                cls.register_path(name, path)
                count += 1
        
        logger.info("schemas_discovered", directory=str(directory), count=count)
        return count
    
    @classmethod
    def list_schemas(cls) -> list[str]:
        """List all registered schema names (loaded and pending)."""
        names = set(cls._schemas.keys())
        names.update(cls._schema_paths.keys())
        return sorted(names)
    
    @classmethod
    def is_loaded(cls, name: str) -> bool:
        """Check if a schema is already loaded."""
        return name in cls._schemas
    
    @classmethod
    def clear(cls) -> None:
        """Clear all schemas. Useful for testing."""
        cls._schemas.clear()
        cls._schema_paths.clear()
    
    @classmethod
    def get_with_inheritance(cls, name: str) -> list[Any]:
        """
        Get a schema and all its parent schemas.
        
        Follows the inheritance chain (base_schema attribute).
        
        Args:
            name: Schema name
            
        Returns:
            List of schemas from most specific to most general
        """
        schemas = []
        current_name = name
        
        while current_name:
            schema = cls.get(current_name)
            if not schema:
                break
            schemas.append(schema)
            current_name = getattr(schema, "base_schema", None)
        
        return schemas
