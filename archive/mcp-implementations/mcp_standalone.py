#!/usr/bin/env python3
"""
Standalone MCP server for OpenMemory that runs via stdio
This script can be run directly by Cursor MCP configuration
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, Optional

# Import OpenMemory dependencies
from app.utils.memory import get_memory_client

# Import MCP dependencies
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration from environment
USER_ID = os.getenv("USER_ID", "drj")
CLIENT_NAME = os.getenv("CLIENT_NAME", "cursor")
RUN_ID = os.getenv("RUN_ID", "")
# For project isolation, we'll use agent_id in format: client_name-project_name
BASE_AGENT_ID = os.getenv("AGENT_ID", CLIENT_NAME)


class ProjectDetector:
    """Automatically detect project context from environment"""

    def __init__(self):
        self.project_name = self._detect_project_name()
        self.branch_name = self._detect_branch_name()

    def _detect_project_name(self) -> str:
        """Detect project name from git remote or directory"""
        try:
            # Try to get git repository name
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                remote_url = result.stdout.strip()
                if remote_url:
                    # Extract repo name from URL
                    return os.path.basename(remote_url.replace(".git", ""))
        except Exception:
            pass

        # Fallback to directory name
        return os.path.basename(os.getcwd())

    def _detect_branch_name(self) -> Optional[str]:
        """Detect current git branch (excluding main/master)"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                # Only use branch as run_id if it's not main/master
                if branch and branch not in ["main", "master"]:
                    return branch
        except Exception:
            pass
        return None


class StandaloneMCPServer:
    """Standalone MCP server for OpenMemory"""

    def __init__(self):
        self.server = Server("openmemory")
        self.project_detector = ProjectDetector()

        # Determine project context
        self.project_name = self.project_detector.project_name
        self.branch_name = self.project_detector.branch_name

        # Create project-specific agent_id for isolation
        self.agent_id = f"{BASE_AGENT_ID}-{self.project_name}"

        # Use branch name as run_id if available and not set in environment
        self.run_id = RUN_ID or self.branch_name or ""

        logger.info(
            f"Project context: name={self.project_name}, branch={self.branch_name}"
        )
        logger.info(
            f"Memory context: user_id={USER_ID}, agent_id={self.agent_id}, run_id={self.run_id}"
        )

        self._setup_handlers()

    def _get_memory_context(self) -> Dict[str, Any]:
        """Get memory context with project parameters"""
        context = {
            "user_id": USER_ID,
            "agent_id": self.agent_id,
            "metadata": {
                "client_name": CLIENT_NAME,
                "project_name": self.project_name,
                "mcp_client": CLIENT_NAME,
                "base_agent_id": BASE_AGENT_ID,
            },
        }

        # Add run_id if available
        if self.run_id:
            context["run_id"] = self.run_id
            context["metadata"]["run_id"] = self.run_id
            context["metadata"]["branch"] = self.run_id

        return context

    def _setup_handlers(self):
        """Set up MCP handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="add_memories",
                    description="Add a new memory with automatic project context detection",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to remember",
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Optional agent ID override (defaults to project-specific agent)",
                            },
                            "run_id": {
                                "type": "string",
                                "description": "Optional run/session ID override (auto-detected if not provided)",
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="search_memory",
                    description="Search through stored memories with project context filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Optional agent ID to filter results",
                            },
                            "run_id": {
                                "type": "string",
                                "description": "Optional run/session ID to filter results",
                            },
                            "cross_project": {
                                "type": "boolean",
                                "description": "Whether to search across all projects for this user (default: false)",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="list_memories",
                    description="List memories with project context filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Optional agent ID to filter results",
                            },
                            "run_id": {
                                "type": "string",
                                "description": "Optional run/session ID to filter results",
                            },
                            "cross_project": {
                                "type": "boolean",
                                "description": "Whether to list memories across all projects for this user (default: false)",
                            },
                        },
                    },
                ),
                Tool(
                    name="delete_all_memories",
                    description="Delete all memories with project context filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Optional agent ID to filter deletion",
                            },
                            "run_id": {
                                "type": "string",
                                "description": "Optional run/session ID to filter deletion",
                            },
                            "confirm": {
                                "type": "boolean",
                                "description": "Confirmation flag (must be true to proceed)",
                            },
                        },
                        "required": ["confirm"],
                    },
                ),
                Tool(
                    name="get_project_context",
                    description="Get current project context information",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any]
        ) -> list[TextContent]:
            """Handle tool calls."""
            try:
                memory_client = get_memory_client()
                if not memory_client:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Memory system is currently unavailable.",
                        )
                    ]

                if name == "add_memories":
                    text = arguments.get("text")
                    if not text:
                        return [
                            TextContent(
                                type="text", text="Error: text parameter is required"
                            )
                        ]

                    # Get context with overrides
                    context = self._get_memory_context()
                    if arguments.get("agent_id"):
                        context["agent_id"] = arguments["agent_id"]
                        context["metadata"]["agent_id"] = arguments["agent_id"]
                    if arguments.get("run_id"):
                        context["run_id"] = arguments["run_id"]
                        context["metadata"]["run_id"] = arguments["run_id"]

                    result = memory_client.add(text, **context)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "search_memory":
                    query = arguments.get("query")
                    if not query:
                        return [
                            TextContent(
                                type="text", text="Error: query parameter is required"
                            )
                        ]

                    # Build search context
                    search_params = {"user_id": USER_ID}

                    if not arguments.get("cross_project", False):
                        # Default to current project unless cross_project is explicitly requested
                        search_params["agent_id"] = arguments.get(
                            "agent_id", self.agent_id
                        )

                    if arguments.get("run_id"):
                        search_params["run_id"] = arguments["run_id"]

                    results = memory_client.search(query, **search_params)

                    # Add context info to results
                    if isinstance(results, dict):
                        context_info = {
                            "search_context": {
                                "project_name": self.project_name,
                                "branch_name": self.branch_name,
                                "agent_id": search_params.get("agent_id"),
                                "search_params": search_params,
                                "cross_project": arguments.get("cross_project", False),
                            }
                        }
                        results["context"] = context_info

                    return [
                        TextContent(type="text", text=json.dumps(results, indent=2))
                    ]

                elif name == "list_memories":
                    # Build list context
                    list_params = {"user_id": USER_ID}

                    if not arguments.get("cross_project", False):
                        # Default to current project unless cross_project is explicitly requested
                        list_params["agent_id"] = arguments.get(
                            "agent_id", self.agent_id
                        )

                    if arguments.get("run_id"):
                        list_params["run_id"] = arguments["run_id"]

                    results = memory_client.get_all(**list_params)

                    # Add context info to results
                    if isinstance(results, dict):
                        context_info = {
                            "list_context": {
                                "project_name": self.project_name,
                                "branch_name": self.branch_name,
                                "agent_id": list_params.get("agent_id"),
                                "list_params": list_params,
                                "cross_project": arguments.get("cross_project", False),
                            }
                        }
                        results["context"] = context_info

                    return [
                        TextContent(type="text", text=json.dumps(results, indent=2))
                    ]

                elif name == "delete_all_memories":
                    confirm = arguments.get("confirm", False)
                    if not confirm:
                        return [
                            TextContent(
                                type="text",
                                text="Error: confirm parameter must be true to proceed with deletion",
                            )
                        ]

                    # Build delete context
                    delete_params = {"user_id": USER_ID}

                    if arguments.get("agent_id"):
                        delete_params["agent_id"] = arguments["agent_id"]
                    elif arguments.get("run_id"):
                        delete_params["run_id"] = arguments["run_id"]
                    else:
                        # Default to current project context
                        delete_params["agent_id"] = self.agent_id

                    result = memory_client.delete_all(**delete_params)
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]

                elif name == "get_project_context":
                    context_info = {
                        "project_name": self.project_name,
                        "branch_name": self.branch_name,
                        "user_id": USER_ID,
                        "client_name": CLIENT_NAME,
                        "base_agent_id": BASE_AGENT_ID,
                        "agent_id": self.agent_id,
                        "run_id": self.run_id,
                        "memory_context": self._get_memory_context(),
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(context_info, indent=2)
                        )
                    ]

                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown tool: {name}",
                        )
                    ]
            except Exception as e:
                logger.error(f"Error in handle_call_tool: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error: {str(e)}",
                    )
                ]

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="openmemory",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main function to run the MCP server."""
    server = StandaloneMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
