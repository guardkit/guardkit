"""Shared SDK utilities for AssistantMessage error handling (bug #472 defense)."""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def check_assistant_message_error(message: Any) -> Optional[str]:
    """Check if an AssistantMessage carries a bug #472 API error.

    SDK v0.1.9+ may return API errors as AssistantMessage with .error set
    rather than raising an exception (GitHub Issue #472).

    Parameters
    ----------
    message : Any
        A message from the SDK query() stream

    Returns
    -------
    Optional[str]
        Error string if error detected, None otherwise
    """
    if hasattr(message, 'error') and message.error is not None:
        return str(message.error)
    return None
