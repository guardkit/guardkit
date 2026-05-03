"""Unit tests for ``CoachValidator._match_by_promises`` criterion_text
fallback (TASK-CVAC-002).

TASK-CVAC-001 taught Coach to extract natural-label AC IDs (e.g.
``AC-SEED-01``) from criterion markdown so it could match Player promises
that key on the natural label. TASK-CVAC-002 closes the inverse failure
mode: Player still emits index-based ``criterion_id`` (``AC-001``) for the
same criterion while putting the natural label inside ``criterion_text``.

The fallback re-keys each promise by the AC ID extracted from its own
``criterion_text`` field, so Coach matches by either Player naming
convention without requiring a Player-prompt change.

Coverage:
- AC-CVAC-2-01: promise_map carries both keys when they diverge.
- AC-CVAC-2-02: DEBUG line emitted when the fallback key resolves a match.
- AC-CVAC-2-03: FEAT-FD32 reproducer — verified=1, all_criteria_met=True.
- AC-CVAC-2-04: backwards-compat — explicit criterion_id still wins.
- AC-CVAC-2-05: criterion_text=None / unparseable / empty does not raise.
- AC-CVAC-2-06: order-stability — fallback is a no-op when aligned.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


@pytest.fixture
def validator(tmp_path) -> CoachValidator:
    """A CoachValidator instance pointed at a throwaway worktree.

    ``_match_by_promises`` is pure (no IO), so the worktree never has to
    exist on disk for these tests — but ``tmp_path`` keeps the constructor
    happy and avoids polluting the real repo.
    """
    return CoachValidator(worktree_path=str(tmp_path))


# ============================================================================
# AC-CVAC-2-03 — FEAT-FD32 reproducer (the canonical failure mode)
# ============================================================================


class TestFeatFd32Reproducer:
    """Verbatim shape from FEAT-FD32 Run 4 / TASK-GR-SEED stall."""

    def test_natural_label_criterion_matches_index_keyed_promise(
        self, validator: CoachValidator
    ):
        """Coach approves when Player keys promise on AC-001 but text says AC-SEED-01."""
        # Mirror of the diagnostic dump cited in the task description
        # (study-tutor FEAT-FD32 Run 4, line 333 of the failure history).
        acceptance_criteria = [
            "**AC-SEED-01** — `python scripts/seed_student_model.py` runs successfully against the live FalkorDB instance",
        ]
        promise = {
            "criterion_id": "AC-001",
            "criterion_text": (
                "AC-SEED-01** — `python scripts/seed_student_model.py` "
                "runs successfully against the live FalkorDB instance"
            ),
            "status": "complete",
            "evidence": "File-existence verified: scripts/seed_student_model.py",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_total == 1
        assert result.criteria_met == 1
        assert result.all_criteria_met is True
        assert result.missing == []
        # The matched criterion_id is the natural label, not the index ID.
        assert result.criteria_results[0].criterion_id == "AC-SEED-01"
        assert result.criteria_results[0].result == "verified"

    def test_pre_fix_baseline_would_have_stalled(
        self, validator: CoachValidator
    ):
        """Sanity check: without criterion_text, the lookup would still fail.

        This is the pre-fix behaviour the task is closing the gap against —
        when the promise has neither the natural-label criterion_id nor a
        criterion_text containing it, no fallback can rescue the match. We
        document the contract here so future regressions can't quietly
        re-enable the bug by adding spurious recovery logic.
        """
        acceptance_criteria = [
            "**AC-SEED-01** — seed script runs successfully",
        ]
        promise = {
            "criterion_id": "AC-001",
            "criterion_text": None,  # No text → no fallback possible.
            "status": "complete",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        # No way to bridge AC-001 → AC-SEED-01 without text → still missing.
        assert result.criteria_met == 0
        assert result.all_criteria_met is False


# ============================================================================
# AC-CVAC-2-02 — DEBUG log emitted when fallback resolves the match
# ============================================================================


class TestFallbackDiagnosticLog:
    """The contract-drift DEBUG log fires exactly when fallback rescues."""

    def test_debug_log_emitted_on_fallback_match(
        self, validator: CoachValidator, caplog: pytest.LogCaptureFixture
    ):
        """When the lookup hits via the criterion_text key, log it."""
        acceptance_criteria = ["**AC-SEED-01** — text"]
        promise = {
            "criterion_id": "AC-001",
            "criterion_text": "AC-SEED-01** — text",
            "status": "complete",
        }

        with caplog.at_level(
            logging.DEBUG,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            validator._match_by_promises(acceptance_criteria, [promise])

        fallback_lines = [
            r.getMessage() for r in caplog.records
            if "matched via criterion_text fallback" in r.getMessage()
        ]
        assert len(fallback_lines) == 1
        message = fallback_lines[0]
        assert "AC-SEED-01" in message
        # Both the original criterion_id and the extracted text id are surfaced
        assert "'AC-001'" in message
        assert "'AC-SEED-01'" in message

    def test_no_debug_log_when_promise_uses_natural_label_directly(
        self, validator: CoachValidator, caplog: pytest.LogCaptureFixture
    ):
        """No fallback log when promise.criterion_id already matches."""
        acceptance_criteria = ["**AC-SEED-01** — text"]
        promise = {
            "criterion_id": "AC-SEED-01",
            "criterion_text": "AC-SEED-01** — text",
            "status": "complete",
        }

        with caplog.at_level(
            logging.DEBUG,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            validator._match_by_promises(acceptance_criteria, [promise])

        fallback_lines = [
            r.getMessage() for r in caplog.records
            if "matched via criterion_text fallback" in r.getMessage()
        ]
        assert fallback_lines == []


# ============================================================================
# AC-CVAC-2-04 — Backwards compatibility (explicit criterion_id wins)
# ============================================================================


class TestBackwardsCompatibility:
    """Existing match paths from TASK-CVAC-001 must keep working."""

    def test_promise_keyed_by_natural_label_directly_still_matches(
        self, validator: CoachValidator
    ):
        """The post-CVAC-001 happy path: Player and Coach use the same label."""
        acceptance_criteria = [
            "**AC-LOAD-01** — Settings has log_level field",
        ]
        promise = {
            "criterion_id": "AC-LOAD-01",
            "criterion_text": "AC-LOAD-01: Settings has log_level field",
            "status": "complete",
            "evidence": "Direct match",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1
        assert result.criteria_results[0].criterion_id == "AC-LOAD-01"
        assert result.criteria_results[0].evidence == "Direct match"

    def test_explicit_criterion_id_wins_when_both_keys_resolve(
        self, validator: CoachValidator
    ):
        """If two promises collide on a fallback key, the explicit one wins.

        Promise A explicitly claims ``AC-LOAD-01``. Promise B has
        ``criterion_text`` that would also extract to ``AC-LOAD-01``. The
        ``setdefault`` semantic means promise A's status (and evidence)
        survive — the fallback never overwrites an existing key.
        """
        acceptance_criteria = ["**AC-LOAD-01** — Settings field"]
        promise_explicit = {
            "criterion_id": "AC-LOAD-01",
            "status": "complete",
            "evidence": "Explicit match wins",
        }
        promise_implicit = {
            "criterion_id": "AC-999",
            "criterion_text": "AC-LOAD-01: Settings field",
            "status": "incomplete",  # Would override if fallback won
            "evidence": "Should NOT win",
        }

        result = validator._match_by_promises(
            acceptance_criteria, [promise_explicit, promise_implicit]
        )

        assert result.criteria_met == 1
        assert result.criteria_results[0].evidence == "Explicit match wins"

    def test_index_based_promise_for_unlabelled_criterion(
        self, validator: CoachValidator
    ):
        """Unlabelled criterion + index-based promise still match (CVAC-001 path)."""
        acceptance_criteria = ["Plain prose criterion with no AC label"]
        promise = {
            "criterion_id": "AC-001",
            "status": "complete",
            "evidence": "Index-based fallback",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1
        assert result.criteria_results[0].criterion_id == "AC-001"


# ============================================================================
# AC-CVAC-2-05 — Edge cases (None, empty, unparseable do not raise)
# ============================================================================


class TestFallbackEdgeCases:
    """The fallback degrades silently when criterion_text is unusable."""

    def test_criterion_text_none_does_not_raise(
        self, validator: CoachValidator
    ):
        """None criterion_text → fallback skipped, behaviour unchanged."""
        acceptance_criteria = ["**AC-LOAD-01** — text"]
        promise = {
            "criterion_id": "AC-LOAD-01",
            "criterion_text": None,
            "status": "complete",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1

    def test_criterion_text_missing_key_does_not_raise(
        self, validator: CoachValidator
    ):
        """Promise without criterion_text key at all → fallback skipped."""
        acceptance_criteria = ["**AC-LOAD-01** — text"]
        promise = {"criterion_id": "AC-LOAD-01", "status": "complete"}

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1

    def test_unparseable_criterion_text_does_not_raise(
        self, validator: CoachValidator
    ):
        """criterion_text with no extractable AC ID → fallback skipped."""
        acceptance_criteria = ["**AC-LOAD-01** — text"]
        promise = {
            "criterion_id": "AC-LOAD-01",
            "criterion_text": "Some prose without any AC identifier here.",
            "status": "complete",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1

    def test_empty_criterion_text_does_not_raise(
        self, validator: CoachValidator
    ):
        """Empty-string criterion_text → fallback skipped."""
        acceptance_criteria = ["**AC-LOAD-01** — text"]
        promise = {
            "criterion_id": "AC-LOAD-01",
            "criterion_text": "",
            "status": "complete",
        }

        result = validator._match_by_promises(acceptance_criteria, [promise])

        assert result.criteria_met == 1


# ============================================================================
# AC-CVAC-2-06 — Order stability (fallback is a no-op when aligned)
# ============================================================================


class TestOrderStability:
    """When Player and Coach already agree, the fallback adds no entries."""

    def test_aligned_naming_preserves_promise_map_size(
        self, validator: CoachValidator
    ):
        """Aligned case: criterion_id == extracted text_id → 1 entry per promise.

        Indirect assertion: build the same arguments _match_by_promises uses,
        confirm every promise resolves on its first key (no need for fallback),
        and that all are verified. ``len(promise_map) == len(promises)`` is
        the structural invariant the task spec asks us to preserve.
        """
        acceptance_criteria = [
            "**AC-LOAD-01** — first criterion",
            "**AC-LOAD-02** — second criterion",
            "**AC-LOAD-03** — third criterion",
        ]
        promises = [
            {
                "criterion_id": "AC-LOAD-01",
                "criterion_text": "AC-LOAD-01: first criterion",
                "status": "complete",
            },
            {
                "criterion_id": "AC-LOAD-02",
                "criterion_text": "AC-LOAD-02: second criterion",
                "status": "complete",
            },
            {
                "criterion_id": "AC-LOAD-03",
                "criterion_text": "AC-LOAD-03: third criterion",
                "status": "complete",
            },
        ]

        result = validator._match_by_promises(acceptance_criteria, promises)

        # All three resolved without fallback noise.
        assert result.criteria_met == 3
        assert result.all_criteria_met is True
        assert [r.criterion_id for r in result.criteria_results] == [
            "AC-LOAD-01",
            "AC-LOAD-02",
            "AC-LOAD-03",
        ]

    def test_aligned_naming_emits_no_fallback_log(
        self, validator: CoachValidator, caplog: pytest.LogCaptureFixture
    ):
        """Aligned case: no DEBUG fallback log lines at all."""
        acceptance_criteria = ["**AC-LOAD-01** — text"]
        promises = [
            {
                "criterion_id": "AC-LOAD-01",
                "criterion_text": "AC-LOAD-01: text",
                "status": "complete",
            },
        ]

        with caplog.at_level(
            logging.DEBUG,
            logger="guardkit.orchestrator.quality_gates.coach_validator",
        ):
            validator._match_by_promises(acceptance_criteria, promises)

        fallback_lines = [
            r for r in caplog.records
            if "matched via criterion_text fallback" in r.getMessage()
        ]
        assert fallback_lines == []
