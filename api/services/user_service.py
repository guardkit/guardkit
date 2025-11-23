"""User service providing business logic for user operations."""

from typing import Dict

from api.exceptions import UserNotFoundError
from api.models.user import User


class UserService:
    """
    Service class for user-related business logic.

    This service manages user data operations. In a production environment,
    this would interact with a database. For demonstration purposes,
    it uses an in-memory dictionary.

    Attributes:
        _users: Mock database storing user data
    """

    def __init__(self):
        """Initialize the service with mock user data."""
        self._users: Dict[int, User] = {
            1: User(
                id=1,
                name="Alice Johnson",
                email="alice.johnson@example.com",
                is_active=True
            ),
            2: User(
                id=2,
                name="Bob Smith",
                email="bob.smith@example.com",
                is_active=True
            ),
            3: User(
                id=3,
                name="Charlie Brown",
                email="charlie.brown@example.com",
                is_active=False
            ),
        }

    def get_user(self, user_id: int) -> User:
        """
        Retrieve a user by their ID.

        Args:
            user_id: The unique identifier of the user to retrieve

        Returns:
            User object containing user data

        Raises:
            UserNotFoundError: If the user with the given ID doesn't exist
        """
        user = self._users.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user
