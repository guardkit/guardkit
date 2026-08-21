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

# Path to fixture files for byte-comparison tests.
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "coach-contract"


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
    """Resolution precedence: env > ``.guardkit/config.yaml`` > built-in default.

    The two DEFAULT-tier tests below run from an empty ``tmp_path`` on purpose.
    ``_resolve_coach_contract()`` reads ``.guardkit/config.yaml`` from the
    CURRENT WORKING DIRECTORY, and guardkit's own config has declared
    ``autobuild.coach.contract: v4`` since the 2026-07-26 v4 flip (754ce150,
    a deliberate production change). Clearing only the environment variable
    therefore did not reach the default tier at all — it fell through to
    guardkit's own config and read ``v4``, so the tests were measuring the
    repo they happened to run in rather than the default they name.
    Chdir-ing to a directory with no config is what isolates the default tier.
    (Config-tier behaviour is covered separately by the resolver's own tests.)
    """

    def test_default_is_coachsplit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_CONTRACT", raising=False)
        monkeypatch.chdir(tmp_path)  # no .guardkit/config.yaml here
        assert _resolve_coach_contract() == "coachsplit"

    @pytest.mark.parametrize("val", ["", "coachsplit", " CoachSplit "])
    def test_coachsplit_values(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, val: str
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", val)
        monkeypatch.chdir(tmp_path)  # no .guardkit/config.yaml here
        # Empty falls back to default; non-enum values (incl. case/space
        # variants) NORMALIZE then validate — never pass through raw.
        assert _resolve_coach_contract() == "coachsplit"

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
            acceptance_criteria=[{"id": "AC-001", "text": "Test criterion"}],
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
        assert "Surface as a reject finding" in prompt
        assert 'Surface a "reject" verdict' in prompt
        assert "verbatim in the finding locus" in prompt
        assert "that is a REJECT, not approval" in prompt
        assert "Either APPROVE or REJECT with specific findings" in prompt
        assert "verify each criterion against the evidence" in prompt
        assert "## Acceptance Criteria to Verify" in prompt


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
            acceptance_criteria=[{"id": "AC-001", "text": "Test criterion"}],
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
        assert "## Acceptance Criteria to Verify" in prompt


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
            acceptance_criteria=[{"id": "AC-001", "text": "Test criterion"}],
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
        # The prompt should still contain verdict-bearing markers
        # (behavioural_oracle and stub_scan only appear when present in evidence)
        always_present = [
            "## Original Requirements",
            "## Acceptance Criteria to Verify",
            "## Honesty Verification",
            "<honesty_verification>",
            "<evidence_bundle>",
            "## Deterministic Evidence Bundle",
            "<absence_of_failure_guards>",
        ]
        for marker in always_present:
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
            acceptance_criteria=[{"id": "AC-001", "text": "Test criterion"}],
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
        # Core verdict-bearing sections must survive
        assert "## Original Requirements" in prompt
        assert "## Acceptance Criteria to Verify" in prompt
        assert "<absence_of_failure_guards>" in prompt


# ---------------------------------------------------------------------------
# AC-1 (byte-compare): v4 Decision Format block matches spec verbatim
# ---------------------------------------------------------------------------


class TestV4SpecByteCompare:
    def test_v4_prompt_contains_verbatim_spec_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: The v4 Decision Format block in the rendered prompt must
        match the normative spec text VERBATIM (byte-compare)."""
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")
        spec_text = (_FIXTURES_DIR / "v4_decision_format_spec.txt").read_text()
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-V4-BYTE-001",
            turn=1,
            requirements="test reqs",
            player_report={"files_modified": []},
            synthesis=False,
        )
        assert spec_text in prompt, (
            "v4 Decision Format block does not match spec verbatim"
        )

    def test_v4_spec_file_is_non_empty(self) -> None:
        """Sanity: the spec file must exist and be non-empty."""
        spec = (_FIXTURES_DIR / "v4_decision_format_spec.txt").read_text()
        assert len(spec) > 0, "v4 spec file is empty"
        assert "## Decision Format" in spec


# ---------------------------------------------------------------------------
# AC-3 (golden): coachsplit prompt is byte-identical to baseline
# ---------------------------------------------------------------------------


class TestCoachsplitGoldenBaseline:
    def test_coachsplit_prompt_matches_golden_baseline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3: The coachsplit prompt (default contract) must be
        byte-identical to the golden baseline file."""
        monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "coachsplit")
        baseline = (_FIXTURES_DIR / "coachsplit_golden_baseline.txt").read_text()
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-GOLDEN-CS-001",
            turn=1,
            requirements="test requirements",
            player_report={
                "files_modified": ["src/test.py"],
                "files_created": [],
                "tests_written": ["tests/test.py"],
            },
            synthesis=False,
        )
        assert prompt == baseline, (
            "coachsplit prompt is NOT byte-identical to golden baseline"
        )

    def test_golden_baseline_file_is_non_empty(self) -> None:
        """Sanity: the golden baseline file must exist and be non-empty."""
        baseline = (_FIXTURES_DIR / "coachsplit_golden_baseline.txt").read_text()
        assert len(baseline) > 0, "coachsplit golden baseline is empty"
        assert "## Decision Format" in baseline
