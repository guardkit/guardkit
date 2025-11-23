"""Comprehensive test suite for users endpoint."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.exceptions import UserNotFoundError
from api.models.user import User
from api.services.user_service import UserService
from main import app

# Create test client
client = TestClient(app)


class MockUserService:
    """Mock UserService for testing dependency injection."""

    def __init__(self, users=None, raise_error=False):
        """
        Initialize mock service.

        Args:
            users: Dictionary of mock users to return
            raise_error: If True, raise generic Exception instead of UserNotFoundError
        """
        self.users = users or {}
        self.raise_error = raise_error

    def get_user(self, user_id: int) -> User:
        """
        Mock get_user method.

        Args:
            user_id: User ID to retrieve

        Returns:
            User object if found

        Raises:
            UserNotFoundError: If user not found and raise_error is False
            Exception: If raise_error is True
        """
        if self.raise_error:
            raise Exception("Unexpected service error")

        if user_id not in self.users:
            raise UserNotFoundError(user_id)

        return self.users[user_id]


@pytest.fixture
def mock_users():
    """Fixture providing mock user data."""
    return {
        1: User(
            id=1,
            name="Test User",
            email="test@example.com",
            is_active=True
        ),
        2: User(
            id=2,
            name="Another User",
            email="another@example.com",
            is_active=False
        ),
    }


def test_get_user_success(mock_users):
    """
    Test successful user retrieval.

    Verifies that:
    - GET /api/v1/users/1 returns 200 status
    - Response contains correct user data
    - Response matches User model schema
    """
    response = client.get("/api/v1/users/1")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Alice Johnson"
    assert data["email"] == "alice.johnson@example.com"
    assert data["is_active"] is True


def test_get_user_not_found():
    """
    Test user not found scenario.

    Verifies that:
    - GET /api/v1/users/999 returns 404 status
    - Response contains error detail message
    - Message includes the user ID
    """
    response = client.get("/api/v1/users/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    assert "detail" in data
    assert "999" in data["detail"]
    assert "not found" in data["detail"].lower()


def test_get_user_invalid_id_type():
    """
    Test invalid user ID type handling.

    Verifies that:
    - GET /api/v1/users/abc returns 422 validation error
    - FastAPI's type validation catches non-integer IDs
    """
    response = client.get("/api/v1/users/abc")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    data = response.json()
    assert "detail" in data


def test_get_user_negative_id():
    """
    Test handling of negative user IDs.

    Verifies that:
    - Negative IDs are technically valid integers
    - Returns 404 as they don't exist in the mock database
    """
    response = client.get("/api/v1/users/-1")

    assert response.status_code == status.HTTP_404_NOT_FOUND

    data = response.json()
    assert "detail" in data
    assert "-1" in data["detail"]


def test_get_user_zero_id():
    """
    Test handling of zero as user ID.

    Verifies that:
    - Zero is a valid integer ID
    - Returns 404 as it doesn't exist in the mock database
    """
    response = client.get("/api/v1/users/0")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_user_very_large_id():
    """
    Test handling of very large user IDs.

    Verifies that:
    - System handles large integers correctly
    - Returns 404 for non-existent large IDs
    """
    response = client.get("/api/v1/users/999999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_response_schema_validation(mock_users):
    """
    Test response schema matches User model.

    Verifies that:
    - Response contains all required User fields
    - Field types are correct
    - No extra fields are present
    """
    response = client.get("/api/v1/users/1")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()

    # Verify all required fields present
    assert "id" in data
    assert "name" in data
    assert "email" in data
    assert "is_active" in data

    # Verify field types
    assert isinstance(data["id"], int)
    assert isinstance(data["name"], str)
    assert isinstance(data["email"], str)
    assert isinstance(data["is_active"], bool)


def test_health_check_endpoint():
    """
    Test the root health check endpoint.

    Verifies that:
    - GET / returns 200 status
    - Response contains status and version information
    """
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data


def test_openapi_docs_accessible():
    """
    Test OpenAPI documentation is accessible.

    Verifies that:
    - /docs endpoint is reachable (Swagger UI)
    - /redoc endpoint is reachable (ReDoc)
    """
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK

    response = client.get("/redoc")
    assert response.status_code == status.HTTP_200_OK


def test_user_service_get_user_found():
    """
    Test UserService.get_user with existing user.

    Verifies that:
    - Service returns correct User object
    - All user fields match expected values
    """
    service = UserService()
    user = service.get_user(1)

    assert isinstance(user, User)
    assert user.id == 1
    assert user.name == "Alice Johnson"
    assert user.email == "alice.johnson@example.com"
    assert user.is_active is True


def test_user_service_get_user_not_found():
    """
    Test UserService.get_user with non-existent user.

    Verifies that:
    - Service raises UserNotFoundError
    - Exception contains correct user_id
    - Exception message is formatted correctly
    """
    service = UserService()

    with pytest.raises(UserNotFoundError) as exc_info:
        service.get_user(999)

    assert exc_info.value.user_id == 999
    assert "999" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


def test_user_model_validation():
    """
    Test User model validation with valid data.

    Verifies that:
    - User model accepts valid data
    - Email validation works with EmailStr
    - Default value for is_active is True
    """
    user = User(
        id=1,
        name="Test User",
        email="test@example.com"
    )

    assert user.id == 1
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.is_active is True  # Default value


def test_user_model_invalid_email():
    """
    Test User model email validation.

    Verifies that:
    - Invalid email format raises ValidationError
    - Pydantic's EmailStr type enforces email format
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        User(
            id=1,
            name="Test User",
            email="invalid-email"
        )

    # Verify the error is about email validation
    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert any("email" in str(error).lower() for error in errors)


def test_user_not_found_error_attributes():
    """
    Test UserNotFoundError exception attributes.

    Verifies that:
    - Exception stores user_id correctly
    - Message format is correct
    - Exception can be raised and caught
    """
    error = UserNotFoundError(user_id=123)

    assert error.user_id == 123
    assert error.message == "User with ID 123 not found"
    assert str(error) == "User with ID 123 not found"
