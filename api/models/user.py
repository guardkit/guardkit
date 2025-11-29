"""User data models for API validation and serialization."""

from pydantic import BaseModel, ConfigDict, EmailStr


class User(BaseModel):
    """
    User model representing a user entity.

    Attributes:
        id: Unique identifier for the user
        name: Full name of the user
        email: Valid email address
        is_active: Whether the user account is active
    """

    id: int
    name: str
    email: EmailStr
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "is_active": True
                }
            ]
        }
    )
