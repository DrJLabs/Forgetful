from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from app.config import MAX_MEMORY_PAGE_SIZE
from app.models import App, Memory, User
from app.schemas import MemoryResponse
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from shared.logging_system import api_logger

from .query_builders import (
    apply_common_memory_filters,
    apply_general_sorting,
    apply_related_memory_filters_and_sort,
    build_base_memory_query,
)


def _memory_to_response(memory: Memory) -> MemoryResponse:
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        created_at=(
            memory.created_at.isoformat()
            if isinstance(memory.created_at, datetime)
            else None
        ),
        state=memory.state.value,
        app_id=memory.app_id,
        app_name=memory.app.name if memory.app else None,
        categories=[c.name for c in memory.categories],
        metadata_=memory.metadata_,
    )


async def perform_memory_search_with_fallback(
    *,
    db: Session,
    user: User,
    params: Params,
    search_query: str | None = None,
    app_id: UUID | None = None,
    app_ids: list[UUID] | None = None,
    from_date: int | None = None,
    to_date: int | None = None,
    categories: list[str] | None = None,
    exclude_ids: list[UUID] | None = None,
    is_related_search: bool = False,
    is_filter_search: bool = False,
    show_archived: bool = False,
    sort_column: str | None = None,
    sort_direction: str | None = None,
    source_memory_id: UUID | None = None,
    access_control_app_id: UUID | None = None,
) -> Page[MemoryResponse]:
    """Perform mem0 search with PostgreSQL fallback and return paginated results."""

    memory_ids: list[str] | None = None
    try:
        memory_client = get_memory_client()
        if memory_client and search_query is not None:
            mem0_results = memory_client.search(
                query=search_query or "",
                user_id=user.user_id,
                limit=100,
            )
            memory_ids = [r["id"] for r in mem0_results.get("results", [])]
            api_logger.info(
                "Retrieved memories from mem0",
                count=len(memory_ids),
                user_id=user.user_id,
            )
    except Exception as mem0_error:
        api_logger.error(
            "mem0 search failed, falling back to PostgreSQL",
            user_id=user.user_id,
            error=str(mem0_error),
        )
        memory_ids = None

    if memory_ids:
        query = db.query(Memory).filter(
            Memory.id.in_([UUID(mid) for mid in memory_ids])
        )
        query = build_base_memory_query(query, user.id)
        order_case = case(
            *[(Memory.id == UUID(mid), idx) for idx, mid in enumerate(memory_ids)],
            else_=len(memory_ids),
        )
        query = query.order_by(order_case)
    else:
        query = db.query(Memory)
        query = build_base_memory_query(query, user.id)
        query = apply_common_memory_filters(
            query,
            app_id=app_id,
            app_ids=app_ids,
            from_date=from_date,
            to_date=to_date,
            categories=categories,
            search_query=search_query,
            show_archived=show_archived,
            exclude_ids=exclude_ids,
        )
        query = apply_general_sorting(
            query, sort_column=sort_column, sort_direction=sort_direction
        )

    if memory_ids and not is_filter_search:
        # Apply additional filters even when mem0 returns IDs
        query = apply_common_memory_filters(
            query,
            app_id=app_id,
            app_ids=app_ids,
            from_date=from_date,
            to_date=to_date,
            categories=categories,
            show_archived=show_archived,
            exclude_ids=exclude_ids,
        )
        query = apply_general_sorting(
            query, sort_column=sort_column, sort_direction=sort_direction
        )

    if is_related_search and source_memory_id is not None:
        query = apply_related_memory_filters_and_sort(
            query,
            source_memory_id=source_memory_id,
            categories=categories,
        )

    query = query.join(App, Memory.app_id == App.id)
    query = query.options(
        joinedload(Memory.categories), joinedload(Memory.app)
    ).distinct(Memory.id)

    params = Params(page=params.page, size=min(params.size, MAX_MEMORY_PAGE_SIZE))

    page = sqlalchemy_paginate(
        query,
        params,
        transformer=lambda items: [
            _memory_to_response(memory)
            for memory in items
            if check_memory_access_permissions(db, memory, access_control_app_id)
        ],
    )
    return page
