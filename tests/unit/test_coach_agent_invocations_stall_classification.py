"""Unit tests for TASK-FIX-7A07 coach_agent_invocations_stall classification.

Covers AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7 and AC-9:

1. ``classify_stall`` detects ``coach_agent_invocations_stall`` when N recent
   turns all carry ``coach_result.report.issues[0].category ==
   "agent_invocations_violation"`` (AC-1).
2. ``_build_summary_details`` emits the new actionable hint citing
   sub-agent names (AC-2).
3. ``coach_validator.py``'s issue-construction cites specific sub-agent
   names derived from the stack profile (AC-3).
4. Review-summary's ``_render_task_table`` shows the sub-type alongside the
   legacy ``unrecoverable_stall`` token and the feature-level verdict flips
   to ``MIXED_PARTIAL_FAILURE`` when appropriate (AC-4, AC-6).
5. ``_normalize_feedback_for_stall`` folds a sorted ``missing_phases``
   canonical form into the md5 input so feedback that differs only by
   phase ordering still collapses to a single stall signature (AC-5).
6. AC-7: Co-fire case — ``coach_agent_invocations_stall`` AND
   ``context_pollution_stall_no_checkpoint`` produce a decision_subtype
   containing both labels joined with ``" + "``.
7. AC-7: TASK-FIX-7A02 ``player_invocation_stall`` continues to classify
   correctly with no cross-branch regression.
8. AC-9: Replay the minimised jarvis FEAT-J002 fixture and assert the new
   classifier produces ``coach_agent_invocations_stall``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    STALL_COACH_AGENT_INVOCATIONS,
    STALL_CONTEXT_POLLUTION,
    STALL_FEEDBACK_GENERIC,
    StallClassification,
    TurnRecord,
    _extract_agent_invocations_violation,
    classify_stall,
)
from guardkit.orchestrator.phase_specialists import (
    GENERIC_PHASE_3_FALLBACK,
    phase_3_specialist_for_stack,
    render_missing_phase_list,
    specialist_for_phase,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _make_orchestrator() -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=10)


def _real_player_result(turn: int, task_id: str = "TASK-TEST-7A07") -> AgentInvocationResult:
    """A real Player report — not synthetic. Ensures we don't confuse the
    7A07 classifier with the 7A02 player-invocation-stall detector."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": ["src/feature.py"],
            "files_created": ["tests/test_feature.py"],
            "tests_passed": True,
            "test_count": 5,
            "implementation_notes": "Real Player report",
        },
        duration_seconds=12.0,
        error=None,
    )


def _coach_result_with_violation(
    turn: int,
    missing_phases: Optional[List[Any]] = None,
    expected_phases: int = 3,
    actual_invocations: int = 1,
    task_id: str = "TASK-TEST-7A07",
) -> AgentInvocationResult:
    if missing_phases is None:
        missing_phases = ["4", "5"]
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": f"Agent-invocations protocol violation: missing phases {', '.join(str(p) for p in missing_phases)}",
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "agent_invocations_violation",
                    "description": "task-work results claim phases were completed without matching invocations.",
                    "details": {
                        "missing_phases": missing_phases,
                        "expected_phases": expected_phases,
                        "actual_invocations": actual_invocations,
                    },
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )


def _turn_from_agent_invocations_violation(
    turn: int,
    missing_phases: Optional[List[Any]] = None,
    task_id: str = "TASK-TEST-7A07",
) -> TurnRecord:
    coach_result = _coach_result_with_violation(
        turn, missing_phases, task_id=task_id
    )
    feedback = coach_result.report["feedback"]
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn, task_id),
        coach_result=coach_result,
        decision="feedback",
        feedback=feedback,
        timestamp=f"2026-04-24T11:0{turn}:00Z",
    )


def _turn_from_generic_coach_rejection(turn: int) -> TurnRecord:
    """Coach rejected on AC grounds (no agent_invocations_violation issue)."""
    feedback = (
        "0/5 acceptance criteria passing. AC-001: tests not written. "
        "AC-002: error handling missing."
    )
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-7A07",
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": feedback,
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "acceptance_criteria",
                    "description": "0/5 criteria passing",
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=feedback,
        timestamp=f"2026-04-24T11:0{turn}:00Z",
    )


# ---------------------------------------------------------------------------
# AC-1: classify_stall + coach_agent_invocations detection
# ---------------------------------------------------------------------------


class TestExtractAgentInvocationsViolation:
    """Predicate: ``_extract_agent_invocations_violation`` — schema-stable walk."""

    def test_returns_violation_dict_when_present(self):
        turn = _turn_from_agent_invocations_violation(1)
        violation = _extract_agent_invocations_violation(turn)
        assert violation is not None
        assert violation["category"] == "agent_invocations_violation"

    def test_returns_none_when_no_coach_result(self):
        turn = TurnRecord(
            turn=1,
            player_result=_real_player_result(1),
            coach_result=None,
            decision="error",
            feedback=None,
            timestamp="2026-04-24T11:00:00Z",
        )
        assert _extract_agent_invocations_violation(turn) is None

    def test_returns_none_when_non_violation_issues(self):
        turn = _turn_from_generic_coach_rejection(1)
        assert _extract_agent_invocations_violation(turn) is None

    def test_returns_none_when_issues_missing(self):
        coach_result = AgentInvocationResult(
            task_id="TASK-TEST-7A07",
            turn=1,
            agent_type="coach",
            success=True,
            report={"decision": "feedback", "feedback": "ok"},
            duration_seconds=0.1,
        )
        turn = TurnRecord(
            turn=1,
            player_result=_real_player_result(1),
            coach_result=coach_result,
            decision="feedback",
            feedback="ok",
            timestamp="2026-04-24T11:00:00Z",
        )
        assert _extract_agent_invocations_violation(turn) is None


class TestClassifyStallCoachAgentInvocations:
    """AC-1: three consecutive violation turns → coach_agent_invocations_stall."""

    def test_three_violation_turns_classified(self):
        history = [_turn_from_agent_invocations_violation(i) for i in range(1, 4)]
        c = classify_stall(history, "unrecoverable_stall")
        assert c is not None
        assert c.decision_label == STALL_COACH_AGENT_INVOCATIONS
        assert STALL_COACH_AGENT_INVOCATIONS in c.co_fires
        assert c.decision_subtype == STALL_COACH_AGENT_INVOCATIONS

    def test_missing_phases_populated(self):
        history = [
            _turn_from_agent_invocations_violation(i, missing_phases=["4", "5"])
            for i in range(1, 4)
        ]
        c = classify_stall(history, "unrecoverable_stall")
        assert c is not None
        assert c.missing_phases == ["4", "5"]
        assert c.expected_phases == 3
        assert c.actual_invocations == 1

    def test_missing_phases_dict_form_normalised(self):
        """When missing_phases is stored as [{"phase": "...", "description": "..."}]."""
        history = [
            _turn_from_agent_invocations_violation(
                i,
                missing_phases=[
                    {"phase": "5", "description": "Code Review"},
                    {"phase": "4", "description": "Testing"},
                ],
            )
            for i in range(1, 4)
        ]
        c = classify_stall(history, "unrecoverable_stall")
        assert c is not None
        assert c.missing_phases == ["4", "5"]  # sorted

    def test_two_violations_below_threshold_no_classification(self):
        history = [_turn_from_agent_invocations_violation(i) for i in range(1, 3)]
        c = classify_stall(history, "unrecoverable_stall")
        # Below threshold, falls back to generic
        assert c is not None
        assert c.decision_label == STALL_FEEDBACK_GENERIC

    def test_non_stall_final_decision_returns_none(self):
        history = [_turn_from_agent_invocations_violation(i) for i in range(1, 4)]
        assert classify_stall(history, "approved") is None
        assert classify_stall(history, "max_turns_exceeded") is None
        assert classify_stall(history, "player_invocation_stall") is None

    def test_interleaved_non_violation_breaks_classification(self):
        history = [
            _turn_from_agent_invocations_violation(1),
            _turn_from_generic_coach_rejection(2),
            _turn_from_agent_invocations_violation(3),
        ]
        c = classify_stall(history, "unrecoverable_stall")
        assert c is not None
        # Not all 3 recent turns carry the violation, falls back to generic.
        assert STALL_COACH_AGENT_INVOCATIONS not in c.co_fires
        assert c.decision_label == STALL_FEEDBACK_GENERIC


# ---------------------------------------------------------------------------
# AC-2: _build_summary_details renders the new hint
# ---------------------------------------------------------------------------


class TestSummaryDetailsAgentInvocationsBranch:
    """AC-2: summary-hint renderer names sub-agents and the direct fallback."""

    def test_new_hint_rendered_for_agent_invocations_stall(self):
        orch = _make_orchestrator()
        history = [_turn_from_agent_invocations_violation(i) for i in range(1, 4)]
        summary = orch._build_summary_details(history, "unrecoverable_stall")

        # Names the classification
        assert STALL_COACH_AGENT_INVOCATIONS in summary
        # Cites missing phases
        assert "missing phases" in summary.lower()
        assert "['4', '5']" in summary or "[4, 5]" in summary
        # Cites the task_work_results inspection path
        assert "task_work_results.json" in summary
        assert "agent_invocations_validation" in summary
        # Provides remediation options (a) and (b)
        assert "implementation_mode: direct" in summary
        assert "Task tool" in summary
        # Does NOT emit the generic task-blaming hint
        assert "Review task_type classification" not in summary

    def test_hint_names_phase_4_and_phase_5_specialists(self):
        """When stack template is unresolvable (no settings.json in repo root),
        Phase-3 uses the generic fallback but Phase 4 and Phase 5 still name
        their specialists verbatim."""
        orch = _make_orchestrator()
        history = [
            _turn_from_agent_invocations_violation(i, missing_phases=["4", "5"])
            for i in range(1, 4)
        ]
        summary = orch._build_summary_details(history, "unrecoverable_stall")
        assert "test-orchestrator" in summary
        assert "code-reviewer" in summary


# ---------------------------------------------------------------------------
# AC-3: coach_validator.py issue construction names specialists
# ---------------------------------------------------------------------------


class TestPhaseSpecialistRendering:
    """AC-3 helpers live in guardkit.orchestrator.phase_specialists."""

    def test_phase_4_always_test_orchestrator(self):
        assert specialist_for_phase("4") == "test-orchestrator"

    def test_phase_5_always_code_reviewer(self):
        assert specialist_for_phase("5") == "code-reviewer"

    def test_phase_3_python_stack_resolves_specialist(self):
        assert phase_3_specialist_for_stack("fastapi-python") == "python-api-specialist"

    def test_phase_3_react_stack_resolves_specialist(self):
        assert phase_3_specialist_for_stack("react-typescript") == "react-typescript-specialist"

    def test_phase_3_unknown_stack_falls_back(self):
        """AC-3 + Implementation Note: 'do not hardcode' when detection fails."""
        assert phase_3_specialist_for_stack(None) == GENERIC_PHASE_3_FALLBACK
        assert phase_3_specialist_for_stack("unknown-stack") == GENERIC_PHASE_3_FALLBACK

    def test_render_missing_phase_list_formats_each_phase(self):
        lines = render_missing_phase_list(["3", "4", "5"], "fastapi-python")
        assert len(lines) == 3
        assert "`python-api-specialist`" in lines[0]
        assert "`test-orchestrator`" in lines[1]
        assert "`code-reviewer`" in lines[2]
        assert "(Implementation)" in lines[0]
        assert "(Testing)" in lines[1]
        assert "(Code Review)" in lines[2]

    def test_render_missing_only_4_and_5(self):
        lines = render_missing_phase_list(["4", "5"], stack_template=None)
        assert len(lines) == 2
        assert "`test-orchestrator`" in lines[0]
        assert "`code-reviewer`" in lines[1]


class TestCoachValidatorEnrichedDescription:
    """AC-3: coach_validator's issue description cites specialists."""

    def _make_task_work_results(
        self,
        missing_phases: List[str] = None,
        expected: int = 3,
        actual: int = 1,
    ) -> Dict[str, Any]:
        if missing_phases is None:
            missing_phases = ["4", "5"]
        return {
            "task_id": "TASK-TEST-7A07",
            "quality_gates": {"all_gates_passed": True},
            "agent_invocations_validation": {
                "status": "violation",
                "missing_phases": missing_phases,
                "expected_phases": expected,
                "actual_invocations": actual,
            },
        }

    def test_enriched_description_names_specialists(self, tmp_path, monkeypatch):
        """Build a minimal CoachValidator, feed it synthetic task-work results,
        and assert the resulting feedback issue description includes the
        phase-specialist lines AC-3 prescribes."""
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        # Build a CoachValidator with a bare worktree; missing_phases → 4, 5.
        validator = CoachValidator(worktree_path=tmp_path)

        # Monkeypatch the task_work_results loader to return our fixture so
        # we don't need to render the full feature_validation path.
        results = self._make_task_work_results()
        monkeypatch.setattr(
            validator,
            "read_quality_gate_results",
            lambda *a, **kw: results,
        )

        task_payload = {
            "title": "Test task",
            "description": "unit test",
            "acceptance_criteria": ["AC-1"],
            "task_type": "feature",
        }
        decision = validator.validate(
            task_id="TASK-TEST-7A07",
            turn=5,
            task=task_payload,
        )

        # The violation gate should have returned feedback, not approval.
        assert decision.decision == "feedback"
        # First issue must carry the enriched description (AC-3).
        issue = decision.issues[0]
        assert issue["category"] == "agent_invocations_violation"
        desc = issue["description"]
        # Cites expected/actual counts (AC-3).
        assert "1 of 3" in desc or "1 of" in desc
        # Names Phase 4 and Phase 5 specialists (AC-3).
        assert "test-orchestrator" in desc
        assert "code-reviewer" in desc
        # Phase descriptions included.
        assert "Testing" in desc
        assert "Code Review" in desc


# ---------------------------------------------------------------------------
# AC-4 + AC-6: review_summary renderer
# ---------------------------------------------------------------------------


class TestReviewSummaryDecisionSubtype:
    """AC-4: review-summary shows decision_subtype alongside legacy decision."""

    def _build_result(
        self,
        task_configs: List[Dict[str, Any]],
        feature_id: str = "FEAT-7A07-TEST",
    ):
        """Build a minimal FeatureOrchestrationResult for summary rendering."""
        from guardkit.orchestrator.feature_orchestrator import (
            FeatureOrchestrationResult,
            TaskExecutionResult,
            WaveExecutionResult,
        )
        from guardkit.worktrees import Worktree

        tasks = []
        for i, cfg in enumerate(task_configs, start=1):
            tasks.append(
                TaskExecutionResult(
                    task_id=cfg["task_id"],
                    success=cfg.get("success", False),
                    total_turns=cfg.get("turns", 3),
                    final_decision=cfg.get("final_decision", "unrecoverable_stall"),
                    error=cfg.get("error"),
                    decision_subtype=cfg.get("decision_subtype"),
                    decision_subtype_co_fires=cfg.get("co_fires", []),
                )
            )
        wave = WaveExecutionResult(
            wave_number=cfg.get("wave", 1),
            task_ids=[cfg["task_id"] for cfg in task_configs],
            results=tasks,
            all_succeeded=all(cfg.get("success", False) for cfg in task_configs),
        )
        wt = Worktree(
            task_id=feature_id,
            branch_name="autobuild/fake",
            path=Path("/tmp/nonexistent"),
            base_branch="main",
        )
        return FeatureOrchestrationResult(
            feature_id=feature_id,
            success=all(cfg.get("success", False) for cfg in task_configs),
            status="failed",
            total_tasks=len(task_configs),
            tasks_completed=sum(1 for cfg in task_configs if cfg.get("success")),
            tasks_failed=sum(1 for cfg in task_configs if not cfg.get("success")),
            wave_results=[wave],
            worktree=wt,
            error=None,
        )

    def test_subtype_appears_in_decision_cell(self, tmp_path):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._build_result(
            [
                {
                    "task_id": "TASK-J002-008",
                    "success": False,
                    "turns": 6,
                    "final_decision": "unrecoverable_stall",
                    "decision_subtype": "coach_agent_invocations_stall",
                },
            ]
        )
        generator = ReviewSummaryGenerator(output_dir=tmp_path)
        out = generator.generate(result)
        assert out.success
        md = out.output_path.read_text(encoding="utf-8")
        # Legacy token + new sub-type both present in the Decision column.
        assert "unrecoverable_stall" in md
        assert "coach_agent_invocations_stall" in md
        # Format: "legacy | subtype"
        assert "unrecoverable_stall | coach_agent_invocations_stall" in md

    def test_co_fire_subtype_rendered_with_plus(self, tmp_path):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._build_result(
            [
                {
                    "task_id": "TASK-J002-013",
                    "success": False,
                    "turns": 3,
                    "final_decision": "unrecoverable_stall",
                    "decision_subtype": (
                        "coach_agent_invocations_stall + "
                        "context_pollution_stall_no_checkpoint"
                    ),
                },
            ]
        )
        generator = ReviewSummaryGenerator(output_dir=tmp_path)
        out = generator.generate(result)
        md = out.output_path.read_text(encoding="utf-8")
        assert (
            "coach_agent_invocations_stall + context_pollution_stall_no_checkpoint"
            in md
        )


class TestFeatureVerdictMixedPartialFailure:
    """AC-6: feature-level verdict is MIXED_PARTIAL_FAILURE when applicable."""

    def _build(self, task_configs: List[Dict[str, Any]], status: str = "failed"):
        from guardkit.orchestrator.feature_orchestrator import (
            FeatureOrchestrationResult,
            TaskExecutionResult,
            WaveExecutionResult,
        )
        from guardkit.worktrees import Worktree

        tasks = [
            TaskExecutionResult(
                task_id=cfg["task_id"],
                success=cfg.get("success", False),
                total_turns=cfg.get("turns", 1),
                final_decision=cfg.get("final_decision", "approved"),
                error=cfg.get("error"),
                decision_subtype=cfg.get("decision_subtype"),
            )
            for cfg in task_configs
        ]
        wave = WaveExecutionResult(
            wave_number=1,
            task_ids=[c["task_id"] for c in task_configs],
            results=tasks,
            all_succeeded=False,
        )
        wt = Worktree(
            task_id="FEAT-XXX",
            branch_name="autobuild/fake",
            path=Path("/tmp/nonexistent"),
            base_branch="main",
        )
        return FeatureOrchestrationResult(
            feature_id="FEAT-VERDICT-TEST",
            success=False,
            status=status,
            total_tasks=len(task_configs),
            tasks_completed=sum(1 for c in task_configs if c.get("success")),
            tasks_failed=sum(1 for c in task_configs if not c.get("success")),
            wave_results=[wave],
            worktree=wt,
            error=None,
        )

    def test_14_of_16_approve_2_stall_2_preempt_emits_mixed_partial_failure(
        self, tmp_path
    ):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        configs = []
        # 14 approved tasks
        for i in range(1, 15):
            configs.append(
                {
                    "task_id": f"TASK-OK-{i:03d}",
                    "success": True,
                    "final_decision": "approved",
                    "turns": 1,
                }
            )
        # 2 stalled tasks
        configs.append(
            {
                "task_id": "TASK-STALL-001",
                "success": False,
                "final_decision": "unrecoverable_stall",
                "decision_subtype": "coach_agent_invocations_stall",
                "turns": 6,
            }
        )
        configs.append(
            {
                "task_id": "TASK-STALL-002",
                "success": False,
                "final_decision": "unrecoverable_stall",
                "decision_subtype": "coach_agent_invocations_stall",
                "turns": 3,
            }
        )
        # 2 preempted tasks
        configs.append(
            {
                "task_id": "TASK-PREEMPT-001",
                "success": False,
                "final_decision": "cancelled",
            }
        )
        configs.append(
            {
                "task_id": "TASK-PREEMPT-002",
                "success": False,
                "final_decision": "cancelled",
            }
        )

        result = self._build(configs)
        generator = ReviewSummaryGenerator(output_dir=tmp_path)
        out = generator.generate(result)
        md = out.output_path.read_text(encoding="utf-8")
        assert "MIXED_PARTIAL_FAILURE" in md
        # Headline summary: 14 approved, 2 stalled, 2 preempted
        assert "14 of 18 observed tasks approved" in md
        assert "2 stalled" in md
        assert "2 preempted under stop_on_failure" in md

    def test_all_approved_emits_completed(self, tmp_path):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._build(
            [
                {"task_id": "TASK-A", "success": True, "final_decision": "approved"},
                {"task_id": "TASK-B", "success": True, "final_decision": "approved"},
            ],
            status="completed",
        )
        # Mark success manually because _build sets success=False by default.
        object.__setattr__(result, "success", True)
        object.__setattr__(result, "status", "completed")
        generator = ReviewSummaryGenerator(output_dir=tmp_path)
        out = generator.generate(result)
        md = out.output_path.read_text(encoding="utf-8")
        assert "COMPLETED" in md
        assert "MIXED_PARTIAL_FAILURE" not in md

    def test_all_failed_no_preempt_emits_failed_not_mixed(self, tmp_path):
        from guardkit.orchestrator.review_summary import ReviewSummaryGenerator

        result = self._build(
            [
                {
                    "task_id": "TASK-A",
                    "success": False,
                    "final_decision": "unrecoverable_stall",
                    "decision_subtype": "coach_agent_invocations_stall",
                },
                {
                    "task_id": "TASK-B",
                    "success": False,
                    "final_decision": "unrecoverable_stall",
                    "decision_subtype": "coach_agent_invocations_stall",
                },
            ]
        )
        generator = ReviewSummaryGenerator(output_dir=tmp_path)
        out = generator.generate(result)
        md = out.output_path.read_text(encoding="utf-8")
        assert "MIXED_PARTIAL_FAILURE" not in md
        assert "FAILED" in md


# ---------------------------------------------------------------------------
# AC-5: md5 signature normalisation is robust to missing_phases ordering
# ---------------------------------------------------------------------------


class TestFeedbackNormalisationRobustness:
    """AC-5: reordered missing_phases must produce identical md5 signatures."""

    def test_reordered_missing_phases_produce_same_signature(self):
        orch = _make_orchestrator()
        turn_a = _turn_from_agent_invocations_violation(1, missing_phases=["4", "5"])
        turn_b = _turn_from_agent_invocations_violation(2, missing_phases=["5", "4"])

        # Bare feedback strings will differ textually
        raw_feedback_a = turn_a.feedback
        raw_feedback_b = turn_b.feedback
        assert raw_feedback_a != raw_feedback_b

        # But normalised-with-turn-record output folds sorted missing_phases
        # into a canonical JSON appendix so md5s collide.
        normalised_a = orch._normalize_feedback_for_stall(raw_feedback_a, turn_a)
        normalised_b = orch._normalize_feedback_for_stall(raw_feedback_b, turn_b)

        sig_a = hashlib.md5(
            normalised_a.strip().lower().encode()
        ).hexdigest()[:8]
        sig_b = hashlib.md5(
            normalised_b.strip().lower().encode()
        ).hexdigest()[:8]
        assert sig_a == sig_b

    def test_canonical_fingerprint_only_for_violation_feedback(self):
        """Non-violation feedback must not get the CANONICAL appendix; this
        preserves TASK-AB-SD01's text-only normalisation."""
        orch = _make_orchestrator()
        turn = _turn_from_generic_coach_rejection(1)
        normalised = orch._normalize_feedback_for_stall(turn.feedback, turn)
        assert "|CANONICAL|" not in normalised

    def test_violation_feedback_gets_canonical_appendix(self):
        orch = _make_orchestrator()
        turn = _turn_from_agent_invocations_violation(1)
        normalised = orch._normalize_feedback_for_stall(turn.feedback, turn)
        assert "|CANONICAL|" in normalised
        # The appendix is valid JSON after the marker
        _prefix, canonical = normalised.split("|CANONICAL|", 1)
        parsed = json.loads(canonical)
        assert parsed["category"] == "agent_invocations_violation"
        assert parsed["missing_phases"] == ["4", "5"]


# ---------------------------------------------------------------------------
# AC-7: Co-fire case — agent_invocations + context_pollution
# ---------------------------------------------------------------------------


class TestCoFireClassification:
    """AC-7.3: co-fire coach_agent_invocations + context_pollution."""

    def test_co_fire_both_labels_in_decision_subtype(self):
        history = [_turn_from_agent_invocations_violation(i) for i in range(1, 4)]
        c = classify_stall(
            history,
            "unrecoverable_stall",
            context_pollution_fired=True,
        )
        assert c is not None
        assert STALL_COACH_AGENT_INVOCATIONS in c.co_fires
        assert STALL_CONTEXT_POLLUTION in c.co_fires
        assert "+" in c.decision_subtype
        assert STALL_COACH_AGENT_INVOCATIONS in c.decision_subtype
        assert STALL_CONTEXT_POLLUTION in c.decision_subtype

    def test_context_pollution_alone_fires(self):
        """Context pollution with no violation trail → only context_pollution."""
        history = [_turn_from_generic_coach_rejection(i) for i in range(1, 4)]
        c = classify_stall(
            history,
            "unrecoverable_stall",
            context_pollution_fired=True,
        )
        assert c is not None
        assert c.decision_label == STALL_CONTEXT_POLLUTION
        assert STALL_COACH_AGENT_INVOCATIONS not in c.co_fires


# ---------------------------------------------------------------------------
# AC-7.4: TASK-FIX-7A02 player_invocation_stall regression check
# ---------------------------------------------------------------------------


class TestPlayerInvocationStallRegression:
    """AC-7.4: existing player_invocation_stall path must still work."""

    def _player_error_turn(self, turn: int) -> TurnRecord:
        result = AgentInvocationResult(
            task_id="TASK-TEST",
            turn=turn,
            agent_type="player",
            success=False,
            report={},
            duration_seconds=0.0,
            error="SDK API error: 500",
        )
        return TurnRecord(
            turn=turn,
            player_result=result,
            coach_result=None,
            decision="error",
            feedback=None,
            timestamp=f"2026-04-24T12:0{turn}:00Z",
        )

    def test_player_invocation_stall_final_decision_returns_none_from_classify(self):
        """classify_stall is only defined for unrecoverable_stall; the
        player_invocation_stall label is a distinct final_decision that
        bypasses classify_stall entirely."""
        history = [self._player_error_turn(i) for i in range(1, 4)]
        assert classify_stall(history, "player_invocation_stall") is None

    def test_player_invocation_detector_still_fires(self):
        """AC-7.4 sanity: the original 7A02 detector is independent."""
        orch = _make_orchestrator()
        history = [self._player_error_turn(i) for i in range(1, 4)]
        assert orch._is_player_invocation_stalled(history) is True


# ---------------------------------------------------------------------------
# AC-9: Jarvis FEAT-J002 replay fixture
# ---------------------------------------------------------------------------


class TestJarvisFeatJ002Replay:
    """AC-9: the preserved jarvis forensic evidence must classify as
    ``coach_agent_invocations_stall`` under the new classifier."""

    FIXTURE_DIR = (
        Path(__file__).parent.parent
        / "fixtures"
        / "jarvis_feat_j002_replay"
    )

    def test_fixture_files_exist(self):
        assert (self.FIXTURE_DIR / "task_work_results.json").exists()
        assert (self.FIXTURE_DIR / "coach_turn_5.json").exists()
        assert (self.FIXTURE_DIR / "coach_turn_6.json").exists()

    def _build_turn_from_fixture(self, coach_fixture: Path, turn: int) -> TurnRecord:
        data = json.loads(coach_fixture.read_text(encoding="utf-8"))
        coach_result = AgentInvocationResult(
            task_id=data["task_id"],
            turn=data["turn"],
            agent_type="coach",
            success=True,
            report={
                "decision": data["decision"],
                "feedback": data["feedback"],
                "issues": data["issues"],
            },
            duration_seconds=0.5,
            error=None,
        )
        return TurnRecord(
            turn=turn,
            player_result=_real_player_result(turn, data["task_id"]),
            coach_result=coach_result,
            decision="feedback",
            feedback=data["feedback"],
            timestamp=f"2026-04-24T13:0{turn}:00Z",
        )

    def test_jarvis_replay_classifies_as_coach_agent_invocations_stall(self):
        # The real jarvis run had 6 turns of this violation. We have 2 fixtures
        # + one duplicate to hit the 3-turn threshold.
        turn_5 = self._build_turn_from_fixture(
            self.FIXTURE_DIR / "coach_turn_5.json", turn=4
        )
        turn_6 = self._build_turn_from_fixture(
            self.FIXTURE_DIR / "coach_turn_6.json", turn=5
        )
        # Synthesise a third consecutive turn (same shape) to hit threshold.
        turn_7 = self._build_turn_from_fixture(
            self.FIXTURE_DIR / "coach_turn_6.json", turn=6
        )
        history = [turn_5, turn_6, turn_7]

        c = classify_stall(history, "unrecoverable_stall")
        assert c is not None
        assert c.decision_label == STALL_COACH_AGENT_INVOCATIONS
        assert c.missing_phases == ["4", "5"]
        assert c.expected_phases == 3
        assert c.actual_invocations == 1


# ---------------------------------------------------------------------------
# TASK-FIX-7A08 AC: forge-run-3 post-prompt-fix replay
# ---------------------------------------------------------------------------


class TestForgeRun3PostFixReplay:
    """TASK-FIX-7A08: when the Player follows the new prompt mandate
    (i.e., invokes Phase 3/4/5 specialists via Task), the fixture reflects
    ``agent_invocations_validation.status == "passed"`` with 3/3 required
    invocations, AND the Coach's agent-invocations gate does NOT reject
    (no ``agent_invocations_violation`` issue is emitted), AND
    ``classify_stall`` over 3 such turns does NOT classify as
    ``coach_agent_invocations_stall``.

    Derived from forge-run-3 (docs/reviews/bdd-acceptance-wired-up/forge-run-3.md)
    turn 1 of TASK-NFI-003 (lines 1084-1111) and TASK-NFI-007 (lines 1178-1205),
    minimised and forward-rolled to post-fix behaviour.
    """

    FIXTURE_DIR = (
        Path(__file__).parent.parent
        / "fixtures"
        / "forge_run_3_replay"
    )

    def test_fixtures_exist(self):
        assert (self.FIXTURE_DIR / "nfi_003_turn_1_post_fix.json").exists()
        assert (self.FIXTURE_DIR / "nfi_007_turn_1_post_fix.json").exists()

    def _load_fixture(self, name: str) -> Dict[str, Any]:
        return json.loads((self.FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_nfi_003_fixture_reports_3_of_3_required_invocations(self):
        """The AC-named invariant: fixture must report 3/3 with status=passed."""
        data = self._load_fixture("nfi_003_turn_1_post_fix.json")
        validation = data["agent_invocations_validation"]
        assert validation["status"] == "passed"
        assert validation["expected_phases"] == 3
        assert validation["actual_invocations"] == 3
        assert validation["missing_phases"] == []

    def test_nfi_007_fixture_reports_3_of_3_required_invocations(self):
        data = self._load_fixture("nfi_007_turn_1_post_fix.json")
        validation = data["agent_invocations_validation"]
        assert validation["status"] == "passed"
        assert validation["expected_phases"] == 3
        assert validation["actual_invocations"] == 3
        assert validation["missing_phases"] == []

    def test_fixtures_name_the_mandated_specialists(self):
        """The Player's agent_invocations must name the specialists that the
        new prompt mandates — anything else would mean the fixture is simulating
        the wrong post-fix state."""
        specialist_names = {
            inv["agent"]
            for fname in (
                "nfi_003_turn_1_post_fix.json",
                "nfi_007_turn_1_post_fix.json",
            )
            for inv in self._load_fixture(fname)["agent_invocations"]
        }
        # Phase-4 and Phase-5 specialists are fixed across stacks.
        assert "test-orchestrator" in specialist_names
        assert "code-reviewer" in specialist_names

    def _build_post_fix_turn(self, fixture_name: str, turn: int) -> TurnRecord:
        """Build a TurnRecord representing a successful post-fix turn —
        Coach approves because the agent-invocations gate passes, so no
        ``agent_invocations_violation`` issue is present."""
        data = self._load_fixture(fixture_name)
        task_id = data["task_id"]
        player_result = AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=True,
            report={
                "files_modified": data["files_modified"],
                "files_created": data["files_created"],
                "tests_passed": data["tests_passed"],
                "test_count": data["quality_gates"]["tests_pass"]["total"],
                "implementation_notes": data["implementation_notes"],
                # The validator's verdict the Player persisted to disk:
                "agent_invocations_validation": data["agent_invocations_validation"],
            },
            duration_seconds=12.0,
            error=None,
        )
        coach_result = AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="coach",
            success=True,
            report={
                "decision": "approved",
                "feedback": "All quality gates passed.",
                "issues": [],  # no violation → the classifier must stay quiet
            },
            duration_seconds=0.4,
            error=None,
        )
        return TurnRecord(
            turn=turn,
            player_result=player_result,
            coach_result=coach_result,
            decision="approved",
            feedback="All quality gates passed.",
            timestamp=f"2026-04-24T19:0{turn}:00Z",
        )

    def test_post_fix_turn_has_no_agent_invocations_violation(self):
        """``_extract_agent_invocations_violation`` must return None for a
        turn built from the post-fix fixture (no violation issue emitted)."""
        turn = self._build_post_fix_turn("nfi_003_turn_1_post_fix.json", turn=1)
        assert _extract_agent_invocations_violation(turn) is None

    def test_classify_stall_quiet_over_three_post_fix_turns(self):
        """Three consecutive post-fix turns — each with passed validation and
        Coach approval — must NOT classify as coach_agent_invocations_stall.
        If this assertion ever flips, the prompt fix has regressed or the
        classifier has drifted."""
        history = [
            self._build_post_fix_turn("nfi_003_turn_1_post_fix.json", turn=1),
            self._build_post_fix_turn("nfi_007_turn_1_post_fix.json", turn=2),
            self._build_post_fix_turn("nfi_003_turn_1_post_fix.json", turn=3),
        ]
        c = classify_stall(history, "unrecoverable_stall")
        # Either no classification at all, or a non-coach-agent-invocations
        # classification. The specific invariant is: the agent-invocations
        # branch must not fire.
        if c is not None:
            assert c.decision_label != STALL_COACH_AGENT_INVOCATIONS, (
                "After the TASK-FIX-7A08 prompt change, three turns with "
                "passed agent_invocations_validation should NOT trigger the "
                "coach_agent_invocations_stall classification."
            )
            assert STALL_COACH_AGENT_INVOCATIONS not in c.co_fires
