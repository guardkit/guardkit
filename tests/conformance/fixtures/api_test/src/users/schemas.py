"""Pydantic schemas for users."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


class UserBase(BaseModel):
    """Base schema for user operations."""

    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                }
            ]
        }
    )


class DomainCountResponse(BaseModel):
    """Schema for domain count entries."""

    domain: str
    count: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "domain": "example.com",
                    "count": 5,
                }
            ]
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                }
            ]
        }
    )


class UserPublic(BaseModel):
    """Schema for user responses.

    Includes id, name (derived from full_name), and email as per ASSUM-001.
    """

    id: str
    email: EmailStr
    name: str | None = None
    full_name: str | None = None
    is_active: bool = True
    created_at: str
    updated_at: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "john.doe@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ]
        },
    )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def format_datetime(cls, v: datetime | str) -> str:
        """Format datetime to ISO format string."""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    @model_validator(mode="after")
    def populate_name_from_full_name(self) -> UserPublic:
        """Populate the name field from full_name if name is not set.

        Ensures the response includes 'name' as required by ASSUM-001.
        """
        if self.name is None and self.full_name is not None:
            self.name = self.full_name
        return self


class UserCountResponse(BaseModel):
    """Schema for user count responses."""

    count: int

    model_config = ConfigDict(json_schema_extra={"examples": [{"count": 42}]})


class UserSummaryResponse(BaseModel):
    """Schema for user summary responses."""

    username: str
    display_name: str
    profile_metadata: dict[str, str]
    days_since_created: int
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "john.doe@example.com",
                    "display_name": "John Doe",
                    "profile_metadata": {
                        "email": "john.doe@example.com",
                        "status": "active",
                    },
                    "days_since_created": 365,
                    "is_active": True,
                }
            ]
        }
    )


class UserList(BaseModel):
    """Schema for paginated user list responses."""

    items: list[UserPublic]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "john.doe@example.com",
                            "full_name": "John Doe",
                            "is_active": True,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                        }
                    ],
                    "total": 1,
                }
            ]
        }
    )


class RecentUsersResponse(BaseModel):
    """Schema for recent users responses."""

    users: list[UserPublic]
    total: int

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "users": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "email": "john.doe@example.com",
                            "full_name": "John Doe",
                            "is_active": True,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                        }
                    ],
                    "total": 1,
                }
            ]
        }
    )
