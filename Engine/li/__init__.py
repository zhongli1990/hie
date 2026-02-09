"""
LI (Lightweight Integration) Engine

An enterprise-grade, IRIS-compatible workflow orchestrator for healthcare integration.
Designed for NHS hospital trust integration engines with support for:
- IRIS production XML configuration
- HL7v2 messaging with MLLP
- Schema-driven lazy parsing
- Dynamic runtime management
- Scalable Docker deployment
"""

__version__ = "0.1.0"
__author__ = "LI Engine Team"

from Engine.li.config import ProductionConfig, ItemConfig
from Engine.li.registry import ClassRegistry, SchemaRegistry

__all__ = [
    "ProductionConfig",
    "ItemConfig", 
    "ClassRegistry",
    "SchemaRegistry",
]
