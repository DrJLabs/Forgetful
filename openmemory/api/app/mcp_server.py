"""
MCP Server for OpenMemory with Agent 4 Operational Excellence Integration

This module implements an MCP (Model Context Protocol) server with:
- Agent 4 structured logging with correlation IDs
- Advanced error handling with classification
- Resilience patterns for memory operations
- Performance monitoring and caching
"""

import contextvars
import datetime
import json
import logging
import os
import uuid

from app.database import SessionLocal
from app.models import Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from shared.caching import cache_manager, cached
from shared.errors import (
    ExternalServiceError,
    NotFoundError,
    ValidationError,
    create_error_response,
    handle_error,
)

# Agent 4 Integration - Structured Logging and Error Handling
from shared.logging_system import (
    CorrelationContextManager,
    get_logger,
    performance_logger,
)
from shared.resilience import RetryPolicy, resilient, retry

# Replace standard logging with structured logging
logger = get_logger("mcp_server")

# Load environment variables
load_dotenv()

# Initialize MCP
mcp = FastMCP("mem0-mcp-server")


# Agent 4 Enhanced Memory Client Access
@retry(RetryPolicy(max_attempts=2, initial_delay=0.5))
def get_memory_client_safe():
    """Get memory client with Agent 4 resilience patterns"""
    try:
        with performance_logger.timer("memory_client_access"):
            client = get_memory_client()
            if not client:
                raise ExternalServiceError(
                    "Memory client unavailable", service_name="mem0_client"
                )
            return client
    except Exception as e:
        structured_error = handle_error(e, {"operation": "memory_client_access"})
        logger.error("Memory client access failed", error=structured_error.to_dict())
        return None


# Context variables for user_id and client_name
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

# Create a router for MCP endpoints
mcp_router = APIRouter(prefix="/mcp")

# Initialize SSE transport
sse = SseServerTransport("/mcp/messages/")


@mcp.tool(
    description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something."
)
async def add_memories(text: str) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)

    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Check if app is active
            if not app.is_active:
                return f"Error: App {app.name} is currently paused on OpenMemory. Cannot create new memories."

            response = memory_client.add(
                text,
                user_id=uid,
                metadata={
                    "source_app": "openmemory",
                    "mcp_client": client_name,
                },
            )

            # Process the response and update database
            if isinstance(response, dict) and "results" in response:
                for result in response["results"]:
                    memory_id = uuid.UUID(result["id"])
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()

                    if result["event"] == "ADD":
                        if not memory:
                            memory = Memory(
                                id=memory_id,
                                user_id=user.id,
                                app_id=app.id,
                                content=result["memory"],
                                state=MemoryState.active,
                            )
                            db.add(memory)
                        else:
                            memory.state = MemoryState.active
                            memory.content = result["memory"]

                        # Create history entry
                        history = MemoryStatusHistory(
                            memory_id=memory_id,
                            changed_by=user.id,
                            old_state=MemoryState.deleted if memory else None,
                            new_state=MemoryState.active,
                        )
                        db.add(history)

                    elif result["event"] == "DELETE":
                        if memory:
                            memory.state = MemoryState.deleted
                            memory.deleted_at = datetime.datetime.now(datetime.UTC)
                            # Create history entry
                            history = MemoryStatusHistory(
                                memory_id=memory_id,
                                changed_by=user.id,
                                old_state=MemoryState.active,
                                new_state=MemoryState.deleted,
                            )
                            db.add(history)

                db.commit()

            return response
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(
    description="Search through stored memories. This method is called EVERYTIME the user asks anything."
)
async def search_memory(query: str) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Get accessible memory IDs based on ACL
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [
                memory.id
                for memory in user_memories
                if check_memory_access_permissions(db, memory, app.id)
            ]

            # Use mem0's search method instead of direct vector store access
            search_results = memory_client.search(query, user_id=uid, limit=10)

            # Filter results based on accessible memory IDs
            memories = []
            if isinstance(search_results, dict) and "results" in search_results:
                for result in search_results["results"]:
                    if "id" in result:
                        memory_id = uuid.UUID(result["id"])
                        if memory_id in accessible_memory_ids:
                            memories.append(
                                {
                                    "id": result["id"],
                                    "memory": result.get("memory", ""),
                                    "hash": result.get("hash"),
                                    "created_at": result.get("created_at"),
                                    "updated_at": result.get("updated_at"),
                                    "score": result.get("score", 0.0),
                                }
                            )
            else:
                # Handle list format
                for result in search_results:
                    if "id" in result:
                        memory_id = uuid.UUID(result["id"])
                        if memory_id in accessible_memory_ids:
                            memories.append(
                                {
                                    "id": result["id"],
                                    "memory": result.get("memory", ""),
                                    "hash": result.get("hash"),
                                    "created_at": result.get("created_at"),
                                    "updated_at": result.get("updated_at"),
                                    "score": result.get("score", 0.0),
                                }
                            )

            # Log memory access for each memory found
            if isinstance(memories, dict) and "results" in memories:
                print(f"Memories: {memories}")
                for memory_data in memories["results"]:
                    if "id" in memory_data:
                        memory_id = uuid.UUID(memory_data["id"])
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="search",
                            metadata_={
                                "query": query,
                                "score": memory_data.get("score"),
                                "hash": memory_data.get("hash"),
                            },
                        )
                        db.add(access_log)
                db.commit()
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory["id"])
                    # Create access log entry
                    access_log = MemoryAccessLog(
                        memory_id=memory_id,
                        app_id=app.id,
                        access_type="search",
                        metadata_={
                            "query": query,
                            "score": memory.get("score"),
                            "hash": memory.get("hash"),
                        },
                    )
                    db.add(access_log)
                db.commit()
            return json.dumps(memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(e)
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories in the user's memory")
async def list_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Get all memories
            memories = memory_client.get_all(user_id=uid)
            filtered_memories = []

            # Filter memories based on permissions
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [
                memory.id
                for memory in user_memories
                if check_memory_access_permissions(db, memory, app.id)
            ]
            if isinstance(memories, dict) and "results" in memories:
                for memory_data in memories["results"]:
                    if "id" in memory_data:
                        memory_id = uuid.UUID(memory_data["id"])
                        if memory_id in accessible_memory_ids:
                            # Create access log entry
                            access_log = MemoryAccessLog(
                                memory_id=memory_id,
                                app_id=app.id,
                                access_type="list",
                                metadata_={"hash": memory_data.get("hash")},
                            )
                            db.add(access_log)
                            filtered_memories.append(memory_data)
                db.commit()
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory["id"])
                    memory_obj = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory_obj and check_memory_access_permissions(
                        db, memory_obj, app.id
                    ):
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="list",
                            metadata_={"hash": memory.get("hash")},
                        )
                        db.add(access_log)
                        filtered_memories.append(memory)
                db.commit()
            return json.dumps(filtered_memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Delete all memories in the user's memory")
async def delete_all_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [
                memory.id
                for memory in user_memories
                if check_memory_access_permissions(db, memory, app.id)
            ]

            # delete the accessible memories only
            for memory_id in accessible_memory_ids:
                try:
                    memory_client.delete(memory_id)
                except Exception as delete_error:
                    logging.warning(
                        f"Failed to delete memory {memory_id} from vector store: {delete_error}"
                    )

            # Update each memory's state and create history entries
            now = datetime.datetime.now(datetime.UTC)
            for memory_id in accessible_memory_ids:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                # Update memory state
                memory.state = MemoryState.deleted
                memory.deleted_at = now

                # Create history entry
                history = MemoryStatusHistory(
                    memory_id=memory_id,
                    changed_by=user.id,
                    old_state=MemoryState.active,
                    new_state=MemoryState.deleted,
                )
                db.add(history)

                # Create access log entry
                access_log = MemoryAccessLog(
                    memory_id=memory_id,
                    app_id=app.id,
                    access_type="delete_all",
                    metadata_={"operation": "bulk_delete"},
                )
                db.add(access_log)

            db.commit()
            return "Successfully deleted all memories"
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    """Handle SSE connections for a specific user and client"""
    # Extract user_id and client_name from path parameters
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    client_name = request.path_params.get("client_name")
    client_token = client_name_var.set(client_name or "")

    try:
        # Handle SSE connection
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        # Clean up context variables
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)


@mcp_router.post("/messages/")
async def handle_get_message(request: Request):
    return await handle_post_message(request)


@mcp_router.post("/{client_name}/sse/{user_id}/messages/")
async def handle_post_message(request: Request):
    return await handle_post_message(request)


async def handle_post_message(request: Request):
    """Handle POST messages for SSE"""
    try:
        body = await request.body()

        # Create a simple receive function that returns the body
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        # Create a simple send function that does nothing
        async def send(message):
            return {}

        # Call handle_post_message with the correct arguments
        await sse.handle_post_message(request.scope, receive, send)

        # Return a success response
        return {"status": "ok"}
    finally:
        pass
        # Clean up context variable
        # client_name_var.reset(client_token)


def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = f"mem0-mcp-server"

    # Include MCP router in the FastAPI app
    app.include_router(mcp_router)
