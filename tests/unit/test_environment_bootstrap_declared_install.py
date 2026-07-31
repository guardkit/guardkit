"""TS-lane D.1b — a declared install command beats manifest inference.

Inference is a *reading* of the repo's manifests; a declaration is the repo
*telling* us. Where they disagree, the repo wins.

The headline case is the **api_test hollow-pyproject wart**, retired here as a
side effect without touching the manifest ladder's logic. Its real shape
(verified in situ): ``pyproject.toml`` with ``dependencies = []`` plus a
``dev`` extra, alongside ``uv.lock``. The empty ``dependencies`` list still
LOCKS the python stack, so the ``requirements*.txt`` branch never fires; the
lockfile then selects ``uv sync --frozen`` against a lock carrying only the
``dev`` extra. Result: a worktree venv with pytest and no fastapi. One
declared line replaces the whole deduction.

Back-compat is the prime invariant, so every case below has a NO-DECLARATION
control asserting the historic command.

Network-free: no install ever runs — ``subprocess.run`` is patched wherever a
command would be executed.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
)
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration

_UV_ON_PATH = "guardkit.orchestrator.environment_bootstrap._uv_on_path"


def _declare(root: Path, block: dict) -> None:
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": block}), encoding="utf-8"
    )


@pytest.fixture
def hollow_pyproject_repo(tmp_path):
    """api_test's REAL manifest shape: ``dependencies = []`` + ``uv.lock``."""
    root = tmp_path / "api_test"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[build-system]",
                'requires = ["setuptools>=68.0"]',
                'build-backend = "setuptools.build_meta"',
                "",
                "[project]",
                'name = "api_test"',
                'version = "0.1.0"',
                'requires-python = ">=3.11"',
                "dependencies = []",
                "",
                "[project.optional-dependencies]",
                'dev = ["pytest>=7.4.0", "httpx>=0.25.0"]',
            ]
        ),
        encoding="utf-8",
    )
    (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi>=0.110\n", encoding="utf-8")
    (root / "api_test").mkdir()  # so the project reads as source-complete
    (root / "api_test" / "__init__.py").touch()
    return root


@pytest.fixture
def node_repo(tmp_path):
    root = tmp_path / "ts-api-test"
    root.mkdir()
    (root / "package.json").write_text('{"name":"x","main":"src/app.js"}', "utf-8")
    (root / "package-lock.json").write_text("{}", encoding="utf-8")
    return root


# =========================================================================
# 1. THE HOLLOW-PYPROJECT WART — as found, and retired
# =========================================================================


class TestHollowPyprojectWart:
    def test_the_wart_as_found_with_no_declaration(self, hollow_pyproject_repo):
        """CONTROL. ``dependencies = []`` locks the python stack, so the
        requirements.txt carrying the real dependency is never installed and
        ``uv sync --frozen`` runs against a dev-only lock."""
        with patch(_UV_ON_PATH, return_value=True):
            manifests = ProjectEnvironmentDetector(hollow_pyproject_repo).detect()
        assert len(manifests) == 1
        assert manifests[0].install_command == ["uv", "sync", "--frozen"]
        assert manifests[0].declared is False
        # the requirements.txt was suppressed — the wart, in one assertion
        assert not any("requirements" in str(m.path) for m in manifests)

    def test_a_declared_install_retires_the_wart(self, hollow_pyproject_repo):
        _declare(hollow_pyproject_repo, {"install": 'uv pip install -e ".[dev]" -r requirements.txt'})
        with patch(_UV_ON_PATH, return_value=True):
            manifests = ProjectEnvironmentDetector(hollow_pyproject_repo).detect()
        assert len(manifests) == 1
        m = manifests[0]
        assert m.declared is True
        assert m.install_command == shlex.split(
            'uv pip install -e ".[dev]" -r requirements.txt'
        )
        assert m.install_cwd == hollow_pyproject_repo

    def test_the_declared_manifest_keeps_the_python_stack_label(
        self, hollow_pyproject_repo
    ):
        """The COMMAND is the declaration's; the stack LABEL still comes from
        the markers, so stack-keyed behaviour downstream (bootstrap's eager
        Python venv) is unchanged for a Python repo that declares."""
        _declare(hollow_pyproject_repo, {"install": "uv sync --extra dev"})
        with patch(_UV_ON_PATH, return_value=True):
            manifests = ProjectEnvironmentDetector(hollow_pyproject_repo).detect()
        assert manifests[0].stack == "python"

    def test_the_declaration_is_hashed_so_changing_it_reinstalls(
        self, hollow_pyproject_repo
    ):
        """``path`` points at .guardkit/config.yaml precisely so the bootstrap
        content hash invalidates when the DECLARATION changes."""
        bootstrapper = EnvironmentBootstrapper(hollow_pyproject_repo)

        _declare(hollow_pyproject_repo, {"install": "uv sync --extra dev"})
        first = ProjectEnvironmentDetector(hollow_pyproject_repo).detect()
        hash_a = bootstrapper._compute_hash(first)

        _declare(hollow_pyproject_repo, {"install": "uv sync --extra test"})
        second = ProjectEnvironmentDetector(hollow_pyproject_repo).detect()
        hash_b = bootstrapper._compute_hash(second)

        assert hash_a != hash_b


# =========================================================================
# 2. Node / generic behaviour
# =========================================================================


class TestDeclaredInstallGeneral:
    def test_control_node_repo_infers_npm_ci(self, node_repo):
        manifests = ProjectEnvironmentDetector(node_repo).detect()
        assert [m.install_command for m in manifests] == [["npm", "ci"]]

    def test_declared_install_beats_the_lockfile_inference(self, node_repo):
        _declare(node_repo, {"test": "npm test", "install": "npm ci --no-audit"})
        manifests = ProjectEnvironmentDetector(node_repo).detect()
        assert len(manifests) == 1
        assert manifests[0].install_command == ["npm", "ci", "--no-audit"]
        assert manifests[0].stack == "node"

    def test_test_only_declaration_leaves_inference_alone(self, node_repo):
        """Declaring ``test:`` and nothing else must not touch the
        environment leg."""
        _declare(node_repo, {"test": "npm test"})
        manifests = ProjectEnvironmentDetector(node_repo).detect()
        assert [m.install_command for m in manifests] == [["npm", "ci"]]
        assert manifests[0].declared is False

    def test_markerless_repo_gets_a_generic_stack_label(self, tmp_path):
        _declare(tmp_path, {"install": "make deps"})
        manifests = ProjectEnvironmentDetector(tmp_path).detect()
        assert len(manifests) == 1
        assert manifests[0].stack == "declared"
        assert manifests[0].install_command == ["make", "deps"]

    def test_subdirectory_inference_is_untouched(self, tmp_path):
        """Scope is the ROOT directory only — a monorepo's depth-1 packages
        are still inferred."""
        root = tmp_path / "mono"
        (root / "svc").mkdir(parents=True)
        (root / "package.json").write_text('{"name":"root","main":"i.js"}', "utf-8")
        (root / "svc" / "requirements.txt").write_text("flask\n", encoding="utf-8")
        _declare(root, {"install": "npm ci"})
        manifests = ProjectEnvironmentDetector(root).detect()
        assert [m.install_command for m in manifests] == [
            ["npm", "ci"],
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        ]

    def test_explicit_declaration_argument_is_honoured(self, node_repo):
        manifests = ProjectEnvironmentDetector(
            node_repo, toolchain=ToolchainDeclaration(install="pnpm install")
        ).detect()
        assert manifests[0].install_command == ["pnpm", "install"]

    def test_unparseable_declared_install_degrades_to_inference(self, node_repo, caplog):
        """A broken declaration is LOUD, then falls back — never a crashed
        bootstrap."""
        _declare(node_repo, {"install": 'npm ci "unterminated'})
        with caplog.at_level("ERROR"):
            manifests = ProjectEnvironmentDetector(node_repo).detect()
        assert [m.install_command for m in manifests] == [["npm", "ci"]]
        assert any("not a parseable command" in r.message for r in caplog.records)


# =========================================================================
# 3. Execution: cwd + install_timeout
# =========================================================================


class TestDeclaredInstallExecution:
    def _run(self, manifest, root):
        bootstrapper = EnvironmentBootstrapper(root)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            assert bootstrapper._run_install(manifest) is True
        return mock_run.call_args

    def test_declared_command_runs_at_the_repo_root_not_in_dot_guardkit(
        self, node_repo
    ):
        _declare(node_repo, {"install": "npm ci"})
        manifest = ProjectEnvironmentDetector(node_repo).detect()[0]
        # the manifest path is inside .guardkit/, purely for content hashing
        assert manifest.path.parent.name == ".guardkit"
        call = self._run(manifest, node_repo)
        assert call.kwargs["cwd"] == str(node_repo)

    def test_declared_install_timeout_is_honoured(self, node_repo):
        _declare(node_repo, {"install": "npm ci", "install_timeout": 900})
        manifest = ProjectEnvironmentDetector(node_repo).detect()[0]
        call = self._run(manifest, node_repo)
        assert call.kwargs["timeout"] == 900

    def test_undeclared_timeout_stays_at_todays_300s(self, node_repo):
        _declare(node_repo, {"install": "npm ci"})
        manifest = ProjectEnvironmentDetector(node_repo).detect()[0]
        call = self._run(manifest, node_repo)
        assert call.kwargs["timeout"] == 300

    def test_inferred_manifests_keep_their_own_parent_cwd_and_300s(self, node_repo):
        manifest = ProjectEnvironmentDetector(node_repo).detect()[0]
        assert manifest.install_cwd is None
        call = self._run(manifest, node_repo)
        assert call.kwargs["cwd"] == str(node_repo)
        assert call.kwargs["timeout"] == 300

    def test_declared_manifest_never_takes_the_per_dependency_path(self, node_repo):
        """``is_project_complete`` must stay True for a declared manifest, or
        the bootstrap would try to parse .guardkit/config.yaml as a
        package.json."""
        _declare(node_repo, {"install": "npm ci"})
        manifest = ProjectEnvironmentDetector(node_repo).detect()[0]
        assert manifest.is_project_complete() is True
        assert manifest.get_dependency_install_commands() is None


# =========================================================================
# 4. Back-compat pin on the dataclass itself
# =========================================================================


def test_detected_manifest_new_fields_default_to_the_historic_behaviour():
    m = DetectedManifest(
        path=Path("/x/pyproject.toml"),
        stack="python",
        is_lock_file=False,
        install_command=["pip", "install", "-e", "."],
    )
    assert m.declared is False
    assert m.install_cwd is None
    assert m.install_timeout is None
