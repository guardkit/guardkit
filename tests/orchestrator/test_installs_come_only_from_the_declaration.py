"""Installs come only from the project's declaration (1 November 2026).

Rich, 31 October 2026: "I don't want any more hidden surprises". GuardKit no
longer works out an install from a project's files: no package manager is
chosen from a manifest, no virtual environment is made, and no interpreter is
looked for. What runs:

* the root ``toolchain.install``, at the worktree root, before the agents
  work and again when a file it serves has changed;
* a component's or a ``parts:`` entry's ``install``, in its folder, before
  that part's tests.

No declared install means no install, said once in the build log ("no install
declared; nothing installed"). A failed declared install is reported, and the
after-task check then says the project's tests could not run.

Every declared command here is the running interpreter recording that it ran,
so nothing is fetched and no package manager has to be installed.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.environment_bootstrap import (
    NO_INSTALL_DECLARED,
    EnvironmentBootstrapper,
    bootstrap_worktree,
    declared_root_install,
    rerun_declared_install_if_due,
)
from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block
from guardkit.orchestrator.work_runner import install_declared

#: Files that used to make GuardKit guess an install (pip, uv, npm, flutter,
#: go, cargo). Their presence must change nothing.
MANIFESTS = {
    "pyproject.toml": "[project]\nname = 'demo'\nversion = '0.1.0'\n",
    "uv.lock": "version = 1\n",
    "requirements.txt": "requests\n",
    "package.json": '{"name": "demo"}\n',
    "package-lock.json": '{"lockfileVersion": 3}\n',
    "pubspec.yaml": "name: demo\n",
    "go.mod": "module demo\n",
    "Cargo.toml": "[package]\nname = 'demo'\n",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _recorder(marker: Path, word: str, exit_code: int = 0) -> str:
    """A declared command (an argument list, no shell) that appends ``word``."""
    script = (
        "import sys; "
        f"open({json.dumps(str(marker))}, 'a').write({json.dumps(word)} + '\\n'); "
        f"sys.exit({exit_code})"
    )
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"


def _ran(marker: Path) -> list:
    return marker.read_text().splitlines() if marker.exists() else []


def _declare(root: Path, toolchain: dict) -> None:
    (root / ".guardkit").mkdir(exist_ok=True)
    (root / ".guardkit" / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": toolchain}), encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git checkout carrying every manifest GuardKit used to read, a root
    file and a web app folder."""
    root = tmp_path / "wt"
    (root / "apps" / "web" / "src").mkdir(parents=True)
    for name, text in MANIFESTS.items():
        (root / name).write_text(text, encoding="utf-8")
    (root / "apps" / "web" / "package.json").write_text('{"name": "web"}\n')
    (root / "apps" / "web" / "src" / "a.ts").write_text("export const a = 1;\n")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "start")
    return root


def _no_environment_made(root: Path) -> None:
    assert not (root / ".venv").exists()
    assert not (root / ".guardkit" / "venv").exists()
    assert not (root / "apps" / "web" / ".venv").exists()


# ---------------------------------------------------------------------------
# No declaration: no install, no virtual environment
# ---------------------------------------------------------------------------


class TestNoDeclarationMeansNoInstall:
    def test_nothing_runs_and_no_venv_is_made(self, repo: Path) -> None:
        _declare(repo, {"test": "true"})  # a test command, but no install

        with patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
            result = bootstrap_worktree(repo)

        assert result.declared is False and result.success is True
        assert result.summary == NO_INSTALL_DECLARED
        run.assert_not_called()
        popen.assert_not_called()
        _no_environment_made(repo)
        assert not (repo / ".guardkit" / "bootstrap_state.json").exists()

    def test_no_guardkit_folder_at_all_is_the_same(self, repo: Path) -> None:
        assert declared_root_install(repo) is None
        assert bootstrap_worktree(repo).declared is False
        _no_environment_made(repo)

    def test_the_build_says_so_once(
        self, repo: Path, caplog: pytest.LogCaptureFixture, capsys
    ) -> None:
        orchestrator = FeatureOrchestrator(
            repo_root=repo, skip_validation=True, worktree_manager=MagicMock()
        )
        worktree = SimpleNamespace(path=repo)

        with caplog.at_level("INFO"):
            for _wave in range(3):
                result = orchestrator._bootstrap_environment(worktree)
                assert result is not None and result.declared is False

        said = [r for r in caplog.records if NO_INSTALL_DECLARED in r.getMessage()]
        assert len(said) == 1
        assert capsys.readouterr().out.count(NO_INSTALL_DECLARED) == 1
        _no_environment_made(repo)

    def test_a_turn_runs_nothing(self, repo: Path) -> None:
        with patch("subprocess.run") as run:
            assert rerun_declared_install_if_due(repo) is None
        run.assert_not_called()

    def test_the_work_leg_installs_nothing(self, repo: Path) -> None:
        block = install_declared(repo)

        assert block["declared"] is False
        assert block["ran"] is False and block["success"] is True
        assert block["summary"] == NO_INSTALL_DECLARED
        _no_environment_made(repo)


# ---------------------------------------------------------------------------
# A declared root install runs, as declared
# ---------------------------------------------------------------------------


class TestADeclaredRootInstallRuns:
    def test_it_runs_at_the_root_and_only_it_runs(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        script = "import os; open(%r, 'a').write(os.getcwd() + '\\n')" % str(marker)
        _declare(repo, {"install": f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"})

        result = bootstrap_worktree(repo)

        assert result.declared and result.success and not result.skipped
        assert _ran(marker) == [str(repo)]
        _no_environment_made(repo)

    def test_its_declared_time_limit_is_used(self, repo: Path) -> None:
        _declare(repo, {"install": "true", "install_timeout": 1234})
        assert declared_root_install(repo).timeout == 1234

    def test_it_runs_once_until_a_file_it_serves_changes(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(repo, {"install": _recorder(marker, "install")})

        bootstrap_worktree(repo)
        assert bootstrap_worktree(repo).skipped is True
        # An untracked file, or a file below a folder it does not serve,
        # does not make it due again.
        (repo / "scratch.log").write_text("build output\n")
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")
        assert rerun_declared_install_if_due(repo).skipped is True
        # A tracked file directly in the root folder does.
        (repo / "package.json").write_text('{"name": "demo", "deps": {"x": "1"}}\n')
        again = rerun_declared_install_if_due(repo)

        assert again.skipped is False and again.success is True
        assert _ran(marker) == ["install", "install"]

    def test_a_changed_declaration_makes_it_due(self, repo: Path, tmp_path: Path) -> None:
        marker = tmp_path / "ran.txt"
        _declare(repo, {"install": _recorder(marker, "first")})
        bootstrap_worktree(repo)
        _declare(repo, {"install": _recorder(marker, "second")})

        bootstrap_worktree(repo)

        assert _ran(marker) == ["first", "second"]

    def test_a_component_folder_without_its_own_install_is_served(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(
            repo,
            {
                "install": _recorder(marker, "root"),
                "components": {"web": {"cwd": "apps/web", "test": "true"}},
            },
        )
        bootstrap_worktree(repo)
        (repo / "apps" / "web" / "package.json").write_text('{"name": "web2"}\n')

        rerun_declared_install_if_due(repo)

        assert _ran(marker) == ["root", "root"]


# ---------------------------------------------------------------------------
# A declared component install runs before that component's tests
# ---------------------------------------------------------------------------


class TestADeclaredComponentInstallRuns:
    def _validator(self, repo: Path, marker: Path) -> CoachValidator:
        toolchain = parse_toolchain_block(
            {
                "install": _recorder(marker, "root install"),
                "components": {
                    "web": {
                        "cwd": "apps/web",
                        "install": _recorder(marker, "web install"),
                        "test": _recorder(marker, "web test"),
                    }
                },
            }
        )
        return CoachValidator(
            str(repo),
            task_id="TASK-DECL-001",
            toolchain=toolchain,
            baseline_commit=_git(repo, "rev-parse", "HEAD"),
        )

    def test_it_runs_in_its_folder_before_its_tests(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        (repo / "apps" / "web" / "src" / "a.ts").write_text("export const a = 2;\n")

        result = self._validator(repo, marker).run_changed_parts()

        assert result.tests_passed is True, result.test_output_summary
        assert _ran(marker) == ["web install", "web test"]
        _no_environment_made(repo)

    def test_the_root_install_does_not_serve_a_component_with_its_own(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(
            repo,
            {
                "install": _recorder(marker, "root install"),
                "components": {
                    "web": {
                        "cwd": "apps/web",
                        "install": _recorder(marker, "web install"),
                        "test": "true",
                    }
                },
            },
        )
        bootstrap_worktree(repo)
        (repo / "apps" / "web" / "package.json").write_text('{"name": "web2"}\n')

        assert rerun_declared_install_if_due(repo).skipped is True
        assert _ran(marker) == ["root install"]


# ---------------------------------------------------------------------------
# A failed declared install is reported, plainly
# ---------------------------------------------------------------------------


class TestAFailedDeclaredInstall:
    def test_it_fails_with_its_output_and_is_not_rerun_inside_the_cooldown(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        script = "import sys; open(%r, 'a').write('x\\n'); sys.stderr.write('no index reachable'); sys.exit(4)" % str(marker)
        _declare(repo, {"install": f"{shlex.quote(sys.executable)} -c {shlex.quote(script)}"})

        first = bootstrap_worktree(repo)
        second = bootstrap_worktree(repo)

        assert first.success is False and first.declared is True
        assert "failed" in first.error and "no index reachable" in first.error
        assert second.success is False and second.skipped is True
        assert _ran(marker) == ["x"]
        state = json.loads((repo / ".guardkit" / "bootstrap_state.json").read_text())
        assert state["success"] is False

    def test_it_is_retried_once_the_cooldown_has_passed(
        self, repo: Path, tmp_path: Path
    ) -> None:
        marker = tmp_path / "ran.txt"
        _declare(repo, {"install": _recorder(marker, "try", exit_code=1)})
        install = declared_root_install(repo)

        EnvironmentBootstrapper(repo, retry_cooldown_seconds=0).bootstrap(install)
        EnvironmentBootstrapper(repo, retry_cooldown_seconds=0).bootstrap(install)

        assert _ran(marker) == ["try", "try"]

    def test_a_missing_program_is_named(self, repo: Path) -> None:
        _declare(repo, {"install": "no-such-installer-for-guardkit-tests sync"})

        result = bootstrap_worktree(repo)

        assert result.success is False
        assert result.failure.missing_tool == "no-such-installer-for-guardkit-tests"
        assert "is not installed where the build runs" in result.error

    def test_the_work_leg_reports_it_and_goes_on(self, repo: Path) -> None:
        _declare(repo, {"install": "false"})

        block = install_declared(repo)

        assert block["declared"] is True and block["ran"] is True
        assert block["success"] is False
        assert "the declared install `false` failed" in block["error"]

    def test_an_unreadable_declaration_is_never_taken_as_none(self, repo: Path) -> None:
        from guardkit.orchestrator.toolchain_declaration import ToolchainDeclarationError

        _declare(repo, {"install": "x 'unclosed"})
        with pytest.raises(ToolchainDeclarationError):
            declared_root_install(repo)
        assert install_declared(repo)["success"] is False


# ---------------------------------------------------------------------------
# A feature file's bootstrap_extras is said to be unused, not ignored silently
# ---------------------------------------------------------------------------


def _feature_file(root: Path, extras: list) -> None:
    features_dir = root / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "id": "FEAT-EXTRAS",
        "name": "Extras feature",
        "status": "planned",
        "tasks": [
            {
                "id": "TASK-001",
                "name": "A task",
                "file_path": "tasks/backlog/TASK-001.md",
                "status": "pending",
            }
        ],
        "orchestration": {"parallel_groups": [["TASK-001"]]},
    }
    if extras:
        data["bootstrap_extras"] = extras
    (features_dir / "FEAT-EXTRAS.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


class TestBootstrapExtrasIsSaidToBeUnused:
    MESSAGE = (
        "bootstrap_extras in FEAT-EXTRAS is no longer used: GuardKit installs "
        "only what .guardkit/config.yaml toolchain declares"
    )

    def _load_for_a_build(self, root: Path, caplog) -> str:
        """Run the build's setup phase as far as loading the feature (the
        validation that follows is told to stop it), and return the log."""
        from guardkit.orchestrator.feature_loader import (
            FeatureLoader,
            FeatureValidationError,
        )

        orchestrator = FeatureOrchestrator(
            repo_root=root, skip_validation=True, worktree_manager=MagicMock()
        )
        with caplog.at_level("WARNING"), patch.object(
            FeatureLoader, "validate_feature", return_value=["stop here"]
        ), pytest.raises(FeatureValidationError):
            orchestrator._setup_phase("FEAT-EXTRAS", "main")
        return caplog.text

    def test_a_feature_with_extras_is_told_once_in_plain_words(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _feature_file(tmp_path, ["dev"])

        text = self._load_for_a_build(tmp_path, caplog)

        assert text.count(self.MESSAGE) == 1

    def test_a_feature_without_extras_says_nothing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _feature_file(tmp_path, [])

        text = self._load_for_a_build(tmp_path, caplog)

        assert "bootstrap_extras" not in text
