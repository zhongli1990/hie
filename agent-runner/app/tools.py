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


# Standard tools + HIE-specific tools
TOOLS = [
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
    # HIE-specific tools
    {
        "name": "hie_list_projects",
        "description": "List all HIE projects in a workspace via the Manager API",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "description": "The workspace UUID"
                }
            },
            "required": ["workspace_id"]
        }
    },
    {
        "name": "hie_get_project",
        "description": "Get detailed HIE project configuration including items, connections, and routing rules",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "description": "The workspace UUID"
                },
                "project_id": {
                    "type": "string",
                    "description": "The project UUID"
                }
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    {
        "name": "hie_create_item",
        "description": "Create a new item (service, process, or operation) in an HIE project",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "description": "The workspace UUID"},
                "project_id": {"type": "string", "description": "The project UUID"},
                "name": {"type": "string", "description": "Item name (e.g. 'ADT_Receiver')"},
                "item_type": {"type": "string", "enum": ["service", "process", "operation"], "description": "Item type"},
                "class_name": {"type": "string", "description": "Implementation class (e.g. 'Engine.li.hosts.hl7.HL7TCPService')"},
                "adapter_settings": {"type": "object", "description": "Adapter-specific settings (e.g. port, host)"},
                "host_settings": {"type": "object", "description": "Host-specific settings"}
            },
            "required": ["workspace_id", "project_id", "name", "item_type", "class_name"]
        }
    },
    {
        "name": "hie_create_connection",
        "description": "Create a connection between two items in an HIE project",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"},
                "source_item_id": {"type": "string", "description": "Source item UUID"},
                "target_item_id": {"type": "string", "description": "Target item UUID"},
                "connection_type": {"type": "string", "enum": ["standard", "error", "async"], "description": "Connection type"}
            },
            "required": ["workspace_id", "project_id", "source_item_id", "target_item_id"]
        }
    },
    {
        "name": "hie_deploy_project",
        "description": "Deploy and start an HIE project",
        "input_schema": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "project_id": {"type": "string"},
                "start_after_deploy": {"type": "boolean", "default": True}
            },
            "required": ["workspace_id", "project_id"]
        }
    },
    {
        "name": "hie_test_item",
        "description": "Send a test message to an HIE item",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "item_name": {"type": "string"},
                "message": {"type": "string", "description": "Test message content (e.g. HL7 message)"}
            },
            "required": ["project_id", "item_name"]
        }
    },
    {
        "name": "hie_list_item_types",
        "description": "List available HIE item types (services, processes, operations) from the registry",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["service", "process", "operation"],
                    "description": "Filter by category"
                }
            }
        }
    },
]


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

        # HIE-specific tools
        elif tool_name == "hie_list_projects":
            ws_id = tool_input["workspace_id"]
            return _hie_api_call("GET", f"/api/workspaces/{ws_id}/projects")

        elif tool_name == "hie_get_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            return _hie_api_call("GET", f"/api/workspaces/{ws_id}/projects/{proj_id}")

        elif tool_name == "hie_create_item":
            ws_id = tool_input.pop("workspace_id")
            proj_id = tool_input.pop("project_id")
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/items", tool_input)

        elif tool_name == "hie_create_connection":
            ws_id = tool_input.pop("workspace_id")
            proj_id = tool_input.pop("project_id")
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/connections", tool_input)

        elif tool_name == "hie_deploy_project":
            ws_id = tool_input["workspace_id"]
            proj_id = tool_input["project_id"]
            start = tool_input.get("start_after_deploy", True)
            return _hie_api_call("POST", f"/api/workspaces/{ws_id}/projects/{proj_id}/deploy", {"start_after_deploy": start})

        elif tool_name == "hie_test_item":
            proj_id = tool_input["project_id"]
            item_name = tool_input["item_name"]
            message = tool_input.get("message")
            body = {"message": message} if message else None
            return _hie_api_call("POST", f"/api/projects/{proj_id}/items/{item_name}/test", body)

        elif tool_name == "hie_list_item_types":
            category = tool_input.get("category", "")
            query = f"?category={category}" if category else ""
            return _hie_api_call("GET", f"/api/item-types{query}")

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"success": False, "error": str(e)}
