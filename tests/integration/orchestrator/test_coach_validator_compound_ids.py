"""Integration tests for compound AC ID matching in CoachValidator (TASK-CVAC-001).

These tests reproduce the failure mode discovered in study-tutor FEAT-FD32
Run 1 (2026-05-02): Coach generated index-based IDs (``AC-001`` …
``AC-008``) regardless of any natural label in the markdown, so Player
promises emitted under the natural label (``AC-LOAD-01`` … ``AC-LOAD-08``)
never matched and the orchestrator interpreted the unchanging ``0/8`` as
a "feedback stall" — exiting "unrecoverable_stall" even when the
underlying implementation was correct.

After the fix, ``_match_by_promises`` extracts the natural label from
the markdown and uses it as the lookup key, so labelled promises hit
labelled criteria.

Two scenarios:

- AC-CVAC-06 (FEAT-FD32 reproducer): eight ``**AC-LOAD-NN**`` markdown
  ACs + eight matching ``AC-LOAD-NN`` promises → ``criteria_met=8,
  all_criteria_met=True``.
- AC-CVAC-07 (backwards compatibility): markdown with no AC IDs at all
  + Player promises emitted under index-based IDs (``AC-001`` …
  ``AC-008``) → all match via the index-based fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validator(tmp_path) -> CoachValidator:
    """A CoachValidator anchored at a throwaway worktree path."""
    return CoachValidator(str(tmp_path))


@pytest.fixture
def feat_fd32_criteria() -> list[str]:
    """Eight AC-LOAD-NN criteria mirroring the FEAT-FD32 TASK-GR-LOAD task."""
    return [
        "- [ ] **AC-LOAD-01** — Loader recognises the new graph payload format",
        "- [ ] **AC-LOAD-02** — Persistence layer writes the loaded graph atomically",
        "- [ ] **AC-LOAD-03** — Loader rejects malformed payloads with a typed error",
        "- [ ] **AC-LOAD-04** — Existing graph loader fixtures continue to pass",
        "- [ ] **AC-LOAD-05** — Loader emits structured logs at INFO for each load",
        "- [ ] **AC-LOAD-06** — Concurrent loads serialise on the global write lock",
        "- [ ] **AC-LOAD-07** — Loader integrates with the existing dispatcher pipeline",
        "- [ ] **AC-LOAD-08** — Coverage of the loader module remains above 85%",
    ]


@pytest.fixture
def feat_fd32_promises() -> list[dict]:
    """Eight Player completion promises emitted under the natural labels."""
    return [
        {
            "criterion_id": f"AC-LOAD-{i:02d}",
            "status": "complete",
            "evidence": f"AC-LOAD-{i:02d} satisfied by loader changes (turn 4)",
        }
        for i in range(1, 9)
    ]


# ============================================================================
# AC-CVAC-06 — FEAT-FD32 stall reproducer
# ============================================================================


class TestFeatFd32Reproducer:
    """Reproduce the study-tutor FEAT-FD32 Run 1 / TASK-GR-LOAD turn 4 stall."""

    def test_compound_ids_match_via_promises(
        self,
        validator: CoachValidator,
        feat_fd32_criteria: list[str],
        feat_fd32_promises: list[dict],
    ):
        """8 ``**AC-LOAD-NN**`` ACs + 8 matching promises → 8/8, all met.

        Pre-fix this returned ``criteria_met=0, all_criteria_met=False``
        with eight ``No completion promise for AC-001`` diagnostics —
        the exact symptom captured in the FEAT-FD32 turn 4 history.
        """
        result = validator._match_by_promises(
            feat_fd32_criteria, feat_fd32_promises,
        )

        assert result.criteria_total == 8
        assert result.criteria_met == 8, (
            f"Expected 8/8 criteria met after the AC ID fix; "
            f"got {result.criteria_met}/8 (regression: FEAT-FD32 stall returned)"
        )
        assert result.all_criteria_met is True
        assert result.missing == []

        # Each criterion result is keyed by the natural label.
        natural_ids = [
            cr.criterion_id for cr in result.criteria_results
        ]
        assert natural_ids == [
            f"AC-LOAD-{i:02d}" for i in range(1, 9)
        ]
        assert all(cr.result == "verified" for cr in result.criteria_results)

    def test_acceptance_criteria_status_uses_natural_labels(
        self,
        validator: CoachValidator,
        feat_fd32_criteria: list[str],
        feat_fd32_promises: list[dict],
    ):
        """AC-CVAC-04: ``acceptance_criteria_status`` keyed by extracted IDs.

        Coach's ``criteria_results[i].criterion_id`` is what the autobuild
        orchestrator copies into ``turn_state_turn_N.json``'s
        ``acceptance_criteria_status``. Verifying the criterion_id values
        here is equivalent to verifying the dict keys in the turn-state
        artefact.
        """
        result = validator._match_by_promises(
            feat_fd32_criteria, feat_fd32_promises,
        )

        # Build the same dict the orchestrator would write to the
        # turn-state artefact.
        ac_status = {
            cr.criterion_id: cr.status for cr in result.criteria_results
        }

        # Pre-fix this dict was keyed by ``AC-001`` … ``AC-008``,
        # making turn-state files incoherent with the markdown labels.
        for i in range(1, 9):
            assert f"AC-LOAD-{i:02d}" in ac_status
            assert ac_status[f"AC-LOAD-{i:02d}"] == "verified"


# ============================================================================
# AC-CVAC-07 — Backwards compatibility (unlabelled criteria)
# ============================================================================


class TestUnlabelledBackwardsCompat:
    """Markdown with no AC IDs continues to work via index-based fallback."""

    def test_unlabelled_criteria_match_index_based_promises(
        self, validator: CoachValidator,
    ):
        """No AC IDs in markdown + Player promises ``AC-001`` … ``AC-008`` → 8/8."""
        criteria = [
            f"- [ ] Description text for criterion number {i}"
            for i in range(1, 9)
        ]
        promises = [
            {
                "criterion_id": f"AC-{i:03d}",
                "status": "complete",
                "evidence": f"index-based promise {i}",
            }
            for i in range(1, 9)
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_total == 8
        assert result.criteria_met == 8
        assert result.all_criteria_met is True
        assert result.missing == []

        # Index-based fallback IDs survived the change.
        assert [cr.criterion_id for cr in result.criteria_results] == [
            f"AC-{i:03d}" for i in range(1, 9)
        ]


# ============================================================================
# Mixed markdown formats — labelled + unlabelled in the same task
# ============================================================================


class TestMixedFormats:
    """Tasks that mix labelled and unlabelled criteria still match correctly."""

    def test_mixed_compound_and_unlabelled(self, validator: CoachValidator):
        """One compound-ID criterion + one unlabelled, both matched."""
        criteria = [
            "- [ ] **AC-LOAD-01** — labelled criterion",
            "- [ ] unlabelled criterion at index 1",
        ]
        promises = [
            {"criterion_id": "AC-LOAD-01", "status": "complete"},
            {"criterion_id": "AC-002", "status": "complete"},
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 2
        assert result.all_criteria_met is True
        assert [cr.criterion_id for cr in result.criteria_results] == [
            "AC-LOAD-01",
            "AC-002",
        ]

    def test_unmatched_compound_id_reports_natural_label(
        self, validator: CoachValidator,
    ):
        """When no matching promise exists, the diagnostic uses the natural label.

        Pre-fix the diagnostic was ``No completion promise for AC-001``
        even when the markdown labelled the criterion ``**AC-LOAD-01**``,
        making it impossible to correlate the rejection back to the
        markdown without counting line numbers.
        """
        criteria = [
            "- [ ] **AC-LOAD-01** — labelled criterion with no promise",
        ]
        promises: list[dict] = []  # Player emitted no promises for this criterion.

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 0
        assert result.criteria_results[0].criterion_id == "AC-LOAD-01"
        assert (
            "AC-LOAD-01" in result.criteria_results[0].evidence
        ), (
            "Diagnostic should reference the natural label (AC-LOAD-01), "
            "not the index-based AC-001 — see TASK-CVAC-001."
        )
