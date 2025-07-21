"""
ChatGPT Connector Router

Provides specialized endpoints for ChatGPT Actions integration with OIDC authentication.
Returns only necessary data (IDs, scores, text) without exposing metadata.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Memory, MemoryState
from app.utils.auth import JWTPayload, require_authentication
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp/connector",
    tags=["connector"],
    include_in_schema=True,
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)


class SearchRequest(BaseModel):
    """Request model for memory search"""

    query: str = Field(
        ..., description="Search query text", min_length=1, max_length=1000
    )
    limit: int = Field(
        10, description="Maximum number of results to return", ge=1, le=100
    )


class SearchResult(BaseModel):
    """Search result containing only ID and relevance score"""

    id: str = Field(..., description="Memory UUID")
    score: float = Field(..., description="Relevance score (0.0 to 1.0)")


class FetchRequest(BaseModel):
    """Request model for fetching memories by IDs"""

    ids: list[str] = Field(
        ..., description="List of memory UUIDs to fetch", min_items=1, max_items=50
    )

    @validator("ids")
    def validate_uuids(cls, v):
        """Validate that all IDs are valid UUIDs"""
        validated_ids = []
        for id_str in v:
            try:
                uuid_obj = UUID(id_str)
                # Reject nil UUID as invalid
                if uuid_obj == UUID("00000000-0000-0000-0000-000000000000"):
                    raise ValueError("Nil UUID is not allowed")
                validated_ids.append(str(uuid_obj))
            except ValueError:
                raise ValueError(f"Invalid UUID format: {id_str}")
        return validated_ids


class FetchResult(BaseModel):
    """Fetch result containing only ID and text content"""

    id: str = Field(..., description="Memory UUID")
    text: str = Field(..., description="Memory text content")


async def get_current_app_id(
    current_user: JWTPayload = Depends(require_authentication),
) -> UUID | None:
    """
    Extract app_id from JWT claims or generate default app for user
    For ChatGPT integration, we'll use a default app per user
    """
    # For now, return None to indicate default app access
    # In production, you might want to extract this from JWT or use a specific ChatGPT app
    return None


async def get_current_user_id(
    current_user: JWTPayload = Depends(require_authentication),
) -> str:
    """Extract user_id from JWT token"""
    return current_user.sub


async def fetch_by_ids(db: Session, ids: list[str], app_id: UUID | None) -> list[dict]:
    """
    Helper function to fetch memories by IDs with access control
    """
    results = []
    memory_client = get_memory_client()

    if not memory_client:
        logger.warning("Memory client not available for fetch operation")
        return results

    for id_str in ids:
        try:
            # Validate and convert to UUID
            memory_uuid = UUID(id_str)

            # Load memory record from database
            memory = db.query(Memory).filter(Memory.id == memory_uuid).first()

            if not memory:
                logger.warning(f"Memory not found: {id_str}")
                continue

            # Check access permissions
            if not check_memory_access_permissions(db, memory, app_id):
                logger.warning(f"Access denied for memory: {id_str}")
                continue

            # Memory must be active
            if memory.state != MemoryState.active:
                logger.warning(f"Memory not active: {id_str} (state: {memory.state})")
                continue

            # Get memory text from mem0 client
            try:
                mem0_result = memory_client.get(id_str)
                if mem0_result and "content" in mem0_result:
                    results.append({"id": id_str, "text": mem0_result["content"]})
                else:
                    # Fallback to database content if mem0 doesn't have it
                    results.append({"id": id_str, "text": memory.content})
            except Exception as mem0_error:
                logger.warning(f"Failed to fetch from mem0 for {id_str}: {mem0_error}")
                # Fallback to database content
                results.append({"id": id_str, "text": memory.content})

        except Exception as e:
            logger.error(f"Error processing memory ID {id_str}: {e}")
            continue

    return results


@router.post(
    "/search",
    summary="Search memories",
    description="Search memories and return only IDs and relevance scores",
    response_model=list[SearchResult],
)
async def search_memories(
    request: SearchRequest,
    current_user_id: str = Depends(get_current_user_id),
    current_user: JWTPayload = Depends(require_authentication),
) -> list[SearchResult]:
    """
    Search memories using the provided query string.
    Returns only memory IDs and relevance scores for security.
    """
    try:
        memory_client = get_memory_client()
        if not memory_client:
            raise HTTPException(
                status_code=503, detail="Memory service temporarily unavailable"
            )

        # Use mem0's search method
        search_results = memory_client.search(
            request.query, user_id=current_user_id, limit=request.limit
        )

        # Extract only IDs and scores
        results = []
        if search_results and "results" in search_results:
            for result in search_results["results"]:
                if "id" in result and "score" in result:
                    results.append(
                        SearchResult(id=str(result["id"]), score=float(result["score"]))
                    )

        logger.info(
            f"Search completed: query='{request.query}', results={len(results)}, user={current_user_id}"
        )
        return results

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search operation failed")


@router.post(
    "/fetch",
    summary="Fetch memories by IDs",
    description="Fetch memory content by providing specific memory IDs",
    response_model=list[FetchResult],
)
async def fetch_memories(
    request: FetchRequest,
    app_id: UUID | None = Depends(get_current_app_id),
    current_user: JWTPayload = Depends(require_authentication),
    db: Session = Depends(get_db),
) -> list[FetchResult]:
    """
    Fetch memory text content for the provided memory IDs.
    Only returns memories that the current user/app has access to.
    """
    try:
        # Fetch memories with access control
        accessible_memories = await fetch_by_ids(db, request.ids, app_id)

        # Convert to response format
        results = [
            FetchResult(id=mem["id"], text=mem["text"]) for mem in accessible_memories
        ]

        logger.info(
            f"Fetch completed: requested={len(request.ids)}, accessible={len(results)}, user={current_user.sub}"
        )
        return results

    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Fetch operation failed")
