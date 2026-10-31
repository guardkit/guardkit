"""THE DECLARATION — a repo's own toolchain commands (TS-lane D.1b).

The factory could only ever prove work in Python, for one reason: the LAST
step of finding the tests defaulted to ``pytest tests/ -v --tb=short`` with a
shrug in the log. Everything around that step is already language-blind — the
verdict is an exit code, the model seats have zero language hits, the
conformance rules say "stack-agnostic" in their own docstring.

So the cure is not "add TypeScript support". It is: **the target repo declares
its own commands, and the verification loop honours the declaration.** pytest
becomes one declaration among many.

Where it lives
--------------
``<repo>/.guardkit/config.yaml``, top-level ``toolchain:`` block — the repo
level, because a toolchain is a property of the REPO and every existing
mechanism that answers "how do I run this repo's tests" is already repo-keyed
(``_scan_directory`` reads repo manifests; the deleted pytest default was a repo-level assumption wearing
a per-task disguise). The reader precedent is
``AutoBuildOrchestrator._load_coach_config``, which reads the same file.

Shape
-----
.. code-block:: yaml

    toolchain:
      test:            "npm test"          # verdict-bearing
      install:         "npm ci"            # environment
      install_timeout: 900
      test_timeout:    600
      typecheck:       "npm run typecheck" # non-verdict legs (see below)
      lint:            "npm run lint"
      build:           "npm run build"
      runtime: {node: "v24.15.0"}
      environment_inventory: "npm ls --all" # evidence only (run_evidence)

Only ``test`` is verdict-bearing by default. ``typecheck`` / ``lint`` /
``build`` are *available* — a plan that wants one enforced writes it as a
``conformance: assert_command`` rule, which is already a shipped, wired,
verdict-bearing path. We do not invent a second enforcement mechanism.

Two laws (design §B.4)
----------------------
**LAW — exit code is the verdict.** A declared command passes iff
``returncode == 0``. Parsing a command's stdout is advisory only; it may
enrich a checkpoint or a summary, it may never decide anything. (Until 1
November 2026 a per-framework "a test ran" rule could turn a 0 into "no
test signal"; it was removed with the stack rows it used. The
``absent_substrings``, ``ran_marker_regex`` and ``requires_ran_marker``
fields are still accepted, so a project that declares them keeps its
toolchain, and are not used.)

**LAW — the declaration is snapshotted before the model's first turn.** This
file lives INSIDE the target repo, which means it lives inside the worktree
the builder is editing. Without a snapshot, a Player turn could rewrite
``toolchain.test`` to ``true`` and green itself. :func:`snapshot_task_toolchain`
is pinned at the same pre-turn-1 call site as ``snapshot_task_conformance``,
reads the declaration COMMITTED at the worktree's HEAD (the canonical
``repo_root`` tree only when the worktree is not a git checkout), and writes
OUTSIDE the shared worktree. Committed, never the working file: at a task's
first turn HEAD holds only what earlier tasks of the same feature finished and
the reviewer saw, so a test setup declared by an earlier task reaches the tasks
after it (a recorded Go feature build, 29 October 2026: its second task
declared the Go tests, and the four tasks after it never ran them because the
pin read the main checkout), while an uncommitted edit in the worktree still
cannot. The pinned copy is what executes for the whole build —
:func:`load_toolchain_snapshot` is the ONLY reader the verdict path uses. It
never falls back to the live file: no snapshot means no declaration, and the
check reports that nothing is declared (GuardKit never guesses a command).

Environment resolution (design §B.5)
------------------------------------
Declared commands run **with the worktree as cwd** and **inherit the daemon's
environment**, PATH included. The daemon's PATH is fixed in a systemd unit
(``Environment=PATH=%h/.agentecflow/bin:%h/.local/bin:...``) which never sees
nvm, so ``node`` resolves only because D.0 puts
``~/.local/bin/{node,npm,npx}`` symlinks — pointing at a pinned version — on
that already-present PATH. **An nvm ``source`` line must NEVER be baked into
this executor**: nvm is a login-shell rc thing, systemd user units never
source it, and an executor that shells out to an interactive rc file is both
unreproducible and invisible. The environment is a property of the estate
(D.0), not of the builder.

``runtime:`` records the version pin the estate fence is expected to satisfy.
D.1b stores it; the pre-install assertion that both pins agree is NOT wired
here (see the lane report's honest gaps).

PER-COMPONENT SCOPING (the monorepo seam, design §B.2(iii))
-----------------------------------------------------------
One flat block per repo cannot describe a repo that is TWO products in one
tree (a Python backend at the root, a Flutter app under ``app/``). There is no
single ``test:`` string that is correct for such a repo: declare the backend's
and every ``app/`` task silently gets the Python suite as its verdict on Dart
work — the exact false signal this module was built to delete.

So the ONE declaration gains per-path sections:

.. code-block:: yaml

    toolchain:
      test: "uv run --no-sync python -m pytest -q"   # THE ROOT COMPONENT
      components:
        app:
          cwd:  "app"                                 # REQUIRED
          test: "flutter test"
          install: "flutter pub get"
          test_timeout: 900

* The TOP-level block keeps meaning **the root component** — unchanged.
* ``components:`` maps a component NAME to a FULL nested declaration (the same
  fields) plus a **required** ``cwd:`` — the repo-relative directory the
  commands run in. ``cwd`` is the field that makes it real: ``flutter test``
  needs the package root, and ``cd app && …`` baked into a command string is
  invisible to the snapshot reader and to anyone auditing the receipt.
* A task's tests are chosen by the files it changed (after-task check
  redesign, 31 October 2026). A file belongs to the declared component whose
  ``cwd`` holds it, the deepest one winning; a file under no component belongs
  to the root component. Each changed part's ``test`` runs once, in its own
  folder, and the task passes only when every one of them ran and passed.
* ``parts:`` is a list of folder patterns for parts that appear as the project
  grows. Each entry has ``under``, ``marker`` and the same command fields:
  every folder directly under ``under`` that holds the file ``marker`` is a
  part, tested with the entry's ``test`` in that folder. The folders are found
  in the tree when the check runs, so a folder made by this very task is
  tested at once; the commands still come from the pinned declaration.

  .. code-block:: yaml

      toolchain:
        parts:
          - under: apps
            marker: package.json
            test: "npm test"

* The full check before a merge is the root ``test`` plus every component's
  and every pattern part's ``test``, each in its own folder with its own
  ``test_timeout`` (:func:`full_check_parts`). ``feature_check`` is not part
  of it: it stays the build's own whole-feature check after the last wave.
* ``extra="forbid"`` holds at every level, so a typo'd component or part
  field is as loud as a typo'd root field.

**The snapshot law is unchanged, and that is why this shape was chosen.** The
pin is one whole-model ``model_dump`` read back by one ``model_validate``, so a
nested field round-trips byte-for-byte with ZERO snapshot changes. The Player
still cannot edit a component's test command mid-build.

**A part's ``install``** (a component's or a ``parts:`` entry's) runs before
that part's tests, in its folder: the first time the part is tested in a
worktree, and again only when the files directly in its folder have changed
(31 October 2026). A failed install is "the check could not run". The root
``install`` stays the build's own bootstrap (``environment_bootstrap``).
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# The repo-level config file, relative to the repo root. Same file
# ``_load_coach_config`` reads (the reader precedent, design §B.1).
CONFIG_RELATIVE_PATH = Path(".guardkit") / "config.yaml"

TOOLCHAIN_KEY = "toolchain"

# Bounds copied in spirit from ``AssertCommandRule`` (spec_conformance.py):
# every declared command is time-bounded, and the bound itself is validated so
# a typo'd 6000000 is loud rather than a hung build.
_DEFAULT_TIMEOUT = 300
_MAX_TIMEOUT = 3600

# Snapshot layout, mirroring ``spec_conformance``'s.
_SNAPSHOT_SUBDIR = "toolchain"
_SNAPSHOT_FILE = "toolchain.json"


class ToolchainDeclarationError(ValueError):
    """A declaration problem that must stop the build, raised only on request.

    :func:`load_toolchain_declaration` raises it when called with
    ``strict=True`` and either the declaration file exists but cannot be read,
    or a ``components.<name>.cwd`` is refused by the schema (a ``..`` segment,
    an absolute path, a ``~``). Every other malformed block keeps the loud
    log-and-ignore. ``component`` and ``cwd`` name the offending entry when
    there is one; ``cwd`` is the value as written.
    """

    def __init__(
        self,
        message: str,
        *,
        component: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.component = component
        self.cwd = cwd


class ToolchainRuntime(BaseModel):
    """Declared runtime version pins (``runtime: {node: "v24.15.0"}``).

    Recorded, not yet asserted — see the module docstring. ``extra="forbid"``
    so an unknown runtime name is a loud typo rather than a silent no-op.
    """

    model_config = ConfigDict(extra="forbid")

    node: Optional[str] = None
    python: Optional[str] = None
    dotnet: Optional[str] = None
    go: Optional[str] = None


class _ToolchainCommands(BaseModel):
    """The command fields shared by the root block and every component.

    Split out so ``components:`` is provably "the SAME fields" rather than a
    hand-copied near-twin that drifts. ``ToolchainDeclaration`` is this plus
    ``components``; ``ComponentToolchain`` is this plus a required ``cwd``.

    ``extra="forbid"`` is the point of the schema, not a detail: a repo that
    writes ``tests:`` instead of ``test:`` must be told, loudly, at load time
    — a silently-ignored declaration would read as "nothing declared" and
    look like the tool ignoring the repo.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- verdict-bearing ------------------------------------------------
    test: Optional[str] = Field(default=None, min_length=1)
    # Accepted and not run (31 October 2026: nothing measures coverage on the
    # check path). Kept in the schema because ``extra="forbid"`` would
    # otherwise drop the whole toolchain of a project that still declares it.
    coverage: Optional[str] = Field(default=None, min_length=1)
    coverage_timeout: int = Field(default=_DEFAULT_TIMEOUT, ge=1, le=_MAX_TIMEOUT)

    # ---- environment ----------------------------------------------------
    install: Optional[str] = Field(default=None, min_length=1)

    # ---- non-verdict legs (available to plans as assert_command rules) ---
    typecheck: Optional[str] = Field(default=None, min_length=1)
    lint: Optional[str] = Field(default=None, min_length=1)
    build: Optional[str] = Field(default=None, min_length=1)

    # ---- the whole-feature check (B9 correction, 2026-09-19) -------------
    # The one command that proves the FINISHED FEATURE at the surface the
    # person uses, run once after the last wave. Exit 0 is the only pass (the
    # standing law above). CONSUMED FROM THE ROOT BLOCK ONLY: a feature is a
    # property of the repository, not of one component. The field lives here,
    # with the other commands, so the root and component schemas stay provably
    # "the SAME fields".
    feature_check: Optional[str] = Field(default=None, min_length=1)
    feature_check_timeout: int = Field(default=600, ge=1, le=_MAX_TIMEOUT)

    # ---- the resolved-environment record (repair 7, 2026-10-12) ----------
    # OPTIONAL and evidence only: a command that prints what the environment
    # resolved to (a package list, say). When declared, GuardKit runs it just
    # before each declared command it measures, in that command's directory
    # and environment, and keeps the output with a SHA-256 on the command's
    # record. It never decides anything. There is no default: a project that
    # declares nothing is recorded as "not declared". See ``run_evidence``.
    environment_inventory: Optional[str] = Field(default=None, min_length=1)
    environment_inventory_timeout: int = Field(default=120, ge=1, le=600)

    # ---- bounded timeouts -----------------------------------------------
    # Both default to TODAY's hardcoded 300s, deliberately: a repo that
    # declares only ``test:`` must not silently acquire a different timeout
    # than it had before the declaration existed. A repo that needs longer
    # (``npm ci`` on a real app) declares the number it needs.
    test_timeout: int = Field(default=_DEFAULT_TIMEOUT, ge=1, le=_MAX_TIMEOUT)
    install_timeout: int = Field(default=_DEFAULT_TIMEOUT, ge=1, le=_MAX_TIMEOUT)

    # ---- accepted and not used (1 November 2026) -------------------------
    # They overlaid the removed per-framework "a test ran" rule. Kept in the
    # schema because ``extra="forbid"`` would otherwise drop the whole
    # toolchain of a project that still declares them.
    absent_substrings: Optional[List[str]] = None
    ran_marker_regex: Optional[str] = None
    requires_ran_marker: Optional[bool] = None

    # ---- explicit runtime pin -------------------------------------------
    runtime: Optional[ToolchainRuntime] = None

    @field_validator("ran_marker_regex")
    @classmethod
    def _regex_must_compile(cls, value: Optional[str]) -> Optional[str]:
        """A non-compiling regex is a loud declaration error, not a silent
        classifier that never matches (which would read as a false ABSENT)."""
        if value is None:
            return value
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"ran_marker_regex is not a valid regex: {exc}") from exc
        return value

    @property
    def has_classifier_overlay(self) -> bool:
        """True when the declaration overrides any stack-row absence field."""
        return (
            self.absent_substrings is not None
            or self.ran_marker_regex is not None
            or self.requires_ran_marker is not None
        )

    @property
    def is_empty(self) -> bool:
        """True for a ``toolchain: {}`` block that declares nothing at all."""
        return not any(
            (
                self.test,
                self.coverage,
                self.install,
                self.typecheck,
                self.lint,
                self.build,
                self.has_classifier_overlay,
                self.runtime,
                self.feature_check,
                self.environment_inventory,
            )
        )


class ComponentToolchain(_ToolchainCommands):
    """ONE component of a multi-product repo — the same fields, plus ``cwd``.

    ``cwd`` is REQUIRED and repo-relative. A component without a directory is
    not a component (it would be the root block wearing a name), so its
    absence is a loud declaration error rather than an implicit ``"."``.

    The containment rule is enforced HERE, at declaration time, not at
    execution time: an absolute path, a ``~``, or any ``..`` segment is a
    ValidationError. Design §G: *"a cwd that escapes the worktree must be a
    declaration error, not a path that resolves."*
    """

    cwd: str = Field(min_length=1)

    @field_validator("cwd")
    @classmethod
    def _cwd_must_be_contained(cls, value: str) -> str:
        return _contained_folder(value, "cwd")


def _contained_folder(value: str, field: str) -> str:
    """A repo-relative folder, normalised; refuses ``~``, absolute and ``..``."""
    raw = value.strip()
    if not raw:
        raise ValueError(f"{field} must not be blank")
    if raw.startswith("~"):
        raise ValueError(
            f"{field} must be repo-relative, not a home-relative path: {value!r}"
        )
    candidate = PurePosixPath(raw.replace("\\", "/"))
    if candidate.is_absolute() or raw.startswith("/"):
        raise ValueError(f"{field} must be repo-relative, not absolute: {value!r}")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(
            f"{field} must not escape the worktree (no `..` segments): {value!r}"
        )
    # Normalise "./app/" -> "app" so the receipt and the snapshot agree.
    parts = [p for p in candidate.parts if p not in (".", "")]
    return "/".join(parts) if parts else "."


class PartFolders(_ToolchainCommands):
    """One ``toolchain.parts`` entry: a folder pattern for parts.

    Every folder directly under ``under`` that holds the file ``marker`` is a
    part, and its commands run in that folder. ``marker`` is a plain file name
    the project chooses; GuardKit attaches no meaning to it.
    """

    under: str = Field(min_length=1)
    marker: str = Field(min_length=1)

    @field_validator("under")
    @classmethod
    def _under_must_be_contained(cls, value: str) -> str:
        return _contained_folder(value, "under")

    @field_validator("marker")
    @classmethod
    def _marker_is_a_file_name(cls, value: str) -> str:
        name = value.strip()
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            raise ValueError(f"marker must be a plain file name: {value!r}")
        return name


class LanguageServer(BaseModel):
    """One language server the repo names for code tools (28 October 2026).

    guardkitfactory's ``code_references`` tool asks the server for a symbol's
    references. The factory keeps no list of languages or servers: the repo
    names which one to run (``command``, a program the factory's image
    provides), for which files, from which folder, with which settings.
    Nothing here installs or runs anything; GuardKit only accepts the shape so
    a repo that declares a server keeps the rest of its toolchain. The tool
    checks the values (program names only, a root inside the repo, no PATH in
    ``env``). ``extra="forbid"`` so a typo'd key is loud, as everywhere here.
    """

    model_config = ConfigDict(extra="forbid")

    command: List[str] = Field(min_length=1)
    files: List[str] = Field(min_length=1)
    root: str = "."
    env: Optional[Dict[str, str]] = None
    initialization_options: Optional[Any] = None
    language_id: Optional[str] = None


class ToolchainDeclaration(_ToolchainCommands):
    """The repo's declared toolchain: THE ROOT COMPONENT, plus its components.

    The top-level command fields are the root component's — byte-for-byte the
    meaning they had before ``components:`` existed. ``components`` is
    ``Optional`` and defaults to ``None``, so every repo with a flat
    declaration is unchanged (design §G).
    """

    # ---- per-path sections (the monorepo seam, design §B.2(iii)) ---------
    components: Optional[Dict[str, ComponentToolchain]] = None
    # ---- folder patterns for parts (31 October 2026) ---------------------
    parts: Optional[List[PartFolders]] = None

    # ---- code tools (read by guardkitfactory, not by GuardKit) -----------
    language_servers: Optional[List[LanguageServer]] = None

    @field_validator("components")
    @classmethod
    def _component_names_must_be_usable(
        cls, value: Optional[Dict[str, "ComponentToolchain"]]
    ) -> Optional[Dict[str, "ComponentToolchain"]]:
        """A blank or whitespace-bearing component name is a typo: it is
        shown in receipts and logs as the part's name."""
        if value is None:
            return value
        for name in value:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("component names must be non-empty strings")
            if name != name.strip() or any(c.isspace() for c in name):
                raise ValueError(
                    f"component name {name!r} must not contain whitespace"
                )
        return value

    @property
    def is_empty(self) -> bool:
        """True for a ``toolchain: {}`` block that declares nothing at all.

        A block that declares ONLY ``components:`` is NOT empty — dropping it
        would silently un-declare every component task in the repo. Nor is one
        that declares only ``language_servers:`` (29 October 2026): dropping it
        would take the builder's references tool away for no reason. With no
        ``test:`` the declared test command is still None, so test detection
        runs as before.
        """
        return (
            super().is_empty
            and not self.components
            and not self.parts
            and not self.language_servers
        )

    @property
    def component_names(self) -> List[str]:
        """Declared component names, sorted — for loud error messages."""
        return sorted(self.components) if self.components else []

    def component(self, name: str) -> Optional[ComponentToolchain]:
        """Return the named component's declaration, or ``None`` if undeclared."""
        if not self.components:
            return None
        return self.components.get(name)


def parse_toolchain_block(raw: Any) -> ToolchainDeclaration:
    """Validate a raw ``toolchain`` mapping into a :class:`ToolchainDeclaration`.

    Loud on a typo'd key (``extra="forbid"``), an empty command string, an
    out-of-bounds timeout, or a non-compiling ``ran_marker_regex``. The raised
    message names the offending field so a repo owner can fix the YAML
    directly. Mirrors ``parse_conformance_block``.

    Raises
    ------
    ValueError
        If the block is malformed.
    """
    if not isinstance(raw, dict):
        raise ValueError(
            "Invalid `toolchain:` block in .guardkit/config.yaml: expected a "
            f"mapping of command names to values, got {type(raw).__name__}."
        )
    try:
        return ToolchainDeclaration.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(
            "Invalid `toolchain:` block in .guardkit/config.yaml:\n"
            f"{exc}\n\n"
            "Allowed keys: test, install, typecheck, lint, build, "
            "test_timeout, install_timeout, absent_substrings, "
            "ran_marker_regex, requires_ran_marker, runtime, components, "
            "parts, language_servers, feature_check, feature_check_timeout, "
            "environment_inventory, environment_inventory_timeout. "
            "Unknown keys are rejected — check for typos.\n"
            "Inside `components: <name>:` the SAME keys are allowed plus a "
            "REQUIRED repo-relative `cwd:`; each `parts:` entry takes them "
            "plus `under:` and `marker:`."
        ) from exc


def load_toolchain_declaration(
    repo_root: Path, *, strict: bool = False
) -> Optional[ToolchainDeclaration]:
    """Read the ``toolchain:`` block from ``<repo_root>/.guardkit/config.yaml``.

    Without ``strict`` it never raises. Returns ``None`` when the file is
    absent, unreadable, not a mapping, or carries no ``toolchain`` key — i.e.
    every repo that has not opted in behaves exactly as it did before this
    module existed.

    A MALFORMED block is logged at ERROR (the loud-degrade lesson: a typo must
    never be mistaken for "the tool ignored me") and degrades to ``None``, so
    a schema mistake in an opt-in feature cannot crash an existing build. The
    schema itself still raises for direct callers of
    :func:`parse_toolchain_block`.

    ``strict=True`` (the environment detector asks for it) raises
    :class:`ToolchainDeclarationError` in exactly two cases, so that neither
    silently falls back to guessing the install: the file exists but cannot be
    read or decoded, or a ``components.<name>.cwd`` is refused by the schema.
    A missing file still means "not declared", and a file that is not valid
    YAML, or any other malformed block, keeps the log-and-ignore above.
    """
    config_path = Path(repo_root) / CONFIG_RELATIVE_PATH
    if strict:
        # Look the file up and read it in one step, so only genuine absence
        # means "not declared". ``exists()`` itself raises when the
        # ``.guardkit`` directory cannot be searched; that, and any other
        # access or I/O failure, is a declaration that cannot be trusted.
        try:
            text = config_path.read_text(encoding="utf-8")
        except (FileNotFoundError, NotADirectoryError):
            return None
        except (OSError, UnicodeDecodeError) as exc:
            raise ToolchainDeclarationError(
                f"The toolchain declaration {config_path} cannot be looked up "
                f"or read ({exc}), so the declared install cannot be trusted."
            ) from exc
    else:
        if not config_path.exists():
            return None
        try:
            text = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Failed to read %s: %s", config_path, exc)
            return None
    return _declaration_from_text(text, config_path, strict=strict)


def _declaration_from_text(
    text: str, config_path: Any, *, strict: bool = False
) -> Optional[ToolchainDeclaration]:
    """Parse a ``.guardkit/config.yaml`` text the way the loader does.

    ``config_path`` only names the source in log lines (a path, or
    ``HEAD:.guardkit/config.yaml`` for a committed copy).
    """
    try:
        data = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 — a broken config never crashes a build
        logger.warning("Failed to read %s: %s", config_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    raw = data.get(TOOLCHAIN_KEY)
    if raw is None:
        return None
    try:
        declaration = parse_toolchain_block(raw)
    except ValueError as exc:
        if strict:
            _raise_for_refused_component_cwd(exc.__cause__, config_path)
        logger.error(
            "MALFORMED `toolchain:` block in %s — the declaration will NOT be "
            "used for this repo until it is fixed, so nothing is declared for "
            "it. %s",
            config_path,
            exc,
        )
        return None
    if declaration.is_empty:
        logger.warning(
            "`toolchain:` block in %s declares nothing — ignoring it.",
            config_path,
        )
        return None
    return declaration


def _raise_for_refused_component_cwd(cause: Any, config_path: Path) -> None:
    """Raise :class:`ToolchainDeclarationError` for a refused component ``cwd``.

    Looks only at schema errors located at ``components.<name>.cwd``; any
    other validation error returns quietly so the caller logs and ignores it.
    """
    if not isinstance(cause, ValidationError):
        return
    for error in cause.errors():
        loc = error.get("loc", ())
        if len(loc) == 3 and loc[0] == "components" and loc[2] == "cwd":
            component = str(loc[1])
            written = error.get("input")
            raise ToolchainDeclarationError(
                f"Component {component!r} in {config_path} declares cwd "
                f"{written!r}, which is refused: {error.get('msg')}. The "
                "build stops rather than guess the install without the "
                "declaration.",
                component=component,
                cwd=written if isinstance(written, str) else None,
            )


# =========================================================================
# Snapshot at task load (design §B.4 — the crux, NOT optional)
# =========================================================================
#
# SEAM (pinned): the snapshot fires in ``AutoBuildOrchestrator.orchestrate``
# immediately after ``_setup_phase`` creates the worktree and before Phase
# 2/3 — the SAME pre-turn-1 pin as ``snapshot_task_conformance``.
# CONSTRAINT: pre-turn-1 and Player-unreachable. It writes into
# ``TaskArtifactPaths.task_private_dir``, which resolves OUTSIDE the shared
# worktree, and it READS from ``repo_root`` (the canonical tree the Player has
# not touched). A Player that rewrites ``.guardkit/config.yaml`` mid-build
# changes nothing, because the executor reads THIS snapshot and never the live
# file.


def toolchain_snapshot_paths(task_id: str, worktree_path: Path) -> Dict[str, Path]:
    """Return the snapshot dir + file for a task. Pure path derivation."""
    from guardkit.orchestrator.paths import TaskArtifactPaths

    base = (
        TaskArtifactPaths.task_private_dir(task_id, Path(worktree_path))
        / _SNAPSHOT_SUBDIR
    )
    return {"dir": base, "file": base / _SNAPSHOT_FILE}


def load_committed_toolchain_declaration(
    worktree_path: Path,
) -> Tuple[bool, Optional[ToolchainDeclaration]]:
    """Read the declaration committed at ``worktree_path``'s HEAD.

    Returns ``(True, declaration)`` when the worktree is a git checkout (the
    declaration is ``None`` when that commit has no config file or no
    ``toolchain:`` block), and ``(False, None)`` when git cannot answer, so
    the caller can fall back. Never raises.
    """
    try:
        from guardkit.lib.project_git import run_git

        inside = run_git(
            ["rev-parse", "--is-inside-work-tree"], cwd=Path(worktree_path), timeout=30
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return False, None
        shown = run_git(
            ["show", f"HEAD:{CONFIG_RELATIVE_PATH.as_posix()}"],
            cwd=Path(worktree_path), timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Could not ask git for %s's committed config (%s)", worktree_path, exc)
        return False, None
    if shown.returncode != 0:
        # A checkout whose HEAD has no config file declares nothing.
        return True, None
    return True, _declaration_from_text(
        shown.stdout, f"{worktree_path} HEAD:{CONFIG_RELATIVE_PATH.as_posix()}"
    )


def snapshot_task_toolchain(
    task_id: str,
    worktree_path: Path,
    repo_root: Path,
) -> Optional[Path]:
    """Snapshot the toolchain declaration pre-turn-1.

    The source is the declaration committed at the worktree's HEAD, so a
    feature task sees what earlier tasks of the feature declared; the
    ``repo_root`` tree is read only when the worktree is not a git checkout.

    Returns the snapshot file path when a declaration was captured, else
    ``None`` (no declaration, or an error — both mean the build behaves
    exactly as it did before the declaration existed). Never raises.

    A fresh snapshot is a new build of the task (a resume keeps its
    snapshot and never comes here), so whatever an earlier build of the same
    task id pinned is removed first. Otherwise a project that has no
    `toolchain:` block now would be judged by an older build's pin.
    """
    try:
        stale = (toolchain_snapshot_paths(task_id, Path(worktree_path))["file"],)
        for path in stale:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "Could not remove an earlier build's pin %s for %s (%s); "
                    "it may be used again.",
                    path,
                    task_id,
                    exc,
                )
        committed, declaration = load_committed_toolchain_declaration(
            Path(worktree_path)
        )
        if not committed:
            declaration = load_toolchain_declaration(Path(repo_root))
        if declaration is None:
            # byte-equivalent no-op for every repo that has not opted in
            return None

        paths = toolchain_snapshot_paths(task_id, worktree_path)
        paths["dir"].mkdir(parents=True, exist_ok=True)
        paths["file"].write_text(
            json.dumps(declaration.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        logger.info(
            "TS-lane D.1b: pinned the toolchain declaration for %s pre-turn-1 "
            "(test=%r install=%r) at %s — the Player cannot change it for the "
            "rest of this build.",
            task_id,
            declaration.test,
            declaration.install,
            paths["file"],
        )
        return paths["file"]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "TS-lane D.1b: toolchain snapshot failed for %s (%s) — the "
            "declaration will be absent for this task, so the check will say "
            "that nothing is declared",
            task_id,
            exc,
        )
        return None


def load_toolchain_snapshot(
    task_id: str, worktree_path: Path
) -> Optional[ToolchainDeclaration]:
    """Load the pre-turn-1 declaration snapshot for a task.

    THE ONLY reader on the verdict path. Returns ``None`` when no snapshot was
    captured or it is unreadable — deliberately WITHOUT falling back to the
    live ``<worktree>/.guardkit/config.yaml``, because that file is inside the
    tree the Player edits (design §B.4 / §F.1). Never raises.
    """
    try:
        path = toolchain_snapshot_paths(task_id, worktree_path)["file"]
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return ToolchainDeclaration.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — an unreadable snapshot is absence
        logger.warning(
            "TS-lane D.1b: could not read the toolchain snapshot for %s (%s) — "
            "treating the declaration as absent",
            task_id,
            exc,
        )
        return None


@dataclass(frozen=True)
class DeclaredPart:
    """One part of the project whose tests run on their own.

    ``name`` is ``"root"`` for the root component, the component's name, or
    the folder (``apps/web``) for a part found through a ``parts:`` pattern.
    ``toolchain`` holds the part's commands with its ``cwd``; it is ``None``
    for the root component, whose commands are the declaration's top level.
    ``test`` is ``None`` when the part declares no test command.
    """

    name: str
    cwd: str
    test: Optional[str]
    toolchain: Optional[ComponentToolchain] = None


ROOT_PART = "root"


def _inside(path: str, folder: str) -> bool:
    return folder == "." or path == folder or path.startswith(folder + "/")


def _pattern_parts(
    declaration: ToolchainDeclaration, tree: Path
) -> List[DeclaredPart]:
    """The folders the ``parts:`` patterns match in ``tree`` now."""
    found: List[DeclaredPart] = []
    for entry in declaration.parts or ():
        base = Path(tree) / entry.under
        try:
            children = sorted(c for c in base.iterdir() if c.is_dir())
        except OSError:
            continue
        for child in children:
            if not (child / entry.marker).is_file():
                continue
            cwd = child.name if entry.under == "." else f"{entry.under}/{child.name}"
            commands = entry.model_dump(exclude={"under", "marker"})
            found.append(
                DeclaredPart(
                    name=cwd,
                    cwd=cwd,
                    test=entry.test,
                    toolchain=ComponentToolchain(cwd=cwd, **commands),
                )
            )
    return found


def _named_parts(declaration: ToolchainDeclaration) -> List[DeclaredPart]:
    return [
        DeclaredPart(name=name, cwd=comp.cwd, test=comp.test, toolchain=comp)
        for name, comp in sorted((declaration.components or {}).items())
    ]


def _declares_any_test(declaration: Optional[ToolchainDeclaration]) -> bool:
    if declaration is None:
        return False
    return bool(
        declaration.test
        or any(c.test for c in (declaration.components or {}).values())
        or any(p.test for p in declaration.parts or ())
    )


def parts_for_files(
    declaration: Optional[ToolchainDeclaration],
    tree: Path,
    files: Sequence[str],
) -> List[DeclaredPart]:
    """The parts the changed ``files`` belong to, each once, root first.

    A file belongs to the declared component or pattern part whose folder
    holds it, the deepest one winning, a named component before a pattern
    part at the same folder. A file in no such folder belongs to the root
    component when the top level declares ``test``. When the project
    declares no test command anywhere (or nothing at all), every file belongs
    to the root component (whatever changed, even nothing), which then has
    nothing declared, so the check reports that it could not run rather than
    guess a command. Files in no
    part (documentation in a project whose root declares no test, say) are
    left out: nothing runs for them before the merge's full check.

    The pattern parts are found in ``tree`` now, so a folder this task made
    counts. The commands come from ``declaration`` (the pinned copy).
    """
    if not _declares_any_test(declaration):
        return [DeclaredPart(name=ROOT_PART, cwd=".", test=None)]
    assert declaration is not None
    candidates = _named_parts(declaration)
    named_folders = {p.cwd for p in candidates}
    candidates += [
        p for p in _pattern_parts(declaration, tree) if p.cwd not in named_folders
    ]
    root = (
        DeclaredPart(name=ROOT_PART, cwd=".", test=declaration.test)
        if declaration.test
        else None
    )
    chosen: Dict[str, DeclaredPart] = {}
    for raw in files:
        path = str(raw).replace("\\", "/").lstrip("/")
        while path.startswith("./"):
            path = path[2:]
        matches = [p for p in candidates if _inside(path, p.cwd)]
        if matches:
            # Deepest folder wins; ``max`` keeps the first (a named component)
            # of equal depth.
            part = max(
                matches,
                key=lambda p: 0 if p.cwd == "." else len(p.cwd.split("/")),
            )
        elif root is not None:
            part = root
        else:
            continue
        chosen.setdefault(part.name, part)
    ordered = sorted(chosen.values(), key=lambda p: (p.name != ROOT_PART, p.name))
    return ordered


def full_check_parts(
    declaration: Optional[ToolchainDeclaration], tree: Path
) -> List[DeclaredPart]:
    """What the project's full check runs, each in its own folder.

    The root ``test`` when declared, then every named component, then every
    folder a ``parts:`` pattern matches in ``tree`` (one a component already
    names is not repeated). A component or pattern without ``test`` is
    included with nothing declared, so the check says it could not run.
    Empty when nothing is declared.

    ``feature_check`` is never a substitute for these (1 November 2026 fix
    pass): a project that declares one, such as a browser journey, still has
    its root and parts checked here. It is the build's whole-feature check.
    """
    if declaration is None:
        return []
    parts: List[DeclaredPart] = []
    if declaration.test:
        parts.append(DeclaredPart(name=ROOT_PART, cwd=".", test=declaration.test))
    named = _named_parts(declaration)
    folders = {p.cwd for p in named}
    parts += named
    parts += [p for p in _pattern_parts(declaration, tree) if p.cwd not in folders]
    return parts


def resolve_component_cwd(base: Path, cwd: str) -> Path:
    """Resolve a component's ``cwd`` under ``base``, refusing any escape.

    The schema already rejects ``..`` / absolute / ``~`` at declaration time;
    this is the belt-and-braces check at the point of use, because a SYMLINK
    inside the worktree can still point outside it and no schema can see that.

    Raises
    ------
    ValueError
        If the resolved directory is not contained by ``base``.
    """
    base_path = Path(base)
    candidate = base_path / cwd
    try:
        candidate.resolve().relative_to(base_path.resolve())
    except ValueError as exc:
        raise ValueError(
            f"component cwd {cwd!r} resolves outside the worktree "
            f"({candidate} is not under {base_path}) — refusing to run a "
            "declared command there."
        ) from exc
    return candidate


__all__ = [
    "CONFIG_RELATIVE_PATH",
    "TOOLCHAIN_KEY",
    "ComponentToolchain",
    "ToolchainDeclaration",
    "ToolchainDeclarationError",
    "ToolchainRuntime",
    "resolve_component_cwd",
    "parse_toolchain_block",
    "load_toolchain_declaration",
    "toolchain_snapshot_paths",
    "snapshot_task_toolchain",
    "load_toolchain_snapshot",
    "DeclaredPart",
    "ROOT_PART",
    "PartFolders",
    "parts_for_files",
    "full_check_parts",
]
