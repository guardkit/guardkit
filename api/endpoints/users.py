"""User API endpoints with dependency injection."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.exceptions import UserNotFoundError
from api.models.user import User
from api.services.user_service import UserService

# Create router for user endpoints
router = APIRouter(prefix="/users", tags=["users"])


def get_user_service() -> UserService:
    """
    Dependency provider for UserService.

    Returns:
        UserService instance for handling user operations
    """
    return UserService()


@router.get(
    "/{user_id}",
    response_model=User,
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieve a single user by their unique identifier",
    responses={
        200: {
            "description": "User found and returned successfully",
            "model": User,
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {"detail": "User with ID 999 not found"}
                }
            },
        },
        422: {
            "description": "Invalid user ID format",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def get_user(
    user_id: int,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    """
    Get a user by their ID.

    Args:
        user_id: The unique identifier of the user to retrieve
        user_service: Injected UserService dependency

    Returns:
        User object with user details

    Raises:
        HTTPException: 404 if user not found
    """
    try:
        return user_service.get_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
