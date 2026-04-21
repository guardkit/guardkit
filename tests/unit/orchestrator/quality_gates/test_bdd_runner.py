"""Unit tests for the task-level BDD oracle runner (TASK-BDD-E8954).

Coverage Target: >=85%

The runner is a thin shell over a pytest-bdd subprocess. To keep tests fast
and hermetic we patch the subprocess seam (``_invoke_pytest_bdd``) and the
pytest-bdd availability probe (``has_pytest_bdd``), then exercise the parser
and the public ``run_bdd_for_task`` wiring with crafted JUnit XML payloads.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import (
    BDDResult,
    FailureDetail,
    PendingDetail,
    _PytestInvocation,
    _build_pytest_argv,
    find_feature_files_with_tag,
    parse_junit_xml,
    run_bdd_for_task,
    task_tag,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    (tmp_path / "features").mkdir()
    return tmp_path


def _write_feature(worktree: Path, name: str, body: str) -> Path:
    fp = worktree / "features" / name
    fp.write_text(body, encoding="utf-8")
    return fp


_PASS_FEATURE = """\
Feature: Login

  @task:TASK-001
  Scenario: User logs in
    Given a valid user
    When the user logs in
    Then the user is greeted
"""


_PENDING_FEATURE = """\
Feature: Signup

  @task:TASK-001
  Scenario: User signs up
    Given an empty database
    When the user signs up
    Then the user is created
"""


_UNTAGGED_FEATURE = """\
Feature: Whole-feature smoke

  Scenario: Visit homepage
    Given the app is up
    When the user visits the homepage
    Then they see the marketing copy
"""


_FAILED_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1" errors="0">
    <testcase classname="features/login.feature" name="User logs in">
      <failure message="AssertionError: assert 'Welcome' in 'Goodbye'">
Traceback (most recent call last):
  File "tests/steps/test_login.py", line 42, in then_user_is_greeted
    assert "Welcome" in body, body
AssertionError: assert 'Welcome' in 'Goodbye'
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""


_PENDING_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1" errors="0">
    <testcase classname="features/signup.feature" name="User signs up">
      <failure message="StepDefinitionNotFoundError: Step definition is not found: When the user signs up">
StepDefinitionNotFoundError: Step definition is not found:
When the user signs up
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""


_PASSED_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" errors="0">
    <testcase classname="features/login.feature" name="User logs in" />
  </testsuite>
</testsuites>
"""


# ---------------------------------------------------------------------------
# task_tag + discovery
# ---------------------------------------------------------------------------


class TestTaskTag:
    def test_task_tag_format(self):
        assert task_tag("TASK-001") == "@task:TASK-001"

    def test_task_tag_with_prefix(self):
        assert task_tag("TASK-AUTH-AB12") == "@task:TASK-AUTH-AB12"


class TestFindFeatureFilesWithTag:
    def test_returns_empty_when_features_dir_missing(self, tmp_path: Path):
        assert find_feature_files_with_tag(tmp_path / "features", "@task:TASK-001") == []

    def test_returns_only_matching_files(self, worktree: Path):
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        _write_feature(worktree, "homepage.feature", _UNTAGGED_FEATURE)

        matches = find_feature_files_with_tag(worktree / "features", "@task:TASK-001")

        assert [p.name for p in matches] == ["login.feature"]

    def test_handles_multiple_matches_sorted(self, worktree: Path):
        _write_feature(worktree, "b.feature", _PASS_FEATURE)
        _write_feature(worktree, "a.feature", _PASS_FEATURE)

        matches = find_feature_files_with_tag(worktree / "features", "@task:TASK-001")

        assert [p.name for p in matches] == ["a.feature", "b.feature"]


# ---------------------------------------------------------------------------
# JUnit XML parsing
# ---------------------------------------------------------------------------


class TestParseJunitXml:
    def test_empty_input(self):
        passed, failures, pending = parse_junit_xml("")
        assert passed == 0
        assert failures == []
        assert pending == []

    def test_passed_scenario(self):
        passed, failures, pending = parse_junit_xml(_PASSED_JUNIT)
        assert passed == 1
        assert failures == []
        assert pending == []

    def test_failed_scenario_classifies_as_failure(self):
        passed, failures, pending = parse_junit_xml(_FAILED_JUNIT)
        assert passed == 0
        assert pending == []
        assert len(failures) == 1
        f = failures[0]
        assert isinstance(f, FailureDetail)
        assert f.scenario_name == "User logs in"
        assert "features/login.feature" in f.feature_file
        assert "AssertionError" in f.reason

    def test_pending_step_classifies_as_pending(self):
        passed, failures, pending = parse_junit_xml(_PENDING_JUNIT)
        assert passed == 0
        assert failures == []
        assert len(pending) == 1
        p = pending[0]
        assert isinstance(p, PendingDetail)
        assert p.scenario_name == "User signs up"
        assert "features/signup.feature" in p.feature_file
        # The extracted step should be the offending Gherkin line, not the
        # StepDefinitionNotFoundError header.
        assert "the user signs up" in p.pending_step.lower()

    def test_pending_and_failure_in_same_run(self):
        combined = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" failures="2" errors="0">
    <testcase classname="features/a.feature" name="Pass case" />
    <testcase classname="features/a.feature" name="Real bug">
      <failure message="AssertionError: expected 1 got 0">AssertionError</failure>
    </testcase>
    <testcase classname="features/b.feature" name="Pending case">
      <failure message="StepDefinitionNotFoundError: Step definition is not found: When something happens">x</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
        passed, failures, pending = parse_junit_xml(combined)
        assert passed == 1
        assert len(failures) == 1
        assert len(pending) == 1

    def test_skipped_node_neither_passes_nor_fails(self):
        skipped = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" errors="0" skipped="1">
    <testcase classname="features/x.feature" name="Skipped scenario">
      <skipped message="not relevant"/>
    </testcase>
  </testsuite>
</testsuites>
"""
        passed, failures, pending = parse_junit_xml(skipped)
        assert passed == 0
        assert failures == []
        assert pending == []

    def test_malformed_xml_returns_empty(self):
        passed, failures, pending = parse_junit_xml("not xml at all <<<")
        assert passed == 0
        assert failures == []
        assert pending == []


# ---------------------------------------------------------------------------
# Argv construction
# ---------------------------------------------------------------------------


class TestBuildPytestArgv:
    def test_argv_contains_required_flags(self, tmp_path: Path):
        feat = tmp_path / "features" / "x.feature"
        feat.parent.mkdir()
        feat.write_text("Feature: x")
        junit = tmp_path / "out.xml"

        argv = _build_pytest_argv([feat], "@task:TASK-001", junit)

        assert argv[0] == "pytest"
        assert "--gherkin-terminal-reporter" in argv
        assert any(a.startswith("--junitxml=") for a in argv)
        assert "-m" in argv
        # Tag must be sanitised to a valid pytest marker — no leading @ or colon.
        marker_idx = argv.index("-m") + 1
        marker = argv[marker_idx]
        assert not marker.startswith("@")
        assert ":" not in marker
        assert "TASK_001" in marker
        assert str(feat) in argv


# ---------------------------------------------------------------------------
# Public entry point: run_bdd_for_task
# ---------------------------------------------------------------------------


class _Patcher:
    """Tiny helper to capture monkeypatched invocation arguments."""

    def __init__(self, junit_xml: str, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.junit_xml = junit_xml
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: List[dict] = []

    def __call__(self, *, feature_files, tag, cwd, junit_xml_path, timeout, python_executable=None):
        self.calls.append({
            "feature_files": list(feature_files),
            "tag": tag,
            "cwd": cwd,
            "junit_xml_path": junit_xml_path,
            "timeout": timeout,
        })
        # Materialise the junit file too so the runner can read it back.
        Path(junit_xml_path).parent.mkdir(parents=True, exist_ok=True)
        Path(junit_xml_path).write_text(self.junit_xml, encoding="utf-8")
        return _PytestInvocation(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            junit_xml=self.junit_xml,
        )


class TestRunBddForTask:
    def test_no_feature_file_returns_none(self, worktree: Path, monkeypatch):
        # AC: tests/unit/orchestrator/quality_gates/test_bdd_runner.py::test_no_feature_file_returns_none
        # No .feature files exist at all.
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        result = run_bdd_for_task("TASK-001", worktree)

        assert result is None
        assert invoker.calls == []  # subprocess never invoked

    def test_no_matching_tag_returns_none(self, worktree: Path, monkeypatch):
        # .feature exists but does not carry the task-scope tag.
        _write_feature(worktree, "homepage.feature", _UNTAGGED_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        result = run_bdd_for_task("TASK-001", worktree)

        assert result is None
        assert invoker.calls == []

    def test_pytest_bdd_unavailable_returns_none(self, worktree: Path, monkeypatch):
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: False)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        result = run_bdd_for_task("TASK-001", worktree)

        assert result is None
        assert invoker.calls == []

    def test_failing_scenario_recorded(self, worktree: Path, monkeypatch):
        # AC: test_failing_scenario_recorded — assertion failure produces
        # BDDResult(scenarios_failed=1) and pending stays at 0.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(_FAILED_JUNIT, returncode=1),
        )

        result = run_bdd_for_task("TASK-001", worktree)

        assert isinstance(result, BDDResult)
        assert result.scenarios_failed == 1
        assert result.scenarios_pending == 0
        assert result.scenarios_passed == 0
        assert result.failures[0].scenario_name == "User logs in"
        assert result.tag == "@task:TASK-001"
        assert "features/login.feature" in result.feature_files

    def test_pending_step_recorded_distinctly(self, worktree: Path, monkeypatch):
        # AC: test_pending_step_recorded_distinctly — pending must not collapse
        # into failed.
        _write_feature(worktree, "signup.feature", _PENDING_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(_PENDING_JUNIT, returncode=1),
        )

        result = run_bdd_for_task("TASK-001", worktree)

        assert isinstance(result, BDDResult)
        assert result.scenarios_pending == 1
        assert result.scenarios_failed == 0  # CRUCIAL: no false positives
        assert result.scenarios_passed == 0
        assert result.pending[0].scenario_name == "User signs up"

    def test_passing_scenario_recorded(self, worktree: Path, monkeypatch):
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(_PASSED_JUNIT, returncode=0),
        )

        result = run_bdd_for_task("TASK-001", worktree)

        assert isinstance(result, BDDResult)
        assert result.scenarios_passed == 1
        assert result.scenarios_failed == 0
        assert result.scenarios_pending == 0

    def test_pytest_no_tests_collected_returns_none(self, worktree: Path, monkeypatch):
        # If a .feature file mentions the tag in a comment but no scenario is
        # actually tagged, pytest exits with code 5 and no testcases. Treat as
        # "no scenarios ran" rather than runner failure.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        empty_junit = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="0" failures="0" errors="0"/></testsuites>
"""
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(empty_junit, returncode=5),
        )

        result = run_bdd_for_task("TASK-001", worktree)

        assert result is None

    def test_subprocess_invoked_with_tag_and_files(self, worktree: Path, monkeypatch):
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        run_bdd_for_task("TASK-001", worktree)

        assert len(invoker.calls) == 1
        call = invoker.calls[0]
        assert call["tag"] == "@task:TASK-001"
        assert call["cwd"] == worktree
        assert any(p.name == "login.feature" for p in call["feature_files"])


# ---------------------------------------------------------------------------
# BDDResult.to_dict
# ---------------------------------------------------------------------------


class TestBDDResultSerialisation:
    def test_to_dict_round_trip(self):
        result = BDDResult(
            scenarios_passed=1,
            scenarios_failed=2,
            scenarios_pending=3,
            failures=[FailureDetail("features/x.feature", "S1", "Then x", "boom")],
            pending=[PendingDetail("features/x.feature", "S2", "When y")],
            feature_files=["features/x.feature"],
            tag="@task:TASK-001",
        )

        d = result.to_dict()

        assert d["scenarios_passed"] == 1
        assert d["scenarios_failed"] == 2
        assert d["scenarios_pending"] == 3
        assert d["failures"][0]["scenario_name"] == "S1"
        assert d["pending"][0]["pending_step"] == "When y"
        assert d["tag"] == "@task:TASK-001"
        assert d["feature_files"] == ["features/x.feature"]


# ---------------------------------------------------------------------------
# has_pytest_bdd subprocess path (worktree-targeted probe)
# ---------------------------------------------------------------------------


class TestHasPytestBdd:
    def test_subprocess_path_returncode_zero_means_available(self, monkeypatch):
        # Drive the subprocess branch of has_pytest_bdd.
        class _Proc:
            returncode = 0

        monkeypatch.setattr(bdd_runner.subprocess, "run", lambda *a, **k: _Proc())
        assert bdd_runner.has_pytest_bdd(python_executable="/usr/bin/python") is True

    def test_subprocess_path_returncode_nonzero_means_unavailable(self, monkeypatch):
        class _Proc:
            returncode = 1

        monkeypatch.setattr(bdd_runner.subprocess, "run", lambda *a, **k: _Proc())
        assert bdd_runner.has_pytest_bdd(python_executable="/usr/bin/python") is False

    def test_subprocess_path_swallows_oserror(self, monkeypatch):
        def raise_oserror(*a, **k):
            raise OSError("no such interpreter")

        monkeypatch.setattr(bdd_runner.subprocess, "run", raise_oserror)
        assert bdd_runner.has_pytest_bdd(python_executable="/no/such/python") is False


# ---------------------------------------------------------------------------
# Step extraction edge cases
# ---------------------------------------------------------------------------


class TestStepExtraction:
    def test_empty_message_returns_empty_step(self):
        from guardkit.orchestrator.quality_gates.bdd_runner import _extract_step_from_message

        assert _extract_step_from_message("") == ""

    def test_skips_pending_header_when_extracting(self):
        from guardkit.orchestrator.quality_gates.bdd_runner import _extract_step_from_message

        msg = (
            "StepDefinitionNotFoundError: Step definition is not found:\n"
            "When the user signs up\n"
        )
        step = _extract_step_from_message(msg)
        assert "the user signs up" in step.lower()
        assert "StepDefinitionNotFoundError" not in step
