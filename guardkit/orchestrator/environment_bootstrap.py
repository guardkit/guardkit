"""
Environment bootstrap for AutoBuild feature orchestration.

Detects dependency manifests in a worktree and runs the appropriate install
commands before agents execute. This prevents ModuleNotFoundError failures
in Wave 2+ when Wave 1 creates project files (e.g. pyproject.toml) that have
never been installed.

Known Limitation:
    Scanning is limited to root and depth-1 subdirectories. Deeper monorepo
    structures (e.g. packages/backend/api/pyproject.toml) are not detected.
    This is acceptable for v1 and can be extended in a future task.

Architecture:
    Two-class design:
    1. ProjectEnvironmentDetector — discovers dependency manifests
    2. EnvironmentBootstrapper — runs install commands with content-hash dedup

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.environment_bootstrap import (
    ...     ProjectEnvironmentDetector,
    ...     EnvironmentBootstrapper,
    ... )
    >>>
    >>> detector = ProjectEnvironmentDetector(root=Path("/worktree"))
    >>> manifests = detector.detect()
    >>> bootstrapper = EnvironmentBootstrapper(root=Path("/worktree"))
    >>> result = bootstrapper.bootstrap(manifests)
    >>> print(result.success, result.stacks_detected)
    True ['python']
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PEP668_SENTINEL = "externally-managed-environment"

# uv emits this stderr fragment when ``uv pip install`` is invoked outside an
# active venv and no ``.venv`` is discoverable. The literal lives in uv's
# source as ``"No virtual environment found"`` and is the substring we match
# on; the trailing "; run `uv venv` ..." advice text is not stable enough to
# include in a sentinel.
#
# Triggered by the ``[tool.uv.sources]``-present + ``uv on PATH``-yes row of
# the install matrix above. ``_run_install`` detects this stderr, calls
# ``_ensure_uv_venv`` to create a worktree-local ``.venv``, and retries the
# original ``uv pip install`` with ``VIRTUAL_ENV`` and ``PATH`` exported. See
# :meth:`EnvironmentBootstrapper._run_install` for the retry block.
UV_NO_VENV_SENTINEL = "No virtual environment found"

# Truncate stderr excerpts attached to failure-detail records. Full stderr is
# still logged at WARNING by the install helpers — this cap only bounds what
# rides along on the in-memory BootstrapResult (e.g. for error messages).
_STDERR_EXCERPT_MAX_CHARS = 2000


def _tail_excerpt(stderr: Optional[str], max_chars: int = _STDERR_EXCERPT_MAX_CHARS) -> str:
    """Return the trailing ``max_chars`` of ``stderr``, or an empty string."""
    if not stderr:
        return ""
    stripped = stderr.strip()
    if len(stripped) <= max_chars:
        return stripped
    return "…" + stripped[-max_chars:]


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class DetectedManifest:
    """
    A dependency manifest file found in the worktree.

    Attributes
    ----------
    path : Path
        Absolute path to the manifest file.
    stack : str
        Technology stack identifier: "python", "node", "dotnet", "go",
        "rust", or "flutter".
    is_lock_file : bool
        True when the manifest is a lock file (e.g. poetry.lock,
        pnpm-lock.yaml).  Lock files take priority over non-lock manifests
        for the same (directory, stack) pair.
    install_command : List[str]
        argv list for the install command, suitable for subprocess.run().
    """

    path: Path
    stack: str
    is_lock_file: bool
    install_command: List[str]

    # ---- Completeness detection ----------------------------------------

    def is_project_complete(self) -> bool:
        """
        Return True if the project source tree is complete enough for a full install.

        When False, use ``get_dependency_install_commands()`` to install declared
        dependencies individually instead of running ``install_command``.

        Per-stack logic:

        - python / pyproject.toml: checks for a source directory that matches the
          ``[project].name`` in a flat or ``src/`` layout.
        - python / poetry.lock, requirements.txt: always True.
        - node / package.json: checks that the ``main`` or ``module`` entry point
          file exists.
        - node / lock files: always True.
        - dotnet, go: always True (restore/download work without source).
        - rust: True when ``src/`` directory exists.
        - flutter: True when ``lib/`` directory exists.
        """
        parent = self.path.parent

        if self.stack == "python":
            if self.path.name == "pyproject.toml":
                return self._python_pyproject_is_complete(parent)
            return True  # poetry.lock / requirements.txt: no source-dir concept

        if self.stack == "node":
            if self.path.name == "package.json":
                return self._node_package_is_complete(parent)
            return True  # lock files: assume complete

        if self.stack == "rust":
            return (parent / "src").is_dir()

        if self.stack == "flutter":
            return (parent / "lib").is_dir()

        # dotnet, go: restore / download work without source
        return True

    def get_dependency_install_commands(self) -> Optional[List[List[str]]]:
        """
        Return per-dependency install commands for incomplete projects.

        For stacks where the build tool works without source code (dotnet, go,
        rust, flutter) the standard restore command is returned wrapped in a list.
        For Python (pyproject.toml) and Node (package.json) the manifest is parsed
        and one command per declared dependency is returned.

        Returns ``None`` when no dependency-level install is applicable (e.g.
        lock files, or manifests with no declared dependencies).
        """
        if self.stack == "python":
            if self.path.name == "pyproject.toml":
                return self._python_dep_commands()
            return None  # poetry.lock / requirements.txt: not applicable

        if self.stack == "node":
            if self.path.name == "package.json":
                return self._node_dep_commands()
            return None  # lock files: not applicable

        if self.stack == "dotnet":
            return [["dotnet", "restore"]]

        if self.stack == "go":
            return [["go", "mod", "download"]]

        if self.stack == "rust":
            return [["cargo", "fetch"]]

        if self.stack == "flutter":
            return [["flutter", "pub", "get"]]

        return None

    # ---- Private helpers -----------------------------------------------

    def _python_pyproject_is_complete(self, directory: Path) -> bool:
        """Check whether the Python project source directory exists."""
        try:
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib  # type: ignore[import,no-redef]
            data = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug(
                "Could not parse %s for completeness check: %s", self.path, exc
            )
            return True  # Conservative: assume complete on parse failure

        project_name: str = data.get("project", {}).get("name", "")
        if not project_name:
            return True  # No name declared; assume complete

        # PEP 427: normalise hyphens to underscores for import name
        import_name = project_name.replace("-", "_")

        # Flat layout: {name}/ at project root
        if (directory / import_name).is_dir():
            return True
        # src layout: src/{name}/
        if (directory / "src" / import_name).is_dir():
            return True

        return False

    def _node_package_is_complete(self, directory: Path) -> bool:
        """Check whether the Node project's declared entry point exists."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug(
                "Could not parse %s for completeness check: %s", self.path, exc
            )
            return True  # Conservative: assume complete on parse failure

        entry: Optional[str] = data.get("main") or data.get("module")
        if not entry:
            return True  # No entry point declared; assume complete

        return (directory / entry).exists()

    def _python_dep_commands(self) -> Optional[List[List[str]]]:
        """Parse [project.dependencies] from pyproject.toml for per-dep installs."""
        try:
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib  # type: ignore[import,no-redef]
            data = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(
                "Could not parse %s for dependency extraction: %s", self.path, exc
            )
            return None

        deps: List[str] = data.get("project", {}).get("dependencies", [])
        if not deps:
            return None

        # Pass the full PEP 508 string to pip; pip handles version resolution.
        return [[sys.executable, "-m", "pip", "install", dep] for dep in deps]

    def _node_dep_commands(self) -> Optional[List[List[str]]]:
        """Parse dependencies from package.json for per-dep installs."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(
                "Could not parse %s for dependency extraction: %s", self.path, exc
            )
            return None

        deps: dict = data.get("dependencies", {})
        if not deps:
            return None

        return [["npm", "install", name] for name in deps]

    def get_requires_python(self) -> Optional[str]:
        """
        Return the ``requires-python`` constraint for this manifest, or None.

        Checks, in order:
          1. PEP 621 ``[project].requires-python`` (standard modern layout)
          2. Poetry ``[tool.poetry].python`` (legacy Poetry layout)

        Only Python pyproject.toml manifests declare this; other stacks and
        requirements.txt / poetry.lock return None. Parse errors are swallowed
        (None returned) — this feeds both failure diagnostics and the pre-pip
        requires-python gate (TASK-REV-JMBP Workstream E).
        """
        if self.stack != "python" or self.path.name != "pyproject.toml":
            return None
        try:
            try:
                import tomllib  # Python 3.11+
            except ImportError:
                import tomli as tomllib  # type: ignore[import,no-redef]
            data = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None

        value = data.get("project", {}).get("requires-python")
        if isinstance(value, str) and value.strip():
            return value

        # Poetry legacy layout: [tool.poetry] python = ">=3.9,<4.0"
        poetry_value = data.get("tool", {}).get("poetry", {}).get("python")
        if isinstance(poetry_value, str) and poetry_value.strip():
            return poetry_value

        return None


@dataclass
class BootstrapFailureDetail:
    """
    Per-install failure metadata surfaced on ``BootstrapResult.failure_details``.

    Captured for each failing install so callers (e.g. the feature-orchestrator
    hard-fail gate) can render an actionable error message naming the exact
    interpreter / manifest mismatch rather than a generic ``0/N succeeded`` line.

    Attributes
    ----------
    stack : str
        Stack identifier (``python``, ``node``, …).
    manifest_path : str
        Absolute path of the manifest whose install failed.
    stderr_excerpt : str
        Trailing stderr excerpt from the failed install command (truncated to a
        readable length — callers should not assume the full stderr is present).
    is_pep668 : bool
        True when the stderr matches the PEP 668 ``externally-managed-environment``
        sentinel. The gate uses this to distinguish interpreter-constraint
        failures from generic install failures.
    requires_python : Optional[str]
        ``requires-python`` constraint (e.g. ``>=3.13``) extracted from the
        manifest when available (Python stack only, via ``pyproject.toml``).
        None for other stacks or when the manifest does not declare one.
    essential : bool
        True when this failure counted toward ``installs_failed`` (i.e. the
        stack was considered essential at bootstrap time). False when the
        failure was filtered into ``non_relevant_failures``.
    """

    stack: str
    manifest_path: str
    stderr_excerpt: str
    is_pep668: bool = False
    requires_python: Optional[str] = None
    essential: bool = True


@dataclass
class BootstrapResult:
    """
    Result of a bootstrap operation.

    Attributes
    ----------
    success : bool
        True if all attempted installs succeeded (or were skipped).
    skipped : bool
        True if content hash matched saved state and installs were deduped.
    stacks_detected : List[str]
        Sorted list of stack identifiers for detected manifests.
    manifests_found : List[str]
        Absolute path strings of all detected manifests.
    installs_attempted : int
        Number of install commands executed.
    installs_failed : int
        Number of install commands that failed (essential stacks only).
    error : Optional[str]
        Human-readable error message when success is False, else None.
    duration_seconds : float
        Wall-clock duration of the bootstrap operation in seconds.
    non_relevant_failures : int
        Count of failures from non-relevant stacks (non-blocking).
    skipped_stacks : List[str]
        Stacks that were skipped or had non-blocking failures.
    failure_details : List[BootstrapFailureDetail]
        Per-install failure metadata (stack, manifest, stderr excerpt,
        PEP-668 flag, requires-python). Populated for both essential and
        non-relevant failures; ``essential=True`` entries are the ones that
        drove ``installs_failed``.
    """

    success: bool
    skipped: bool
    stacks_detected: List[str]
    manifests_found: List[str]
    installs_attempted: int = 0
    installs_failed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    venv_python: Optional[str] = None
    non_relevant_failures: int = 0
    skipped_stacks: List[str] = field(default_factory=list)
    failure_details: List[BootstrapFailureDetail] = field(default_factory=list)


# ============================================================================
# uv-sources detection (TASK-FIX-F09A2)
# ============================================================================
#
# When a Python project's pyproject.toml declares ``[tool.uv.sources]`` (uv's
# sibling-source override mechanism), plain ``pip install -e .`` does NOT
# honour those overrides — only ``uv`` itself does. The forge / jarvis layout
# (a sibling-source pin to a private wheel) is the canonical case. The
# detection here teaches the bootstrap to prefer the right install command
# instead of leaving every consuming repo to ship its own preflight script.
#
# Behaviour matrix (applied to a directory with pyproject.toml):
#
#   pyproject [tool.uv.sources] | uv.lock | uv on PATH | install command
#   ----------------------------|---------|------------|------------------
#   absent                      | absent  | any        | pip install -e .  (unchanged)
#   absent                      | present | yes        | uv sync --frozen
#   absent                      | present | no         | pip install -e .  (+ warn)
#   present                     | any     | yes        | uv pip install -e .  [1][2]
#   present                     | any     | no         | HARD-FAIL (UvSourcesRequireUvError)
#
# [1] ``uv pip install`` requires either an active venv or ``--system``. When
#     this row fires and the worktree has neither an active ``$VIRTUAL_ENV``
#     nor a discoverable ``.venv`` in cwd, uv exits with stderr "No virtual
#     environment found" before any wheels are pulled. The bootstrapper
#     detects this sentinel (see :data:`UV_NO_VENV_SENTINEL`) inside
#     :meth:`EnvironmentBootstrapper._run_install`, calls ``uv venv`` to
#     create ``<cwd>/.venv`` (where uv looks first), and retries the
#     original command with ``VIRTUAL_ENV`` and ``PATH`` exported. The
#     retry is single-shot per bootstrap pass — if it still fails, the
#     hard-fail gate (TASK-FIX-7A04) surfaces the failure as usual.
#     ``--system`` is intentionally avoided: it writes to the host Python
#     and on managed Pythons would re-trigger PEP 668. (TASK-FIX-AB60)
#
# [2] For this row, guardkit pre-creates symlinks at worktree-relative
#     paths for any ``[tool.uv.sources]`` entries with ``path = "..."``
#     that point outside the worktree's own checkout. uv resolves
#     path-typed sources relative to the pyproject's directory, so a
#     sibling pin like ``foo = { path = "../foo" }`` resolves to a
#     different filesystem location from a worktree at
#     ``.guardkit/worktrees/<feat>/`` than from the source repo root.
#     The symlink bridges the two. See
#     :func:`_resolve_uv_sources_symlinks` and
#     :func:`_create_worktree_uv_sources_symlinks`, plumbed from
#     :meth:`FeatureOrchestrator._create_new_worktree`. This makes
#     sibling-source overrides work transparently from worktrees without
#     requiring per-repo preflight scripts. (TASK-FIX-AB61)


class UvSourcesRequireUvError(RuntimeError):
    """
    Raised at detection time when a pyproject.toml declares
    ``[tool.uv.sources]`` but ``uv`` is not on PATH.

    Plain pip cannot honour the sibling-source overrides, so installing would
    silently produce a broken environment. The orchestrator catches this and
    surfaces it as a hard-fail before any pip work runs.
    """


def _uv_on_path() -> bool:
    """Return True when ``uv`` is resolvable via PATH."""
    return shutil.which("uv") is not None


def _pyproject_has_uv_sources(pyproject_path: Path) -> bool:
    """
    Return True when ``pyproject_path`` declares a ``[tool.uv.sources]`` table.

    Parse failures are swallowed (returns False) — the existing
    ``_python_pyproject_is_complete`` helper takes the same conservative
    stance, and a malformed pyproject is pip's problem to surface, not
    detection's.
    """
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[import,no-redef]
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug(
            "Could not parse %s for uv-sources detection: %s", pyproject_path, exc
        )
        return False
    sources = data.get("tool", {}).get("uv", {}).get("sources")
    return isinstance(sources, dict) and bool(sources)


def _resolve_uv_sources_symlinks(
    source_pyproject_path: Path,
    worktree_pyproject_path: Path,
) -> List[tuple[Path, Path]]:
    """
    Compute worktree symlinks needed to bridge ``[tool.uv.sources]`` paths
    between a source repo and its worktree checkout (TASK-FIX-AB61).

    uv resolves a path-typed source entry relative to the *pyproject's own
    directory*. When the worktree pyproject lives at a different filesystem
    location than the source pyproject, a sibling pin like
    ``foo = { path = "../foo" }`` resolves to two different absolute paths.
    This helper returns the ``(symlink_path, target_path)`` pairs that the
    orchestrator should pre-create so uv finds the same files from the
    worktree as it would from the source repo.

    Parameters
    ----------
    source_pyproject_path : Path
        Path to the source repo's ``pyproject.toml``.
    worktree_pyproject_path : Path
        Path to the worktree checkout's ``pyproject.toml``. Typically a
        descendant of ``<source>/.guardkit/worktrees/<feat>/``.

    Returns
    -------
    list[tuple[Path, Path]]
        Each tuple is ``(symlink_path, target_path)`` where
        ``symlink_path`` is where uv WILL look from the worktree, and
        ``target_path`` is where the file actually lives. Both are
        absolute, ``.resolve()``-d paths. Empty list when no
        ``[tool.uv.sources]`` table is present, when all entries are
        non-path-typed (``git``, ``index``, ``workspace``, ``url``), or
        when every path-typed entry already lives inside the worktree's
        own checkout.

    Notes
    -----
    Entries whose ``source_resolved`` does not exist are skipped with a
    warning rather than emitted — letting the bootstrap surface uv's own
    "Distribution not found" error is more informative than mocking up a
    broken symlink.
    """
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[import,no-redef]
        data = tomllib.loads(source_pyproject_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug(
            "Could not parse %s for uv-sources symlink resolution: %s",
            source_pyproject_path,
            exc,
        )
        return []

    sources = data.get("tool", {}).get("uv", {}).get("sources")
    if not isinstance(sources, dict) or not sources:
        return []

    source_dir = source_pyproject_path.parent
    worktree_dir = worktree_pyproject_path.parent

    symlinks: List[tuple[Path, Path]] = []
    for key, entry in sources.items():
        if not isinstance(entry, dict):
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            # Non-path-typed entries (git, index, workspace, url) need no
            # symlink. They're out of scope for AB61.
            continue

        worktree_resolved = (worktree_dir / path_value).resolve()
        source_resolved = (source_dir / path_value).resolve()

        if worktree_resolved == source_resolved:
            # Path points inside the worktree's own checkout — uv finds it
            # without help.
            continue

        if not source_resolved.exists():
            logger.warning(
                "uv-sources entry '%s' in %s points to %s which does not "
                "exist; skipping symlink creation. uv will surface its own "
                "'Distribution not found' error.",
                key,
                source_pyproject_path,
                source_resolved,
            )
            continue

        symlinks.append((worktree_resolved, source_resolved))

    return symlinks


def _create_worktree_uv_sources_symlinks(
    symlinks: List[tuple[Path, Path]],
) -> None:
    """
    Create the worktree symlinks computed by
    :func:`_resolve_uv_sources_symlinks` (TASK-FIX-AB61).

    Idempotent:

    * If the symlink path is already a symlink pointing at the correct
      target, leave it alone.
    * If the symlink path is a symlink pointing elsewhere, replace it.
    * If a non-symlink (real file or directory) already exists at the
      symlink path, log a warning and skip — the consuming repo may have
      a real directory there for another reason and silent overwrite
      would be destructive.

    Parameters
    ----------
    symlinks : list[tuple[Path, Path]]
        ``(symlink_path, target_path)`` pairs as returned by
        :func:`_resolve_uv_sources_symlinks`. Both paths must be
        absolute. Empty list is a no-op.

    Raises
    ------
    OSError
        If symlink creation itself fails (permission denied, target
        unreadable, parent directory creation failed). The caller is
        responsible for surfacing this with a hint that names the
        symlink path, target, and OS error — and that does NOT point at
        ``bootstrap_failure_mode: warn`` (mirrors the AB60 hint pattern).
    """
    for symlink_path, target_path in symlinks:
        if symlink_path.is_symlink():
            try:
                current = Path(os.readlink(symlink_path))
            except OSError as exc:
                logger.warning(
                    "Could not read existing symlink at %s: %s; replacing.",
                    symlink_path,
                    exc,
                )
                current = None
            if current is not None and current == target_path:
                logger.debug(
                    "uv-sources symlink already correct: %s -> %s",
                    symlink_path,
                    target_path,
                )
                continue
            symlink_path.unlink()
        elif symlink_path.exists():
            logger.warning(
                "Path %s exists and is not a symlink; skipping uv-sources "
                "symlink creation. Remove or relocate it to enable "
                "transparent sibling-source resolution from this worktree.",
                symlink_path,
            )
            continue

        symlink_path.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target_path, symlink_path)
        logger.debug(
            "Created uv-sources symlink: %s -> %s",
            symlink_path,
            target_path,
        )


def _resolve_python_pyproject_install_command(
    directory: Path, pyproject_path: Path
) -> List[str]:
    """
    Choose the install command for a Python ``pyproject.toml`` manifest.

    Implements the matrix at the top of this section. The ``uv.lock`` /
    no-uv-on-path row emits a warning so operators know they're falling
    back to pip when a uv lockfile was available.

    Raises
    ------
    UvSourcesRequireUvError
        When pyproject declares ``[tool.uv.sources]`` and ``uv`` is missing
        from PATH. The error message names the file and lists the two
        actionable fixes (install uv, or remove the block).
    """
    has_uv_sources = _pyproject_has_uv_sources(pyproject_path)
    has_uv_lock = (directory / "uv.lock").exists()
    uv_available = _uv_on_path()

    if has_uv_sources and not uv_available:
        raise UvSourcesRequireUvError(
            f"{pyproject_path} declares [tool.uv.sources] but `uv` is not on PATH. "
            "pip cannot honour these sibling-source overrides — installing "
            "would silently produce a broken environment. "
            "Fix by installing uv (https://astral.sh/uv) or removing the "
            "[tool.uv.sources] block from pyproject.toml."
        )

    if has_uv_sources:
        return ["uv", "pip", "install", "-e", "."]

    if has_uv_lock and uv_available:
        # `uv sync --frozen` is project-aware (reads pyproject.toml + uv.lock)
        # and `--frozen` guarantees the orchestrator never silently re-locks.
        # `uv pip sync` only accepts requirements.txt / pylock.toml — it
        # cannot parse uv's native `uv.lock` format. (TASK-FIX-FD32)
        return ["uv", "sync", "--frozen"]

    if has_uv_lock and not uv_available:
        logger.warning(
            "%s/uv.lock present but `uv` is not on PATH — falling back to "
            "`pip install -e .`. Install uv (https://astral.sh/uv) for full "
            "lockfile fidelity.",
            directory,
        )

    return [sys.executable, "-m", "pip", "install", "-e", "."]


# ============================================================================
# ProjectEnvironmentDetector
# ============================================================================


class ProjectEnvironmentDetector:
    """
    Scans a worktree for dependency manifests and produces install commands.

    Detection rules per directory
    -----------------------------
    Lock files are always preferred over non-lock manifests for the same
    (directory, stack) combination.  The full priority order within a
    directory is:

    Python:
      1. poetry.lock      → pip install -e .
      2. pyproject.toml   → pip install -e .
      3. requirements.txt → pip install -r requirements.txt

    Node:
      4. pnpm-lock.yaml   → pnpm install --frozen-lockfile
      5. yarn.lock        → yarn install --frozen-lockfile
      6. package-lock.json→ npm ci
      7. package.json     → npm install

    .NET:
      8. *.csproj (glob)  → dotnet restore
      9. *.sln   (glob)   → dotnet restore

    Go:
     10. go.mod           → go mod download

    Rust:
     11. Cargo.toml       → cargo fetch

    Flutter:
     12. pubspec.yaml     → flutter pub get

    Attributes
    ----------
    root : Path
        Absolute path to the worktree root.

    Examples
    --------
    >>> detector = ProjectEnvironmentDetector(root=Path("/worktree"))
    >>> manifests = detector.detect()
    >>> for m in manifests:
    ...     print(m.stack, m.path.name)
    python pyproject.toml
    """

    def __init__(
        self,
        root: Path,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the detector.

        Parameters
        ----------
        root : Path
            Absolute path to the worktree root directory.
        exclude_patterns : Optional[List[str]], optional
            Directory path patterns to exclude from scanning (relative to
            root). Any subdirectory whose path relative to root starts with
            one of these patterns is skipped. Defaults to
            ``["tests/fixtures"]``.
        """
        self._root = root
        self._exclude_patterns: List[str] = (
            exclude_patterns if exclude_patterns is not None else ["tests/fixtures"]
        )

    def detect(self) -> List[DetectedManifest]:
        """
        Scan root and depth-1 subdirectories for dependency manifests.

        Returns
        -------
        List[DetectedManifest]
            Detected manifests ordered by (directory, stack, priority).
            At most one manifest is returned per (directory, stack) pair —
            lock files suppress non-lock manifests for the same pair.
        """
        results: List[DetectedManifest] = []
        for directory in self._scan_dirs():
            results.extend(self._scan_directory(directory))
        logger.debug(
            "ProjectEnvironmentDetector found %d manifest(s) in %s",
            len(results),
            self._root,
        )
        return results

    def _scan_dirs(self) -> List[Path]:
        """
        Return directories to scan: root plus immediate non-hidden subdirs.

        Directories whose path relative to root starts with any pattern in
        ``self._exclude_patterns`` are omitted.

        Returns
        -------
        List[Path]
            [root] + immediate subdirectories (hidden and excluded dirs omitted).
        """
        dirs: List[Path] = [self._root]
        try:
            for entry in sorted(self._root.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                try:
                    rel = entry.relative_to(self._root).as_posix()
                except ValueError:
                    rel = entry.name
                if any(rel.startswith(pattern) for pattern in self._exclude_patterns):
                    logger.debug(
                        "Skipping excluded directory: %s (matches exclude pattern)", entry
                    )
                    continue
                dirs.append(entry)
        except OSError as exc:
            logger.warning("Could not list subdirectories of %s: %s", self._root, exc)
        return dirs

    def _scan_directory(self, directory: Path) -> List[DetectedManifest]:
        """
        Scan a single directory and return detected manifests.

        Uses a set of (directory, stack) pairs already satisfied by a lock
        file to suppress lower-priority non-lock manifests for the same
        (directory, stack).

        Parameters
        ----------
        directory : Path
            Directory to scan.

        Returns
        -------
        List[DetectedManifest]
            Detected manifests for this directory, at most one per stack.
        """
        results: List[DetectedManifest] = []
        # Track (directory, stack) pairs where a lock file was already found
        locked_stacks: set[str] = set()

        # Detection candidates in priority order: (filename_or_glob, stack,
        # is_lock, install_command_factory)
        # Each entry is checked in sequence; lock files register the stack
        # to block lower-priority non-lock entries for the same stack.

        # ---- Python ----
        if (directory / "poetry.lock").exists():
            results.append(
                DetectedManifest(
                    path=(directory / "poetry.lock").resolve(),
                    stack="python",
                    is_lock_file=True,
                    install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
                )
            )
            locked_stacks.add("python")

        if (directory / "pyproject.toml").exists() and "python" not in locked_stacks:
            pyproject_path = (directory / "pyproject.toml").resolve()
            install_command = _resolve_python_pyproject_install_command(
                directory, pyproject_path
            )
            results.append(
                DetectedManifest(
                    path=pyproject_path,
                    stack="python",
                    is_lock_file=False,
                    install_command=install_command,
                )
            )
            locked_stacks.add("python")  # prevent requirements.txt from also running

        if (directory / "requirements.txt").exists() and "python" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "requirements.txt").resolve(),
                    stack="python",
                    is_lock_file=False,
                    install_command=[
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        "requirements.txt",
                    ],
                )
            )
            locked_stacks.add("python")

        # ---- Node ----
        if (directory / "pnpm-lock.yaml").exists():
            results.append(
                DetectedManifest(
                    path=(directory / "pnpm-lock.yaml").resolve(),
                    stack="node",
                    is_lock_file=True,
                    install_command=["pnpm", "install", "--frozen-lockfile"],
                )
            )
            locked_stacks.add("node")

        if (directory / "yarn.lock").exists() and "node" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "yarn.lock").resolve(),
                    stack="node",
                    is_lock_file=True,
                    install_command=["yarn", "install", "--frozen-lockfile"],
                )
            )
            locked_stacks.add("node")

        if (directory / "package-lock.json").exists() and "node" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "package-lock.json").resolve(),
                    stack="node",
                    is_lock_file=True,
                    install_command=["npm", "ci"],
                )
            )
            locked_stacks.add("node")

        if (directory / "package.json").exists() and "node" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "package.json").resolve(),
                    stack="node",
                    is_lock_file=False,
                    install_command=["npm", "install"],
                )
            )
            locked_stacks.add("node")

        # ---- .NET ----
        csproj_files = list(directory.glob("*.csproj"))
        if csproj_files and "dotnet" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=csproj_files[0].resolve(),
                    stack="dotnet",
                    is_lock_file=False,
                    install_command=["dotnet", "restore"],
                )
            )
            locked_stacks.add("dotnet")

        sln_files = list(directory.glob("*.sln"))
        if sln_files and "dotnet" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=sln_files[0].resolve(),
                    stack="dotnet",
                    is_lock_file=False,
                    install_command=["dotnet", "restore"],
                )
            )
            locked_stacks.add("dotnet")

        # ---- Go ----
        if (directory / "go.mod").exists() and "go" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "go.mod").resolve(),
                    stack="go",
                    is_lock_file=False,
                    install_command=["go", "mod", "download"],
                )
            )
            locked_stacks.add("go")

        # ---- Rust ----
        if (directory / "Cargo.toml").exists() and "rust" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "Cargo.toml").resolve(),
                    stack="rust",
                    is_lock_file=False,
                    install_command=["cargo", "fetch"],
                )
            )
            locked_stacks.add("rust")

        # ---- Flutter ----
        if (directory / "pubspec.yaml").exists() and "flutter" not in locked_stacks:
            results.append(
                DetectedManifest(
                    path=(directory / "pubspec.yaml").resolve(),
                    stack="flutter",
                    is_lock_file=False,
                    install_command=["flutter", "pub", "get"],
                )
            )
            locked_stacks.add("flutter")

        return results


# ============================================================================
# EnvironmentBootstrapper
# ============================================================================


class EnvironmentBootstrapper:
    """
    Installs project dependencies found by ProjectEnvironmentDetector.

    Deduplication is performed via a SHA-256 content hash of all manifest
    files. When the hash matches the previously saved state the bootstrap
    is skipped, making the operation idempotent across multiple calls for
    the same worktree state.

    State is persisted in ``<root>/.guardkit/bootstrap_state.json``.

    Attributes
    ----------
    _root : Path
        Worktree root path.
    _state_file : Path
        Path to the JSON state file used for hash-based dedup.

    Examples
    --------
    >>> bootstrapper = EnvironmentBootstrapper(root=Path("/worktree"))
    >>> result = bootstrapper.bootstrap(manifests)
    >>> print(result.skipped)
    False
    """

    def __init__(
        self,
        root: Path,
        state_file: Optional[Path] = None,
        retry_cooldown_seconds: int = 60,
    ) -> None:
        """
        Initialize the bootstrapper.

        Parameters
        ----------
        root : Path
            Absolute path to the worktree root.
        state_file : Optional[Path], optional
            Override path for the state JSON file.  Defaults to
            ``<root>/.guardkit/bootstrap_state.json``.
        retry_cooldown_seconds : int, optional
            Seconds to wait before retrying a previously failed install with
            the same content hash.  Defaults to 60.
        """
        self._root = root
        self._state_file = state_file or (root / ".guardkit" / "bootstrap_state.json")
        self._retry_cooldown_seconds = retry_cooldown_seconds
        self._venv_python: Optional[Path] = None
        # Per-bootstrap cache for the worktree-local venv created when the
        # ``[tool.uv.sources]``-present matrix row hits uv's "No virtual
        # environment found" stderr. Distinct from ``_venv_python`` (which
        # lives at ``<root>/.guardkit/venv/`` for the PEP 668 path) — the
        # uv-venv lives at ``<cwd>/.venv`` (where uv discovers it natively)
        # and is created only on retry, not preserved across bootstrap runs.
        self._uv_venv_python: Optional[Path] = None
        # Diagnostics captured by _run_install / _run_single_command for the
        # MOST RECENT call only — consumed by bootstrap() to populate
        # BootstrapResult.failure_details. Kept as private scratch state so
        # the helpers can retain their bool return type (and existing tests
        # that assert ``is True`` / ``is False`` don't regress).
        self._last_failure_stderr: str = ""
        self._last_failure_is_pep668: bool = False

    def bootstrap(
        self,
        manifests: List[DetectedManifest],
        relevant_stacks: Optional[List[str]] = None,
    ) -> BootstrapResult:
        """
        Install dependencies for the given manifests.

        The operation is idempotent: if the combined content hash of all
        manifests matches the saved state the function returns immediately
        with ``skipped=True``.

        Parameters
        ----------
        manifests : List[DetectedManifest]
            Manifests returned by ProjectEnvironmentDetector.detect().
        relevant_stacks : Optional[List[str]], optional
            When provided, only manifests whose stack is in this list are
            treated as essential. Failures from non-relevant stacks are
            logged at WARNING level and counted in
            ``BootstrapResult.non_relevant_failures`` rather than
            ``installs_failed``, so they do not affect ``success``.
            Defaults to None (all stacks are treated as essential).

        Returns
        -------
        BootstrapResult
            Result describing what was done, skipped, or failed.
        """
        start_time = time.monotonic()

        if not manifests:
            return BootstrapResult(
                success=True,
                skipped=False,
                stacks_detected=[],
                manifests_found=[],
                duration_seconds=time.monotonic() - start_time,
            )

        # Build result metadata
        stacks_detected = sorted(set(m.stack for m in manifests))
        manifests_found = [str(m.path) for m in manifests]

        # Hash-based deduplication with outcome awareness
        content_hash = self._compute_hash(manifests)
        if self._should_skip(content_hash):
            logger.debug(
                "Bootstrap skipped: hash %s matches saved state", content_hash[:8]
            )
            saved = self._load_state()
            return BootstrapResult(
                success=True,
                skipped=True,
                stacks_detected=stacks_detected,
                manifests_found=manifests_found,
                venv_python=saved.get("venv_python"),
                duration_seconds=time.monotonic() - start_time,
            )

        # Recover venv from previous run if available
        saved = self._load_state()
        saved_venv = saved.get("venv_python")
        if saved_venv and Path(saved_venv).exists():
            self._venv_python = Path(saved_venv)
            logger.info(
                "PEP 668: reusing virtualenv from previous run at %s",
                self._venv_python,
            )

        # Run install commands
        installs_attempted = 0
        installs_failed = 0
        non_relevant_failures = 0
        skipped_stacks: List[str] = []
        failure_details: List[BootstrapFailureDetail] = []

        def _record_failure(manifest: DetectedManifest, essential: bool) -> None:
            failure_details.append(
                BootstrapFailureDetail(
                    stack=manifest.stack,
                    manifest_path=str(manifest.path),
                    stderr_excerpt=self._last_failure_stderr,
                    is_pep668=self._last_failure_is_pep668,
                    requires_python=manifest.get_requires_python(),
                    essential=essential,
                )
            )

        for manifest in manifests:
            is_essential = (
                relevant_stacks is None or manifest.stack in relevant_stacks
            )

            if manifest.is_project_complete():
                # Full project install (standard path)
                installs_attempted += 1
                success = self._run_install(manifest)
                if not success:
                    _record_failure(manifest, is_essential)
                    if is_essential:
                        installs_failed += 1
                    else:
                        non_relevant_failures += 1
                        if manifest.stack not in skipped_stacks:
                            skipped_stacks.append(manifest.stack)
                        logger.warning(
                            "Non-relevant stack install failed for %s (%s) — "
                            "not counted as blocking failure",
                            manifest.stack,
                            manifest.path.name,
                        )
            else:
                # Incomplete project: install declared dependencies individually
                dep_commands = manifest.get_dependency_install_commands()
                if dep_commands:
                    for cmd in dep_commands:
                        installs_attempted += 1
                        success = self._run_single_command(cmd, manifest.path.parent)
                        if not success:
                            _record_failure(manifest, is_essential)
                            if is_essential:
                                installs_failed += 1
                            else:
                                non_relevant_failures += 1
                                if manifest.stack not in skipped_stacks:
                                    skipped_stacks.append(manifest.stack)
                                logger.warning(
                                    "Non-relevant stack dep-install failed for %s (%s) — "
                                    "not counted as blocking failure",
                                    manifest.stack,
                                    manifest.path.name,
                                )
                else:
                    logger.warning(
                        "Incomplete project at %s (%s): no dependency install available",
                        manifest.path,
                        manifest.stack,
                    )

        duration = time.monotonic() - start_time
        overall_success = installs_failed == 0

        # TASK-SGER-002: always expose the active interpreter on successful
        # Python bootstrap. The PEP 668 and uv-no-venv fallback paths set
        # ``self._venv_python`` / ``self._uv_venv_python`` in their own retry
        # blocks. The macOS happy path (``uv pip install`` succeeds first try
        # against the orchestrator's parent shell venv) hits neither — the
        # install IS effective (sys.executable has the package), but no
        # fallback ran, so ``self._venv_python`` stays ``None`` and the
        # downstream smoke gate inherits unchanged PATH (FEAT-61F1 failure
        # shape). Capturing ``sys.executable`` here makes the contract
        # uniform: every successful Python bootstrap exposes its interpreter.
        if (
            overall_success
            and self._venv_python is None
            and any(m.stack == "python" for m in manifests)
        ):
            self._venv_python = Path(sys.executable)
            logger.info(
                "Bootstrap: install ran against parent venv; venv_python "
                "set to sys.executable=%s",
                sys.executable,
            )

        # Persist state hash with outcome so failed attempts can be retried
        self._save_state(content_hash, success=overall_success)

        return BootstrapResult(
            success=overall_success,
            skipped=False,
            stacks_detected=stacks_detected,
            manifests_found=manifests_found,
            installs_attempted=installs_attempted,
            installs_failed=installs_failed,
            error=(
                f"{installs_failed}/{installs_attempted} install(s) failed"
                if not overall_success
                else None
            ),
            duration_seconds=duration,
            venv_python=str(self._venv_python) if self._venv_python else None,
            non_relevant_failures=non_relevant_failures,
            skipped_stacks=sorted(skipped_stacks),
            failure_details=failure_details,
        )

    def _compute_hash(self, manifests: List[DetectedManifest]) -> str:
        """
        Compute a SHA-256 hash of all manifest file contents.

        The hash is computed over the sorted manifest paths + their file
        contents, ensuring that changes to any file invalidate the cache.

        Parameters
        ----------
        manifests : List[DetectedManifest]
            Manifests to hash.

        Returns
        -------
        str
            Hex-encoded SHA-256 digest.
        """
        hasher = hashlib.sha256()
        for manifest in sorted(manifests, key=lambda m: str(m.path)):
            # Include the path itself so that adding/removing manifests changes
            # the hash even if file contents are identical.
            hasher.update(str(manifest.path).encode("utf-8"))
            try:
                hasher.update(manifest.path.read_bytes())
            except OSError as exc:
                logger.warning(
                    "Could not read manifest for hashing (%s): %s", manifest.path, exc
                )
        return hasher.hexdigest()

    def _should_skip(self, content_hash: str) -> bool:
        """
        Determine whether the bootstrap should be skipped for this content hash.

        Skip logic:
        - No saved state → run install.
        - Hash differs → run install (content changed).
        - Hash matches + previous success → skip (idempotent).
        - Hash matches + previous failure → retry after cooldown expires.

        Old state files without a ``success`` field are treated as successful
        for backward compatibility.

        Parameters
        ----------
        content_hash : str
            Hex-encoded SHA-256 digest of the current manifests.

        Returns
        -------
        bool
            True if the bootstrap should be skipped, False if it should run.
        """
        saved = self._load_state()
        if not saved:
            return False

        if saved.get("content_hash") != content_hash:
            return False

        # Hash matches — check outcome (default True for old-format backward compat)
        if saved.get("success", True):
            return True

        # Previous attempt failed with the same hash — retry after cooldown
        timestamp_str = saved.get("timestamp")
        if timestamp_str:
            try:
                last_attempt = datetime.fromisoformat(timestamp_str)
                elapsed = (datetime.now() - last_attempt).total_seconds()
                if elapsed < self._retry_cooldown_seconds:
                    logger.debug(
                        "Bootstrap skipped: previous failure within cooldown "
                        "(%.1fs / %ds)", elapsed, self._retry_cooldown_seconds
                    )
                    return True
            except (ValueError, TypeError) as exc:
                logger.debug("Could not parse state timestamp %r: %s", timestamp_str, exc)

        logger.debug(
            "Bootstrap retry: previous failure cooldown expired for hash %s",
            content_hash[:8],
        )
        return False

    def _load_state(self) -> Dict[str, str]:
        """
        Load the saved bootstrap state.

        Returns
        -------
        Dict[str, str]
            Parsed state dict, or empty dict when the file is missing or
            corrupt.
        """
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load bootstrap state from %s: %s", self._state_file, exc)
        return {}

    def _save_state(self, content_hash: str, success: bool) -> None:
        """
        Persist the content hash, outcome, and timestamp to the state file.

        Parameters
        ----------
        content_hash : str
            Hex-encoded SHA-256 digest to save.
        success : bool
            True if the install succeeded, False if it failed.
        """
        state: Dict[str, object] = {
            "content_hash": content_hash,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        if self._venv_python:
            state["venv_python"] = str(self._venv_python)
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps(state, indent=2),
                encoding="utf-8",
            )
            logger.debug("Saved bootstrap state to %s", self._state_file)
        except OSError as exc:
            logger.warning("Could not save bootstrap state to %s: %s", self._state_file, exc)

    def _is_pep668_error(self, stderr: str) -> bool:
        """
        Return True if *stderr* contains the PEP 668 sentinel.

        Parameters
        ----------
        stderr : str
            Standard error output from a failed pip command.
        """
        return PEP668_SENTINEL in stderr

    def _ensure_venv(self) -> Path:
        """
        Create a project-local virtualenv (if needed) and return the Python path.

        The venv is created at ``<root>/.guardkit/venv/``.  If the venv
        already exists on disk the existing Python is returned without
        recreating it.  The result is cached in ``self._venv_python``.

        Returns
        -------
        Path
            Absolute path to the venv Python interpreter.
        """
        if self._venv_python is not None:
            return self._venv_python

        venv_dir = self._root / ".guardkit" / "venv"
        venv_python = venv_dir / "bin" / "python"

        if not venv_python.exists():
            logger.info(
                "PEP 668: falling back to virtualenv at %s", venv_dir
            )
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_dir)],
                check=True,
            )
        else:
            logger.info(
                "PEP 668: reusing existing virtualenv at %s", venv_dir
            )

        self._venv_python = venv_python
        return self._venv_python

    def _is_uv_no_venv_error(self, stderr: str) -> bool:
        """
        Return True if *stderr* contains uv's "no venv discoverable" sentinel.

        Symmetric with :meth:`_is_pep668_error`. Triggered by ``uv pip
        install`` invocations against a project that declares
        ``[tool.uv.sources]`` but where neither ``$VIRTUAL_ENV`` is set
        nor ``<cwd>/.venv`` exists, on a uv version that requires an
        explicit environment for non-system installs.

        Parameters
        ----------
        stderr : str
            Standard error output from a failed ``uv pip install`` command.
        """
        return UV_NO_VENV_SENTINEL in stderr

    def _ensure_uv_venv(self, cwd: Path) -> Path:
        """
        Create a worktree-local venv at ``<cwd>/.venv`` (if needed).

        Distinct from :meth:`_ensure_venv`: the PEP 668 venv lives at
        ``<root>/.guardkit/venv/`` (a single shared interpreter for the
        bootstrap pass), whereas the uv-sources venv lives **inside the
        worktree** because uv discovers ``.venv`` relative to its cwd.
        Putting it under ``.guardkit/venv/`` would not be discovered.

        Idempotent — if ``.venv/bin/python`` already exists it is returned
        without re-creating. The path is also cached on
        ``self._uv_venv_python`` so a second ``uv pip install`` call inside
        the same bootstrap pass short-circuits.

        Parameters
        ----------
        cwd : Path
            Working directory of the failing ``uv pip install`` call —
            typically the manifest's parent directory.

        Returns
        -------
        Path
            Absolute path to the venv directory (``<cwd>/.venv``), suitable
            for export as ``VIRTUAL_ENV``. Callers that want the python
            interpreter should append ``/bin/python``.
        """
        if self._uv_venv_python is not None:
            return self._uv_venv_python.parent.parent

        venv_dir = cwd / ".venv"
        venv_python = venv_dir / "bin" / "python"

        if not venv_python.exists():
            logger.info(
                "uv-sources: creating worktree-local virtualenv at %s",
                venv_dir,
            )
            subprocess.run(
                ["uv", "venv", str(venv_dir)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
        else:
            logger.info(
                "uv-sources: reusing existing worktree-local virtualenv at %s",
                venv_dir,
            )

        self._uv_venv_python = venv_python
        return venv_dir

    def _run_install(self, manifest: DetectedManifest) -> bool:
        """
        Run the install command for a single manifest.

        The command is executed with the manifest's parent directory as the
        working directory so that relative paths in install commands (e.g.
        ``-r requirements.txt``) resolve correctly.

        On PEP 668 failure (``externally-managed-environment``), a project-
        local virtualenv is created and the command is retried with the venv
        Python.

        On uv "no virtual environment found" failure (the
        ``[tool.uv.sources]`` install matrix row when the worktree has no
        venv), a worktree-local ``.venv`` is created via ``uv venv`` and
        the original ``uv pip install`` is retried with ``VIRTUAL_ENV``
        and ``PATH`` exported. (TASK-FIX-AB60)

        On failure, the stderr excerpt and PEP-668 flag are stashed on
        ``self._last_failure_stderr`` / ``self._last_failure_is_pep668`` so
        :meth:`bootstrap` can surface them in
        :attr:`BootstrapResult.failure_details`. The method itself returns
        only ``bool`` so existing callers (and their mocks) remain stable.

        Parameters
        ----------
        manifest : DetectedManifest
            Manifest whose install_command should be executed.

        Returns
        -------
        bool
            True if the command succeeded (exit code 0), False otherwise.
            Never raises — all errors are caught and logged.
        """
        # Reset per-call diagnostics so a later failure-detail reader can't
        # see stale values from a previous install.
        self._last_failure_stderr = ""
        self._last_failure_is_pep668 = False
        cmd = list(manifest.install_command)
        is_python_cmd = cmd and cmd[0] == sys.executable

        # If a venv was created (by a previous PEP 668 fallback), use it
        if self._venv_python and is_python_cmd:
            cmd[0] = str(self._venv_python)

        cwd = str(manifest.path.parent)
        logger.info(
            "Running install for %s (%s): %s",
            manifest.stack,
            manifest.path.name,
            " ".join(cmd),
        )
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode == 0:
                logger.info(
                    "Install succeeded for %s (%s)", manifest.stack, manifest.path.name
                )
                if proc.stdout:
                    logger.debug("Install stdout:\n%s", proc.stdout)
                return True

            # PEP 668 fallback: detect and retry with venv
            if (
                is_python_cmd
                and not self._venv_python
                and self._is_pep668_error(proc.stderr or "")
            ):
                venv_python = self._ensure_venv()
                retry_cmd = list(manifest.install_command)
                retry_cmd[0] = str(venv_python)
                logger.info(
                    "PEP 668: retrying install for %s (%s): %s",
                    manifest.stack,
                    manifest.path.name,
                    " ".join(retry_cmd),
                )
                retry_proc = subprocess.run(
                    retry_cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if retry_proc.returncode == 0:
                    logger.info(
                        "PEP 668 retry succeeded for %s (%s)",
                        manifest.stack,
                        manifest.path.name,
                    )
                    return True
                logger.warning(
                    "PEP 668 retry failed for %s (%s) with exit code %d:\n"
                    "stderr: %s\nstdout: %s",
                    manifest.stack,
                    manifest.path.name,
                    retry_proc.returncode,
                    retry_proc.stderr or "(empty)",
                    retry_proc.stdout or "(empty)",
                )
                self._last_failure_stderr = _tail_excerpt(retry_proc.stderr)
                self._last_failure_is_pep668 = True
                return False

            # uv-sources fallback: ``uv pip install`` against a project that
            # declares ``[tool.uv.sources]`` requires a discoverable venv.
            # When uv reports "No virtual environment found" we create one
            # at ``<cwd>/.venv`` and retry once with VIRTUAL_ENV/PATH set.
            # Gated to ``uv pip install ...`` specifically (cmd[1:3]) so
            # ``uv sync`` (the FD32 path) is not intercepted. (AB60)
            if (
                cmd
                and cmd[0] == "uv"
                and cmd[1:3] == ["pip", "install"]
                and self._uv_venv_python is None
                and self._is_uv_no_venv_error(proc.stderr or "")
            ):
                try:
                    venv_dir = self._ensure_uv_venv(Path(cwd))
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                    logger.warning(
                        "uv-sources: failed to create worktree-local venv at "
                        "%s/.venv: %s",
                        cwd,
                        exc,
                    )
                    self._last_failure_stderr = _tail_excerpt(
                        f"uv venv creation failed: {exc}\n"
                        "Original uv pip install stderr:\n"
                        + (proc.stderr or "")
                    )
                    return False

                retry_cmd = list(manifest.install_command)
                retry_env = {
                    **os.environ,
                    "VIRTUAL_ENV": str(venv_dir),
                    "PATH": str(venv_dir / "bin")
                    + os.pathsep
                    + os.environ.get("PATH", ""),
                }
                logger.info(
                    "uv-sources: retrying install for %s (%s) with VIRTUAL_ENV=%s: %s",
                    manifest.stack,
                    manifest.path.name,
                    venv_dir,
                    " ".join(retry_cmd),
                )
                retry_proc = subprocess.run(
                    retry_cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=retry_env,
                )
                if retry_proc.returncode == 0:
                    logger.info(
                        "uv-sources retry succeeded for %s (%s)",
                        manifest.stack,
                        manifest.path.name,
                    )
                    return True
                logger.warning(
                    "uv-sources retry failed for %s (%s) with exit code %d:\n"
                    "stderr: %s\nstdout: %s",
                    manifest.stack,
                    manifest.path.name,
                    retry_proc.returncode,
                    retry_proc.stderr or "(empty)",
                    retry_proc.stdout or "(empty)",
                )
                self._last_failure_stderr = _tail_excerpt(retry_proc.stderr)
                return False

            stderr_text = proc.stderr or ""
            logger.warning(
                "Install failed for %s (%s) with exit code %d:\nstderr: %s\nstdout: %s",
                manifest.stack,
                manifest.path.name,
                proc.returncode,
                stderr_text or "(empty)",
                proc.stdout or "(empty)",
            )
            self._last_failure_stderr = _tail_excerpt(stderr_text)
            self._last_failure_is_pep668 = self._is_pep668_error(stderr_text)
            return False
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Install raised CalledProcessError for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            self._last_failure_stderr = str(exc)
            return False
        except OSError as exc:
            logger.warning(
                "Install raised OSError for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            self._last_failure_stderr = str(exc)
            return False
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "Install timed out (300s) for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            self._last_failure_stderr = f"install timed out after 300s: {exc}"
            return False

    def _run_single_command(self, cmd: List[str], cwd: Path) -> bool:
        """
        Run a single command in the given working directory.

        Used for per-dependency installs when
        ``DetectedManifest.is_project_complete()`` returns False.

        On PEP 668 failure for Python pip commands, a project-local
        virtualenv is created and the command is retried.

        Failure diagnostics (stderr excerpt, PEP-668 flag) are stashed on
        ``self._last_failure_stderr`` / ``self._last_failure_is_pep668`` for
        :meth:`bootstrap` to consume; see :meth:`_run_install` for rationale.

        Parameters
        ----------
        cmd : List[str]
            argv list for the command to run.
        cwd : Path
            Working directory for the command.

        Returns
        -------
        bool
            True if the command succeeded (exit code 0), False otherwise.
            Never raises — all errors are caught and logged.
        """
        self._last_failure_stderr = ""
        self._last_failure_is_pep668 = False

        run_cmd = list(cmd)
        is_python_cmd = run_cmd and run_cmd[0] == sys.executable

        # If a venv was created (by a previous PEP 668 fallback), use it
        if self._venv_python and is_python_cmd:
            run_cmd[0] = str(self._venv_python)

        logger.info("Running dep-install: %s", " ".join(run_cmd))
        try:
            proc = subprocess.run(
                run_cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if proc.returncode == 0:
                logger.debug("Command succeeded: %s", " ".join(run_cmd))
                return True

            # PEP 668 fallback: detect and retry with venv
            if (
                is_python_cmd
                and not self._venv_python
                and self._is_pep668_error(proc.stderr or "")
            ):
                venv_python = self._ensure_venv()
                retry_cmd = list(cmd)
                retry_cmd[0] = str(venv_python)
                logger.info(
                    "PEP 668: retrying dep-install: %s", " ".join(retry_cmd)
                )
                retry_proc = subprocess.run(
                    retry_cmd,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if retry_proc.returncode == 0:
                    logger.debug(
                        "PEP 668 retry succeeded: %s", " ".join(retry_cmd)
                    )
                    return True
                logger.warning(
                    "PEP 668 retry failed (exit %d): %s\n%s",
                    retry_proc.returncode,
                    " ".join(retry_cmd),
                    retry_proc.stderr or retry_proc.stdout,
                )
                self._last_failure_stderr = _tail_excerpt(retry_proc.stderr)
                self._last_failure_is_pep668 = True
                return False

            stderr_text = proc.stderr or ""
            logger.warning(
                "Command failed (exit %d): %s\n%s",
                proc.returncode,
                " ".join(run_cmd),
                stderr_text or proc.stdout,
            )
            self._last_failure_stderr = _tail_excerpt(stderr_text)
            self._last_failure_is_pep668 = self._is_pep668_error(stderr_text)
            return False
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Command raised CalledProcessError: %s: %s", " ".join(run_cmd), exc
            )
            self._last_failure_stderr = str(exc)
            return False
        except OSError as exc:
            logger.warning("Command raised OSError: %s: %s", " ".join(run_cmd), exc)
            self._last_failure_stderr = str(exc)
            return False
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "Command timed out (300s): %s: %s", " ".join(run_cmd), exc
            )
            self._last_failure_stderr = f"command timed out after 300s: {exc}"
            return False


# ============================================================================
# requires-python pre-check (TASK-REV-JMBP Workstream E)
# ============================================================================


@dataclass
class RequiresPythonMismatch:
    """
    Per-manifest mismatch between the active interpreter and a manifest's
    ``requires-python`` specifier. Emitted by
    :func:`check_requires_python_precheck`.

    Attributes
    ----------
    manifest_path : str
        Absolute path of the manifest that declared the constraint.
    specifier : str
        The raw specifier string (e.g. ``">=3.12,<3.13"``).
    active_version : str
        The active interpreter version actually detected (``"3.14.2"`` shape).
    """

    manifest_path: str
    specifier: str
    active_version: str


def _active_python_version() -> str:
    """Return the active interpreter version in ``major.minor.micro`` form."""
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"


def check_requires_python_precheck(
    manifests: List[DetectedManifest],
    *,
    active_version: Optional[str] = None,
) -> List[RequiresPythonMismatch]:
    """
    Compare each manifest's ``requires-python`` against the active interpreter.

    Runs BEFORE any pip invocation so the orchestrator can surface a clean
    "your interpreter doesn't match" signal rather than relying on pip's
    "requires a different Python: X not in '...'" line (which arrives after
    a resolver pass and is easy to miss).

    Behavior contract:

    - Manifests without a ``requires-python`` constraint are silently skipped
      (pip remains authoritative for those).
    - Non-Python manifests are skipped.
    - If :mod:`packaging.specifiers` is unavailable, the pre-check is a no-op
      (empty list) — callers must still run the bootstrap, which lets pip be
      authoritative. This matches the AC-REQPY-PRECHECK "skip gracefully"
      requirement.
    - Invalid specifier strings are skipped with a debug log; pip will still
      get a chance to error.

    Parameters
    ----------
    manifests : List[DetectedManifest]
        Manifests produced by :class:`ProjectEnvironmentDetector`.
    active_version : Optional[str]
        Override for the active Python version (test fixtures inject a
        fabricated version like ``"3.14.2"``). Defaults to
        :func:`_active_python_version`.

    Returns
    -------
    List[RequiresPythonMismatch]
        One entry per manifest whose specifier is not satisfied by the
        active interpreter. Empty list = no mismatches or pre-check unable to
        run.
    """
    try:
        from packaging.specifiers import InvalidSpecifier, SpecifierSet
    except ImportError:
        logger.debug(
            "packaging.specifiers unavailable — skipping requires-python pre-check"
        )
        return []

    current = active_version or _active_python_version()
    mismatches: List[RequiresPythonMismatch] = []

    for manifest in manifests:
        specifier = manifest.get_requires_python()
        if not specifier:
            continue
        try:
            spec_set = SpecifierSet(specifier)
        except InvalidSpecifier as exc:
            logger.debug(
                "Invalid requires-python %r in %s: %s — falling through to pip",
                specifier,
                manifest.path,
                exc,
            )
            continue
        if current not in spec_set:
            mismatches.append(
                RequiresPythonMismatch(
                    manifest_path=str(manifest.path),
                    specifier=specifier,
                    active_version=current,
                )
            )

    return mismatches


def format_requires_python_remediation(
    mismatch: RequiresPythonMismatch,
) -> str:
    """
    Format a multi-line remediation hint for a single mismatch.

    The hint names several package managers (uv / pyenv / conda) without
    trying to auto-detect which one is available — the user decides. This
    matches AC-REQPY-PRECHECK's "do not try to auto-detect the available
    package manager" requirement.
    """
    # Pick a minor-only example version from the specifier when possible
    # (e.g. specifier ">=3.12,<3.13" → suggest "3.12"). Fall back to a
    # plain string otherwise. This keeps suggestions concrete rather than
    # reprinting the specifier.
    example = _example_version_from_specifier(mismatch.specifier) or "<pinned>"
    return (
        f"Python {mismatch.active_version} does not satisfy "
        f"requires-python=`{mismatch.specifier}` for {mismatch.manifest_path}.\n"
        f"Install a compatible interpreter with one of:\n"
        f"  • uv python install {example}\n"
        f"  • pyenv install {example} && pyenv local {example}\n"
        f"  • conda create -n <name> python={example} && conda activate <name>"
    )


def _example_version_from_specifier(specifier: str) -> Optional[str]:
    """Pick a plausible ``major.minor`` install target from a specifier."""
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version
    except ImportError:
        return None
    try:
        spec_set = SpecifierSet(specifier)
    except Exception:
        return None
    # Try candidate versions covering the usual supported range; return the
    # first that satisfies the specifier.
    candidates = [f"3.{minor}" for minor in range(8, 16)]
    for candidate in candidates:
        try:
            if Version(candidate) in spec_set:
                return candidate
        except Exception:
            continue
    return None


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "PEP668_SENTINEL",
    "DetectedManifest",
    "BootstrapResult",
    "BootstrapFailureDetail",
    "ProjectEnvironmentDetector",
    "EnvironmentBootstrapper",
    "RequiresPythonMismatch",
    "UvSourcesRequireUvError",
    "check_requires_python_precheck",
    "format_requires_python_remediation",
    "_resolve_uv_sources_symlinks",
    "_create_worktree_uv_sources_symlinks",
]
