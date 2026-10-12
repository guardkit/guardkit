"""THE LAUNCH DECLARATION — what a project's own commands need from their shell.

A project names, in its own ``.guardkit/config.yaml``, the settings its builds
need (12 October 2026, web readiness W1/R4):

.. code-block:: yaml

    launch:
      settings: [PLAYWRIGHT_BROWSERS_PATH]           # Forge's block, 22 September 2026
      scratch: [GOPATH, GOCACHE, npm_config_cache]   # new here

``settings`` is Forge's existing declaration. Forge reads it at the commit the
work starts from and passes each named value into this process's environment,
only when the launching process has one (``forge.launch_environment``). The
builder's and verifier's shell does NOT inherit this process's environment
(guardkitfactory ``backend_config``: ``inherit_env=False``, ``PATH``,
``HOME=<worktree>``), so the same names are carried into it from here, again
only when set.

``scratch`` names are each set to ``<scratch folder>/toolchain/<NAME>``,
created on demand. The scratch folder is the one GuardKit already keeps per
worktree inside its git directory (``paths.builder_scratch_dir``): outside the
project tree, ``git status`` and the candidate. Without a scratch folder the
command does not run; nothing falls back into the worktree. Forge reads only
``settings`` and treats other keys in the block as ordinary, so one block holds
both lists.

Central code carries the names as text and knows nothing about what tool they
belong to (CLAUDE.md rule 5). A project without the block is unchanged.

The name rules MIRROR Forge's ``declared_setting_refusal``. GuardKit cannot
import Forge (Forge depends on GuardKit, not the other way round), so the rules
are copied here; keep the two in step.

Like the toolchain declaration, the block lives inside the tree the Player
edits, so it is pinned before turn 1 from the canonical repo root
(:func:`snapshot_task_launch`) and only that copy is read during the build.
"""

from __future__ import annotations

import json
import logging
import os
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

LAUNCH_KEY = "launch"
SETTINGS_KEY = "settings"
SCRATCH_KEY = "scratch"

# Scratch entries live here, under the worktree's scratch folder.
SCRATCH_SUBDIR = "toolchain"

# ---- mirrored from forge.launch_environment (22 September 2026) ----------
DECLARED_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_DECLARED_NAME_LENGTH = 128
MAX_DECLARED_SETTINGS = 32
RESERVED_PREFIXES: Tuple[str, ...] = (
    "FORGE_",
    "GUARDKIT_",
    "FLEET_MEMORY_",
    "OPENAI_",
    "ANTHROPIC_",
)
RESERVED_NAMES: Tuple[str, ...] = ("PATH", "HOME", "TMPDIR", "SSH_AUTH_SOCK")
RESERVED_CREDENTIAL_WORDS: Tuple[str, ...] = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "APIKEY",
    "CREDENTIAL",
    "PRIVATE_KEY",
)

_SNAPSHOT_SUBDIR = "toolchain"
_SNAPSHOT_FILE = "launch.json"


class LaunchEnvironmentError(OSError):
    """The declared launch environment could not be prepared.

    An ``OSError`` so that every caller which already treats "the command
    could not start" as that command's failure treats this the same way, with
    this plain message.
    """


def declared_setting_refusal(name: object) -> Optional[str]:
    """``None`` when a project may declare this name, or the sentence why not.

    The same rules as Forge's function of the same name.
    """
    if not isinstance(name, str):
        return f"a declared name must be text (this one reads as {type(name).__name__})"
    candidate = name.strip()
    if not candidate:
        return "a declared name is empty"
    if len(candidate) > MAX_DECLARED_NAME_LENGTH:
        return f"a declared name is longer than {MAX_DECLARED_NAME_LENGTH} characters"
    if not DECLARED_NAME_PATTERN.fullmatch(candidate):
        return (
            f"{candidate!r} is not the shape of a setting name: letters, digits "
            "and underscores, never starting with a digit"
        )
    upper = candidate.upper()
    for prefix in RESERVED_PREFIXES:
        if upper.startswith(prefix):
            return f"{candidate!r} starts with {prefix}, which the factory keeps for itself"
    if upper in RESERVED_NAMES:
        return f"{candidate!r} is one of the settings the factory sets itself"
    for word in RESERVED_CREDENTIAL_WORDS:
        if word in upper:
            return f"{candidate!r} is credential-shaped (it contains {word!r})"
    return None


@dataclass(frozen=True)
class LaunchDeclaration:
    """The names a project's ``launch:`` block declares."""

    settings: Tuple[str, ...] = ()
    scratch: Tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.settings and not self.scratch

    def as_backend_argument(self) -> Dict[str, list]:
        """The plain mapping ``build_autobuild_backend`` accepts."""
        return {SETTINGS_KEY: list(self.settings), SCRATCH_KEY: list(self.scratch)}


def _names(block: Mapping[str, Any], key: str) -> Tuple[str, ...]:
    raw = block.get(key)
    if raw is None:
        return ()
    if isinstance(raw, str) or not isinstance(raw, (list, tuple)):
        raise ValueError(
            f"`launch.{key}` must be a list of names (it reads as {type(raw).__name__})"
        )
    if len(raw) > MAX_DECLARED_SETTINGS:
        raise ValueError(
            f"`launch.{key}` names {len(raw)} settings; at most "
            f"{MAX_DECLARED_SETTINGS} are allowed"
        )
    names: list = []
    for entry in raw:
        refusal = declared_setting_refusal(entry)
        if refusal is not None:
            raise ValueError(f"`launch.{key}`: {refusal}")
        name = entry.strip()
        if name in names:
            raise ValueError(f"`launch.{key}` lists {name} more than once")
        names.append(name)
    return tuple(names)


def parse_launch_block(raw: Any) -> LaunchDeclaration:
    """Validate a raw ``launch`` mapping. Raises ``ValueError`` when malformed.

    A ``launch`` value that is not a mapping declares nothing, as in Forge.
    """
    if not isinstance(raw, dict):
        return LaunchDeclaration()
    settings = _names(raw, SETTINGS_KEY)
    scratch = _names(raw, SCRATCH_KEY)
    both = sorted(set(settings) & set(scratch))
    if both:
        raise ValueError(
            f"{', '.join(both)} cannot be both passed through (`launch.settings`) "
            "and a scratch folder (`launch.scratch`)"
        )
    return LaunchDeclaration(settings=settings, scratch=scratch)


def load_launch_declaration(repo_root: Path) -> Optional[LaunchDeclaration]:
    """Read ``launch:`` from ``<repo_root>/.guardkit/config.yaml``.

    Never raises. ``None`` when the file or block is absent or declares
    nothing. A malformed block is logged at ERROR and degrades to ``None`` —
    the same posture as ``load_toolchain_declaration``.
    """
    from guardkit.orchestrator.toolchain_declaration import CONFIG_RELATIVE_PATH

    config_path = Path(repo_root) / CONFIG_RELATIVE_PATH
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — a broken config never crashes a build
        logger.warning("Failed to read %s: %s", config_path, exc)
        return None
    if not isinstance(data, dict) or data.get(LAUNCH_KEY) is None:
        return None
    try:
        declaration = parse_launch_block(data[LAUNCH_KEY])
    except ValueError as exc:
        logger.error(
            "MALFORMED `launch:` block in %s — its settings and scratch "
            "folders will NOT be applied until it is fixed: %s",
            config_path,
            exc,
        )
        return None
    return None if declaration.is_empty else declaration


def launch_snapshot_path(task_id: str, worktree_path: Path) -> Path:
    """Where the pinned copy lives: beside the toolchain snapshot."""
    from guardkit.orchestrator.paths import TaskArtifactPaths

    return (
        TaskArtifactPaths.task_private_dir(task_id, Path(worktree_path))
        / _SNAPSHOT_SUBDIR
        / _SNAPSHOT_FILE
    )


def snapshot_task_launch(
    task_id: str, worktree_path: Path, repo_root: Path
) -> Optional[Path]:
    """Pin the canonical ``launch:`` block pre-turn-1. Never raises."""
    try:
        declaration = load_launch_declaration(Path(repo_root))
        if declaration is None:
            return None
        path = launch_snapshot_path(task_id, worktree_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(declaration), indent=2), encoding="utf-8")
        logger.info(
            "Pinned the launch declaration for %s pre-turn-1 (settings=%s "
            "scratch=%s) at %s",
            task_id,
            list(declaration.settings),
            list(declaration.scratch),
            path,
        )
        return path
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("launch snapshot failed for %s (%s)", task_id, exc)
        return None


def load_launch_snapshot(
    task_id: Optional[str], worktree_path: Path
) -> Optional[LaunchDeclaration]:
    """The pinned declaration for a task, or ``None``. Never raises.

    Never falls back to the live file in the worktree.
    """
    if not task_id:
        return None
    try:
        path = launch_snapshot_path(task_id, worktree_path)
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        declaration = parse_launch_block(raw)
    except Exception as exc:  # noqa: BLE001 — an unreadable snapshot is absence
        logger.warning(
            "could not read the launch snapshot for %s (%s) — treating the "
            "declaration as absent",
            task_id,
            exc,
        )
        return None
    return None if declaration.is_empty else declaration


def _private_directory(directory: Path) -> Path:
    """Create ``directory`` (mode 0700) or reuse it; refuse anything else."""
    try:
        if not os.path.lexists(directory):
            directory.mkdir(mode=0o700)
        status = directory.lstat()
    except OSError as exc:
        raise LaunchEnvironmentError(
            f"the declared scratch folder could not be created at {directory}: {exc}"
        ) from exc
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        raise LaunchEnvironmentError(
            f"the declared scratch folder is not a real folder: {directory}"
        )
    return directory


def apply_launch_environment(
    env: Optional[Dict[str, str]],
    declaration: Optional[LaunchDeclaration],
    worktree: Path,
) -> Optional[Dict[str, str]]:
    """Add the declared settings and scratch folders to a command's environment.

    THE ONE HELPER every GuardKit caller of a project command uses. ``env`` is
    the environment the caller already built (``None`` meaning "inherit this
    process's"). With no declaration it is returned as it is, so callers stay
    byte-for-byte unchanged.

    Otherwise a new dictionary: ``settings`` names copied from this process's
    environment when set there, and each ``scratch`` name set to
    ``<scratch folder>/toolchain/<NAME>`` for ``worktree``.

    Raises
    ------
    LaunchEnvironmentError
        When scratch names are declared and the worktree has no usable scratch
        folder, or a folder cannot be created.
    """
    if declaration is None or declaration.is_empty:
        return env
    result = dict(os.environ if env is None else env)
    for name in declaration.settings:
        value = os.environ.get(name)
        if value is not None:
            result[name] = value
    if declaration.scratch:
        from guardkit.orchestrator.paths import prepare_builder_scratch_dir

        folder = prepare_builder_scratch_dir(Path(worktree))
        if folder is None:
            raise LaunchEnvironmentError(
                f"the project declares `launch.scratch` "
                f"({', '.join(declaration.scratch)}), but the worktree {worktree} "
                "has no scratch folder, so the command was not run. Nothing is "
                "put inside the project instead."
            )
        base = _private_directory(folder / SCRATCH_SUBDIR)
        for name in declaration.scratch:
            result[name] = str(_private_directory(base / name))
    return result


def apply_task_launch_environment(
    env: Optional[Dict[str, str]], task_id: Optional[str], worktree: Path
) -> Optional[Dict[str, str]]:
    """:func:`apply_launch_environment` with the task's pinned declaration.

    For callers that hold a task id rather than a declaration (the Coach's
    own test and coverage commands). No task id or no pinned block: ``env``
    unchanged.
    """
    if not task_id:
        return env
    return apply_launch_environment(
        env, load_launch_snapshot(task_id, worktree), worktree
    )


__all__ = [
    "LAUNCH_KEY",
    "LaunchDeclaration",
    "LaunchEnvironmentError",
    "apply_launch_environment",
    "apply_task_launch_environment",
    "declared_setting_refusal",
    "launch_snapshot_path",
    "load_launch_declaration",
    "load_launch_snapshot",
    "parse_launch_block",
    "snapshot_task_launch",
]
