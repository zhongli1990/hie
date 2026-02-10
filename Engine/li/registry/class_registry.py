"""
LI Class Registry

Provides dynamic class lookup for hosts, adapters, and other components.
Enables configuration-driven instantiation without hardcoded imports.
"""

from __future__ import annotations

from typing import Any, Type, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from Engine.li.hosts.base import Host
    from Engine.li.adapters.base import Adapter

logger = structlog.get_logger(__name__)


class ClassRegistry:
    """
    Global registry for dynamic class lookup.
    
    Enables the engine to instantiate classes by name from configuration,
    supporting both built-in and custom user classes.
    
    Usage:
        # Register a class
        ClassRegistry.register_host("li.hosts.hl7.HL7TCPService", HL7TCPService)
        
        # Look up and instantiate
        host_class = ClassRegistry.get_host_class("li.hosts.hl7.HL7TCPService")
        host = host_class(config)
    """
    
    # Class registries
    _hosts: dict[str, Type[Any]] = {}
    _adapters: dict[str, Type[Any]] = {}
    _transforms: dict[str, Type[Any]] = {}
    _rules: dict[str, Type[Any]] = {}
    
    # Alias mappings (for IRIS compatibility)
    _aliases: dict[str, str] = {}
    
    @classmethod
    def register_host(cls, name: str, host_class: Type[Any]) -> None:
        """
        Register a host class.
        
        Args:
            name: Full class name (e.g., "li.hosts.hl7.HL7TCPService")
            host_class: The host class
        """
        cls._hosts[name] = host_class
        logger.debug("host_registered", name=name, class_name=host_class.__name__)
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[Any]) -> None:
        """
        Register an adapter class.
        
        Args:
            name: Full class name (e.g., "li.adapters.mllp.MLLPInboundAdapter")
            adapter_class: The adapter class
        """
        cls._adapters[name] = adapter_class
        logger.debug("adapter_registered", name=name, class_name=adapter_class.__name__)
    
    @classmethod
    def register_transform(cls, name: str, transform_class: Type[Any]) -> None:
        """
        Register a transform class.
        
        Args:
            name: Full class name
            transform_class: The transform class
        """
        cls._transforms[name] = transform_class
        logger.debug("transform_registered", name=name, class_name=transform_class.__name__)
    
    @classmethod
    def register_rule(cls, name: str, rule_class: Type[Any]) -> None:
        """
        Register a rule class.
        
        Args:
            name: Full class name
            rule_class: The rule class
        """
        cls._rules[name] = rule_class
        logger.debug("rule_registered", name=name, class_name=rule_class.__name__)
    
    @classmethod
    def register_alias(cls, alias: str, target: str) -> None:
        """
        Register a class name alias.
        
        Useful for IRIS compatibility where class names differ.
        
        Args:
            alias: Alias name (e.g., "EnsLib.HL7.Service.TCPService")
            target: Target class name (e.g., "li.hosts.hl7.HL7TCPService")
        """
        cls._aliases[alias] = target
        logger.debug("alias_registered", alias=alias, target=target)
    
    @classmethod
    def resolve_name(cls, name: str) -> str:
        """
        Resolve a class name, following aliases.
        
        Args:
            name: Class name (possibly an alias)
            
        Returns:
            Resolved class name
        """
        return cls._aliases.get(name, name)
    
    @classmethod
    def get_host_class(cls, name: str) -> Type[Any] | None:
        """
        Get a host class by name.
        
        Args:
            name: Class name (will resolve aliases)
            
        Returns:
            Host class or None if not found
        """
        resolved = cls.resolve_name(name)
        return cls._hosts.get(resolved)
    
    @classmethod
    def get_or_import_host_class(cls, name: str) -> Type[Any]:
        """
        Get a host class by name with automatic import fallback.

        Strategy:
        1. Try ClassRegistry (fast, pre-registered)
        2. Try dynamic import (flexible, on-demand)
        3. Raise if neither works

        Args:
            name: Class name (can be alias, short name, or fully qualified name)

        Returns:
            Host class

        Raises:
            ValueError: If class cannot be found or imported

        Examples:
            # Pre-registered class (fast path)
            cls = get_or_import_host_class("li.hosts.hl7.HL7TCPService")

            # Fully qualified name (dynamic import)
            cls = get_or_import_host_class("Engine.li.hosts.hl7.HL7TCPService")

            # Custom user class (dynamic import)
            cls = get_or_import_host_class("custom.my_org.MyCustomProcess")
        """
        # 1. Try registry first (fast)
        host_class = cls.get_host_class(name)
        if host_class is not None:
            logger.debug("host_class_from_registry", name=name)
            return host_class

        # 2. Try dynamic import (flexible)
        try:
            from Engine.core.meta_instantiation import import_host_class
            host_class = import_host_class(name)
            logger.info("host_class_dynamically_imported", name=name)

            # Cache in registry for future use
            cls.register_host(name, host_class)

            return host_class
        except Exception as e:
            raise ValueError(
                f"Cannot find or import host class '{name}'. "
                f"Not in registry and dynamic import failed: {e}"
            )

    @classmethod
    def get_adapter_class(cls, name: str) -> Type[Any] | None:
        """
        Get an adapter class by name.

        Args:
            name: Class name (will resolve aliases)

        Returns:
            Adapter class or None if not found
        """
        resolved = cls.resolve_name(name)
        return cls._adapters.get(resolved)
    
    @classmethod
    def get_transform_class(cls, name: str) -> Type[Any] | None:
        """
        Get a transform class by name.
        
        Args:
            name: Class name (will resolve aliases)
            
        Returns:
            Transform class or None if not found
        """
        resolved = cls.resolve_name(name)
        return cls._transforms.get(resolved)
    
    @classmethod
    def get_rule_class(cls, name: str) -> Type[Any] | None:
        """
        Get a rule class by name.
        
        Args:
            name: Class name (will resolve aliases)
            
        Returns:
            Rule class or None if not found
        """
        resolved = cls.resolve_name(name)
        return cls._rules.get(resolved)
    
    @classmethod
    def list_hosts(cls) -> list[str]:
        """List all registered host class names."""
        return list(cls._hosts.keys())
    
    @classmethod
    def list_adapters(cls) -> list[str]:
        """List all registered adapter class names."""
        return list(cls._adapters.keys())
    
    @classmethod
    def list_transforms(cls) -> list[str]:
        """List all registered transform class names."""
        return list(cls._transforms.keys())
    
    @classmethod
    def list_rules(cls) -> list[str]:
        """List all registered rule class names."""
        return list(cls._rules.keys())
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registries. Useful for testing."""
        cls._hosts.clear()
        cls._adapters.clear()
        cls._transforms.clear()
        cls._rules.clear()
        cls._aliases.clear()
    
    @classmethod
    def register_defaults(cls) -> None:
        """
        Register default built-in classes.
        
        Called during engine initialization to register all standard classes.
        """
        # This will be populated as we implement the host classes
        # For now, set up IRIS aliases
        cls._setup_iris_aliases()
    
    @classmethod
    def _setup_iris_aliases(cls) -> None:
        """Set up IRIS to LI class name aliases."""
        aliases = {
            # HL7 Services
            "EnsLib.HL7.Service.TCPService": "li.hosts.hl7.HL7TCPService",
            "EnsLib.HL7.Service.HTTPService": "li.hosts.hl7.HL7HTTPService",
            "EnsLib.HL7.Service.FileService": "li.hosts.hl7.HL7FileService",
            
            # HL7 Operations
            "EnsLib.HL7.Operation.TCPOperation": "li.hosts.hl7.HL7TCPOperation",
            "EnsLib.HL7.Operation.HTTPOperation": "li.hosts.hl7.HL7HTTPOperation",
            "EnsLib.HL7.Operation.FileOperation": "li.hosts.hl7.HL7FileOperation",
            
            # HL7 Processes
            "EnsLib.HL7.MsgRouter.RoutingEngine": "li.hosts.hl7.HL7RoutingEngine",
            "EnsLib.HL7.SequenceManager": "li.hosts.hl7.HL7SequenceManager",
            
            # Generic
            "EnsLib.MsgRouter.RoutingEngine": "li.hosts.routing.RoutingEngine",
            "EnsLib.EMail.AlertOperation": "li.hosts.email.EmailAlertOperation",
        }
        
        for alias, target in aliases.items():
            cls.register_alias(alias, target)


def register_host(name: str):
    """
    Decorator to register a host class.
    
    Usage:
        @register_host("li.hosts.hl7.HL7TCPService")
        class HL7TCPService(BusinessService):
            ...
    """
    def decorator(cls):
        ClassRegistry.register_host(name, cls)
        return cls
    return decorator


def register_adapter(name: str):
    """
    Decorator to register an adapter class.
    
    Usage:
        @register_adapter("li.adapters.mllp.MLLPInboundAdapter")
        class MLLPInboundAdapter(InboundAdapter):
            ...
    """
    def decorator(cls):
        ClassRegistry.register_adapter(name, cls)
        return cls
    return decorator
