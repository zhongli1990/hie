"""
LI Configuration Module

Provides configuration loading and models for LI Engine productions.
Supports IRIS XML format and YAML/JSON formats.
"""

from Engine.li.config.production_config import ProductionConfig
from Engine.li.config.item_config import ItemConfig, SettingTarget
from Engine.li.config.iris_xml_loader import IRISXMLLoader

__all__ = [
    "ProductionConfig",
    "ItemConfig",
    "SettingTarget",
    "IRISXMLLoader",
]
