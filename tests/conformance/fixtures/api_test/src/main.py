"""FastAPI application initialization."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.core.etag import ETagMiddleware
from src.core.logging import setup_logging
from src.core.middleware import (
    APIVersionHeaderMiddleware,
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
)
from src.db.session import dispose_engine, init_engine
from src.health.router import router as health_router
from src.search.router import router as search_router
from src.stats.router import StatsCounterMiddleware
from src.stats.router import router as stats_router
from src.time.router import router as time_router
from src.uptime.router import router as uptime_router
from src.users.router import recent_router
from src.users.router import router as users_router
from src.version.router import router as version_router
from src.whoami.router import router as whoami_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup/shutdown events.

    On startup:
    - Configures structlog logging infrastructure
    - Initializes the database engine

    On shutdown:
    - Disposes of the database engine to clean up connections
    """
    # Configure logging on startup
    setup_logging()

    # Initialize database engine on startup
    init_engine()

    yield

    # Dispose of database engine on shutdown
    await dispose_engine()


app = FastAPI(
    redirect_slashes=False,
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description=(
        settings.app_description
        + "\n\n> All responses include an `X-API-Version` header."
    ),
    summary=settings.app_summary,
    contact={
        "name": settings.app_contact_name,
        "url": settings.app_contact_url,
        "email": settings.app_contact_email,
    },
    license_info={
        "name": settings.app_license_name,
        "url": settings.app_license_url,
    },
    terms_of_service=settings.app_terms_of_service,
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and status endpoints",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
        {
            "name": "whoami",
            "description": "Service identification endpoints",
        },
        {
            "name": "uptime",
            "description": "Service uptime information",
        },
        {
            "name": "stats",
            "description": "Service request statistics",
        },
        {
            "name": "time",
            "description": "Server time information",
        },
        {
            "name": "version",
            "description": "Version and build information",
        },
        {
            "name": "search",
            "description": "Search endpoints",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "tryItOutEnabled": True,
    },
    lifespan=lifespan,
)

# Register middleware: CorrelationID -> StatsCounter -> RequestLogging ->
# APIVersion -> ETag
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(StatsCounterMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(APIVersionHeaderMiddleware)
app.add_middleware(ETagMiddleware)

# Include health router with empty prefix so endpoint is at /health
app.include_router(health_router)

# Include whoami router with empty prefix so endpoint is at /whoami
app.include_router(whoami_router, tags=["whoami"])

# Include users router (prefix already set in router.py)
app.include_router(users_router, tags=["users"])

# Include recent-users router (prefix already set in router.py)
app.include_router(recent_router, tags=["users"])

# Include uptime router (prefix already set in router.py)
app.include_router(uptime_router, tags=["uptime"])

# Include stats router (prefix already set in router.py)
app.include_router(stats_router, tags=["stats"])

# Include time router (prefix already set in router.py)
app.include_router(time_router, tags=["time"])

# Include version router (prefix already set in router.py)
app.include_router(version_router, tags=["version"])

# Include search router (prefix already set in router.py)
app.include_router(search_router, tags=["search"])
