# OpenLI HIE — Custom Class Developer Guide

**Version:** 1.7.3  
**Date:** February 11, 2026  

---

## The Golden Rule

> **Never modify core product classes. Always extend in the `custom.*` namespace.**

| Namespace | Owner | Can Modify? | Purpose |
|-----------|-------|-------------|---------|
| `li.*` | LI Product Team | ❌ **NO** | Core host classes, adapters, schemas |
| `Engine.li.*` | LI Product Team | ❌ **NO** | Same classes via fully-qualified path |
| `EnsLib.*` | IRIS Aliases | ❌ **NO** | Read-only compatibility aliases |
| **`custom.*`** | **You (Developer)** | ✅ **YES** | Your custom extensions |

This is enforced at runtime by the `ClassRegistry`. Attempting to register a class in a protected namespace raises a `ValueError`.

---

## How It Works

### Core Classes (Use As-Is)

Core classes are pre-built, production-tested components. You **configure** them via the Portal or API — you don't modify their source code.

| Core Class | Type | What It Does |
|-----------|------|-------------|
| `li.hosts.hl7.HL7TCPService` | Service | Receives HL7 v2.x via MLLP |
| `li.hosts.hl7.HL7FileService` | Service | Watches directory for HL7 files |
| `li.hosts.http.HTTPService` | Service | HTTP/REST inbound |
| `li.hosts.routing.HL7RoutingEngine` | Process | Content-based message routing |
| `li.hosts.hl7.HL7TCPOperation` | Operation | Sends HL7 v2.x via MLLP |
| `li.hosts.file.FileOperation` | Operation | Writes messages to files |

**IRIS developers:** These map directly to `EnsLib.*` classes. The aliases work too:
- `EnsLib.HL7.Service.TCPService` → `li.hosts.hl7.HL7TCPService`
- `EnsLib.HL7.MsgRouter.RoutingEngine` → `li.hosts.routing.HL7RoutingEngine`
- `EnsLib.HL7.Operation.TCPOperation` → `li.hosts.hl7.HL7TCPOperation`

### Custom Classes (You Create These)

When you need logic that doesn't exist in core classes, you create a custom class:

```
Engine/custom/
├── __init__.py              ← register_host decorator + auto-loader
├── nhs/                     ← Your organisation namespace
│   ├── __init__.py
│   ├── validation.py        ← custom.nhs.NHSValidationProcess
│   └── fhir_bridge.py       ← custom.nhs.FHIRHTTPService
├── sth/                     ← Another organisation
│   ├── __init__.py
│   └── patient_lookup.py    ← custom.sth.PatientLookupProcess
└── _example/                ← Template to copy
    ├── __init__.py
    └── example_process.py   ← custom._example.ExampleProcess
```

---

## Quick Start: Create a Custom Process

### Step 1: Copy the Template

```bash
cp -r Engine/custom/_example Engine/custom/myorg
```

### Step 2: Create Your Class

```python
# Engine/custom/myorg/my_enrichment.py

from Engine.li.hosts.base import BusinessProcess
from Engine.custom import register_host

@register_host("custom.myorg.PatientEnrichmentProcess")
class PatientEnrichmentProcess(BusinessProcess):
    """Enriches messages with data from an external REST API."""

    def __init__(self, name, config=None, **kwargs):
        super().__init__(name=name, config=config, **kwargs)
        self._api_url = self.get_setting("Host", "EnrichmentAPIUrl", "")
        self._timeout = float(self.get_setting("Host", "APITimeout", 5.0))

    async def on_message(self, message):
        # Your custom logic here
        from Engine.li.hosts.hl7 import HL7Message
        if isinstance(message, HL7Message) and message.parsed:
            patient_id = message.parsed.get_field("PID-3.1", "")
            # ... call external API, enrich message ...
        
        self._metrics.messages_processed += 1
        return message
```

### Step 3: Configure via Portal

1. **Portal → Projects → Add Item**
2. Type: **Process**
3. Class: `custom.myorg.PatientEnrichmentProcess`
4. Host Settings:
   - `TargetConfigNames`: `ADT.Content.Router`
   - `EnrichmentAPIUrl`: `https://api.myorg.nhs.uk/patient`
   - `APITimeout`: `5.0`

### Step 4: Or Configure via API

```bash
curl -X POST http://localhost:9300/api/workspaces/{ws_id}/projects/{proj_id}/items \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Patient.Enrichment",
    "item_type": "process",
    "class_name": "custom.myorg.PatientEnrichmentProcess",
    "pool_size": 2,
    "host_settings": {
      "TargetConfigNames": "ADT.Content.Router",
      "EnrichmentAPIUrl": "https://api.myorg.nhs.uk/patient",
      "APITimeout": "5.0"
    }
  }'
```

### Step 5: Or Configure via GenAI Agent

```
> Create a patient enrichment process that calls https://api.myorg.nhs.uk/patient
  and routes to ADT.Content.Router
```

The agent will call `hie_create_item` with `class_name="custom.myorg.PatientEnrichmentProcess"`.

---

## Base Classes to Extend

| Base Class | Import | When to Use |
|-----------|--------|-------------|
| `BusinessService` | `from Engine.li.hosts.base import BusinessService` | Custom inbound (e.g. FHIR HTTP, custom protocol) |
| `BusinessProcess` | `from Engine.li.hosts.base import BusinessProcess` | Custom validation, enrichment, transformation |
| `BusinessOperation` | `from Engine.li.hosts.base import BusinessOperation` | Custom outbound (e.g. REST API, database, email) |

### Key Methods to Override

**BusinessService:**
```python
async def on_message_received(self, data: bytes) -> Any:
    """Called when raw data arrives from the adapter."""

async def _process_message(self, message: Any) -> Any:
    """Called to process and route the parsed message."""
```

**BusinessProcess:**
```python
async def on_message(self, message: Any) -> Any:
    """Called for each message from upstream. Return message to forward."""
```

**BusinessOperation:**
```python
async def on_message(self, message: Any) -> Any:
    """Called to send/deliver the message to the external system."""
```

### Key Properties Available

```python
self.name                    # Item name (e.g. "NHS.Validation.Process")
self.target_config_names     # List of downstream targets
self.business_rule_name      # Associated routing rule set
self._metrics                # HostMetrics (messages_processed, errors, etc.)

# Read settings:
self.get_setting("Host", "MyKey", "default")
self.get_setting("Adapter", "Port", "2575")
```

---

## The `@register_host` Decorator

```python
from Engine.custom import register_host

@register_host("custom.myorg.MyClassName")
class MyClassName(BusinessProcess):
    ...
```

**What it does:**
1. Validates the name starts with `custom.`
2. Registers the class in `ClassRegistry._hosts`
3. Makes it available for configuration via Portal, API, and Agent

**What happens if you try a protected namespace:**
```python
@register_host("li.hosts.myprocess.MyProcess")  # ❌ RAISES ValueError
class MyProcess(BusinessProcess): ...

# ValueError: Cannot register class 'li.hosts.myprocess.MyProcess' in
# protected namespace 'li.'. Custom classes must use the 'custom.' namespace,
# e.g. 'custom.myorg.MyProcess'
```

---

## Docker Volume Mount

In production, custom classes are mounted into the engine container:

```yaml
# docker-compose.yml
services:
  hie-engine:
    image: openli/hie-engine:v1.7.3
    volumes:
      - ./custom:/app/custom:ro    # Your custom classes
```

The engine auto-discovers and loads all modules in `custom/` at startup via `load_custom_modules()`.

---

## IRIS Developer Comparison

| IRIS Workflow | HIE Workflow |
|--------------|-------------|
| Create class in Studio extending `Ens.BusinessProcess` | Create Python file extending `BusinessProcess` |
| Register in Production via Portal | Register via `@register_host` decorator |
| Compile in Studio | Auto-loaded at engine startup |
| Configure settings in Portal | Configure settings in Portal (identical) |
| Debug in Terminal with `zwrite` | Debug with `structlog` + Portal Logs page |
| Export as XML | Export as Python module + JSON config |

---

## See Also

- [Developer & User Guide](./LI_HIE_DEVELOPER_GUIDE.md) — Full walkthrough
- [NHS Trust Demo](./NHS_TRUST_DEMO.md) — Complete 3+2+3 route example
- [Example Custom Process](../../Engine/custom/_example/example_process.py) — Copy-paste template
- [NHS Validation Process](../../Engine/custom/nhs/validation.py) — Production reference
