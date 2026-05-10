"""Producer-side fold for ``task_work_results.code_review.score`` (TASK-FIX-DF51).

Regression test for the canonical *runner-without-producer* anti-pattern (sibling
of TASK-FIX-RWOP1.3.1 / TASK-FIX-RWOP1.3.2): under the OSI architecture the
orchestrator-invoked ``code-reviewer`` specialist completes successfully but no
upstream producer was writing the ``code_review.score`` key the Coach gate
reads at ``coach_validator.py:1709``. Default-to-0 → ``arch_review_passed=False``
forever → ``MAX_TURNS_EXCEEDED`` regardless of actual review quality.

Reproducer: TASK-OBS-ABST autobuild run, 2026-05-10. Coach rejected all 5 turns
with ``must_fix/architectural`` despite the code-reviewer agent completing
cleanly in turn 5 (403s of work). The on-disk ``task_work_results.json`` had no
``code_review`` key.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ==================== Fixtures ====================


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Empty worktree the AgentInvoker can be constructed against."""
    (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    """AgentInvoker scoped to a temp worktree.

    The fold under test (``_compute_code_review_block``) is pure-computational
    and doesn't touch the worktree, so a minimal AgentInvoker is enough.
    """
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=1,
        sdk_timeout_seconds=10,
    )


def _phase5_invocation(
    *,
    status: str,
    source: str = "orchestrator",
    error: str | None = None,
) -> dict:
    """Build a synthetic Phase-5 ``agent_invocations`` entry.

    Mirrors the shape :meth:`AgentInvoker._inject_specialist_records_into_task_work_results`
    writes after merging ``specialist_results.json``'s ``phase_5`` block.
    """
    inv: dict = {
        "phase": "5",
        "agent": "code-reviewer",
        "status": status,
        "source": source,
        "duration_seconds": 403.13,
    }
    if error is not None:
        inv["error"] = error
    return inv


def _baseline_results(invocations: list[dict] | None) -> dict:
    """Synthetic ``task_work_results.json`` shape missing ``code_review``.

    Mirrors the on-disk capture from
    ``.guardkit/worktrees/TASK-OBS-ABST/.guardkit/autobuild/TASK-OBS-ABST/task_work_results.json``
    (2026-05-10): top-level keys present, ``code_review`` and
    ``architectural_review`` absent, ``agent_invocations`` carrying the
    orchestrator-invoked Phase-5 record.
    """
    results: dict = {
        "task_id": "TASK-OBS-ABST",
        "completed": True,
        "phases": {
            "phase_3": {"detected": True, "text": "Implementation", "completed": True}
        },
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 12,
            "tests_failed": 0,
            "coverage": 85.5,
            "coverage_met": True,
            "all_passed": True,
        },
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }
    if invocations is not None:
        results["agent_invocations"] = invocations
    return results


# ==================== AC-001: Score round-trips into code_review.score ====================


class TestProducerFoldSynthesisOnCompletion:
    """When the orchestrator-invoked Phase-5 specialist completes cleanly,
    the producer fold synthesises ``code_review = {score, status, source}``."""

    def test_completed_phase5_yields_score_100(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results([_phase5_invocation(status="completed")])

        block = invoker._compute_code_review_block(results)

        assert block is not None
        assert block["score"] == 100
        assert block["status"] == "completed"
        assert block["source"] == "orchestrator_specialist_completion"

    def test_completed_phase5_score_is_int_in_0_100_range(
        self, invoker: AgentInvoker
    ) -> None:
        """AC-001 contract: ``score`` is an integer in the 0-100 range."""
        results = _baseline_results([_phase5_invocation(status="completed")])

        block = invoker._compute_code_review_block(results)

        assert isinstance(block["score"], int)
        assert 0 <= block["score"] <= 100

    def test_completed_phase5_status_is_string(
        self, invoker: AgentInvoker
    ) -> None:
        """AC-001 contract: ``status`` is a string."""
        results = _baseline_results([_phase5_invocation(status="completed")])

        block = invoker._compute_code_review_block(results)

        assert isinstance(block["status"], str)


# ==================== AC-002: Coach reads code_review.score and gate clears ====================


class TestCoachGateClearsAfterFold:
    """End-to-end: synthesised block → ``CoachValidator.verify_quality_gates``
    returns ``arch_review_passed=True`` for the FEATURE profile (threshold 60).

    The producer-side fix MUST keep the consumer reading
    ``task_work_results["code_review"]["score"]`` at
    ``coach_validator.py:1709`` (do not silently relocate the consumer).
    """

    def test_arch_review_passes_after_producer_fold(
        self,
        invoker: AgentInvoker,
        worktree: Path,
    ) -> None:
        results = _baseline_results([_phase5_invocation(status="completed")])
        # Sanity-check the reproducer state: no ``code_review`` key on disk
        # before the fold runs.
        assert "code_review" not in results

        block = invoker._compute_code_review_block(results)
        assert block is not None
        results["code_review"] = block

        validator = CoachValidator(worktree_path=str(worktree))
        status = validator.verify_quality_gates(
            results,
            profile=get_profile(TaskType.FEATURE),
        )

        assert status.arch_review_passed is True
        assert status.arch_review_required is True

    def test_arch_review_fails_when_phase5_failed(
        self,
        invoker: AgentInvoker,
        worktree: Path,
    ) -> None:
        """AC-005 corollary: explicit specialist failure surfaces as score=0
        and the gate correctly fails (not masked by the synthesis path)."""
        results = _baseline_results(
            [_phase5_invocation(status="failed", error="SDK timeout")]
        )

        block = invoker._compute_code_review_block(results)
        assert block is not None
        assert block["score"] == 0
        assert block["status"] == "failed"
        assert block["source"] == "orchestrator_specialist_failure"
        assert block["error"] == "SDK timeout"

        results["code_review"] = block
        validator = CoachValidator(worktree_path=str(worktree))
        status = validator.verify_quality_gates(
            results,
            profile=get_profile(TaskType.FEATURE),
        )

        assert status.arch_review_passed is False


# ==================== AC-003: Stack-specific subscores preserved (best-effort) ====================


class TestSubscoresPreservation:
    """If the Player stream emitted SOLID/DRY/YAGNI subscores into
    ``code_review`` (legacy ``architectural_review`` extraction in
    ``_write_task_work_results``), the fold MUST leave the existing block
    untouched. The fold only synthesises when no measured score is on disk.
    """

    def test_existing_player_stream_block_is_preserved(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results([_phase5_invocation(status="completed")])
        results["code_review"] = {
            "score": 85,
            "solid": 28,
            "dry": 29,
            "yagni": 28,
        }

        block = invoker._compute_code_review_block(results)

        # ``None`` signals "leave existing block alone" — the Player-stream
        # path remains authoritative whenever it captured a real score.
        assert block is None

    def test_existing_block_without_score_is_overridden(
        self, invoker: AgentInvoker
    ) -> None:
        """Edge case: a partial ``code_review`` dict without a ``score`` field
        does NOT block the fold (no measured signal to preserve)."""
        results = _baseline_results([_phase5_invocation(status="completed")])
        results["code_review"] = {"status": "in_progress"}

        block = invoker._compute_code_review_block(results)

        assert block is not None
        assert block["score"] == 100


# ==================== AC-005: Validator-error fallback unchanged ====================


class TestFalsePositiveSuppression:
    """The fold MUST NOT mask genuine code-review failures by writing a
    synthesised pass when no clean completion is on record. Specifically:

    - skipped Phase-5 → no key written → default-to-0 fires
    - missing Phase-5 record → no key written → default-to-0 fires
    - missing ``agent_invocations`` list → no key written → default-to-0 fires
    """

    def test_skipped_phase5_writes_no_block(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results([_phase5_invocation(status="skipped")])

        block = invoker._compute_code_review_block(results)

        assert block is None

    def test_missing_phase5_writes_no_block(
        self, invoker: AgentInvoker
    ) -> None:
        # Only Phase-4 invoked, no Phase-5 record at all.
        phase4 = {
            "phase": "4",
            "agent": "test-orchestrator",
            "status": "completed",
            "source": "orchestrator",
        }
        results = _baseline_results([phase4])

        block = invoker._compute_code_review_block(results)

        assert block is None

    def test_missing_invocations_list_writes_no_block(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results(invocations=None)
        assert "agent_invocations" not in results

        block = invoker._compute_code_review_block(results)

        assert block is None

    def test_player_sourced_phase5_does_not_trigger_synthesis(
        self, invoker: AgentInvoker
    ) -> None:
        """The synthesis path is gated to ``source == "orchestrator"`` because
        Player-sourced Phase-5 entries are dropped during specialist injection
        (see ``_inject_specialist_records_into_task_work_results``). A stale
        Player record must not trigger synthesis on its own — it could be a
        forged claim that the Player ran Phase 5 when it didn't.
        """
        player_phase5 = _phase5_invocation(status="completed", source="player")
        results = _baseline_results([player_phase5])

        block = invoker._compute_code_review_block(results)

        assert block is None

    def test_default_to_zero_path_still_applies_when_block_absent(
        self, invoker: AgentInvoker, worktree: Path
    ) -> None:
        """End-to-end AC-005: when the fold produces ``None``, the on-disk
        ``code_review`` key is left absent and the consumer's
        ``code_review.get("score", 0)`` default-to-0 still fails the gate.
        """
        results = _baseline_results([_phase5_invocation(status="skipped")])
        block = invoker._compute_code_review_block(results)
        assert block is None
        # Producer would NOT add the key in this branch.
        assert "code_review" not in results

        validator = CoachValidator(worktree_path=str(worktree))
        status = validator.verify_quality_gates(
            results,
            profile=get_profile(TaskType.FEATURE),
        )

        assert status.arch_review_passed is False


# ==================== Defensive: malformed inputs are silently ignored ====================


class TestDefensiveAgainstMalformedInputs:
    """The fold never raises. Malformed entries fall through to the next
    candidate or to the default ``None`` return."""

    def test_non_dict_invocation_entry_is_skipped(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results(
            [
                "not a dict",  # type: ignore[list-item]
                _phase5_invocation(status="completed"),
            ]
        )

        block = invoker._compute_code_review_block(results)

        assert block is not None
        assert block["score"] == 100

    def test_phase_field_as_int_still_matches(
        self, invoker: AgentInvoker
    ) -> None:
        """The fold normalises ``phase`` via ``str(...)`` so an int phase
        value matches the canonical ``"5"`` string."""
        inv = _phase5_invocation(status="completed")
        inv["phase"] = 5  # type: ignore[assignment]
        results = _baseline_results([inv])

        block = invoker._compute_code_review_block(results)

        assert block is not None
        assert block["score"] == 100

    def test_non_list_invocations_field_is_silently_ignored(
        self, invoker: AgentInvoker
    ) -> None:
        results = _baseline_results(invocations=None)
        results["agent_invocations"] = {"phase": "5"}  # wrong type

        block = invoker._compute_code_review_block(results)

        assert block is None
