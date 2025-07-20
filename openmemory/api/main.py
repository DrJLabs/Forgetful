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
from app.routers import apps_router, config_router, connector_router, memories_router, stats_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_pagination import add_pagination

from shared.errors import ExternalServiceError, NotFoundError, ValidationError

app = FastAPI(
    title="OpenMemory API",
    description="Memory storage and retrieval API with ChatGPT integration",
    version="1.0.0",
    # OpenAPI 3.1.0 security scheme for ChatGPT OIDC integration
    servers=[
        {"url": "https://mcp.drjlabs.com", "description": "Production server"},
        {"url": "http://localhost:8765", "description": "Development server"}
    ]
)


# Exception handlers for custom errors
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    """Handle NotFoundError by returning HTTP 404"""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle ValidationError by returning HTTP 400"""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError):
    """Handle ExternalServiceError by returning HTTP 503"""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# Health endpoint for monitoring and troubleshooting
@app.get("/health")
async def health_check():
    """
    Health check endpoint that validates system components
    """
    try:
        # Test database connection
        db = SessionLocal()
        try:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
            db_status = "healthy"
            db.close()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        # Test memory client
        try:
            from app.utils.memory import get_memory_client

            memory_client = get_memory_client()
            mem0_status = (
                "healthy" if memory_client else "unhealthy: client not initialized"
            )
        except Exception as e:
            mem0_status = f"unhealthy: {str(e)}"

        # Overall status
        overall_status = (
            "healthy"
            if db_status == "healthy" and "healthy" in mem0_status
            else "degraded"
        )

        return {
            "status": overall_status,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "services": {
                "database": db_status,
                "mem0_client": mem0_status,
                "api": "healthy",
            },
            "version": "1.0.0",
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "error": str(e),
            },
        )


app.add_middleware(
    CORSMiddleware,
    # Tightened CORS for production security
    allow_origins=[
        "http://localhost:3000",           # Local UI development
        "https://chat.openai.com",         # ChatGPT origin
    ],
    allow_credentials=False,  # Bearer tokens don't need credentials
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],  # Only necessary headers
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

# OIDC Discovery: OpenAPI schema points directly to oidc.drjlabs.com/.well-known/openid-configuration
# This follows best practice: resource server publishes schema, auth server publishes discovery

# Add OpenAPI security scheme for ChatGPT integration
@app.on_event("startup")
def configure_openapi_security():
    """Configure OpenAPI security scheme for OIDC authentication"""
    if not hasattr(app, 'openapi_schema') or app.openapi_schema is None:
        from fastapi.openapi.utils import get_openapi

        # Generate base OpenAPI schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=app.servers
        )

        # Add OIDC security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "oidc": {
                "type": "openIdConnect",
                "openIdConnectUrl": "https://oidc.drjlabs.com/.well-known/openid-configuration"
            }
        }

        # Apply security globally
        openapi_schema["security"] = [{"oidc": ["openid", "email", "profile"]}]

        app.openapi_schema = openapi_schema

# Setup MCP server
setup_mcp_server(app)

# Include routers - using the corrected memories router
app.include_router(memories_router)
app.include_router(apps_router)
app.include_router(stats_router)
app.include_router(config_router)

# Create ChatGPT connector sub-application with specific CORS
connector_app = FastAPI(
    title="OpenMemory ChatGPT Connector",
    docs_url=None,  # Disable docs for security
    redoc_url=None,  # Disable redoc for security
    openapi_url=None  # Disable OpenAPI for security
)

# ChatGPT-specific CORS configuration
connector_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com"],
    allow_credentials=False,  # Bearer tokens don't need credentials
    allow_methods=["POST", "OPTIONS"],  # Only allow POST requests
    allow_headers=["Authorization", "Content-Type"],
)

# Include connector router in sub-application
connector_app.include_router(connector_router)

# Mount connector sub-application
app.mount("/mcp/connector", connector_app)

# Add pagination support
add_pagination(app)
