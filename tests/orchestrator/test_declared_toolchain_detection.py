"""TS-lane D.1b — the declaration on the VERDICT path (CoachValidator).

Four things are pinned here, in the order the design argues them:

1. **The declaration wins over every guess** — over ``detect_stack_profile``
   and, since Rich's ruling of 2026-09-09, over the task-specific ladder
   above it as well; and it fires in PARALLEL WAVES too. The
   ``not self.is_parallel`` guard exists because marker detection is a guess;
   a declaration is not a guess. Removing the parallel-wave fall-through to
   the LLM ``test-orchestrator`` specialist is the lane's M0-POSITIVE change:
   it deletes a frontier hop.
2. **THE PYTEST DEMOTION PROOF** — with ``toolchain.test:
   "pytest tests/ -v --tb=short"`` declared, the chosen command is
   BYTE-IDENTICAL to today's, resolved through the same interpreter-pinned
   branch, with no stack profile attached. pytest is now one declaration
   among many, and we have proved it by demoting it.
3. **Nothing declared means nothing is guessed** (31 October 2026) — with no
   declaration the check could not run and says so; GuardKit runs no
   marker-guessed or pytest command.
4. **The snapshot law** — only the pinned declaration is read.

Network-free and broker-free: every subprocess is patched.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import (
    ToolchainDeclaration,
    snapshot_task_toolchain,
)

_TASK_ID = "TASK-TS-042"
_TODAYS_PYTEST_DEFAULT = "pytest tests/ -v --tb=short"


def _write_config(root, block):
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": block}), encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path):
    """Repo root + the worktree beneath it, laid out as autobuild does."""
    root = tmp_path / "target-repo"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    return root, worktree


def _validator_with_declaration(root, worktree, block, **kwargs):
    """Declare, snapshot pre-turn-1, then build the validator — the real
    sequence, so these tests also exercise the snapshot seam."""
    _write_config(root, block)
    snapshot_task_toolchain(_TASK_ID, worktree, root)
    kwargs.setdefault("task_id", _TASK_ID)
    return CoachValidator(str(worktree), **kwargs)


# =========================================================================
# 1. The declaration wins over marker detection — incl. the parallel wave
# =========================================================================


class TestDeclaredWinsOverDetection:
    def test_declaration_beats_the_node_stack_row(self, repo):
        root, worktree = repo
        (worktree / "package.json").touch()  # would detect "npm test"
        v = _validator_with_declaration(root, worktree, {"test": "npx vitest run"})
        assert v._detect_test_command() == "npx vitest run"

    def test_control_no_declaration_guesses_nothing_from_the_stack_row(self, repo):
        """31 October 2026: a marker file is not a declaration."""
        root, worktree = repo
        (worktree / "package.json").touch()
        v = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert v._detect_test_command() is None

    def test_declaration_overlays_the_matched_stack_row(self, repo):
        """The row is DATA; the declaration overlays it. The node row's
        false-green guard (``success_requires_ran_marker``) is inherited."""
        root, worktree = repo
        (worktree / "package.json").touch()
        v = _validator_with_declaration(root, worktree, {"test": "npx vitest run"})
        v._detect_test_command()
        profile = v._active_stack_profile
        assert profile is not None
        assert profile.stack == "node"
        assert profile.whole_suite_command == "npx vitest run"
        assert profile.success_requires_ran_marker is True

    def test_declared_classifier_fields_override_the_row(self, repo):
        root, worktree = repo
        (worktree / "package.json").touch()
        v = _validator_with_declaration(
            root,
            worktree,
            {
                "test": "npx vitest run",
                "absent_substrings": ["no test files found"],
                "requires_ran_marker": False,
            },
        )
        v._detect_test_command()
        profile = v._active_stack_profile
        assert profile.absent_substrings == ("no test files found",)
        assert profile.success_requires_ran_marker is False
        # ran_marker_regex was NOT declared ⇒ inherited from the node row.
        assert profile.ran_marker_regex is not None

    # ---- the M0-positive half -------------------------------------------

    def test_parallel_wave_honours_the_declaration(self, repo):
        """A parallel wave must NOT fall through to the LLM test-orchestrator
        when the repo has told us the answer. This removes the one frontier
        hop on the non-Python verdict path (design §G)."""
        root, worktree = repo
        (worktree / "package.json").touch()
        v = _validator_with_declaration(
            root, worktree, {"test": "npx vitest run"}, wave_size=4
        )
        assert v.is_parallel is True
        assert v._detect_test_command() == "npx vitest run"

    def test_control_parallel_wave_without_a_declaration_still_defers(self, repo):
        """The ``not self.is_parallel`` guard stays for the GUESS path."""
        root, worktree = repo
        (worktree / "package.json").touch()
        v = CoachValidator(str(worktree), task_id=_TASK_ID, wave_size=4)
        assert v._detect_test_command() is None

    def test_declaration_preempts_task_specific_python_tests(self, repo):
        """RICH'S RULING, 2026-09-09: the leg runs what the repository
        declares — above the task-specific ladder, not merely above the
        marker guesses below it.

        This test used to assert the opposite, and that older precedence is
        what killed a fix journey twenty-six times: the coder wrote a
        PostgreSQL test, the leg ran a bare pytest against a repository with
        no database standing, and the merge-ready checkpoint — which has
        always honoured the declaration — passed the very same code.

        The cost is real and is accepted: the declared command is usually the
        whole suite, so a leg can go red for somebody else's defect, and in a
        parallel wave a sibling's failure lands here. A declaration is not a
        guess; the ladder below it is."""
        root, worktree = repo
        tests_dir = worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_ts_042_thing.py").touch()
        v = _validator_with_declaration(root, worktree, {"test": "npx vitest run"})
        assert v._detect_test_command() == "npx vitest run"
        assert v.test_command_source() == "repository toolchain declaration"

    def test_control_no_declaration_runs_no_task_specific_pytest(self, repo):
        """31 October 2026: the task-specific pytest ladder is gone."""
        root, worktree = repo
        tests_dir = worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_ts_042_thing.py").touch()
        v = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert v._detect_test_command() is None

    def test_no_task_id_tail_also_honours_the_declaration(self, repo):
        root, worktree = repo
        (worktree / "pyproject.toml").touch()
        v = _validator_with_declaration(root, worktree, {"test": "npx vitest run"})
        assert v._detect_test_command() == "npx vitest run"


# =========================================================================
# 2. THE PYTEST DEMOTION PROOF
# =========================================================================


class TestPytestDemotion:
    def test_declared_pytest_is_byte_identical_to_todays_command(self, repo, tmp_path):
        """pytest is now ONE DECLARATION AMONG MANY. Declaring today's exact
        string must produce today's exact string — byte for byte."""
        root, worktree = repo
        (worktree / "pyproject.toml").touch()
        declared = _validator_with_declaration(
            root, worktree, {"test": _TODAYS_PYTEST_DEFAULT}
        )

        control_wt = tmp_path / "control"
        control_wt.mkdir()
        (control_wt / "pyproject.toml").touch()
        control = CoachValidator(str(control_wt))

        chosen = declared._detect_test_command()
        assert chosen == _TODAYS_PYTEST_DEFAULT
        # The same repository without the declaration gets no command.
        assert control._detect_test_command() is None

    def test_declared_pytest_acquires_no_stack_profile(self, repo):
        """No marker row matched and no classifier field was declared, so the
        run keeps the existing pytest absence classifier — which is what makes
        the byte-identity claim true at execution time, not just at
        string-comparison time."""
        root, worktree = repo
        (worktree / "pyproject.toml").touch()
        v = _validator_with_declaration(root, worktree, {"test": _TODAYS_PYTEST_DEFAULT})
        v._detect_test_command()
        assert v._active_stack_profile is None

    def test_a_declared_pytest_command_runs_exactly_as_declared(self, repo):
        """31 October 2026: GuardKit does not rewrite a declared ``pytest …``
        (no pinned interpreter, no injected flags); it runs through the shell
        like any other declared command."""
        root, worktree = repo
        (worktree / "pyproject.toml").touch()
        v = _validator_with_declaration(root, worktree, {"test": _TODAYS_PYTEST_DEFAULT})
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            result = v.run_independent_tests()
        assert mock_run.call_args.args[0] == _TODAYS_PYTEST_DEFAULT
        assert mock_run.call_args.kwargs.get("shell") is True
        assert result.tests_passed is True


# =========================================================================
# 3. The loud absence (the deleted pytest default)
# =========================================================================


class TestLoudAbsence:
    def test_unrecognisable_repo_resolves_no_command(self, tmp_path):
        v = CoachValidator(str(tmp_path))
        assert v._detect_test_command() is None

    def test_the_message_names_the_declaration_and_every_empty_rung(self, tmp_path, caplog):
        v = CoachValidator(str(tmp_path))
        with caplog.at_level("ERROR"):
            v._detect_test_command()
        msg = v._detection_absence
        assert msg.startswith("nothing declared")
        assert "toolchain" in msg  # the fix is named
        # and it was LOUD, not a shrug at WARNING
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_absence_is_unknown_never_a_pass_and_never_a_failure(self, tmp_path):
        v = CoachValidator(str(tmp_path))
        with patch("subprocess.run") as mock_run:
            result = v.run_independent_tests()
        mock_run.assert_not_called()  # no guessed command was executed
        assert result.signal_absent is True
        assert result.check_could_not_run is True
        assert result.tests_passed is False
        assert "nothing declared" in result.test_output_summary

    def test_a_declaration_cures_the_absence_in_a_markerless_repo(self, repo):
        """The whole point: a repo the ladder cannot recognise is now
        buildable by declaring one line."""
        root, worktree = repo
        v = _validator_with_declaration(root, worktree, {"test": "make check"})
        assert v._detect_test_command() == "make check"
        assert v._detection_absence is None

    def test_a_block_declaring_no_test_command_says_so(self, repo):
        root, worktree = repo
        v = _validator_with_declaration(root, worktree, {"install": "npm ci"})
        v._detect_test_command()
        assert "declares no `test:`" in v._detection_absence

# =========================================================================
# 4. Timeout + environment resolution (design §B.5)
# =========================================================================


class TestDeclaredExecution:
    def test_declared_test_timeout_is_honoured(self, repo):
        root, worktree = repo
        v = _validator_with_declaration(
            root, worktree, {"test": "npm test", "test_timeout": 900}
        )
        assert v.test_timeout == 900

    def test_explicit_caller_timeout_still_wins(self, repo):
        root, worktree = repo
        v = _validator_with_declaration(
            root, worktree, {"test": "npm test", "test_timeout": 900}, test_timeout=120
        )
        assert v.test_timeout == 120

    def test_no_declaration_keeps_the_historic_300s(self, tmp_path):
        assert CoachValidator(str(tmp_path)).test_timeout == 300

    def test_declared_command_runs_with_worktree_cwd_and_explicit_env(self, repo):
        """§B.5: the command runs with the worktree cwd and the daemon's PATH
        — made explicit so the resolution rule is visible where the command
        runs. No nvm source, ever. Since 13 October 2026 the rest of the
        daemon's environment is NOT inherited: it is built from nothing, so an
        undeclared setting stays out."""
        root, worktree = repo
        (worktree / "package.json").touch()
        v = _validator_with_declaration(root, worktree, {"test": "npm test"})
        with patch.dict(os.environ, {"GK_TS_LANE_PROBE": "1"}), patch(
            "subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            v.run_independent_tests()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["shell"] is True
        assert kwargs["cwd"] == str(worktree)
        assert kwargs["timeout"] == v.test_timeout
        assert "GK_TS_LANE_PROBE" not in kwargs["env"]
        assert kwargs["env"]["PATH"] == os.environ["PATH"]

    def test_explicit_declaration_argument_bypasses_the_snapshot(self, tmp_path):
        """Callers that already hold a declaration may pass it directly."""
        v = CoachValidator(
            str(tmp_path), toolchain=ToolchainDeclaration(test="go test ./...")
        )
        assert v._detect_test_command() == "go test ./..."

    def test_no_snapshot_means_the_live_config_is_ignored(self, repo):
        """THE §B.4 LAW at the executor: a config the Player wrote into the
        worktree with NO pre-turn-1 snapshot must be invisible."""
        root, worktree = repo
        (worktree / "pyproject.toml").touch()
        _write_config(worktree, {"test": "true"})  # a Player self-green attempt
        v = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert v._detect_test_command() is None
