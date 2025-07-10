from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, App
from app.mem0_client import get_memory_client


router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

@router.get("/")
async def get_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        # Create user if not exists (for compatibility)
        from uuid import uuid4
        import datetime
        user = User(
            id=uuid4(),
            user_id=user_id,
            name=f"User {user_id}",
            created_at=datetime.datetime.now(datetime.UTC)
        )
        db.add(user)
        db.commit()
    
    # Get total number of memories from mem0
    try:
        memory_client = get_memory_client()
        memories = memory_client.get_all(user_id=user_id)
        total_memories = len(memories.get("results", []))
    except Exception as e:
        total_memories = 0

    # Get total number of apps
    apps = db.query(App).filter(App.owner == user)
    total_apps = apps.count()

    return {
        "total_memories": total_memories,
        "total_apps": total_apps,
        "apps": apps.all()
    }

