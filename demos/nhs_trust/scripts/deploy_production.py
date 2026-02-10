#!/usr/bin/env python3
"""
NHS Acute Trust Production Deployment Script

This script demonstrates how the Portal UI interacts with the Manager API
to deploy a complete NHS acute trust integration production.

Everything is configuration-driven - this script just makes API calls
with the configuration data. In production, users would fill out forms
in the Portal UI, and the UI would make these exact same API calls.

Usage:
    python deploy_production.py --api-url http://localhost:8081 --config nhs_acute_trust_production.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class ProductionDeployer:
    """Deploys NHS Trust production via Manager API."""

    def __init__(self, api_url: str, config_path: Path):
        self.api_url = api_url.rstrip("/")
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.workspace_id: str = ""
        self.project_id: str = ""

    async def load_configuration(self) -> None:
        """Load production configuration from JSON file."""
        logger.info("loading_configuration", path=str(self.config_path))

        with open(self.config_path) as f:
            self.config = json.load(f)

        logger.info(
            "configuration_loaded",
            workspace=self.config["workspace"]["name"],
            project=self.config["project"]["name"],
            items=len(self.config["items"]),
            connections=len(self.config["connections"])
        )

    async def create_workspace(self, session: aiohttp.ClientSession) -> None:
        """
        Create workspace via Manager API.

        Portal UI: Admin → Workspaces → "Create Workspace" button → Form
        """
        workspace_data = self.config["workspace"]

        logger.info("creating_workspace", name=workspace_data["name"])

        url = f"{self.api_url}/api/workspaces"
        async with session.post(url, json=workspace_data) as resp:
            if resp.status == 201:
                result = await resp.json()
                self.workspace_id = result["id"]
                logger.info("workspace_created", id=self.workspace_id, name=workspace_data["name"])
            elif resp.status == 409:
                # Workspace already exists, get it
                logger.info("workspace_exists", name=workspace_data["name"])
                async with session.get(f"{url}?name={workspace_data['name']}") as get_resp:
                    workspaces = await get_resp.json()
                    if workspaces:
                        self.workspace_id = workspaces[0]["id"]
            else:
                error = await resp.text()
                raise Exception(f"Failed to create workspace: {resp.status} - {error}")

    async def create_project(self, session: aiohttp.ClientSession) -> None:
        """
        Create project via Manager API.

        Portal UI: Workspace → Projects → "Create Project" button → Form
        """
        project_data = {
            **self.config["project"],
            "workspace_id": self.workspace_id
        }

        logger.info("creating_project", name=project_data["name"])

        url = f"{self.api_url}/api/projects"
        async with session.post(url, json=project_data) as resp:
            if resp.status == 201:
                result = await resp.json()
                self.project_id = result["id"]
                logger.info("project_created", id=self.project_id, name=project_data["name"])
            elif resp.status == 409:
                # Project already exists
                logger.info("project_exists", name=project_data["name"])
                async with session.get(f"{url}?workspace_id={self.workspace_id}") as get_resp:
                    projects = await get_resp.json()
                    for proj in projects:
                        if proj["name"] == project_data["name"]:
                            self.project_id = proj["id"]
                            break
            else:
                error = await resp.text()
                raise Exception(f"Failed to create project: {resp.status} - {error}")

    async def create_items(self, session: aiohttp.ClientSession) -> None:
        """
        Create all items via Manager API.

        Portal UI: Project → Items → "Add Item" button → Select type → Fill form

        Each item configuration represents what a user fills out in Portal UI forms:
        - Name, Display Name, Enabled checkbox
        - Adapter Settings tab (port, IP, file path, etc.)
        - Host Settings tab (targets, ACK mode, etc.)
        - Performance & Execution tab (Phase 2: execution mode, worker count)
        - Queue Configuration tab (Phase 2: queue type, size, overflow)
        - Reliability & Auto-Restart tab (Phase 2: restart policy, max restarts)
        - Messaging tab (Phase 2: messaging pattern, timeout)
        """
        logger.info("creating_items", count=len(self.config["items"]))

        url = f"{self.api_url}/api/projects/{self.project_id}/items"

        for item in self.config["items"]:
            logger.info(
                "creating_item",
                name=item["name"],
                type=item["type"],
                execution_mode=item["host_settings"].get("ExecutionMode", "async"),
                queue_type=item["host_settings"].get("QueueType", "fifo")
            )

            # Prepare item data for Manager API
            item_data = {
                "name": item["name"],
                "display_name": item["display_name"],
                "item_type": item["item_type"],
                "class_name": item.get("class_name", f"Engine.li.hosts.{item['type'].replace('.', '_')}"),
                "enabled": item["enabled"],
                "pool_size": item["pool_size"],
                "comment": item.get("comment", ""),
                "adapter_settings": item["adapter_settings"],
                "host_settings": item["host_settings"]
            }

            async with session.post(url, json=item_data) as resp:
                if resp.status == 201:
                    result = await resp.json()
                    logger.info("item_created", name=item["name"], id=result["id"])
                elif resp.status == 409:
                    logger.info("item_exists", name=item["name"])
                else:
                    error = await resp.text()
                    logger.error("item_creation_failed", name=item["name"], error=error)
                    raise Exception(f"Failed to create item {item['name']}: {resp.status} - {error}")

    async def create_connections(self, session: aiohttp.ClientSession) -> None:
        """
        Create connections between items via Manager API.

        Portal UI: Project → Visual Workflow Designer → Drag lines between items

        Each connection represents a visual line drawn in the workflow designer.
        """
        logger.info("creating_connections", count=len(self.config["connections"]))

        url = f"{self.api_url}/api/projects/{self.project_id}/connections"

        for conn in self.config["connections"]:
            logger.info(
                "creating_connection",
                from_item=conn["from"],
                to_item=conn["to"],
                description=conn.get("description", "")
            )

            conn_data = {
                "from_item": conn["from"],
                "to_item": conn["to"],
                "condition": conn.get("condition", ""),
                "description": conn.get("description", "")
            }

            async with session.post(url, json=conn_data) as resp:
                if resp.status == 201:
                    result = await resp.json()
                    logger.info("connection_created", id=result["id"])
                elif resp.status == 409:
                    logger.info("connection_exists")
                else:
                    error = await resp.text()
                    logger.warning("connection_creation_failed", error=error)

    async def deploy_production(self, session: aiohttp.ClientSession) -> None:
        """
        Deploy production via Manager API.

        Portal UI: Project → "Deploy" button

        This tells Manager API to:
        1. Load configuration from PostgreSQL
        2. Instantiate ProductionEngine
        3. For each item, instantiate Host class with configuration
        4. Register hosts with ServiceRegistry
        5. Prepare for start (but don't start yet)
        """
        logger.info("deploying_production", project_id=self.project_id)

        url = f"{self.api_url}/api/projects/{self.project_id}/deploy"

        async with session.post(url) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info("production_deployed", result=result)
            else:
                error = await resp.text()
                raise Exception(f"Failed to deploy production: {resp.status} - {error}")

    async def start_production(self, session: aiohttp.ClientSession) -> None:
        """
        Start production via Manager API.

        Portal UI: Project → "Start" button

        This tells Manager API to:
        1. Call ProductionEngine.start()
        2. Start all enabled items
        3. Each item starts its workers (processes/threads)
        4. TCP listeners start accepting connections
        5. File watchers start monitoring directories
        6. ServiceRegistry becomes active
        """
        logger.info("starting_production", project_id=self.project_id)

        url = f"{self.api_url}/api/projects/{self.project_id}/start"

        async with session.post(url) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info("production_started", result=result)
                logger.info(
                    "production_running",
                    message="Portal UI would now show: Status = RUNNING 🟢"
                )
            else:
                error = await resp.text()
                raise Exception(f"Failed to start production: {resp.status} - {error}")

    async def get_production_status(self, session: aiohttp.ClientSession) -> None:
        """
        Get production status via Manager API.

        Portal UI: Dashboard → Real-time status display
        """
        logger.info("checking_production_status", project_id=self.project_id)

        url = f"{self.api_url}/api/projects/{self.project_id}/status"

        async with session.get(url) as resp:
            if resp.status == 200:
                status = await resp.json()
                logger.info(
                    "production_status",
                    state=status.get("state", "UNKNOWN"),
                    items_running=status.get("items_running", 0),
                    items_total=status.get("items_total", 0),
                    messages_processed=status.get("messages_processed", 0)
                )
            else:
                logger.warning("status_unavailable", status=resp.status)

    async def deploy(self) -> None:
        """
        Execute full deployment workflow.

        This is what Portal UI does behind the scenes when user:
        1. Fills out workspace form → POST /api/workspaces
        2. Fills out project form → POST /api/projects
        3. Adds items via forms → POST /api/projects/{id}/items (for each item)
        4. Draws connections in visual designer → POST /api/projects/{id}/connections
        5. Clicks "Deploy & Start" → POST /api/projects/{id}/deploy + /start
        """
        await self.load_configuration()

        async with aiohttp.ClientSession() as session:
            try:
                # Step 1: Create Workspace
                await self.create_workspace(session)

                # Step 2: Create Project
                await self.create_project(session)

                # Step 3: Create Items
                await self.create_items(session)

                # Step 4: Create Connections
                await self.create_connections(session)

                # Step 5: Deploy
                await self.deploy_production(session)

                # Step 6: Start
                await self.start_production(session)

                # Step 7: Verify Status
                await asyncio.sleep(2)  # Give it a moment to start
                await self.get_production_status(session)

                logger.info(
                    "deployment_complete",
                    workspace=self.config["workspace"]["name"],
                    project=self.config["project"]["name"],
                    message="Production is now running! Check Portal UI dashboard for real-time metrics."
                )

            except Exception as e:
                logger.error("deployment_failed", error=str(e))
                raise


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy NHS Acute Trust integration production via Manager API"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8081",
        help="Manager API URL (default: http://localhost:8081)"
    )
    parser.add_argument(
        "--config",
        default="../config/nhs_acute_trust_production.json",
        help="Production configuration file path"
    )

    args = parser.parse_args()

    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    # Resolve config path
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path

    if not config_path.exists():
        logger.error("config_not_found", path=str(config_path))
        sys.exit(1)

    # Deploy production
    deployer = ProductionDeployer(args.api_url, config_path)
    await deployer.deploy()


if __name__ == "__main__":
    asyncio.run(main())
