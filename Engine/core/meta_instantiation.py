"""
Universal Meta-Instantiation System

Enables dynamic instantiation of ANY Python class from configuration.
Supports both registered classes (fast) and dynamic import (flexible).
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, Type, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class ImportPolicy:
    """Security policy for dynamic imports."""

    def __init__(
        self,
        allowed_packages: list[str] | None = None,
        blocked_packages: list[str] | None = None,
        require_base_class: Type | None = None
    ):
        """
        Configure import policy.

        Args:
            allowed_packages: Whitelist of allowed package prefixes (None = allow all)
            blocked_packages: Blacklist of blocked package prefixes
            require_base_class: Require imported classes inherit from this base
        """
        self.allowed_packages = allowed_packages or []
        self.blocked_packages = blocked_packages or [
            "os",           # OS operations
            "sys",          # System operations
            "subprocess",   # Command execution
            "importlib",    # Dynamic imports (prevent recursive exploits)
            "pickle",       # Arbitrary code execution
            "__main__",     # Main module
        ]
        self.require_base_class = require_base_class

    def is_allowed(self, module_name: str) -> bool:
        """Check if module is allowed to be imported."""
        # Check blacklist first
        for blocked in self.blocked_packages:
            if module_name.startswith(blocked):
                return False

        # If whitelist exists, must match
        if self.allowed_packages:
            return any(module_name.startswith(allowed) for allowed in self.allowed_packages)

        return True

    def validate_class(self, cls: Type) -> bool:
        """Validate that class meets requirements."""
        if self.require_base_class:
            return issubclass(cls, self.require_base_class)
        return True


class MetaInstantiator:
    """
    Universal meta-instantiation system.

    Combines ClassRegistry (fast, pre-registered) with dynamic import (flexible, on-demand).
    """

    def __init__(self, policy: ImportPolicy | None = None):
        """
        Initialize meta-instantiator.

        Args:
            policy: Import security policy (default: restrictive)
        """
        self.policy = policy or ImportPolicy(
            allowed_packages=[
                "Engine.",           # HIE engine classes
                "demos.",            # Demo classes
                "custom.",           # User custom classes (by convention)
            ],
            require_base_class=None  # Will be set per context
        )

        # Import cache (avoid re-importing same class)
        self._class_cache: dict[str, Type] = {}

    def import_class(self, fully_qualified_name: str) -> Type:
        """
        Import a class by fully qualified name.

        Args:
            fully_qualified_name: Full class path (e.g., "Engine.li.hosts.hl7.HL7TCPService")

        Returns:
            The imported class

        Raises:
            ImportError: If class cannot be imported
            SecurityError: If import is not allowed by policy
            TypeError: If imported class does not meet requirements

        Examples:
            # Built-in host
            cls = import_class("Engine.li.hosts.hl7.HL7TCPService")

            # Custom business process
            cls = import_class("demos.nhs_trust.lib.nhs_validation_process.NHSValidationProcess")

            # User-defined custom class
            cls = import_class("custom.my_organization.MyCustomRouter")
        """
        # Check cache first
        if fully_qualified_name in self._class_cache:
            return self._class_cache[fully_qualified_name]

        # Parse fully qualified name
        parts = fully_qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            raise ImportError(f"Invalid class name: {fully_qualified_name}. Must be module.ClassName")

        module_name, class_name = parts

        # Security check
        if not self.policy.is_allowed(module_name):
            raise SecurityError(f"Import not allowed by policy: {module_name}")

        # Dynamic import
        try:
            logger.debug("importing_class", module=module_name, class_name=class_name)
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import {fully_qualified_name}: {e}")

        # Validate class
        if not inspect.isclass(cls):
            raise TypeError(f"{fully_qualified_name} is not a class")

        if not self.policy.validate_class(cls):
            raise TypeError(
                f"{fully_qualified_name} does not meet requirements "
                f"(must inherit from {self.policy.require_base_class})"
            )

        # Cache and return
        self._class_cache[fully_qualified_name] = cls
        logger.info("class_imported", class_name=fully_qualified_name)

        return cls

    def instantiate(
        self,
        fully_qualified_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Import and instantiate a class in one step.

        Args:
            fully_qualified_name: Full class path
            *args: Positional arguments for class constructor
            **kwargs: Keyword arguments for class constructor

        Returns:
            Instance of the class

        Examples:
            # Instantiate with constructor arguments
            host = instantiate(
                "Engine.li.hosts.hl7.HL7TCPService",
                name="MyService",
                config=config
            )
        """
        cls = self.import_class(fully_qualified_name)

        try:
            instance = cls(*args, **kwargs)
            logger.info("class_instantiated", class_name=fully_qualified_name)
            return instance
        except Exception as e:
            raise RuntimeError(f"Failed to instantiate {fully_qualified_name}: {e}")


class SecurityError(Exception):
    """Raised when import is blocked by security policy."""
    pass


# Global instantiators for different contexts
_host_instantiator = None
_adapter_instantiator = None
_transform_instantiator = None


def get_host_instantiator() -> MetaInstantiator:
    """Get global host instantiator."""
    global _host_instantiator
    if _host_instantiator is None:
        from Engine.li.hosts.base import Host
        _host_instantiator = MetaInstantiator(
            policy=ImportPolicy(
                allowed_packages=["Engine.", "demos.", "custom."],
                require_base_class=Host
            )
        )
    return _host_instantiator


def get_adapter_instantiator() -> MetaInstantiator:
    """Get global adapter instantiator."""
    global _adapter_instantiator
    if _adapter_instantiator is None:
        from Engine.li.adapters.base import Adapter
        _adapter_instantiator = MetaInstantiator(
            policy=ImportPolicy(
                allowed_packages=["Engine.", "demos.", "custom."],
                require_base_class=Adapter
            )
        )
    return _adapter_instantiator


def import_host_class(fully_qualified_name: str) -> Type:
    """
    Import a host class by fully qualified name.

    Convenience function that uses the global host instantiator.
    """
    return get_host_instantiator().import_class(fully_qualified_name)


def instantiate_host(fully_qualified_name: str, *args, **kwargs) -> Any:
    """
    Import and instantiate a host class.

    Convenience function that uses the global host instantiator.
    """
    return get_host_instantiator().instantiate(fully_qualified_name, *args, **kwargs)
