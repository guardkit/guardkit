"""Required behavioural-oracle fail-closed integration controls."""

from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.feature_loader import BehaviouralOracle
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.worktrees.manager import Worktree


def _write_checker(path: Path, payload: Dict[str, Any], *, exit_code: int = 0,
                   mutate: str | None = None) -> None:
    mutation = ""
    if mutate is not None:
        mutation = (
            "candidate = Path(os.environ['GUARDKIT_CANDIDATE_ROOT'])\n"
            f"(candidate / {mutate!r}).write_text('changed')\n"
        )
    path.write_text(
        "from pathlib import Path\n"
        "import json, os\n"
        + mutation
        + "receipt = Path(os.environ['GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT'])\n"
        + f"receipt.write_text(json.dumps({payload!r}))\n"
        + f"raise SystemExit({exit_code})\n"
    )


def _required_task(worktree: Path, checker: Path, *, expected_checks: int = 1,
                   command: str | None = None) -> Dict[str, Any]:
    return {
        "behavioural_oracle": {
            "command": command or f"{sys.executable} -B {checker}",
            "expected_exit": 0,
            "timeout": 20,
            "required": True,
            "expected_checks": expected_checks,
            "checker_path": str(checker),
            "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
            "source_paths": ["source.txt"],
        }
    }


def _fixture(tmp_path: Path, payload: Dict[str, Any] | None = None,
             *, exit_code: int = 0, mutate: str | None = None):
    worktree = tmp_path / "candidate"
    worktree.mkdir()
    (worktree / "source.txt").write_text("stable")
    checker = tmp_path / "checker.py"
    _write_checker(
        checker,
        payload or {"run": 1, "failures": 0, "errors": 0, "skipped": 0},
        exit_code=exit_code,
        mutate=mutate,
    )
    task = _required_task(worktree, checker)
    validator = CoachValidator(worktree_path=worktree, task_id="TASK-REQ", turn=2)
    return worktree, checker, task, validator


def _bundle(oracle: Any) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(verified=True),
        gathering_status="complete",
        behavioural_oracle=oracle,
    )


def _apply_guard(tmp_path: Path, declaration: Dict[str, Any], oracle: Any):
    invoker = AgentInvoker.__new__(AgentInvoker)
    decision = {"decision": "approve", "rationale": "model approved", "issues": []}
    output = tmp_path / "coach_turn_1.json"
    output.write_text(json.dumps(decision))
    invoker._apply_behavioural_oracle_guard(
        decision=decision,
        evidence_bundle=_bundle(oracle) if oracle is not None else None,
        behavioural_oracle_declaration=declaration,
        task_id="TASK-REQ",
        turn=1,
        coach_output_path=output,
    )
    return decision, json.loads(output.read_text())


class TestRequiredSchema:
    def test_defaults_remain_optional(self) -> None:
        model = BehaviouralOracle(command="true")
        assert model.required is False
        assert model.expected_checks is None

    @pytest.mark.parametrize(
        "override",
        [
            {},
            {"expected_checks": True},
            {"expected_checks": 0},
            {"expected_checks": 1, "checker_path": "x", "checker_sha256": "A" * 64,
             "source_paths": ["source.txt"]},
            {"expected_checks": 1, "checker_path": "x", "checker_sha256": "a" * 64,
             "source_paths": []},
            {"expected_checks": 1, "checker_path": "x", "checker_sha256": "a" * 64,
             "source_paths": ["source.txt", "source.txt"]},
        ],
    )
    def test_invalid_required_declarations_fail_validation(self, override) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle.model_validate(
                {"command": "true", "required": True, **override}
            )

    def test_actual_model_preserves_all_fields_and_copies_sources(self) -> None:
        sources = ["source.txt"]
        model = BehaviouralOracle(
            command="true", expected_exit=3, timeout=9, required=True,
            expected_checks=1, checker_path="checker.py",
            checker_sha256="a" * 64, source_paths=sources,
        )
        declaration = CoachValidator._oracle_declaration(
            {"behavioural_oracle": model}
        )
        assert declaration == model.model_dump(exclude_none=True)
        assert declaration["source_paths"] is not sources


class TestRequiredProducer:
    def test_complete_green_shape_and_real_guard(self, tmp_path: Path) -> None:
        _, _, task, validator = _fixture(tmp_path)
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=2
        )
        assert result is not None and result["passed"] is True
        assert result["expected_exit"] == result["exit_code"] == 0
        assert result["receipt_validation"] == {
            "valid": True,
            "fresh": True,
            "confined": True,
            "regular_file": True,
            "path": result["receipt_validation"]["path"],
        }
        assert result["receipt"]["run"] == 1
        assert result["checker_identity"]["before"] == result["checker_identity"]["after"]
        assert result["source_identities"][0]["before"] == result["source_identities"][0]["after"]
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], result
        )
        assert decision["decision"] == persisted["decision"] == "approve"

    def test_required_command_beats_discovered_roundtrip(self, tmp_path: Path) -> None:
        worktree, checker, task, validator = _fixture(
            tmp_path,
            {"run": 1, "failures": 1, "errors": 0, "skipped": 0},
            exit_code=1,
        )
        roundtrip = worktree / "tests" / "acceptance" / "x_roundtrip.py"
        roundtrip.parent.mkdir(parents=True)
        roundtrip.write_text("def test_pass(): assert True\n")
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["command"] == f"{sys.executable} -B {checker}"
        assert result["receipt"]["failures"] == 1
        assert result["passed"] is False

    def test_source_mutation_is_detected_even_with_green_receipt(self, tmp_path: Path) -> None:
        _, _, task, validator = _fixture(tmp_path, mutate="source.txt")
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["passed"] is False
        assert result["reason"] == "identity_changed"

    def test_checker_digest_mismatch_refuses_before_execution(self, tmp_path: Path) -> None:
        _, _, task, validator = _fixture(tmp_path)
        task["behavioural_oracle"]["checker_sha256"] = "0" * 64
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["reason"] == "checker_digest_mismatch"
        assert result["status"] == "not_run"

    @pytest.mark.parametrize(
        ("payload", "reason"),
        [
            ({"run": 0, "failures": 0, "errors": 0, "skipped": 0}, "zero_checks"),
            ({"run": 2, "failures": 0, "errors": 0, "skipped": 0}, "wrong_check_count"),
            ({"run": 1, "failures": 0, "errors": 0}, "receipt_invalid"),
            ({"run": True, "failures": 0, "errors": 0, "skipped": 0}, "receipt_invalid"),
        ],
    )
    def test_receipt_failures_are_explicit(self, tmp_path: Path, payload, reason) -> None:
        _, _, task, validator = _fixture(tmp_path, payload)
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None and result["reason"] == reason
        assert result["passed"] is False

    def test_fifo_receipt_is_refused_without_blocking(self, tmp_path: Path) -> None:
        worktree, checker, task, validator = _fixture(tmp_path)
        checker.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "os.mkfifo(Path(os.environ['GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT']))\n"
        )
        task["behavioural_oracle"]["checker_sha256"] = hashlib.sha256(
            checker.read_bytes()
        ).hexdigest()
        started = __import__("time").monotonic()
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        elapsed = __import__("time").monotonic() - started
        assert elapsed < 5
        assert result is not None and result["reason"] == "receipt_unsafe"
        assert result["passed"] is False

    def test_preexisting_attempt_directory_preserves_sentinel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree, _, task, validator = _fixture(tmp_path)
        private = TaskArtifactPaths.task_private_dir("TASK-REQ", worktree)
        attempt = private / "behavioural-oracle-turn-1-fixed"
        attempt.mkdir(parents=True)
        sentinel = attempt / "sentinel"
        sentinel.write_text("keep")
        monkeypatch.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator.secrets.token_hex",
            lambda _: "fixed",
        )
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None and result["reason"] == "receipt_unsafe"
        assert sentinel.read_text() == "keep"


class TestRequiredGuard:
    @pytest.mark.parametrize(
        "mutation",
        [
            "absent",
            "bare_true",
            "wrong_command",
            "missing_receipt",
            "boolean_count",
            "missing_checker",
            "missing_sources",
            "timed_out",
        ],
    )
    def test_incomplete_or_contradictory_evidence_persists_feedback(
        self, tmp_path: Path, mutation: str
    ) -> None:
        _, _, task, validator = _fixture(tmp_path)
        green = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert green is not None
        if mutation == "absent":
            oracle = None
        elif mutation == "bare_true":
            oracle = {"passed": True}
        else:
            oracle = deepcopy(green)
            if mutation == "wrong_command":
                oracle["command"] = "different"
            elif mutation == "missing_receipt":
                oracle.pop("receipt")
            elif mutation == "boolean_count":
                oracle["receipt"]["run"] = True
            elif mutation == "missing_checker":
                oracle.pop("checker_identity")
            elif mutation == "missing_sources":
                oracle["source_identities"] = []
            elif mutation == "timed_out":
                oracle["timed_out"] = True
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], oracle
        )
        assert decision["decision"] == persisted["decision"] == "feedback"
        issues = [i for i in persisted["issues"] if i["category"] == "behavioural_oracle_failure"]
        assert len(issues) == 1

    def test_evidence_required_flag_cannot_enable_guard(self, tmp_path: Path) -> None:
        decision, persisted = _apply_guard(
            tmp_path,
            {"command": "true", "required": False},
            {"required": True, "passed": True},
        )
        assert decision["decision"] == persisted["decision"] == "approve"


class TestRequiredActualInvoker:
    @pytest.mark.parametrize("oracle", [None, [], {"passed": True}, {"passed": True, "output_tail": [1]}])
    def test_actual_invoker_rejects_missing_or_malformed_leg(
        self, tmp_path: Path, oracle: Any
    ) -> None:
        invoker = AgentInvoker.__new__(AgentInvoker)
        invoker.worktree_path = tmp_path
        invoker.sdk_timeout_seconds = 600
        invoker._calculate_sdk_timeout = MagicMock(return_value=600)
        invoker._venv_python = None
        verdict = {
            "task_id": "TASK-REQ",
            "turn": 1,
            "decision": "approve",
            "rationale": "model approved",
            "criteria_verification": [],
        }
        events = [
            AssistantMessageEvent(
                text="```json\n" + json.dumps(verdict) + "\n```"
            ),
            ResultMessageEvent(session_id=None),
        ]
        with patch.object(
            invoker, "_invoke_with_role", AsyncMock(return_value=(None, events))
        ):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-REQ",
                    turn=1,
                    requirements="req",
                    player_report={"files_modified": [], "tests_passed": True},
                    evidence_bundle=_bundle(oracle),
                    behavioural_oracle_declaration=_dispatch_declaration(),
                )
            )
        assert result.report["decision"] == "feedback"
        issue = next(
            item for item in result.report["issues"]
            if item["category"] == "behavioural_oracle_failure"
        )
        assert issue["severity"] == "must_fix"
        path = TaskArtifactPaths.private_artifact_path(
            "TASK-REQ", "coach_turn_1.json", tmp_path
        )
        assert json.loads(path.read_text())["decision"] == "feedback"


def _make_orchestrator(tmp_path: Path, invoker: Any) -> tuple[AutoBuildOrchestrator, Worktree]:
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    worktree = Worktree("TASK-REQ", "branch", worktree_path, "main")
    orchestrator = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=2,
        worktree_manager=MagicMock(),
        agent_invoker=invoker,
        progress_display=MagicMock(),
        enable_context=False,
    )
    return orchestrator, worktree


def _dispatch_declaration() -> Dict[str, Any]:
    return {
        "command": "true", "expected_exit": 0, "timeout": 20,
        "required": True, "expected_checks": 1,
        "checker_path": "/tmp/checker", "checker_sha256": "a" * 64,
        "source_paths": ["source.txt"],
    }


class TestRequiredPrimaryDispatch:
    @pytest.mark.parametrize("bundle", [None, {}])
    def test_missing_or_wrong_bundle_persists_before_coach(
        self, tmp_path: Path, bundle: Any
    ) -> None:
        invoker = MagicMock()
        invoker.invoke_coach = AsyncMock()
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        validator = MagicMock()
        validator.gather_evidence.return_value = bundle
        with patch("guardkit.orchestrator.autobuild.CoachValidator", return_value=validator):
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-REQ", turn=1, requirements="req",
                player_report={"files_modified": []}, worktree=worktree,
                behavioural_oracle=_dispatch_declaration(),
            )
        assert result.report["decision"] == "feedback"
        assert invoker.invoke_coach.call_count == 0
        decision_path = TaskArtifactPaths.private_artifact_path(
            "TASK-REQ", "coach_turn_1.json", worktree.path
        )
        assert json.loads(decision_path.read_text())["issues"][0]["category"] == "behavioural_oracle_failure"

    def test_old_signature_refuses_required_declaration(self, tmp_path: Path) -> None:
        invoker = MagicMock()
        invoker.invoke_coach = AsyncMock()
        invoker.invoke_coach.__signature__ = inspect.Signature(
            [inspect.Parameter("task_id", inspect.Parameter.KEYWORD_ONLY)]
        )
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        validator = MagicMock()
        validator.gather_evidence.return_value = _bundle({"passed": False})
        with patch("guardkit.orchestrator.autobuild.CoachValidator", return_value=validator):
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-REQ", turn=1, requirements="req",
                player_report={"files_modified": []}, worktree=worktree,
                behavioural_oracle=_dispatch_declaration(),
            )
        assert result.report["decision"] == "feedback"
        assert "required_behavioural_oracle_unsupported" in result.report["rationale"]
        assert invoker.invoke_coach.call_count == 0

    def test_supported_signature_receives_exact_declaration(self, tmp_path: Path) -> None:
        invoker = MagicMock()
        invoker.invoke_coach = AsyncMock(
            return_value=AgentInvocationResult(
                task_id="TASK-REQ", turn=1, agent_type="coach", success=True,
                report={"decision": "approve"}, duration_seconds=0,
            )
        )
        real = inspect.signature(AgentInvoker.invoke_coach)
        invoker.invoke_coach.__signature__ = real.replace(
            parameters=[p for p in real.parameters.values() if p.name != "self"]
        )
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        validator = MagicMock()
        validator.gather_evidence.return_value = _bundle({"passed": False})
        declaration = _dispatch_declaration()
        with patch("guardkit.orchestrator.autobuild.CoachValidator", return_value=validator), \
             patch.object(orchestrator, "_produce_spec_conformance_leg", return_value=None), \
             patch.object(orchestrator, "_evidence_repo_gate", return_value=None), \
             patch.object(orchestrator, "_direct_mode_evidence_gate", return_value=None):
            orchestrator._invoke_coach_safely(
                task_id="TASK-REQ", turn=1, requirements="req",
                player_report={"files_modified": []}, worktree=worktree,
                behavioural_oracle=declaration,
            )
        assert invoker.invoke_coach.call_args.kwargs["behavioural_oracle_declaration"] == declaration


class TestFrozenRejectedCandidate:
    def test_combined20_real_producer_and_guard(self, tmp_path: Path) -> None:
        import os

        raw_root = os.environ.get("GUARDKIT_REJECTED_97AD785_ROOT")
        raw_checker = os.environ.get("GUARDKIT_COMBINED20_CHECKER")
        if not raw_root or not raw_checker:
            pytest.skip("frozen rejected-candidate fixture not supplied")
        root = Path(raw_root)
        checker = Path(raw_checker)
        expected_sources = {
            "src/career_assistant/queue.py": "f0abaca5ac2489ec41b4e1560d732b3128ef60ea671d0ede78cd5963cafbd729",
            "tests/test_queue.py": "1551f5badfafbda31430e5f2bc254c06085562bafbe80340916a652feae14b1b",
            "README.md": "3cf297ca846d56ebbe5d307125ced20be728b11d49be7185f69218ab6087a3ae",
        }
        before = {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in expected_sources
        }
        assert before == expected_sources
        checker_digest = hashlib.sha256(checker.read_bytes()).hexdigest()
        assert checker_digest == "ecee4a383d3396a043b72454d175fe0e22df98a761f066eb4e0840ff24b408d5"
        declaration = {
            "command": f"{sys.executable} -B {checker}",
            "expected_exit": 0,
            "timeout": 120,
            "required": True,
            "expected_checks": 20,
            "checker_path": str(checker),
            "checker_sha256": checker_digest,
            "source_paths": list(expected_sources),
        }
        validator = CoachValidator(root, task_id="TASK-CA71-201", turn=1)
        result = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": declaration},
            task_id="TASK-CA71-201",
            turn=1,
        )
        assert result is not None
        assert result["passed"] is False
        assert result["receipt"]["run"] == 20
        assert result["receipt"]["failures"] == 6
        assert result["receipt"]["errors"] == result["receipt"]["skipped"] == 0
        decision, persisted = _apply_guard(tmp_path, declaration, result)
        assert decision["decision"] == persisted["decision"] == "feedback"
        assert persisted["issues"][0]["details"]["receipt"]["failures"] == 6
        after = {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in expected_sources
        }
        assert after == before
        result_path = os.environ.get("GUARDKIT_REQUIRED_NEGATIVE_RESULT")
        if result_path:
            Path(result_path).write_text(
                json.dumps({"producer": result, "decision": persisted}, indent=2)
            )


class TestRequiredLegacyDispatch:
    def test_required_declaration_refuses_legacy_before_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        invoker = MagicMock()
        invoker.invoke_coach = AsyncMock()
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        validator = MagicMock()
        with patch("guardkit.orchestrator.autobuild.CoachValidator", return_value=validator):
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-REQ", turn=1, requirements="req",
                player_report={"files_modified": []}, worktree=worktree,
                behavioural_oracle=_dispatch_declaration(),
            )
        assert result.report["decision"] == "feedback"
        assert validator.validate.call_count == 0
        assert invoker.invoke_coach.call_count == 0


class TestRequiredFrozenDesignControls:
    def test_operator_supplied_receipt_path_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BehaviouralOracle.model_validate(
                {
                    "command": "true",
                    "required": True,
                    "expected_checks": 1,
                    "checker_path": "checker.py",
                    "checker_sha256": "a" * 64,
                    "source_paths": ["source.txt"],
                    "receipt_path": "/tmp/attacker-selected",
                }
            )

    def test_actual_model_runs_through_real_producer_and_guard(
        self, tmp_path: Path
    ) -> None:
        _, _, task, validator = _fixture(tmp_path)
        model = BehaviouralOracle.model_validate(task["behavioural_oracle"])
        result = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": model},
            task_id="TASK-REQ",
            turn=2,
        )
        declaration = model.model_dump(exclude_none=True)
        assert result is not None and result["passed"] is True
        decision, persisted = _apply_guard(tmp_path, declaration, result)
        assert decision["decision"] == persisted["decision"] == "approve"

    @pytest.mark.parametrize("declared_path", ["/tmp/outside", "../outside"])
    def test_source_escape_is_rejected(
        self, tmp_path: Path, declared_path: str
    ) -> None:
        _, _, task, validator = _fixture(tmp_path)
        task["behavioural_oracle"]["source_paths"] = [declared_path]
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["reason"] == "source_binding_invalid"
        assert result["status"] == "not_run"

    def test_source_symlink_is_rejected(self, tmp_path: Path) -> None:
        worktree, _, task, validator = _fixture(tmp_path)
        target = tmp_path / "outside-source"
        target.write_text("stable")
        (worktree / "source.txt").unlink()
        (worktree / "source.txt").symlink_to(target)
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["reason"] == "source_binding_invalid"
        assert target.read_text() == "stable"

    def test_checker_mutation_after_initial_read_is_detected(
        self, tmp_path: Path
    ) -> None:
        _, checker, task, validator = _fixture(tmp_path)
        checker.write_text(
            "from pathlib import Path\n"
            "import json, os\n"
            "Path(__file__).write_text(Path(__file__).read_text() + '# changed\\n')\n"
            "receipt = Path(os.environ['GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT'])\n"
            "receipt.write_text(json.dumps("
            "{'run': 1, 'failures': 0, 'errors': 0, 'skipped': 0}))\n"
        )
        task["behavioural_oracle"]["checker_sha256"] = hashlib.sha256(
            checker.read_bytes()
        ).hexdigest()
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None
        assert result["reason"] == "identity_changed"

    def test_subprocess_start_failure_is_explicit_and_guarded(
        self, tmp_path: Path
    ) -> None:
        _, _, task, validator = _fixture(tmp_path)
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
            side_effect=OSError("cannot start"),
        ):
            result = validator._produce_behavioural_oracle(
                authored_files=[], task=task, task_id="TASK-REQ", turn=1
            )
        assert result is not None and result["reason"] == "failed_to_start"
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], result
        )
        assert decision["decision"] == persisted["decision"] == "feedback"

    def test_timeout_is_explicit_and_guarded(self, tmp_path: Path) -> None:
        import subprocess

        _, _, task, validator = _fixture(tmp_path)
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                "checker", 1, output="partial"
            ),
        ):
            result = validator._produce_behavioural_oracle(
                authored_files=[], task=task, task_id="TASK-REQ", turn=1
            )
        assert result is not None and result["reason"] == "timed_out"
        assert result["status"] == "ran" and result["timed_out"] is True
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], result
        )
        assert decision["decision"] == persisted["decision"] == "feedback"

    def test_missing_shell_runner_never_returns_none(self, tmp_path: Path) -> None:
        _, _, task, validator = _fixture(tmp_path)
        task["behavioural_oracle"]["command"] = (
            "/definitely/missing/required-oracle-runner"
        )
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None and result["passed"] is False
        assert result["reason"] in {"command_failed", "receipt_missing"}
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], result
        )
        assert decision["decision"] == persisted["decision"] == "feedback"

    def test_receipt_symlink_is_refused_without_modifying_target(
        self, tmp_path: Path
    ) -> None:
        _, checker, task, validator = _fixture(tmp_path)
        target = tmp_path / "sentinel-target"
        target.write_text("keep")
        checker.write_text(
            "from pathlib import Path\n"
            "import os\n"
            "Path(os.environ['GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT']).symlink_to("
            f"{str(target)!r})\n"
        )
        task["behavioural_oracle"]["checker_sha256"] = hashlib.sha256(
            checker.read_bytes()
        ).hexdigest()
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None and result["reason"] == "receipt_unsafe"
        assert target.read_text() == "keep"

    def test_private_root_symlink_is_refused_without_modifying_target(
        self, tmp_path: Path
    ) -> None:
        worktree, _, task, validator = _fixture(tmp_path)
        target = tmp_path / "sentinel-directory"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_text("keep")
        (worktree / ".guardkit").symlink_to(target, target_is_directory=True)
        result = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert result is not None and result["reason"] == "receipt_unsafe"
        assert sentinel.read_text() == "keep"


class TestRequiredStrictGuardControls:
    @pytest.mark.parametrize(
        "mutation",
        [
            "not_ran",
            "passed_false",
            "wrong_expected_exit",
            "string_count",
            "float_count",
            "wrong_checker_digest",
            "boolean_checker_device",
            "string_source_inode",
        ],
    )
    def test_strict_malformed_values_persist_feedback(
        self, tmp_path: Path, mutation: str
    ) -> None:
        _, _, task, validator = _fixture(tmp_path)
        oracle = validator._produce_behavioural_oracle(
            authored_files=[], task=task, task_id="TASK-REQ", turn=1
        )
        assert oracle is not None and oracle["passed"] is True
        oracle = deepcopy(oracle)
        if mutation == "not_ran":
            oracle["status"] = "not_run"
        elif mutation == "passed_false":
            oracle["passed"] = False
        elif mutation == "wrong_expected_exit":
            oracle["expected_exit"] = 1
        elif mutation == "string_count":
            oracle["receipt"]["run"] = "1"
        elif mutation == "float_count":
            oracle["receipt"]["run"] = 1.0
        elif mutation == "wrong_checker_digest":
            oracle["checker_identity"]["expected_sha256"] = "b" * 64
        elif mutation == "boolean_checker_device":
            oracle["checker_identity"]["before"]["device"] = True
        elif mutation == "string_source_inode":
            oracle["source_identities"][0]["after"]["inode"] = "1"
        decision, persisted = _apply_guard(
            tmp_path, task["behavioural_oracle"], oracle
        )
        assert decision["decision"] == persisted["decision"] == "feedback"
        issues = [
            item
            for item in persisted["issues"]
            if item["category"] == "behavioural_oracle_failure"
        ]
        assert len(issues) == 1

    def test_evidence_required_flag_cannot_disable_guard(
        self, tmp_path: Path
    ) -> None:
        declaration = _dispatch_declaration()
        oracle = {"required": False, "passed": True}
        decision, persisted = _apply_guard(tmp_path, declaration, oracle)
        assert decision["decision"] == persisted["decision"] == "feedback"


class TestFrozenHistoricalCandidate:
    def test_historical13_real_producer_and_guard(self, tmp_path: Path) -> None:
        import os

        raw_root = os.environ.get("GUARDKIT_REJECTED_3A9A06F_ROOT")
        raw_checker = os.environ.get("GUARDKIT_HISTORICAL13_CHECKER")
        if not raw_root or not raw_checker:
            pytest.skip("frozen historical candidate fixture not supplied")
        root = Path(raw_root)
        checker = Path(raw_checker)
        expected_sources = {
            "src/career_assistant/queue.py":
                "18cae1e27cc9d2e8b1ab4698f54d4eb34c1155bc12d4fedabdb433a816f42c76",
            "tests/test_queue.py":
                "1551f5badfafbda31430e5f2bc254c06085562bafbe80340916a652feae14b1b",
            "README.md":
                "3cf297ca846d56ebbe5d307125ced20be728b11d49be7185f69218ab6087a3ae",
        }
        before = {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in expected_sources
        }
        assert before == expected_sources
        checker_digest = hashlib.sha256(checker.read_bytes()).hexdigest()
        assert checker_digest == (
            "4c6f6e5c07933a25431cf3ae3abad60d256e1d36f7fe34536f04deabac6a9c2d"
        )
        declaration = {
            "command": f"{sys.executable} -B {checker}",
            "expected_exit": 0,
            "timeout": 120,
            "required": True,
            "expected_checks": 13,
            "checker_path": str(checker),
            "checker_sha256": checker_digest,
            "source_paths": list(expected_sources),
        }
        validator = CoachValidator(root, task_id="TASK-CA71-201-HIST", turn=1)
        result = validator._produce_behavioural_oracle(
            authored_files=[],
            task={"behavioural_oracle": declaration},
            task_id="TASK-CA71-201-HIST",
            turn=1,
        )
        assert result is not None and result["passed"] is False
        assert result["receipt"]["run"] == 13
        assert result["receipt"]["failures"] == 10
        assert result["receipt"]["errors"] == result["receipt"]["skipped"] == 0
        decision, persisted = _apply_guard(tmp_path, declaration, result)
        assert decision["decision"] == persisted["decision"] == "feedback"
        assert persisted["issues"][0]["details"]["receipt"]["failures"] == 10
        after = {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in expected_sources
        }
        assert after == before
        result_path = os.environ.get("GUARDKIT_HISTORICAL13_RESULT")
        if result_path:
            Path(result_path).write_text(
                json.dumps({"producer": result, "decision": persisted}, indent=2)
            )


class TestRequiredPrimaryCompatibilityControls:
    def test_uninspectable_signature_refuses_required_declaration(
        self, tmp_path: Path
    ) -> None:
        class Uninspectable:
            __signature__ = 1

            def __init__(self) -> None:
                self.called = False

            async def __call__(self, **kwargs):
                self.called = True
                raise AssertionError("unsupported invoker must not run")

        invoker = MagicMock()
        uninspectable = Uninspectable()
        invoker.invoke_coach = uninspectable
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        validator = MagicMock()
        validator.gather_evidence.return_value = _bundle({"passed": False})
        with (
            patch(
                "guardkit.orchestrator.autobuild.CoachValidator",
                return_value=validator,
            ),
            patch.object(
                orchestrator, "_produce_spec_conformance_leg", return_value=None
            ),
            patch.object(orchestrator, "_evidence_repo_gate", return_value=None),
            patch.object(
                orchestrator, "_direct_mode_evidence_gate", return_value=None
            ),
        ):
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-REQ",
                turn=1,
                requirements="req",
                player_report={"files_modified": []},
                worktree=worktree,
                behavioural_oracle=_dispatch_declaration(),
            )
        assert result.report["decision"] == "feedback"
        assert "required_behavioural_oracle_unsupported" in result.report["rationale"]
        assert uninspectable.called is False

    def test_event_loop_fallback_reuses_exact_required_declaration(
        self, tmp_path: Path
    ) -> None:
        expected_result = AgentInvocationResult(
            task_id="TASK-REQ",
            turn=1,
            agent_type="coach",
            success=True,
            report={"decision": "approve"},
            duration_seconds=0,
        )
        invoker = MagicMock()
        invoker.invoke_coach = AsyncMock(return_value=expected_result)
        real = inspect.signature(AgentInvoker.invoke_coach)
        invoker.invoke_coach.__signature__ = real.replace(
            parameters=[
                parameter
                for parameter in real.parameters.values()
                if parameter.name != "self"
            ]
        )
        orchestrator, worktree = _make_orchestrator(tmp_path, invoker)
        validator = MagicMock()
        validator.gather_evidence.return_value = _bundle({"passed": False})
        declaration = _dispatch_declaration()

        def reject_running_loop(coroutine):
            coroutine.close()
            raise RuntimeError("asyncio.run() cannot be called from a running event loop")

        loop = MagicMock()

        def finish(coroutine):
            coroutine.close()
            return expected_result

        loop.run_until_complete.side_effect = finish
        with (
            patch(
                "guardkit.orchestrator.autobuild.CoachValidator",
                return_value=validator,
            ),
            patch.object(
                orchestrator, "_produce_spec_conformance_leg", return_value=None
            ),
            patch.object(orchestrator, "_evidence_repo_gate", return_value=None),
            patch.object(
                orchestrator, "_direct_mode_evidence_gate", return_value=None
            ),
            patch("asyncio.run", side_effect=reject_running_loop),
            patch("asyncio.get_event_loop", return_value=loop),
        ):
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-REQ",
                turn=1,
                requirements="req",
                player_report={"files_modified": []},
                worktree=worktree,
                behavioural_oracle=declaration,
            )
        assert result is expected_result
        assert invoker.invoke_coach.call_count == 2
        for call in invoker.invoke_coach.call_args_list:
            assert call.kwargs["behavioural_oracle_declaration"] == declaration
