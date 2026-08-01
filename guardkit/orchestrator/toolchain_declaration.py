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
(``STACK_TEST_PROFILES`` matches repo marker globs; ``_scan_directory`` reads
repo manifests; the deleted pytest default was a repo-level assumption wearing
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
      absent_substrings: ["missing script"] # optional stack-row overlay
      ran_marker_regex:  null
      requires_ran_marker: true
      runtime: {node: "v24.15.0"}

Only ``test`` is verdict-bearing by default. ``typecheck`` / ``lint`` /
``build`` are *available* — a plan that wants one enforced writes it as a
``conformance: assert_command`` rule, which is already a shipped, wired,
verdict-bearing path. We do not invent a second enforcement mechanism.

Two laws (design §B.4)
----------------------
**LAW — exit code is the verdict.** A declared command passes iff
``returncode == 0``. Parsing a command's stdout is advisory only; it may
enrich a checkpoint or a summary, it may never decide green. The one
permitted exception is not parsing-for-verdict but a false-green guard
(``success_requires_ran_marker``), which may turn a 0 into "absent", never an
absence into a pass.

**LAW — the declaration is snapshotted before the model's first turn.** This
file lives INSIDE the target repo, which means it lives inside the worktree
the builder is editing. Without a snapshot, a Player turn could rewrite
``toolchain.test`` to ``true`` and green itself. :func:`snapshot_task_toolchain`
is pinned at the same pre-turn-1 call site as ``snapshot_task_conformance``,
reads from the canonical ``repo_root`` tree, and writes OUTSIDE the shared
worktree. The pinned copy is what executes for the whole build —
:func:`load_toolchain_snapshot` is the ONLY reader the verdict path uses. It
never falls back to the live file: no snapshot means no declaration, and the
pre-declaration ladder runs unchanged.

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
* Selection is EXPLICIT and per task (``component: app`` in the task's
  frontmatter). **No path inference** — a mixed-touch task must be split, not
  silently assigned to one component (design §B.2).
* ``extra="forbid"`` holds at BOTH levels, so a typo'd component field is as
  loud as a typo'd root field.

**The snapshot law is unchanged, and that is why this shape was chosen.** The
pin is one whole-model ``model_dump`` read back by one ``model_validate``, so a
nested field round-trips byte-for-byte with ZERO snapshot changes. The Player
still cannot edit a component's test command mid-build.

**Scoped OUT of this lane, loudly:** a component's ``install:`` is accepted by
the schema but is NOT consumed. The declared install stays ROOT-ONLY
(``environment_bootstrap._scan_directory``) so depth-1 subpackage inference in
every other monorepo in the estate is preserved by construction (design §G);
:func:`load_toolchain_declaration` logs a WARNING naming any component install
that will not be run.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

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
    — a silently-ignored declaration would fall through to the detection
    ladder and look like the tool ignoring the repo.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- verdict-bearing ------------------------------------------------
    test: Optional[str] = Field(default=None, min_length=1)

    # ---- environment ----------------------------------------------------
    install: Optional[str] = Field(default=None, min_length=1)

    # ---- non-verdict legs (available to plans as assert_command rules) ---
    typecheck: Optional[str] = Field(default=None, min_length=1)
    lint: Optional[str] = Field(default=None, min_length=1)
    build: Optional[str] = Field(default=None, min_length=1)

    # ---- bounded timeouts -----------------------------------------------
    # Both default to TODAY's hardcoded 300s, deliberately: a repo that
    # declares only ``test:`` must not silently acquire a different timeout
    # than it had before the declaration existed. A repo that needs longer
    # (``npm ci`` on a real app) declares the number it needs.
    test_timeout: int = Field(default=_DEFAULT_TIMEOUT, ge=1, le=_MAX_TIMEOUT)
    install_timeout: int = Field(default=_DEFAULT_TIMEOUT, ge=1, le=_MAX_TIMEOUT)

    # ---- optional overlay of the stack row's absence classifier ----------
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
                self.install,
                self.typecheck,
                self.lint,
                self.build,
                self.has_classifier_overlay,
                self.runtime,
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
        raw = value.strip()
        if not raw:
            raise ValueError("cwd must not be blank")
        if raw.startswith("~"):
            raise ValueError(
                f"cwd must be repo-relative, not a home-relative path: {value!r}"
            )
        candidate = PurePosixPath(raw.replace("\\", "/"))
        if candidate.is_absolute() or raw.startswith("/"):
            raise ValueError(
                f"cwd must be repo-relative, not absolute: {value!r}"
            )
        if any(part == ".." for part in candidate.parts):
            raise ValueError(
                f"cwd must not escape the worktree (no `..` segments): {value!r}"
            )
        # Normalise "./app/" -> "app" so the receipt and the snapshot agree.
        parts = [p for p in candidate.parts if p not in (".", "")]
        return "/".join(parts) if parts else "."


class ToolchainDeclaration(_ToolchainCommands):
    """The repo's declared toolchain: THE ROOT COMPONENT, plus its components.

    The top-level command fields are the root component's — byte-for-byte the
    meaning they had before ``components:`` existed. ``components`` is
    ``Optional`` and defaults to ``None``, so every repo with a flat
    declaration is unchanged (design §G).
    """

    # ---- per-path sections (the monorepo seam, design §B.2(iii)) ---------
    components: Optional[Dict[str, ComponentToolchain]] = None

    @field_validator("components")
    @classmethod
    def _component_names_must_be_usable(
        cls, value: Optional[Dict[str, "ComponentToolchain"]]
    ) -> Optional[Dict[str, "ComponentToolchain"]]:
        """A component name is written in a task file by hand — a blank or
        whitespace-bearing key is a typo that would never be selectable."""
        if value is None:
            return value
        for name in value:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("component names must be non-empty strings")
            if name != name.strip() or any(c.isspace() for c in name):
                raise ValueError(
                    f"component name {name!r} must not contain whitespace — it "
                    "is written verbatim as a task's `component:` selector"
                )
        return value

    @property
    def is_empty(self) -> bool:
        """True for a ``toolchain: {}`` block that declares nothing at all.

        A block that declares ONLY ``components:`` is NOT empty — dropping it
        would silently un-declare every component task in the repo.
        """
        return super().is_empty and not self.components

    @property
    def component_names(self) -> List[str]:
        """Declared component names, sorted — for loud error messages."""
        return sorted(self.components) if self.components else []

    def component(self, name: str) -> Optional[ComponentToolchain]:
        """Return the named component's declaration, or ``None`` if undeclared.

        Callers MUST treat ``None`` for a task that named a component as an
        error, never as "fall back to the root block" — falling back is the
        silent-wrong-verdict this whole seam exists to remove.
        """
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
            "ran_marker_regex, requires_ran_marker, runtime, components. "
            "Unknown keys are rejected — check for typos.\n"
            "Inside `components: <name>:` the SAME keys are allowed plus a "
            "REQUIRED repo-relative `cwd:`."
        ) from exc


def load_toolchain_declaration(repo_root: Path) -> Optional[ToolchainDeclaration]:
    """Read the ``toolchain:`` block from ``<repo_root>/.guardkit/config.yaml``.

    Never raises. Returns ``None`` when the file is absent, unreadable, not a
    mapping, or carries no ``toolchain`` key — i.e. every repo that has not
    opted in behaves exactly as it did before this module existed.

    A MALFORMED block is logged at ERROR (the loud-degrade lesson: a typo must
    never be mistaken for "the tool ignored me") and degrades to ``None``, so
    a schema mistake in an opt-in feature cannot crash an existing build. The
    schema itself still raises for direct callers of
    :func:`parse_toolchain_block`.
    """
    config_path = Path(repo_root) / CONFIG_RELATIVE_PATH
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
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
        logger.error(
            "MALFORMED `toolchain:` block in %s — the declaration will NOT be "
            "used for this repo until it is fixed, and command detection falls "
            "back to the marker ladder. %s",
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
    _warn_about_unconsumed_component_installs(declaration, config_path)
    return declaration


def _warn_about_unconsumed_component_installs(
    declaration: ToolchainDeclaration, config_path: Path
) -> None:
    """SCOPED OUT, LOUDLY: a component's ``install:`` is NOT run.

    The declared install is resolved by ``ProjectEnvironmentDetector``, which
    is repo-keyed and per-task-blind (it never sees which component a task
    selected), and it is deliberately ROOT-ONLY so depth-1 subpackage
    inference in every other monorepo in the estate stays untouched (design
    §G, ``environment_bootstrap.py`` ``_scan_directory``). Threading a
    per-task component through the bootstrap chain is a different change; the
    verdict-bearing half — command RESOLUTION and its ``cwd`` — is what this
    seam delivers. A repo that declares a component install must not be left
    guessing why nothing installed, so say it out loud, once, at load.
    """
    if not declaration.components:
        return
    named = sorted(
        name for name, comp in declaration.components.items() if comp.install
    )
    if not named:
        return
    logger.warning(
        "`toolchain.components.%s.install` in %s is DECLARED BUT NOT RUN — "
        "per-component install is scoped OUT of the per-component toolchain "
        "seam. The declared install stays ROOT-ONLY (`toolchain.install`); a "
        "component's dependencies are installed by depth-1 manifest inference "
        "or not at all. The component's `test:` and `cwd:` ARE honoured.",
        ", ".join(named),
        config_path,
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


def snapshot_task_toolchain(
    task_id: str,
    worktree_path: Path,
    repo_root: Path,
) -> Optional[Path]:
    """Snapshot the repo's toolchain declaration pre-turn-1.

    Returns the snapshot file path when a declaration was captured, else
    ``None`` (no declaration, or an error — both mean the build behaves
    exactly as it did before the declaration existed). Never raises.
    """
    try:
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
            "declaration will be absent for this task and detection falls back "
            "to the marker ladder",
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
    "ToolchainRuntime",
    "resolve_component_cwd",
    "parse_toolchain_block",
    "load_toolchain_declaration",
    "toolchain_snapshot_paths",
    "snapshot_task_toolchain",
    "load_toolchain_snapshot",
]
