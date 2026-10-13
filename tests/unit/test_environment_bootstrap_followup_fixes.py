"""Declared install follow-up fixes (design of 13 October 2026, sections 1c and 3c).

- 1c: which install's failure blocks a per-turn refresh is read from the
  install plan detection builds. A declared depth-one component with its own
  inferred install is served by that install, and an undeclared depth-one
  directory is not served by the declared root install. The saved state
  records success only when no install failed, and a recorded failure is
  returned (never a success) inside the retry cooldown.
- 1a: one shared dependency-file check, used by detection's names, the
  per-turn trigger, the stack scoping and the declared install's cache key;
  ``*.csproj`` and ``*.sln`` are on it.
- 3c: a change to ``.guardkit/config.yaml`` triggers the per-turn refresh.

As in ``test_environment_bootstrap_web_components.py``, "the install ran"
means the command reached ``subprocess.run``; version and env probes pass
through to the real ``subprocess.run`` and nothing is ever installed.
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.environment_bootstrap import (
    EnvironmentBootstrapper,
    ProjectEnvironmentDetector,
    changed_dependency_manifests,
    refresh_environment_for_changes,
    stacks_for_changed_manifests,
)

_REAL_RUN = subprocess.run

_ROOT_INSTALL = ("npm", "ci")
_GO_INSTALL = ("go", "mod", "download")
_DOTNET_INSTALL = ("dotnet", "restore")
_PROBE_ARGS = frozenset({"--version", "-v", "version", "env"})


def _declare(root: Path, components: dict | None = None) -> None:
    block: dict = {"install": " ".join(_ROOT_INSTALL)}
    if components:
        block["components"] = components
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(yaml.safe_dump({"toolchain": block}), "utf-8")


def _node_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "package.json").write_text('{"name":"root","private":true}\n', "utf-8")
    (root / "package-lock.json").write_text('{"lockfileVersion":3}\n', "utf-8")
    return root


def _go_dir(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "go.mod").write_text("module example.com/x\n\ngo 1.26\n", "utf-8")
    (directory / "go.sum").write_text("example.com/dep v1.0.0 h1:aaaa=\n", "utf-8")


def _fake_run(codes: Dict[Tuple[str, ...], int] | None = None):
    """Each install returns its code from *codes* (default 0); probes run."""
    codes = codes or {}

    def run(cmd, *args, **kwargs):
        argv = tuple(str(a) for a in cmd)
        if argv in codes:
            return MagicMock(returncode=codes[argv], stdout="", stderr="boom")
        if _PROBE_ARGS.intersection(argv[1:]):
            return _REAL_RUN(cmd, *args, **kwargs)
        return MagicMock(returncode=0, stdout="", stderr="")

    return run


def _ran(mock_run: MagicMock, argv: Tuple[str, ...]) -> int:
    return sum(1 for c in mock_run.call_args_list if tuple(map(str, c.args[0])) == argv)


def _bootstrap(root: Path, codes=None, cooldown: int = 60):
    with patch("subprocess.run", side_effect=_fake_run(codes)) as mock_run:
        manifests = ProjectEnvironmentDetector(root).detect()
        result = EnvironmentBootstrapper(
            root, retry_cooldown_seconds=cooldown
        ).bootstrap(manifests)
    return result, mock_run


def _refresh(root: Path, changed: List[str], codes=None):
    with patch("subprocess.run", side_effect=_fake_run(codes)) as mock_run:
        result = refresh_environment_for_changes(
            root,
            changed,
            relevant_stacks=stacks_for_changed_manifests(changed) or None,
        )
    return result, mock_run


def _saved_state(root: Path) -> dict:
    return json.loads((root / ".guardkit" / "bootstrap_state.json").read_text("utf-8"))


# =========================================================================
# 1c. Partial-refresh controls
# =========================================================================


class TestPartialRefreshControls:
    def test_an_undeclared_depth_one_subpackage_keeps_a_root_failure_a_warning(
        self, tmp_path
    ):
        """``tools/`` is not declared, so the declared root install does not
        serve it: after a ``tools/go.mod`` change its own install runs, a
        failing root install stays a warning, and the refresh succeeds. The
        failure is still saved as a failure."""
        root = _node_root(tmp_path)
        _go_dir(root / "tools")
        _declare(root)
        first, _ = _bootstrap(root)
        assert first.success is True

        (root / "tools" / "go.mod").write_text("module example.com/tools\n", "utf-8")
        result, mock_run = _refresh(root, ["tools/go.mod"], {_ROOT_INSTALL: 1})

        assert _ran(mock_run, _GO_INSTALL) == 1
        assert _ran(mock_run, _ROOT_INSTALL) == 1
        assert result is not None and result.success is True
        assert result.non_relevant_failures == 1
        assert _saved_state(root)["success"] is False

    @pytest.mark.parametrize(
        ("failing", "expected_success"),
        [(_ROOT_INSTALL, True), (_GO_INSTALL, False)],
        ids=["root-install-fails", "component-install-fails"],
    )
    def test_a_declared_depth_one_component_is_served_by_its_own_install(
        self, tmp_path, failing, expected_success
    ):
        """Root declares a Node install; component ``api`` at ``api/`` has a
        ``go.mod``, so detection infers its own install. After an
        ``api/go.sum``-only change a failing root install stays a warning,
        while a failing ``api`` install blocks the refresh."""
        root = _node_root(tmp_path)
        _go_dir(root / "api")
        _declare(root, {"api": {"cwd": "api", "test": "go test ./..."}})
        first, _ = _bootstrap(root)
        assert first.success is True

        (root / "api" / "go.sum").write_text("example.com/dep v1.0.1 h1:b=\n", "utf-8")
        result, mock_run = _refresh(root, ["api/go.sum"], {failing: 1})

        assert _ran(mock_run, _GO_INSTALL) == 1
        assert _ran(mock_run, _ROOT_INSTALL) == 1
        assert result is not None
        assert result.success is expected_success


# =========================================================================
# 1c. A recorded failure inside the cooldown is returned, never a success
# =========================================================================


class TestRecordedFailureInsideTheCooldown:
    def test_a_failed_partial_refresh_then_a_full_bootstrap_fails(self, tmp_path):
        root = _node_root(tmp_path)
        _go_dir(root / "tools")
        _declare(root)
        first, _ = _bootstrap(root)
        assert first.success is True

        (root / "tools" / "go.mod").write_text("module example.com/tools\n", "utf-8")
        partial, _ = _refresh(root, ["tools/go.mod"], {_ROOT_INSTALL: 1})
        assert partial is not None and partial.success is True  # a warning only

        # At once, a full bootstrap: nothing runs and the failure comes back.
        waiting, waiting_run = _bootstrap(root, cooldown=3600)
        assert _ran(waiting_run, _ROOT_INSTALL) == 0
        assert _ran(waiting_run, _GO_INSTALL) == 0
        assert waiting.success is False
        assert waiting.skipped is True
        assert waiting.installs_failed >= 1
        assert any(
            d.essential and Path(d.manifest_path).name == "config.yaml"
            for d in waiting.failure_details
        )

        # After the cooldown the install runs again, and a pass is saved.
        retried, retried_run = _bootstrap(root, cooldown=0)
        assert _ran(retried_run, _ROOT_INSTALL) == 1
        assert retried.success is True and retried.skipped is False
        assert _saved_state(root)["success"] is True

        hit, hit_run = _bootstrap(root, cooldown=3600)
        assert _ran(hit_run, _ROOT_INSTALL) == 0
        assert hit.success is True and hit.skipped is True


# =========================================================================
# 1a. One shared dependency-file check
# =========================================================================


# Every (name or pattern, stack) detection reads, from the markers it labels
# stacks with. ``test_detection_reads_no_name_without_a_stack_marker`` keeps
# this list complete.
_DETECTION_NAMES: List[Tuple[str, str]] = [
    (pattern, stack)
    for stack, patterns in ProjectEnvironmentDetector._STACK_LABEL_MARKERS
    for pattern in patterns
]


class TestSharedDependencyFileCheck:
    def test_detection_reads_no_name_without_a_stack_marker(self):
        """Scan ``_scan_directory``'s source for the names it reads, so a name
        added there without a marker (and so without this guard) is caught."""
        source = inspect.getsource(ProjectEnvironmentDetector._scan_directory)
        scanned = set(re.findall(r'directory / "([^"]+)"', source))
        scanned |= set(re.findall(r'directory\.glob\("([^"]+)"\)', source))
        assert {"package.json", "*.csproj", "*.sln", "requirements*.txt"} <= scanned
        assert scanned <= {pattern for pattern, _stack in _DETECTION_NAMES}

    @pytest.mark.parametrize(("pattern", "stack"), _DETECTION_NAMES)
    def test_every_name_detection_reads_is_a_dependency_file(self, pattern, stack):
        name = pattern.replace("*", "x")
        assert changed_dependency_manifests([f"pkg/{name}"]) == [f"pkg/{name}"]
        assert stacks_for_changed_manifests([f"pkg/{name}"]) == [stack]

    def test_a_declared_install_reruns_after_a_component_csproj_change(self, tmp_path):
        root = _node_root(tmp_path)
        svc = root / "services" / "svc"
        svc.mkdir(parents=True)
        (svc / "Svc.csproj").write_text("<Project />\n", "utf-8")
        _declare(root, {"svc": {"cwd": "services/svc", "test": "dotnet test"}})
        first, _ = _bootstrap(root)
        assert first.success is True

        (svc / "Svc.csproj").write_text('<Project Sdk="x" />\n', "utf-8")
        result, mock_run = _bootstrap(root)
        assert _ran(mock_run, _ROOT_INSTALL) == 1
        assert result.success is True and result.skipped is False

    def test_a_turn_editing_a_csproj_triggers_the_per_turn_refresh(self, tmp_path):
        """Through the real per-turn caller."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        root = _node_root(tmp_path)
        svc = root / "services" / "svc"
        svc.mkdir(parents=True)
        (svc / "Svc.csproj").write_text("<Project />\n", "utf-8")
        _declare(root, {"svc": {"cwd": "services/svc", "test": "dotnet test"}})
        first, _ = _bootstrap(root)
        assert first.success is True

        (svc / "Svc.csproj").write_text('<Project Sdk="x" />\n', "utf-8")
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator._venv_python = None
        with patch("subprocess.run", side_effect=_fake_run({_ROOT_INSTALL: 1})) as mock_run:
            feedback = orchestrator._maybe_refresh_venv_for_manifest_change(
                SimpleNamespace(report={"files_modified": ["services/svc/Svc.csproj"]}),
                SimpleNamespace(path=str(root)),
                1,
            )
        assert _ran(mock_run, _ROOT_INSTALL) == 1
        assert feedback, "a failing declared install after a .csproj edit passed silently"


# =========================================================================
# 3c. A change to the declaration triggers the per-turn refresh
# =========================================================================


class TestDeclarationChangeRefreshes:
    def test_the_declaration_is_matched_by_its_path_not_its_name(self, tmp_path):
        assert changed_dependency_manifests([".guardkit/config.yaml"]) == [
            ".guardkit/config.yaml"
        ]
        assert changed_dependency_manifests(["repo:.guardkit/config.yaml"])
        absolute = str(tmp_path / ".guardkit" / "config.yaml")
        assert changed_dependency_manifests([absolute], tmp_path) == [absolute]
        assert changed_dependency_manifests(["config.yaml"]) == []
        assert changed_dependency_manifests(["app/.guardkit/config.yaml"]) == []
        assert changed_dependency_manifests(["app/config.yaml"]) == []

    def test_a_turn_that_edits_the_declaration_refreshes(self, tmp_path):
        """Through the real per-turn caller: the builder changed the declared
        install, so it runs again before the verifier."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        root = _node_root(tmp_path)
        _declare(root)
        first, _ = _bootstrap(root)
        assert first.success is True

        cfg = root / ".guardkit" / "config.yaml"
        cfg.write_text(
            yaml.safe_dump({"toolchain": {"install": "npm ci", "install_timeout": 900}}),
            "utf-8",
        )
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator._venv_python = None
        with patch("subprocess.run", side_effect=_fake_run()) as mock_run:
            feedback = orchestrator._maybe_refresh_venv_for_manifest_change(
                SimpleNamespace(report={"files_modified": [".guardkit/config.yaml"]}),
                SimpleNamespace(path=str(root)),
                1,
            )
        assert feedback is None
        assert _ran(mock_run, _ROOT_INSTALL) == 1
