"""
OpenLI HIE — Custom Developer Extensions
==========================================

This package is the DEVELOPER namespace for custom host classes.
All custom services, processes, and operations MUST be defined here.

Namespace Convention:
    custom.<org>.<ClassName>

    Examples:
        custom.nhs.NHSValidationProcess
        custom.sth.PatientLookupProcess
        custom.myorg.FHIRBridgeService

Rules:
    1. NEVER modify classes in the li.* or Engine.li.* namespaces.
       Those are core product classes maintained by the LI team.
    2. ALL custom classes must subclass a core base class:
       - BusinessService  (for inbound services)
       - BusinessProcess  (for routing/transformation)
       - BusinessOperation (for outbound operations)
    3. Register custom classes using the @register_host decorator:

       from Engine.custom import register_host
       from Engine.li.hosts.base import BusinessProcess

       @register_host("custom.nhs.NHSValidationProcess")
       class NHSValidationProcess(BusinessProcess):
           ...

    4. Custom classes are loaded from:
       - Engine/custom/<org>/<module>.py  (in the engine container)
       - /app/custom/<org>/<module>.py    (via Docker volume mount)

Directory Structure:
    Engine/custom/
    ├── __init__.py          ← This file (register_host decorator)
    ├── nhs/                 ← NHS-specific custom classes
    │   ├── __init__.py
    │   ├── validation.py    ← NHSValidationProcess
    │   └── fhir_bridge.py   ← FHIRHTTPService
    ├── sth/                 ← St Thomas' Hospital custom classes
    │   ├── __init__.py
    │   └── patient_lookup.py
    └── _example/            ← Example template for developers
        ├── __init__.py
        └── example_process.py
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Type

import structlog

logger = structlog.get_logger(__name__)


def register_host(class_name: str):
    """
    Decorator to register a custom host class with the ClassRegistry.

    The class_name MUST start with 'custom.' — the ClassRegistry will
    reject any attempt to register in a protected namespace (li.*, EnsLib.*).

    Usage:
        from Engine.custom import register_host
        from Engine.li.hosts.base import BusinessProcess

        @register_host("custom.nhs.NHSValidationProcess")
        class NHSValidationProcess(BusinessProcess):
            async def on_message(self, message):
                # Custom validation logic
                ...

    Args:
        class_name: Full dotted class name starting with 'custom.'

    Returns:
        Decorator that registers the class and returns it unchanged.

    Raises:
        ValueError: If class_name does not start with 'custom.'
        ValueError: If class_name is in a protected namespace
    """
    if not class_name.startswith("custom."):
        raise ValueError(
            f"Custom class name '{class_name}' must start with 'custom.' — "
            f"e.g. 'custom.nhs.{class_name.rsplit('.', 1)[-1]}'"
        )

    def decorator(cls: Type[Any]) -> Type[Any]:
        from Engine.li.registry import ClassRegistry
        ClassRegistry.register_host(class_name, cls)
        logger.info(
            "custom_host_registered",
            class_name=class_name,
            python_class=f"{cls.__module__}.{cls.__qualname__}",
        )
        return cls

    return decorator


def register_transform(class_name: str):
    """
    Decorator to register a custom transform class.

    Usage:
        from Engine.custom import register_transform

        @register_transform("custom.sth.v23_to_v251_RIS")
        class V23ToV251RIS:
            def transform(self, message): ...
    """
    if not class_name.startswith("custom."):
        raise ValueError(
            f"Custom transform name '{class_name}' must start with 'custom.'"
        )

    def decorator(cls: Type[Any]) -> Type[Any]:
        from Engine.li.registry import ClassRegistry
        ClassRegistry.register_transform(class_name, cls)
        logger.info("custom_transform_registered", class_name=class_name)
        return cls

    return decorator


def load_custom_modules() -> int:
    """
    Auto-discover and import all custom modules in this package.

    Called during engine startup to ensure all @register_host and
    @register_transform decorators are executed.

    Returns:
        Number of modules loaded.
    """
    loaded = 0
    package_path = __path__
    package_name = __name__

    for importer, modname, ispkg in pkgutil.walk_packages(
        path=package_path,
        prefix=f"{package_name}.",
    ):
        # Skip private/internal modules
        if modname.split(".")[-1].startswith("_"):
            continue
        try:
            importlib.import_module(modname)
            loaded += 1
            logger.debug("custom_module_loaded", module=modname)
        except Exception as e:
            logger.error("custom_module_load_error", module=modname, error=str(e))

    logger.info("custom_modules_loaded", count=loaded)
    return loaded
