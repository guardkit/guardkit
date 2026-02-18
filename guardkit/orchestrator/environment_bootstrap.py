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
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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
        Number of install commands that failed.
    error : Optional[str]
        Human-readable error message when success is False, else None.
    duration_seconds : float
        Wall-clock duration of the bootstrap operation in seconds.
    """

    success: bool
    skipped: bool
    stacks_detected: List[str]
    manifests_found: List[str]
    installs_attempted: int = 0
    installs_failed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


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

    def __init__(self, root: Path) -> None:
        """
        Initialize the detector.

        Parameters
        ----------
        root : Path
            Absolute path to the worktree root directory.
        """
        self._root = root

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

        Returns
        -------
        List[Path]
            [root] + immediate subdirectories (hidden dirs excluded).
        """
        dirs: List[Path] = [self._root]
        try:
            for entry in sorted(self._root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
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
            results.append(
                DetectedManifest(
                    path=(directory / "pyproject.toml").resolve(),
                    stack="python",
                    is_lock_file=False,
                    install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
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
        """
        self._root = root
        self._state_file = state_file or (root / ".guardkit" / "bootstrap_state.json")

    def bootstrap(self, manifests: List[DetectedManifest]) -> BootstrapResult:
        """
        Install dependencies for the given manifests.

        The operation is idempotent: if the combined content hash of all
        manifests matches the saved state the function returns immediately
        with ``skipped=True``.

        Parameters
        ----------
        manifests : List[DetectedManifest]
            Manifests returned by ProjectEnvironmentDetector.detect().

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

        # Hash-based deduplication
        content_hash = self._compute_hash(manifests)
        saved_state = self._load_state()
        if saved_state.get("content_hash") == content_hash:
            logger.debug(
                "Bootstrap skipped: hash %s matches saved state", content_hash[:8]
            )
            return BootstrapResult(
                success=True,
                skipped=True,
                stacks_detected=stacks_detected,
                manifests_found=manifests_found,
                duration_seconds=time.monotonic() - start_time,
            )

        # Run install commands
        installs_attempted = 0
        installs_failed = 0

        for manifest in manifests:
            installs_attempted += 1
            success = self._run_install(manifest)
            if not success:
                installs_failed += 1

        # Persist new state hash (even on partial failure)
        self._save_state(content_hash)

        duration = time.monotonic() - start_time
        overall_success = installs_failed == 0

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

    def _save_state(self, content_hash: str) -> None:
        """
        Persist the content hash to the state file.

        Parameters
        ----------
        content_hash : str
            Hex-encoded SHA-256 digest to save.
        """
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps({"content_hash": content_hash}, indent=2),
                encoding="utf-8",
            )
            logger.debug("Saved bootstrap state to %s", self._state_file)
        except OSError as exc:
            logger.warning("Could not save bootstrap state to %s: %s", self._state_file, exc)

    def _run_install(self, manifest: DetectedManifest) -> bool:
        """
        Run the install command for a single manifest.

        The command is executed with the manifest's parent directory as the
        working directory so that relative paths in install commands (e.g.
        ``-r requirements.txt``) resolve correctly.

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
        cmd = manifest.install_command
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
            else:
                logger.warning(
                    "Install failed for %s (%s) with exit code %d:\nstderr: %s\nstdout: %s",
                    manifest.stack,
                    manifest.path.name,
                    proc.returncode,
                    proc.stderr or "(empty)",
                    proc.stdout or "(empty)",
                )
                return False
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Install raised CalledProcessError for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            return False
        except OSError as exc:
            logger.warning(
                "Install raised OSError for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            return False
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "Install timed out (300s) for %s (%s): %s",
                manifest.stack,
                manifest.path.name,
                exc,
            )
            return False


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "DetectedManifest",
    "BootstrapResult",
    "ProjectEnvironmentDetector",
    "EnvironmentBootstrapper",
]
