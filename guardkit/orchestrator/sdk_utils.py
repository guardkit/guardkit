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


# ---------------------------------------------------------------------------
# Message-reader transport-noise dedup filter (TASK-FIX-A7B5, AC-004)
#
# Upstream claude_agent_sdk._internal.query.read_messages() emits an
# ERROR-level "Fatal error in message reader: Command failed with exit
# code 1" line every time the wrapped `claude` CLI subprocess exits
# non-zero after delivering its result. Coach's SDK-first dispatch
# already catches the underlying ProcessError and falls back to direct
# subprocess execution (see coach_validator.run_independent_tests), so
# the line is benign — but it fires once per Coach gate and dominates
# autobuild run output.
#
# Real root cause is blocked on TASK-REV-COSE landing real CLI stderr
# capture. Until then this filter promotes the FIRST occurrence per
# process to WARNING (so the noise still surfaces once for visibility)
# and demotes subsequent occurrences to DEBUG (silenced under default
# INFO logging). See docs/reviews/TASK-FIX-A7B5-sdk-message-reader-
# investigation.md for the full deferral note.
# ---------------------------------------------------------------------------

_SDK_QUERY_LOGGER_NAME = "claude_agent_sdk._internal.query"
_DEDUP_TOKEN = "Fatal error in message reader"
_INSTALL_FLAG_ATTR = "_guardkit_message_reader_dedup_installed"


class MessageReaderDedupFilter(logging.Filter):
    """Demote upstream message-reader transport-noise log records.

    First match per filter instance: ERROR → WARNING.
    Subsequent matches: ERROR → DEBUG.
    Non-matching records pass through unchanged.
    """

    def __init__(self) -> None:
        super().__init__()
        self._seen = False

    def filter(self, record: logging.LogRecord) -> bool:
        if _DEDUP_TOKEN in record.getMessage():
            if self._seen:
                record.levelno = logging.DEBUG
                record.levelname = "DEBUG"
            else:
                record.levelno = logging.WARNING
                record.levelname = "WARNING"
                self._seen = True
        return True


def install_sdk_message_reader_dedup_filter() -> None:
    """Idempotently attach the dedup filter to the SDK query logger.

    Safe to call from any SDK invocation site — a flag on the logger
    object prevents double-attachment when called from multiple
    entry points or repeatedly within one process.
    """
    sdk_logger = logging.getLogger(_SDK_QUERY_LOGGER_NAME)
    if getattr(sdk_logger, _INSTALL_FLAG_ATTR, False):
        return
    sdk_logger.addFilter(MessageReaderDedupFilter())
    setattr(sdk_logger, _INSTALL_FLAG_ATTR, True)
