"""Custom exception classes for domain errors."""


class UserNotFoundError(Exception):
    """
    Exception raised when a user is not found in the system.

    This exception should be raised by service layer methods when
    attempting to retrieve a user that doesn't exist.

    Attributes:
        user_id: The ID of the user that was not found
        message: Human-readable error message
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.message = f"User with ID {user_id} not found"
        super().__init__(self.message)
