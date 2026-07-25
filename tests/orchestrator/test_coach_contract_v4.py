"""TASK-CMIR-002: v4 Decision Format prompt + vocabulary mirror (switch-gated).

Tests the contract-resolution seam for the Coach synthesis prompt:

* ``_resolve_coach_contract`` reads ``GUARDKIT_COACH_CONTRACT`` (default
  ``"coachsplit"``) and returns the active contract identifier.
* Under ``contract=v4`` the rendered synthesis prompt contains the v4
  Decision Format block (``verdict`` + ``findings`` shape) and does NOT
  contain legacy vocabulary.
* Under ``contract=coachsplit`` the rendered prompt is byte-identical to
  the legacy path (the existing test suite passes unmodified).
* The synthesis budget (_trim_synthesis_prompt) still applies on the v4
  path and its _VERDICT_BEARING_MARKERS still protect evidence sections.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    _resolve_coach_contract,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _build_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker for prompt/routing tests."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


# ---------------------------------------------------------------------------
# Contract resolution
# ---------------------------------------------------------------------------


class TestContractResolution:
    def test_default_is_coachsplit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        assert _resolve_coach_contract() == "coachsplit"

    @pytest.mark.parametrize("val", ["", "coachsplit", " CoachSplit "])
    def test_coachsplit_values(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", val)
        # Empty string falls back to default
        if val == "":
            assert _resolve_coach_contract() == "coachsplit"
        else:
            assert _resolve_coach_contract() == val

    def test_v4_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        assert _resolve_coach_contract() == "v4"


# ---------------------------------------------------------------------------
# AC-1: v4 Decision Format block — present and legacy strings absent
# ---------------------------------------------------------------------------


LEGACY_DECISION_FORMAT_STRINGS = [
    "fenced JSON block",
    "criteria_verification",
    '"decision": "approve" | "feedback"',
    "takes only the **last** fenced block",
]


class TestV4DecisionFormatBlock:
    def test_v4_prompt_contains_verdict_shape(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-V4-001",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            synthesis=False,
        )
        assert '"verdict": "approve" | "reject"' in prompt
        assert '"findings": []' in prompt

    @pytest.mark.parametrize("bad_str", LEGACY_DECISION_FORMAT_STRINGS)
    def test_v4_prompt_excludes_legacy_strings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_str: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-V4-002",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            synthesis=False,
        )
        assert bad_str not in prompt, f"Legacy string found in v4 prompt: {bad_str!r}"


# ---------------------------------------------------------------------------
# AC-2: v4 vocabulary substitutions — legacy phrases absent
# ---------------------------------------------------------------------------


LEGACY_VOCABULARY_PHRASES = [
    "Surface as feedback",
    'Surface a "feedback" decision',
    "verbatim in the rationale",
    "that is FEEDBACK, not approval",
    "Either APPROVE or provide specific FEEDBACK",
    "create a criteria_verification entry",
]


class TestV4VocabularySubstitutions:
    @pytest.mark.parametrize("bad_phrase", LEGACY_VOCABULARY_PHRASES)
    def test_v4_prompt_excludes_legacy_vocabulary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_phrase: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-V4-003",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            evidence_bundle=SimpleNamespace(
                honesty=SimpleNamespace(
                    verified=True,
                    discrepancies=[],
                    honesty_score=1.0,
                    resolved_paths=[],
                ),
                gathering_status="complete",
            ),
            synthesis=True,
        )
        assert bad_phrase not in prompt, (
            f"Legacy vocabulary found in v4 prompt: {bad_phrase!r}"
        )

    def test_v4_prompt_contains_v4_vocabulary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-V4-004",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            evidence_bundle=SimpleNamespace(
                honesty=SimpleNamespace(
                    verified=True,
                    discrepancies=[],
                    honesty_score=1.0,
                    resolved_paths=[],
                ),
                gathering_status="complete",
            ),
            synthesis=True,
        )
        assert "flag as feedback" in prompt
        assert "issue a 'reject' decision" in prompt
        assert "verbatim in the findings" in prompt
        assert "that is REJECT, not APPROVE" in prompt
        assert "APPROVE or REJECT" in prompt
        assert "include findings[]" in prompt


# ---------------------------------------------------------------------------
# AC-3: coachsplit path — byte-identical to legacy
# ---------------------------------------------------------------------------


class TestCoachsplitBackwardCompatibility:
    def test_coachsplit_prompt_contains_legacy_strings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-CS-001",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            synthesis=False,
        )
        # Legacy format must be present
        assert '"decision": "approve" | "feedback"' in prompt
        assert "criteria_verification" in prompt
        assert "fenced JSON block" in prompt

    def test_coachsplit_prompt_contains_legacy_vocabulary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-CS-002",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            evidence_bundle=SimpleNamespace(
                honesty=SimpleNamespace(
                    verified=True,
                    discrepancies=[],
                    honesty_score=1.0,
                    resolved_paths=[],
                ),
                gathering_status="complete",
            ),
            synthesis=True,
        )
        assert "Surface as feedback" in prompt
        assert 'Surface a "feedback" decision' in prompt
        assert "verbatim in the rationale" in prompt
        assert "that is FEEDBACK, not approval" in prompt
        assert "Either APPROVE or provide specific FEEDBACK" in prompt
        assert "create a criteria_verification entry" in prompt


# ---------------------------------------------------------------------------
# AC-4: synthesis budget still applies on v4 path
# ---------------------------------------------------------------------------


class TestSynthesisBudgetV4Path:
    def test_trim_synthesis_prompt_applies_to_v4_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        invoker = _build_invoker(tmp_path)
        # Create a large player report to trigger trimming
        large_report = {"files_modified": ["x"] * 5000}
        prompt = invoker._build_coach_prompt(
            task_id="TASK-V4-005",
            turn=1,
            requirements="test reqs",
            player_report=large_report,
            synthesis=True,
        )
        # The prompt should still contain verdict-bearing markers
        for marker in AgentInvoker._VERDICT_BEARING_MARKERS:
            assert marker in prompt, f"Verdict-bearing marker missing: {marker!r}"

    def test_verdict_bearing_markers_protected_in_v4_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        invoker = _build_invoker(tmp_path)
        prompt = invoker._build_coach_prompt(
            task_id="TASK-V4-006",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            synthesis=True,
        )
        # Core verdict-bearing sections must survive
        assert "## Original Requirements" in prompt
        assert "## Acceptance Criteria to Verify" in prompt
        assert "<absence_of_failure_guards>" in prompt
