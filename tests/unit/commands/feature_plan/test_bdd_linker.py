"""Unit tests for installer/core/commands/lib/bdd_linker.py (TASK-FP-LINK).

Covers the acceptance criteria on the mechanical half:

- Parse + rewrite preserves formatting (comments, blank lines, existing tags).
- Existing ``@task:`` tags are never overwritten or duplicated.
- Idempotency: running the rewrite twice yields the same file.
- Confidence threshold filtering.
- Edge cases: empty file, all already tagged, more scenarios than tasks.
- Atomic rewrite via temp file + os.replace (no truncation on failure).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from installer.core.commands.lib.bdd_linker import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    FeatureDocument,
    LinkingResult,
    MatchingRequest,
    ScenarioInfo,
    TaskInfo,
    TaskMatch,
    apply_mapping,
    build_matching_request,
    existing_task_tags,
    parse_feature_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SIMPLE_FEATURE = """Feature: Sign in

  Scenario: User signs in with valid credentials
    Given a registered user
    When they submit correct credentials
    Then a session is created

  Scenario: Bad password shows clear error
    Given a registered user
    When they submit an invalid password
    Then they see an error message
"""


_FEATURE_WITH_EXISTING_TAGS = """Feature: Sign in

  @smoke
  Scenario: User signs in with valid credentials
    Given a registered user
    When they submit correct credentials
    Then a session is created

  @key-example @task:TASK-AUTH-001
  Scenario: Bad password shows clear error
    Given a registered user
    When they submit an invalid password
    Then they see an error message
"""


_FEATURE_WITH_COMMENTS_AND_BLANKS = """# Top-of-file comment
Feature: Sign in

  # Describe the login flow
  Scenario: User signs in with valid credentials
    Given a registered user

    When they submit correct credentials
    Then a session is created


  @smoke
  Scenario: Bad password shows clear error
    Given a registered user
    When they submit an invalid password
    Then they see an error message
"""


_FEATURE_WITH_RULE = """Feature: Subscriptions

  Rule: Free tier limits

    Scenario: Free user hits monthly cap
      Given a free-tier account
      When the 11th request is made
      Then the user is rate-limited

    Scenario: Free user upgrades
      Given a free-tier account
      When the user upgrades
      Then paid features are unlocked
"""


_EMPTY_FEATURE = ""


@pytest.fixture
def feature_file(tmp_path: Path):
    """Helper that writes a feature file and returns its path."""
    def _write(content: str, name: str = "sample.feature") -> Path:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path
    return _write


# ---------------------------------------------------------------------------
# parse_feature_file
# ---------------------------------------------------------------------------


class TestParseFeatureFile:
    def test_simple_feature_two_scenarios(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)

        assert doc.path == path
        assert doc.feature_name == "Sign in"
        assert doc.feature_tags == []
        assert len(doc.scenarios) == 2
        assert doc.scenarios[0].name == "User signs in with valid credentials"
        assert doc.scenarios[1].name == "Bad password shows clear error"
        assert doc.scenarios[0].keyword == "Scenario"
        assert doc.scenarios[0].tags == []
        assert doc.scenarios[0].tag_line is None

    def test_records_scenario_line_numbers(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        # Line 3 = first Scenario:, line 8 = second Scenario:
        assert doc.scenarios[0].line == 3
        assert doc.scenarios[1].line == 8

    def test_records_existing_tags(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        doc = parse_feature_file(path)

        assert doc.scenarios[0].tags == ["@smoke"]
        assert doc.scenarios[0].tag_line == 3
        assert doc.scenarios[1].tags == ["@key-example", "@task:TASK-AUTH-001"]
        assert doc.scenarios[1].tag_line == 9

    def test_captures_indent_for_scenario_and_tags(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        doc = parse_feature_file(path)
        assert doc.scenarios[0].indent == "  "
        assert doc.scenarios[0].tag_indent == "  "
        assert doc.scenarios[1].tag_indent == "  "

    def test_captures_steps_for_matching_payload(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        steps = doc.scenarios[0].steps
        assert any("registered user" in s for s in steps)
        assert any("correct credentials" in s for s in steps)

    def test_rule_children_are_included(self, feature_file):
        path = feature_file(_FEATURE_WITH_RULE)
        doc = parse_feature_file(path)
        assert len(doc.scenarios) == 2
        assert doc.scenarios[0].name == "Free user hits monthly cap"
        assert doc.scenarios[1].name == "Free user upgrades"

    def test_empty_file_is_no_feature(self, feature_file):
        path = feature_file(_EMPTY_FEATURE)
        doc = parse_feature_file(path)
        assert doc.scenarios == []
        assert doc.feature_name == ""

    def test_detects_lf_line_ending(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        assert doc.line_ending == "\n"
        assert doc.trailing_newline is True

    def test_detects_crlf_line_ending(self, tmp_path: Path):
        content = _SIMPLE_FEATURE.replace("\n", "\r\n")
        path = tmp_path / "crlf.feature"
        path.write_text(content, encoding="utf-8", newline="")
        doc = parse_feature_file(path)
        assert doc.line_ending == "\r\n"


# ---------------------------------------------------------------------------
# existing_task_tags
# ---------------------------------------------------------------------------


class TestExistingTaskTags:
    def test_no_task_tags(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        assert existing_task_tags(doc) == {}

    def test_finds_task_tag_among_others(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        doc = parse_feature_file(path)
        # First scenario has only @smoke; second has @task:TASK-AUTH-001.
        assert existing_task_tags(doc) == {1: "TASK-AUTH-001"}

    def test_ignores_task_like_substring_in_step_text(self, feature_file):
        content = """Feature: Tricky

  Scenario: Step text mentions @task:something
    Given a step that contains "@task:fake-id" in its text
    When nothing
    Then nothing
"""
        path = feature_file(content)
        doc = parse_feature_file(path)
        # @task: is inside step text, not an actual scenario tag.
        assert existing_task_tags(doc) == {}


# ---------------------------------------------------------------------------
# build_matching_request
# ---------------------------------------------------------------------------


class TestBuildMatchingRequest:
    def _tasks(self) -> List[TaskInfo]:
        return [
            TaskInfo(
                task_id="TASK-AUTH-001",
                title="Implement successful login",
                description="Register a user and let them log in.",
                acceptance_criteria=["Valid creds produce a session"],
            ),
            TaskInfo(
                task_id="TASK-AUTH-002",
                title="Show error on bad password",
                description="Reject invalid credentials with an error.",
                acceptance_criteria=["Invalid password returns user-visible error"],
            ),
        ]

    def test_payload_contains_all_scenarios_when_none_tagged(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        req = build_matching_request(doc, self._tasks())

        assert req.feature_name == "Sign in"
        assert req.confidence_threshold == DEFAULT_CONFIDENCE_THRESHOLD
        assert len(req.scenarios) == 2
        assert req.scenarios[0]["index"] == 0
        assert req.scenarios[0]["keyword"] == "Scenario"
        assert "steps" in req.scenarios[0]
        assert len(req.tasks) == 2
        assert req.tasks[0]["task_id"] == "TASK-AUTH-001"
        assert "acceptance_criteria" in req.tasks[0]

    def test_skips_already_tagged_scenarios_by_default(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        doc = parse_feature_file(path)
        req = build_matching_request(doc, self._tasks())
        # Only the untagged scenario (index 0) should be in the payload.
        assert [s["index"] for s in req.scenarios] == [0]

    def test_existing_task_tags_filtered_from_existing_tags_list(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        doc = parse_feature_file(path)
        req = build_matching_request(doc, self._tasks(), skip_already_tagged=False)
        # Second scenario present; @task: tag should not leak into existing_tags.
        scenario = [s for s in req.scenarios if s["index"] == 1][0]
        assert "@task:TASK-AUTH-001" not in scenario["existing_tags"]
        assert "@key-example" in scenario["existing_tags"]

    def test_to_json_roundtrip(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        doc = parse_feature_file(path)
        req = build_matching_request(doc, self._tasks())
        import json
        parsed = json.loads(req.to_json())
        assert parsed["feature_name"] == "Sign in"
        assert len(parsed["scenarios"]) == 2


# ---------------------------------------------------------------------------
# apply_mapping
# ---------------------------------------------------------------------------


class TestApplyMapping:
    def test_inserts_task_tag_above_scenario_with_no_existing_tags(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-AUTH-001", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-AUTH-002", confidence=0.85),
        ]
        result = apply_mapping(path, matches)
        assert result.rewritten is True
        assert set(result.linked) == {(0, "TASK-AUTH-001"), (1, "TASK-AUTH-002")}

        content = path.read_text(encoding="utf-8")
        # Both tag lines present on their own line, directly above their Scenario.
        assert "  @task:TASK-AUTH-001\n  Scenario: User signs in" in content
        assert "  @task:TASK-AUTH-002\n  Scenario: Bad password" in content

    def test_inserts_above_existing_tags_preserving_them(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        # Scenario 1 already tagged with @task:TASK-AUTH-001 — should be skipped.
        # Scenario 0 has @smoke only — a new @task: tag goes above @smoke.
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-AUTH-010", confidence=0.95),
        ]
        result = apply_mapping(path, matches)
        content = path.read_text(encoding="utf-8")

        assert "  @task:TASK-AUTH-010\n  @smoke\n  Scenario: User signs in" in content
        # Existing @task: tag on scenario 1 is untouched.
        assert content.count("@task:TASK-AUTH-001") == 1

    def test_does_not_duplicate_existing_task_tag_on_reapply(self, feature_file):
        path = feature_file(_FEATURE_WITH_EXISTING_TAGS)
        matches = [
            # Even re-feeding the same match should not duplicate the tag.
            TaskMatch(scenario_index=1, task_id="TASK-AUTH-001", confidence=0.99),
        ]
        result = apply_mapping(path, matches)
        content = path.read_text(encoding="utf-8")

        assert result.rewritten is False
        assert content.count("@task:TASK-AUTH-001") == 1
        assert 1 in result.skipped_already_tagged

    def test_idempotency_double_run(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-AUTH-001", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-AUTH-002", confidence=0.9),
        ]
        apply_mapping(path, matches)
        first_content = path.read_text(encoding="utf-8")

        # Second run: same matches supplied.
        result2 = apply_mapping(path, matches)
        second_content = path.read_text(encoding="utf-8")

        assert first_content == second_content
        assert result2.rewritten is False
        assert set(result2.skipped_already_tagged) == {0, 1}
        assert result2.linked == []

    def test_preserves_comments_and_blank_lines(self, feature_file):
        path = feature_file(_FEATURE_WITH_COMMENTS_AND_BLANKS)
        original = path.read_text(encoding="utf-8")

        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-LOGIN-OK", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-LOGIN-BAD", confidence=0.9),
        ]
        apply_mapping(path, matches)
        rewritten = path.read_text(encoding="utf-8")

        # Every original line should survive, plus two new @task: lines.
        for original_line in original.splitlines():
            assert original_line in rewritten, f"Lost line: {original_line!r}"
        assert rewritten.count("@task:") == 2

    def test_confidence_threshold_filters_matches(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-A", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-B", confidence=0.3),  # below default 0.6
        ]
        result = apply_mapping(path, matches)
        content = path.read_text(encoding="utf-8")

        assert (0, "TASK-A") in result.linked
        assert len(result.skipped_low_confidence) == 1
        assert result.skipped_low_confidence[0][1] == "TASK-B"
        assert "@task:TASK-A" in content
        assert "@task:TASK-B" not in content

    def test_custom_threshold_lets_lower_confidence_pass(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [TaskMatch(scenario_index=0, task_id="TASK-X", confidence=0.4)]
        result = apply_mapping(path, matches, confidence_threshold=0.3)
        assert (0, "TASK-X") in result.linked

    def test_highest_confidence_wins_on_duplicate_scenario_matches(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-WRONG", confidence=0.7),
            TaskMatch(scenario_index=0, task_id="TASK-RIGHT", confidence=0.95),
        ]
        result = apply_mapping(path, matches)
        content = path.read_text(encoding="utf-8")

        assert (0, "TASK-RIGHT") in result.linked
        assert "@task:TASK-RIGHT" in content
        assert "@task:TASK-WRONG" not in content

    def test_more_scenarios_than_tasks_leaves_extras_untagged(self, feature_file):
        # _SIMPLE_FEATURE has 2 scenarios; we supply a match only for index 0.
        path = feature_file(_SIMPLE_FEATURE)
        matches = [TaskMatch(scenario_index=0, task_id="TASK-ONLY", confidence=0.9)]
        result = apply_mapping(path, matches)

        assert result.linked == [(0, "TASK-ONLY")]
        assert result.unmatched_scenarios == [1]

    def test_fewer_scenarios_than_tasks_reports_unmatched_tasks(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-A", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-B", confidence=0.9),
            # Extra task with no matching scenario. We simulate this by giving
            # it an invalid (below-threshold) match — the caller is expected
            # to supply the agent's best-effort answer even when confidence
            # is low, so we mimic that shape.
            TaskMatch(scenario_index=0, task_id="TASK-ORPHAN", confidence=0.1),
        ]
        result = apply_mapping(path, matches)
        assert "TASK-ORPHAN" in result.unmatched_tasks
        assert "TASK-A" not in result.unmatched_tasks

    def test_empty_feature_file_is_noop(self, feature_file):
        path = feature_file(_EMPTY_FEATURE)
        result = apply_mapping(path, [])
        assert result.linked == []
        assert result.rewritten is False

    def test_all_already_tagged_is_noop(self, feature_file):
        content = """Feature: All tagged

  @task:TASK-001
  Scenario: A
    Given nothing

  @task:TASK-002
  Scenario: B
    Given nothing
"""
        path = feature_file(content)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-999", confidence=0.99),
            TaskMatch(scenario_index=1, task_id="TASK-888", confidence=0.99),
        ]
        before = path.read_text(encoding="utf-8")
        result = apply_mapping(path, matches)
        after = path.read_text(encoding="utf-8")

        assert before == after
        assert result.rewritten is False
        assert result.linked == []
        assert set(result.skipped_already_tagged) == {0, 1}

    def test_dry_run_does_not_write(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        before = path.read_text(encoding="utf-8")
        result = apply_mapping(
            path,
            [TaskMatch(scenario_index=0, task_id="TASK-A", confidence=0.9)],
            dry_run=True,
        )
        after = path.read_text(encoding="utf-8")

        assert before == after
        assert result.rewritten is False
        assert (0, "TASK-A") in result.linked  # still reported as "would-be linked"

    def test_summary_includes_counts(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=0, task_id="TASK-A", confidence=0.9),
            TaskMatch(scenario_index=1, task_id="TASK-B", confidence=0.2),
        ]
        result = apply_mapping(path, matches)
        assert "linked 1" in result.summary
        assert "below threshold" in result.summary

    def test_invalid_scenario_index_reported_not_crashing(self, feature_file):
        path = feature_file(_SIMPLE_FEATURE)
        matches = [
            TaskMatch(scenario_index=99, task_id="TASK-GHOST", confidence=0.99),
        ]
        result = apply_mapping(path, matches)
        # Agent proposed a bogus index — surface it without crashing.
        assert any(m[1] == "TASK-GHOST" for m in result.skipped_low_confidence)
        assert result.rewritten is False

    def test_preserves_crlf_line_endings(self, tmp_path: Path):
        crlf_content = _SIMPLE_FEATURE.replace("\n", "\r\n")
        path = tmp_path / "crlf.feature"
        path.write_text(crlf_content, encoding="utf-8", newline="")

        result = apply_mapping(
            path,
            [TaskMatch(scenario_index=0, task_id="TASK-CRLF", confidence=0.9)],
        )
        assert result.rewritten is True

        rewritten = path.read_bytes()
        # File should still use CRLF (plus the new tag line uses CRLF too).
        assert b"\r\n" in rewritten
        # And not a mixed ending.
        assert rewritten.count(b"\n") == rewritten.count(b"\r\n")

    def test_atomic_rewrite_cleans_up_tempfile_on_failure(
        self,
        feature_file,
        monkeypatch,
    ):
        """If os.replace raises, the tempfile must not be left behind and the
        source file must be untouched."""
        import os

        path = feature_file(_SIMPLE_FEATURE)
        before = path.read_bytes()
        parent = path.parent
        tempfiles_before = {p.name for p in parent.iterdir()}

        def _boom(src, dst):
            raise OSError("simulated disk error")

        # Patch the os.replace used inside bdd_linker's module namespace.
        from installer.core.commands.lib import bdd_linker as mod
        monkeypatch.setattr(mod.os, "replace", _boom)

        with pytest.raises(OSError, match="simulated disk error"):
            apply_mapping(
                path,
                [TaskMatch(scenario_index=0, task_id="TASK-FAIL", confidence=0.9)],
            )

        # Source untouched, tempfile cleaned up.
        assert path.read_bytes() == before
        tempfiles_after = {p.name for p in parent.iterdir()}
        assert tempfiles_after == tempfiles_before

    def test_scenario_outline_tagged_like_scenario(self, feature_file):
        content = """Feature: Pricing

  Scenario Outline: Discount tiers
    Given a user with <spend> in monthly spend
    Then their discount is <discount>

    Examples:
      | spend | discount |
      |  100  |    5     |
      |  500  |   15     |
"""
        path = feature_file(content)
        result = apply_mapping(
            path,
            [TaskMatch(scenario_index=0, task_id="TASK-TIER", confidence=0.9)],
        )
        rewritten = path.read_text(encoding="utf-8")
        assert "  @task:TASK-TIER\n  Scenario Outline: Discount tiers" in rewritten
        assert result.rewritten is True
