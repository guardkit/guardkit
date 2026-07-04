"""Unit tests for the ``--basetemp`` isolation helpers in
``guardkit.lib.pytest_argv`` (TASK-AB-BASETEMP01).

pytest's default basetemp is the per-USER ``/tmp/pytest-of-<user>``, not
per-run, so two concurrent autobuild loops on one host race each other's
tmp-dir creation/cleanup (the FEAT-ABL-005 Coach died on that race three
turns straight). ``isolated_basetemp`` gives every orchestrator-constructed
pytest invocation its own unique basetemp under the system temp dir, with
best-effort cleanup and fail-open semantics.
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from guardkit.lib.pytest_argv import has_basetemp, isolated_basetemp


class TestHasBasetemp:
    def test_separate_value_form(self):
        assert has_basetemp(["tests/", "--basetemp", "/tmp/x"]) is True

    def test_equals_form(self):
        assert has_basetemp(["tests/", "--basetemp=/tmp/x"]) is True

    def test_absent(self):
        assert has_basetemp(["tests/", "-v", "--tb=short"]) is False

    def test_empty_argv(self):
        assert has_basetemp([]) is False

    def test_prefix_lookalike_does_not_match(self):
        # A different option that merely starts with "--basetemp" but is not
        # the =-form must not count (there is no such pytest option today;
        # defensive precision).
        assert has_basetemp(["--basetempx"]) is False


class TestIsolatedBasetemp:
    def test_yields_fragment_with_unique_existing_dir(self):
        with isolated_basetemp("TASK-XXXX-coach-independent") as fragment:
            assert fragment[0] == "--basetemp"
            assert len(fragment) == 2
            basetemp = fragment[1]
            assert os.path.isdir(basetemp)
            # Under the SYSTEM temp dir — never the worktree (checkpoint
            # `git add -A` would sweep a worktree-local tmp dir).
            assert os.path.dirname(basetemp) == tempfile.gettempdir()

    def test_prefix_carries_context_label(self):
        with isolated_basetemp("TASK-AB12-phase4") as fragment:
            name = os.path.basename(fragment[1])
            assert name.startswith("guardkit-pytest-TASK-AB12-phase4-")

    def test_unique_dirs_per_call(self):
        with isolated_basetemp("ctx") as first, isolated_basetemp("ctx") as second:
            assert first[1] != second[1]

    def test_cleanup_removes_dir(self):
        with isolated_basetemp("ctx") as fragment:
            basetemp = fragment[1]
            # Simulate pytest writing into its basetemp.
            (Path(basetemp) / "pytest-of-run").mkdir()
            assert os.path.isdir(basetemp)
        assert not os.path.exists(basetemp)

    def test_cleanup_runs_when_body_raises(self):
        captured = {}
        try:
            with isolated_basetemp("ctx") as fragment:
                captured["dir"] = fragment[1]
                raise RuntimeError("subprocess timed out")
        except RuntimeError:
            pass
        assert not os.path.exists(captured["dir"])

    def test_cleanup_error_swallowed_and_logged_debug(self, caplog):
        caplog.set_level(logging.DEBUG, logger="guardkit.lib.pytest_argv")
        with patch(
            "guardkit.lib.pytest_argv.shutil.rmtree",
            side_effect=OSError("busy"),
        ):
            with isolated_basetemp("ctx") as fragment:
                basetemp = fragment[1]
        # No exception propagated; DEBUG breadcrumb emitted.
        debug_records = [
            r for r in caplog.records if r.levelno == logging.DEBUG
        ]
        assert any("Best-effort cleanup" in r.getMessage() for r in debug_records)
        # Clean up for real (rmtree was mocked away).
        import shutil

        shutil.rmtree(basetemp, ignore_errors=True)

    def test_respects_preexisting_basetemp_separate_form(self):
        with patch("guardkit.lib.pytest_argv.tempfile.mkdtemp") as mkdtemp:
            with isolated_basetemp(
                "ctx", ["tests/", "--basetemp", "/custom"]
            ) as fragment:
                assert fragment == []
        mkdtemp.assert_not_called()

    def test_respects_preexisting_basetemp_equals_form(self):
        with patch("guardkit.lib.pytest_argv.tempfile.mkdtemp") as mkdtemp:
            with isolated_basetemp("ctx", ["--basetemp=/custom"]) as fragment:
                assert fragment == []
        mkdtemp.assert_not_called()

    def test_mkdtemp_failure_fails_open(self, caplog):
        """Tmp-dir trouble must never fail (or fabricate a verdict for) the
        oracle run — drop the flag and log (the task's tri-state regression
        constraint)."""
        caplog.set_level(logging.WARNING, logger="guardkit.lib.pytest_argv")
        with patch(
            "guardkit.lib.pytest_argv.tempfile.mkdtemp",
            side_effect=OSError("no space"),
        ):
            with isolated_basetemp("ctx") as fragment:
                assert fragment == []
        assert any(
            "running without --basetemp" in r.getMessage()
            for r in caplog.records
        )

    def test_context_label_sanitised(self):
        with isolated_basetemp("TASK X/π:weird") as fragment:
            name = os.path.basename(fragment[1])
            assert name.startswith("guardkit-pytest-TASK-X-weird-")

    def test_empty_context_falls_back_to_run(self):
        with isolated_basetemp("///") as fragment:
            name = os.path.basename(fragment[1])
            assert name.startswith("guardkit-pytest-run-")
