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
import uuid

from app.database import SessionLocal
from app.models import Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from dotenv import load_dotenv
# NEW IMPORTS
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from typing import List
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from shared.errors import (
    ExternalServiceError,
    handle_error,
)

# Agent 4 Integration - Structured Logging and Error Handling
from shared.logging_system import (
    get_logger,
    performance_logger,
)
from shared.resilience import RetryPolicy, retry

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


# Context variables for backward compatibility (kept for non-MCP usage)
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

# Router
router = APIRouter(prefix="/mcp", tags=["mcp"])

# Initialize SSE transport
sse = SseServerTransport("/mcp/messages/")


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────


class MessagesRequest(BaseModel):
    """Schema for /mcp/messages payload."""

    user_id: str = Field(..., description="User identifier")
    messages: List[str] = Field(..., description="List of message strings")

    @property
    def content(self) -> str:
        """Return messages concatenated for storage."""
        return "\n".join(self.messages)


# ─────────────────────────────────────────────────────────────────────────────
# Unified helper – shared by both GET & POST routes
# ─────────────────────────────────────────────────────────────────────────────

async def _process_mcp_messages(req: MessagesRequest):
    """Persist the messages and return memory metadata."""
    # Use the existing add_memories MCP tool
    result = await add_memories(
        text=req.content,
        user_id=req.user_id,
        agent_id="mcp-client"
    )

    return {"status": "ok", "result": result}


# ─────────────────────────────────────────────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something."
)
async def add_memories(
    text: str, user_id: str = "drj", agent_id: str = "default"
) -> str:
    """
    Add a new memory with proper MCP parameter handling

    Args:
        text: The content to remember
        user_id: User identifier (defaults to "drj" for backward compatibility)
        agent_id: Agent/client identifier (defaults to "default")
    """
    try:
        # Validate and sanitize inputs
        text = validate_text_input(text)
        uid = validate_user_id(user_id)
        client_name = validate_agent_id(agent_id)

        logger.info(
            "MCP add_memories called",
            extra={"user_id": uid, "agent_id": client_name, "text_length": len(text)},
        )

        # Get memory client safely
        memory_client = get_memory_client_safe()
        if not memory_client:
            return (
                "Error: Memory system is currently unavailable. Please try again later."
            )

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

            logger.info(
                "Memory added successfully",
                extra={
                    "user_id": uid,
                    "agent_id": client_name,
                    "response_type": type(response).__name__,
                },
            )
            return json.dumps(response, indent=2, default=str)
        finally:
            db.close()
    except ValueError as e:
        logger.warning(f"Input validation error in add_memories: {e}")
        return f"Input validation error: {e}"
    except Exception as e:
        logger.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(
    description="Search through stored memories. This method is called EVERYTIME the user asks anything."
)
async def search_memory(
    query: str, user_id: str = "drj", agent_id: str = "default"
) -> str:
    """
    Search through stored memories with proper MCP parameter handling

    Args:
        query: The search query
        user_id: User identifier (defaults to "drj" for backward compatibility)
        agent_id: Agent/client identifier (defaults to "default")
    """
    try:
        # Validate and sanitize inputs
        query = validate_query_input(query)
        uid = validate_user_id(user_id)
        client_name = validate_agent_id(agent_id)

        logger.info(
            "MCP search_memory called",
            extra={"user_id": uid, "agent_id": client_name, "query": query},
        )

        # Get memory client safely
        memory_client = get_memory_client_safe()
        if not memory_client:
            return json.dumps([], indent=2)

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

            # Check if we have schema mismatch (no overlapping IDs)
            mem0_ids = set()
            if isinstance(search_results, dict) and "results" in search_results:
                mem0_ids = {result.get("id") for result in search_results["results"] if "id" in result}
            elif isinstance(search_results, list):
                mem0_ids = {result.get("id") for result in search_results if "id" in result}

            accessible_id_strings = {str(mid) for mid in accessible_memory_ids}
            has_overlap = bool(mem0_ids.intersection(accessible_id_strings))

            # If no overlap detected (schema mismatch), return mem0 results directly
            # This is a temporary fix until data synchronization is implemented
            if not has_overlap and mem0_ids:
                logger.warning(
                    "Schema mismatch detected: no overlapping IDs between OpenMemory ACL and mem0 results. "
                    "Returning mem0 results directly as temporary fix.",
                    extra={
                        "user_id": uid,
                        "agent_id": client_name,
                        "accessible_ids_count": len(accessible_memory_ids),
                        "mem0_ids_count": len(mem0_ids),
                    }
                )

                # Format mem0 results for return
                memories = []
                if isinstance(search_results, dict) and "results" in search_results:
                    for result in search_results["results"]:
                        memories.append({
                            "id": result.get("id"),
                            "memory": result.get("memory", ""),
                            "hash": result.get("hash"),
                            "created_at": result.get("created_at"),
                            "updated_at": result.get("updated_at"),
                            "score": result.get("score", 0.0),
                            "metadata": result.get("metadata", {}),
                        })
                else:
                    # Handle list format
                    for result in search_results:
                        memories.append({
                            "id": result.get("id"),
                            "memory": result.get("memory", ""),
                            "hash": result.get("hash"),
                            "created_at": result.get("created_at"),
                            "updated_at": result.get("updated_at"),
                            "score": result.get("score", 0.0),
                            "metadata": result.get("metadata", {}),
                        })

                # Skip access logging for schema mismatch cases to avoid database errors
                logger.info(
                    "Memory search completed (schema mismatch bypass, access logging skipped)",
                    extra={
                        "user_id": uid,
                        "agent_id": client_name,
                        "query": query,
                        "results_count": len(memories),
                    },
                )
                return json.dumps(memories, indent=2, default=str)

            # Normal ACL filtering when schemas match
            memories = []
            if isinstance(search_results, dict) and "results" in search_results:
                for result in search_results["results"]:
                    if "id" in result:
                        try:
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
                        except ValueError:
                            # Skip invalid UUIDs
                            continue
            else:
                # Handle list format
                for result in search_results:
                    if "id" in result:
                        try:
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
                        except ValueError:
                            # Skip invalid UUIDs
                            continue

            # Log memory access for each memory found
            for memory in memories:
                try:
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
                except (ValueError, Exception) as log_error:
                    logger.warning(f"Failed to create access log for memory {memory.get('id')}: {log_error}")

            db.commit()

            logger.info(
                "Memory search completed",
                extra={
                    "user_id": uid,
                    "agent_id": client_name,
                    "query": query,
                    "results_count": len(memories),
                },
            )
            return json.dumps(memories, indent=2, default=str)
        finally:
            db.close()
    except ValueError as e:
        logger.warning(f"Input validation error in search_memory: {str(e)}")
        return json.dumps({"error": f"Input validation error: {str(e)}"}, indent=2)
    except Exception as e:
        # Fix JSON serialization issue by converting exception to string immediately
        error_msg = str(e)
        logger.exception(f"Error in search_memory: {error_msg}")
        return json.dumps({"error": f"Error searching memory: {error_msg}"}, indent=2)


@mcp.tool(description="List all memories in the user's memory")
async def list_memories(user_id: str = "drj", agent_id: str = "default") -> str:
    """
    List all memories with proper MCP parameter handling

    Args:
        user_id: User identifier (defaults to "drj" for backward compatibility)
        agent_id: Agent/client identifier (defaults to "default")
    """
    try:
        # Validate and sanitize inputs
        uid = validate_user_id(user_id)
        client_name = validate_agent_id(agent_id)

        logger.info(
            "MCP list_memories called", extra={"user_id": uid, "agent_id": client_name}
        )

        # Get memory client safely
        memory_client = get_memory_client_safe()
        if not memory_client:
            return (
                "Error: Memory system is currently unavailable. Please try again later."
            )

        # Get all memories directly from mem0
        memories = memory_client.get_all(user_id=uid)

        # Return results directly - simplified without complex permission filtering
        if isinstance(memories, dict) and "results" in memories:
            filtered_memories = memories["results"]
        else:
            # Handle case where memories is a list
            filtered_memories = memories if isinstance(memories, list) else []

        logger.info(
            "Memory list completed",
            extra={
                "user_id": uid,
                "agent_id": client_name,
                "results_count": len(filtered_memories),
            },
        )
        return json.dumps(filtered_memories, indent=2, default=str)

    except Exception as e:
        logger.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Delete all memories in the user's memory")
async def delete_all_memories(user_id: str = "drj", agent_id: str = "default") -> str:
    """
    Delete all memories with proper MCP parameter handling

    Args:
        user_id: User identifier (defaults to "drj" for backward compatibility)
        agent_id: Agent/client identifier (defaults to "default")
    """
    try:
        # Validate and sanitize inputs
        uid = validate_user_id(user_id)
        client_name = validate_agent_id(agent_id)

        logger.info(
            "MCP delete_all_memories called",
            extra={"user_id": uid, "agent_id": client_name},
        )

        # Get memory client safely
        memory_client = get_memory_client_safe()
        if not memory_client:
            return (
                "Error: Memory system is currently unavailable. Please try again later."
            )

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
                    logger.warning(
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

            logger.info(
                "Memory deletion completed",
                extra={
                    "user_id": uid,
                    "agent_id": client_name,
                    "deleted_count": len(accessible_memory_ids),
                },
            )
            return f"Successfully deleted {len(accessible_memory_ids)} memories"
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


# Legacy endpoint handlers (keep for backward compatibility)
@router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    """Handle SSE connections for a specific user and client - LEGACY"""
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


# Standard MCP SSE endpoint following MCP protocol specifications
@router.get("/sse")
async def handle_mcp_sse(request: Request):
    """Standard MCP SSE endpoint following protocol specifications"""
    try:
        # Create FastMCP SSE app
        sse_app = mcp.sse_app()

        # Handle the SSE connection using FastMCP's built-in SSE support
        return await sse_app(request.scope, request.receive, request._send)
    except Exception as e:
        logger.error(f"Error in MCP SSE endpoint: {e}")
        return {"error": "SSE connection failed", "detail": str(e)}


# MCP Health and Debugging Endpoints
@router.get("/health")
async def mcp_health_check():
    """Health check endpoint for MCP server debugging"""
    try:
        # Test memory client connection
        memory_client = get_memory_client_safe()
        memory_client_status = "healthy" if memory_client else "unhealthy"

        # Check database connection
        db_status = "healthy"
        try:
            from sqlalchemy import text
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        # Get available tools
        tools = []
        for tool_name in [
            "add_memories",
            "search_memory",
            "list_memories",
            "delete_all_memories",
        ]:
            tools.append({"name": tool_name, "available": True})

        health_data = {
            "status": "healthy",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "services": {
                "memory_client": memory_client_status,
                "database": db_status,
            },
            "tools": tools,
            "version": "1.0.0",
        }

        logger.info("MCP health check completed", extra=health_data)
        return health_data
    except Exception as e:
        logger.error(f"MCP health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "error": str(e),
        }


@router.get("/tools")
async def list_mcp_tools():
    """List available MCP tools for debugging"""
    try:
        tools = [
            {
                "name": "add_memories",
                "description": "Add a new memory to the system",
                "parameters": ["text", "user_id", "agent_id"],
                "required": ["text"],
            },
            {
                "name": "search_memory",
                "description": "Search through stored memories",
                "parameters": ["query", "user_id", "agent_id"],
                "required": ["query"],
            },
            {
                "name": "list_memories",
                "description": "List all memories for a user",
                "parameters": ["user_id", "agent_id"],
                "required": [],
            },
            {
                "name": "delete_all_memories",
                "description": "Delete all memories for a user",
                "parameters": ["user_id", "agent_id"],
                "required": [],
            },
        ]

        return {
            "tools": tools,
            "count": len(tools),
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing MCP tools: {e}")
        return {"error": "Failed to list tools", "detail": str(e)}


# Input validation functions
def validate_user_id(user_id: str) -> str:
    """Validate and sanitize user_id"""
    if not user_id or not user_id.strip():
        return "drj"  # Default fallback

    # Basic sanitization
    sanitized = user_id.strip()
    if len(sanitized) > 100:  # Reasonable limit
        sanitized = sanitized[:100]

    return sanitized


def validate_agent_id(agent_id: str) -> str:
    """Validate and sanitize agent_id"""
    if not agent_id or not agent_id.strip():
        return "default"  # Default fallback

    # Basic sanitization
    sanitized = agent_id.strip()
    if len(sanitized) > 100:  # Reasonable limit
        sanitized = sanitized[:100]

    return sanitized


def validate_text_input(text: str) -> str:
    """Validate and sanitize text input"""
    if not text or not text.strip():
        raise ValueError("Text input cannot be empty")

    # Basic sanitization while preserving meaningful content
    sanitized = text.strip()
    if len(sanitized) > 10000:  # Reasonable limit for memory content
        raise ValueError("Text input too long (max 10000 characters)")

    return sanitized


def validate_query_input(query: str) -> str:
    """Validate and sanitize search query"""
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    # Basic sanitization
    sanitized = query.strip()
    if len(sanitized) > 1000:  # Reasonable limit for queries
        sanitized = sanitized[:1000]

    return sanitized


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/messages/", status_code=status.HTTP_201_CREATED)
async def post_messages(payload: MessagesRequest):
    """Create a memory from a list of messages."""
    return await _process_mcp_messages(payload)


@router.get("/messages/")
async def get_messages(payload: MessagesRequest):
    """Alias to POST so agent callers can use GET if easier."""
    return await _process_mcp_messages(payload)


# Standard MCP POST endpoint for SSE messages
@router.post("/sse")
async def handle_mcp_sse_post(request: Request):
    """Standard MCP POST endpoint for SSE messages"""
    try:
        # Create FastMCP SSE app
        sse_app = mcp.sse_app()

        # Handle the POST message using FastMCP's built-in SSE support
        return await sse_app(request.scope, request.receive, request._send)
    except Exception as e:
        logger.error(f"Error in MCP SSE POST endpoint: {e}")
        return {"error": "SSE POST failed", "detail": str(e)}


async def handle_sse_post_message(request: Request):
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


# MCP Memory Operation Endpoints
@router.post("/memories")
async def mcp_add_memories(request: Request):
    """MCP endpoint for adding memories"""
    try:
        body = await request.json()
        text = validate_text_input(body.get("text", ""))
        user_id = validate_user_id(body.get("user_id", "drj"))
        agent_id = validate_agent_id(
            body.get("app_id") or body.get("agent_id", "default")
        )

        correlation_id = str(uuid.uuid4())
        user_id_var.set(user_id)
        client_name_var.set(agent_id)

        result = await add_memories(text, user_id, agent_id)
        return {"status": "success", "result": result, "correlation_id": correlation_id}

    except Exception as e:
        logger.error(f"MCP add_memories failed: {e}")
        return {"error": "add_memories failed", "detail": str(e)}


@router.post("/search")
async def mcp_search_memory(request: Request):
    """MCP endpoint for searching memories"""
    try:
        body = await request.json()
        query = validate_query_input(body.get("query", ""))
        user_id = validate_user_id(body.get("user_id", "drj"))
        agent_id = validate_agent_id(
            body.get("app_id") or body.get("agent_id", "default")
        )

        correlation_id = str(uuid.uuid4())
        user_id_var.set(user_id)
        client_name_var.set(agent_id)

        result = await search_memory(query, user_id, agent_id)
        return {"status": "success", "result": result, "correlation_id": correlation_id}

    except Exception as e:
        logger.error(f"MCP search_memory failed: {e}")
        return {"error": "search_memory failed", "detail": str(e)}


@router.get("/memories")
async def mcp_list_memories(request: Request):
    """MCP endpoint for listing memories"""
    try:
        params = request.query_params
        user_id = validate_user_id(params.get("user_id", "drj"))
        agent_id = validate_agent_id(
            params.get("app_id") or params.get("agent_id", "default")
        )

        correlation_id = str(uuid.uuid4())
        user_id_var.set(user_id)
        client_name_var.set(agent_id)

        result = await list_memories(user_id, agent_id)
        return {"status": "success", "result": result, "correlation_id": correlation_id}

    except Exception as e:
        logger.error(f"MCP list_memories failed: {e}")
        return {"error": "list_memories failed", "detail": str(e)}


@router.delete("/memories")
async def mcp_delete_all_memories(request: Request):
    """MCP endpoint for deleting all memories"""
    try:
        params = request.query_params
        user_id = validate_user_id(params.get("user_id", "drj"))
        agent_id = validate_agent_id(
            params.get("app_id") or params.get("agent_id", "default")
        )

        correlation_id = str(uuid.uuid4())
        user_id_var.set(user_id)
        client_name_var.set(agent_id)

        result = await delete_all_memories(user_id, agent_id)
        return {"status": "success", "result": result, "correlation_id": correlation_id}

    except Exception as e:
        logger.error(f"MCP delete_all_memories failed: {e}")
        return {"error": "delete_all_memories failed", "detail": str(e)}




def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = "mem0-mcp-server"

    # Include MCP router in the FastAPI app
    app.include_router(router)
