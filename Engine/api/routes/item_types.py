"""
Item Type Registry API Routes

Provides available item types and their configuration schemas.
"""

from __future__ import annotations

from aiohttp import web
import structlog

from Engine.api.models import (
    ItemTypeDefinition,
    ItemTypeRegistryResponse,
    SettingDefinition,
    ItemType,
)

logger = structlog.get_logger(__name__)


# Item Type Registry - defines all available item types
ITEM_TYPE_REGISTRY: list[ItemTypeDefinition] = [
    # HL7 Services (Inbound)
    ItemTypeDefinition(
        type="hl7.tcp.service",
        name="HL7 TCP Service",
        description="Receives HL7v2 messages via MLLP/TCP protocol",
        category=ItemType.SERVICE,
        iris_class_name="EnsLib.HL7.Service.TCPService",
        li_class_name="li.hosts.hl7.HL7TCPService",
        adapter_settings=[
            SettingDefinition(
                key="port",
                label="Port",
                type="number",
                required=True,
                default=2575,
                description="TCP port to listen on",
                validation={"min": 1, "max": 65535},
            ),
            SettingDefinition(
                key="readTimeout",
                label="Read Timeout (seconds)",
                type="number",
                required=False,
                default=30,
                description="Timeout for reading data from connection",
            ),
            SettingDefinition(
                key="stayConnected",
                label="Stay Connected",
                type="number",
                required=False,
                default=-1,
                description="-1 = keep alive, 0 = close after each message",
            ),
            SettingDefinition(
                key="sslConfig",
                label="SSL Configuration",
                type="string",
                required=False,
                description="Name of SSL/TLS configuration to use",
            ),
        ],
        host_settings=[
            SettingDefinition(
                key="messageSchemaCategory",
                label="HL7 Version",
                type="select",
                required=False,
                default="2.4",
                options=[
                    {"value": "2.3", "label": "HL7 v2.3"},
                    {"value": "2.4", "label": "HL7 v2.4"},
                    {"value": "2.5", "label": "HL7 v2.5"},
                    {"value": "2.5.1", "label": "HL7 v2.5.1"},
                ],
                description="HL7 message version for parsing and ACK generation",
            ),
            SettingDefinition(
                key="targetConfigNames",
                label="Target Items",
                type="multiselect",
                required=True,
                description="Items to route received messages to",
            ),
            SettingDefinition(
                key="ackMode",
                label="ACK Mode",
                type="select",
                required=False,
                default="App",
                options=[
                    {"value": "App", "label": "Application ACK"},
                    {"value": "Immediate", "label": "Immediate ACK"},
                    {"value": "None", "label": "No ACK"},
                ],
                description="When to send acknowledgment",
            ),
            SettingDefinition(
                key="archiveIO",
                label="Archive Messages",
                type="boolean",
                required=False,
                default=True,
                description="Archive inbound messages for audit",
            ),
        ],
    ),
    
    # HL7 Operations (Outbound)
    ItemTypeDefinition(
        type="hl7.tcp.operation",
        name="HL7 TCP Operation",
        description="Sends HL7v2 messages via MLLP/TCP protocol",
        category=ItemType.OPERATION,
        iris_class_name="EnsLib.HL7.Operation.TCPOperation",
        li_class_name="li.hosts.hl7.HL7TCPOperation",
        adapter_settings=[
            SettingDefinition(
                key="ipAddress",
                label="IP Address",
                type="string",
                required=True,
                description="Target server IP address or hostname",
            ),
            SettingDefinition(
                key="port",
                label="Port",
                type="number",
                required=True,
                default=2575,
                description="Target server port",
                validation={"min": 1, "max": 65535},
            ),
            SettingDefinition(
                key="connectTimeout",
                label="Connect Timeout (seconds)",
                type="number",
                required=False,
                default=30,
                description="Timeout for establishing connection",
            ),
            SettingDefinition(
                key="reconnectRetry",
                label="Reconnect Retry Count",
                type="number",
                required=False,
                default=5,
                description="Number of reconnection attempts",
            ),
            SettingDefinition(
                key="stayConnected",
                label="Stay Connected",
                type="number",
                required=False,
                default=-1,
                description="-1 = keep alive, 0 = close after each message",
            ),
            SettingDefinition(
                key="sslConfig",
                label="SSL Configuration",
                type="string",
                required=False,
                description="Name of SSL/TLS configuration to use",
            ),
        ],
        host_settings=[
            SettingDefinition(
                key="replyCodeActions",
                label="Reply Code Actions",
                type="string",
                required=False,
                default=":?R=F,:?E=S,:~=S,:?A=C,:*=S",
                description="IRIS-style reply code action mapping",
            ),
            SettingDefinition(
                key="retryInterval",
                label="Retry Interval (seconds)",
                type="number",
                required=False,
                default=5,
                description="Delay between retry attempts",
            ),
            SettingDefinition(
                key="failureTimeout",
                label="Failure Timeout (seconds)",
                type="number",
                required=False,
                default=15,
                description="Time before marking message as failed",
            ),
            SettingDefinition(
                key="archiveIO",
                label="Archive Messages",
                type="boolean",
                required=False,
                default=True,
                description="Archive outbound messages for audit",
            ),
        ],
    ),
    
    # HL7 Routing Engine (Process)
    ItemTypeDefinition(
        type="hl7.routing.engine",
        name="HL7 Routing Engine",
        description="Routes HL7 messages based on business rules",
        category=ItemType.PROCESS,
        iris_class_name="EnsLib.HL7.MsgRouter.RoutingEngine",
        li_class_name="li.hosts.routing.HL7RoutingEngine",
        adapter_settings=[],
        host_settings=[
            SettingDefinition(
                key="businessRuleName",
                label="Business Rule Name",
                type="string",
                required=False,
                description="Name of the business rule set to use",
            ),
            SettingDefinition(
                key="validation",
                label="Validation Mode",
                type="select",
                required=False,
                default="",
                options=[
                    {"value": "", "label": "None"},
                    {"value": "Warn", "label": "Warn on Invalid"},
                    {"value": "Error", "label": "Error on Invalid"},
                ],
                description="How to handle validation failures",
            ),
            SettingDefinition(
                key="ruleLogging",
                label="Rule Logging",
                type="select",
                required=False,
                default="a",
                options=[
                    {"value": "", "label": "None"},
                    {"value": "a", "label": "All Rules"},
                    {"value": "e", "label": "Errors Only"},
                ],
                description="Level of rule execution logging",
            ),
        ],
    ),
    
    # HTTP Service (Inbound)
    ItemTypeDefinition(
        type="http.service",
        name="HTTP Service",
        description="Receives messages via HTTP/REST endpoints",
        category=ItemType.SERVICE,
        iris_class_name="EnsLib.HTTP.Service.Standard",
        li_class_name="li.hosts.http.HTTPService",
        adapter_settings=[
            SettingDefinition(
                key="port",
                label="Port",
                type="number",
                required=True,
                default=8080,
                description="HTTP port to listen on",
                validation={"min": 1, "max": 65535},
            ),
            SettingDefinition(
                key="path",
                label="URL Path",
                type="string",
                required=False,
                default="/",
                description="URL path to handle requests",
            ),
            SettingDefinition(
                key="sslConfig",
                label="SSL Configuration",
                type="string",
                required=False,
                description="Name of SSL/TLS configuration for HTTPS",
            ),
        ],
        host_settings=[
            SettingDefinition(
                key="targetConfigNames",
                label="Target Items",
                type="multiselect",
                required=True,
                description="Items to route received messages to",
            ),
            SettingDefinition(
                key="contentType",
                label="Expected Content Type",
                type="select",
                required=False,
                default="application/json",
                options=[
                    {"value": "application/json", "label": "JSON"},
                    {"value": "application/xml", "label": "XML"},
                    {"value": "text/plain", "label": "Plain Text"},
                    {"value": "application/hl7-v2", "label": "HL7v2"},
                ],
            ),
        ],
    ),
    
    # HTTP Operation (Outbound)
    ItemTypeDefinition(
        type="http.operation",
        name="HTTP Operation",
        description="Sends messages via HTTP/REST requests",
        category=ItemType.OPERATION,
        iris_class_name="EnsLib.HTTP.Operation.Standard",
        li_class_name="li.hosts.http.HTTPOperation",
        adapter_settings=[
            SettingDefinition(
                key="url",
                label="URL",
                type="string",
                required=True,
                description="Target URL for HTTP requests",
            ),
            SettingDefinition(
                key="method",
                label="HTTP Method",
                type="select",
                required=False,
                default="POST",
                options=[
                    {"value": "GET", "label": "GET"},
                    {"value": "POST", "label": "POST"},
                    {"value": "PUT", "label": "PUT"},
                    {"value": "PATCH", "label": "PATCH"},
                    {"value": "DELETE", "label": "DELETE"},
                ],
            ),
            SettingDefinition(
                key="connectTimeout",
                label="Connect Timeout (seconds)",
                type="number",
                required=False,
                default=30,
            ),
            SettingDefinition(
                key="sslConfig",
                label="SSL Configuration",
                type="string",
                required=False,
            ),
        ],
        host_settings=[
            SettingDefinition(
                key="retryInterval",
                label="Retry Interval (seconds)",
                type="number",
                required=False,
                default=5,
            ),
            SettingDefinition(
                key="failureTimeout",
                label="Failure Timeout (seconds)",
                type="number",
                required=False,
                default=15,
            ),
        ],
    ),
    
    # File Service (Inbound)
    ItemTypeDefinition(
        type="file.service",
        name="File Service",
        description="Watches directories for incoming files",
        category=ItemType.SERVICE,
        iris_class_name="EnsLib.File.Service.Standard",
        li_class_name="li.hosts.file.FileService",
        adapter_settings=[
            SettingDefinition(
                key="filePath",
                label="File Path",
                type="string",
                required=True,
                description="Directory to watch for files",
            ),
            SettingDefinition(
                key="fileSpec",
                label="File Pattern",
                type="string",
                required=False,
                default="*.hl7",
                description="File name pattern to match (e.g., *.hl7)",
            ),
            SettingDefinition(
                key="pollingInterval",
                label="Polling Interval (seconds)",
                type="number",
                required=False,
                default=5,
            ),
            SettingDefinition(
                key="archivePath",
                label="Archive Path",
                type="string",
                required=False,
                description="Directory to move processed files to",
            ),
        ],
        host_settings=[
            SettingDefinition(
                key="targetConfigNames",
                label="Target Items",
                type="multiselect",
                required=True,
            ),
        ],
    ),
    
    # File Operation (Outbound)
    ItemTypeDefinition(
        type="file.operation",
        name="File Operation",
        description="Writes messages to files",
        category=ItemType.OPERATION,
        iris_class_name="EnsLib.File.Operation.Standard",
        li_class_name="li.hosts.file.FileOperation",
        adapter_settings=[
            SettingDefinition(
                key="filePath",
                label="File Path",
                type="string",
                required=True,
                description="Directory to write files to",
            ),
            SettingDefinition(
                key="fileName",
                label="File Name Pattern",
                type="string",
                required=False,
                default="%Y%m%d_%H%M%S_%f.hl7",
                description="File name pattern with timestamp placeholders",
            ),
            SettingDefinition(
                key="overwrite",
                label="Overwrite Existing",
                type="boolean",
                required=False,
                default=False,
            ),
        ],
        host_settings=[],
    ),
    
    # Transform Process
    ItemTypeDefinition(
        type="transform.process",
        name="Transform Process",
        description="Transforms messages using DTL or custom logic",
        category=ItemType.PROCESS,
        iris_class_name="EnsLib.MsgRouter.TransformProcess",
        li_class_name="li.hosts.transform.TransformProcess",
        adapter_settings=[],
        host_settings=[
            SettingDefinition(
                key="transformClass",
                label="Transform Class",
                type="string",
                required=True,
                description="Name of the transform class to apply",
            ),
            SettingDefinition(
                key="targetConfigNames",
                label="Target Items",
                type="multiselect",
                required=True,
            ),
        ],
    ),
    
    # Passthrough Process
    ItemTypeDefinition(
        type="passthrough.process",
        name="Passthrough Process",
        description="Passes messages through without modification",
        category=ItemType.PROCESS,
        iris_class_name="Ens.BusinessProcess",
        li_class_name="li.hosts.passthrough.PassthroughProcess",
        adapter_settings=[],
        host_settings=[
            SettingDefinition(
                key="targetConfigNames",
                label="Target Items",
                type="multiselect",
                required=True,
            ),
        ],
    ),
]


def setup_item_type_routes(app: web.Application, db_pool=None) -> None:
    """Set up item type registry routes."""
    
    async def list_item_types(request: web.Request) -> web.Response:
        """List all available item types."""
        category = request.query.get("category")
        
        types = ITEM_TYPE_REGISTRY
        if category:
            types = [t for t in types if t.category.value == category]
        
        response = ItemTypeRegistryResponse(item_types=types)
        return web.json_response(response.model_dump(mode='json'))
    
    async def get_item_type(request: web.Request) -> web.Response:
        """Get item type by type identifier."""
        type_id = request.match_info["type_id"]
        
        for item_type in ITEM_TYPE_REGISTRY:
            if item_type.type == type_id:
                return web.json_response(item_type.model_dump(mode='json'))
        
        return web.json_response({"error": f"Item type '{type_id}' not found"}, status=404)
    
    async def get_item_type_by_class(request: web.Request) -> web.Response:
        """Get item type by IRIS or LI class name."""
        class_name = request.query.get("class_name")
        if not class_name:
            return web.json_response({"error": "class_name query parameter required"}, status=400)
        
        for item_type in ITEM_TYPE_REGISTRY:
            if item_type.iris_class_name == class_name or item_type.li_class_name == class_name:
                return web.json_response(item_type.model_dump(mode='json'))
        
        return web.json_response({"error": f"Item type for class '{class_name}' not found"}, status=404)
    
    # Register routes
    app.router.add_get("/api/item-types", list_item_types)
    app.router.add_get("/api/item-types/by-class", get_item_type_by_class)
    app.router.add_get("/api/item-types/{type_id}", get_item_type)
