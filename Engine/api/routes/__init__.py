"""
HIE API Routes

Modular route handlers for the management API.
"""

from Engine.api.routes.workspaces import setup_workspace_routes
from Engine.api.routes.projects import setup_project_routes
from Engine.api.routes.items import setup_item_routes
from Engine.api.routes.item_types import setup_item_type_routes

__all__ = [
    "setup_workspace_routes",
    "setup_project_routes",
    "setup_item_routes",
    "setup_item_type_routes",
]
