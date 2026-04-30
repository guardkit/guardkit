"""Tests for the SDK message-reader dedup filter (TASK-FIX-A7B5 AC-004)."""
from __future__ import annotations

import logging

import pytest

from guardkit.orchestrator.sdk_utils import (
    MessageReaderDedupFilter,
    install_sdk_message_reader_dedup_filter,
)

_SDK_QUERY_LOGGER_NAME = "claude_agent_sdk._internal.query"
_DEDUP_TOKEN = "Fatal error in message reader"
_INSTALL_FLAG_ATTR = "_guardkit_message_reader_dedup_installed"


def _make_record(message: str, level: int = logging.ERROR) -> logging.LogRecord:
    return logging.LogRecord(
        name=_SDK_QUERY_LOGGER_NAME,
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )


class TestMessageReaderDedupFilter:
    def test_first_match_demoted_to_warning(self) -> None:
        flt = MessageReaderDedupFilter()
        record = _make_record(f"{_DEDUP_TOKEN}: Command failed with exit code 1")

        assert flt.filter(record) is True
        assert record.levelno == logging.WARNING
        assert record.levelname == "WARNING"

    def test_subsequent_matches_demoted_to_debug(self) -> None:
        flt = MessageReaderDedupFilter()
        first = _make_record(f"{_DEDUP_TOKEN}: Command failed with exit code 1")
        second = _make_record(f"{_DEDUP_TOKEN}: Command failed with exit code 1")
        third = _make_record(f"{_DEDUP_TOKEN}: Command failed with exit code 1")

        flt.filter(first)
        flt.filter(second)
        flt.filter(third)

        assert first.levelname == "WARNING"
        assert second.levelno == logging.DEBUG
        assert second.levelname == "DEBUG"
        assert third.levelno == logging.DEBUG

    def test_unrelated_error_passes_through_unchanged(self) -> None:
        flt = MessageReaderDedupFilter()
        record = _make_record("some unrelated SDK error", level=logging.ERROR)

        assert flt.filter(record) is True
        assert record.levelno == logging.ERROR
        assert record.levelname == "ERROR"

    def test_token_substring_match_inside_longer_message(self) -> None:
        flt = MessageReaderDedupFilter()
        record = _make_record(
            f"prefix noise {_DEDUP_TOKEN}: Command failed with exit code 1 trailing"
        )

        flt.filter(record)
        assert record.levelname == "WARNING"

    def test_filter_never_drops_records(self) -> None:
        # Filter must always return True — handlers do level filtering.
        flt = MessageReaderDedupFilter()
        match = _make_record(f"{_DEDUP_TOKEN}: x")
        unrelated = _make_record("unrelated")
        assert flt.filter(match) is True
        assert flt.filter(unrelated) is True


class TestInstallIdempotency:
    @pytest.fixture(autouse=True)
    def _reset_logger(self):
        sdk_logger = logging.getLogger(_SDK_QUERY_LOGGER_NAME)
        original_filters = list(sdk_logger.filters)
        had_flag = hasattr(sdk_logger, _INSTALL_FLAG_ATTR)
        original_flag = getattr(sdk_logger, _INSTALL_FLAG_ATTR, False)
        # Strip filter + flag so each test sees a clean slate.
        sdk_logger.filters = [
            f for f in sdk_logger.filters
            if not isinstance(f, MessageReaderDedupFilter)
        ]
        if had_flag:
            delattr(sdk_logger, _INSTALL_FLAG_ATTR)

        yield

        sdk_logger.filters = original_filters
        if had_flag:
            setattr(sdk_logger, _INSTALL_FLAG_ATTR, original_flag)
        elif hasattr(sdk_logger, _INSTALL_FLAG_ATTR):
            delattr(sdk_logger, _INSTALL_FLAG_ATTR)

    def test_install_attaches_filter_once(self) -> None:
        sdk_logger = logging.getLogger(_SDK_QUERY_LOGGER_NAME)
        install_sdk_message_reader_dedup_filter()

        dedup_filters = [
            f for f in sdk_logger.filters
            if isinstance(f, MessageReaderDedupFilter)
        ]
        assert len(dedup_filters) == 1
        assert getattr(sdk_logger, _INSTALL_FLAG_ATTR) is True

    def test_install_is_idempotent(self) -> None:
        sdk_logger = logging.getLogger(_SDK_QUERY_LOGGER_NAME)
        install_sdk_message_reader_dedup_filter()
        install_sdk_message_reader_dedup_filter()
        install_sdk_message_reader_dedup_filter()

        dedup_filters = [
            f for f in sdk_logger.filters
            if isinstance(f, MessageReaderDedupFilter)
        ]
        assert len(dedup_filters) == 1

    def test_installed_filter_demotes_real_log_calls(self, caplog) -> None:
        install_sdk_message_reader_dedup_filter()
        sdk_logger = logging.getLogger(_SDK_QUERY_LOGGER_NAME)

        with caplog.at_level(logging.DEBUG, logger=_SDK_QUERY_LOGGER_NAME):
            sdk_logger.error(f"{_DEDUP_TOKEN}: Command failed with exit code 1")
            sdk_logger.error(f"{_DEDUP_TOKEN}: Command failed with exit code 1")
            sdk_logger.error("unrelated upstream error")

        records = [r for r in caplog.records if r.name == _SDK_QUERY_LOGGER_NAME]
        # Three records were emitted; the filter mutates the level of
        # the matching ones before handlers see them.
        matching = [r for r in records if _DEDUP_TOKEN in r.getMessage()]
        unrelated = [r for r in records if _DEDUP_TOKEN not in r.getMessage()]

        assert len(matching) == 2
        assert matching[0].levelname == "WARNING"
        assert matching[1].levelname == "DEBUG"
        assert len(unrelated) == 1
        assert unrelated[0].levelname == "ERROR"
