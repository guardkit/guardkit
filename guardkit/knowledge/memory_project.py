"""Which memory does this build use, and why.

ONE function answers it: :func:`resolve_memory_project`. Everything that needs a
memory name asks here, so there is a single place to read when a build turns out
to have read or written under a name nobody expected.

The order of authority (design pass 2026-09-21, item 2):

1. **A name handed over on purpose**, through the ``GUARDKIT_MEMORY_PROJECT``
   setting, and only when that setting is actually set and not empty. This is how
   a caller that already knows the project's declaration (it read it from the
   commit the work started from) tells this process which memory to use, so the
   two cannot disagree and a stale checkout cannot supply the name.
2. **The project's own declaration**: ``memory: project: <name>`` in the
   project's ``.guardkit/config.yaml``, read from the folder the build works in.
   This is the by-hand case, where nothing handed a name over.
3. **Nothing.** Memory is then OFF for this build: nothing is read and nothing is
   written, under any name. There is no fallback name, deliberately — a build
   that quietly files its work under somebody else's name is worse than a build
   with no memory at all, which is what happened up to 2026-09-21.

A name that breaks the memory service's rule (letters, digits and underscores)
is REFUSED with a plain sentence. It is never quietly rewritten into something
acceptable, because the rewritten name is then a second place records can hide.

Nothing here knows or cares what language the project is written in, what it
tests with, or how it is laid out. It reads one optional file in the project's
own folder and one setting.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Optional

import yaml

logger = logging.getLogger(__name__)

#: The setting a caller uses to hand a name over on purpose.
MEMORY_PROJECT_ENV = "GUARDKIT_MEMORY_PROJECT"

#: Where a project declares its own name, relative to the folder being built.
CONFIG_RELATIVE_PATH = Path(".guardkit") / "config.yaml"

#: The declaration block and the key inside it.
MEMORY_KEY = "memory"
PROJECT_KEY = "project"

#: The memory service's rule for a name: letters, digits and underscores only
#: (``fleet-memory/src/fleet_memory/payloads/base.py`` IDENTIFIER_PATTERN). A
#: name that fails this is rejected by the service itself, so a build that used
#: it would lose every write.
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

#: A declaration file larger than this is ignored rather than parsed, so a huge
#: or hostile file cannot stall a build. Matches the existing bounded reader in
#: ``autobuild_context_loader._load_relevant_pattern_document_tags``.
MAX_CONFIG_BYTES = 256 * 1024

#: A name longer than this is refused. The service sets no limit; this one keeps
#: an accidental paste (a whole file, a token) out of every natural key.
MAX_NAME_LENGTH = 128

Source = Literal["handover", "declaration", "none", "refused", "failed"]


@dataclass(frozen=True)
class MemoryProjectResolution:
    """The answer, and the plain sentence that explains it.

    Attributes:
        project: The memory name to use, or ``None`` when memory is off.
        source: Where the name came from — ``"handover"`` (the setting),
            ``"declaration"`` (the project's own file), ``"none"`` (nothing said),
            ``"failed"`` (resolving it raised: memory is off, said so),
            or ``"refused"`` (something was said and it is not usable).
        message: One plain sentence (or a short block) for a human to read. For
            ``"none"`` and ``"refused"`` it says exactly which line to add to
            which file.
    """

    project: Optional[str]
    source: Source
    message: str

    @property
    def is_on(self) -> bool:
        """Whether this build has a memory to read and write."""
        return bool(self.project)


def _declaration_path(project_root: Path) -> Path:
    return Path(project_root) / CONFIG_RELATIVE_PATH


def _how_to_turn_it_on(project_root: Optional[Path]) -> str:
    """The two lines to add, and the file to add them to."""
    where = (
        str(_declaration_path(project_root))
        if project_root is not None
        else "the project's .guardkit/config.yaml"
    )
    return (
        f"To turn memory on, add these two lines to {where}:\n"
        f"  memory:\n"
        f"    project: <a name of letters, digits and underscores>"
    )


def _check_name(raw: Any, where: str, project_root: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    """Return ``(name, refusal)``: exactly one of the two is set.

    A usable name comes back stripped of surrounding blanks and otherwise
    untouched. Anything else comes back as a plain sentence saying why not.
    """
    if not isinstance(raw, str):
        return None, (
            f"memory: OFF — the memory name in {where} is not text "
            f"(it reads as {type(raw).__name__}). "
            f"Nothing will be read and nothing will be written until it is fixed.\n"
            f"{_how_to_turn_it_on(project_root)}"
        )
    name = raw.strip()
    if not name:
        return None, (
            f"memory: OFF — the memory name in {where} is empty. "
            f"Nothing will be read and nothing will be written until it is fixed.\n"
            f"{_how_to_turn_it_on(project_root)}"
        )
    if len(name) > MAX_NAME_LENGTH:
        return None, (
            f"memory: OFF — the memory name in {where} is longer than "
            f"{MAX_NAME_LENGTH} characters. "
            f"Nothing will be read and nothing will be written until it is fixed.\n"
            f"{_how_to_turn_it_on(project_root)}"
        )
    if not NAME_PATTERN.fullmatch(name):
        return None, (
            f"memory: OFF — the memory name {name!r} in {where} is not allowed. "
            f"A memory name may contain only letters, digits and underscores, and "
            f"it is never rewritten for you, because the rewritten name would be a "
            f"second place records can hide. "
            f"Nothing will be read and nothing will be written until it is fixed.\n"
            f"{_how_to_turn_it_on(project_root)}"
        )
    return name, None


def read_declared_project(
    project_root: Optional[Path],
) -> tuple[Optional[str], Optional[str], bool]:
    """Read ``memory: project:`` from the project's own settings file.

    Bounded and safe, exactly like the reader already on the builder's path
    (``autobuild_context_loader._load_relevant_pattern_document_tags``): inside
    the given folder only, no symlink escape, a size cap, the shape checked, and
    it never raises.

    Returns ``(name, refusal, declared)``:
        * ``(name, None, True)`` — a usable declared name.
        * ``(None, sentence, True)`` — something was declared and is not usable.
        * ``(None, None, False)`` — nothing was declared (no file, no block).
    """
    if project_root is None:
        return None, None, False
    try:
        root = Path(project_root).resolve()
    except (OSError, RuntimeError, ValueError):
        return None, None, False
    config_path = Path(project_root) / CONFIG_RELATIVE_PATH
    where = str(config_path)
    try:
        if config_path.is_symlink() or not config_path.is_file():
            return None, None, False
        if not config_path.resolve().is_relative_to(root):
            logger.warning(
                "memory: the settings file at %s points outside the project "
                "folder; ignoring it.",
                where,
            )
            return None, None, False
        if config_path.stat().st_size > MAX_CONFIG_BYTES:
            logger.warning(
                "memory: the settings file at %s is larger than %d bytes; "
                "ignoring it.",
                where,
                MAX_CONFIG_BYTES,
            )
            return None, None, False
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        logger.warning("memory: cannot read the settings file at %s: %s", where, exc)
        return None, None, False
    if not isinstance(data, dict):
        logger.warning(
            "memory: the settings file at %s is not a set of settings; ignoring it.",
            where,
        )
        return None, None, False
    if MEMORY_KEY not in data:
        return None, None, False
    block = data[MEMORY_KEY]
    if not isinstance(block, dict) or PROJECT_KEY not in block:
        # A `memory:` block with no `project:` is ordinary — other settings live
        # in that block too. Nothing is declared about the name.
        return None, None, False
    name, refusal = _check_name(block[PROJECT_KEY], where, Path(project_root))
    return name, refusal, True


def resolve_memory_project(
    project_root: Optional[Path],
    env: Optional[Mapping[str, str]] = None,
) -> MemoryProjectResolution:
    """Answer "what memory does this build use, and why" — the only answer.

    Args:
        project_root: The folder the build works in, whose ``.guardkit/config.yaml``
            carries the project's own declaration. ``None`` when there is no such
            folder; then only a handed-over name can turn memory on.
        env: The settings to read the handover from. Defaults to this process's.

    Returns:
        A :class:`MemoryProjectResolution`. It never raises.
    """
    settings = os.environ if env is None else env
    root = Path(project_root) if project_root is not None else None

    handed_over = settings.get(MEMORY_PROJECT_ENV)
    if handed_over is not None and str(handed_over).strip():
        name, refusal = _check_name(handed_over, f"the {MEMORY_PROJECT_ENV} setting", root)
        if name is not None:
            return MemoryProjectResolution(
                project=name,
                source="handover",
                message=(
                    f"memory: ON (project={name}) — this name was handed to the "
                    f"build on purpose, through the {MEMORY_PROJECT_ENV} setting."
                ),
            )
        return MemoryProjectResolution(project=None, source="refused", message=refusal or "")

    declared, refusal, was_declared = read_declared_project(root)
    if declared is not None:
        return MemoryProjectResolution(
            project=declared,
            source="declaration",
            message=(
                f"memory: ON (project={declared}) — the project declares this name "
                f"in {_declaration_path(root)}."
            ),
        )
    if was_declared:
        return MemoryProjectResolution(project=None, source="refused", message=refusal or "")

    return MemoryProjectResolution(
        project=None,
        source="none",
        message=(
            "memory: OFF — this project has not said which memory it uses, so "
            "this run reads no prior decisions and writes no outcomes. Nothing "
            "is read or written under any other name.\n"
            f"{_how_to_turn_it_on(root)}"
        ),
    )


def log_resolution(resolution: MemoryProjectResolution) -> None:
    """Say the answer out loud, at a level nobody can miss when memory is off."""
    if resolution.is_on:
        logger.info("%s", resolution.message)
    else:
        logger.warning("%s", resolution.message)
