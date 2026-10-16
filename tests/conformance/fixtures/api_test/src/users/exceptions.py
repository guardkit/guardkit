"""Custom exceptions for users feature."""

from __future__ import annotations

from http import HTTPStatus

from fastapi import HTTPException


class UserNotFoundError(HTTPException):
    """Exception raised when a user is not found."""

    def __init__(self, user_id: str | None = None, email: str | None = None) -> None:
        if user_id:
            detail = f"User with id '{user_id}' not found"
        elif email:
            detail = f"User with email '{email}' not found"
        else:
            detail = "User not found"

        super().__init__(status_code=HTTPStatus.NOT_FOUND, detail=detail)


class UserAlreadyExistsError(HTTPException):
    """Exception raised when a user already exists."""

    def __init__(self, email: str | None = None) -> None:
        if email:
            detail = f"User with email '{email}' already exists"
        else:
            detail = "User already exists"

        super().__init__(status_code=HTTPStatus.CONFLICT, detail=detail)
