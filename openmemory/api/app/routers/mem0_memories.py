"""
Simplified memory router that bridges OpenMemory API to main mem0 system
This replaces the complex SQLite-based memories.py router
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
import logging
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.mem0_client import get_memory_client

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])
logger = logging.getLogger(__name__)


class CreateMemoryRequest(BaseModel):
    user_id: str
    text: str
    metadata: dict = {}
    app: str = "openmemory"


class MemoryResponse(BaseModel):
    id: str
    content: str
    created_at: str
    user_id: str
    metadata: Optional[dict] = {}


class PaginatedMemoryResponse(BaseModel):
    items: List[MemoryResponse]
    total: int
    page: int
    size: int
    pages: int


@router.get("/", response_model=PaginatedMemoryResponse)
async def list_memories(
    user_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search_query: Optional[str] = None
):
    """List memories for a user, optionally filtered by search query"""
    try:
        memory_client = get_memory_client()
        
        if search_query:
            # Use search if query provided
            results = memory_client.search(
                query=search_query,
                user_id=user_id,
                limit=size
            )
            memories = results.get("results", [])
        else:
            # Get all memories for user
            results = memory_client.get_all(user_id=user_id)
            memories = results.get("results", [])
        
        # Paginate results
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_memories = memories[start_idx:end_idx]
        
        # Transform to response format
        items = []
        for mem in paginated_memories:
            items.append(MemoryResponse(
                id=mem.get("id", str(uuid4())),
                content=mem.get("memory", ""),
                created_at=mem.get("created_at", datetime.utcnow().isoformat()),
                user_id=user_id,
                metadata=mem.get("metadata", {})
            ))
        
        total = len(memories)
        pages = (total + size - 1) // size
        
        return PaginatedMemoryResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        # Return empty results on error
        return PaginatedMemoryResponse(
            items=[],
            total=0,
            page=page,
            size=size,
            pages=0
        )


@router.post("/")
async def create_memory(request: CreateMemoryRequest):
    """Create a new memory in the main mem0 system"""
    try:
        memory_client = get_memory_client()
        
        # Create messages format for mem0
        messages = [
            {"role": "user", "content": request.text}
        ]
        
        # Add metadata
        metadata = request.metadata.copy()
        metadata["source_app"] = "openmemory"
        metadata["mcp_client"] = request.app
        
        # Add to mem0
        result = memory_client.add(
            messages,
            user_id=request.user_id,
            metadata=metadata
        )
        
        logger.info(f"Created memory via mem0: {result}")
        
        # Return the result as-is since OpenMemory expects this format
        return result
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        return {"error": str(e)}


@router.get("/{memory_id}")
async def get_memory(memory_id: str):
    """Get a specific memory by ID"""
    try:
        memory_client = get_memory_client()
        
        # mem0 doesn't have a direct get_by_id, so we search all and filter
        # This is not ideal but works for now
        # In production, you'd want to implement a proper get_by_id in mem0
        
        # For now, return a not found error
        raise HTTPException(status_code=404, detail="Memory not found - direct ID lookup not implemented")
        
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory"""
    try:
        memory_client = get_memory_client()
        
        # Delete from mem0
        memory_client.delete(memory_id)
        
        return {"message": f"Successfully deleted memory {memory_id}"}
        
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{memory_id}")
async def update_memory(memory_id: str, text: str):
    """Update a memory"""
    try:
        memory_client = get_memory_client()
        
        # Update in mem0
        result = memory_client.update(memory_id, text)
        
        return {"message": "Memory updated successfully!", "result": result}
        
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Simplified endpoints that just return empty results for now
@router.get("/categories")
async def get_categories(user_id: str):
    """Get categories - not implemented in mem0"""
    return {"categories": [], "total": 0}


@router.post("/filter")
async def filter_memories(
    user_id: str,
    search_query: Optional[str] = None,
    page: int = 1,
    size: int = 50
):
    """Filter memories - redirects to list_memories"""
    return await list_memories(user_id=user_id, page=page, size=size, search_query=search_query) 