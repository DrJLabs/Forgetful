#!/usr/bin/env python3
"""
Standalone MCP server for OpenMemory that runs via stdio
This script can be run directly by Cursor MCP configuration
"""

import os
import sys
import asyncio
import logging
import json
from typing import Any, Dict

# Import MCP dependencies
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import OpenMemory dependencies
from app.utils.memory import get_memory_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configuration from environment
USER_ID = os.getenv("USER_ID", "drj")
CLIENT_NAME = os.getenv("CLIENT_NAME", "cursor")


class OpenMemoryMCPServer:
    def __init__(self):
        self.server = Server("mem0-mcp-server")
        self.setup_handlers()
        
    def setup_handlers(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """Return the list of available tools."""
            return [
                Tool(
                    name="add_memories",
                    description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to remember"
                            }
                        },
                        "required": ["text"]
                    }
                ),
                Tool(
                    name="search_memory",
                    description="Search through stored memories. This method is called EVERYTIME the user asks anything.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_memories",
                    description="List all memories in the user's memory",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="delete_all_memories",
                    description="Delete all memories in the user's memory",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                memory_client = get_memory_client()
                if not memory_client:
                    return [TextContent(type="text", text="Error: Memory system is currently unavailable.")]
                
                if name == "add_memories":
                    text = arguments.get("text")
                    if not text:
                        return [TextContent(type="text", text="Error: text parameter is required")]
                    
                    result = memory_client.add(
                        text,
                        user_id=USER_ID,
                        metadata={
                            "source_app": "openmemory",
                            "mcp_client": CLIENT_NAME,
                        }
                    )
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
                elif name == "search_memory":
                    query = arguments.get("query")
                    if not query:
                        return [TextContent(type="text", text="Error: query parameter is required")]
                    
                    results = memory_client.search(query, user_id=USER_ID, limit=10)
                    return [TextContent(type="text", text=json.dumps(results, indent=2))]
                
                elif name == "list_memories":
                    memories = memory_client.get_all(user_id=USER_ID)
                    return [TextContent(type="text", text=json.dumps(memories, indent=2))]
                
                elif name == "delete_all_memories":
                    # Get all memories first
                    memories = memory_client.get_all(user_id=USER_ID)
                    deleted_count = 0
                    
                    if isinstance(memories, dict) and 'results' in memories:
                        for memory in memories['results']:
                            try:
                                memory_client.delete(memory['id'])
                                deleted_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete memory {memory['id']}: {e}")
                    else:
                        for memory in memories:
                            try:
                                memory_client.delete(memory['id'])
                                deleted_count += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete memory {memory['id']}: {e}")
                    
                    return [TextContent(type="text", text=f"Deleted {deleted_count} memories")]
                
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def run(self):
        """Run the MCP server."""
        options = InitializationOptions(
            server_name="mem0-mcp-server",
            server_version="1.0.0",
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                options,
            )


async def main():
    """Main entry point."""
    server = OpenMemoryMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 