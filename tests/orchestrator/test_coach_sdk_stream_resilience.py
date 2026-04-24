"""
Unit tests for TASK-FIX-7A09: Extend 7A03 defensive SDK handling to the
Coach independent-test path.

Covers three acceptance criteria on
``CoachValidator._run_tests_via_sdk`` and its caller
``CoachValidator.run_independent_tests``:

  (a) A ``ProcessError(exit_code=1, stderr=...)`` raised mid-stream in the
      SDK path lands in the outer fallback log line emitted from
      ``run_independent_tests`` — that log line must contain the
      structured ``error_class``/``exit_code`` context and a substring of
      the stderr head, *not* the opaque ``{e}`` repr the code used to
      emit.
  (b) A ``MessageParseError`` on a single message is non-terminal — the
      per-message try/except logs and skips the offending message so the
      turn continues with whatever valid messages follow.
  (c) A valid ``ResultMessage`` (well, a valid SDK message — we use
      ``UserMessage`` with a ``ToolResultBlock`` because that is the
      message type that carries real test output on this path) yielded
      *before* a ``ProcessError`` is still processed by the per-message
      handler — the narrow ``(MessageParseError, ValueError)`` catch does
      not swallow transport-level failures, so no silent data loss
      occurs.

Coverage Target: >=80% on the changed lines in
``guardkit/orchestrator/quality_gates/coach_validator.py::_run_tests_via_sdk``
and the fallback-log block in ``run_independent_tests``.
"""

import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import claude_agent_sdk
from claude_agent_sdk import (
    ProcessError,
    CLINotFoundError,
    CLIJSONDecodeError,
    UserMessage,
    ToolResultBlock,
)
from claude_agent_sdk._errors import MessageParseError

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------


class FakeAsyncGen:
    """Test double mimicking the async-iterable SDK query stream.

    The script is a list of ``("yield", msg)`` / ``("raise", exc)``
    tuples. Unlike a real Python async generator, this double lets the
    caller continue iterating after a raised exception — so the test
    script can simulate both "production shape" (exception terminates
    the generator and the next ``__anext__`` returns ``StopAsyncIteration``)
    and "recovery shape" (yield-after-raise) in the same harness.
    """

    def __init__(self, events):
        self._events = list(events)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        kind, payload = self._events.pop(0)
        if kind == "yield":
            return payload
        if kind == "raise":
            raise payload
        raise AssertionError(f"Unknown fake-gen event kind: {kind!r}")

    async def aclose(self):  # pragma: no cover - trivial
        return None


def _make_validator(tmp_path: Path, test_command: str = "pytest tests/dummy.py") -> CoachValidator:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return CoachValidator(
        worktree_path=str(worktree),
        test_command=test_command,
        test_timeout=30,
        task_id="TASK-TEST-7A09",
        coach_test_execution="sdk",
        matching_strategy="text",
        wave_size=1,
    )


def _user_tool_result_msg(
    text: str = "bash output line 1\nbash output line 2",
    is_error: bool = False,
) -> UserMessage:
    block = ToolResultBlock(
        tool_use_id="tu-1",
        content=[{"type": "text", "text": text}],
        is_error=is_error,
    )
    return UserMessage(content=[block])


# ----------------------------------------------------------------------
# AC (b): MessageParseError mid-stream is non-terminal
# ----------------------------------------------------------------------


class TestAC_B_MessageParseErrorNonTerminal:
    """AC (b): MessageParseError on one message → stream continues,
    per-message WARNING logged, post-stream summary WARNING records the
    drop count."""

    @pytest.mark.asyncio
    async def test_parse_error_then_valid_message_completes_turn(
        self, tmp_path, caplog
    ):
        validator = _make_validator(tmp_path)

        good = _user_tool_result_msg("tests passed", is_error=False)
        fake_gen = FakeAsyncGen([
            ("raise", MessageParseError(
                "Unknown message type: rate_limit_event",
                {"type": "rate_limit_event"},
            )),
            ("yield", good),
        ])

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                result = await validator._run_tests_via_sdk("pytest tests/dummy.py")

        # Turn completed without raising — the parse error was skipped,
        # the subsequent valid message was processed normally.
        assert isinstance(result, IndependentTestResult)
        # UserMessage with is_error=False → tests_passed=True path.
        assert result.tests_passed is True

        # Per-message WARNING names the error_class and the unknown type.
        per_msg_warnings = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(per_msg_warnings) == 1
        assert "MessageParseError" in per_msg_warnings[0].getMessage()
        assert "rate_limit_event" in per_msg_warnings[0].getMessage()

        # Post-stream summary WARNING records the drop count.
        summary = [
            r for r in caplog.records
            if "unparseable message(s) dropped" in r.getMessage()
        ]
        assert len(summary) == 1
        assert "1 unparseable" in summary[0].getMessage()

    @pytest.mark.asyncio
    async def test_valueerror_midstream_is_dropped_same_as_parse_error(
        self, tmp_path, caplog
    ):
        """The per-message catch is ``(MessageParseError, ValueError)`` —
        a stray ValueError (e.g. from the SDK's ``Unsupported plugin
        type`` raise) is dropped the same way with ``error_class``
        reflecting the concrete type."""
        validator = _make_validator(tmp_path)

        good = _user_tool_result_msg("tests passed", is_error=False)
        fake_gen = FakeAsyncGen([
            ("raise", ValueError("Unsupported plugin type: weird")),
            ("yield", good),
        ])

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
                result = await validator._run_tests_via_sdk("pytest tests/dummy.py")

        assert result.tests_passed is True

        drop_warns = [
            r for r in caplog.records
            if "Skipping unparseable SDK message" in r.getMessage()
        ]
        assert len(drop_warns) == 1
        assert "error_class=ValueError" in drop_warns[0].getMessage()


# ----------------------------------------------------------------------
# AC (c): Valid message before ProcessError is still processed
# ----------------------------------------------------------------------


class TestAC_C_ProcessErrorAfterValidMessage:
    """AC (c): A valid SDK message yielded before a mid-stream
    ``ProcessError`` is processed by the per-message handler. The
    narrow ``(MessageParseError, ValueError)`` catch does *not* swallow
    transport-level failures — ``ProcessError`` propagates out with its
    ``exit_code``/``stderr`` intact so the outer cascade can surface
    them."""

    @pytest.mark.asyncio
    async def test_user_message_processed_then_process_error_propagates(
        self, tmp_path
    ):
        validator = _make_validator(tmp_path)

        good = _user_tool_result_msg("tests collected 5 items", is_error=False)
        transport_err = ProcessError(
            "CLI subprocess exited unexpectedly",
            exit_code=1,
            stderr="bundled CLI crashed: out of memory",
        )
        fake_gen = FakeAsyncGen([
            ("yield", good),
            ("raise", transport_err),
        ])

        # Wrap _extract_content_text so we can observe it was called
        # during the valid-message processing pass before ProcessError
        # raised.
        original_extract = CoachValidator._extract_content_text
        call_log = []

        def spy_extract(content):
            result = original_extract(content)
            call_log.append((content, result))
            return result

        with patch.object(claude_agent_sdk, "query", return_value=fake_gen):
            with patch.object(
                CoachValidator,
                "_extract_content_text",
                staticmethod(spy_extract),
            ):
                with pytest.raises(ProcessError) as ei:
                    await validator._run_tests_via_sdk("pytest tests/dummy.py")

        # ProcessError propagated untouched — structured info intact.
        err = ei.value
        assert err.exit_code == 1
        assert err.stderr == "bundled CLI crashed: out of memory"

        # The valid UserMessage was processed before the ProcessError —
        # _extract_content_text was called with its ToolResultBlock
        # content. This proves the per-message defensive catch did not
        # swallow the valid message or short-circuit its handler.
        assert len(call_log) >= 1
        extracted = [result for _, result in call_log]
        assert any("tests collected 5 items" in text for text in extracted)


# ----------------------------------------------------------------------
# Inner exception-cascade coverage
# ----------------------------------------------------------------------


class TestInnerExceptionCascade:
    """Coverage for the split inner handlers inside
    ``_run_tests_via_sdk``. Each typed handler emits a structured
    ``error_class`` tag and re-raises the original exception untouched
    so the caller can introspect type and attributes."""

    @pytest.mark.asyncio
    async def test_cli_not_found_handler_logs_class_and_reraises(
        self, tmp_path, caplog
    ):
        validator = _make_validator(tmp_path)

        def boom(**kwargs):
            raise CLINotFoundError("Claude Code CLI binary not found on PATH")

        with caplog.at_level(
            logging.ERROR,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", side_effect=boom):
                with pytest.raises(CLINotFoundError):
                    await validator._run_tests_via_sdk("pytest tests/dummy.py")

        tagged = [
            r for r in caplog.records
            if "SDK coach test execution failed" in r.getMessage()
            and "error_class=CLINotFoundError" in r.getMessage()
        ]
        assert len(tagged) == 1

    @pytest.mark.asyncio
    async def test_cli_json_decode_handler_logs_class_and_reraises(
        self, tmp_path, caplog
    ):
        validator = _make_validator(tmp_path)

        def boom(**kwargs):
            raise CLIJSONDecodeError(
                "garbage line from CLI",
                ValueError("Expecting value"),
            )

        with caplog.at_level(
            logging.ERROR,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", side_effect=boom):
                with pytest.raises(CLIJSONDecodeError):
                    await validator._run_tests_via_sdk("pytest tests/dummy.py")

        tagged = [
            r for r in caplog.records
            if "SDK coach test execution failed" in r.getMessage()
            and "error_class=CLIJSONDecodeError" in r.getMessage()
        ]
        assert len(tagged) == 1

    @pytest.mark.asyncio
    async def test_process_error_inner_handler_captures_exit_code_and_stderr(
        self, tmp_path, caplog
    ):
        """The ``ProcessError`` inner handler emits a log line carrying
        the ``exit_code`` and a head of the ``stderr`` for downstream
        diagnosis — separate from the fallback log in the caller."""
        validator = _make_validator(tmp_path)

        stderr_text = "transport-layer failure: exit=1\nstack trace..."

        def boom(**kwargs):
            raise ProcessError(
                "CLI subprocess failed",
                exit_code=1,
                stderr=stderr_text,
            )

        with caplog.at_level(
            logging.ERROR,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", side_effect=boom):
                with pytest.raises(ProcessError) as ei:
                    await validator._run_tests_via_sdk("pytest tests/dummy.py")

        # Structured inner log emitted.
        tagged = [
            r for r in caplog.records
            if "SDK coach test execution failed" in r.getMessage()
            and "error_class=ProcessError" in r.getMessage()
        ]
        assert len(tagged) == 1
        inner_msg = tagged[0].getMessage()
        assert "exit_code=1" in inner_msg
        assert "transport-layer failure" in inner_msg

        # Original exception passes through untouched for the caller.
        assert ei.value.exit_code == 1
        assert ei.value.stderr == stderr_text

    @pytest.mark.asyncio
    async def test_blanket_exception_handler_tags_concrete_class_name(
        self, tmp_path, caplog
    ):
        """Unknown exception types (RuntimeError here) hit the bare
        ``except Exception`` clause which tags ``type(e).__name__`` on
        the log line."""
        validator = _make_validator(tmp_path)

        def boom(**kwargs):
            raise RuntimeError("some unexpected transport failure")

        with caplog.at_level(
            logging.ERROR,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(claude_agent_sdk, "query", side_effect=boom):
                with pytest.raises(RuntimeError):
                    await validator._run_tests_via_sdk("pytest tests/dummy.py")

        tagged = [
            r for r in caplog.records
            if "SDK coach test execution failed" in r.getMessage()
            and "error_class=RuntimeError" in r.getMessage()
        ]
        assert len(tagged) == 1


# ----------------------------------------------------------------------
# AC (a): ProcessError from SDK path → structured fallback log
# ----------------------------------------------------------------------


class TestAC_A_FallbackLogStructuredShape:
    """AC (a): When ``_run_tests_via_sdk`` raises ``ProcessError``, the
    fallback log line in ``run_independent_tests`` must surface the
    error_class, exit_code, and a head of the stderr instead of the old
    opaque ``{e}`` repr."""

    def test_process_error_fallback_log_contains_exit_code_and_stderr(
        self, tmp_path, caplog, monkeypatch
    ):
        validator = _make_validator(tmp_path)

        stderr_text = (
            "bundled CLI crashed: out of memory\n"
            "  at claude_agent_sdk/internal/transport/subprocess_cli.py:123"
        )
        transport_err = ProcessError(
            "CLI subprocess exited unexpectedly",
            exit_code=1,
            stderr=stderr_text,
        )

        async def failing_sdk(self, test_cmd):
            raise transport_err

        # Neutralise the subprocess fallback so the test does not
        # actually run pytest — we only care about the log line the SDK
        # branch emitted before the fall-through.
        fake_completed = MagicMock(returncode=0, stdout="1 passed", stderr="")
        # ANTHROPIC_BASE_URL must not point to a non-Anthropic endpoint,
        # or _is_custom_api_base() would force the subprocess path and
        # skip the SDK branch entirely.
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(
                CoachValidator,
                "_run_tests_via_sdk",
                new=failing_sdk,
            ):
                with patch(
                    "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
                    return_value=fake_completed,
                ):
                    result = validator.run_independent_tests(
                        task_work_results={},
                        task=None,
                        turn=1,
                    )

        # Fallback path returned the subprocess result.
        assert result.tests_passed is True

        # Exactly one warning should be the new structured fallback log.
        fallback_warnings = [
            r for r in caplog.records
            if "falling back to subprocess" in r.getMessage()
            and "SDK test execution failed" in r.getMessage()
        ]
        assert len(fallback_warnings) == 1
        fallback_msg = fallback_warnings[0].getMessage()

        # Structured context fields present.
        assert "error_class=ProcessError" in fallback_msg
        assert "exit_code=1" in fallback_msg
        # A substring of the stderr head is included, not the whole
        # message.
        assert "bundled CLI crashed: out of memory" in fallback_msg

    def test_non_process_error_fallback_log_emits_class_without_exit_code(
        self, tmp_path, caplog, monkeypatch
    ):
        """Generic exceptions without ``exit_code``/``stderr`` attributes
        still get a structured fallback log (error_class only, no
        exit_code component)."""
        validator = _make_validator(tmp_path)

        class _WeirdTransportError(RuntimeError):
            pass

        async def failing_sdk(self, test_cmd):
            raise _WeirdTransportError("something odd happened")

        fake_completed = MagicMock(returncode=0, stdout="1 passed", stderr="")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        with caplog.at_level(
            logging.WARNING,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            with patch.object(
                CoachValidator,
                "_run_tests_via_sdk",
                new=failing_sdk,
            ):
                with patch(
                    "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
                    return_value=fake_completed,
                ):
                    validator.run_independent_tests(
                        task_work_results={},
                        task=None,
                        turn=1,
                    )

        fallback_warnings = [
            r for r in caplog.records
            if "falling back to subprocess" in r.getMessage()
            and "SDK test execution failed" in r.getMessage()
        ]
        assert len(fallback_warnings) == 1
        fallback_msg = fallback_warnings[0].getMessage()
        assert "error_class=_WeirdTransportError" in fallback_msg
        # No exit_code attribute on the exception — the log omits it.
        assert "exit_code=" not in fallback_msg
