"""TASK-ABFIX-012 — TESTING test-gate gated on a widened substrate-vs-code classifier.

Reproduces the FEAT-FMDR-004 second finding (the mirror of ABFIX-010's main bug):
a TESTING-type task — whose deliverable IS a passing test — was false-APPROVED on
turn 1 while its own deterministic run was 5/9 red, because the test gate was
``required=False`` and the LLM Coach reasoned the real code bugs away as
"a substrate failure … evidence is ABSENT, not failed".

The fix has two halves that must not be reversed (constraint 5 of the task):

* a real CODE bug → deterministic block (``_apply_independent_test_code_failure_guard``);
* a host-SUBSTRATE gap → ``signal_absent`` → the existing absent guard → feedback
  bounded by ``max_turns`` (the false-red ABFIX-010 prevents), NEVER a code block
  and NEVER a pass.

Instances of ``.claude/rules/absence-of-failure-is-not-success.md`` and
``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.

Coverage Target: >=90%
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    IndependentTestClassification,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


@pytest.fixture(autouse=True)
def _pin_sdk_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-007 / multi-machine CI: pin the SDK harness for harness-adjacent tests."""
    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")


# ============================================================================
# Test fixtures (real exception-token output vs substrate vs contention shapes)
# ============================================================================

# A real own-code bug (the FMDR-004 shape: wrong method name + bad assertion).
_CODE_ASSERT = (
    "FAILED tests/test_runbook.py::test_status\n"
    "E   AttributeError: 'RunbookStore' object has no attribute 'get_runbook_by_id'\n"
    "FAILED tests/test_runbook.py::test_complete\n"
    "E   AssertionError: assert 'pending' == 'complete'\n"
    "5 failed, 4 passed in 0.42s"
)

# A host-substrate gap: the test needs a tool that is missing on the host.
_SUBSTRATE = "/bin/sh: 1: psql: command not found\n1 failed in 0.05s"

# A non-token failure that LOOKS like it could be transient parallel contention
# (no clean Python exception token in the summary).
_NONTOKEN = (
    "FAILED tests/test_x.py::test_widget\n"
    "E   ValueError: bad widget config\n"
    "1 failed in 0.10s"
)

# A genuine code failure whose message happens to contain "not found" — must NOT
# be mis-routed to substrate (the tightened anchoring).
_KEY_NOT_FOUND = (
    "FAILED tests/test_x.py::test_lookup\n"
    "E   KeyError: 'key: not found'\n"
    "1 failed in 0.10s"
)


def _validator(tmp_path: Path, wave_size: int = 1) -> CoachValidator:
    return CoachValidator(str(tmp_path), task_id="TASK-FMDR-004", wave_size=wave_size)


# ============================================================================
# 1. _is_host_substrate_gap (the shared helper)
# ============================================================================


class TestIsHostSubstrateGap:
    def test_returncode_127_is_substrate(self, tmp_path: Path) -> None:
        assert _validator(tmp_path)._is_host_substrate_gap(127, "anything") is True

    def test_returncode_126_is_substrate(self, tmp_path: Path) -> None:
        assert _validator(tmp_path)._is_host_substrate_gap(126, "anything") is True

    def test_command_not_found_string_is_substrate(self, tmp_path: Path) -> None:
        assert _validator(tmp_path)._is_host_substrate_gap(1, "psql: command not found") is True

    def test_windows_not_recognized_is_substrate(self, tmp_path: Path) -> None:
        out = "'dotnet' is not recognized as an internal or external command"
        assert _validator(tmp_path)._is_host_substrate_gap(1, out) is True

    def test_key_not_found_is_NOT_substrate(self, tmp_path: Path) -> None:
        # The over-broad ": not found" idiom was deliberately excluded so a real
        # code failure mentioning "not found" is never mis-routed to substrate.
        assert _validator(tmp_path)._is_host_substrate_gap(1, "KeyError: 'key: not found'") is False

    def test_file_not_found_assertion_is_NOT_substrate(self, tmp_path: Path) -> None:
        out = "E   FileNotFoundError: [Errno 2] No such file or directory: '/data/x.txt'"
        assert _validator(tmp_path)._is_host_substrate_gap(1, out) is False


# ============================================================================
# 2. _classify_test_failure widening + TESTING own-code override
# ============================================================================


class TestClassifierWidening:
    def test_substrate_is_infrastructure_high_single_wave(self, tmp_path: Path) -> None:
        assert _validator(tmp_path, 1)._classify_test_failure(_SUBSTRATE) == (
            "infrastructure", "high",
        )

    def test_substrate_is_infrastructure_high_parallel_wave(self, tmp_path: Path) -> None:
        # Checked BEFORE the is_parallel reclassification → never amnestied as
        # parallel_contention, never a code block.
        assert _validator(tmp_path, 3)._classify_test_failure(_SUBSTRATE) == (
            "infrastructure", "high",
        )

    def test_testing_assertion_is_code_high_single_wave(self, tmp_path: Path) -> None:
        assert _validator(tmp_path, 1)._classify_test_failure(
            _CODE_ASSERT, task_type="testing"
        ) == ("code", "high")

    def test_testing_assertion_is_code_high_parallel_wave(self, tmp_path: Path) -> None:
        # The wave_size-swing neutralisation: a real assertion failure stays
        # ("code", "high") in a parallel wave, NOT amnestied to parallel_contention.
        assert _validator(tmp_path, 3)._classify_test_failure(
            _CODE_ASSERT, task_type="testing"
        ) == ("code", "high")

    def test_feature_assertion_parallel_stays_contention(self, tmp_path: Path) -> None:
        # Scope: only TESTING changes. FEATURE keeps the ABFIX-005 amnesty.
        assert _validator(tmp_path, 3)._classify_test_failure(
            _CODE_ASSERT, task_type="feature"
        ) == ("parallel_contention", "high")

    def test_no_task_type_assertion_parallel_stays_contention(self, tmp_path: Path) -> None:
        # Default (no task_type) is unchanged from pre-ABFIX-012 behaviour.
        assert _validator(tmp_path, 3)._classify_test_failure(_CODE_ASSERT) == (
            "parallel_contention", "high",
        )

    def test_testing_nontoken_parallel_keeps_amnesty(self, tmp_path: Path) -> None:
        # A non-token failure in a parallel wave still classifies as
        # parallel_contention → the genuine cross-task contention amnesty is
        # preserved even for TESTING.
        assert _validator(tmp_path, 3)._classify_test_failure(
            _NONTOKEN, task_type="testing"
        ) == ("parallel_contention", "high")

    def test_testing_nontoken_single_is_code(self, tmp_path: Path) -> None:
        # Single wave: a non-token failure is ("code", "n/a") — a real failure
        # the guard still blocks (firing only on "high" would be a false-green).
        assert _validator(tmp_path, 1)._classify_test_failure(
            _NONTOKEN, task_type="testing"
        ) == ("code", "n/a")

    def test_key_not_found_testing_is_code_not_substrate(self, tmp_path: Path) -> None:
        # Anchoring: "key: not found" is a real KeyError code failure, not a
        # substrate gap (it would have re-opened a false-green).
        fc, _ = _validator(tmp_path, 1)._classify_test_failure(
            _KEY_NOT_FOUND, task_type="testing"
        )
        assert fc == "code"


# ============================================================================
# 3. run_independent_tests routes a host-substrate gap to signal_absent
# ============================================================================


def _proc(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _subprocess_validator(tmp_path: Path) -> CoachValidator:
    v = CoachValidator(
        worktree_path=str(tmp_path),
        task_id="TASK-FMDR-004",
        test_command="pytest tests/ -v",
    )
    v._coach_test_execution = "subprocess"
    return v


class TestSubstrateRoutesToSignalAbsent:
    def test_rc127_command_not_found_is_absent(self, tmp_path: Path) -> None:
        v = _subprocess_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(127, stderr="psql: command not found")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is True  # absent → feedback, never a code block

    def test_pytest_wrapped_command_not_found_is_absent(self, tmp_path: Path) -> None:
        # pytest exits 1 but a test shelled out to a missing tool — the captured
        # "command not found" string makes it an absent signal.
        v = _subprocess_validator(tmp_path)
        out = "FAILED tests/test_x.py::test_db\nbash: psql: command not found\n1 failed"
        with patch("subprocess.run", return_value=_proc(1, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is True

    def test_genuine_code_failure_is_NOT_absent(self, tmp_path: Path) -> None:
        # The load-bearing regression: a real code failure (no substrate string)
        # must stay a ran-and-failed signal so it reaches the code-failure guard.
        v = _subprocess_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stdout=_CODE_ASSERT)):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False

    def test_key_not_found_failure_is_NOT_absent(self, tmp_path: Path) -> None:
        # Anchoring at the run_independent_tests layer too.
        v = _subprocess_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stdout=_KEY_NOT_FOUND)):
            r = v.run_independent_tests()
        assert r.signal_absent is False


# ============================================================================
# 4. IndependentTestClassification serialises into the bundle (ABFIX-010 invariant)
# ============================================================================


class TestClassificationSerialisation:
    def test_classification_serialises_via_to_dict(self) -> None:
        cls = IndependentTestClassification(
            failure_class="code", confidence="high", raw_output_excerpt="E AssertionError",
        )
        bundle = CoachEvidenceBundle(honesty=None, independent_test_classification=cls)
        d = bundle.to_dict()
        assert d["independent_test_classification"]["failure_class"] == "code"
        assert d["independent_test_classification"]["confidence"] == "high"
        # Whole bundle stays json-serialisable.
        json.dumps(d)

    def test_classification_defaults_none(self) -> None:
        assert CoachEvidenceBundle(honesty=None).independent_test_classification is None


# ============================================================================
# 5. _apply_independent_test_code_failure_guard — the FMDR-004 backstop
# ============================================================================


def _guard(
    decision: dict,
    *,
    task_type: str,
    tests_passed: bool,
    signal_absent: bool,
    failure_class: str | None,
    tmp_path: Path,
    confidence: str = "high",
) -> dict:
    inv = AgentInvoker.__new__(AgentInvoker)
    itr = IndependentTestResult(
        tests_passed=tests_passed,
        test_command="pytest tests/ -v",
        test_output_summary="x",
        duration_seconds=0.1,
        raw_output=_CODE_ASSERT,
        signal_absent=signal_absent,
    )
    cls = (
        IndependentTestClassification(
            failure_class=failure_class, confidence=confidence, raw_output_excerpt=_CODE_ASSERT,
        )
        if failure_class is not None
        else None
    )
    bundle = CoachEvidenceBundle(
        honesty=None,
        task_type=task_type,
        independent_tests=itr,
        independent_test_classification=cls,
    )
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_independent_test_code_failure_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-FMDR-004",
        turn=1,
        coach_output_path=coach_path,
    )
    return decision


class TestCodeFailureGuard:
    def test_blocks_testing_code_failure_high(self, tmp_path: Path) -> None:
        """The FMDR-004 reproducer: a TESTING task with real code bugs is NOT approved."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class="code", tmp_path=tmp_path,
        )
        assert out["decision"] == "feedback"
        assert out["issues"][0]["category"] == "independent_test_code_failure"
        assert out["issues"][0]["severity"] == "must_fix"
        # Re-persisted so Layer-4 late-approval cannot resurrect the approve.
        persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
        assert persisted["decision"] == "feedback"

    def test_blocks_testing_code_failure_na_confidence(self, tmp_path: Path) -> None:
        """Single-wave ("code", "n/a") still blocks — NOT just ("code", "high")."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class="code", confidence="n/a", tmp_path=tmp_path,
        )
        assert out["decision"] == "feedback"

    def test_noop_when_signal_absent(self, tmp_path: Path) -> None:
        """A substrate gap (signal_absent True) is owned by the absent guard,
        NEVER blocked as code (absence-of-failure-is-not-success)."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=True,
            failure_class="code", tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_noop_when_infrastructure(self, tmp_path: Path) -> None:
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class="infrastructure", tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_noop_when_parallel_contention(self, tmp_path: Path) -> None:
        """Genuine cross-task contention amnesty preserved (not classified code)."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class="parallel_contention", tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_noop_for_feature_task_type(self, tmp_path: Path) -> None:
        """Scope: only TESTING gate semantics change. FEATURE is untouched."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="feature", tests_passed=False, signal_absent=False,
            failure_class="code", tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_noop_when_classification_none(self, tmp_path: Path) -> None:
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class=None, tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_noop_when_tests_passed(self, tmp_path: Path) -> None:
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="testing", tests_passed=True, signal_absent=False,
            failure_class=None, tmp_path=tmp_path,
        )
        assert out["decision"] == "approve"

    def test_leaves_feedback_verdict_untouched(self, tmp_path: Path) -> None:
        decision = {"decision": "feedback", "issues": [{"x": 1}], "rationale": "already"}
        out = _guard(
            decision, task_type="testing", tests_passed=False, signal_absent=False,
            failure_class="code", tmp_path=tmp_path,
        )
        assert out["decision"] == "feedback"

    def test_task_type_case_insensitive(self, tmp_path: Path) -> None:
        """Defends against an uppercased task_type reaching the bundle."""
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(
            decision, task_type="TESTING", tests_passed=False, signal_absent=False,
            failure_class="code", tmp_path=tmp_path,
        )
        assert out["decision"] == "feedback"
