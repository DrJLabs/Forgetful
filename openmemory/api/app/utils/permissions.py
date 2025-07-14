from typing import Optional
from uuid import UUID

from app.models import App, Memory, MemoryState
from sqlalchemy.orm import Session


def check_memory_access_permissions(
    db: Session, memory: Memory, app_id: Optional[UUID] = None
) -> bool:
    """
    Check if the given app has permission to access a memory based on:
    1. Memory state (must be active)
    2. App state (must not be paused)
    3. App-specific access controls

    Args:
        db: Database session
        memory: Memory object to check access for
        app_id: Optional app ID to check permissions for

    Returns:
        bool: True if access is allowed, False otherwise
    """
    # Check if memory is active
    if memory.state != MemoryState.active:
        return False

    # If no app_id provided, only check memory state
    if not app_id:
        return True

    # Check if app exists and is active
    app = db.query(App).filter(App.id == app_id).first()
    if not app:
        return False

    # Check if app is paused/inactive
    if not app.is_active:
        return False

    # SECURITY CHECK: Ensure the app belongs to the same user as the memory
    # This prevents cross-user memory access
    if app.owner_id != memory.user_id:
        return False

    # Check app-specific access controls
    from app.routers.memories import get_accessible_memory_ids

    accessible_memory_ids = get_accessible_memory_ids(db, app_id)

    # If accessible_memory_ids is None, no explicit ACL rules exist
    # In this case, apply default app-level isolation:
    # apps can only access memories they created
    if accessible_memory_ids is None:
        return memory.app_id == app_id

    # Check if memory is in the accessible set (explicit ACL rules exist)
    return memory.id in accessible_memory_ids
