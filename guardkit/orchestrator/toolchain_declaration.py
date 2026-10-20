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
      environment_inventory: "npm ls --all" # evidence only (run_evidence)

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
import posixpath
import re
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
    — a silently-ignored declaration would fall through to the detection
    ladder and look like the tool ignoring the repo.
    """

    model_config = ConfigDict(extra="forbid")

    # ---- verdict-bearing ------------------------------------------------
    test: Optional[str] = Field(default=None, min_length=1)
    # B9 Lane C: the project's OWN coverage measurement. Exit 0 = the project's
    # coverage threshold is met; non-zero = not met. The Coach runs it itself,
    # after its own independent test run, and that exit decides coverage_met.
    # Optional: a project that declares nothing keeps today's behaviour, and
    # an unmeasured required coverage stays UNKNOWN rather than becoming a pass.
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
            "ran_marker_regex, requires_ran_marker, runtime, components, "
            "feature_check, feature_check_timeout, environment_inventory, "
            "environment_inventory_timeout. "
            "Unknown keys are rejected — check for typos.\n"
            "Inside `components: <name>:` the SAME keys are allowed plus a "
            "REQUIRED repo-relative `cwd:`."
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


def declared_coverage_command(
    toolchain: Optional[ToolchainDeclaration],
    component: Optional[str] = None,
) -> Optional[str]:
    """The coverage command declared for one task, or ``None``.

    The same rule as ``CoachValidator._declared_coverage_command``: a task
    that names a component gets that component's ``coverage:`` and never the
    root block's; a task that names none gets the root block's.
    """
    if component:
        resolved = toolchain.component(component) if toolchain is not None else None
        return (resolved.coverage or None) if resolved is not None else None
    if toolchain is None:
        return None
    return toolchain.coverage or None


# A coverage command added for a task whose canonical repository declared NO
# `toolchain:` block (20 October 2026, review round 1). It is kept in its own
# file beside the pin, never turned into a declaration: with no `toolchain:`
# block pinned, the test command and everything else keep their
# no-declaration behaviour, and only coverage is known.
_COVERAGE_ONLY_FILE = "coverage-only.json"


def _coverage_only_path(task_id: str, worktree_path: Path) -> Path:
    return toolchain_snapshot_paths(task_id, worktree_path)["dir"] / _COVERAGE_ONLY_FILE


def load_coverage_only_pin(
    task_id: str, worktree_path: Path
) -> Optional[Tuple[str, int]]:
    """The coverage command (and its timeout) pinned for a task whose
    canonical repository declared no ``toolchain:`` block, or ``None``.

    Read only when no declaration is pinned. Never raises.
    """
    try:
        path = _coverage_only_path(task_id, Path(worktree_path))
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        command = raw.get("coverage") if isinstance(raw, dict) else None
        timeout = raw.get("coverage_timeout") if isinstance(raw, dict) else None
        if not isinstance(command, str) or not command.strip():
            return None
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
            timeout = _DEFAULT_TIMEOUT
        return command, timeout
    except Exception as exc:  # noqa: BLE001 - unreadable is absent
        logger.warning(
            "Could not read the pinned coverage command for %s (%s); treating "
            "it as absent.",
            task_id,
            exc,
        )
        return None


def coverage_view_of_pin(
    task_id: str, worktree_path: Path
) -> Optional[ToolchainDeclaration]:
    """What a task's pin says about coverage, as a declaration, or ``None``.

    The pinned declaration when there is one. Otherwise, when only a coverage
    command was pinned (see :func:`load_coverage_only_pin`), a declaration
    holding that command alone. For coverage decisions ONLY (the task-start
    check and the after-turn check): it is never handed to the Coach as the
    project's declaration.
    """
    pinned = load_toolchain_snapshot(task_id, worktree_path)
    if pinned is not None:
        return pinned
    only = load_coverage_only_pin(task_id, worktree_path)
    if only is None:
        return None
    return ToolchainDeclaration(coverage=only[0], coverage_timeout=only[1])


def add_coverage_to_pin(
    task_id: str,
    worktree_path: Path,
    source: Optional[ToolchainDeclaration],
    component: Optional[str] = None,
) -> Optional[str]:
    """Add a coverage command to a task's pinned declaration, never replace one.

    20 October 2026. A project with no coverage command gets one only when a
    task writes it into ``.guardkit/config.yaml``. The pin is cut from the
    canonical repository before the task starts, so it could not see that:
    the task that wrote the command, and every task after it in the same
    build, were judged as if nothing had been declared.

    This copies ONLY the coverage command and its timeout from ``source``,
    and ONLY when the pin declares none for this task (the root block, or the
    task's component). A coverage command the pin already has is never
    changed, and no other command (``test``, ``install`` and the rest) is
    ever taken from ``source``: those still come from the canonical
    repository alone. Once added, the command is pinned like the rest, so a
    later turn cannot change it.

    When the canonical repository declared no ``toolchain:`` block at all,
    so nothing is pinned (review round 1), the command is kept in a file of
    its own beside the pin (:func:`load_coverage_only_pin`), for a task that
    names no component. It is never turned into a declaration, so the test
    command keeps its no-declaration behaviour and is never taken from
    ``source``. A coverage command already kept there is never replaced.

    Returns the command added, or ``None`` when nothing was added: the pin
    already declares coverage for this task, the task's component is not in
    the pin or not in ``source``, a component task has nothing pinned, or
    ``source`` declares no coverage for it. Never raises.
    """
    try:
        pinned = load_toolchain_snapshot(task_id, worktree_path)
        if pinned is None:
            if component or source is None:
                return None
            if load_coverage_only_pin(task_id, worktree_path) is not None:
                return None
            command = declared_coverage_command(source, None)
            if not command:
                return None
            path = _coverage_only_path(task_id, Path(worktree_path))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {"coverage": command, "coverage_timeout": source.coverage_timeout},
                    indent=2,
                ),
                encoding="utf-8",
            )
            return command
        if declared_coverage_command(pinned, component):
            return None
        command = declared_coverage_command(source, component)
        if not command or source is None:
            return None
        if component:
            from_source = source.component(component)
            target = pinned.component(component)
            if from_source is None or target is None:
                return None
            components = dict(pinned.components or {})
            components[component] = target.model_copy(
                update={
                    "coverage": command,
                    "coverage_timeout": from_source.coverage_timeout,
                }
            )
            updated = pinned.model_copy(update={"components": components})
        else:
            updated = pinned.model_copy(
                update={
                    "coverage": command,
                    "coverage_timeout": source.coverage_timeout,
                }
            )
        path = toolchain_snapshot_paths(task_id, worktree_path)["file"]
        path.write_text(
            json.dumps(updated.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return command
    except Exception as exc:  # noqa: BLE001 - never crash a build over this
        logger.warning(
            "Could not add a coverage command to the pinned declaration for "
            "%s (%s); the pin is left as it was.",
            task_id,
            exc,
        )
        return None


def declares_config_file(paths: Iterable[Any]) -> bool:
    """True when ``paths`` names the project's ``.guardkit/config.yaml``.

    ``paths`` is what a task says it will create or change: its task
    document's "Files to Create" / "Files to Modify" sections, or the
    ``files_to_create`` / ``files_to_modify`` lists. Written forms such as
    ``./.guardkit/config.yaml`` count; anything that is not a string is
    ignored.
    """
    wanted = CONFIG_RELATIVE_PATH.as_posix()
    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            continue
        text = raw.strip().strip("`").replace("\\", "/")
        if posixpath.normpath(text) == wanted:
            return True
    return False


def undeclared_coverage_refusal(
    *,
    task_type: Any,
    toolchain: Optional[ToolchainDeclaration],
    component: Optional[str] = None,
    implementation_mode: Any = None,
    after_turn: bool = False,
) -> Optional[str]:
    """Say why a task can never pass because no coverage command is declared.

    Since 19 September 2026 a task whose type requires coverage passes only
    on a MEASURED coverage, and the only thing that measures it is the
    project's own declared ``coverage`` command (the Coach runs it). So a task
    of such a type in a project that declares none cannot pass, however good
    the code is. This finds that out before any turn is spent and returns the
    plain reason; it returns ``None`` whenever the task can still pass.

    The rule itself is unchanged: which types require coverage comes from the
    task-type profiles, and nothing here counts an undeclared coverage as met.

    ``None`` is returned when:

    * the task's type does not require coverage;
    * the task's type is not a valid type (the Coach's own invalid-task-type
      stop reports that, with its own message);
    * the task is routed to the direct Player (``implementation_mode:
      direct``), the one named relaxation of the coverage gate;
    * a coverage command is declared for the task (root, or its component).

    ``after_turn`` (20 October 2026) words the same reason for a task that
    said it would change ``.guardkit/config.yaml``, was therefore given its
    turn, and still left no coverage command declared.
    """
    from guardkit.models.task_types import (
        DEFAULT_PROFILES,
        TASK_TYPE_ALIASES,
        TaskType,
    )

    # The Coach's resolution (CoachValidator._resolve_task_type): absent means
    # feature, then the enum, then the alias table; anything else is invalid.
    if task_type is None:
        resolved = TaskType.FEATURE
    elif not isinstance(task_type, str):
        return None
    else:
        try:
            resolved = TaskType(task_type)
        except ValueError:
            resolved = TASK_TYPE_ALIASES.get(task_type)
            if resolved is None:
                return None
    if not DEFAULT_PROFILES[resolved].coverage_required:
        return None
    # The router sends exactly "direct" to the direct Player
    # (AgentInvoker._get_implementation_mode), whose results the Coach reads
    # as the direct-mode relaxation.
    if implementation_mode == "direct":
        return None
    if declared_coverage_command(toolchain, component):
        return None

    needing = [t.value for t in TaskType if DEFAULT_PROFILES[t].coverage_required]
    needing_words = ", ".join(needing[:-1]) + " or " + needing[-1]
    if task_type is None:
        type_words = (
            f"{resolved.value} task (a task with no task_type is a feature task)"
        )
    elif task_type != resolved.value:
        type_words = f"{resolved.value} task (task_type: {task_type})"
    else:
        type_words = f"{resolved.value} task"
    if component:
        where = (
            f"for the task's component `{component}` "
            f"(`toolchain.components.{component}.coverage`)"
        )
        place = f"under `toolchain.components.{component}:`"
    else:
        where = "(`toolchain.coverage`)"
        place = "under `toolchain:`"
    if after_turn:
        stopped = (
            "this task said it would change .guardkit/config.yaml, so it was "
            "given a turn to declare one, but after that turn the file still "
            "declares none, and it was stopped there."
        )
    else:
        stopped = "it was stopped before any work was done."
    return (
        f"This project declares no coverage command {where} in "
        f".guardkit/config.yaml, and a {type_words} needs measured coverage "
        f"to pass. Nothing else measures coverage, so this task cannot pass "
        f"however good the code is; {stopped} "
        f"To fix it, add "
        f'`coverage: "<command that exits 0 when the coverage threshold is '
        f'met>"` {place} in .guardkit/config.yaml, then run the task again. '
        f"Only {needing_words} tasks need this; other task types are "
        f"unaffected."
    )


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
    "declared_coverage_command",
    "undeclared_coverage_refusal",
    "add_coverage_to_pin",
    "declares_config_file",
    "load_coverage_only_pin",
    "coverage_view_of_pin",
]
