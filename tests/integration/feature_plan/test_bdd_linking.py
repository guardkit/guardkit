"""Integration tests for /feature-plan Step 11 (BDD scenario linking).

Exercises the full Step 11 flow end-to-end using the orchestrator in
``installer/core/commands/lib/bdd_linking_phase.py``. The ``bdd-linker``
subagent is replaced with a callable fixture that emits a canned
``TaskMatch`` list — this keeps the test suite deterministic and independent
of the LLM runtime while still covering the entire parse → match → rewrite
pipeline.

Covered cases (per TASK-FP-LNKB-19AC acceptance criteria):

- End-to-end: feature file + task list + mock matcher → rewritten file with
  ``@task:<TASK-ID>`` tags.
- ``--no-questions`` path: threshold applied non-interactively, below-
  threshold matches surface in the summary.
- Idempotency: re-running the phase against the same inputs writes nothing
  and reports 0 new tags.
- Silent skip: no ``features/*.feature`` file → phase returns
  ``no_feature_file`` and prints nothing.
- Silent no-op: all scenarios already tagged → phase returns ``all_tagged``
  without invoking the matcher.
- Discoverability: rewritten files are returned by
  ``bdd_runner.find_feature_files_with_tag`` for each linked task (closes
  the pipeline with TASK-BDD-E8954's consumer).
- Interactive edit/skip: per-scenario overrides survive round-trip.
- Matcher error surfacing: malformed subagent responses raise
  ``MatcherResponseError`` with an actionable message.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from installer.core.commands.lib.bdd_linker import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    MatchingRequest,
    TaskInfo,
    TaskMatch,
)
from installer.core.commands.lib.bdd_linking_phase import (
    MatcherResponseError,
    PhaseResult,
    discover_feature_file,
    parse_matcher_response,
    run_linking_phase,
)
from guardkit.orchestrator.quality_gates.bdd_runner import (
    find_feature_files_with_tag,
    task_tag,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_CHECKOUT_FEATURE = """Feature: Checkout

  @smoke
  Scenario: Guest completes purchase with valid card
    Given a guest with an item in cart
    When they submit valid card details
    Then the order is confirmed

  Scenario: Declined card shows retry option
    Given a guest with an item in cart
    When the card is declined
    Then they see a retry prompt

  Scenario: Cart persists across sessions
    Given an item in cart
    When the session ends
    Then the item is still there on next login
"""


_CHECKOUT_TASKS = [
    TaskInfo(
        task_id="TASK-CK-001",
        title="Implement card payment flow",
        description=(
            "Accept card details, call the payment gateway, "
            "handle success and decline."
        ),
        acceptance_criteria=[
            "Successful charges confirm the order",
            "Declined cards surface a retry prompt",
        ],
    ),
    TaskInfo(
        task_id="TASK-CK-002",
        title="Persist cart state in session storage",
        description="Cart survives session end and is restored on next login.",
        acceptance_criteria=["Cart items restored on login"],
    ),
]


def _write_feature(tmp_path: Path, slug: str, body: str, nested: bool = True) -> Path:
    """Write a feature file using either nested or flat layout."""
    if nested:
        feature_dir = tmp_path / "features" / slug
        feature_dir.mkdir(parents=True, exist_ok=True)
        feature_file = feature_dir / f"{slug}.feature"
    else:
        feature_dir = tmp_path / "features"
        feature_dir.mkdir(parents=True, exist_ok=True)
        feature_file = feature_dir / f"{slug}.feature"
    feature_file.write_text(body, encoding="utf-8")
    return feature_file


def _canned_matcher(matches: List[TaskMatch]):
    """Build a matcher callback that returns the provided matches."""
    def _matcher(request: MatchingRequest) -> List[TaskMatch]:
        # Sanity-check that the orchestrator built a non-trivial request.
        assert isinstance(request, MatchingRequest)
        return matches

    return _matcher


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class TestDiscovery:
    """discover_feature_file honours both /feature-spec layouts."""

    def test_nested_layout_preferred(self, tmp_path: Path) -> None:
        nested = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE, nested=True)
        flat = tmp_path / "features" / "checkout.feature"
        flat.write_text("Feature: flat\n", encoding="utf-8")

        resolved = discover_feature_file(tmp_path, "checkout")
        assert resolved == nested

    def test_flat_layout_fallback(self, tmp_path: Path) -> None:
        flat = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE, nested=False)
        resolved = discover_feature_file(tmp_path, "checkout")
        assert resolved == flat

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert discover_feature_file(tmp_path, "nonexistent") is None

    def test_empty_slug_returns_none(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "anything", _CHECKOUT_FEATURE)
        assert discover_feature_file(tmp_path, "") is None


# ---------------------------------------------------------------------------
# parse_matcher_response
# ---------------------------------------------------------------------------


class TestParseMatcherResponse:
    """Subagent response coercion handles the realistic shapes."""

    def test_parses_json_string(self) -> None:
        raw = '[{"scenario_index": 0, "task_id": "TASK-A", "confidence": 0.9}]'
        matches = parse_matcher_response(raw)
        assert matches == [
            TaskMatch(scenario_index=0, task_id="TASK-A", confidence=0.9)
        ]

    def test_parses_list_of_dicts(self) -> None:
        raw = [{"scenario_index": 1, "task_id": "TASK-B", "confidence": 0.75}]
        matches = parse_matcher_response(raw)
        assert matches[0].task_id == "TASK-B"

    def test_passes_through_typed_list(self) -> None:
        source = [TaskMatch(scenario_index=0, task_id="TASK-X", confidence=0.5)]
        assert parse_matcher_response(source) == source

    def test_unwraps_matches_key(self) -> None:
        raw = {"matches": [{"scenario_index": 0, "task_id": "TASK-Y", "confidence": 0.8}]}
        assert parse_matcher_response(raw)[0].task_id == "TASK-Y"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(MatcherResponseError, match="invalid JSON"):
            parse_matcher_response("not json")

    def test_missing_field_raises(self) -> None:
        with pytest.raises(MatcherResponseError, match="missing required field"):
            parse_matcher_response([{"scenario_index": 0, "task_id": "TASK-A"}])

    def test_empty_task_id_raises(self) -> None:
        with pytest.raises(MatcherResponseError, match="empty task_id"):
            parse_matcher_response(
                [{"scenario_index": 0, "task_id": "", "confidence": 0.9}]
            )

    def test_non_list_raises(self) -> None:
        with pytest.raises(MatcherResponseError, match="must be a list"):
            parse_matcher_response({"not": "a list"})

    def test_none_raises(self) -> None:
        with pytest.raises(MatcherResponseError):
            parse_matcher_response(None)


# ---------------------------------------------------------------------------
# Silent skip paths
# ---------------------------------------------------------------------------


class TestSilentSkip:
    """Step 11 is a silent no-op when there is nothing to do."""

    def test_no_feature_file(self, tmp_path: Path) -> None:
        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="absent",
            tasks=_CHECKOUT_TASKS,
            matcher=lambda req: [],  # must never be called
            interactive=False,
            printer=printed.append,
        )
        assert result.status == "no_feature_file"
        assert result.feature_path is None
        assert result.linking_result is None
        assert printed == []  # truly silent

    def test_feature_file_with_no_scenarios(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "empty", "# just a comment, no Feature:\n")
        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="empty",
            tasks=_CHECKOUT_TASKS,
            matcher=lambda req: [],
            interactive=False,
            printer=printed.append,
        )
        assert result.status == "no_scenarios"
        assert printed == []

    def test_all_scenarios_already_tagged(self, tmp_path: Path) -> None:
        # Write a feature where every scenario already has @task: — the
        # orchestrator must not invoke the matcher at all.
        body = """Feature: Checkout

  @task:TASK-CK-001
  Scenario: Guest completes purchase
    Given a guest with an item in cart
    When they submit valid card details
    Then the order is confirmed

  @task:TASK-CK-002
  Scenario: Cart persists
    Given an item in cart
    When the session ends
    Then the item is still there on next login
"""
        _write_feature(tmp_path, "checkout", body)
        call_count = {"n": 0}

        def _matcher(request: MatchingRequest) -> List[TaskMatch]:
            call_count["n"] += 1
            return []

        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS[:2],
            matcher=_matcher,
            interactive=False,
            printer=printed.append,
        )
        assert result.status == "all_tagged"
        assert call_count["n"] == 0
        assert printed == []


# ---------------------------------------------------------------------------
# End-to-end: --no-questions
# ---------------------------------------------------------------------------


class TestNoQuestionsPath:
    """--no-questions: threshold applied non-interactively."""

    def test_applies_above_threshold_matches(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
            TaskMatch(scenario_index=1, task_id="TASK-CK-001", confidence=0.88),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.90),
        ]

        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=False,
            printer=printed.append,
        )
        assert result.status == "applied"
        assert result.linking_result is not None
        assert result.linking_result.rewritten is True

        content = feature_file.read_text(encoding="utf-8")
        assert "@task:TASK-CK-001" in content
        assert "@task:TASK-CK-002" in content
        # The `@smoke` tag on scenario 0 must survive the rewrite.
        assert "@smoke" in content

        # Step summary should be printed once.
        assert any("linked 3 scenario(s)" in line for line in printed)

    def test_below_threshold_reported_in_summary(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        # Scenario 0 is a strong fit, scenario 1 is below the default threshold
        # (0.6), scenario 2 is omitted entirely — the subagent's choice.
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.92),
            TaskMatch(scenario_index=1, task_id="TASK-CK-001", confidence=0.40),
        ]

        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=False,
            printer=printed.append,
        )
        assert result.status == "applied"
        lr = result.linking_result
        assert lr is not None
        assert (1, "TASK-CK-001", 0.40) in lr.skipped_low_confidence
        # Only the above-threshold match was tagged.
        assert [(0, "TASK-CK-001")] == lr.linked
        # Summary mentions the below-threshold miss explicitly.
        assert any("below threshold" in line for line in printed)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Running Step 11 twice leaves the file unchanged on the second pass."""

    def test_second_run_reports_all_tagged(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
            TaskMatch(scenario_index=1, task_id="TASK-CK-001", confidence=0.88),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.90),
        ]

        matcher_calls = {"n": 0}

        def _matcher(request: MatchingRequest) -> List[TaskMatch]:
            matcher_calls["n"] += 1
            return matches

        # First run: applies everything.
        first = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_matcher,
            interactive=False,
        )
        assert first.status == "applied"
        after_first = feature_file.read_text(encoding="utf-8")

        # Second run: every scenario is tagged → short-circuit before matcher.
        second = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_matcher,
            interactive=False,
        )
        assert second.status == "all_tagged"
        # Matcher was only invoked on the first pass.
        assert matcher_calls["n"] == 1

        after_second = feature_file.read_text(encoding="utf-8")
        assert after_first == after_second

        # Each task appears exactly once in the file.
        assert after_second.count("@task:TASK-CK-001") == 2  # two scenarios
        assert after_second.count("@task:TASK-CK-002") == 1


# ---------------------------------------------------------------------------
# Discoverability by bdd_runner
# ---------------------------------------------------------------------------


class TestBddRunnerDiscovery:
    """The runtime consumer (bdd_runner) finds every linked task."""

    def test_find_feature_files_with_tag_after_linking(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
            TaskMatch(scenario_index=1, task_id="TASK-CK-001", confidence=0.88),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.90),
        ]

        run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=False,
        )

        features_dir = tmp_path / "features"
        for task in _CHECKOUT_TASKS:
            discovered = find_feature_files_with_tag(features_dir, task_tag(task.task_id))
            assert feature_file in discovered, (
                f"bdd_runner.find_feature_files_with_tag should discover "
                f"{feature_file.name} for {task.task_id}, got {discovered}"
            )


# ---------------------------------------------------------------------------
# Interactive review round-trip
# ---------------------------------------------------------------------------


class TestInteractiveReview:
    """The rich-driven review loop honours per-scenario overrides."""

    def test_accept_all_default(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.90),
        ]

        # Single empty input = accept-all default.
        inputs = iter([""])

        def _input(prompt: str) -> str:
            return next(inputs)

        printed: List[str] = []
        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=True,
            input_fn=_input,
            printer=printed.append,
        )
        assert result.status == "applied"
        lr = result.linking_result
        assert lr is not None
        assert (0, "TASK-CK-001") in lr.linked
        assert (2, "TASK-CK-002") in lr.linked

        # Verify the table rendered.
        assert any("Proposed scenario" in p for p in printed)

    def test_skip_scenario(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.90),
        ]

        inputs = iter(["s 0", "a"])  # skip scenario 0, then accept the rest

        def _input(prompt: str) -> str:
            return next(inputs)

        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=True,
            input_fn=_input,
            printer=lambda _s: None,
        )
        lr = result.linking_result
        assert lr is not None
        # Scenario 0 was skipped → untagged.
        assert (0, "TASK-CK-001") not in lr.linked
        # Scenario 2 was accepted → linked.
        assert (2, "TASK-CK-002") in lr.linked

        content = feature_file.read_text(encoding="utf-8")
        assert "@task:TASK-CK-002" in content
        # The skipped scenario must NOT have been tagged.
        idx = content.index("Guest completes purchase")
        nearby = content[max(0, idx - 80): idx]
        assert "@task:TASK-CK-001" not in nearby

    def test_edit_reassigns_task(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        # Subagent thought scenario 0 was TASK-CK-001; user corrects to -002.
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.70),
        ]

        inputs = iter(["e 0 TASK-CK-002", "d"])  # edit then done

        def _input(prompt: str) -> str:
            return next(inputs)

        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=True,
            input_fn=_input,
            printer=lambda _s: None,
        )
        lr = result.linking_result
        assert lr is not None
        # User's edit wins — scenario 0 is linked to CK-002, not CK-001.
        assert (0, "TASK-CK-002") in lr.linked
        assert (0, "TASK-CK-001") not in lr.linked

        content = feature_file.read_text(encoding="utf-8")
        # The file records the user's choice.
        first_scenario_block = content.split("Scenario: Declined")[0]
        assert "@task:TASK-CK-002" in first_scenario_block


# ---------------------------------------------------------------------------
# Configurable threshold
# ---------------------------------------------------------------------------


class TestThresholdOverride:
    """--bdd-link-threshold flows through the orchestrator."""

    def test_higher_threshold_drops_marginal_matches(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        # Matches at 0.65 and 0.80. With threshold 0.75 only the second survives.
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.65),
            TaskMatch(scenario_index=2, task_id="TASK-CK-002", confidence=0.80),
        ]

        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=False,
            confidence_threshold=0.75,
            printer=lambda _s: None,
        )
        lr = result.linking_result
        assert lr is not None
        assert lr.linked == [(2, "TASK-CK-002")]
        assert (0, "TASK-CK-001", 0.65) in lr.skipped_low_confidence


# ---------------------------------------------------------------------------
# Matcher error surfacing
# ---------------------------------------------------------------------------


class TestMatcherErrors:
    """Malformed matcher responses raise actionable errors."""

    def test_invalid_json_raises_response_error(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        def _bad(request: MatchingRequest) -> str:
            return "definitely not json"

        with pytest.raises(MatcherResponseError, match="invalid JSON"):
            run_linking_phase(
                project_root=tmp_path,
                feature_slug="checkout",
                tasks=_CHECKOUT_TASKS,
                matcher=_bad,
                interactive=False,
                printer=lambda _s: None,
            )

    def test_missing_field_raises(self, tmp_path: Path) -> None:
        _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)

        def _partial(request: MatchingRequest):
            return [{"scenario_index": 0, "task_id": "TASK-CK-001"}]  # no confidence

        with pytest.raises(MatcherResponseError, match="missing required field"):
            run_linking_phase(
                project_root=tmp_path,
                feature_slug="checkout",
                tasks=_CHECKOUT_TASKS,
                matcher=_partial,
                interactive=False,
                printer=lambda _s: None,
            )


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


class TestDryRun:
    """dry_run=True produces a LinkingResult but never touches the file."""

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        feature_file = _write_feature(tmp_path, "checkout", _CHECKOUT_FEATURE)
        original = feature_file.read_text(encoding="utf-8")

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-CK-001", confidence=0.93),
        ]

        result = run_linking_phase(
            project_root=tmp_path,
            feature_slug="checkout",
            tasks=_CHECKOUT_TASKS,
            matcher=_canned_matcher(matches),
            interactive=False,
            dry_run=True,
            printer=lambda _s: None,
        )
        lr = result.linking_result
        assert lr is not None
        assert lr.linked == [(0, "TASK-CK-001")]
        assert lr.rewritten is False
        # File is unchanged.
        assert feature_file.read_text(encoding="utf-8") == original
