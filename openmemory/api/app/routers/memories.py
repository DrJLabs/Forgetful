import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    AccessControl,
    App,
    Category,
    Memory,
    MemoryAccessLog,
    MemoryState,
    MemoryStatusHistory,
    User,
)
from app.schemas import MemoryResponse
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from shared.errors import (
    NotFoundError,
)

# Agent 4 Integration - Structured Logging and Error Handling
from shared.logging_system import (
    api_logger,
)

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


def get_memory_or_404(db: Session, memory_id: UUID) -> Memory:
    memory = db.query(Memory).filter(Memory.id == memory_id).first()
    if not memory:
        api_logger.warning("Memory not found", memory_id=str(memory_id))
        raise NotFoundError(
            f"Memory with ID {memory_id} not found",
            resource_type="memory",
            resource_id=str(memory_id),
        )
    return memory


def update_memory_state(
    db: Session, memory_id: UUID, new_state: MemoryState, user_id: UUID
):
    memory = get_memory_or_404(db, memory_id)
    old_state = memory.state

    # Update memory state
    memory.state = new_state
    if new_state == MemoryState.archived:
        memory.archived_at = datetime.now(UTC)
    elif new_state == MemoryState.deleted:
        memory.deleted_at = datetime.now(UTC)

    # Record state change
    history = MemoryStatusHistory(
        memory_id=memory_id,
        changed_by=user_id,
        old_state=old_state,
        new_state=new_state,
    )
    db.add(history)
    db.commit()
    return memory


def get_accessible_memory_ids(db: Session, app_id: UUID) -> set[UUID]:
    """
    Get the set of memory IDs that the app has access to based on app-level ACL rules.
    Returns all memory IDs if no specific restrictions are found.
    """
    # Get app-level access controls
    app_access = (
        db.query(AccessControl)
        .filter(
            AccessControl.subject_type == "app",
            AccessControl.subject_id == app_id,
            AccessControl.object_type == "memory",
        )
        .all()
    )

    # If no app-level rules exist, return None to indicate all memories are accessible
    if not app_access:
        return None

    # Initialize sets for allowed and denied memory IDs
    allowed_memory_ids = set()
    denied_memory_ids = set()

    # Process app-level rules
    for rule in app_access:
        if rule.effect == "allow":
            if rule.object_id:  # Specific memory access
                allowed_memory_ids.add(rule.object_id)
            else:  # All memories access
                return None  # All memories allowed
        elif rule.effect == "deny":
            if rule.object_id:  # Specific memory denied
                denied_memory_ids.add(rule.object_id)
            else:  # All memories denied
                return set()  # No memories accessible

    # Remove denied memories from allowed set
    if allowed_memory_ids:
        allowed_memory_ids -= denied_memory_ids

    return allowed_memory_ids


# List all memories with filtering
@router.get("/", response_model=Page[MemoryResponse])
async def list_memories(
    user_id: str,
    app_id: UUID | None = None,
    from_date: int | None = Query(
        None,
        description="Filter memories created after this date (timestamp)",
        examples=[1718505600],
    ),
    to_date: int | None = Query(
        None,
        description="Filter memories created before this date (timestamp)",
        examples=[1718505600],
    ),
    categories: str | None = None,
    params: Params = Depends(),
    search_query: str | None = None,
    sort_column: str | None = Query(
        None, description="Column to sort by (memory, categories, app_name, created_at)"
    ),
    sort_direction: str | None = Query(
        None, description="Sort direction (asc or desc)"
    ),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Use mem0 search as source of truth for intelligent memory retrieval
    try:
        memory_client = get_memory_client()
        if memory_client:
            # Use mem0's semantic search with minimal filtering for better results
            # Let PostgreSQL handle detailed filtering after mem0 provides the semantic matches
            mem0_results = memory_client.search(
                query=search_query or "",
                user_id=user_id,
                limit=100,  # Get more results to apply additional filtering
            )

            # Extract memory IDs from mem0 results
            memory_ids = [result["id"] for result in mem0_results.get("results", [])]
            api_logger.info(
                "Retrieved memories from mem0", count=len(memory_ids), user_id=user_id
            )

        else:
            api_logger.warning(
                "Memory client unavailable, falling back to PostgreSQL", user_id=user_id
            )
            memory_ids = None

    except Exception as mem0_error:
        api_logger.error(
            "mem0 search failed, falling back to PostgreSQL",
            user_id=user_id,
            error=str(mem0_error),
        )
        memory_ids = None

    # Build PostgreSQL query for metadata enrichment or fallback
    if memory_ids is not None:
        # Use mem0 results as source of truth, query PostgreSQL for metadata only
        query = db.query(Memory).filter(
            Memory.id.in_(memory_ids), Memory.user_id == user.id
        )
    else:
        # Fallback to direct PostgreSQL query if mem0 unavailable
        query = db.query(Memory).filter(
            Memory.user_id == user.id,
            Memory.state != MemoryState.deleted,
            Memory.state != MemoryState.archived,
            Memory.content.ilike(f"%{search_query}%") if search_query else True,
        )

    # Apply additional filters (when not using mem0 results or for PostgreSQL-specific filters)
    if memory_ids is None and app_id:
        query = query.filter(Memory.app_id == app_id)

    if from_date:
        from_datetime = datetime.fromtimestamp(from_date, tz=UTC)
        query = query.filter(Memory.created_at >= from_datetime)

    if to_date:
        to_datetime = datetime.fromtimestamp(to_date, tz=UTC)
        query = query.filter(Memory.created_at <= to_datetime)

    # Preserve mem0's semantic relevance ranking when available
    if memory_ids is not None and search_query:
        # Create a case statement to preserve mem0's result order
        from sqlalchemy import case

        memory_order = case(
            *[
                (Memory.id == memory_id, index)
                for index, memory_id in enumerate(memory_ids)
            ],
            else_=len(memory_ids),
        )
        query = query.order_by(memory_order)

    # Join App so we can display app_name
    query = query.join(App, Memory.app_id == App.id)

    # Join categories only if filtering by them
    if categories:
        category_list = [c.strip() for c in categories.split(",")]
        query = query.join(Memory.categories).filter(Category.name.in_(category_list))

    # Apply sorting if specified
    if sort_column:
        sort_field = getattr(Memory, sort_column, None)
        if sort_field:
            query = (
                query.order_by(sort_field.desc())
                if sort_direction == "desc"
                else query.order_by(sort_field.asc())
            )

    # Eager‑load relations (no distinct needed now)
    query = query.options(
        joinedload(Memory.categories),
        joinedload(Memory.app),
    )

    # Get paginated results
    paginated_results = sqlalchemy_paginate(
        query,
        params,
        transformer=lambda items: [
            MemoryResponse(
                id=memory.id,
                content=memory.content,
                created_at=memory.created_at,
                state=memory.state.value,
                app_id=memory.app_id,
                app_name=memory.app.name if memory.app else None,
                categories=[category.name for category in memory.categories],
                metadata_=memory.metadata_,
            )
            for memory in items
            if check_memory_access_permissions(db, memory, app_id)
        ],
    )

    return paginated_results


# Get all categories
@router.get("/categories")
async def get_categories(user_id: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get unique categories associated with the user's memories
        # Get all memories
        memories = (
            db.query(Memory)
            .filter(
                Memory.user_id == user.id,
                Memory.state != MemoryState.deleted,
                Memory.state != MemoryState.archived,
            )
            .all()
        )

        # Get all categories from memories (handle potential None values)
        categories = []
        for memory in memories:
            if memory.categories:
                categories.extend([category.name for category in memory.categories])

        # Get unique categories
        unique_categories = list(set(categories))

        return {"categories": unique_categories, "total": len(unique_categories)}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting categories: {e}")
        # Return empty categories instead of error
        return {"categories": [], "total": 0}


class CreateMemoryRequest(BaseModel):
    user_id: str
    text: str
    metadata: dict = {}
    infer: bool = True
    app: str = "openmemory"

    @validator("text")
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Text cannot be empty")
        return v

    @validator("user_id")
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError("User ID cannot be empty")
        return v


class SearchMemoryRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 10

    @validator("query")
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v


# Create new memory
@router.post("/")
async def create_memory(request: CreateMemoryRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or create app
    app_obj = (
        db.query(App).filter(App.name == request.app, App.owner_id == user.id).first()
    )
    if not app_obj:
        app_obj = App(name=request.app, owner_id=user.id)
        db.add(app_obj)
        db.commit()
        db.refresh(app_obj)

    # Check if app is active
    if not app_obj.is_active:
        raise HTTPException(
            status_code=403,
            detail=f"App {request.app} is currently paused on OpenMemory. Cannot create new memories.",
        )

    # Log what we're about to do
    logging.info(
        f"Creating memory for user_id: {request.user_id} with app: {request.app}"
    )

    # Try to get memory client safely
    try:
        memory_client = get_memory_client()
        if not memory_client:
            raise Exception("Memory client is not available")
    except Exception as client_error:
        logging.warning(
            f"Memory client unavailable: {client_error}. Creating memory in database only."
        )
        return {"error": str(client_error)}

    # Try to save to mem0 via memory_client
    try:
        # Use the text directly as mem0 handles message formatting
        mem0_response = memory_client.add(
            request.text,
            user_id=request.user_id,
            metadata={
                "source_app": "openmemory",
                "mcp_client": request.app,
                **request.metadata,
            },
        )

        # Log the response for debugging
        logging.info(f"Mem0 response: {mem0_response}")

        # Process mem0 response - it should have "results" array with proper UUIDs
        stored_memories = []
        if isinstance(mem0_response, dict) and "results" in mem0_response:
            results = mem0_response.get("results", [])

            for result in results:
                if isinstance(result, dict) and result.get("event") == "ADD":
                    # Get the mem0-generated UUID
                    memory_id = UUID(result["id"])
                    memory_content = result.get("memory", "")

                    # Check if memory already exists in our database
                    existing_memory = (
                        db.query(Memory).filter(Memory.id == memory_id).first()
                    )

                    if existing_memory:
                        # Update existing memory
                        existing_memory.state = MemoryState.active
                        existing_memory.content = memory_content
                        existing_memory.metadata_ = {
                            **existing_memory.metadata_,
                            **request.metadata,
                        }
                        memory = existing_memory
                    else:
                        # Create new memory with the UUID from mem0
                        memory = Memory(
                            id=memory_id,
                            user_id=user.id,
                            app_id=app_obj.id,
                            content=memory_content,
                            metadata_=request.metadata,
                            state=MemoryState.active,
                        )
                        db.add(memory)

                    # Create history entry
                    history = MemoryStatusHistory(
                        memory_id=memory_id,
                        changed_by=user.id,
                        old_state=MemoryState.deleted
                        if existing_memory
                        else MemoryState.deleted,
                        new_state=MemoryState.active,
                    )
                    db.add(history)

            # Commit all changes before building response
            db.commit()

            # Build response by querying refreshed memory objects
            for result in results:
                if isinstance(result, dict) and result.get("event") == "ADD":
                    memory_id = UUID(result["id"])
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory:
                        stored_memories.append(
                            {
                                "id": str(memory.id),
                                "memory": memory.content,
                                "created_at": memory.created_at.isoformat()
                                if memory.created_at
                                else None,
                                "user_id": request.user_id,
                                "metadata": memory.metadata_,
                            }
                        )

            # Return in format expected by GPT Actions Bridge
            return {
                "results": stored_memories,
                "relations": mem0_response.get("relations", {}),
            }
        else:
            # If mem0 response doesn't have expected format, log and return error
            logging.error(f"Unexpected mem0 response format: {mem0_response}")
            return {"error": "Unexpected response format from memory system"}

    except Exception as mem0_error:
        logging.error(f"Mem0 operation failed: {mem0_error}")
        return {"error": str(mem0_error)}


# Add search endpoint after the create_memory endpoint
@router.post("/search")
async def search_memories(request: SearchMemoryRequest, db: Session = Depends(get_db)):
    """Search memories using the query"""
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        memory_client = get_memory_client()
        if not memory_client:
            raise Exception("Memory client is not available")
    except Exception as client_error:
        logging.warning(f"Memory client unavailable: {client_error}")
        return {"error": str(client_error)}

    try:
        # Use mem0's search method
        search_results = memory_client.search(
            request.query, user_id=request.user_id, limit=request.limit
        )

        # Return results in expected format
        return {"results": search_results.get("results", [])}

    except Exception as search_error:
        logging.warning(f"Search operation failed: {search_error}")
        return {"error": str(search_error)}


# Get memory by ID
@router.get("/{memory_id}")
async def get_memory(memory_id: str, db: Session = Depends(get_db)):
    try:
        # Validate UUID format
        memory_uuid = UUID(memory_id)
        # Reject nil UUID as invalid
        if memory_uuid == UUID("00000000-0000-0000-0000-000000000000"):
            raise ValueError("Nil UUID is not allowed")
    except ValueError as err:
        raise HTTPException(status_code=422, detail="Invalid UUID format") from err

    memory = get_memory_or_404(db, memory_uuid)
    return {
        "id": memory.id,
        "text": memory.content,
        "created_at": int(memory.created_at.timestamp()),
        "state": memory.state.value,
        "app_id": memory.app_id,
        "app_name": memory.app.name if memory.app else None,
        "categories": [category.name for category in memory.categories],
        "metadata_": memory.metadata_,
    }


class DeleteMemoriesRequest(BaseModel):
    memory_ids: list[UUID]
    user_id: str


# Delete multiple memories
@router.delete("/")
async def delete_memories(
    request: DeleteMemoriesRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete from mem0 first, then update PostgreSQL
    try:
        memory_client = get_memory_client()
        if memory_client:
            for memory_id in request.memory_ids:
                try:
                    memory_client.delete(str(memory_id))
                except Exception as mem0_error:
                    api_logger.error(
                        "Failed to delete memory from mem0",
                        memory_id=str(memory_id),
                        error=str(mem0_error),
                    )
            api_logger.info(
                "Bulk deleted memories from mem0", count=len(request.memory_ids)
            )
        else:
            api_logger.warning(
                "Memory client unavailable, deleting from PostgreSQL only"
            )
    except Exception as client_error:
        api_logger.error(
            "Memory client error during bulk delete", error=str(client_error)
        )

    # Update PostgreSQL states
    for memory_id in request.memory_ids:
        update_memory_state(db, memory_id, MemoryState.deleted, user.id)
    return {"message": f"Successfully deleted {len(request.memory_ids)} memories"}


# Delete a single memory
@router.delete("/{memory_id}")
async def delete_memory(memory_id: UUID, db: Session = Depends(get_db)):
    memory = get_memory_or_404(db, memory_id)

    # Delete from mem0 vector store first
    try:
        memory_client = get_memory_client()
        if memory_client:
            memory_client.delete(str(memory_id))
            api_logger.info("Memory deleted from mem0", memory_id=str(memory_id))
        else:
            api_logger.warning(
                "Memory client unavailable, deleting from PostgreSQL only",
                memory_id=str(memory_id),
            )
    except Exception as mem0_error:
        api_logger.error(
            "mem0 delete failed, proceeding with PostgreSQL delete",
            memory_id=str(memory_id),
            error=str(mem0_error),
        )

    # Then update PostgreSQL state
    update_memory_state(db, memory_id, MemoryState.deleted, memory.user_id)
    return {"message": f"Successfully deleted memory {memory_id}"}


# Archive memories
@router.post("/actions/archive")
async def archive_memories(
    memory_ids: list[UUID], user_id: UUID, db: Session = Depends(get_db)
):
    # Update mem0 metadata for archived state
    try:
        memory_client = get_memory_client()
        if memory_client:
            for memory_id in memory_ids:
                try:
                    # Get current memory to build metadata
                    memory = get_memory_or_404(db, memory_id)
                    # Update mem0 with archived state in metadata
                    memory_client.update(
                        str(memory_id),
                        data=memory.content,
                        metadata={**memory.to_mem0_metadata(), "state": "archived"},
                    )
                except Exception as mem0_error:
                    api_logger.error(
                        "Failed to update archived state in mem0",
                        memory_id=str(memory_id),
                        error=str(mem0_error),
                    )
            api_logger.info("Updated archived state in mem0", count=len(memory_ids))
        else:
            api_logger.warning(
                "Memory client unavailable, archiving in PostgreSQL only"
            )
    except Exception as client_error:
        api_logger.error("Memory client error during archive", error=str(client_error))

    # Update PostgreSQL states
    for memory_id in memory_ids:
        update_memory_state(db, memory_id, MemoryState.archived, user_id)
    return {"message": f"Successfully archived {len(memory_ids)} memories"}


class PauseMemoriesRequest(BaseModel):
    memory_ids: list[UUID] | None = None
    category_ids: list[UUID] | None = None
    app_id: UUID | None = None
    all_for_app: bool = False
    global_pause: bool = False
    state: MemoryState | None = None
    user_id: str


# Pause access to memories
@router.post("/actions/pause")
async def pause_memories(request: PauseMemoriesRequest, db: Session = Depends(get_db)):
    global_pause = request.global_pause
    all_for_app = request.all_for_app
    app_id = request.app_id
    memory_ids = request.memory_ids
    category_ids = request.category_ids
    state = request.state or MemoryState.paused

    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.id

    if global_pause:
        # Pause all memories
        memories = (
            db.query(Memory)
            .filter(
                Memory.state != MemoryState.deleted,
                Memory.state != MemoryState.archived,
            )
            .all()
        )
        for memory in memories:
            update_memory_state(db, memory.id, state, user_id)
        return {"message": "Successfully paused all memories"}

    if app_id:
        # Pause all memories for an app
        memories = (
            db.query(Memory)
            .filter(
                Memory.app_id == app_id,
                Memory.user_id == user.id,
                Memory.state != MemoryState.deleted,
                Memory.state != MemoryState.archived,
            )
            .all()
        )
        for memory in memories:
            update_memory_state(db, memory.id, state, user_id)
        return {"message": f"Successfully paused all memories for app {app_id}"}

    if all_for_app and memory_ids:
        # Pause all memories for an app
        memories = (
            db.query(Memory)
            .filter(
                Memory.user_id == user.id,
                Memory.state != MemoryState.deleted,
                Memory.id.in_(memory_ids),
            )
            .all()
        )
        for memory in memories:
            update_memory_state(db, memory.id, state, user_id)
        return {"message": "Successfully paused all memories"}

    if memory_ids:
        # Pause specific memories
        for memory_id in memory_ids:
            update_memory_state(db, memory_id, state, user_id)
        return {"message": f"Successfully paused {len(memory_ids)} memories"}

    if category_ids:
        # Pause memories by category
        memories = (
            db.query(Memory)
            .join(Memory.categories)
            .filter(
                Category.id.in_(category_ids),
                Memory.state != MemoryState.deleted,
                Memory.state != MemoryState.archived,
            )
            .all()
        )
        for memory in memories:
            update_memory_state(db, memory.id, state, user_id)
        return {
            "message": f"Successfully paused memories in {len(category_ids)} categories"
        }

    raise HTTPException(status_code=400, detail="Invalid pause request parameters")


# Get memory access logs
@router.get("/{memory_id}/access-log")
async def get_memory_access_log(
    memory_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(MemoryAccessLog).filter(MemoryAccessLog.memory_id == memory_id)
    total = query.count()
    logs = (
        query.order_by(MemoryAccessLog.accessed_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Get app name
    for log in logs:
        app = db.query(App).filter(App.id == log.app_id).first()
        log.app_name = app.name if app else None

    return {"total": total, "page": page, "page_size": page_size, "logs": logs}


class UpdateMemoryRequest(BaseModel):
    memory_content: str
    user_id: str


# Update a memory
@router.put("/{memory_id}")
async def update_memory(
    memory_id: UUID, request: UpdateMemoryRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    memory = get_memory_or_404(db, memory_id)

    # Update through mem0 for re-embedding and conflict resolution
    try:
        memory_client = get_memory_client()
        if memory_client:
            # Use mem0's update method to maintain intelligence
            memory_client.update(
                str(memory_id),
                data=request.memory_content,
                metadata=memory.to_mem0_metadata(),  # Preserve state info
            )
            api_logger.info("Memory updated through mem0", memory_id=str(memory_id))
        else:
            api_logger.warning(
                "Memory client unavailable, updating PostgreSQL only",
                memory_id=str(memory_id),
            )
    except Exception as mem0_error:
        api_logger.error(
            "mem0 update failed, proceeding with PostgreSQL update",
            memory_id=str(memory_id),
            error=str(mem0_error),
        )

    # Sync PostgreSQL with updated content
    memory.content = request.memory_content
    memory.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(memory)

    return {
        "id": memory.id,
        "content": memory.content,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        "state": memory.state.value,
        "app_id": memory.app_id,
        "metadata_": memory.metadata_,
    }


class FilterMemoriesRequest(BaseModel):
    user_id: str
    page: int = 1
    size: int = 10
    search_query: str | None = None
    app_ids: list[UUID] | None = None
    category_ids: list[UUID] | None = None
    sort_column: str | None = None
    sort_direction: str | None = None
    from_date: int | None = None
    to_date: int | None = None
    show_archived: bool | None = False


@router.post("/filter", response_model=Page[MemoryResponse])
async def filter_memories(
    request: FilterMemoriesRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Use mem0 search as source of truth for intelligent filtering
    try:
        memory_client = get_memory_client()
        if memory_client:
            # Use mem0's semantic search with minimal filtering for better results
            # Let PostgreSQL handle detailed filtering after mem0 provides the semantic matches
            mem0_results = memory_client.search(
                query=request.search_query or "",
                user_id=request.user_id,
                limit=100,  # Get more results for additional filtering
            )

            # Extract memory IDs from mem0 results
            memory_ids = [result["id"] for result in mem0_results.get("results", [])]
            api_logger.info(
                "Filtered memories from mem0",
                count=len(memory_ids),
                user_id=request.user_id,
            )

        else:
            api_logger.warning(
                "Memory client unavailable, falling back to PostgreSQL",
                user_id=request.user_id,
            )
            memory_ids = None

    except Exception as mem0_error:
        api_logger.error(
            "mem0 search failed, falling back to PostgreSQL",
            user_id=request.user_id,
            error=str(mem0_error),
        )
        memory_ids = None

    # Build PostgreSQL query for metadata enrichment or fallback
    if memory_ids is not None:
        # Use mem0 results as source of truth, query PostgreSQL for metadata only
        query = db.query(Memory).filter(
            Memory.id.in_(memory_ids), Memory.user_id == user.id
        )
    else:
        # Fallback to direct PostgreSQL query if mem0 unavailable
        query = db.query(Memory).filter(
            Memory.user_id == user.id,
            Memory.state != MemoryState.deleted,
        )

        # Filter archived memories based on show_archived parameter (fallback only)
        if not request.show_archived:
            query = query.filter(Memory.state != MemoryState.archived)

        # Apply search filter (fallback only)
        if request.search_query:
            query = query.filter(Memory.content.ilike(f"%{request.search_query}%"))

    # Apply app filter (fallback only, handled in mem0 filters when available)
    if memory_ids is None and request.app_ids:
        query = query.filter(Memory.app_id.in_(request.app_ids))

    # Add joins for app and categories
    query = query.outerjoin(App, Memory.app_id == App.id)

    # Apply category filter
    if request.category_ids:
        query = query.join(Memory.categories).filter(
            Category.id.in_(request.category_ids)
        )
    else:
        query = query.outerjoin(Memory.categories)

    # Apply date filters
    if request.from_date:
        from_datetime = datetime.fromtimestamp(request.from_date, tz=UTC)
        query = query.filter(Memory.created_at >= from_datetime)

    if request.to_date:
        to_datetime = datetime.fromtimestamp(request.to_date, tz=UTC)
        query = query.filter(Memory.created_at <= to_datetime)

    # Apply sorting with DISTINCT ON compatibility
    if request.sort_column and request.sort_direction:
        sort_direction = request.sort_direction.lower()
        if sort_direction not in ["asc", "desc"]:
            raise HTTPException(status_code=400, detail="Invalid sort direction")

        sort_mapping = {
            "memory": Memory.content,
            "app_name": App.name,
            "created_at": Memory.created_at,
        }

        if request.sort_column not in sort_mapping:
            raise HTTPException(status_code=400, detail="Invalid sort column")

        sort_field = sort_mapping[request.sort_column]
        if sort_direction == "desc":
            query = query.order_by(Memory.id, sort_field.desc())
        else:
            query = query.order_by(Memory.id, sort_field.asc())
    else:
        # Default sorting - Memory.id first for DISTINCT ON compatibility
        query = query.order_by(Memory.id, Memory.created_at.desc())

    # Add eager loading for categories and make the query distinct
    query = query.options(joinedload(Memory.categories)).distinct(Memory.id)

    # Use fastapi-pagination's paginate function
    return sqlalchemy_paginate(
        query,
        Params(page=request.page, size=request.size),
        transformer=lambda items: [
            MemoryResponse(
                id=memory.id,
                content=memory.content,
                created_at=memory.created_at,
                state=memory.state.value,
                app_id=memory.app_id,
                app_name=memory.app.name if memory.app else None,
                categories=[category.name for category in memory.categories],
                metadata_=memory.metadata_,
            )
            for memory in items
        ],
    )


@router.get("/{memory_id}/related", response_model=Page[MemoryResponse])
async def get_related_memories(
    memory_id: UUID,
    user_id: str,
    params: Params = Depends(),
    db: Session = Depends(get_db),
):
    """Get related memories using mem0's knowledge graph intelligence"""

    # Validate user
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get the source memory
    memory = get_memory_or_404(db, memory_id)

    # Use mem0's intelligence to find related memories through semantic search
    memory_ids = None
    try:
        memory_client = get_memory_client()
        if memory_client:
            # Use mem0's semantic search for relationship discovery
            # Use the source memory's content as semantic query to find related memories
            mem0_results = memory_client.search(
                query=memory.content[:200],  # Use first 200 chars as semantic query
                user_id=user_id,
                limit=20,  # Get more results for filtering
            )

            # Extract related memory IDs (excluding the source memory)
            memory_ids = [
                result["id"]
                for result in mem0_results.get("results", [])
                if result["id"] != str(memory_id)
            ]

            api_logger.info(
                "Found related memories via mem0",
                source_memory=str(memory_id),
                related_count=len(memory_ids),
                user_id=user_id,
            )

        else:
            api_logger.warning(
                "Memory client unavailable, using fallback",
                memory_id=str(memory_id),
                user_id=user_id,
            )

    except Exception as mem0_error:
        api_logger.error(
            "mem0 related search failed, using fallback",
            memory_id=str(memory_id),
            error=str(mem0_error),
            user_id=user_id,
        )

    # Query PostgreSQL for metadata enrichment or fallback
    try:
        if memory_ids:
            # Use mem0 results as source of truth
            query = db.query(Memory).filter(
                Memory.id.in_([UUID(mid) for mid in memory_ids]),
                Memory.user_id == user.id,
                Memory.state != MemoryState.deleted,
            )
        else:
            # Fallback: Simple category-based matching with proper error handling
            category_ids = (
                [category.id for category in memory.categories]
                if memory.categories
                else []
            )
            if category_ids:
                query = (
                    db.query(Memory)
                    .filter(
                        Memory.user_id == user.id,
                        Memory.id != memory_id,
                        Memory.state != MemoryState.deleted,
                    )
                    .join(
                        Memory.categories, isouter=True
                    )  # Use LEFT JOIN to prevent failures
                    .filter(Category.id.in_(category_ids))
                )
            else:
                # No categories available - return empty result
                return Page.create([], total=0, params=params)

        # Add eager loading
        query = query.options(joinedload(Memory.categories), joinedload(Memory.app))

        # Force reasonable page size
        params = Params(page=params.page, size=min(params.size, 10))

        return sqlalchemy_paginate(
            query,
            params,
            transformer=lambda items: [
                MemoryResponse(
                    id=memory.id,
                    content=memory.content,
                    created_at=memory.created_at,
                    state=memory.state.value,
                    app_id=memory.app_id,
                    app_name=memory.app.name if memory.app else None,
                    categories=[category.name for category in memory.categories],
                    metadata_=memory.metadata_,
                )
                for memory in items
            ],
        )

    except Exception as db_error:
        api_logger.error(
            "Database fallback failed",
            memory_id=str(memory_id),
            error=str(db_error),
            user_id=user_id,
        )
        return Page.create([], total=0, params=params)
