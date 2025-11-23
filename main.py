"""FastAPI application initialization and configuration."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from api.endpoints import users
from api.exceptions import UserNotFoundError

# Create FastAPI application instance
app = FastAPI(
    title="User Management API",
    description="RESTful API for managing users with dependency injection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(UserNotFoundError)
async def user_not_found_exception_handler(
    request: Request, exc: UserNotFoundError
) -> JSONResponse:
    """
    Global exception handler for UserNotFoundError.

    Args:
        request: The incoming request that caused the exception
        exc: The UserNotFoundError exception instance

    Returns:
        JSONResponse with 404 status and error details
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


# Include routers with API versioning prefix
app.include_router(users.router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def root() -> dict:
    """
    Root endpoint for health check.

    Returns:
        Dictionary with status and API version
    """
    return {
        "status": "healthy",
        "message": "User Management API is running",
        "version": "1.0.0",
    }
