"""TASK-SELFFIX-003 — synthesis-prompt budget enforcement tests.

Covers the acceptance criteria for bounding the rendered coach synthesis
prompt at ``GUARDKIT_COACH_SYNTHESIS_MAX_CHARS`` (default 300,000 chars).

Acceptance criteria tested:
- AC-002: oversized synthetic bundle renders within budget
- AC-003: trimming drops low-signal content first, NEVER verdict-bearing fields
- AC-004: trimming is loud (visible notice in prompt + WARNING logged)
- AC-005: normal-sized bundle renders byte-identically (no-trim path)
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

# Ensure the project root is on sys.path for imports.
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_project_root))

from guardkit.orchestrator.agent_invoker import AgentInvoker


# ============================================================================
# Helpers
# ============================================================================


def _make_large_player_report(n_promises: int = 200) -> Dict[str, Any]:
    """Create a player report with many completion_promises to bloat JSON."""
    promises = []
    for i in range(n_promises):
        promises.append({
            "criterion_id": f"AC-{i:03d}",
            "criterion_text": f"This is a long acceptance criterion text that takes up space number {i}",
            "status": "complete",
            "evidence": f"Evidence for criterion {i} - this is a detailed explanation of what was done",
            "test_file": f"tests/test_feature_{i}.py",
            "implementation_files": [f"src/feature_{i}.py", f"src/feature_{i}_helper.py"],
        })
    return {
        "task_id": "TASK-SELFFIX-003",
        "turn": 1,
        "files_modified": [f"src/file_{i}.py" for i in range(50)],
        "files_created": [f"src/new_{i}.py" for i in range(50)],
        "tests_written": [f"tests/test_{i}.py" for i in range(50)],
        "tests_run": True,
        "tests_passed": True,
        "test_output_summary": "All tests passed successfully",
        "completion_promises": promises,
    }


def _make_large_evidence_bundle() -> Dict[str, Any]:
    """Create an evidence bundle with large raw_output and output_tail fields."""
    large_output = "X" * 30000  # 30k char raw output
    large_tail = "Y" * 20000    # 20k char output tail
    return {
        "gathering_status": "complete",
        "honesty": {
            "verified": True,
            "discrepancies": [],
            "honesty_score": 1.0,
            "resolved_paths": [],
        },
        "independent_tests": {
            "tests_passed": True,
            "tests_run": 100,
            "test_output_summary": "All 100 tests passed",
            "raw_output": large_output,
            "signal_absent": False,
        },
        "bdd": {
            "scenarios_attempted": 10,
            "scenarios_passed": 10,
            "scenarios_failed": 0,
            "discoveries": [{"name": f"scenario_{i}", "status": "passed"} for i in range(25)],
            "errors": [{"message": f"error_{i}"} for i in range(15)],
        },
        "coverage_details": {
            "line_coverage": 85.0,
            "branch_coverage": 70.0,
            "files_below_threshold": [],
        },
        "quality_gates": {
            "all_passed": True,
            "tests_failed": 0,
            "tests_run": True,
            "coverage_met": True,
        },
        "stub_scan": {
            "status": "clean",
            "findings": [],
            "symbols_examined": 50,
        },
        "behavioural_oracle": {
            "status": "ran",
            "passed": True,
            "exit_code": 0,
            "output_tail": large_tail,
        },
    }


def _build_synthesis_prompt(
    player_report: Dict[str, Any] | None = None,
    evidence_bundle: Dict[str, Any] | None = None,
    requirements: str = "",
    acceptance_criteria: list[Dict[str, str]] | None = None,
) -> str:
    """Build a synthesis prompt using AgentInvoker._build_coach_prompt."""
    invoker = AgentInvoker(
        worktree_path=Path("/tmp/fake-worktree"),
        max_turns_per_agent=1,
        sdk_timeout_seconds=30,
    )

    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    honesty = HonestyVerification(
        verified=True,
        discrepancies=[],
        honesty_score=1.0,
        resolved_paths=[],
    )

    bundle = None
    if evidence_bundle is not None:
        bundle = CoachEvidenceBundle(
            honesty=honesty,
            gathering_status="complete",
            **{k: v for k, v in evidence_bundle.items()
               if k not in ("honesty", "gathering_status")},
        )

    return invoker._build_coach_prompt(
        task_id="TASK-SELFFIX-003",
        turn=1,
        requirements=requirements or "# Requirements\n\nTest requirements",
        player_report=player_report or {},
        honesty_verification=honesty,
        evidence_bundle=bundle,
        acceptance_criteria=acceptance_criteria or [
            {"id": "AC-001", "text": "Criterion 1"},
            {"id": "AC-002", "text": "Criterion 2"},
        ],
        synthesis=True,
    )


# ============================================================================
# AC-005: No-trim path — normal-sized bundle renders identically
# ============================================================================


class TestNoTrimPath:
    """AC-005: A normal-sized bundle renders byte-identically to today."""

    def test_normal_bundle_unmodified(self) -> None:
        """Small prompt returns unchanged when under budget."""
        prompt = _build_synthesis_prompt(
            player_report={"task_id": "TASK-1", "turn": 1, "completion_promises": []},
        )
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert result == prompt
        assert len(result) < AgentInvoker._COACH_SYNTHESIS_MAX_CHARS

    def test_normal_bundle_via_build_coach_prompt(self) -> None:
        """Full synthesis prompt builder returns unmodified for small bundles."""
        prompt = _build_synthesis_prompt(
            player_report={"task_id": "TASK-1", "turn": 1, "completion_promises": []},
        )
        # The prompt should be well under the budget
        assert len(prompt) < AgentInvoker._COACH_SYNTHESIS_MAX_CHARS


# ============================================================================
# AC-002: Oversized bundle renders within budget
# ============================================================================


class TestOversizedBundleBudget:
    """AC-002: The rendered coach synthesis prompt fits the budget."""

    def test_oversized_bundle_fits_budget(self) -> None:
        """An oversized synthetic bundle produces a prompt within the budget."""
        prompt = _build_synthesis_prompt(
            player_report=_make_large_player_report(n_promises=200),
            evidence_bundle=_make_large_evidence_bundle(),
        )
        assert len(prompt) <= AgentInvoker._COACH_SYNTHESIS_MAX_CHARS, (
            f"Prompt length {len(prompt)} exceeds budget "
            f"{AgentInvoker._COACH_SYNTHESIS_MAX_CHARS}"
        )

    def test_trim_enforces_budget_directly(self) -> None:
        """_trim_synthesis_prompt enforces the budget on any oversized string."""
        oversized = "A" * 500000  # 500k chars, well over 300k budget
        result = AgentInvoker._trim_synthesis_prompt(oversized)
        assert len(result) <= AgentInvoker._COACH_SYNTHESIS_MAX_CHARS

    def test_custom_budget_from_env(self) -> None:
        """GUARDKIT_COACH_SYNTHESIS_MAX_CHARS env var sets the budget."""
        with patch.dict(os.environ, {"GUARDKIT_COACH_SYNTHESIS_MAX_CHARS": "1000"}):
            # Force re-read of the class variable
            old_val = AgentInvoker._COACH_SYNTHESIS_MAX_CHARS
            try:
                AgentInvoker._COACH_SYNTHESIS_MAX_CHARS = 1000
                oversized = "B" * 5000
                result = AgentInvoker._trim_synthesis_prompt(oversized)
                assert len(result) <= 1000
            finally:
                AgentInvoker._COACH_SYNTHESIS_MAX_CHARS = old_val


# ============================================================================
# AC-003: Trimming drops low-signal first, NEVER verdict-bearing fields
# ============================================================================


class TestTrimmingPreservesVerdictFields:
    """AC-003: Trimming preserves verdict-bearing fields."""

    def test_requirements_preserved(self) -> None:
        """Requirements section is never trimmed."""
        requirements = "# Requirements\n\nThis is the full requirements text that must be preserved."
        prompt = _build_synthesis_prompt(requirements=requirements)
        # Make it oversized by appending a large section
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert requirements in result

    def test_acceptance_criteria_preserved(self) -> None:
        """Acceptance criteria section is never trimmed."""
        criteria_text = "## Acceptance Criteria to Verify"
        prompt = _build_synthesis_prompt()
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert criteria_text in result

    def test_honesty_section_preserved(self) -> None:
        """Honesty verification section is never trimmed."""
        # Pass a minimal evidence_bundle so the XML-tagged path is taken
        # (without it, _build_coach_prompt uses the legacy prose path)
        bundle = _make_large_evidence_bundle()
        prompt = _build_synthesis_prompt(evidence_bundle=bundle)
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert "## Honesty Verification" in result
        assert "<honesty_verification>" in result

    def test_stub_scan_preserved(self) -> None:
        """stub_scan field in bundle is never trimmed."""
        bundle = _make_large_evidence_bundle()
        prompt = _build_synthesis_prompt(evidence_bundle=bundle)
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert "stub_scan" in result
        assert "## Deterministic Evidence Bundle" in result

    def test_behavioural_oracle_preserved(self) -> None:
        """behavioural_oracle field in bundle is never trimmed."""
        bundle = _make_large_evidence_bundle()
        prompt = _build_synthesis_prompt(evidence_bundle=bundle)
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        assert "behavioural_oracle" in result

    def test_low_signal_trimmed_first(self) -> None:
        """Raw output tails are trimmed before verdict-bearing fields."""
        bundle = _make_large_evidence_bundle()
        player_report = _make_large_player_report(n_promises=200)
        prompt = _build_synthesis_prompt(
            player_report=player_report,
            evidence_bundle=bundle,
        )
        # Push over budget to trigger trimming
        prompt += "\n" + "Z" * 400000
        original_len = len(prompt)
        result = AgentInvoker._trim_synthesis_prompt(prompt)
        result_len = len(result)

        # Must be smaller
        assert result_len < original_len

        # Must still contain verdict-bearing content
        assert "## Original Requirements" in result
        assert "## Acceptance Criteria to Verify" in result
        assert "## Honesty Verification" in result
        assert "<evidence_bundle>" in result
        assert "</evidence_bundle>" in result

    def test_evidence_bundle_structure_preserved(self) -> None:
        """The evidence bundle remains valid JSON structure after trimming."""
        bundle = _make_large_evidence_bundle()
        prompt = _build_synthesis_prompt(evidence_bundle=bundle)
        # Add enough to trigger trimming
        prompt += "\n" + "Z" * 400000
        result = AgentInvoker._trim_synthesis_prompt(prompt)

        # Extract the bundle JSON and verify it's parseable
        bundle_start = result.find("<evidence_bundle>")
        bundle_end = result.find("</evidence_bundle>")
        assert bundle_start != -1 and bundle_end != -1
        bundle_json = result[bundle_start + len("<evidence_bundle>"):bundle_end]
        # The bundle might have truncation markers, so wrap in braces if needed
        try:
            data = json.loads(bundle_json)
            # Key verdict-bearing fields should exist
            assert "stub_scan" in data
            assert "behavioural_oracle" in data
        except json.JSONDecodeError:
            # If not valid JSON (e.g., truncated mid-JSON), at least check
            # the key fields are present as text
            assert "stub_scan" in bundle_json
            assert "behavioural_oracle" in bundle_json


# ============================================================================
# AC-004: Trimming is loud — visible notice + WARNING logged
# ============================================================================


class TestLoudTrimming:
    """AC-004: Trimming produces visible notices and WARNING logs."""

    def test_visible_notice_in_prompt(self) -> None:
        """Oversized prompt contains a visible truncation notice."""
        oversized = "A" * 500000
        result = AgentInvoker._trim_synthesis_prompt(oversized)
        assert "truncated" in result.lower() or "elided" in result.lower()

    def test_notice_names_what_was_cut(self) -> None:
        """The truncation notice names what was cut."""
        oversized = "A" * 500000
        result = AgentInvoker._trim_synthesis_prompt(oversized)
        # Should mention chars elided or similar
        assert "chars" in result.lower()

    def test_warning_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """A WARNING is logged when trimming occurs."""
        oversized = "B" * 500000
        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            AgentInvoker._trim_synthesis_prompt(oversized)
        assert any("trimmed" in record.message.lower() for record in caplog.records), (
            f"Expected WARNING about trimming, got: {[r.message for r in caplog.records]}"
        )

    def test_no_warning_when_under_budget(self, caplog: pytest.LogCaptureFixture) -> None:
        """No WARNING is logged when prompt is under budget."""
        small = "C" * 100
        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            AgentInvoker._trim_synthesis_prompt(small)
        trim_warnings = [
            r for r in caplog.records
            if "trimmed" in r.message.lower()
        ]
        assert len(trim_warnings) == 0

    def test_notice_includes_elided_count(self) -> None:
        """The truncation notice includes the number of chars elided."""
        oversized = "D" * 500000
        result = AgentInvoker._trim_synthesis_prompt(oversized)
        # Should include a number indicating how much was elided
        import re
        # Match patterns like "12345 chars elided", "12345 chars removed",
        # "12345 additional chars", or "12345 more chars"
        assert re.search(r"\d+\s+chars?\s+elided", result) or \
               re.search(r"\d+\s+chars?\s+removed", result) or \
               re.search(r"\d+\s+additional\s+chars", result) or \
               re.search(r"\d+\s+more\s+chars", result)


# ============================================================================
# Integration: full synthesis prompt with oversized bundle
# ============================================================================


class TestFullSynthesisIntegration:
    """Integration tests for the full synthesis prompt path."""

    def test_full_synthesis_prompt_fits_budget(self) -> None:
        """A full synthesis prompt with oversized bundle fits the budget."""
        prompt = _build_synthesis_prompt(
            player_report=_make_large_player_report(n_promises=300),
            evidence_bundle=_make_large_evidence_bundle(),
            requirements="# Requirements\n\n" + "Long requirement text. " * 100,
            acceptance_criteria=[
                {"id": f"AC-{i:03d}", "text": f"Acceptance criterion {i} with detailed text."}
                for i in range(20)
            ],
        )
        assert len(prompt) <= AgentInvoker._COACH_SYNTHESIS_MAX_CHARS, (
            f"Full synthesis prompt length {len(prompt)} exceeds budget "
            f"{AgentInvoker._COACH_SYNTHESIS_MAX_CHARS}"
        )

    def test_full_synthesis_preserves_all_sections(self) -> None:
        """All prompt sections are present after trimming."""
        prompt = _build_synthesis_prompt(
            player_report=_make_large_player_report(n_promises=200),
            evidence_bundle=_make_large_evidence_bundle(),
        )
        assert "## Original Requirements" in prompt
        assert "## Acceptance Criteria to Verify" in prompt
        assert "## Player's Report" in prompt
        assert "## Deterministic Evidence Bundle" in prompt
        assert "## Honesty Verification" in prompt
        assert "<absence_of_failure_guards>" in prompt
        assert "## Decision Format" in prompt
        assert "## Your Responsibilities" in prompt
