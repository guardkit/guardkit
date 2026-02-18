"""
Unit tests for TASK-BOOT-E3C0: ProjectEnvironmentDetector and EnvironmentBootstrapper.

Tests cover:
1. ProjectEnvironmentDetector — manifest detection, lock-file dedup, monorepo scanning
2. EnvironmentBootstrapper — hash-based skip, state persistence, install execution
3. FeatureOrchestrator._bootstrap_environment — integration with orchestrator

Coverage Target: >=85%
Test Count: 45+ tests
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# ---------------------------------------------------------------------------
# TOML availability — used to gate tests that parse pyproject.toml
# ---------------------------------------------------------------------------
try:
    import tomllib as _tomllib_probe  # noqa: F401

    HAS_TOML = True
except ImportError:
    try:
        import tomli as _tomllib_probe  # type: ignore[import] # noqa: F401

        HAS_TOML = True
    except ImportError:
        HAS_TOML = False

requires_toml = pytest.mark.skipif(not HAS_TOML, reason="tomllib/tomli not available")

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapResult,
    DetectedManifest,
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
)


# ============================================================================
# Helpers
# ============================================================================


def make_manifest(
    path: Path,
    stack: str = "python",
    is_lock_file: bool = False,
    install_command: List[str] | None = None,
) -> DetectedManifest:
    """Create a DetectedManifest for test use."""
    if install_command is None:
        install_command = [sys.executable, "-m", "pip", "install", "-e", "."]
    return DetectedManifest(
        path=path,
        stack=stack,
        is_lock_file=is_lock_file,
        install_command=install_command,
    )


# ============================================================================
# 1. TestDetectedManifest
# ============================================================================


class TestDetectedManifest:
    """Tests for the DetectedManifest dataclass."""

    def test_fields_accessible(self, tmp_path: Path) -> None:
        """All DetectedManifest fields can be read after construction."""
        p = tmp_path / "pyproject.toml"
        m = DetectedManifest(
            path=p,
            stack="python",
            is_lock_file=False,
            install_command=["pip", "install", "."],
        )
        assert m.path == p
        assert m.stack == "python"
        assert m.is_lock_file is False
        assert m.install_command == ["pip", "install", "."]

    def test_lock_file_flag_true(self, tmp_path: Path) -> None:
        """is_lock_file is True for lock-file manifests."""
        m = make_manifest(tmp_path / "poetry.lock", is_lock_file=True)
        assert m.is_lock_file is True


# ============================================================================
# 2. TestBootstrapResult
# ============================================================================


class TestBootstrapResult:
    """Tests for the BootstrapResult dataclass."""

    def test_defaults(self) -> None:
        """BootstrapResult defaults are correct."""
        r = BootstrapResult(
            success=True,
            skipped=False,
            stacks_detected=[],
            manifests_found=[],
        )
        assert r.installs_attempted == 0
        assert r.installs_failed == 0
        assert r.error is None
        assert r.duration_seconds == 0.0

    def test_all_fields(self) -> None:
        """BootstrapResult can hold all fields."""
        r = BootstrapResult(
            success=False,
            skipped=False,
            stacks_detected=["python"],
            manifests_found=["/a/pyproject.toml"],
            installs_attempted=1,
            installs_failed=1,
            error="1/1 install(s) failed",
            duration_seconds=2.5,
        )
        assert r.success is False
        assert r.installs_failed == 1
        assert r.error == "1/1 install(s) failed"
        assert r.duration_seconds == 2.5


# ============================================================================
# 3. TestProjectEnvironmentDetectorScanDirs
# ============================================================================


class TestProjectEnvironmentDetectorScanDirs:
    """Tests for _scan_dirs method."""

    def test_scan_dirs_includes_root(self, tmp_path: Path) -> None:
        """_scan_dirs always includes root as the first directory."""
        detector = ProjectEnvironmentDetector(root=tmp_path)
        dirs = detector._scan_dirs()
        assert dirs[0] == tmp_path

    def test_scan_dirs_includes_subdirs(self, tmp_path: Path) -> None:
        """_scan_dirs returns root + non-hidden subdirectories."""
        subdir = tmp_path / "backend"
        subdir.mkdir()
        detector = ProjectEnvironmentDetector(root=tmp_path)
        dirs = detector._scan_dirs()
        assert subdir in dirs

    def test_scan_dirs_excludes_hidden(self, tmp_path: Path) -> None:
        """_scan_dirs excludes directories starting with '.'."""
        hidden = tmp_path / ".git"
        hidden.mkdir()
        visible = tmp_path / "src"
        visible.mkdir()
        detector = ProjectEnvironmentDetector(root=tmp_path)
        dirs = detector._scan_dirs()
        assert hidden not in dirs
        assert visible in dirs

    def test_scan_dirs_excludes_files(self, tmp_path: Path) -> None:
        """_scan_dirs does not include files, only directories."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        dirs = detector._scan_dirs()
        # Only root should be present (no subdirs created)
        assert dirs == [tmp_path]

    def test_scan_dirs_missing_root_returns_root_only(self, tmp_path: Path) -> None:
        """_scan_dirs handles OSError gracefully and returns [root]."""
        detector = ProjectEnvironmentDetector(root=tmp_path / "nonexistent")
        dirs = detector._scan_dirs()
        assert dirs == [tmp_path / "nonexistent"]


# ============================================================================
# 4. TestProjectEnvironmentDetectorDetect — Python stack
# ============================================================================


class TestProjectEnvironmentDetectorPython:
    """Tests for Python manifest detection."""

    def test_detects_pyproject_toml(self, tmp_path: Path) -> None:
        """pyproject.toml is detected as a python non-lock manifest."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='foo'\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert len(manifests) == 1
        assert manifests[0].stack == "python"
        assert manifests[0].is_lock_file is False
        assert manifests[0].path.name == "pyproject.toml"
        assert sys.executable in manifests[0].install_command

    def test_detects_requirements_txt(self, tmp_path: Path) -> None:
        """requirements.txt is detected as a python non-lock manifest."""
        (tmp_path / "requirements.txt").write_text("requests==2.31.0\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert len(manifests) == 1
        assert manifests[0].stack == "python"
        assert "requirements.txt" in manifests[0].install_command

    def test_detects_poetry_lock_as_lock_file(self, tmp_path: Path) -> None:
        """poetry.lock is detected as a python lock manifest."""
        (tmp_path / "poetry.lock").write_text("# lock\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert len(manifests) == 1
        assert manifests[0].is_lock_file is True
        assert manifests[0].stack == "python"

    def test_poetry_lock_suppresses_pyproject_toml(self, tmp_path: Path) -> None:
        """When both poetry.lock and pyproject.toml exist, only one python manifest returned."""
        (tmp_path / "poetry.lock").write_text("# lock\n")
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        python_manifests = [m for m in manifests if m.stack == "python"]
        assert len(python_manifests) == 1
        assert python_manifests[0].is_lock_file is True

    def test_pyproject_toml_suppresses_requirements_txt(self, tmp_path: Path) -> None:
        """When both pyproject.toml and requirements.txt exist, only one python manifest returned."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "requirements.txt").write_text("requests\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        python_manifests = [m for m in manifests if m.stack == "python"]
        assert len(python_manifests) == 1
        assert python_manifests[0].path.name == "pyproject.toml"

    def test_no_python_manifests_returns_empty(self, tmp_path: Path) -> None:
        """Empty directory yields no manifests."""
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert manifests == []


# ============================================================================
# 5. TestProjectEnvironmentDetectorDetect — Node stack
# ============================================================================


class TestProjectEnvironmentDetectorNode:
    """Tests for Node manifest detection."""

    def test_detects_package_json(self, tmp_path: Path) -> None:
        """package.json is detected as a node non-lock manifest."""
        (tmp_path / "package.json").write_text('{"name":"app"}\n')
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert any(m.stack == "node" for m in manifests)

    def test_detects_pnpm_lock_yaml(self, tmp_path: Path) -> None:
        """pnpm-lock.yaml is detected as a node lock manifest."""
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        node = [m for m in manifests if m.stack == "node"]
        assert len(node) == 1
        assert node[0].is_lock_file is True
        assert "pnpm" in node[0].install_command

    def test_pnpm_lock_suppresses_package_json(self, tmp_path: Path) -> None:
        """pnpm-lock.yaml suppresses package.json for the same directory."""
        (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '6.0'\n")
        (tmp_path / "package.json").write_text('{"name":"app"}\n')
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        node = [m for m in manifests if m.stack == "node"]
        assert len(node) == 1
        assert node[0].is_lock_file is True

    def test_detects_yarn_lock(self, tmp_path: Path) -> None:
        """yarn.lock is detected as a node lock manifest."""
        (tmp_path / "yarn.lock").write_text("# yarn\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        node = [m for m in manifests if m.stack == "node"]
        assert len(node) == 1
        assert "yarn" in node[0].install_command

    def test_detects_package_lock_json(self, tmp_path: Path) -> None:
        """package-lock.json is detected as a node lock manifest with npm ci."""
        (tmp_path / "package-lock.json").write_text('{"lockfileVersion":3}\n')
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        node = [m for m in manifests if m.stack == "node"]
        assert len(node) == 1
        assert "npm" in node[0].install_command[0]
        assert "ci" in node[0].install_command


# ============================================================================
# 6. TestProjectEnvironmentDetectorDetect — other stacks
# ============================================================================


class TestProjectEnvironmentDetectorOtherStacks:
    """Tests for .NET, Go, Rust, and Flutter manifest detection."""

    def test_detects_csproj(self, tmp_path: Path) -> None:
        """A *.csproj file is detected as a dotnet manifest."""
        (tmp_path / "MyApp.csproj").write_text("<Project/>\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        dotnet = [m for m in manifests if m.stack == "dotnet"]
        assert len(dotnet) == 1
        assert "dotnet" in dotnet[0].install_command

    def test_detects_sln(self, tmp_path: Path) -> None:
        """A *.sln file is detected as a dotnet manifest when no csproj exists."""
        (tmp_path / "Solution.sln").write_text("\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        dotnet = [m for m in manifests if m.stack == "dotnet"]
        assert len(dotnet) == 1
        assert "dotnet" in dotnet[0].install_command

    def test_csproj_suppresses_sln(self, tmp_path: Path) -> None:
        """*.csproj suppresses *.sln for the same directory."""
        (tmp_path / "App.csproj").write_text("<Project/>\n")
        (tmp_path / "Solution.sln").write_text("\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        dotnet = [m for m in manifests if m.stack == "dotnet"]
        assert len(dotnet) == 1
        assert dotnet[0].path.suffix == ".csproj"

    def test_detects_go_mod(self, tmp_path: Path) -> None:
        """go.mod is detected as a go manifest."""
        (tmp_path / "go.mod").write_text("module example.com/app\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        go = [m for m in manifests if m.stack == "go"]
        assert len(go) == 1
        assert go[0].install_command == ["go", "mod", "download"]

    def test_detects_cargo_toml(self, tmp_path: Path) -> None:
        """Cargo.toml is detected as a rust manifest."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname='foo'\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        rust = [m for m in manifests if m.stack == "rust"]
        assert len(rust) == 1
        assert rust[0].install_command == ["cargo", "fetch"]

    def test_detects_pubspec_yaml(self, tmp_path: Path) -> None:
        """pubspec.yaml is detected as a flutter manifest."""
        (tmp_path / "pubspec.yaml").write_text("name: app\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        flutter = [m for m in manifests if m.stack == "flutter"]
        assert len(flutter) == 1
        assert flutter[0].install_command == ["flutter", "pub", "get"]


# ============================================================================
# 7. TestProjectEnvironmentDetectorMonorepo
# ============================================================================


class TestProjectEnvironmentDetectorMonorepo:
    """Tests for monorepo (depth-1) scanning."""

    def test_detects_in_subdirectory(self, tmp_path: Path) -> None:
        """Manifests in depth-1 subdirectories are detected."""
        subdir = tmp_path / "backend"
        subdir.mkdir()
        (subdir / "requirements.txt").write_text("flask\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert any(m.stack == "python" for m in manifests)

    def test_multiple_subdirectories_detected(self, tmp_path: Path) -> None:
        """Manifests in multiple subdirectories are all detected."""
        for name in ["frontend", "backend"]:
            d = tmp_path / name
            d.mkdir()
        (tmp_path / "frontend" / "package.json").write_text('{"name":"fe"}\n')
        (tmp_path / "backend" / "pyproject.toml").write_text("[project]\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        stacks = {m.stack for m in manifests}
        assert "node" in stacks
        assert "python" in stacks

    def test_hidden_subdirectory_not_scanned(self, tmp_path: Path) -> None:
        """Manifests inside hidden subdirectories are not detected."""
        hidden = tmp_path / ".devcontainer"
        hidden.mkdir()
        (hidden / "requirements.txt").write_text("ansible\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert manifests == []

    def test_root_and_subdir_same_stack_both_returned(self, tmp_path: Path) -> None:
        """Root and subdir can each produce a manifest for the same stack."""
        (tmp_path / "requirements.txt").write_text("flask\n")
        subdir = tmp_path / "worker"
        subdir.mkdir()
        (subdir / "requirements.txt").write_text("celery\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        python_manifests = [m for m in manifests if m.stack == "python"]
        assert len(python_manifests) == 2


# ============================================================================
# 8. TestEnvironmentBootstrapperComputeHash
# ============================================================================


class TestEnvironmentBootstrapperComputeHash:
    """Tests for _compute_hash method."""

    def test_hash_is_deterministic(self, tmp_path: Path) -> None:
        """Same manifests always produce the same hash."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        h1 = bootstrapper._compute_hash([m])
        h2 = bootstrapper._compute_hash([m])
        assert h1 == h2

    def test_hash_changes_when_content_changes(self, tmp_path: Path) -> None:
        """Hash changes when manifest file content changes."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        h1 = bootstrapper._compute_hash([m])
        f.write_text("flask\ndjango\n")
        h2 = bootstrapper._compute_hash([m])
        assert h1 != h2

    def test_hash_changes_with_different_manifests(self, tmp_path: Path) -> None:
        """Hash changes when the set of manifests changes."""
        f1 = tmp_path / "requirements.txt"
        f1.write_text("flask\n")
        f2 = tmp_path / "pyproject.toml"
        f2.write_text("[project]\n")
        m1 = make_manifest(f1)
        m2 = make_manifest(f2)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        h1 = bootstrapper._compute_hash([m1])
        h2 = bootstrapper._compute_hash([m1, m2])
        assert h1 != h2

    def test_hash_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        """_compute_hash does not raise when a manifest file is missing."""
        m = make_manifest(tmp_path / "nonexistent.txt")
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        # Should not raise
        h = bootstrapper._compute_hash([m])
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest


# ============================================================================
# 9. TestEnvironmentBootstrapperState
# ============================================================================


class TestEnvironmentBootstrapperState:
    """Tests for _load_state and _save_state methods."""

    def test_load_state_returns_empty_dict_when_missing(self, tmp_path: Path) -> None:
        """_load_state returns {} when state file does not exist."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        assert bootstrapper._load_state() == {}

    def test_save_and_load_state_round_trip(self, tmp_path: Path) -> None:
        """State saved with _save_state can be reloaded with _load_state."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        bootstrapper._save_state("abc123")
        state = bootstrapper._load_state()
        assert state == {"content_hash": "abc123"}

    def test_save_state_creates_parent_dirs(self, tmp_path: Path) -> None:
        """_save_state creates parent directories if they do not exist."""
        state_file = tmp_path / "deep" / "nested" / "state.json"
        bootstrapper = EnvironmentBootstrapper(root=tmp_path, state_file=state_file)
        bootstrapper._save_state("deadbeef")
        assert state_file.exists()

    def test_load_state_returns_empty_on_corrupt_json(self, tmp_path: Path) -> None:
        """_load_state returns {} when state file contains invalid JSON."""
        state_file = tmp_path / ".guardkit" / "bootstrap_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not-json{{{{")
        bootstrapper = EnvironmentBootstrapper(root=tmp_path, state_file=state_file)
        assert bootstrapper._load_state() == {}


# ============================================================================
# 10. TestEnvironmentBootstrapperRunInstall
# ============================================================================


class TestEnvironmentBootstrapperRunInstall:
    """Tests for _run_install method."""

    def test_run_install_success_returns_true(self, tmp_path: Path) -> None:
        """_run_install returns True when subprocess exits with code 0."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            assert bootstrapper._run_install(m) is True

    def test_run_install_nonzero_exit_returns_false(self, tmp_path: Path) -> None:
        """_run_install returns False when subprocess exits with non-zero code."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=1, stdout="", stderr="error msg")
        with patch("subprocess.run", return_value=mock_result):
            assert bootstrapper._run_install(m) is False

    def test_run_install_os_error_returns_false(self, tmp_path: Path) -> None:
        """_run_install returns False and does not raise when OSError occurs."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch("subprocess.run", side_effect=OSError("command not found")):
            assert bootstrapper._run_install(m) is False

    def test_run_install_timeout_returns_false(self, tmp_path: Path) -> None:
        """_run_install returns False and does not raise on TimeoutExpired."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pip install", timeout=300),
        ):
            assert bootstrapper._run_install(m) is False

    def test_run_install_uses_manifest_parent_as_cwd(self, tmp_path: Path) -> None:
        """_run_install passes manifest's parent directory as cwd."""
        subdir = tmp_path / "subproject"
        subdir.mkdir()
        f = subdir / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            bootstrapper._run_install(m)
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["cwd"] == str(subdir)


# ============================================================================
# 11. TestEnvironmentBootstrapperBootstrap
# ============================================================================


class TestEnvironmentBootstrapperBootstrap:
    """Tests for the bootstrap() method."""

    def test_bootstrap_empty_manifests_returns_success(self, tmp_path: Path) -> None:
        """bootstrap([]) returns success immediately without calling subprocess."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch("subprocess.run") as mock_run:
            result = bootstrapper.bootstrap([])
        mock_run.assert_not_called()
        assert result.success is True
        assert result.skipped is False
        assert result.stacks_detected == []
        assert result.manifests_found == []

    def test_bootstrap_skips_on_hash_match(self, tmp_path: Path) -> None:
        """bootstrap() returns skipped=True when hash matches saved state."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        # Precompute and save the hash
        h = bootstrapper._compute_hash([m])
        bootstrapper._save_state(h)
        with patch("subprocess.run") as mock_run:
            result = bootstrapper.bootstrap([m])
        mock_run.assert_not_called()
        assert result.skipped is True
        assert result.success is True

    def test_bootstrap_runs_install_when_hash_differs(self, tmp_path: Path) -> None:
        """bootstrap() calls _run_install when hash does not match."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = bootstrapper.bootstrap([m])
        mock_run.assert_called_once()
        assert result.success is True
        assert result.installs_attempted == 1
        assert result.installs_failed == 0

    def test_bootstrap_records_failed_installs(self, tmp_path: Path) -> None:
        """bootstrap() counts failed installs correctly."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=1, stdout="", stderr="err")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])
        assert result.success is False
        assert result.installs_attempted == 1
        assert result.installs_failed == 1
        assert result.error is not None

    def test_bootstrap_saves_new_hash_after_install(self, tmp_path: Path) -> None:
        """bootstrap() persists the new hash after running installs."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            bootstrapper.bootstrap([m])
        state = bootstrapper._load_state()
        assert "content_hash" in state
        assert len(state["content_hash"]) == 64

    def test_bootstrap_stacks_detected_sorted(self, tmp_path: Path) -> None:
        """stacks_detected is sorted alphabetically."""
        py_f = tmp_path / "requirements.txt"
        py_f.write_text("flask\n")
        node_f = tmp_path / "package.json"
        node_f.write_text('{"name":"app"}\n')
        manifests = [
            make_manifest(py_f, stack="python"),
            make_manifest(node_f, stack="node", install_command=["npm", "install"]),
        ]
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap(manifests)
        assert result.stacks_detected == ["node", "python"]

    def test_bootstrap_manifests_found_contains_all_paths(self, tmp_path: Path) -> None:
        """manifests_found lists all manifest paths as strings."""
        f1 = tmp_path / "requirements.txt"
        f1.write_text("flask\n")
        f2 = tmp_path / "package.json"
        f2.write_text('{"name":"app"}\n')
        manifests = [
            make_manifest(f1, stack="python"),
            make_manifest(f2, stack="node", install_command=["npm", "install"]),
        ]
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap(manifests)
        assert str(f1) in result.manifests_found
        assert str(f2) in result.manifests_found

    def test_bootstrap_duration_is_positive(self, tmp_path: Path) -> None:
        """bootstrap() records a non-negative duration_seconds."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = make_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])
        assert result.duration_seconds >= 0.0


# ============================================================================
# 12. TestBootstrapEnvironmentIntegrationWithOrchestrator
# ============================================================================


class TestBootstrapEnvironmentOrchestrator:
    """Integration tests for _bootstrap_environment in FeatureOrchestrator."""

    def _make_orchestrator(self, tmp_path: Path):
        """Create a minimal FeatureOrchestrator for testing."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        # Use a mock worktree_manager so no git operations run
        mock_wm = MagicMock()
        return FeatureOrchestrator(
            repo_root=tmp_path,
            max_turns=1,
            worktree_manager=mock_wm,
        )

    def _make_worktree(self, path: Path):
        """Create a minimal Worktree-like object."""
        from guardkit.worktrees import Worktree

        return Worktree(
            task_id="FEAT-TEST",
            branch_name="autobuild/FEAT-TEST",
            path=path,
            base_branch="main",
        )

    def test_returns_none_when_no_manifests(self, tmp_path: Path) -> None:
        """_bootstrap_environment returns None when no manifests are found."""
        orchestrator = self._make_orchestrator(tmp_path)
        worktree = self._make_worktree(tmp_path)
        result = orchestrator._bootstrap_environment(worktree)
        assert result is None

    def test_returns_bootstrap_result_when_manifests_found(self, tmp_path: Path) -> None:
        """_bootstrap_environment returns BootstrapResult when manifests exist."""
        (tmp_path / "requirements.txt").write_text("flask\n")
        orchestrator = self._make_orchestrator(tmp_path)
        worktree = self._make_worktree(tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = orchestrator._bootstrap_environment(worktree)
        assert isinstance(result, BootstrapResult)
        assert result.success is True

    def test_returns_none_on_unexpected_exception(self, tmp_path: Path) -> None:
        """_bootstrap_environment returns None and does not raise on unexpected error."""
        orchestrator = self._make_orchestrator(tmp_path)
        worktree = self._make_worktree(tmp_path)
        with patch(
            "guardkit.orchestrator.feature_orchestrator.ProjectEnvironmentDetector",
            side_effect=RuntimeError("unexpected"),
        ):
            result = orchestrator._bootstrap_environment(worktree)
        assert result is None

    def test_skipped_result_does_not_call_subprocess(self, tmp_path: Path) -> None:
        """When hash matches, subprocess is not called."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")

        # Pre-populate state so hash matches
        state_file = tmp_path / ".guardkit" / "bootstrap_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        # Compute hash by instantiating a bootstrapper first
        bootstrapper = EnvironmentBootstrapper(root=tmp_path, state_file=state_file)
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        h = bootstrapper._compute_hash(manifests)
        bootstrapper._save_state(h)

        orchestrator = self._make_orchestrator(tmp_path)
        worktree = self._make_worktree(tmp_path)
        with patch("subprocess.run") as mock_run:
            result = orchestrator._bootstrap_environment(worktree)
        mock_run.assert_not_called()
        assert result is not None
        assert result.skipped is True


# ============================================================================
# 13. TestDetectedManifestIsProjectComplete
# ============================================================================


class TestDetectedManifestIsProjectComplete:
    """Tests for DetectedManifest.is_project_complete() per stack."""

    # Python / pyproject.toml

    @requires_toml
    def test_python_pyproject_flat_layout_complete(self, tmp_path: Path) -> None:
        """is_project_complete() returns True when flat-layout source dir exists."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "my_app"\n')
        (tmp_path / "my_app").mkdir()
        m = make_manifest(pfile, stack="python")
        assert m.is_project_complete() is True

    @requires_toml
    def test_python_pyproject_src_layout_complete(self, tmp_path: Path) -> None:
        """is_project_complete() returns True when src-layout source dir exists."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "my_app"\n')
        (tmp_path / "src" / "my_app").mkdir(parents=True)
        m = make_manifest(pfile, stack="python")
        assert m.is_project_complete() is True

    @requires_toml
    def test_python_pyproject_incomplete(self, tmp_path: Path) -> None:
        """is_project_complete() returns False when source directory is absent."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "fastapi_health_app"\n')
        # Source directory NOT created (greenfield)
        m = make_manifest(pfile, stack="python")
        assert m.is_project_complete() is False

    @requires_toml
    def test_python_pyproject_hyphenated_name_normalised(self, tmp_path: Path) -> None:
        """Hyphens in project name are normalised to underscores for dir lookup."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "my-app"\n')
        (tmp_path / "my_app").mkdir()  # PEP 427 normalised name
        m = make_manifest(pfile, stack="python")
        assert m.is_project_complete() is True

    @requires_toml
    def test_python_pyproject_no_name_returns_true(self, tmp_path: Path) -> None:
        """is_project_complete() returns True when no project name is declared."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[build-system]\nrequires = ["setuptools"]\n')
        m = make_manifest(pfile, stack="python")
        assert m.is_project_complete() is True

    def test_python_requirements_txt_always_complete(self, tmp_path: Path) -> None:
        """requirements.txt manifests are always considered complete."""
        f = tmp_path / "requirements.txt"
        f.write_text("requests\n")
        m = make_manifest(
            f,
            stack="python",
            install_command=[sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        )
        assert m.is_project_complete() is True

    def test_python_poetry_lock_always_complete(self, tmp_path: Path) -> None:
        """poetry.lock manifests are always considered complete."""
        f = tmp_path / "poetry.lock"
        f.write_text("# lock\n")
        m = make_manifest(f, stack="python", is_lock_file=True)
        assert m.is_project_complete() is True

    # Node / package.json

    def test_node_package_json_main_exists_complete(self, tmp_path: Path) -> None:
        """is_project_complete() returns True when main entry point file exists."""
        pfile = tmp_path / "package.json"
        pfile.write_text('{"name":"app","main":"index.js"}\n')
        (tmp_path / "index.js").write_text("module.exports = {}\n")
        m = make_manifest(pfile, stack="node", install_command=["npm", "install"])
        assert m.is_project_complete() is True

    def test_node_package_json_main_missing_incomplete(self, tmp_path: Path) -> None:
        """is_project_complete() returns False when main entry point file is absent."""
        pfile = tmp_path / "package.json"
        pfile.write_text('{"name":"app","main":"index.js"}\n')
        # index.js intentionally not created
        m = make_manifest(pfile, stack="node", install_command=["npm", "install"])
        assert m.is_project_complete() is False

    def test_node_package_json_no_entry_returns_true(self, tmp_path: Path) -> None:
        """is_project_complete() returns True when no entry point is declared."""
        pfile = tmp_path / "package.json"
        pfile.write_text('{"name":"app"}\n')
        m = make_manifest(pfile, stack="node", install_command=["npm", "install"])
        assert m.is_project_complete() is True

    def test_node_lock_file_always_complete(self, tmp_path: Path) -> None:
        """Node lock files are always considered complete."""
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: '6.0'\n")
        m = make_manifest(
            f,
            stack="node",
            is_lock_file=True,
            install_command=["pnpm", "install", "--frozen-lockfile"],
        )
        assert m.is_project_complete() is True

    # .NET / Go (always complete)

    def test_dotnet_always_complete(self, tmp_path: Path) -> None:
        """dotnet manifests are always considered complete."""
        f = tmp_path / "App.csproj"
        f.write_text("<Project/>\n")
        m = make_manifest(f, stack="dotnet", install_command=["dotnet", "restore"])
        assert m.is_project_complete() is True

    def test_go_always_complete(self, tmp_path: Path) -> None:
        """go.mod manifests are always considered complete."""
        f = tmp_path / "go.mod"
        f.write_text("module example.com/app\n")
        m = make_manifest(f, stack="go", install_command=["go", "mod", "download"])
        assert m.is_project_complete() is True

    # Rust

    def test_rust_src_dir_exists_complete(self, tmp_path: Path) -> None:
        """Rust manifests are complete when src/ directory exists."""
        f = tmp_path / "Cargo.toml"
        f.write_text("[package]\nname='app'\n")
        (tmp_path / "src").mkdir()
        m = make_manifest(f, stack="rust", install_command=["cargo", "fetch"])
        assert m.is_project_complete() is True

    def test_rust_no_src_dir_incomplete(self, tmp_path: Path) -> None:
        """Rust manifests are incomplete when src/ directory is absent."""
        f = tmp_path / "Cargo.toml"
        f.write_text("[package]\nname='app'\n")
        m = make_manifest(f, stack="rust", install_command=["cargo", "fetch"])
        assert m.is_project_complete() is False

    # Flutter

    def test_flutter_lib_dir_exists_complete(self, tmp_path: Path) -> None:
        """Flutter manifests are complete when lib/ directory exists."""
        f = tmp_path / "pubspec.yaml"
        f.write_text("name: app\n")
        (tmp_path / "lib").mkdir()
        m = make_manifest(f, stack="flutter", install_command=["flutter", "pub", "get"])
        assert m.is_project_complete() is True

    def test_flutter_no_lib_dir_incomplete(self, tmp_path: Path) -> None:
        """Flutter manifests are incomplete when lib/ directory is absent."""
        f = tmp_path / "pubspec.yaml"
        f.write_text("name: app\n")
        m = make_manifest(f, stack="flutter", install_command=["flutter", "pub", "get"])
        assert m.is_project_complete() is False


# ============================================================================
# 14. TestDetectedManifestGetDependencyInstallCommands
# ============================================================================


class TestDetectedManifestGetDependencyInstallCommands:
    """Tests for DetectedManifest.get_dependency_install_commands() per stack."""

    @requires_toml
    def test_python_pyproject_with_deps_returns_pip_commands(self, tmp_path: Path) -> None:
        """pyproject.toml with dependencies returns one pip install command per dep."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text(
            '[project]\nname = "app"\ndependencies = ["fastapi>=0.100", "sqlalchemy"]\n'
        )
        m = make_manifest(pfile, stack="python")
        cmds = m.get_dependency_install_commands()
        assert cmds is not None
        assert len(cmds) == 2
        for cmd in cmds:
            assert cmd[0] == sys.executable
            assert cmd[1:4] == ["-m", "pip", "install"]
        dep_args = [cmd[4] for cmd in cmds]
        assert "fastapi>=0.100" in dep_args
        assert "sqlalchemy" in dep_args

    @requires_toml
    def test_python_pyproject_no_deps_returns_none(self, tmp_path: Path) -> None:
        """pyproject.toml without dependencies section returns None."""
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "app"\n')
        m = make_manifest(pfile, stack="python")
        assert m.get_dependency_install_commands() is None

    def test_python_requirements_txt_returns_none(self, tmp_path: Path) -> None:
        """requirements.txt manifest returns None (not applicable for dep-only install)."""
        f = tmp_path / "requirements.txt"
        f.write_text("requests\n")
        m = make_manifest(
            f,
            stack="python",
            install_command=[sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        )
        assert m.get_dependency_install_commands() is None

    def test_node_package_json_with_deps_returns_npm_commands(self, tmp_path: Path) -> None:
        """package.json with dependencies returns one npm install command per dep."""
        pfile = tmp_path / "package.json"
        pfile.write_text(
            '{"name":"app","dependencies":{"express":"^4.0","lodash":"^4.0"}}\n'
        )
        m = make_manifest(pfile, stack="node", install_command=["npm", "install"])
        cmds = m.get_dependency_install_commands()
        assert cmds is not None
        assert len(cmds) == 2
        for cmd in cmds:
            assert cmd[:2] == ["npm", "install"]
        pkg_names = [cmd[2] for cmd in cmds]
        assert "express" in pkg_names
        assert "lodash" in pkg_names

    def test_node_package_json_no_deps_returns_none(self, tmp_path: Path) -> None:
        """package.json without a dependencies object returns None."""
        pfile = tmp_path / "package.json"
        pfile.write_text('{"name":"app"}\n')
        m = make_manifest(pfile, stack="node", install_command=["npm", "install"])
        assert m.get_dependency_install_commands() is None

    def test_node_lock_file_returns_none(self, tmp_path: Path) -> None:
        """Node lock files return None (not applicable for dep-only install)."""
        f = tmp_path / "pnpm-lock.yaml"
        f.write_text("lockfileVersion: '6.0'\n")
        m = make_manifest(
            f,
            stack="node",
            is_lock_file=True,
            install_command=["pnpm", "install", "--frozen-lockfile"],
        )
        assert m.get_dependency_install_commands() is None

    def test_dotnet_returns_dotnet_restore(self, tmp_path: Path) -> None:
        """.NET manifest returns [['dotnet', 'restore']]."""
        f = tmp_path / "App.csproj"
        f.write_text("<Project/>\n")
        m = make_manifest(f, stack="dotnet", install_command=["dotnet", "restore"])
        assert m.get_dependency_install_commands() == [["dotnet", "restore"]]

    def test_go_returns_go_mod_download(self, tmp_path: Path) -> None:
        """Go manifest returns [['go', 'mod', 'download']]."""
        f = tmp_path / "go.mod"
        f.write_text("module example.com/app\n")
        m = make_manifest(f, stack="go", install_command=["go", "mod", "download"])
        assert m.get_dependency_install_commands() == [["go", "mod", "download"]]

    def test_rust_returns_cargo_fetch(self, tmp_path: Path) -> None:
        """Rust manifest returns [['cargo', 'fetch']]."""
        f = tmp_path / "Cargo.toml"
        f.write_text("[package]\nname='app'\n")
        m = make_manifest(f, stack="rust", install_command=["cargo", "fetch"])
        assert m.get_dependency_install_commands() == [["cargo", "fetch"]]

    def test_flutter_returns_flutter_pub_get(self, tmp_path: Path) -> None:
        """Flutter manifest returns [['flutter', 'pub', 'get']]."""
        f = tmp_path / "pubspec.yaml"
        f.write_text("name: app\n")
        m = make_manifest(f, stack="flutter", install_command=["flutter", "pub", "get"])
        assert m.get_dependency_install_commands() == [["flutter", "pub", "get"]]


# ============================================================================
# 15. TestEnvironmentBootstrapperIncompleteProject
# ============================================================================


class TestEnvironmentBootstrapperIncompleteProject:
    """Tests for bootstrap() detection-first strategy with incomplete projects."""

    @requires_toml
    def test_incomplete_python_project_installs_deps_not_full_install(
        self, tmp_path: Path
    ) -> None:
        """
        Integration test: greenfield Python project installs deps, not full install.

        When pyproject.toml has dependencies but the source directory is missing,
        bootstrap() runs pip install per-dependency instead of pip install -e .
        """
        pfile = tmp_path / "pyproject.toml"
        pfile.write_text(
            '[project]\nname = "fastapi_health_app"\n'
            'dependencies = ["fastapi>=0.100", "sqlalchemy>=2.0"]\n'
        )
        # Source directory intentionally NOT created (greenfield timing gap)
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert len(manifests) == 1
        assert manifests[0].is_project_complete() is False

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = bootstrapper.bootstrap(manifests)

        # Two dep-install calls (one per dependency), not one full install
        assert mock_run.call_count == 2
        # Full editable install must NOT appear in any command
        for call_obj in mock_run.call_args_list:
            cmd = call_obj.args[0]
            assert "-e" not in cmd, "Full editable install must not be run for incomplete project"
        assert result.success is True
        assert result.installs_attempted == 2
        assert result.installs_failed == 0

    def test_complete_python_project_uses_full_install_command(self, tmp_path: Path) -> None:
        """A complete project (requirements.txt) uses the standard install_command."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert manifests[0].is_project_complete() is True

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = bootstrapper.bootstrap(manifests)

        mock_run.assert_called_once()
        cmd = mock_run.call_args.args[0]
        assert "requirements.txt" in cmd
        assert result.success is True

    @requires_toml
    def test_incomplete_project_no_deps_skips_subprocess(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Incomplete project with no declared deps logs a warning and runs no installs."""
        import logging

        pfile = tmp_path / "pyproject.toml"
        pfile.write_text('[project]\nname = "empty_app"\n')
        # No source dir, no dependencies declared
        detector = ProjectEnvironmentDetector(root=tmp_path)
        manifests = detector.detect()
        assert manifests[0].is_project_complete() is False

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch("subprocess.run") as mock_run:
            with caplog.at_level(
                logging.WARNING,
                logger="guardkit.orchestrator.environment_bootstrap",
            ):
                result = bootstrapper.bootstrap(manifests)

        mock_run.assert_not_called()
        assert result.installs_attempted == 0
        assert result.success is True  # No failures

    # _run_single_command tests

    def test_run_single_command_success_returns_true(self, tmp_path: Path) -> None:
        """_run_single_command returns True on exit code 0."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            assert bootstrapper._run_single_command([sys.executable, "--version"], tmp_path) is True

    def test_run_single_command_nonzero_exit_returns_false(self, tmp_path: Path) -> None:
        """_run_single_command returns False on non-zero exit code."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=mock_result):
            assert bootstrapper._run_single_command(["false"], tmp_path) is False

    def test_run_single_command_oserror_returns_false(self, tmp_path: Path) -> None:
        """_run_single_command returns False and does not raise on OSError."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch("subprocess.run", side_effect=OSError("no such file")):
            assert bootstrapper._run_single_command(["nonexistent"], tmp_path) is False

    def test_run_single_command_timeout_returns_false(self, tmp_path: Path) -> None:
        """_run_single_command returns False and does not raise on TimeoutExpired."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="pip install flask", timeout=300),
        ):
            assert (
                bootstrapper._run_single_command(
                    [sys.executable, "-m", "pip", "install", "flask"], tmp_path
                )
                is False
            )
