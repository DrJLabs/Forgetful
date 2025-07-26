from __future__ import annotations

from datetime import datetime, UTC
from typing import Iterable, List, Optional
from uuid import UUID

from sqlalchemy.orm import Query
from sqlalchemy import func

from app.models import Memory, MemoryState, Category, App


def build_base_memory_query(query: Query, user_id: UUID) -> Query:
    """Start a memory query filtered by user and excluding deleted."""
    return query.filter(Memory.user_id == user_id, Memory.state != MemoryState.deleted)


def apply_common_memory_filters(
    query: Query,
    *,
    app_id: Optional[UUID] = None,
    app_ids: Optional[Iterable[UUID]] = None,
    from_date: Optional[int] = None,
    to_date: Optional[int] = None,
    categories: Optional[List[str]] = None,
    search_query: Optional[str] = None,
    show_archived: bool = False,
    exclude_ids: Optional[Iterable[UUID]] = None,
) -> Query:
    if not show_archived:
        query = query.filter(Memory.state != MemoryState.archived)

    if app_id:
        query = query.filter(Memory.app_id == app_id)
    elif app_ids:
        query = query.filter(Memory.app_id.in_(app_ids))

    if from_date:
        query = query.filter(Memory.created_at >= datetime.fromtimestamp(from_date, tz=UTC))
    if to_date:
        query = query.filter(Memory.created_at <= datetime.fromtimestamp(to_date, tz=UTC))

    if search_query:
        query = query.filter(Memory.content.ilike(f"%{search_query}%"))

    if categories:
        query = query.join(Memory.categories).filter(Category.name.in_(categories))
    else:
        query = query.outerjoin(Memory.categories)

    if exclude_ids:
        query = query.filter(~Memory.id.in_(list(exclude_ids)))

    return query


def apply_general_sorting(
    query: Query,
    *,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None,
) -> Query:
    if sort_column:
        mapping = {
            "memory": Memory.content,
            "app_name": App.name,
            "created_at": Memory.created_at,
            "categories": func.count(Category.id),
        }
        column = mapping.get(sort_column)
        if column is not None:
            if sort_column == "categories":
                query = query.group_by(Memory.id)
            order = column.desc() if sort_direction == "desc" else column.asc()
            query = query.order_by(order)
    else:
        query = query.order_by(Memory.created_at.desc())
    return query


def apply_related_memory_filters_and_sort(
    query: Query,
    *,
    source_memory_id: UUID,
    categories: Optional[List[str]] = None,
) -> Query:
    query = query.filter(Memory.id != source_memory_id)
    if categories:
        query = query.join(Memory.categories).filter(Category.name.in_(categories))
    else:
        query = query.outerjoin(Memory.categories)
    query = query.order_by(Memory.created_at.desc())
    return query
