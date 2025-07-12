"""
OpenMemory API main application module.

FastAPI application setup with CORS middleware, database initialization,
and router configuration for the OpenMemory API service.
"""
import datetime
import os
from uuid import uuid4

from app.config import DEFAULT_APP_ID, USER_ID
from app.database import Base, SessionLocal, engine
from app.mcp_server import setup_mcp_server
from app.models import App, User
from app.routers import apps_router, config_router
from app.routers import mem0_memories as memories_router
from app.routers import stats_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

app = FastAPI(title="OpenMemory API")

app.add_middleware(
    CORSMiddleware,
    # Specific origins instead of wildcard
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    # Specific methods instead of wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Only create tables and default data if not in testing mode
if os.getenv("TESTING") != "true":
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Check for USER_ID and create default user if needed
    def create_default_user():
        """Create default user if it doesn't exist."""
        db = SessionLocal()
        try:
            # Check if user exists
            user = db.query(User).filter(User.user_id == USER_ID).first()
            if not user:
                # Create default user
                user = User(
                    id=uuid4(),
                    user_id=USER_ID,
                    name="Default User",
                    created_at=datetime.datetime.now(datetime.UTC),
                )
                db.add(user)
                db.commit()
        finally:
            db.close()

    def create_default_app():
        """Create default application if it doesn't exist."""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == USER_ID).first()
            if not user:
                return

            # Check if app already exists
            existing_app = (
                db.query(App)
                .filter(App.name == DEFAULT_APP_ID, App.owner_id == user.id)
                .first()
            )

            if existing_app:
                return

            app = App(
                id=uuid4(),
                name=DEFAULT_APP_ID,
                owner_id=user.id,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
            )
            db.add(app)
            db.commit()
        finally:
            db.close()

    # Create default user on startup
    create_default_user()
    create_default_app()

# Setup MCP server
setup_mcp_server(app)

# Include routers - using the new mem0_memories router
app.include_router(memories_router.router)
app.include_router(apps_router)
app.include_router(stats_router)
app.include_router(config_router)

# Add pagination support
add_pagination(app)
