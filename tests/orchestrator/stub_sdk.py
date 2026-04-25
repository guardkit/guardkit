"""Deterministic stub SDK harness for orchestrator-side specialist tests.

This module provides a ``StubSDKRecorder`` that replaces
``claude_agent_sdk.query`` during tests so the orchestrator's
``invoke_test_orchestrator`` and ``invoke_code_reviewer`` runners can be
exercised end-to-end without hitting the live Anthropic API.

The recorder:

* Records every SDK ``query(prompt, options)`` call (agent_type inferred
  from the prompt, plus ``allowed_tools`` and ``cwd`` captured from the
  ``options`` object).
* Writes a pre-baked ``phase_4_summary.json`` when the test-orchestrator
  is invoked, so the runner's ``_read_phase_4_summary`` returns realistic
  fields instead of all-zero defaults.
* Optionally raises a ``RuntimeError`` to simulate a Phase 4 failure
  (for the wiring's failure path).
* Yields a single ``ResultMessage`` so the consumer in
  ``AgentInvoker._invoke_with_role`` exits cleanly on the first iteration.

References:

* TASK-OSI-007 — this module's pre-merge gate.
* TASK-OSI-006 — the turn-loop wiring under test
  (``guardkit/orchestrator/autobuild.py`` L2625-2748).
* TASK-DIAG-F4A2 — the related stub-SDK pattern in
  ``tests/orchestrator/test_sdk_debug_preservation.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, List, Optional


@dataclass
class InvocationRecord:
    """One SDK invocation observed by :class:`StubSDKRecorder`.

    Attributes
    ----------
    agent_type:
        ``"test-orchestrator"``, ``"code-reviewer"``, or ``"unknown"``.
        Inferred from the prompt body; falls back to ``"unknown"`` when
        neither marker string is present (e.g. an unexpected agent).
    prompt_prefix:
        First 200 characters of the prompt — enough to pin down which
        specialist + which task without bloating the log.
    allowed_tools:
        Snapshot of ``options.allowed_tools`` at call time.
    cwd:
        Snapshot of ``options.cwd`` at call time.
    """

    agent_type: str
    prompt_prefix: str
    allowed_tools: List[str]
    cwd: str


# Default ``phase_4_summary.json`` content for a passing run. Mirrors the
# shape ``specialist_invocations._read_phase_4_summary`` expects.
_PHASE_4_SUMMARY_PASS: dict[str, Any] = {
    "tests_run": 12,
    "tests_failed": 0,
    "coverage_pct": 88.5,
    "output_summary": "All tests pass (stub)",
    "quality_gates_passed": True,
}


class StubSDKRecorder:
    """Drop-in replacement for ``claude_agent_sdk.query`` used in tests.

    Each call to :meth:`query` appends one :class:`InvocationRecord` to
    ``self.invocations``. When the inferred agent_type is
    ``test-orchestrator``, the recorder also writes a pre-baked
    ``phase_4_summary.json`` to the autobuild dir so the orchestrator's
    runner reads realistic numbers when it merges the phase_4 block.

    The recorder yields a single ``ResultMessage`` instance to terminate
    the consumer's ``async for`` loop. The class used for that instance
    is the one set on ``self.ResultMessage`` by
    :func:`build_mock_sdk_module` — the same class the test patches into
    ``sys.modules['claude_agent_sdk'].ResultMessage`` so that
    ``isinstance(message, ResultMessage)`` inside ``_invoke_with_role``
    evaluates to True.
    """

    def __init__(
        self,
        worktree_path: Path,
        task_id: str,
        *,
        fail_test_orchestrator: bool = False,
    ) -> None:
        """Initialize the recorder.

        Parameters
        ----------
        worktree_path:
            Worktree the runner operates against; used to compute the
            ``phase_4_summary.json`` path.
        task_id:
            AutoBuild task ID; used in the autobuild dir path.
        fail_test_orchestrator:
            If True, the recorder raises ``RuntimeError`` when the
            test-orchestrator is invoked. The runner catches this and
            returns ``status="failed"`` — exactly the path the wiring's
            Phase 5 skip branch depends on.
        """
        self.worktree_path = Path(worktree_path)
        self.task_id = task_id
        self.fail_test_orchestrator = fail_test_orchestrator
        self.invocations: List[InvocationRecord] = []
        # ResultMessage class assigned by build_mock_sdk_module() so the
        # consumer's ``isinstance(message, ResultMessage)`` check passes.
        self.ResultMessage: Optional[type] = None

    async def query(
        self, prompt: str, options: Any
    ) -> AsyncIterator[Any]:
        """Async generator standing in for ``claude_agent_sdk.query``."""
        agent_type = self._infer_agent_type(prompt)
        allowed_tools = list(getattr(options, "allowed_tools", None) or [])
        cwd = str(getattr(options, "cwd", "") or "")
        self.invocations.append(
            InvocationRecord(
                agent_type=agent_type,
                prompt_prefix=prompt[:200],
                allowed_tools=allowed_tools,
                cwd=cwd,
            )
        )

        if agent_type == "test-orchestrator":
            if self.fail_test_orchestrator:
                # Caught by run_specialist → status="failed".
                raise RuntimeError(
                    "stub: simulated test-orchestrator SDK failure"
                )
            self._write_phase_4_summary(_PHASE_4_SUMMARY_PASS)

        yield self._make_result_message()

    def _infer_agent_type(self, prompt: str) -> str:
        """Identify the specialist by a marker string in the prompt body.

        The runner-built prompts open with the line
        ``"You are the <name> specialist for task <id>."``, so a substring
        check on ``"<name> specialist"`` is unambiguous.
        """
        if "test-orchestrator specialist" in prompt:
            return "test-orchestrator"
        if "code-reviewer specialist" in prompt:
            return "code-reviewer"
        return "unknown"

    def _write_phase_4_summary(self, payload: dict[str, Any]) -> None:
        autobuild_dir = (
            self.worktree_path / ".guardkit" / "autobuild" / self.task_id
        )
        autobuild_dir.mkdir(parents=True, exist_ok=True)
        summary_path = autobuild_dir / "phase_4_summary.json"
        summary_path.write_text(json.dumps(payload), encoding="utf-8")

    def _make_result_message(self) -> Any:
        """Instantiate the ResultMessage class set by build_mock_sdk_module."""
        if self.ResultMessage is None:
            # Defensive fallback — tests should always wire ResultMessage
            # via build_mock_sdk_module(). Yields a bare object that fails
            # the isinstance check, which would loop forever; raise loudly
            # instead.
            raise RuntimeError(
                "StubSDKRecorder.ResultMessage is None — call "
                "build_mock_sdk_module(recorder) before running the SDK"
            )
        return self.ResultMessage()


class _StubOptions:
    """Lightweight stand-in for ``ClaudeAgentOptions``.

    The real class is a dataclass with ~15 fields. Tests don't need
    schema fidelity — they only need attribute access on the kwargs the
    orchestrator passes (``cwd``, ``allowed_tools``, ``permission_mode``,
    ``max_turns``, ``setting_sources``).
    """

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def build_mock_sdk_module(recorder: StubSDKRecorder) -> Any:
    """Build a ``claude_agent_sdk`` module replacement backed by ``recorder``.

    Returns a ``MagicMock`` with the symbols the orchestrator imports:
    ``query``, ``ClaudeAgentOptions``, exception classes, and the
    ``AssistantMessage`` / ``ResultMessage`` types. The recorder's
    ``ResultMessage`` attribute is bound to the same class exposed by the
    module so ``isinstance(message, ResultMessage)`` inside
    ``_invoke_with_role`` evaluates to True.
    """
    from unittest.mock import MagicMock

    class _MockResultMessage:
        """Sentinel ResultMessage carrying no fields the consumer needs."""

    class _MockAssistantMessage:
        """Sentinel AssistantMessage; consumer uses isinstance + .error."""

    recorder.ResultMessage = _MockResultMessage

    mock = MagicMock()
    mock.query = recorder.query
    mock.ClaudeAgentOptions = _StubOptions
    mock.AssistantMessage = _MockAssistantMessage
    mock.ResultMessage = _MockResultMessage
    mock.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
    mock.ProcessError = type(
        "ProcessError",
        (Exception,),
        {"exit_code": 1, "stderr": ""},
    )
    mock.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})
    return mock
