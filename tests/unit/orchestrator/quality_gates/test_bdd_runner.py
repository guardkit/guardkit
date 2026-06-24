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

    def test_discovers_nested_feature_layout(self, worktree: Path):
        # AC (TASK-FIX-F584 secondary): jarvis's /feature-spec scaffold
        # emits `features/<feature-slug>/<feature-slug>.feature`. The runner
        # must discover these with the default features_subdir="features";
        # the pre-fix non-recursive glob silent-skipped them via path (1).
        nested_dir = worktree / "features" / "project-scaffolding-supervisor-sessions"
        nested_dir.mkdir()
        (nested_dir / "project-scaffolding-supervisor-sessions.feature").write_text(
            _PASS_FEATURE, encoding="utf-8"
        )

        matches = find_feature_files_with_tag(worktree / "features", "@task:TASK-001")

        assert len(matches) == 1
        assert matches[0].name == "project-scaffolding-supervisor-sessions.feature"
        assert matches[0].parent.name == "project-scaffolding-supervisor-sessions"

    def test_filters_out_vendored_and_dotdirs(self, worktree: Path):
        # AC (TASK-FIX-F584 blast-radius mitigation): switching to rglob
        # must NOT pull in .feature files vendored under dotdirs (.venv,
        # .git, .tox) or known non-dot vendored dirs (node_modules,
        # __pycache__, site-packages). Only project-scope feature files
        # should be returned.
        features_dir = worktree / "features"

        # Project-scope: should be found.
        project_nested = features_dir / "real-feature"
        project_nested.mkdir()
        (project_nested / "real.feature").write_text(_PASS_FEATURE, encoding="utf-8")

        # Dotdirs: .venv/, .git/, .tox/, nested combinations.
        for dotdir in (".venv", ".git", ".tox"):
            p = features_dir / dotdir / "deep" / "nested"
            p.mkdir(parents=True)
            (p / "vendored.feature").write_text(_PASS_FEATURE, encoding="utf-8")

        # Non-dot vendored: node_modules/, __pycache__/, site-packages/.
        for vendored in ("node_modules", "__pycache__", "site-packages"):
            p = features_dir / vendored / "pkg"
            p.mkdir(parents=True)
            (p / "vendored.feature").write_text(_PASS_FEATURE, encoding="utf-8")

        matches = find_feature_files_with_tag(features_dir, "@task:TASK-001")

        # Only the project-scope file should be matched; the 6 vendored
        # files (all containing the @task:TASK-001 tag via _PASS_FEATURE)
        # must be filtered out.
        assert len(matches) == 1, (
            f"Filter leaked vendored files: {[str(p) for p in matches]}"
        )
        assert matches[0].name == "real.feature"
        # Defensive: confirm no vendored path component is in the result.
        for part in matches[0].relative_to(features_dir).parts:
            assert not part.startswith(".")
            assert part not in {"node_modules", "__pycache__", "site-packages"}


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

    def __call__(
        self,
        *,
        feature_files,
        tag,
        cwd,
        junit_xml_path,
        timeout,
        python_executable=None,
        task_id=None,
    ):
        self.calls.append({
            "feature_files": list(feature_files),
            "tag": tag,
            "cwd": cwd,
            "junit_xml_path": junit_xml_path,
            "timeout": timeout,
            "python_executable": python_executable,
            "task_id": task_id,
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

    def test_pytest_bdd_unavailable_with_tags_returns_synthetic_blocker(
        self, worktree: Path, monkeypatch, caplog
    ):
        # AC (TASK-FIX-BDDM-1, R1+R2): when tagged feature files exist but
        # pytest-bdd is not importable, the runner must surface a synthetic
        # BDDResult(scenarios_failed=1) so Coach's `scenarios_failed == 0`
        # rule blocks rather than vacuously approving. The pre-fix path
        # returned None, which Coach silently approved.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: False)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        with caplog.at_level("WARNING", logger=bdd_runner.logger.name):
            result = run_bdd_for_task("TASK-001", worktree)

        # Subprocess never invoked — the synthetic blocker is constructed
        # without running pytest at all.
        assert invoker.calls == []

        # Synthetic blocker surfaces as scenarios_failed=1 with a single
        # FailureDetail naming pytest_bdd_not_importable.
        assert isinstance(result, BDDResult)
        assert result.scenarios_failed == 1
        assert result.scenarios_passed == 0
        assert result.scenarios_pending == 0
        assert len(result.failures) == 1

        failure = result.failures[0]
        assert failure.scenario_name == "pytest_bdd_not_importable"
        assert failure.failing_step == ""
        # The reason must include both the task ID (so feedback is
        # actionable per-task) and the pyproject remediation hint.
        assert "TASK-001" in failure.reason
        assert "pytest-bdd" in failure.reason
        assert "pyproject" in failure.reason
        # feature_file is recorded relative to the worktree.
        assert failure.feature_file == "features/login.feature"

        # Tag and feature_files mirror the standard happy path so Coach
        # feedback can name the affected file(s).
        assert result.tag == "@task:TASK-001"
        assert result.feature_files == ["features/login.feature"]

        # Log was promoted from INFO to WARNING (per AC).
        warning_records = [
            r for r in caplog.records
            if r.levelname == "WARNING" and "pytest-bdd not importable" in r.getMessage()
        ]
        assert warning_records, (
            f"Expected WARNING log about pytest-bdd not importable; "
            f"got: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
        )

    def test_pytest_bdd_unavailable_no_tags_still_skips(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-FIX-BDDM-1, regression-safety): the legitimate-skip
        # path at find_feature_files_with_tag → empty must remain
        # unchanged. pytest-bdd absence only synthesises a blocker when
        # tagged feature files actually exist; absence + no tags is still
        # a legitimate "no BDD oracle for this task" skip and must
        # return None so Coach is not falsely blocked.
        _write_feature(worktree, "homepage.feature", _UNTAGGED_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: False)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        result = run_bdd_for_task("TASK-001", worktree)

        # The early-return at the no-matching-files branch fires before
        # the pytest-bdd availability check — so result is None and no
        # synthetic blocker is constructed.
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

    def test_run_threads_task_id_to_invocation(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-AB-004): run_bdd_for_task must thread its ``task_id``
        # argument into _invoke_pytest_bdd so the env-var contract reaches
        # the pytest subprocess. _PASS_FEATURE carries @task:TASK-001 so
        # that's the task id we run the oracle against.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        run_bdd_for_task("TASK-001", worktree)

        assert len(invoker.calls) == 1
        assert invoker.calls[0]["task_id"] == "TASK-001"


# ---------------------------------------------------------------------------
# GUARDKIT_BDD_TASK_ID env-var threading (TASK-AB-004)
#
# When ``task_id`` is supplied to _invoke_pytest_bdd, the pytest subprocess
# must inherit the parent env AND have ``GUARDKIT_BDD_TASK_ID=<task_id>``
# set on top. This is the contract the project's features/conftest.py reads
# to pick the per-task glue module ``test_<slug>__<TASK_ID>.py`` over the
# legacy shared ``test_<slug>.py``.
# ---------------------------------------------------------------------------


class TestBddTaskIdEnvThreading:
    def _capture_subprocess_run(self, monkeypatch):
        """Patch ``subprocess.run`` inside bdd_runner and capture kwargs."""
        captured: dict = {}

        class _CompletedProcess:
            returncode = 0
            stdout = ""
            stderr = ""

        def _fake_run(argv, **kwargs):
            captured["argv"] = list(argv)
            captured["env"] = kwargs.get("env")
            captured["cwd"] = kwargs.get("cwd")
            captured["timeout"] = kwargs.get("timeout")
            return _CompletedProcess()

        monkeypatch.setattr(bdd_runner.subprocess, "run", _fake_run)
        return captured

    def test_invoke_sets_guardkit_bdd_task_id_env(
        self, tmp_path: Path, monkeypatch
    ):
        # AC: GUARDKIT_BDD_TASK_ID is present in the subprocess env when
        # task_id is supplied.
        feature = tmp_path / "x.feature"
        feature.write_text(_PASS_FEATURE, encoding="utf-8")
        junit = tmp_path / "junit.xml"
        captured = self._capture_subprocess_run(monkeypatch)

        bdd_runner._invoke_pytest_bdd(
            feature_files=[feature],
            tag="@task:TASK-FG-002",
            cwd=tmp_path,
            junit_xml_path=junit,
            timeout=30,
            task_id="TASK-FG-002",
        )

        assert captured["env"] is not None
        assert captured["env"][bdd_runner._BDD_TASK_ID_ENV] == "TASK-FG-002"

    def test_invoke_preserves_inherited_env(
        self, tmp_path: Path, monkeypatch
    ):
        # AC: setting GUARDKIT_BDD_TASK_ID must not strip the parent env
        # (PATH, PYTHONPATH, etc.). os.environ.copy() then update.
        monkeypatch.setenv("GUARDKIT_BDD_PROBE_VAR", "probe-value")
        feature = tmp_path / "x.feature"
        feature.write_text(_PASS_FEATURE, encoding="utf-8")
        junit = tmp_path / "junit.xml"
        captured = self._capture_subprocess_run(monkeypatch)

        bdd_runner._invoke_pytest_bdd(
            feature_files=[feature],
            tag="@task:TASK-FG-002",
            cwd=tmp_path,
            junit_xml_path=junit,
            timeout=30,
            task_id="TASK-FG-002",
        )

        env = captured["env"]
        assert env is not None
        assert env.get("GUARDKIT_BDD_PROBE_VAR") == "probe-value"
        assert env[bdd_runner._BDD_TASK_ID_ENV] == "TASK-FG-002"

    def test_invoke_without_task_id_inherits_env_unchanged(
        self, tmp_path: Path, monkeypatch
    ):
        # AC (regression): the legacy single-task path (task_id=None) must
        # leave the subprocess env exactly inherited — passing env=None to
        # subprocess.run delegates that to the OS rather than constructing
        # a clean dict, which is the pre-AB-004 behaviour.
        feature = tmp_path / "x.feature"
        feature.write_text(_PASS_FEATURE, encoding="utf-8")
        junit = tmp_path / "junit.xml"
        captured = self._capture_subprocess_run(monkeypatch)

        bdd_runner._invoke_pytest_bdd(
            feature_files=[feature],
            tag="@task:TASK-FG-002",
            cwd=tmp_path,
            junit_xml_path=junit,
            timeout=30,
            task_id=None,
        )

        # env=None preserves pre-fix behaviour (subprocess inherits parent).
        assert captured["env"] is None


# ---------------------------------------------------------------------------
# Runner-error surfacing (TASK-FIX-F584)
#
# pytest exit codes other than 0 and 5 (NO_TESTS) with no parsed testcases
# indicate the runner itself failed (usage error, internal error, interrupt,
# timeout, conftest import error). The pre-fix behaviour returned
# ``BDDResult(0, 0, 0, [], [])`` which Coach silently approved — a false
# green. The fix surfaces a synthetic FailureDetail so Coach's
# ``scenarios_failed > 0`` rule blocks approval.
# ---------------------------------------------------------------------------


class TestRunnerErrorSurfacing:
    def _run_with_error(
        self,
        worktree: Path,
        monkeypatch,
        *,
        returncode: int,
        stderr: str = "",
        stdout: str = "",
    ) -> BDDResult:
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        # Empty junit_xml — runner errored before producing any testcases.
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher("", returncode=returncode, stderr=stderr, stdout=stdout),
        )
        result = run_bdd_for_task("TASK-001", worktree)
        assert isinstance(result, BDDResult), (
            f"Runner error (exit={returncode}) must surface as BDDResult, "
            f"not None. Returning None here would silent-skip via path (3), "
            f"which Coach treats as BDD-not-applicable — also wrong for an "
            f"explicit @task:-tagged opt-in."
        )
        return result

    def test_timeout_is_absent_not_a_synthesised_failure(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-ABFIX-010, W2b/L2): a pytest-bdd TIMEOUT (TimeoutExpired ->
        # _PYTEST_EXIT_TIMEOUT sentinel, empty junit) is an ABSENT oracle signal,
        # NOT a ran-and-failed scenario. run_bdd_for_task must return None
        # (absent) — NOT a synthesised scenarios_failed>=1 — so the timeout is
        # never coerced into a failure that three turns running would trip the
        # context-pollution guard with, killing a converging task. A genuine
        # non-timeout runner error (the test below) still surfaces a failure.
        # See .claude/rules/absence-must-survive-every-reconciliation-layer.md
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher("", returncode=bdd_runner._PYTEST_EXIT_TIMEOUT, stderr="timed out"),
        )
        result = run_bdd_for_task("TASK-001", worktree)
        assert result is None, (
            "A BDD-runner timeout must be ABSENT (None), not a synthesised "
            "scenarios_failed>=1 failure (TASK-ABFIX-010)."
        )

    def test_runner_error_exit_4_conftest_import_error_surfaces_as_failure(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-FIX-F584): a GENUINE exit=4 runner error — a conftest
        # ImportError — with empty junit_xml must NOT be silently approved as
        # (0, 0, 0). TASK-AB-BDDNEUTRAL01 carves ONLY the *uncollectable*
        # ("not found") exit-4 case out to neutral; a conftest-load failure is
        # a real broken-environment signal, not an absent BDD input, so it
        # still surfaces as a synthetic failure.
        stderr = (
            "ImportError while loading conftest "
            "'/worktree/features/conftest.py'.\n"
            "E   ModuleNotFoundError: No module named 'common'\n"
        )
        result = self._run_with_error(
            worktree, monkeypatch, returncode=4, stderr=stderr
        )

        assert result.scenarios_failed == 1
        assert result.scenarios_passed == 0
        assert result.scenarios_pending == 0
        assert len(result.failures) == 1
        f = result.failures[0]
        assert isinstance(f, FailureDetail)
        assert f.scenario_name == "pytest_runner_error"
        assert "pytest_runner_error: exit=4" in f.reason
        # Stderr snippet should be embedded so Coach feedback names the cause.
        assert "conftest" in f.reason

    def test_runner_error_exit_3_internal_error_surfaces_as_failure(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-FIX-F584): returncode 3 (pytest internal error) must
        # surface, not silent-skip.
        result = self._run_with_error(
            worktree,
            monkeypatch,
            returncode=3,
            stderr="INTERNALERROR> Traceback ...",
        )

        assert result.scenarios_failed == 1
        assert "pytest_runner_error: exit=3" in result.failures[0].reason

    def test_runner_error_exit_2_interrupted_surfaces_as_failure(
        self, worktree: Path, monkeypatch
    ):
        # AC (TASK-FIX-F584): returncode 2 (interrupted via SIGINT /
        # KeyboardInterrupt) must surface, not silent-skip.
        result = self._run_with_error(
            worktree,
            monkeypatch,
            returncode=2,
            stderr="!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!",
        )

        assert result.scenarios_failed == 1
        assert "pytest_runner_error: exit=2" in result.failures[0].reason

    def test_returncode_5_still_silent_skips(self, worktree: Path, monkeypatch):
        # REGRESSION GUARD: the returncode == 5 (NO_TESTS_COLLECTED) silent-
        # skip path must remain intact. "Feature tag in a comment but no
        # scenario tagged" is a legitimate skip; conflating it with usage
        # errors would over-fire and block Coach on benign empty runs.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher("", returncode=5),
        )

        result = run_bdd_for_task("TASK-001", worktree)

        assert result is None

    def test_runner_error_reason_snippet_is_capped(
        self, worktree: Path, monkeypatch
    ):
        # Defensive: long stderr must be truncated so BDDResult stays
        # compact. Bound is _RUNNER_ERROR_REASON_MAX = 200.
        giant_stderr = "x" * 5000
        result = self._run_with_error(
            worktree, monkeypatch, returncode=4, stderr=giant_stderr
        )

        reason = result.failures[0].reason
        # "pytest_runner_error: exit=4; " prefix plus capped snippet.
        assert len(reason) < 300, f"reason not capped: len={len(reason)}"
        assert reason.endswith("...")

    def test_runner_error_with_empty_streams_still_surfaces(
        self, worktree: Path, monkeypatch
    ):
        # Defensive: even with no stderr/stdout at all, runner-error must
        # surface (just without the snippet).
        result = self._run_with_error(
            worktree, monkeypatch, returncode=4, stderr="", stdout=""
        )

        assert result.scenarios_failed == 1
        assert result.failures[0].reason == "pytest_runner_error: exit=4"


# ---------------------------------------------------------------------------
# Absent-feature collection is neutral, not a failure (TASK-AB-BDDNEUTRAL01)
#
# pytest exit 4 with a "not found" collection signature and zero parsed
# testcases means the tagged .feature could not be COLLECTED — typically a
# project missing the features/conftest.py bridge (FEAT-MEM-07 Error 1, "BDD
# exit-4 affects every task") or a .feature with no glue module yet. That is an
# ABSENT BDD input, not a runner failure: run_bdd_for_task must return None
# (-> bdd_results key absent -> Coach treats the gate as not-applicable), never
# a synthetic failure that stacks into an unrecoverable_stall. A genuine runner
# error (conftest ImportError, exit 2/3, empty-stream exit 4) STILL surfaces
# (F584 preserved). See .claude/rules/absence-of-failure-is-not-success.md.
# ---------------------------------------------------------------------------


class TestAbsentFeatureCollectionIsNeutral:
    def _run(
        self,
        worktree: Path,
        monkeypatch,
        *,
        returncode: int,
        stderr: str = "",
        stdout: str = "",
    ):
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher("", returncode=returncode, stderr=stderr, stdout=stdout),
        )
        return run_bdd_for_task("TASK-001", worktree)

    def test_exit_4_not_found_is_neutral(self, worktree: Path, monkeypatch):
        # THE BUG: .feature passed with no conftest bridge -> exit 4
        # "ERROR: not found:". Must be neutral (None), not failed=1.
        stderr = (
            "ERROR: not found: /worktree/features/login.feature\n"
            "(no match in any of [<Dir features>])\n"
        )
        assert self._run(worktree, monkeypatch, returncode=4, stderr=stderr) is None

    def test_exit_4_file_or_directory_not_found_is_neutral(
        self, worktree: Path, monkeypatch
    ):
        # A non-resolving .feature path: "file or directory not found".
        stderr = "ERROR: file or directory not found: features/login.feature\n"
        assert self._run(worktree, monkeypatch, returncode=4, stderr=stderr) is None

    def test_exit_4_not_found_on_stdout_is_neutral(
        self, worktree: Path, monkeypatch
    ):
        # The signature can land on stdout rather than stderr — still neutral.
        stdout = "ERROR: not found: features/login.feature\n"
        assert self._run(worktree, monkeypatch, returncode=4, stdout=stdout) is None

    def test_exit_4_conftest_import_error_is_not_neutral(
        self, worktree: Path, monkeypatch
    ):
        # F584 PRESERVED: a genuine conftest ImportError also exits 4, but it
        # is a broken-environment signal, not an absent input -> surfaces.
        stderr = (
            "ImportError while loading conftest "
            "'/worktree/features/conftest.py'.\n"
            "ModuleNotFoundError: No module named 'common'\n"
        )
        result = self._run(worktree, monkeypatch, returncode=4, stderr=stderr)
        assert result is not None
        assert result.scenarios_failed == 1

    def test_exit_4_empty_streams_is_not_neutral(
        self, worktree: Path, monkeypatch
    ):
        # ABSENCE-OF-FAILURE SAFETY: an exit 4 with no diagnostic output has no
        # positive evidence of the absent-feature reason. Bias to surfacing
        # (failure), not neutral.
        result = self._run(worktree, monkeypatch, returncode=4, stderr="", stdout="")
        assert result is not None
        assert result.scenarios_failed == 1

    def test_only_exit_4_is_eligible_for_neutral(
        self, worktree: Path, monkeypatch
    ):
        # Only exit 4 is eligible for neutral. An interrupt (2) / internal
        # error (3) is never neutral even if "not found" appears in the noise.
        for rc in (2, 3):
            result = self._run(
                worktree, monkeypatch, returncode=rc, stderr="x not found: x"
            )
            assert result is not None, f"exit {rc} must surface, not go neutral"
            assert result.scenarios_failed == 1

    def test_collected_testcases_override_neutral(
        self, worktree: Path, monkeypatch
    ):
        # If pytest actually parsed testcases, the neutral guard
        # (passed==0 and not failures and not pending) does not apply — the
        # real result wins even on an exit-4 "not found" code.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(_FAILED_JUNIT, returncode=4, stderr="ERROR: not found:"),
        )
        result = run_bdd_for_task("TASK-001", worktree)
        assert result is not None
        assert result.scenarios_failed >= 1

    def test_neutral_result_leaves_coach_gate_inactive(
        self, worktree: Path, monkeypatch, tmp_path: Path
    ):
        # END-TO-END: a neutral (None) BDD verdict means agent_invoker omits
        # the bdd_results key (autobuild.py: `if bdd_results is not None`), so
        # Coach's _check_bdd_results sees no gate and returns no blocking
        # issues. The absent input never contributes a failure to the tally.
        stderr = "ERROR: not found: /worktree/features/login.feature\n"
        assert self._run(worktree, monkeypatch, returncode=4, stderr=stderr) is None

        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        # Key absent, exactly as the agent_invoker would leave it.
        task_work_results: dict = {}
        validator = CoachValidator(worktree_path=str(tmp_path))
        blocking, non_blocking = validator._check_bdd_results(task_work_results)
        assert blocking == []
        assert non_blocking == []


class TestGenuineScenarioFailureStillFails:
    def test_failing_scenario_with_feature_present_reports_failed(
        self, worktree: Path, monkeypatch
    ):
        # AC-2: a .feature exists and a scenario FAILS (real assertion failure
        # in the junit) -> still `failed`. Only the absent-INPUT case is
        # neutral; a collected-and-failed scenario is a real Coach-blocking bug.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher(_FAILED_JUNIT, returncode=1),
        )
        result = run_bdd_for_task("TASK-001", worktree)
        assert result is not None
        assert result.scenarios_failed >= 1


# ---------------------------------------------------------------------------
# Coach-rejection end-to-end (TASK-FIX-F584)
#
# The primary motivation for the runner-error fix is that Coach's approval
# rule is ``bdd_results.scenarios_failed == 0`` — so the fix is only useful
# if a runner-error BDDResult actually causes Coach to reject. This test
# exercises the hand-off: runner produces a synthetic failure, result is
# serialised via to_dict() (as the agent_invoker does when writing
# task_work_results.json), and Coach's `_check_bdd_results` must classify
# it as a blocking issue.
#
# Graphiti-captured approval rule (from guardkit/orchestrator/quality_gates/
# bdd_runner.py module docstring and coach_validator.py line 3573):
#
#   "scenarios_failed > 0 → blocking must_fix issue (Coach rejects)."
# ---------------------------------------------------------------------------


class TestCoachRejectsRunnerError:
    def test_coach_rejects_synthetic_runner_error_result(
        self, worktree: Path, monkeypatch, tmp_path: Path
    ):
        # AC (TASK-FIX-F584): end-to-end that the post-fix BDDResult
        # (with scenarios_failed > 0 on runner error) causes Coach's
        # approval validator to reject.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: True)
        # Use a GENUINE runner error (exit 3 internal error) as the trigger.
        # The exit-4 "not found" case is now neutral (TASK-AB-BDDNEUTRAL01) and
        # would no longer produce a blocking BDDResult, but the end-to-end
        # Coach-rejection contract still holds for real runner errors.
        monkeypatch.setattr(
            bdd_runner,
            "_invoke_pytest_bdd",
            _Patcher("", returncode=3, stderr="INTERNALERROR> Traceback ..."),
        )

        # 1. Runner produces a BDDResult with runner-error synthetic failure.
        bdd_result = run_bdd_for_task("TASK-001", worktree)
        assert isinstance(bdd_result, BDDResult)
        assert bdd_result.scenarios_failed > 0  # cites Graphiti rule above

        # 2. Serialise as the agent_invoker would before Coach consumes.
        task_work_results = {"bdd_results": bdd_result.to_dict()}

        # 3. Coach's _check_bdd_results must classify as blocking.
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        validator = CoachValidator(worktree_path=str(tmp_path))
        blocking, non_blocking = validator._check_bdd_results(task_work_results)

        # Blocking issue must be emitted — this is the direct counter to
        # Outcome D (silent false approval on runner error).
        assert len(blocking) == 1
        issue = blocking[0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "bdd_failure"
        assert issue["scenarios_failed"] == bdd_result.scenarios_failed
        # The synthetic failure scenario name should surface in the
        # examples, so Coach feedback names the runner error explicitly
        # rather than saying "scenario assertion failed".
        assert any(
            "pytest_runner_error" in example
            for example in issue["failure_examples"]
        )

    def test_synthetic_blocker_routes_through_coach_validator(
        self, worktree: Path, monkeypatch, tmp_path: Path
    ):
        # AC (TASK-FIX-BDDM-1): end-to-end that the synthetic
        # pytest-bdd-not-importable BDDResult reaches Coach as a
        # bdd_failure blocking issue (must_fix). Without this routing,
        # the new synthetic blocker would be technically constructed
        # but not actually block — same silent-bypass class as the
        # original bug.
        _write_feature(worktree, "login.feature", _PASS_FEATURE)
        monkeypatch.setattr(bdd_runner, "has_pytest_bdd", lambda **_: False)
        # Patch the subprocess seam too, so an accidental code path
        # that tries to invoke pytest would surface as an obvious test
        # error rather than silently passing.
        invoker = _Patcher(_PASSED_JUNIT)
        monkeypatch.setattr(bdd_runner, "_invoke_pytest_bdd", invoker)

        # 1. Runner produces synthetic BDDResult (the patched code path).
        bdd_result = run_bdd_for_task("TASK-001", worktree)
        assert isinstance(bdd_result, BDDResult)
        assert bdd_result.scenarios_failed == 1
        assert invoker.calls == []  # pytest-bdd absent → never invoked

        # 2. Serialise as the agent_invoker would before Coach consumes
        # task_work_results.json.
        task_work_results = {"bdd_results": bdd_result.to_dict()}

        # 3. Coach's _check_bdd_results must classify as blocking.
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        validator = CoachValidator(worktree_path=str(tmp_path))
        blocking, _non_blocking = validator._check_bdd_results(task_work_results)

        assert len(blocking) == 1
        issue = blocking[0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "bdd_failure"
        assert issue["scenarios_failed"] == 1
        # The synthetic-blocker scenario name surfaces in the examples
        # so Coach feedback says "pytest_bdd_not_importable" rather
        # than the generic "scenario assertion failed".
        assert any(
            "pytest_bdd_not_importable" in example
            for example in issue["failure_examples"]
        )


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


# ---------------------------------------------------------------------------
# Collection-error reason enrichment (TASK-AB-003)
#
# When pytest fails to collect a test module (ImportError, ModuleNotFoundError,
# SyntaxError, plugin load failure, ...) it writes the testcase as
# `<error message="collection failure">...traceback...</error>` rather than a
# `<failure>` block. The pre-fix runner copied the `<error message>` attribute
# verbatim, so `BDDFailure.reason` ended up as the literal string
# `"collection failure"` and the Player got no signal about the real cause.
#
# These tests pin the post-fix behaviour: parse the body for the actual
# exception class+message and the last traceback frame.
# ---------------------------------------------------------------------------


_COLLECTION_ERROR_JUNIT_MODULENOTFOUND = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" errors="1">
    <testcase classname="features.fg-001.test_fg-001" name="features/fg-001/test_fg-001.py" time="0.012">
      <error message="collection failure" type="ModuleNotFoundError">
Traceback (most recent call last):
  File "/worktree/.venv/lib/python3.12/site-packages/_pytest/python.py", line 493, in importtestmodule
    mod = import_path(...)
  File "/worktree/features/fg-001/test_fg-001.py", line 41, in &lt;module&gt;
    from common.jarvis_client import JarvisClient
ModuleNotFoundError: No module named 'common'
      </error>
    </testcase>
  </testsuite>
</testsuites>
"""


_COLLECTION_ERROR_JUNIT_SYNTAX = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" errors="1">
    <testcase classname="features.x.test_x" name="features/x/test_x.py" time="0.001">
      <error message="collection failure" type="SyntaxError">
  File "/worktree/features/x/test_x.py", line 7
    def broken(:
              ^
SyntaxError: invalid syntax
      </error>
    </testcase>
  </testsuite>
</testsuites>
"""


class TestCollectionErrorReason:
    def test_extract_error_reason_includes_module_name_and_frame(self):
        # AC (TASK-AB-003): direct unit test of the helper.
        from guardkit.orchestrator.quality_gates.bdd_runner import (
            _extract_error_reason,
        )

        message = "collection failure"
        body = (
            "Traceback (most recent call last):\n"
            '  File "/worktree/features/fg-001/test_fg-001.py", line 41, in <module>\n'
            "    from common.jarvis_client import JarvisClient\n"
            "ModuleNotFoundError: No module named 'common'\n"
        )
        reason = _extract_error_reason(message, body)

        # AC2: reason must include the missing module name and exception class.
        assert "ModuleNotFoundError" in reason
        assert "No module named 'common'" in reason
        # AC1: reason must include the original `<error message>` attribute…
        assert "collection failure" in reason
        # …and the last traceback frame (file:line plus the source snippet).
        assert "features/fg-001/test_fg-001.py:41" in reason
        assert "from common.jarvis_client import JarvisClient" in reason

    def test_extract_error_reason_passes_through_other_classes_verbatim(self):
        # AC3: no special-casing per exception class — SyntaxError must be
        # surfaced just as faithfully as ImportError.
        from guardkit.orchestrator.quality_gates.bdd_runner import (
            _extract_error_reason,
        )

        message = "collection failure"
        body = (
            '  File "/worktree/features/x/test_x.py", line 7\n'
            "    def broken(:\n"
            "              ^\n"
            "SyntaxError: invalid syntax\n"
        )
        reason = _extract_error_reason(message, body)

        assert "SyntaxError" in reason
        assert "invalid syntax" in reason
        assert "test_x.py:7" in reason

    def test_extract_error_reason_falls_back_to_message_when_body_empty(self):
        from guardkit.orchestrator.quality_gates.bdd_runner import (
            _extract_error_reason,
        )

        reason = _extract_error_reason("collection failure", "")

        # No body to parse — at minimum the original message must survive
        # so reason isn't empty.
        assert "collection failure" in reason

    def test_extract_error_reason_caps_overlong_output(self):
        from guardkit.orchestrator.quality_gates.bdd_runner import (
            _extract_error_reason,
        )

        giant_body = (
            "Traceback (most recent call last):\n"
            + "  Filler line that is not a frame\n" * 200
            + "RuntimeError: " + ("x" * 2000) + "\n"
        )
        reason = _extract_error_reason("collection failure", giant_body)

        assert len(reason) <= 800
        assert reason.endswith("...")

    def test_parse_junit_collection_error_produces_rich_reason(self):
        # AC6 (TASK-AB-003): the integration through parse_junit_xml must
        # produce a FailureDetail whose `reason` contains both
        # "ModuleNotFoundError" and "No module named 'common'".
        passed, failures, pending = parse_junit_xml(
            _COLLECTION_ERROR_JUNIT_MODULENOTFOUND
        )

        assert passed == 0
        assert pending == []
        assert len(failures) == 1
        f = failures[0]
        assert isinstance(f, FailureDetail)
        # The parser should NOT collapse this to "collection failure" alone.
        assert "ModuleNotFoundError" in f.reason
        assert "No module named 'common'" in f.reason
        # Last frame info present.
        assert "test_fg-001.py:41" in f.reason

    def test_parse_junit_collection_error_does_not_classify_as_pending(self):
        # Regression guard: collection errors must NEVER fall into the
        # pending bucket, even though they share the `<error>` shape.
        # Pending is exclusively the StepDefinitionNotFoundError class
        # surfaced inside `<failure>` nodes.
        _, failures, pending = parse_junit_xml(
            _COLLECTION_ERROR_JUNIT_MODULENOTFOUND
        )

        assert len(failures) == 1
        assert pending == []

    def test_parse_junit_failure_path_reason_unchanged(self):
        # AC5 regression guard: the `<failure>` reason path must remain
        # the literal-message extraction it always was. Only `<error>`
        # nodes get the new richer extraction.
        passed, failures, pending = parse_junit_xml(_FAILED_JUNIT)

        assert len(failures) == 1
        # Pre-fix invariant from TestParseJunitXml.test_failed_scenario_classifies_as_failure
        assert "AssertionError" in failures[0].reason
        # No traceback-frame string injected for the failure path.
        assert "  at " not in failures[0].reason


class TestCoachFeedbackEmbedsReason:
    def test_check_bdd_results_description_contains_per_failure_reason(
        self, tmp_path: Path
    ):
        # AC7 (TASK-AB-003): the Coach feedback summariser must surface the
        # per-failure `reason` strings in the issue `description` (which is
        # the only field the Player feedback renderer reads — see
        # AgentInvoker._format_feedback_for_player).
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        bdd_results_dict = {
            "scenarios_passed": 0,
            "scenarios_failed": 1,
            "scenarios_pending": 0,
            "failures": [{
                "feature_file": "features/fg-001/fg-001.feature",
                "scenario_name": "User logs in",
                "failing_step": "collection failure",
                "reason": (
                    "collection failure: ModuleNotFoundError: "
                    "No module named 'common'\n"
                    "  at features/fg-001/test_fg-001.py:41 "
                    "(from common.jarvis_client import JarvisClient)"
                ),
            }],
            "pending": [],
            "feature_files": ["features/fg-001/fg-001.feature"],
            "tag": "@task:TASK-FG-002",
        }
        task_work_results = {"bdd_results": bdd_results_dict}

        validator = CoachValidator(worktree_path=str(tmp_path))
        blocking, _non_blocking = validator._check_bdd_results(
            task_work_results
        )

        assert len(blocking) == 1
        issue = blocking[0]
        assert issue["category"] == "bdd_failure"
        assert issue["severity"] == "must_fix"

        # The Player only sees `description` — so the missing-module string
        # MUST appear there, not just in the `failure_examples` aux list.
        description = issue["description"]
        assert "ModuleNotFoundError" in description
        assert "No module named 'common'" in description
        # And the generic header must remain so the high-level signal is
        # still readable.
        assert "BDD oracle" in description
        assert "scenario(s) failed" in description
