"""
OpenLI HIE Agent Runner - Tool Definitions and Execution

Tools available to the AI agent for interacting with the HIE workspace.
Includes standard file/bash tools plus HIE-specific tools for
healthcare integration configuration.
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .config import HIE_MANAGER_URL, WORKSPACES_ROOT


# ─── Standard tools ──────────────────────────────────────────────────

STANDARD_TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the working directory"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file at the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to the working directory"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "list_files",
        "description": "List files and directories at the specified path",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to the working directory"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "bash",
        "description": "Execute a bash command in the working directory",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                }
            },
            "required": ["command"]
        }
    },
]

# ─── HIE-specific tools ──────────────────────────────────────────────
#
# These tools call the HIE Manager API to manage workspaces, projects,
# items, connections, routing rules, and production lifecycle.
#
# Class Namespace Convention (enforced by ClassRegistry):
#   PROTECTED (read-only):  li.*, Engine.li.*, EnsLib.*
#   DEVELOPER (custom):     custom.*
#
# When creating items, use:
#   - Core classes:   "li.hosts.hl7.HL7TCPService" (built-in)
#   - Custom classes: "custom.nhs.NHSValidationProcess" (developer-created)
#   - IRIS aliases:   "EnsLib.HL7.Service.TCPService" (auto-resolved)
# ─────────────────────────────────────────────────────────────────────

HIE_TOOLS = [
    # ── Workspace Management ──
    {
        "name": "hie_list_workspaces",
        "description": "List all HIE workspaces",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "hie_create_workspace",
        "description": "Create a new HIE workspace (equivalent to an IRIS namespace)",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Workspace name (e.g. 'St_Thomas_Hospital')"},
                "display_name": {"type": "string", "description": "Human-readable name"},
                "description": {"type": "string", "description": "Workspace description"}
            },
            "required": ["name"]
        }
    },
    # ── Project Management ──
    {
        "name": "hie_list_projects",
        "description": "List all HIE projects in a workspace",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "The workspace UUID"}
            },
            "required": ["workspace_id"]
        }
    },
    {
        "name": "hie_create_project",
        "description": "Create a new HIE project (equivalent to an IRIS Production)",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "The workspace UUID"},
                "name": {"type": "string", "description": "Project name (e.g. 'ADT_Integration')"},
                "display_name": {"type": "string", "description": "Human-readable name"},
                "description": {"type": "string", "description": "Project description"}
            },
            "required": ["workspace_id", "name"]
        }
    },
    {
        "name": "hie_get_project",
        "description": "Get detailed HIE project configuration including items, connections, and routing rules",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "The workspace UUID"},
                "project_id": {"type": "string", "description": "The project UUID"}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    # ── Item Management ──
    {
        "name": "hie_create_item",
        "description": (
            "Create a new item (service, process, or operation) in an HIE project. "
            "Use core classes (li.hosts.hl7.HL7TCPService) for standard items, "
            "or custom.* namespace (custom.nhs.MyProcess) for developer extensions. "
            "NEVER create classes in the li.* or Engine.li.* namespaces."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "The project UUID"},
                "name": {"type": "string", "description": "Item name using dot notation (e.g. 'Cerner.PAS.Receiver')"},
                "item_type": {"type": "string", "enum": ["service", "process", "operation"], "description": "Item type"},
                "class_name": {
                    "type": "string",
                    "description": (
                        "Implementation class. Core: 'li.hosts.hl7.HL7TCPService', "
                        "'li.hosts.hl7.HL7TCPOperation', 'li.hosts.routing.HL7RoutingEngine', "
                        "'li.hosts.file.FileService', 'li.hosts.file.FileOperation'. "
                        "Custom: 'custom.nhs.NHSValidationProcess' (must start with 'custom.'). "
                        "IRIS aliases also work: 'EnsLib.HL7.Service.TCPService'."
                    )
                },
                "enabled": {"type": "boolean", "description": "Whether the item is enabled (default: true)"},
                "pool_size": {"type": "integer", "description": "Number of worker instances (default: 1)"},
                "adapter_settings": {
                    "type": "object",
                    "description": "Adapter (transport) settings: Port, IPAddress, FilePath, etc."
                },
                "host_settings": {
                    "type": "object",
                    "description": (
                        "Host (business logic) settings: TargetConfigNames, MessageSchemaCategory, "
                        "AckMode, ReplyCodeActions, ExecutionMode, QueueType, RestartPolicy, etc."
                    )
                }
            },
            "required": ["project_id", "name", "item_type", "class_name"]
        }
    },
    # ── Connection Management ──
    {
        "name": "hie_create_connection",
        "description": "Create a connection between two items in an HIE project (wires message flow)",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "The project UUID"},
                "source_item_id": {"type": "string", "description": "Source item UUID"},
                "target_item_id": {"type": "string", "description": "Target item UUID"},
                "connection_type": {
                    "type": "string",
                    "enum": ["standard", "error", "async"],
                    "description": "Connection type (default: standard)"
                }
            },
            "required": ["project_id", "source_item_id", "target_item_id"]
        }
    },
    # ── Routing Rules ──
    {
        "name": "hie_create_routing_rule",
        "description": (
            "Create a routing rule for a routing engine process. "
            "Rules evaluate conditions against HL7 message fields and route to targets. "
            "Condition syntax: {MSH-9.1} = \"ADT\" AND {MSH-9.2} IN (\"A01\",\"A02\")"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "The project UUID"},
                "name": {"type": "string", "description": "Rule name (e.g. 'Route ADT to RIS and Lab')"},
                "priority": {"type": "integer", "description": "Rule priority (lower = higher priority, default: 10)"},
                "enabled": {"type": "boolean", "description": "Whether the rule is active (default: true)"},
                "condition_expression": {
                    "type": "string",
                    "description": (
                        "Condition expression using HL7 field references. "
                        "Examples: '{MSH-9.1} = \"ADT\"', "
                        "'{MSH-9.1} = \"ORM\" AND {OBR-4} Contains \"RAD\"'"
                    )
                },
                "action": {"type": "string", "enum": ["send", "transform", "delete"], "description": "Action when matched"},
                "target_items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target item names to send to"
                },
                "transform_name": {"type": "string", "description": "Transform to apply before sending (optional)"}
            },
            "required": ["project_id", "name", "condition_expression", "action", "target_items"]
        }
    },
    # ── Production Lifecycle ──
    {
        "name": "hie_deploy_project",
        "description": "Deploy project configuration to the Engine (does not start it)",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"},
                "start_after_deploy": {"type": "boolean", "description": "Start production immediately after deploy (default: true)"}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    {
        "name": "hie_start_project",
        "description": "Start a deployed HIE project (production). All enabled items begin processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    {
        "name": "hie_stop_project",
        "description": "Stop a running HIE project (production). All items stop processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    {
        "name": "hie_project_status",
        "description": "Get the runtime status of a project including item states, queue depths, and metrics",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    # ── Testing ──
    {
        "name": "hie_test_item",
        "description": "Send a test message to an HIE item (e.g. HL7 ADT A01 to an inbound service)",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"},
                "item_name": {"type": "string", "description": "Target item name"},
                "message": {"type": "string", "description": "Test message content (HL7, FHIR JSON, etc.)"}
            },
            "required": ["workspace_id", "project_id", "item_name"]
        }
    },
    # ── Registry ──
    {
        "name": "hie_list_item_types",
        "description": (
            "List available HIE item types from the ClassRegistry. "
            "Shows core product classes (li.*) and any registered custom classes (custom.*)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["service", "process", "operation", "all"],
                    "description": "Filter by category (default: all)"
                }
            }
        }
    },
    {
        "name": "hie_reload_custom_classes",
        "description": (
            "Hot-reload custom.* classes without restarting the engine. "
            "Clears cached custom modules, re-discovers from Engine/custom/, "
            "and re-registers all @register_host / @register_transform decorators. "
            "Core li.* classes are untouched. Use after deploying new custom class files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
]

# Combined tool list
TOOLS = STANDARD_TOOLS + HIE_TOOLS


def resolve_path(working_directory: str, relative_path: str, workspaces_root: str) -> str:
    """Resolve a relative path within the working directory, ensuring it stays within bounds."""
    base = Path(working_directory).resolve()
    target = (base / relative_path).resolve()

    root = Path(workspaces_root).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Path {relative_path} escapes workspaces root")

    return str(target)


def _hie_api_call(method: str, path: str, json_body: dict | None = None) -> dict[str, Any]:
    """Make a synchronous call to the HIE Manager API."""
    url = f"{HIE_MANAGER_URL}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                resp = client.get(url)
            elif method == "POST":
                resp = client.post(url, json=json_body or {})
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if resp.status_code < 400:
                return {"success": True, "data": resp.json()}
            else:
                return {"success": False, "status": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    working_directory: str,
    workspaces_root: str
) -> dict[str, Any]:
    """Execute a tool and return the result."""
    try:
        # Standard file tools
        if tool_name == "read_file":
            path = resolve_path(working_directory, tool_input["path"], workspaces_root)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}

        elif tool_name == "write_file":
            path = resolve_path(working_directory, tool_input["path"], workspaces_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(tool_input["content"])
            return {"success": True, "message": f"Wrote {len(tool_input['content'])} bytes to {tool_input['path']}"}

        elif tool_name == "list_files":
            path = resolve_path(working_directory, tool_input["path"], workspaces_root)
            entries = []
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                entry_type = "directory" if os.path.isdir(full_path) else "file"
                entries.append({"name": entry, "type": entry_type})
            return {"success": True, "entries": entries}

        elif tool_name == "bash":
            result = subprocess.run(
                tool_input["command"],
                shell=True,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }

        # ── HIE Workspace tools ──
        elif tool_name == "hie_list_workspaces":
            return _hie_api_call("GET", "/api/workspaces")

        elif tool_name == "hie_create_workspace":
            body = {
                "name": tool_input["name"],
                "display_name": tool_input.get("display_name", tool_input["name"]),
                "description": tool_input.get("description", ""),
            }
            return _hie_api_call("POST", "/api/workspaces", body)

        # ── HIE Project tools ──
        elif tool_name == "hie_list_projects":
            ws_id = tool_input["workspace_id"]
            return _hie_api_call("GET", f"/api/workspaces/{ws_id}/projects")

        elif tool_name == "hie_create_project":
            ws_id = tool_input["workspace_id"]
            body = {
                "name": tool_input["name"],
                "display_name": tool_input.get("display_name", tool_input["name"]),
                "description": tool_input.get("description", ""),
            }
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects", body)

        elif tool_name == "hie_get_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            return _hie_api_call("GET", f"/api/workspaces/{ws_id}/projects/{proj_id}")

        # ── HIE Item tools ──
        elif tool_name == "hie_create_item":
            proj_id = tool_input["project_id"]
            body = {
                "name": tool_input["name"],
                "item_type": tool_input["item_type"],
                "class_name": tool_input["class_name"],
                "enabled": tool_input.get("enabled", True),
                "pool_size": tool_input.get("pool_size", 1),
                "adapter_settings": tool_input.get("adapter_settings", {}),
                "host_settings": tool_input.get("host_settings", {}),
            }
            return _hie_api_call("POST", f"/api/projects/{proj_id}/items", body)

        # ── HIE Connection tools ──
        elif tool_name == "hie_create_connection":
            proj_id = tool_input["project_id"]
            body = {
                "source_item_id": tool_input["source_item_id"],
                "target_item_id": tool_input["target_item_id"],
                "connection_type": tool_input.get("connection_type", "standard"),
            }
            return _hie_api_call("POST", f"/api/projects/{proj_id}/connections", body)

        # ── HIE Routing Rule tools ──
        elif tool_name == "hie_create_routing_rule":
            proj_id = tool_input["project_id"]
            body = {
                "name": tool_input["name"],
                "priority": tool_input.get("priority", 10),
                "enabled": tool_input.get("enabled", True),
                "condition_expression": tool_input["condition_expression"],
                "action": tool_input["action"],
                "target_items": tool_input["target_items"],
                "transform_name": tool_input.get("transform_name"),
            }
            return _hie_api_call("POST", f"/api/projects/{proj_id}/routing-rules", body)

        # ── HIE Production Lifecycle tools ──
        elif tool_name == "hie_deploy_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            start = tool_input.get("start_after_deploy", True)
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/deploy", {"start_after_deploy": start})

        elif tool_name == "hie_start_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/start")

        elif tool_name == "hie_stop_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/stop")

        elif tool_name == "hie_project_status":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            return _hie_api_call("GET", f"/api/workspaces/{ws_id}/projects/{proj_id}/status")

        # ── HIE Testing tools ──
        elif tool_name == "hie_test_item":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            item_name = tool_input["item_name"]
            message = tool_input.get("message")
            body = {"message": message} if message else None
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/items/{item_name}/test", body)

        # ── HIE Registry tools ──
        elif tool_name == "hie_list_item_types":
            category = tool_input.get("category", "all")
            query = f"?category={category}" if category != "all" else ""
            return _hie_api_call("GET", f"/api/item-types{query}")

        elif tool_name == "hie_reload_custom_classes":
            return _hie_api_call("POST", "/api/item-types/reload-custom")

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}
