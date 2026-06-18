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
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

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
    python_extras : tuple[str, ...]
        PEP 621 optional-dependency group names (e.g. ``("dev",)``) the
        bootstrap requested. Only meaningful for Python ``pyproject.toml``
        manifests. Threaded into the *incomplete-project* per-dependency
        install path (:py:meth:`get_dependency_install_commands` →
        :py:meth:`_python_dep_commands`) so extras such as ``dev`` (pytest)
        are installed even when the project source dir is absent and the
        editable ``pip install -e .[dev]`` path is skipped. Without this the
        worktree venv would get only base deps, and the Coach independent
        test would fail 0.0s with "No module named pytest" (TASK-FIX-BSEXTRAS01,
        FEAT-9DDE run-6).
    """

    path: Path
    stack: str
    is_lock_file: bool
    install_command: List[str]
    python_extras: tuple[str, ...] = ()

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
        """Parse [project.dependencies] (+ requested extras) for per-dep installs.

        Base ``[project.dependencies]`` are always installed. When
        ``self.python_extras`` is non-empty, the matching
        ``[project.optional-dependencies]`` groups are appended too
        (TASK-FIX-BSEXTRAS01) — otherwise the incomplete-project path would
        silently drop test extras like ``dev`` (pytest), leaving the worktree
        venv without pytest and the Coach independent test failing 0.0s with
        "No module named pytest". A requested extra absent from the manifest
        is logged and skipped (mirrors the auto-detect warning convention).
        """
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

        project = data.get("project", {}) or {}
        deps: List[str] = list(project.get("dependencies", []) or [])

        optional = project.get("optional-dependencies", {}) or {}
        for extra in self.python_extras:
            group = optional.get(extra)
            if group is None:
                logger.warning(
                    "pyproject %s declares no optional-dependency group '%s'; "
                    "skipping (bootstrap requested extras=%s)",
                    self.path,
                    extra,
                    list(self.python_extras),
                )
                continue
            deps.extend(group)

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


class BootstrapEnvironmentLeakError(RuntimeError):
    """
    Raised when bootstrap completes a Python install but the captured
    interpreter path lies outside the worktree root.

    Instance of the ``absence-of-failure-is-not-success`` rule: the absence
    of an install error does not prove the install landed in the right
    interpreter. When ``self._venv_python`` points outside ``self._root``
    after a "successful" install, the editable ``_editable_impl_*.pth`` line
    has been written into the parent project's venv — silently corrupting
    any downstream process (Claude Desktop MCPs, IDE language servers,
    other autobuilds) that uses that venv after the worktree is torn down.

    Refusing to claim success forces the orchestrator to treat the bootstrap
    as failed and surfaces the actionable diagnostic rather than masking it
    behind a green BootstrapResult.

    See:
        - TASK-FIX-FF61
        - .claude/reviews/TASK-REV-FFC6-review-report.md
        - .claude/rules/absence-of-failure-is-not-success.md
    """


def _uv_on_path() -> bool:
    """Return True when ``uv`` is resolvable via PATH."""
    return shutil.which("uv") is not None


_PY_VERSION_RE = re.compile(r"(\d+)\.(\d+)")


def _uv_python_request(requires_python: Optional[str]) -> Optional[str]:
    """
    Map a ``requires-python`` specifier to a uv ``--python`` request.

    Returns a concrete ``major.minor`` version string (e.g. ``"3.12"``) derived
    from the *lower bound* of the constraint — the smallest ``major.minor`` the
    constraint admits — which is sufficient for ``uv venv --python`` to select
    (or download) a compatible interpreter. Returns ``None`` when the constraint
    is absent or no version token can be parsed, so callers fall back to uv's
    default interpreter selection (behaviour unchanged).

    Taking the minimum across every version token in the specifier yields the
    floor for the common forms without having to classify each bound:

    Examples
    --------
    ``">=3.12"``      -> ``"3.12"``
    ``">=3.12,<4.0"`` -> ``"3.12"``
    ``">=3.9,<4.0"``  -> ``"3.9"``
    ``"^3.11"``       -> ``"3.11"``
    ``"~=3.10"``      -> ``"3.10"``
    ``None`` / ``""`` -> ``None``

    See TASK-AB-BOOTPY01 (FEAT-MEM-01 Error 1: Python 3.10 bootstrap trap).
    """
    if not requires_python:
        return None
    candidates: List[tuple] = []
    for token in requires_python.split(","):
        match = _PY_VERSION_RE.search(token)
        if match:
            candidates.append((int(match.group(1)), int(match.group(2))))
    if not candidates:
        return None
    major, minor = min(candidates)
    return f"{major}.{minor}"


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
    directory: Path,
    pyproject_path: Path,
    extras: Sequence[str] = (),
) -> List[str]:
    """
    Choose the install command for a Python ``pyproject.toml`` manifest.

    Implements the matrix at the top of this section. The ``uv.lock`` /
    no-uv-on-path row emits a warning so operators know they're falling
    back to pip when a uv lockfile was available.

    Parameters
    ----------
    directory : Path
        Project directory containing the manifest.
    pyproject_path : Path
        Path to ``pyproject.toml`` (already verified to exist).
    extras : Sequence[str], optional
        PEP 621 optional-dependency group names to install (e.g.
        ``["dev"]``). When non-empty for the editable-install paths,
        the install target becomes ``.[ext1,ext2]`` instead of ``.``.
        For the ``uv sync --frozen`` row, extras are ignored at install
        time (uv.lock bakes extras at lock time, not install time) and
        a warning is logged. (TASK-GK-BS-001)

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

    target = "."
    if extras:
        # Sort + dedup so the resulting command is deterministic regardless
        # of caller ordering (helps cache hits on the bootstrap content
        # hash, and makes test assertions stable).
        target = f".[{','.join(sorted(set(extras)))}]"

    if has_uv_sources:
        return ["uv", "pip", "install", "-e", target]

    if has_uv_lock and uv_available:
        # `uv sync --frozen` is project-aware (reads pyproject.toml + uv.lock)
        # and `--frozen` guarantees the orchestrator never silently re-locks.
        # `uv pip sync` only accepts requirements.txt / pylock.toml — it
        # cannot parse uv's native `uv.lock` format. (TASK-FIX-FD32)
        #
        # Extras are baked into the lockfile at `uv lock --extra` time,
        # not at install time — applying them here would diverge from
        # the frozen lock. Warn so operators know to add the extra at
        # lock time. (TASK-GK-BS-001)
        if extras:
            logger.warning(
                "%s declares uv.lock; bootstrap_extras=%s ignored at install "
                "time because `uv sync --frozen` reads extras from the lock. "
                "Add extras at lock time via `uv lock --extra %s`, or remove "
                "uv.lock to switch to the editable-install path.",
                directory,
                list(extras),
                ",".join(sorted(set(extras))),
            )
        return ["uv", "sync", "--frozen"]

    if has_uv_lock and not uv_available:
        logger.warning(
            "%s/uv.lock present but `uv` is not on PATH — falling back to "
            "`pip install -e .`. Install uv (https://astral.sh/uv) for full "
            "lockfile fidelity.",
            directory,
        )

    return [sys.executable, "-m", "pip", "install", "-e", target]


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
        python_extras: Sequence[str] = (),
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
        python_extras : Sequence[str], optional
            PEP 621 optional-dependency group names to apply to Python
            ``pyproject.toml`` install commands (e.g. ``["dev"]`` →
            ``pip install -e ".[dev]"``). The ``uv sync --frozen`` row
            ignores this and emits a warning (extras are baked at lock
            time). See :func:`_resolve_python_pyproject_install_command`
            and TASK-GK-BS-001 for the rationale.
        """
        self._root = root
        self._exclude_patterns: List[str] = (
            exclude_patterns if exclude_patterns is not None else ["tests/fixtures"]
        )
        # Frozen as a tuple so ``self._python_extras`` is hashable / can't
        # be mutated by callers after construction.
        self._python_extras: tuple[str, ...] = tuple(python_extras)

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
                directory, pyproject_path, extras=self._python_extras
            )
            results.append(
                DetectedManifest(
                    path=pyproject_path,
                    stack="python",
                    is_lock_file=False,
                    install_command=install_command,
                    # TASK-FIX-BSEXTRAS01: carry the requested extras so the
                    # incomplete-project per-dep path installs them too (the
                    # editable `.[dev]` path above is skipped when the source
                    # dir is absent — e.g. guardkit-py whose import name
                    # `guardkit_py` does not match the `guardkit/` dir).
                    python_extras=self._python_extras,
                )
            )
            locked_stacks.add("python")  # prevent requirements.txt from also running

        # requirements*.txt — ADDITIVE: install EVERY matching file, so both a
        # base+dev/test split (requirements.txt + requirements-dev.txt) AND a
        # non-standard sole manifest (requirements.poc.txt — lpa-platform-poc)
        # land in the worktree venv. Only when no editable manifest
        # (poetry.lock / pyproject.toml) already locked the python stack —
        # those projects install via `pip install -e .[extras]` instead.
        # TASK-AB-PERTASKFG01 AC-003: a project declaring deps solely in a
        # non-standard requirements file otherwise produced an EMPTY worktree
        # venv, so the Coach's independent test could not import the app/test
        # deps and tests could not run (the TASK-AB-PERTASKFG01 broken-venv
        # root cause). Glob is depth-0 within `directory`; `requirements.txt`
        # itself is included so the common single-file case is unchanged.
        if "python" not in locked_stacks:
            req_files = sorted(directory.glob("requirements*.txt"))
            for req_file in req_files:
                results.append(
                    DetectedManifest(
                        path=req_file.resolve(),
                        stack="python",
                        is_lock_file=False,
                        install_command=[
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            "-r",
                            req_file.name,
                        ],
                    )
                )
            if req_files:
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
            saved_venv_path = Path(saved_venv)
            # FFC6 invariant: the saved venv must be inside the worktree.
            # Older state files written before TASK-FIX-FF61 may have
            # captured ``sys.executable`` (the orchestrator's parent venv)
            # via the false-success block at the previous L1239-1249.
            # Discard such stale state — eager creation will re-establish
            # a worktree-local venv below.
            if str(saved_venv_path).startswith(str(self._root)):
                self._venv_python = saved_venv_path
                logger.info(
                    "PEP 668: reusing virtualenv from previous run at %s",
                    self._venv_python,
                )
            else:
                logger.warning(
                    "FFC6: discarding stale saved venv_python %s — outside "
                    "worktree %s. Eager creation will re-establish.",
                    saved_venv_path,
                    self._root,
                )

        # FFC6 (AC-003): eagerly create a worktree-local venv BEFORE any
        # Python install subprocess runs. This guarantees:
        #   1. Pip-path commands have self._venv_python set so the existing
        #      cmd[0] remap fires on the first try (not just on retry).
        #   2. uv pip / uv sync commands receive a worktree-local
        #      VIRTUAL_ENV via _isolated_env (not the inherited parent).
        # Gated to Python-stack manifests so non-Python features (Node /
        # .NET / Go / Rust / Flutter — all leak-free per FFC6 review F8)
        # do not pay the venv-creation cost.
        if any(m.stack == "python" for m in manifests) and (
            self._venv_python is None
            or not str(self._venv_python).startswith(str(self._root))
        ):
            try:
                # Pin the eager venv to the project's requires-python (first
                # python manifest that declares one) so uv does not silently
                # build it on an incompatible host interpreter (TASK-AB-BOOTPY01).
                eager_requires_python = next(
                    (
                        rp
                        for m in manifests
                        if m.stack == "python"
                        for rp in (m.get_requires_python(),)
                        if rp
                    ),
                    None,
                )
                self._venv_python = self._ensure_worktree_venv(
                    self._root, eager_requires_python
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
                logger.warning(
                    "FFC6: eager worktree venv creation failed at %s/.venv: %s. "
                    "Falling through to existing PEP 668 / AB60 retry paths.",
                    self._root,
                    exc,
                )
                # Leave self._venv_python unset; the existing fallback
                # paths in _run_install handle the externally-managed and
                # uv-no-venv cases independently.

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

        # FFC6 (AC-006): replaces the historical TASK-SGER-002 false-success
        # block. SGER-002 captured ``sys.executable`` on the macOS happy path
        # to give the downstream smoke gate a venv path to work with — but
        # ``sys.executable`` is the orchestrator's parent venv, so the
        # editable ``_editable_impl_*.pth`` line had already landed there,
        # silently corrupting the parent project's venv after the worktree
        # was torn down.
        #
        # With AC-003's eager worktree-venv creation in place,
        # ``self._venv_python`` is guaranteed to point at
        # ``<worktree>/.venv/bin/python`` (or, on PEP 668 fallback, at
        # ``<worktree>/.guardkit/venv/bin/python``) before any install
        # subprocess runs. If we still find ourselves with an interpreter
        # outside the worktree, an upstream code path has reintroduced the
        # leak — refuse to claim success and surface the diagnostic.
        # Instance of the ``absence-of-failure-is-not-success`` rule.
        if (
            overall_success
            and any(m.stack == "python" for m in manifests)
            and self._venv_python is not None
            and not str(self._venv_python).startswith(str(self._root))
        ):
            raise BootstrapEnvironmentLeakError(
                f"Python install completed but interpreter "
                f"{self._venv_python} is outside worktree {self._root}. "
                f"Refusing to claim success — this would silently corrupt "
                f"the parent venv. See "
                f".claude/reviews/TASK-REV-FFC6-review-report.md and "
                f".claude/rules/absence-of-failure-is-not-success.md."
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

    def _ensure_uv_venv(
        self, cwd: Path, requires_python: Optional[str] = None
    ) -> Path:
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
        requires_python : Optional[str]
            The manifest's ``requires-python`` constraint, if any. When it
            maps to a concrete interpreter request (via
            :func:`_uv_python_request`), ``uv venv`` is pinned to that version
            so the venv is not silently built on an incompatible host
            interpreter (TASK-AB-BOOTPY01). Absent/unparseable → no ``--python``
            (uv default), behaviour unchanged.

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
            cmd = ["uv", "venv"]
            py_request = _uv_python_request(requires_python)
            if py_request:
                cmd += ["--python", py_request]
            cmd.append(str(venv_dir))
            logger.info(
                "uv-sources: creating worktree-local virtualenv at %s%s",
                venv_dir,
                f" (python {py_request})" if py_request else "",
            )
            subprocess.run(
                cmd,
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

    def _ensure_worktree_venv(
        self, worktree: Path, requires_python: Optional[str] = None
    ) -> Path:
        """
        Create ``<worktree>/.venv`` eagerly (idempotent) and return the
        Python interpreter path.

        Used by :meth:`bootstrap` BEFORE any Python install subprocess
        runs, so that:

        - Pip-path commands (``[sys.executable, "-m", "pip", "install", -e, "."]``)
          have ``self._venv_python`` set, which the existing remap at
          :meth:`_run_install` swaps into ``cmd[0]`` before the install
          subprocess runs.
        - uv pip / uv sync commands receive an explicit ``env=`` kwarg
          (via :meth:`_isolated_env`) with ``VIRTUAL_ENV`` exported to
          the worktree-local venv, preventing inheritance of the
          orchestrator's parent venv.

        Implementation choice: prefer ``uv venv`` when uv is on PATH
        (faster, supports python pinning), fall back to
        ``python -m venv``. Both produce a venv with
        ``<venv>/bin/python``.

        Distinct from :meth:`_ensure_venv` (PEP 668 fallback at
        ``<root>/.guardkit/venv/``) and :meth:`_ensure_uv_venv` (AB60
        retry path at ``<cwd>/.venv``). The PEP 668 path remains as a
        defense-in-depth fallback for the externally-managed Python
        case; AB60 retry remains as a defense-in-depth fallback for any
        uv version that fails the eager creation.

        Parameters
        ----------
        worktree : Path
            Worktree root (absolute). The venv is created at
            ``<worktree>/.venv``.
        requires_python : Optional[str]
            The project's ``requires-python`` constraint, if any. When it maps
            to a concrete interpreter request (via :func:`_uv_python_request`),
            ``uv venv`` is pinned to that version so the worktree venv is not
            silently built on an incompatible host interpreter — e.g. a
            uv-managed cpython-3.10 against a ``requires-python >=3.12`` project
            (TASK-AB-BOOTPY01, FEAT-MEM-01 Error 1). Absent/unparseable → no
            ``--python`` (uv default), behaviour unchanged. The ``python -m
            venv`` fallback cannot honour a pin and is unaffected.

        Returns
        -------
        Path
            Absolute path to the venv's Python interpreter
            (``<worktree>/.venv/bin/python``).

        Notes
        -----
        See:
            - TASK-FIX-FF61
            - .claude/reviews/TASK-REV-FFC6-review-report.md
        """
        venv_dir = worktree / ".venv"
        venv_python = venv_dir / "bin" / "python"

        if venv_python.exists():
            logger.debug(
                "FFC6: reusing existing worktree-local venv at %s", venv_dir
            )
            return venv_python

        if _uv_on_path():
            # ``--seed`` installs pip + setuptools into the new venv. Without
            # it, ``uv venv`` creates a minimal venv that lacks pip, and the
            # subsequent dep-install calls (which run ``<venv>/bin/python -m
            # pip install <pkg>`` via :meth:`_run_install`) fail with "No
            # module named pip" — manifests as a hard-fail bootstrap error
            # despite uv being present.
            cmd = ["uv", "venv", "--seed"]
            py_request = _uv_python_request(requires_python)
            if py_request:
                cmd += ["--python", py_request]
            cmd.append(str(venv_dir))
            logger.info(
                "FFC6: creating worktree-local venv via uv (seeded) at %s%s",
                venv_dir,
                f" (python {py_request})" if py_request else "",
            )
        else:
            cmd = [sys.executable, "-m", "venv", str(venv_dir)]
            logger.info(
                "FFC6: creating worktree-local venv via python -m venv at %s",
                venv_dir,
            )

        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return venv_python

    def _python_install_env(
        self, manifest: DetectedManifest
    ) -> Optional[Dict[str, str]]:
        """
        Compute the subprocess env override for a Python install command.

        Returns ``None`` for non-Python manifests (so they inherit
        ``os.environ`` unchanged). Returns ``None`` for Python manifests
        when ``self._venv_python`` is not set (test fixtures calling
        ``_run_install`` directly without going through ``bootstrap()``,
        and the legacy PEP 668 first-try call where the venv hasn't been
        created yet — the retry call constructs its own env from the
        just-created venv).

        Otherwise returns ``self._isolated_env(<venv_dir>)`` where
        ``<venv_dir>`` is the parent of ``<venv>/bin/python``.
        """
        if manifest.stack != "python":
            return None
        if self._venv_python is None:
            return None
        # _venv_python is <venv_dir>/bin/python; venv_dir is .parent.parent.
        venv_dir = self._venv_python.parent.parent
        return self._isolated_env(venv_dir)

    def _isolated_env(self, worktree_venv: Path) -> Dict[str, str]:
        """
        Build a subprocess env dict that forces ``VIRTUAL_ENV`` to point
        at the worktree-local venv.

        Strips inherited ``VIRTUAL_ENV`` first so we never accidentally
        fall through to the parent shell's venv even if a future uv
        version changes precedence between ``$VIRTUAL_ENV`` and
        explicit args. The strip-then-set order matters — relying solely
        on ``{**os.environ, "VIRTUAL_ENV": ...}`` semantics works today
        but is brittle to future runtime changes.

        Parameters
        ----------
        worktree_venv : Path
            Absolute path to the worktree-local venv directory (NOT the
            interpreter path). For the eager-creation path this is
            ``<worktree>/.venv``; for PEP 668 fallback it is
            ``<worktree>/.guardkit/venv``.

        Returns
        -------
        Dict[str, str]
            Subprocess env dict with ``VIRTUAL_ENV`` set and
            ``<worktree_venv>/bin`` prepended to ``PATH``.

        Notes
        -----
        See:
            - TASK-FIX-FF61 AC-002
            - .claude/rules/namespace-hygiene.md (parent venv as
              externally-defined namespace)
        """
        env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
        env["VIRTUAL_ENV"] = str(worktree_venv)
        env["PATH"] = (
            str(worktree_venv / "bin") + os.pathsep + env.get("PATH", "")
        )
        return env

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

        # If a venv was created (eagerly via FFC6, or by a previous PEP 668
        # fallback), use it. AC-005: with FFC6's eager creation in
        # bootstrap(), self._venv_python is set BEFORE _run_install runs
        # for any python manifest, so the remap fires on first try too.
        if self._venv_python and is_python_cmd:
            cmd[0] = str(self._venv_python)

        # FFC6 (AC-004): for Python install commands, pass env= with
        # VIRTUAL_ENV pointing at the worktree-local venv. Strips inherited
        # parent VIRTUAL_ENV. Non-Python commands (npm, dotnet, cargo, ...)
        # inherit env unchanged.
        env = self._python_install_env(manifest)

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
                env=env,
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
                # FFC6 (AC-004): retry must also receive isolated env so
                # inherited parent VIRTUAL_ENV cannot route the editable
                # .pth back into the parent venv. Use the just-created
                # PEP 668 venv (<root>/.guardkit/venv) as the worktree-local
                # interpreter root.
                retry_env = self._isolated_env(venv_python.parent.parent)
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
                    env=retry_env,
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
                    venv_dir = self._ensure_uv_venv(
                        Path(cwd), manifest.get_requires_python()
                    )
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
                # FFC6: route through _isolated_env so inherited parent
                # VIRTUAL_ENV is stripped first (defense-in-depth against
                # future precedence changes). Observable shape preserved:
                # VIRTUAL_ENV set to <cwd>/.venv, PATH prepended.
                retry_env = self._isolated_env(venv_dir)
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

        # If a venv was created (eagerly via FFC6, or by a previous PEP 668
        # fallback), use it.
        if self._venv_python and is_python_cmd:
            run_cmd[0] = str(self._venv_python)

        # FFC6 (AC-004): Python pip commands receive isolated env so
        # inherited parent VIRTUAL_ENV cannot route the install into the
        # parent venv. Non-Python commands inherit env unchanged.
        env: Optional[Dict[str, str]] = None
        if is_python_cmd and self._venv_python is not None:
            env = self._isolated_env(self._venv_python.parent.parent)

        logger.info("Running dep-install: %s", " ".join(run_cmd))
        try:
            proc = subprocess.run(
                run_cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
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
                # FFC6 (AC-004): retry must also receive isolated env.
                retry_env = self._isolated_env(venv_python.parent.parent)
                logger.info(
                    "PEP 668: retrying dep-install: %s", " ".join(retry_cmd)
                )
                retry_proc = subprocess.run(
                    retry_cmd,
                    cwd=str(cwd),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=retry_env,
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
# Intra-wave manifest-change refresh (TASK-AB-COACHVENV01)
# ============================================================================
#
# The worktree venv is bootstrapped once per feature and re-bootstrapped
# BETWEEN waves (feature_orchestrator inter-wave hook). When a single task adds
# a dependency and consumes it WITHIN the same wave (e.g. tiktoken in
# FEAT-MEM-05), the Coach's independent pytest run executes against the STALE
# venv → ModuleNotFoundError → the Coach rejects every AC even though the
# implementation + pyproject edit are correct. That is a false-red: the Coach's
# environment lags the Player's manifest edit by one wave.
#
# The fix is a per-turn refresh: when a turn's reported file changes touch a
# dependency manifest, reinstall into the existing worktree venv BEFORE the
# Coach's independent test run for that turn. ``changed_dependency_manifests``
# is the cheap diff gate (so unaffected turns pay nothing);
# ``refresh_environment_for_changes`` performs the reinstall by re-running the
# idempotent bootstrap (the content-hash dedup re-runs because the manifest
# changed, and the eager-venv path reuses the existing ``<root>/.venv``).

# Basename set of dependency manifests whose modification within a wave
# warrants a venv refresh. ``requirements*.txt`` is matched separately by
# ``_REQUIREMENTS_RE`` because its name is not fixed.
_DEPENDENCY_MANIFEST_NAMES = frozenset(
    {
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "go.mod",
        "go.sum",
        "Cargo.toml",
        "Cargo.lock",
        "pubspec.yaml",
        "pubspec.lock",
    }
)

# Matches requirements.txt / requirements-dev.txt / requirements/base.txt etc.
_REQUIREMENTS_RE = re.compile(r"requirements[\w.-]*\.txt$")


def changed_dependency_manifests(changed_paths: Iterable[str]) -> List[str]:
    """
    Return the subset of ``changed_paths`` that are dependency manifests.

    Matching is on the path *basename* so it is robust to repo-relative,
    worktree-relative, absolute, or repo-qualified (``repo:path``) strings as
    they appear in a Player report's ``files_modified`` / ``files_created``.

    Parameters
    ----------
    changed_paths : Iterable[str]
        File path strings reported as changed this turn.

    Returns
    -------
    List[str]
        The original path strings that name a dependency manifest, de-duplicated
        and order-preserving. Empty when no manifest changed (the caller treats
        an empty result as "no refresh needed").
    """
    matched: List[str] = []
    seen: set[str] = set()
    for raw in changed_paths:
        if not raw or raw in seen:
            continue
        path_part = str(raw)
        # Strip a repo-qualified prefix (``<repo>:<path>``) introduced by the
        # cross-repo evidence loop, where the token before the first ``:`` is a
        # repo name with no path separator (not a Windows drive — autobuild is
        # POSIX). Leave ordinary paths untouched.
        head, sep, tail = path_part.partition(":")
        if sep and tail and "/" not in head and "\\" not in head:
            path_part = tail
        name = Path(path_part).name
        if name in _DEPENDENCY_MANIFEST_NAMES or _REQUIREMENTS_RE.search(name):
            matched.append(raw)
            seen.add(raw)
    return matched


def refresh_environment_for_changes(
    worktree_root: Path,
    changed_paths: Iterable[str],
    *,
    python_extras: Sequence[str] = (),
    relevant_stacks: Optional[List[str]] = None,
) -> Optional[BootstrapResult]:
    """
    Reinstall dependencies into the worktree venv when a turn changed a manifest.

    No-op (returns ``None``) when ``changed_paths`` contains no dependency
    manifest, or when no manifest is detected in ``worktree_root`` — so a turn
    that did not touch dependencies pays only the cost of the cheap basename
    scan in :func:`changed_dependency_manifests`.

    When a manifest did change, the idempotent
    :meth:`EnvironmentBootstrapper.bootstrap` is re-run: its content-hash dedup
    re-executes the install because the manifest content differs from the saved
    state, and the eager-venv path reuses the existing ``<root>/.venv`` so the
    interpreter path is stable across the refresh.

    Parameters
    ----------
    worktree_root : Path
        Absolute path to the worktree root.
    changed_paths : Iterable[str]
        File path strings reported as changed this turn (Player report
        ``files_modified`` + ``files_created``).
    python_extras : Sequence[str], optional
        PEP 621 optional-dependency groups to thread into the Python install
        command (mirrors the feature bootstrap). Defaults to none — the editable
        reinstall preserves extras installed by the initial bootstrap.
    relevant_stacks : Optional[List[str]], optional
        Forwarded to :meth:`EnvironmentBootstrapper.bootstrap`. Defaults to None
        (all detected stacks treated as essential).

    Returns
    -------
    Optional[BootstrapResult]
        ``None`` when no manifest changed or none was detected; otherwise the
        :class:`BootstrapResult` from the reinstall. The caller is responsible
        for surfacing ``result.success is False`` as actionable feedback rather
        than swallowing it into a silent pass
        (``absence-of-failure-is-not-success``). ``bootstrap`` may also raise
        :class:`UvSourcesRequireUvError` / :class:`BootstrapEnvironmentLeakError`;
        those propagate to the caller for the same reason.
    """
    if not changed_dependency_manifests(changed_paths):
        return None

    detector = ProjectEnvironmentDetector(
        worktree_root, python_extras=tuple(python_extras)
    )
    manifests = detector.detect()
    if not manifests:
        return None

    bootstrapper = EnvironmentBootstrapper(worktree_root)
    return bootstrapper.bootstrap(manifests, relevant_stacks=relevant_stacks)


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
    "changed_dependency_manifests",
    "refresh_environment_for_changes",
    "RequiresPythonMismatch",
    "UvSourcesRequireUvError",
    "BootstrapEnvironmentLeakError",
    "check_requires_python_precheck",
    "format_requires_python_remediation",
    "_resolve_uv_sources_symlinks",
    "_create_worktree_uv_sources_symlinks",
]
