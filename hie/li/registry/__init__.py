"""
LI Registry Module

Provides registries for dynamic class and schema lookup at runtime.
"""

from hie.li.registry.class_registry import ClassRegistry
from hie.li.registry.schema_registry import SchemaRegistry

__all__ = [
    "ClassRegistry",
    "SchemaRegistry",
]
