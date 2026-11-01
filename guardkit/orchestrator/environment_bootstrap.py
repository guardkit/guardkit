"""
The project's declared root install, run in a build's worktree.

Installs come only from the project's own declaration (1 November 2026; Rich,
31 October: "I don't want any more hidden surprises"):

* The root ``toolchain.install`` in ``.guardkit/config.yaml`` runs here, in
  the worktree's root folder, before the agents work, and again when a file
  it serves has changed (:func:`rerun_declared_install_if_due`).
* A component's or a ``parts:`` entry's ``install`` runs before that part's
  tests, in its folder (``CoachValidator._install_part_if_due``).

Nothing is worked out from a project's files. No package manager is chosen
from a manifest, no virtual environment is made, and no interpreter is looked
for. A project that declares no install gets none, and the build log says so
once, in plain words: "no install declared; nothing installed". A declared
install that fails, runs out of time or cannot start is reported with its
output, and the after-task check then says the project's tests could not run.

When the install is due again: the files git tracks directly in each folder
the install serves (the root, each declared component folder that has no
install of its own, and the folders between), fingerprinted by name and
content, plus the declaration file itself. That is the rule a part's install
already follows (31 October 2026), so GuardKit keeps no list of which file
names count as dependency files for which language.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from guardkit.orchestrator.launch_declaration import (
    load_launch_declaration,
    main_checkout_root,
)
from guardkit.orchestrator.project_command_env import (
    minimal_environment_note,
    project_command_environment,
)
from guardkit.orchestrator import process_group

if TYPE_CHECKING:  # pragma: no cover - typing only
    from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration

logger = logging.getLogger(__name__)

#: What the build log says, once, when the project declares no root install.
NO_INSTALL_DECLARED = "no install declared; nothing installed"

# Truncate output excerpts attached to a failure. The whole output is still
# logged at WARNING; this bounds what rides along on the result.
_EXCERPT_MAX_CHARS = 2000


def _tail_excerpt(text: Optional[str], max_chars: int = _EXCERPT_MAX_CHARS) -> str:
    """Return the trailing ``max_chars`` of ``text``, or an empty string."""
    if not text:
        return ""
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return "…" + stripped[-max_chars:]


# ============================================================================
# Data
# ============================================================================


@dataclass(frozen=True)
class DeclaredInstall:
    """The root ``toolchain.install``, as the project declared it.

    ``text`` is the declared string; ``argv`` is what it splits into (the
    command runs without a shell, as a part's install does). ``cwd`` is the
    worktree root. ``served_dirs`` are the worktree-relative POSIX folders
    whose tracked files decide when the install is due again: the root, each
    declared component folder with no ``install`` of its own, and every
    folder between the root and such a component.
    """

    text: str
    argv: Tuple[str, ...]
    cwd: Path
    timeout: int
    served_dirs: Tuple[str, ...] = (".",)


@dataclass
class BootstrapFailureDetail:
    """Why the declared install did not succeed.

    ``output_excerpt`` is the tail of what it printed (errors first), with the
    names of any settings the factory held back from it. ``missing_tool`` is
    the program, when the command's own program could not be found where the
    build runs (a gap in the build environment, not in the project).
    """

    command: str
    cwd: str
    output_excerpt: str
    missing_tool: Optional[str] = None


@dataclass
class BootstrapResult:
    """What the bootstrap did.

    Attributes
    ----------
    declared : bool
        False when the project declares no root install; nothing ran.
    success : bool
        True when nothing was declared, or the declared install succeeded
        (now or, with ``skipped``, last time with the same inputs).
    skipped : bool
        True when the saved record matched these inputs and nothing ran.
    command : Optional[str]
        The declared install text, when there is one.
    error : Optional[str]
        A plain sentence when ``success`` is False.
    failure : Optional[BootstrapFailureDetail]
        The details of the failure, when there was one.
    """

    declared: bool
    success: bool
    skipped: bool = False
    command: Optional[str] = None
    installs_attempted: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    failure: Optional[BootstrapFailureDetail] = None

    @property
    def summary(self) -> str:
        """One plain line for the build log."""
        if not self.declared:
            return NO_INSTALL_DECLARED
        if not self.success:
            return f"the declared install `{self.command}` failed: {self.error}"
        if self.skipped:
            return f"the declared install `{self.command}` is already done for these files"
        return f"the declared install `{self.command}` ran and succeeded"


# ============================================================================
# Reading the declaration
# ============================================================================


def _served_dirs(toolchain: "ToolchainDeclaration") -> Tuple[str, ...]:
    """The root, each component folder with no install of its own, and the
    folders between. A component that declares its own ``install`` is served
    by that install before its tests, not by the root's."""
    dirs: List[str] = ["."]
    for name in sorted(toolchain.components or {}):
        component = toolchain.components[name]
        if component.install:
            continue
        cwd = component.cwd
        parts = [] if cwd == "." else cwd.split("/")
        for depth in range(1, len(parts) + 1):
            rel = "/".join(parts[:depth])
            if rel not in dirs:
                dirs.append(rel)
    return tuple(dirs)


def declared_root_install(
    root: Path, toolchain: Optional["ToolchainDeclaration"] = None
) -> Optional[DeclaredInstall]:
    """The project's declared root install, or ``None`` when none is declared.

    ``toolchain`` defaults to ``<root>/.guardkit/config.yaml``, read strictly:
    a declaration file that exists but cannot be read raises
    ``ToolchainDeclarationError`` rather than being treated as "nothing
    declared". A declared string that cannot be split into a command also
    raises it, so a broken declaration is never mistaken for no declaration.
    """
    from guardkit.orchestrator.toolchain_declaration import (
        ToolchainDeclarationError,
        load_toolchain_declaration,
    )

    if toolchain is None:
        toolchain = load_toolchain_declaration(root, strict=True)
    if toolchain is None or not toolchain.install:
        return None
    text = toolchain.install
    try:
        argv = tuple(shlex.split(text))
    except ValueError as exc:
        raise ToolchainDeclarationError(
            f"The declared `toolchain.install` ({text!r}) cannot be split into "
            f"a command: {exc}"
        ) from exc
    if not argv:
        raise ToolchainDeclarationError(
            f"The declared `toolchain.install` ({text!r}) is empty."
        )
    return DeclaredInstall(
        text=text,
        argv=argv,
        cwd=Path(root),
        timeout=toolchain.install_timeout,
        served_dirs=_served_dirs(toolchain),
    )


# ============================================================================
# Running it
# ============================================================================


def _bootstrap_env(bootstrapper: "EnvironmentBootstrapper") -> Dict[str, str]:
    """The environment the declared install gets (13 October 2026): built
    from nothing by ``project_command_environment``, with the ``launch:``
    block of the main checkout the worktree was cut from. A module-level
    function, so the process-launch guard can rely on it."""
    return project_command_environment(
        bootstrapper._root,
        load_launch_declaration(main_checkout_root(bootstrapper._root)),
    )


def _missing_program(exc: OSError, argv: Sequence[str]) -> Optional[str]:
    """The install's own program, when *exc* says it could not be found.

    The command runs without a shell, so a ``FileNotFoundError`` whose
    ``filename`` is the bare first word means the program is not where the
    build runs. A missing working folder names the folder instead, and a
    path (a project script) is the project's, not the build environment's.
    """
    if (
        isinstance(exc, FileNotFoundError)
        and argv
        and exc.filename is not None
        and str(exc.filename) == str(argv[0])
        and os.path.basename(str(argv[0])) == str(argv[0])
    ):
        return str(argv[0])
    return None


class EnvironmentBootstrapper:
    """Runs the declared root install in a worktree, once per set of inputs.

    The saved record (``<root>/.guardkit/bootstrap_state.json``) holds a
    fingerprint of what the install depends on (see the module notes) and
    whether it succeeded. A match with a success runs nothing. A match with a
    failure inside the retry cooldown runs nothing and returns that failure.
    """

    def __init__(
        self,
        root: Path,
        state_file: Optional[Path] = None,
        retry_cooldown_seconds: int = 60,
    ) -> None:
        self._root = Path(root)
        self._state_file = state_file or (self._root / ".guardkit" / "bootstrap_state.json")
        self._retry_cooldown_seconds = retry_cooldown_seconds
        # The most recent run's failure, read by bootstrap().
        self._last_failure_stderr: str = ""
        self._last_failure_missing_tool: Optional[str] = None
        self._ran_project_command: bool = False

    # ---- the public step ----------------------------------------------

    def bootstrap(self, install: Optional[DeclaredInstall]) -> BootstrapResult:
        """Run ``install`` unless the saved record says it is already done.

        ``None`` (nothing declared) runs nothing; the caller says so once in
        the build log (``BootstrapResult.summary``).
        """
        start = time.monotonic()
        if install is None:
            return BootstrapResult(declared=False, success=True)

        fingerprint = self._fingerprint(install)
        saved = self._load_state()
        if saved.get("content_hash") == fingerprint:
            if saved.get("success", False):
                logger.debug("Declared install skipped: inputs unchanged since it succeeded")
                return BootstrapResult(
                    declared=True,
                    success=True,
                    skipped=True,
                    command=install.text,
                    duration_seconds=time.monotonic() - start,
                )
            if self._inside_cooldown(saved):
                return self._recorded_failure(install, saved, time.monotonic() - start)

        ok = self._run_install(install)
        failure = None
        if not ok:
            failure = BootstrapFailureDetail(
                command=install.text,
                cwd=str(install.cwd),
                output_excerpt=self._with_note(self._last_failure_stderr),
                missing_tool=self._last_failure_missing_tool,
            )
        # Fingerprinted after the run, so files the install itself rewrites
        # (a lock file it refreshes) do not make it due again next time.
        self._save_state(self._fingerprint(install), ok, failure)
        return BootstrapResult(
            declared=True,
            success=ok,
            command=install.text,
            installs_attempted=1,
            error=None if ok else self._failure_sentence(install, failure),
            duration_seconds=time.monotonic() - start,
            failure=failure,
        )

    # ---- the run -------------------------------------------------------

    def _run_install(self, install: DeclaredInstall) -> bool:
        """Run the declared install at the worktree root. Never raises.

        On failure the output tail is kept on ``_last_failure_stderr`` and a
        missing program on ``_last_failure_missing_tool``.
        """
        self._last_failure_stderr = ""
        self._last_failure_missing_tool = None
        self._ran_project_command = False
        argv = list(install.argv)
        logger.info("Running the declared install in %s: %s", install.cwd, install.text)
        try:
            # The environment built from nothing: the project's `launch:`
            # settings and scratch folders, read from the main checkout. A
            # malformed block or a missing scratch folder fails this install
            # with the reason.
            env = _bootstrap_env(self)
            self._ran_project_command = True
            proc = process_group.run_project_command(
                argv,
                cwd=str(install.cwd),
                capture_output=True,
                text=True,
                timeout=install.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("The declared install ran out of its %ss: %s", install.timeout, exc)
            self._last_failure_stderr = (
                f"the declared install ran out of its {install.timeout} seconds"
            )
            return False
        except OSError as exc:
            logger.warning("The declared install could not start: %s", exc)
            self._last_failure_stderr = str(exc)
            self._last_failure_missing_tool = _missing_program(exc, argv)
            return False
        if proc.returncode == 0:
            logger.info("The declared install succeeded: %s", install.text)
            if proc.stdout:
                logger.debug("Install output:\n%s", proc.stdout)
            return True
        logger.warning(
            "The declared install failed with exit code %d:\nstderr: %s\nstdout: %s",
            proc.returncode,
            proc.stderr or "(empty)",
            proc.stdout or "(empty)",
        )
        self._last_failure_stderr = _tail_excerpt(
            "\n".join(part for part in (proc.stderr, proc.stdout) if part)
        ) or f"exit {proc.returncode} with no output"
        return False

    def _with_note(self, excerpt: str) -> str:
        """``excerpt`` with the names of the settings that were held back."""
        if not self._ran_project_command:
            return excerpt
        try:
            note = minimal_environment_note(_bootstrap_env(self))
        except OSError:
            note = ""
        if not note:
            return excerpt
        return f"{excerpt}\n{note}" if excerpt else note

    @staticmethod
    def _failure_sentence(
        install: DeclaredInstall, failure: Optional[BootstrapFailureDetail]
    ) -> str:
        if failure is not None and failure.missing_tool:
            return (
                f"the declared install `{install.text}` could not start: "
                f"`{failure.missing_tool}` is not installed where the build runs"
            )
        excerpt = (failure.output_excerpt if failure else "").strip()
        sentence = f"the declared install `{install.text}` failed"
        return f"{sentence}: {excerpt[-500:]}" if excerpt else sentence

    # ---- the saved record ---------------------------------------------

    def _fingerprint(self, install: DeclaredInstall) -> str:
        """What the install depends on: its text and limit, the declaration
        file, the files git tracks directly in each served folder, the image
        identity (``FORGE_IMAGE_IDENTITY``) and the worktree's location."""
        from guardkit.orchestrator.quality_gates.coach_validator import (
            _folder_fingerprint,
        )
        from guardkit.orchestrator.toolchain_declaration import (
            CONFIG_RELATIVE_PATH,
            resolve_component_cwd,
        )

        hasher = hashlib.sha256()
        hasher.update(b"declared-install/2\n")
        hasher.update(f"command\0{install.text}\0{install.timeout}\n".encode("utf-8"))
        hasher.update(
            f"declaration\0{self._digest(self._root / CONFIG_RELATIVE_PATH)}\n".encode("utf-8")
        )
        for rel_dir in install.served_dirs:
            try:
                folder = resolve_component_cwd(self._root, rel_dir)
                mark = _folder_fingerprint(folder) if folder.is_dir() else "absent"
            except (OSError, RuntimeError, ValueError):
                mark = "unreadable"
            hasher.update(f"folder\0{rel_dir}\0{mark}\n".encode("utf-8"))
        identity = os.environ.get("FORGE_IMAGE_IDENTITY") or "not set"
        hasher.update(f"image\0{identity}\n".encode("utf-8"))
        hasher.update(f"root\0{self._root.resolve()}\n".encode("utf-8"))
        return hasher.hexdigest()

    @staticmethod
    def _digest(path: Path) -> str:
        try:
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError:
            return "unreadable"

    def _inside_cooldown(self, saved: Dict[str, object]) -> bool:
        stamp = saved.get("timestamp")
        if not isinstance(stamp, str):
            return False
        try:
            elapsed = (datetime.now() - datetime.fromisoformat(stamp)).total_seconds()
        except (TypeError, ValueError):
            return False
        return elapsed < self._retry_cooldown_seconds

    def _recorded_failure(
        self, install: DeclaredInstall, saved: Dict[str, object], duration: float
    ) -> BootstrapResult:
        """The failure recorded inside the retry cooldown, running nothing."""
        recorded = saved.get("failure")
        failure = BootstrapFailureDetail(
            command=install.text,
            cwd=str(install.cwd),
            output_excerpt=str(recorded.get("output_excerpt", "")) if isinstance(recorded, dict) else "",
            missing_tool=(recorded.get("missing_tool") if isinstance(recorded, dict) else None),
        )
        logger.warning(
            "The declared install is not retried: it failed with these inputs "
            "within the %ds retry cooldown",
            self._retry_cooldown_seconds,
        )
        return BootstrapResult(
            declared=True,
            success=False,
            skipped=True,
            command=install.text,
            error=self._failure_sentence(install, failure)
            + " (recorded failure, not retried within the cooldown)",
            duration_seconds=duration,
            failure=failure,
        )

    def _load_state(self) -> Dict[str, object]:
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load bootstrap state from %s: %s", self._state_file, exc)
            return {}
        return data if isinstance(data, dict) else {}

    def _save_state(
        self,
        content_hash: str,
        success: bool,
        failure: Optional[BootstrapFailureDetail] = None,
    ) -> None:
        state: Dict[str, object] = {
            "content_hash": content_hash,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        if failure is not None:
            state["failure"] = {
                "output_excerpt": failure.output_excerpt,
                "missing_tool": failure.missing_tool,
            }
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not save bootstrap state to %s: %s", self._state_file, exc)


def bootstrap_worktree(root: Path) -> BootstrapResult:
    """Run the project's declared root install in ``root`` when it is due.

    Nothing declared: nothing runs, and the result says so. Raises
    ``ToolchainDeclarationError`` when the declaration cannot be read.
    """
    return EnvironmentBootstrapper(root).bootstrap(declared_root_install(root))


def rerun_declared_install_if_due(root: Path) -> Optional[BootstrapResult]:
    """After a turn: run the declared root install again if a file it serves
    changed since it last ran. ``None`` when nothing is declared, so the
    per-turn log stays quiet; otherwise the bootstrap's result (a skip when
    nothing it serves changed)."""
    install = declared_root_install(root)
    if install is None:
        return None
    return EnvironmentBootstrapper(root).bootstrap(install)


__all__ = [
    "NO_INSTALL_DECLARED",
    "DeclaredInstall",
    "BootstrapFailureDetail",
    "BootstrapResult",
    "EnvironmentBootstrapper",
    "declared_root_install",
    "bootstrap_worktree",
    "rerun_declared_install_if_due",
]
