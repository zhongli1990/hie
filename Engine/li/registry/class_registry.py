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


# ─── Namespace Conventions ───────────────────────────────────────────
#
# PROTECTED namespaces (core product — developers MUST NOT modify):
#   li.*          — Core LI host classes (HL7TCPService, RoutingEngine, etc.)
#   Engine.li.*   — Same classes via fully-qualified import path
#   EnsLib.*      — IRIS compatibility aliases
#
# DEVELOPER namespaces (custom extensions — developers create here):
#   custom.*      — Organisation-specific custom classes
#                   e.g. custom.nhs.NHSValidationProcess
#                        custom.sth.PatientLookupProcess
#                        custom.myorg.FHIRBridgeService
#
# The ClassRegistry enforces this at registration time:
#   - Internal registration (_register_internal) bypasses checks (for core)
#   - Public registration (register_host) validates namespace
# ─────────────────────────────────────────────────────────────────────

PROTECTED_NAMESPACES = (
    "li.",
    "Engine.li.",
    "EnsLib.",
)

CUSTOM_NAMESPACE_PREFIX = "custom."


class ClassRegistry:
    """
    Global registry for dynamic class lookup.
    
    Enables the engine to instantiate classes by name from configuration,
    supporting both built-in and custom user classes.
    
    Namespace Convention:
        - ``li.*`` and ``Engine.li.*`` — Protected core product classes.
          Developers MUST NOT create or modify classes in these namespaces.
        - ``custom.*`` — Developer extension namespace.
          All custom services, processes, and operations go here.
        - ``EnsLib.*`` — IRIS compatibility aliases (read-only).
    
    Usage:
        # Core class (registered internally by the engine):
        ClassRegistry._register_internal("li.hosts.hl7.HL7TCPService", HL7TCPService)
        
        # Custom class (registered by developer via @register_host decorator):
        @register_host("custom.nhs.NHSValidationProcess")
        class NHSValidationProcess(BusinessProcess): ...
        
        # Look up and instantiate (works for both):
        host_class = ClassRegistry.get_host_class("li.hosts.hl7.HL7TCPService")
        host_class = ClassRegistry.get_host_class("custom.nhs.NHSValidationProcess")
    """
    
    # Class registries
    _hosts: dict[str, Type[Any]] = {}
    _adapters: dict[str, Type[Any]] = {}
    _transforms: dict[str, Type[Any]] = {}
    _rules: dict[str, Type[Any]] = {}
    
    # Alias mappings (for IRIS compatibility)
    _aliases: dict[str, str] = {}
    
    @classmethod
    def _validate_custom_namespace(cls, name: str, allow_internal: bool = False) -> None:
        """
        Validate that a class name follows namespace conventions.
        
        Raises ValueError if a non-internal caller tries to register
        in a protected namespace (li.*, Engine.li.*, EnsLib.*).
        
        Args:
            name: Full class name to validate
            allow_internal: If True, skip validation (for core engine use)
        """
        if allow_internal:
            return
        
        for ns in PROTECTED_NAMESPACES:
            if name.startswith(ns):
                raise ValueError(
                    f"Cannot register class '{name}' in protected namespace '{ns}'. "
                    f"Core product classes (li.*, Engine.li.*, EnsLib.*) are read-only. "
                    f"Custom classes must use the '{CUSTOM_NAMESPACE_PREFIX}' namespace, "
                    f"e.g. 'custom.myorg.{name.rsplit('.', 1)[-1]}'"
                )
    
    @classmethod
    def _register_internal(cls, name: str, host_class: Type[Any]) -> None:
        """
        Register a core product host class (internal use only).
        
        This bypasses namespace validation and is used by the engine
        to register built-in li.* classes during startup.
        
        Args:
            name: Full class name (e.g., "li.hosts.hl7.HL7TCPService")
            host_class: The host class
        """
        cls._hosts[name] = host_class
        logger.debug("host_registered", name=name, class_name=host_class.__name__, internal=True)
    
    @classmethod
    def register_host(cls, name: str, host_class: Type[Any]) -> None:
        """
        Register a host class.
        
        For custom developer classes, the name MUST start with 'custom.'.
        Core product classes (li.*, Engine.li.*) are registered via
        _register_internal() and cannot be overwritten by this method.
        
        Args:
            name: Full class name (e.g., "custom.nhs.NHSValidationProcess")
            host_class: The host class
            
        Raises:
            ValueError: If name is in a protected namespace
        """
        cls._validate_custom_namespace(name)
        cls._hosts[name] = host_class
        logger.debug("host_registered", name=name, class_name=host_class.__name__)
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[Any]) -> None:
        """
        Register an adapter class.
        
        Args:
            name: Full class name (e.g., "custom.myorg.MyAdapter" or internal "li.adapters.mllp.MLLPInboundAdapter")
            adapter_class: The adapter class
        """
        cls._adapters[name] = adapter_class
        logger.debug("adapter_registered", name=name, class_name=adapter_class.__name__)
    
    @classmethod
    def register_transform(cls, name: str, transform_class: Type[Any]) -> None:
        """
        Register a transform class.
        
        Args:
            name: Full class name (e.g., "custom.sth.v23_to_v251")
            transform_class: The transform class
        """
        cls._validate_custom_namespace(name)
        cls._transforms[name] = transform_class
        logger.debug("transform_registered", name=name, class_name=transform_class.__name__)
    
    @classmethod
    def register_rule(cls, name: str, rule_class: Type[Any]) -> None:
        """
        Register a rule class.
        
        Args:
            name: Full class name (e.g., "custom.sth.ADTRoutingRule")
            rule_class: The rule class
        """
        cls._validate_custom_namespace(name)
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

            # Cache in registry for future use (use internal to bypass namespace check
            # since dynamic import may resolve core classes by fully-qualified name)
            cls._register_internal(name, host_class)

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
    def reload_custom_classes(cls) -> dict[str, Any]:
        """
        Hot-reload custom.* classes without restarting the engine.
        
        Clears all custom.* entries from hosts, transforms, and rules,
        then re-runs load_custom_modules() to re-discover and re-register.
        Core li.* / EnsLib.* classes are untouched.
        
        Returns:
            Dict with counts of removed and reloaded classes.
        """
        import importlib
        
        # 1. Snapshot custom entries before clearing
        old_hosts = [n for n in cls._hosts if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        old_transforms = [n for n in cls._transforms if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        old_rules = [n for n in cls._rules if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        
        removed = len(old_hosts) + len(old_transforms) + len(old_rules)
        
        for name in old_hosts:
            del cls._hosts[name]
        for name in old_transforms:
            del cls._transforms[name]
        for name in old_rules:
            del cls._rules[name]
        
        logger.info("custom_classes_cleared", hosts=len(old_hosts),
                     transforms=len(old_transforms), rules=len(old_rules))
        
        # 2. Invalidate cached custom modules so importlib re-reads from disk
        import sys
        stale = [m for m in sys.modules if m.startswith("Engine.custom.") and not m.endswith("__init__")]
        for mod_name in stale:
            mod = sys.modules.pop(mod_name, None)
            if mod is not None:
                importlib.invalidate_caches()
                logger.debug("custom_module_evicted", module=mod_name)
        
        # 3. Re-discover and re-register
        loaded = 0
        try:
            from Engine.custom import load_custom_modules
            loaded = load_custom_modules()
        except ImportError:
            logger.debug("no_custom_modules_package")
        except Exception as e:
            logger.error("custom_reload_error", error=str(e))
        
        new_hosts = [n for n in cls._hosts if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        new_transforms = [n for n in cls._transforms if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        new_rules = [n for n in cls._rules if n.startswith(CUSTOM_NAMESPACE_PREFIX)]
        
        result = {
            "removed": removed,
            "modules_loaded": loaded,
            "registered": {
                "hosts": new_hosts,
                "transforms": new_transforms,
                "rules": new_rules,
            },
        }
        logger.info("custom_classes_reloaded", **result)
        return result
    
    @classmethod
    def is_protected_namespace(cls, name: str) -> bool:
        """Check if a class name is in a protected (core product) namespace."""
        return any(name.startswith(ns) for ns in PROTECTED_NAMESPACES)
    
    @classmethod
    def is_custom_namespace(cls, name: str) -> bool:
        """Check if a class name is in the custom developer namespace."""
        return name.startswith(CUSTOM_NAMESPACE_PREFIX)
    
    @classmethod
    def register_defaults(cls) -> None:
        """
        Register default built-in classes.
        
        Called during engine initialization to register all standard classes.
        Uses _register_internal() to bypass namespace validation for core classes.
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
            "EnsLib.HL7.MsgRouter.RoutingEngine": "li.hosts.routing.HL7RoutingEngine",
            "EnsLib.HL7.SequenceManager": "li.hosts.hl7.HL7SequenceManager",
            
            # FHIR Services
            "HS.FHIRServer.Interop.Service": "li.hosts.fhir.FHIRRESTService",
            
            # FHIR Operations
            "HS.FHIR.REST.Operation": "li.hosts.fhir.FHIRRESTOperation",
            
            # FHIR Processes
            "HS.FHIRServer.Interop.Process": "li.hosts.fhir_routing.FHIRRoutingEngine",
            
            # Generic
            "EnsLib.MsgRouter.RoutingEngine": "li.hosts.routing.RoutingEngine",
            "EnsLib.EMail.AlertOperation": "li.hosts.email.EmailAlertOperation",
        }
        
        for alias, target in aliases.items():
            cls.register_alias(alias, target)


def register_host(name: str):
    """
    Decorator to register a host class with the ClassRegistry.
    
    For DEVELOPER custom classes, use ``Engine.custom.register_host`` instead,
    which enforces the ``custom.*`` namespace convention.
    
    This decorator calls ``ClassRegistry.register_host()`` which validates
    that the name is NOT in a protected namespace (li.*, Engine.li.*, EnsLib.*).
    
    Usage:
        @register_host("custom.myorg.MyProcess")
        class MyProcess(BusinessProcess):
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
