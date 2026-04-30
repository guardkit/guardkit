"""Unit tests for ``installer/core/commands/lib/wave_overlap_detector.py``.

Covers AC-001, AC-002, AC-003 (split mechanics), AC-005, and AC-006 of
TASK-FIX-A7B3. The end-to-end producer wiring (AC-004) is exercised by
``tests/integration/feature_plan/test_wave_overlap_detection.py``.

Coverage Target: >=85%
Test Count: 20+ tests
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add installer lib to path so ``import wave_overlap_detector`` works the
# same way ``test_generate_feature_yaml.py`` imports its module under test.
_INSTALLER_LIB = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(_INSTALLER_LIB) not in sys.path:
    sys.path.insert(0, str(_INSTALLER_LIB))

from wave_overlap_detector import (  # noqa: E402
    OverlapWarning,
    compute_wave_overlaps,
    format_overlap_warning_summary,
    infer_task_files,
    serialize_overlapping_groups,
    warnings_to_dict,
)


# ============================================================================
# 1. infer_task_files — explicit path extraction (AC-001)
# ============================================================================


class TestInferTaskFilesExplicitPaths:
    def test_extracts_path_from_description(self):
        task = {
            "id": "TASK-001",
            "name": "Add login endpoint",
            "description": "Edit `src/auth/login.py` to add the new endpoint.",
        }
        files = infer_task_files(task)
        assert "src/auth/login.py" in files

    def test_extracts_path_from_acceptance_criteria_list(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "acceptance_criteria": [
                "- [ ] Update `tests/unit/test_login.py` with new cases",
            ],
        }
        files = infer_task_files(task)
        assert "tests/unit/test_login.py" in files

    def test_extracts_multiple_paths(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": (
                "Touches `src/auth/login.py` and tests/unit/test_login.py "
                "alongside features/foo/bar.feature."
            ),
        }
        files = infer_task_files(task)
        assert files == frozenset({
            "src/auth/login.py",
            "tests/unit/test_login.py",
            "features/foo/bar.feature",
        })

    def test_strips_trailing_punctuation(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": "See src/x.py. And tests/y.py, plus tests/z.py)",
        }
        files = infer_task_files(task)
        assert files == frozenset({"src/x.py", "tests/y.py", "tests/z.py"})

    def test_skips_glob_patterns(self):
        # Wildcards describe a class of files, not a concrete edit.
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": "Changes affect features/*/test_*.py across the suite.",
        }
        files = infer_task_files(task)
        assert files == frozenset()

    def test_handles_dict_acceptance_criteria(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "acceptance_criteria": [
                {"text": "Touches src/foo.py"},
                {"description": "Also tests/bar.py"},
            ],
        }
        files = infer_task_files(task)
        assert files == frozenset({"src/foo.py", "tests/bar.py"})

    def test_empty_task_returns_empty_set(self):
        assert infer_task_files({"id": "TASK-001"}) == frozenset()
        assert infer_task_files({}) == frozenset()
        assert infer_task_files({"id": "TASK-001", "name": "", "description": ""}) == frozenset()

    def test_text_with_no_paths_returns_empty(self):
        task = {
            "id": "TASK-001",
            "name": "Refactor naming",
            "description": "Rename internal helper without touching files explicitly.",
        }
        assert infer_task_files(task) == frozenset()

    def test_supports_multiple_extensions(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": (
                "Touches lib/foo.ts, app/bar.tsx, tests/baz.cs, "
                "config/qux.yaml, db/migrations/0001.sql"
            ),
        }
        files = infer_task_files(task)
        assert "lib/foo.ts" in files
        assert "app/bar.tsx" in files
        assert "tests/baz.cs" in files
        assert "config/qux.yaml" in files
        assert "db/migrations/0001.sql" in files


# ============================================================================
# 2. infer_task_files — BDD glue inference (AC-006)
# ============================================================================


class TestInferTaskFilesBddGlueInference:
    def test_infers_glue_from_feature_reference_with_step_def_hint(self):
        task = {
            "id": "TASK-001",
            "name": "Add login scenarios",
            "description": (
                "Implement step definitions for features/login/login.feature "
                "(uses pytest-bdd)."
            ),
        }
        files = infer_task_files(task)
        assert "features/login/test_login.py" in files
        assert "features/login/login.feature" in files

    def test_infers_glue_with_at_given_decorator_hint(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": (
                "Wire @given fixture for features/onboard/welcome.feature scenarios."
            ),
        }
        files = infer_task_files(task)
        assert "features/onboard/test_onboard.py" in files

    def test_no_glue_inference_without_hint(self):
        # Just citing a .feature file without step-def language must not
        # phantom-add the glue path.
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": "Update documentation referencing features/foo/x.feature.",
        }
        files = infer_task_files(task)
        assert "features/foo/x.feature" in files
        assert "features/foo/test_foo.py" not in files

    def test_glue_inference_works_with_directly_named_feature_dir(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": (
                "Add @when step_defs entry for features/login/scenarios.feature."
            ),
        }
        files = infer_task_files(task)
        assert "features/login/test_login.py" in files

    def test_multiple_features_each_get_their_glue(self):
        task = {
            "id": "TASK-001",
            "name": "noop",
            "description": (
                "Step definitions for features/login/a.feature and "
                "features/signup/b.feature. Uses pytest-bdd glue."
            ),
        }
        files = infer_task_files(task)
        assert "features/login/test_login.py" in files
        assert "features/signup/test_signup.py" in files


# ============================================================================
# 3. compute_wave_overlaps — pairwise intersection (AC-002, AC-005)
# ============================================================================


class TestComputeWaveOverlaps:
    def test_no_overlap_returns_empty(self):
        groups = [["TASK-001", "TASK-002"]]
        files = {
            "TASK-001": frozenset({"src/a.py"}),
            "TASK-002": frozenset({"src/b.py"}),
        }
        assert compute_wave_overlaps(groups, files) == []

    def test_overlap_in_single_wave(self):
        groups = [["TASK-001", "TASK-002"]]
        files = {
            "TASK-001": frozenset({"features/foo/test_foo.py"}),
            "TASK-002": frozenset({"features/foo/test_foo.py"}),
        }
        warnings = compute_wave_overlaps(groups, files)
        assert len(warnings) == 1
        warning = warnings[0]
        assert warning.wave_index == 1
        assert warning.task_ids == ("TASK-001", "TASK-002")
        assert warning.files == ("features/foo/test_foo.py",)

    def test_skips_single_task_waves(self):
        # AC-002: only waves with len(tasks) > 1 are evaluated.
        groups = [["TASK-001"], ["TASK-002"]]
        files = {
            "TASK-001": frozenset({"src/a.py"}),
            "TASK-002": frozenset({"src/a.py"}),
        }
        # Different waves — no intra-wave overlap.
        assert compute_wave_overlaps(groups, files) == []

    def test_disjoint_plan_unchanged_no_warning(self):
        # AC-005: existing single-task and zero-overlap plans are unchanged.
        groups = [["TASK-001", "TASK-002"], ["TASK-003"]]
        files = {
            "TASK-001": frozenset({"src/a.py"}),
            "TASK-002": frozenset({"src/b.py"}),
            "TASK-003": frozenset({"src/c.py"}),
        }
        assert compute_wave_overlaps(groups, files) == []

    def test_three_tasks_in_wave_two_overlap(self):
        groups = [["TASK-001", "TASK-002", "TASK-003"]]
        files = {
            "TASK-001": frozenset({"src/a.py"}),
            "TASK-002": frozenset({"src/a.py"}),
            "TASK-003": frozenset({"src/b.py"}),
        }
        warnings = compute_wave_overlaps(groups, files)
        assert len(warnings) == 1
        assert set(warnings[0].task_ids) == {"TASK-001", "TASK-002"}
        assert warnings[0].files == ("src/a.py",)

    def test_tasks_with_no_inferred_files_skipped_silently(self):
        # AC-005: no spurious warnings when files cannot be inferred.
        groups = [["TASK-001", "TASK-002"]]
        files = {
            "TASK-001": frozenset(),
            "TASK-002": frozenset({"src/a.py"}),
        }
        assert compute_wave_overlaps(groups, files) == []

    def test_multiple_overlapping_files_aggregated(self):
        groups = [["TASK-001", "TASK-002"]]
        files = {
            "TASK-001": frozenset({"src/a.py", "src/b.py", "src/c.py"}),
            "TASK-002": frozenset({"src/a.py", "src/b.py"}),
        }
        warnings = compute_wave_overlaps(groups, files)
        assert len(warnings) == 1
        assert warnings[0].files == ("src/a.py", "src/b.py")

    def test_wave_index_is_one_based(self):
        groups = [
            ["TASK-001"],  # wave 1, single task
            ["TASK-002", "TASK-003"],  # wave 2, overlap
        ]
        files = {
            "TASK-001": frozenset({"src/a.py"}),
            "TASK-002": frozenset({"src/x.py"}),
            "TASK-003": frozenset({"src/x.py"}),
        }
        warnings = compute_wave_overlaps(groups, files)
        assert len(warnings) == 1
        assert warnings[0].wave_index == 2

    def test_each_wave_emits_at_most_one_warning(self):
        # Multiple pairwise intersections in the same wave aggregate into
        # one warning per wave (matches the runtime contention message
        # shape in coach_validator._detect_source_file_contention).
        groups = [["A", "B", "C"]]
        files = {
            "A": frozenset({"src/x.py", "src/y.py"}),
            "B": frozenset({"src/x.py"}),
            "C": frozenset({"src/y.py"}),
        }
        warnings = compute_wave_overlaps(groups, files)
        assert len(warnings) == 1
        assert set(warnings[0].task_ids) == {"A", "B", "C"}
        assert set(warnings[0].files) == {"src/x.py", "src/y.py"}


# ============================================================================
# 4. serialize_overlapping_groups — split mechanics (AC-003)
# ============================================================================


class TestSerializeOverlappingGroups:
    def test_no_warnings_returns_unchanged_copy(self):
        groups = [["A", "B"], ["C"]]
        new_groups, notes = serialize_overlapping_groups(groups, [])
        assert new_groups == [["A", "B"], ["C"]]
        assert notes == []
        # Defensive copy: mutating the result must not bleed back.
        new_groups[0].append("Z")
        assert groups[0] == ["A", "B"]

    def test_split_two_offenders_into_separate_sequential_waves(self):
        # AC-003: "split into two sequential entries". For 2 offenders that
        # both overlap on the same file, putting them both in a single
        # follow-on wave preserves the conflict — each offender must run
        # in its own sequential wave so they truly serialise.
        groups = [["A", "B"]]
        warnings = [OverlapWarning(
            wave_index=1, task_ids=("A", "B"), files=("src/x.py",)
        )]
        new_groups, notes = serialize_overlapping_groups(groups, warnings)
        assert new_groups == [["A"], ["B"]]
        assert len(notes) == 1
        assert "Wave 1" in notes[0]
        assert "src/x.py" in notes[0]

    def test_split_keeps_non_offenders_in_original_wave(self):
        groups = [["A", "B", "C"]]
        # Only A and B overlap; C is innocent and stays in the original wave.
        # A and B then each get their own follow-on sequential wave.
        warnings = [OverlapWarning(
            wave_index=1, task_ids=("A", "B"), files=("src/x.py",)
        )]
        new_groups, notes = serialize_overlapping_groups(groups, warnings)
        assert new_groups == [["C"], ["A"], ["B"]]
        assert len(notes) == 1

    def test_only_flagged_waves_split(self):
        groups = [["A", "B"], ["C", "D"]]
        # Only wave 2 flagged.
        warnings = [OverlapWarning(
            wave_index=2, task_ids=("C", "D"), files=("src/y.py",)
        )]
        new_groups, notes = serialize_overlapping_groups(groups, warnings)
        assert new_groups == [["A", "B"], ["C"], ["D"]]
        assert len(notes) == 1
        assert "Wave 2" in notes[0]

    def test_split_preserves_original_task_order(self):
        # OverlapWarning.task_ids is sorted for display, but the split must
        # preserve the original wave ordering so dependency wiring stays
        # deterministic.
        groups = [["B", "A"]]
        warnings = [OverlapWarning(
            wave_index=1, task_ids=("A", "B"), files=("src/x.py",)
        )]
        new_groups, _ = serialize_overlapping_groups(groups, warnings)
        # B was originally first → B runs first in the split too.
        assert new_groups == [["B"], ["A"]]


# ============================================================================
# 5. format_overlap_warning_summary — banner copy (visual regression)
# ============================================================================


class TestFormatOverlapWarningSummary:
    def test_empty_warnings_returns_empty_string(self):
        assert format_overlap_warning_summary([]) == ""

    def test_warn_only_banner_mentions_auto_serialise_flag(self):
        warnings = [OverlapWarning(
            wave_index=1,
            task_ids=("TASK-001", "TASK-002"),
            files=("features/foo/test_foo.py",),
        )]
        summary = format_overlap_warning_summary(warnings, auto_serialise=False)
        assert "Wave 1" in summary
        assert "TASK-001" in summary and "TASK-002" in summary
        assert "features/foo/test_foo.py" in summary
        assert "--auto-serialise-overlap" in summary

    def test_auto_serialise_banner_mentions_split_action(self):
        warnings = [OverlapWarning(
            wave_index=1,
            task_ids=("A", "B"),
            files=("src/x.py",),
        )]
        summary = format_overlap_warning_summary(warnings, auto_serialise=True)
        assert "follow-on sequential wave" in summary
        # Banner must not steer the user to re-run with the flag they
        # already set.
        assert "Re-run with --auto-serialise-overlap" not in summary


# ============================================================================
# 6. warnings_to_dict — schema-friendly serialisation
# ============================================================================


def test_warnings_to_dict_round_trip():
    warnings = [
        OverlapWarning(wave_index=2, task_ids=("A", "B"), files=("src/x.py",)),
    ]
    serialised = warnings_to_dict(warnings)
    assert serialised == [{
        "wave_index": 2,
        "task_ids": ["A", "B"],
        "files": ["src/x.py"],
    }]
