"""
Feature YAML loading and validation for AutoBuild feature mode.

This module provides the FeatureLoader class for loading and validating feature
YAML files from .guardkit/features/, as well as data models representing the
feature structure.

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.feature_loader import FeatureLoader
    >>>
    >>> feature = FeatureLoader.load_feature("FEAT-A1B2", repo_root=Path.cwd())
    >>> print(feature.name)
    "User Authentication"
    >>> print(len(feature.tasks))
    4
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, ValidationError
import yaml

from guardkit.models.task_types import TaskType, TASK_TYPE_ALIASES
from guardkit.orchestrator.stamp_normalizer import StampNormalizerError
from guardkit.orchestrator.verifier_stamp import ScenarioStamp

logger = logging.getLogger(__name__)


# ============================================================================
# Schema Documentation (for error messages)
# ============================================================================

TASK_SCHEMA = """
Task Schema:
  id: str (required)        # e.g., "TASK-XXX-YYYY"
  file_path: str            # Path to task markdown file
  name: str                 # Human-readable name (defaults to id)
  complexity: int           # 1-10 (default: 5)
  dependencies: list        # Task IDs this depends on
  status: str               # pending/in_progress/completed/failed/skipped
  implementation_mode: str  # task-work/direct/manual
  estimated_minutes: int    # Default: 30
  requires_infrastructure: list  # e.g., ["postgresql", "redis"]
"""

FEATURE_SCHEMA = """
Feature Schema:
  id: str (required)        # e.g., "FEAT-A1B2"
  name: str                 # Human-readable name (defaults to id)
  description: str          # Feature description
  tasks: list               # List of task objects
  orchestration: dict       # Parallel execution configuration
"""

ORCHESTRATION_SCHEMA = """
Orchestration Schema:
  parallel_groups: list     # Lists of task IDs per wave
  estimated_duration_minutes: int
  recommended_parallel: int # Bound (may only lower, never raise) on the
                            # auto-detected max parallel tasks when neither
                            # the GUARDKIT_MAX_PARALLEL_TASKS env var nor
                            # --max-parallel is set (TASK-AB-WAVECTL01)
"""


# ============================================================================
# Error Message Helpers
# ============================================================================


def _truncate_data(data: Any, max_length: int = 200) -> str:
    """
    Truncate data representation for error messages.

    Parameters
    ----------
    data : Any
        Data to truncate
    max_length : int
        Maximum length of output string

    Returns
    -------
    str
        Truncated string representation
    """
    data_str = str(data)
    if len(data_str) > max_length:
        return data_str[:max_length] + "..."
    return data_str


def _build_schema_error_message(
    missing_field: str,
    context: str,
    data: Dict[str, Any],
    schema: str,
) -> str:
    """
    Build a user-friendly error message with schema hints.

    Parameters
    ----------
    missing_field : str
        The name of the missing required field
    context : str
        Context description (e.g., "task 'TASK-001'", "feature")
    data : Dict[str, Any]
        The actual data that caused the error
    schema : str
        The expected schema documentation

    Returns
    -------
    str
        Formatted error message with hints
    """
    present_fields = list(data.keys()) if data else []

    return f"""Missing required field '{missing_field}' in {context}

{schema.strip()}

Actual data received:
  Present fields: {present_fields}
  Data preview: {_truncate_data(data)}

Fix: Ensure the YAML contains the '{missing_field}' field.
     Re-run /feature-plan to regenerate with correct schema."""


# ============================================================================
# Data Models
# ============================================================================


class FeatureTask(BaseModel):
    """
    Represents a task within a feature.

    Attributes
    ----------
    id : str
        Task identifier (e.g., "TASK-XXX-YYYY")
    name : str
        Human-readable task name
    file_path : Path
        Path to task markdown file
    complexity : int
        Task complexity (1-10)
    dependencies : List[str]
        List of task IDs this task depends on
    status : str
        Current task status
    implementation_mode : str
        How the task should be implemented
    estimated_minutes : int
        Estimated implementation time
    result : Optional[Dict[str, Any]]
        Execution result (populated after completion)
    turns_completed : int
        Number of turns completed (for resume support)
    current_turn : int
        Current turn being executed (for resume support)
    started_at : Optional[str]
        ISO timestamp when task started
    completed_at : Optional[str]
        ISO timestamp when task completed
    requires_infrastructure : List[str]
        Infrastructure services required (e.g., ["postgresql", "redis"])
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    file_path: Path = Path("")
    # The cull (27 October 2026, GKT-033): no allowed-value lists or ranges.
    # A value the planner wrote is kept as it is; code that compares it
    # simply finds no match.
    complexity: int = 5
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"
    implementation_mode: str = "task-work"
    estimated_minutes: int = 30
    requires_infrastructure: List[str] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    turns_completed: int = 0
    current_turn: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def set_name_default(cls, data):
        """Set name to id if not provided."""
        if isinstance(data, dict):
            if not data.get("name") and data.get("id"):
                data["name"] = data["id"]
        return data


class FeatureOrchestration(BaseModel):
    """
    Orchestration configuration for feature execution.

    Attributes
    ----------
    parallel_groups : List[List[str]]
        Wave execution order (tasks in same list can run in parallel)
    estimated_duration_minutes : int
        Total estimated duration
    recommended_parallel : Optional[int]
        Recommended max parallel tasks. Consumed by the orchestrator's
        concurrency resolution with precedence env > CLI flag > this value
        > auto-detect (TASK-AB-WAVECTL01), and it may only LOWER the
        auto-detect result, never raise it (generate_feature_yaml emits it
        as a machine default, so it must not lift the TASK-VPT-001 local
        cap of 1). ``None`` means "not set" — the default must stay
        ``None`` (not a coerced int) so an absent YAML tier survives
        save/load round-trips and never silently caps a run
        (see .claude/rules/absence-must-survive-every-reconciliation-layer.md).
    """

    model_config = ConfigDict(extra="ignore")

    parallel_groups: List[List[str]] = Field(default_factory=list)
    estimated_duration_minutes: int = 0
    recommended_parallel: Optional[int] = None


@dataclass
class FeatureExecution:
    """
    Feature execution state.

    Attributes
    ----------
    started_at : Optional[str]
        ISO timestamp when execution started
    completed_at : Optional[str]
        ISO timestamp when execution completed
    worktree_path : Optional[str]
        Path to shared worktree
    total_turns : int
        Total turns across all tasks
    tasks_completed : int
        Number of completed tasks
    tasks_failed : int
        Number of failed tasks
    current_wave : int
        Current wave being executed (1-indexed, for resume support)
    completed_waves : List[int]
        List of completed wave numbers (for resume support)
    last_updated : Optional[str]
        ISO timestamp of last state update
    archived_at : Optional[str]
        ISO timestamp when feature was archived
    archived_to : Optional[str]
        Path where feature folder was archived (relative to repo root)
    """

    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    worktree_path: Optional[str] = None
    total_turns: int = 0
    tasks_completed: int = 0
    tasks_deferred: int = 0
    tasks_failed: int = 0
    current_wave: int = 0
    completed_waves: List[int] = field(default_factory=list)
    last_updated: Optional[str] = None
    archived_at: Optional[str] = None
    archived_to: Optional[str] = None


class SmokeGates(BaseModel):
    """Optional feature-level smoke gate configuration (TASK-SMK-F703A).

    Implements R3 from TASK-REV-4D012: a single subprocess invocation run
    inside the shared worktree after a specified wave completes, catching
    composition failures that the per-task Player-Coach loop cannot see.

    The gate runs BETWEEN WAVES, not between tasks — per-task smoke is the
    per-task Coach with extra steps.

    Attributes
    ----------
    after_wave : Union[int, List[int], Literal["all"]]
        Which wave(s) to fire after. ``1`` = after topological level 1
        completes. ``[1, 3]`` = after waves 1 and 3. ``"all"`` = after
        every wave. Wave numbers are 1-indexed and come from
        ``orchestration.parallel_groups`` — this field never computes
        waves itself.
    command : str
        Shell command to execute in the shared worktree (e.g.
        ``"pytest features/FEAT-X.feature"`` or a custom smoke script).
    expected_exit : int
        Exit code that signals success. Default: 0.
    timeout : int
        Seconds before the subprocess is killed. Default: 120.

    Only ``expected_exit`` passes; no other exit code means anything special
    (31 October 2026: ``exit5_is_hard_fail`` and the exit-5 "gate not wired"
    pass went; an old feature file that still sets it is read as before,
    since unknown keys are ignored).
    """

    # The cull (27 October 2026, GKT-034): unknown keys are ignored and the
    # values are not range-checked. A block with no command, or one that
    # cannot be read at all, is skipped at load (``_parse_feature``).
    model_config = ConfigDict(extra="ignore")

    after_wave: Union[int, List[int], Literal["all"]]
    command: str = Field(min_length=1)
    expected_exit: int = 0
    timeout: int = 120


class BehaviouralOracle(BaseModel):
    """Declared behavioural-oracle command (TS-lane D.1a).

    The schema home for the ``behavioural_oracle`` declaration. Until this
    model existed the declaration had no schema of any kind — no Pydantic
    model, no frontmatter validator, no ``Feature`` field — and the only
    thing that ever read it was ``CoachValidator._extract_command``, from a
    task dict no production caller ever populated.

    Modelled on :class:`SmokeGates`: a declared shell command and its
    expected exit code.

    Unlike ``SmokeGates`` this is NOT a between-waves gate. It is the
    per-task independent-evidence leg: ``CoachValidator`` runs it during
    ``gather_evidence`` and a ran-and-failed result overrides an approve to
    feedback (``AgentInvoker._apply_behavioural_oracle_guard``).

    Attributes
    ----------
    command : str
        Shell command executed in the worktree root (e.g. ``"npm test"``).
    expected_exit : int
        Exit code that signals success. Default ``0`` — LAW (design §B.4):
        the exit code is the verdict; parsing stdout is advisory only.
    timeout : int
        Seconds before the subprocess is killed. When unset the executor
        reads ``GUARDKIT_ORACLE_TIMEOUT`` (default 300s).
    """

    # The cull (27 October 2026, GKT-035): unknown keys are ignored and the
    # values are not checked; a required declaration need not name its
    # checker. The extra fields are accepted and kept as written.
    model_config = ConfigDict(extra="ignore")

    command: str = Field(min_length=1)
    expected_exit: int = 0
    timeout: Optional[int] = None
    required: bool = False
    expected_checks: Optional[int] = None
    checker_path: Optional[str] = None
    checker_sha256: Optional[str] = None
    source_paths: Optional[List[str]] = None


class Feature(BaseModel):
    """
    Represents a complete feature definition from YAML.

    Attributes
    ----------
    id : str
        Feature identifier (e.g., "FEAT-A1B2")
    name : str
        Feature name
    description : str
        Feature description
    created : str
        ISO timestamp of creation
    status : str
        Current feature status. ``awaiting_merge`` is the merge-ready
        checkpoint written by ``FeatureOrchestrator._archive_phase`` — the
        feature is built and archived, and waits on a human's merge word.
    complexity : int
        Aggregate complexity (1-10)
    estimated_tasks : int
        Number of tasks
    tasks : List[FeatureTask]
        List of tasks in the feature
    orchestration : FeatureOrchestration
        Execution configuration
    execution : FeatureExecution
        Execution state
    file_path : Optional[Path]
        Path to feature YAML file
    """

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: str
    name: str = ""
    description: str = ""
    created: str = ""
    # Known values: planned, in_progress, completed, failed, paused and
    # awaiting_merge (the merge-ready checkpoint written by
    # FeatureOrchestrator._archive_phase). ``guardkit feature audit --fix``
    # cannot infer awaiting_merge and would rewrite it to completed.
    # The cull (27 October 2026): no allowed-value list; the status is kept
    # as written.
    status: str = "planned"
    complexity: int = 5
    estimated_tasks: int = 0
    tasks: List[FeatureTask] = Field(default_factory=list)
    orchestration: FeatureOrchestration = Field(default_factory=FeatureOrchestration)
    execution: FeatureExecution = Field(default_factory=FeatureExecution)
    smoke_gates: Optional[SmokeGates] = None
    # TS-lane D.1a: feature-level declared behavioural oracle. Threaded to
    # every task in the feature via AutoBuildOrchestrator.orchestrate(
    # behavioural_oracle=...); a task's own frontmatter declaration WINS over
    # it (design §B.1 precedence: task frontmatter is the escape hatch that
    # sits above every repo/feature-level declaration). None -> the leg stays
    # absent exactly as before this field existed.
    behavioural_oracle: Optional[BehaviouralOracle] = None
    bootstrap_extras: List[str] = Field(default_factory=list)
    preflight_strict: bool = False
    # TASK-AB-XREPOEV01: declared sibling repositories whose writes count as
    # task evidence. Each entry is either a bare path string
    # (``"../guardkitfactory"``) or a mapping
    # ``{"path": "../guardkitfactory", "test_command": "pytest -q tests/"}``.
    # Empty by default -> the evidence boundary stays scoped to the worktree
    # and undeclared sibling-repo writes remain invisible (AC-003). Resolution
    # and per-repo git/test plumbing live in
    # ``guardkit.orchestrator.evidence_repos``.
    evidence_repos: List[Any] = Field(default_factory=list)
    # Scenario stamps (card Q8/A.2). ``routing_law`` is accepted and kept as
    # written; nothing in GuardKit reads it since the cull (27 October 2026,
    # GKT-041). ``feature_files`` names the feature's Gherkin files (the stamp
    # normaliser reads them); ``scenarios`` maps a scenario title to its
    # verifier stamp. A stamp that cannot be read is skipped (GKT-036).
    routing_law: Any = None
    feature_files: List[str] = Field(default_factory=list)
    scenarios: Dict[str, ScenarioStamp] = Field(default_factory=dict)
    # DELIVERY OWNERSHIP (B9 corrections, 19 September 2026). Approved scenario
    # title -> the id of the task whose acceptance criteria state that
    # scenario's observable behaviour. Accepted and kept as written; the
    # names are not checked against the feature's tasks (GKT-036).
    scenario_owners: Dict[str, Any] = Field(default_factory=dict)
    file_path: Optional[Path] = None

    @field_validator("scenarios", mode="before")
    @classmethod
    def _coerce_scenario_stamps(cls, v: Any) -> Any:
        """Read the per-scenario map; the bare-string shorthand
        (``"toolchain"``) means ``{verifier: toolchain}``. An entry that
        cannot be read is skipped."""
        if not isinstance(v, dict):
            return {}
        coerced: Dict[str, Any] = {}
        for title, stamp in v.items():
            if isinstance(stamp, str):
                stamp = {"verifier": stamp}
            if isinstance(stamp, ScenarioStamp):
                coerced[str(title)] = stamp
                continue
            try:
                coerced[str(title)] = ScenarioStamp.model_validate(stamp)
            except ValidationError:
                continue
        return coerced

    @field_validator("scenario_owners", mode="before")
    @classmethod
    def _owners_mapping(cls, v: Any) -> Any:
        """``None`` or anything that is not a mapping reads as no owners."""
        return v if isinstance(v, dict) else {}


# ============================================================================
# Exceptions
# ============================================================================


class FeatureNotFoundError(FileNotFoundError):
    """Raised when feature file cannot be found."""

    pass


class FeatureParseError(ValueError):
    """Raised when feature YAML cannot be parsed."""

    pass


class FeatureValidationError(ValueError):
    """Raised when feature fails validation."""

    pass


# ============================================================================
# FeatureLoader
# ============================================================================


class FeatureLoader:
    """
    Loads and validates feature YAML files.

    This class provides static methods for loading, validating, and saving
    feature YAML files from the .guardkit/features/ directory.

    Example
    -------
    >>> feature = FeatureLoader.load_feature("FEAT-A1B2")
    >>> errors = FeatureLoader.validate_feature(feature, Path.cwd())
    >>> if not errors:
    ...     print("Feature is valid!")
    """

    FEATURES_DIR = ".guardkit/features"

    # THE STAMP NORMALIZER's post-load hook flag (Rich's ruling 08-16; rules
    # doc ai-transition/docs/routing-law-stamp-normalizer-rules-2026-08-15.md).
    # OFF by default: v1's invoker is forge's plan-commit hook shelling
    # `guardkit qa normalize-stamps`, NOT every load. Flip this class attribute
    # (or pass `normalize_stamps=True`) to run the SAME function inline,
    # after parse.
    normalize_stamps_on_load: bool = False

    @staticmethod
    def load_feature(
        feature_id: str,
        repo_root: Optional[Path] = None,
        features_dir: Optional[Path] = None,
        validate_paths: bool = True,
        normalize_stamps: Optional[bool] = None,
    ) -> Feature:
        """
        Load feature file from .guardkit/features/.

        Parameters
        ----------
        feature_id : str
            Feature identifier (e.g., "FEAT-A1B2")
        repo_root : Optional[Path]
            Repository root directory (default: current directory)
        features_dir : Optional[Path]
            Override features directory (for testing)
        validate_paths : bool
            Kept for callers; no effect since step 2 (26 October 2026),
            when the load-time smoke-path check was deleted (GKT-040).
        normalize_stamps : Optional[bool]
            THE STAMP NORMALIZER hook. ``None`` (default) defers to the
            class flag ``FeatureLoader.normalize_stamps_on_load`` (OFF).
            When on, ``stamp_normalizer.normalize_feature`` runs after
            parse, WRITING rule-minted stamps for unstamped scenarios into
            the feature YAML (never overwriting an existing stamp) and
            re-parsing. Titles no rule decides are left unstamped. Only
            meaningful when the feature declares ``feature_files:``.

        Returns
        -------
        Feature
            Loaded and parsed feature

        Raises
        ------
        FeatureNotFoundError
            If feature file doesn't exist
        FeatureParseError
            If YAML cannot be parsed
        """
        repo_root = repo_root or Path.cwd()
        features_dir = features_dir or repo_root / FeatureLoader.FEATURES_DIR

        # Try both filename patterns
        feature_file = features_dir / f"{feature_id}.yaml"
        if not feature_file.exists():
            feature_file = features_dir / f"{feature_id}.yml"

        if not feature_file.exists():
            raise FeatureNotFoundError(
                f"Feature file not found: {feature_id}\n"
                f"Searched in: {features_dir}\n"
                f"Create feature with: /feature-plan \"your feature description\""
            )

        logger.info(f"Loading feature from {feature_file}")

        try:
            with open(feature_file, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise FeatureParseError(
                f"Failed to parse feature YAML: {feature_id}\n"
                f"File: {feature_file}\n"
                f"Error: {e}"
            )

        # Parse into Feature dataclass
        try:
            feature = FeatureLoader._parse_feature(
                data,
                repo_root=repo_root,
                validate_paths=validate_paths,
            )
            feature.file_path = feature_file
            # THE STAMP NORMALIZER hook (OFF unless asked): mint stamps by
            # rule for unstamped scenarios and WRITE them, then re-parse so
            # the returned feature carries what was written.
            run_normalizer = (
                FeatureLoader.normalize_stamps_on_load
                if normalize_stamps is None
                else normalize_stamps
            )
            if run_normalizer and feature.feature_files:
                from guardkit.orchestrator.stamp_normalizer import normalize_feature

                outcome = normalize_feature(
                    feature_file, feature.feature_files, repo_root
                )
                if outcome.model_stamped:
                    # Parity with the CLI echo: a stamp the MODEL decided
                    # (because no rule could) is never silent at load time
                    # either.
                    logger.warning(
                        "STAMP NORMALIZER (load-time hook): feature %s — the "
                        "model decided %d scenario(s) no rule could decide: %s",
                        feature_id,
                        len(outcome.model_stamped),
                        "; ".join(
                            f"{title!r} -> {outcome.stamped.get(title, '?')}"
                            for title in outcome.model_stamped
                        ),
                    )
                if outcome.written:
                    with open(feature_file, "r") as f:
                        data = yaml.safe_load(f)
                    feature = FeatureLoader._parse_feature(
                        data,
                        repo_root=repo_root,
                        validate_paths=validate_paths,
                    )
                    feature.file_path = feature_file
            return feature
        except FeatureParseError:
            # Re-raise with schema hints intact
            raise
        except StampNormalizerError:
            # The stamp normaliser could not read the feature file; surfaces
            # as itself, never re-wrapped.
            raise
        except KeyError as e:
            # Wrap KeyError with schema context
            raise FeatureParseError(
                _build_schema_error_message(
                    missing_field=str(e).strip("'\""),
                    context=f"feature '{feature_id}'",
                    data=data if isinstance(data, dict) else {},
                    schema=FEATURE_SCHEMA,
                )
            ) from e
        except (TypeError, ValueError) as e:
            # For type/value errors, show generic error with schema reference
            raise FeatureParseError(
                f"Invalid feature structure: {feature_id}\n"
                f"Error: {e}\n\n"
                f"Expected schema:\n{FEATURE_SCHEMA}"
            ) from e

    @staticmethod
    def _parse_feature(
        data: Dict[str, Any],
        repo_root: Optional[Path] = None,
        validate_paths: bool = True,
    ) -> Feature:
        """
        Parse feature dictionary into Feature dataclass.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw YAML data
        repo_root : Optional[Path]
            Kept for callers; not read.
        validate_paths : bool
            Kept for callers; no effect since step 2 (26 October 2026).

        Returns
        -------
        Feature
            Parsed Feature instance

        Raises
        ------
        FeatureParseError
            If required fields are missing, with schema hints
        """
        # The one required field (item 7 of the cull, 27 October 2026): a
        # feature with no id names nothing to build. A missing name defaults
        # to the id, the rule FeatureTask already uses.
        required_fields = ["id"]

        for field in required_fields:
            if field not in data:
                raise FeatureParseError(
                    _build_schema_error_message(
                        missing_field=field,
                        context="feature definition",
                        data=data,
                        schema=FEATURE_SCHEMA,
                    )
                )

        # Parse tasks with per-task error handling
        tasks = []
        for i, task_data in enumerate(data.get("tasks", [])):
            try:
                task = FeatureLoader._parse_task(task_data)
                tasks.append(task)
            except FeatureParseError:
                # Re-raise with original schema hints
                raise
            except (KeyError, TypeError, ValueError) as e:
                # Wrap unexpected errors with schema context
                task_id = task_data.get("id", f"at index {i}") if isinstance(task_data, dict) else f"at index {i}"
                raise FeatureParseError(
                    _build_schema_error_message(
                        missing_field=str(e).strip("'\""),
                        context=f"task '{task_id}'",
                        data=task_data if isinstance(task_data, dict) else {"raw_value": task_data},
                        schema=TASK_SCHEMA,
                    )
                ) from e

        # Parse orchestration using Pydantic
        orch_data = data.get("orchestration", {})
        try:
            orchestration = FeatureOrchestration.model_validate(orch_data)
        except ValidationError as e:
            raise FeatureParseError(
                f"Invalid orchestration data:\n{e}"
            ) from e

        # Parse optional smoke_gates (TASK-SMK-F703A). Key absent -> None.
        # The cull (27 October 2026, GKT-034): a block that cannot be read
        # (no command, or a shape that does not parse) is skipped, and the
        # feature loads without a smoke gate.
        smoke_gates_data = data.get("smoke_gates")
        smoke_gates: Optional[SmokeGates] = None
        if smoke_gates_data is not None:
            try:
                smoke_gates = SmokeGates.model_validate(smoke_gates_data)
            except ValidationError as e:
                logger.warning(
                    "Feature %s: smoke_gates block could not be read and is "
                    "skipped: %s", data.get("id"), e,
                )

        # Parse optional behavioural_oracle (TS-lane D.1a). Same as
        # smoke_gates above: key absent -> None; a block that cannot be read
        # is skipped (the cull, GKT-035).
        oracle_data = data.get("behavioural_oracle")
        behavioural_oracle: Optional[BehaviouralOracle] = None
        if oracle_data is not None:
            # String shortcut parity with CoachValidator._extract_command:
            # ``behavioural_oracle: "npm test"`` is the same declaration as
            # ``behavioural_oracle: {command: "npm test"}``.
            if isinstance(oracle_data, str):
                oracle_data = {"command": oracle_data}
            try:
                behavioural_oracle = BehaviouralOracle.model_validate(oracle_data)
            except ValidationError as e:
                logger.warning(
                    "Feature %s: behavioural_oracle block could not be read "
                    "and is skipped: %s", data.get("id"), e,
                )

        # Parse execution (may not exist) - keep as dataclass
        exec_data = data.get("execution", {})
        execution = FeatureExecution(
            started_at=exec_data.get("started_at"),
            completed_at=exec_data.get("completed_at"),
            worktree_path=exec_data.get("worktree_path"),
            total_turns=exec_data.get("total_turns", 0),
            tasks_completed=exec_data.get("tasks_completed", 0),
            tasks_deferred=exec_data.get("tasks_deferred", 0),
            tasks_failed=exec_data.get("tasks_failed", 0),
            current_wave=exec_data.get("current_wave", 0),
            completed_waves=exec_data.get("completed_waves", []),
            last_updated=exec_data.get("last_updated"),
            archived_at=exec_data.get("archived_at"),
            archived_to=exec_data.get("archived_to"),
        )

        # Use Pydantic to construct Feature
        try:
            # Ensure created is a string (convert datetime if needed)
            created_value = data.get("created")
            if created_value is None:
                created_str = datetime.now().isoformat()
            elif isinstance(created_value, datetime):
                created_str = created_value.isoformat()
            else:
                created_str = str(created_value)

            return Feature.model_validate({
                "id": data["id"],
                "name": data.get("name") or data["id"],
                "description": data.get("description", ""),
                "created": created_str,
                "status": data.get("status", "planned"),
                "complexity": data.get("complexity", 5),
                "estimated_tasks": data.get("estimated_tasks", len(tasks)),
                "tasks": tasks,
                "orchestration": orchestration,
                "execution": execution,
                "smoke_gates": smoke_gates,
                # TS-lane D.1a: thread the validated declaration through.
                # Feature.model_config is extra="ignore", so an untranslated
                # key here would be silently dropped exactly the way
                # evidence_repos once was (TASK-FIX-XREPO-CAUD).
                "behavioural_oracle": behavioural_oracle,
                "bootstrap_extras": data.get("bootstrap_extras", []),
                # TASK-FIX-XREPO-CAUD: thread declared sibling repos through.
                # Without this the field is silently dropped here and
                # ``feature.evidence_repos`` is always [], so the cross-repo
                # contract (resolve_evidence_repos in feature_orchestrator)
                # never activates on the feature path — declaring
                # ``evidence_repos`` in the YAML was inert (FEAT-RBX repro).
                "evidence_repos": data.get("evidence_repos", []),
                # Scenario stamp fields: thread them through — Feature is
                # extra="ignore", so an unthreaded key here would be silently
                # dropped exactly the way evidence_repos once was.
                "routing_law": data.get("routing_law"),
                "feature_files": data.get("feature_files", []),
                "scenarios": data.get("scenarios", {}),
                # DELIVERY OWNERSHIP (B9 corrections, 19 September 2026): thread
                # the plan writer's own top-level ownership map through. Feature
                # is extra="ignore", so an unthreaded key here is silently
                # dropped — exactly how evidence_repos was once inert.
                "scenario_owners": data.get("scenario_owners", {}),
            })
        except ValidationError as e:
            raise FeatureParseError(
                f"Invalid feature data:\n{e}"
            ) from e

    @staticmethod
    def _parse_task(task_data: Dict[str, Any]) -> FeatureTask:
        """
        Parse task dictionary into FeatureTask Pydantic model.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Raw task data from YAML

        Returns
        -------
        FeatureTask
            Parsed task instance

        Raises
        ------
        FeatureParseError
            If required fields are missing or validation fails
        """
        # The one required field (item 7 of the cull): a task with no id
        # cannot be named or scheduled. A missing file_path keeps the empty
        # default; the task file is then found by its id.
        required_fields = ["id"]

        for field in required_fields:
            if field not in task_data:
                task_id = task_data.get("id", "<unknown>")
                raise FeatureParseError(
                    _build_schema_error_message(
                        missing_field=field,
                        context=f"task '{task_id}'",
                        data=task_data,
                        schema=TASK_SCHEMA,
                    )
                )

        # Use Pydantic validation
        try:
            return FeatureTask.model_validate(task_data)
        except ValidationError as e:
            task_id = task_data.get("id", "<unknown>")
            raise FeatureParseError(
                f"Invalid task data for '{task_id}':\n{e}"
            ) from e

    @staticmethod
    def validate_feature(
        feature: Feature,
        repo_root: Optional[Path] = None,
    ) -> List[str]:
        """
        Validate feature structure and task file existence.

        Parameters
        ----------
        feature : Feature
            Feature to validate
        repo_root : Optional[Path]
            Repository root (default: current directory)

        Returns
        -------
        List[str]
            List of validation errors (empty if valid)
        """
        repo_root = repo_root or Path.cwd()
        errors = []

        # Check for tasks
        if not feature.tasks:
            errors.append("Feature has no tasks defined")

        # A task file that is not there leaves nothing to build from (item 7
        # of the cull). The path's form is not checked: the file is also
        # looked for by task id across the task folders.
        for task in feature.tasks:
            task_file = repo_root / task.file_path
            if not task_file.exists() and not _resolve_task_across_lifecycle(
                repo_root, task.id
            ):
                errors.append(f"Task file not found: {task.id} at {task.file_path}")

        # Waves and dependencies (argued keep in the cull, 27 October 2026):
        # the scheduler runs only the tasks named in a wave, and skips a task
        # whose dependency has not finished, so these mistakes lose work at
        # run time rather than at planning time.
        all_task_ids = {t.id for t in feature.tasks}
        orchestrated_ids = set()
        for wave in feature.orchestration.parallel_groups:
            for task_id in wave:
                orchestrated_ids.add(task_id)
                if task_id not in all_task_ids:
                    errors.append(
                        f"Orchestration references unknown task: {task_id}"
                    )

        # Check all tasks are in orchestration
        missing = all_task_ids - orchestrated_ids
        if missing:
            errors.append(
                f"Tasks not in orchestration: {', '.join(missing)}"
            )

        # Check for intra-wave dependencies (tasks depending on others in same wave)
        wave_errors = FeatureLoader.validate_parallel_groups(feature)
        errors.extend(wave_errors)

        return errors

    @staticmethod
    def validate_parallel_groups(feature: Feature) -> List[str]:
        """
        Validate that no task depends on another task in the same parallel group (wave).

        Tasks in the same wave execute in parallel and cannot wait for each other.
        If task A depends on task B, they must be in different waves with B in an earlier wave.

        Parameters
        ----------
        feature : Feature
            Feature to validate

        Returns
        -------
        List[str]
            List of validation errors (empty if valid)
        """
        errors = []
        # The first wave each task appears in. A dependency placed in a LATER
        # wave than the task that needs it is as wrong as one in the same wave:
        # the task would start before the work it needs exists.
        first_wave: Dict[str, int] = {}
        for wave_num, task_ids in enumerate(feature.orchestration.parallel_groups, 1):
            for task_id in task_ids:
                first_wave.setdefault(task_id, wave_num)
        for wave_num, task_ids in enumerate(feature.orchestration.parallel_groups, 1):
            wave_set = set(task_ids)
            for task_id in task_ids:
                task = FeatureLoader.find_task(feature, task_id)
                if task:
                    for dep_id in task.dependencies:
                        if dep_id in wave_set:
                            errors.append(
                                f"Wave {wave_num}: {task_id} depends on {dep_id} "
                                f"but both are in the same parallel group. "
                                f"Move {task_id} to a later wave."
                            )
                        elif first_wave.get(dep_id, 0) > wave_num:
                            dep_wave = first_wave[dep_id]
                            errors.append(
                                f"Wave {wave_num}: {task_id} depends on {dep_id}, "
                                f"but {dep_id} is in wave {dep_wave}, which runs "
                                f"later. Move {task_id} to a wave after wave "
                                f"{dep_wave}, or {dep_id} to a wave before wave "
                                f"{wave_num}."
                            )
        return errors

    @staticmethod
    def _readable_task_file(repo_root: Path, task: FeatureTask) -> Optional[Path]:
        """The task's file as it stands now: the pinned ``file_path`` when it is
        there, otherwise wherever the task has moved in the lifecycle
        (``backlog`` -> ``design_approved`` -> ...). ``None`` when neither
        exists; the missing-file check reports that case."""
        pinned = repo_root / task.file_path
        if str(task.file_path) not in ("", ".") and pinned.is_file():
            return pinned
        return _resolve_task_across_lifecycle(repo_root, task.id)

    @staticmethod
    def validate_task_references(
        feature: Feature,
        repo_root: Optional[Path] = None,
    ) -> List[str]:
        """Kept for callers outside GuardKit (specialist-agent); returns no
        findings. The check that a task file naming another task has an
        order to it was deleted in the cull (27 October 2026, GKT-049)."""
        return []

    @staticmethod
    def validate_yaml(data: Dict[str, Any]) -> List[str]:
        """
        Validate raw feature YAML data against Pydantic schema.

        This method validates a dictionary representation of a feature
        before writing to YAML. It can be used standalone without a Feature
        instance.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw feature data dictionary (as would be loaded from YAML)

        Returns
        -------
        List[str]
            List of human-readable error strings (empty if valid).
            Each error includes field name, expected value, and actual value.

        Examples
        --------
        >>> data = {"id": "FEAT-001", "name": "Test", "status": "planned", "tasks": []}
        >>> errors = FeatureLoader.validate_yaml(data)
        >>> if errors:
        ...     for error in errors:
        ...         print(error)
        """
        errors = []

        try:
            # Validate using Pydantic Feature model
            Feature.model_validate(data)
        except ValidationError as e:
            # Convert Pydantic ValidationError to human-readable strings
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_type = error["type"]
                msg = error["msg"]

                # Extract field value if available
                try:
                    current = data
                    for loc in error["loc"]:
                        if isinstance(current, dict):
                            current = current.get(loc)
                        elif isinstance(current, list) and isinstance(loc, int):
                            current = current[loc] if loc < len(current) else None
                        else:
                            current = None
                            break
                    actual_value = current
                except (KeyError, IndexError, TypeError):
                    actual_value = "<not found>"

                # Format human-readable error message
                if error_type == "literal_error":
                    # Extract expected values from error message
                    expected = error.get("ctx", {}).get("expected", "")
                    error_msg = f"Field '{field_path}': Invalid value '{actual_value}'. Expected one of: {expected}"
                elif error_type == "missing":
                    error_msg = f"Field '{field_path}': Required field is missing"
                elif error_type == "value_error":
                    error_msg = f"Field '{field_path}': {msg}. Actual value: {actual_value}"
                elif error_type.startswith("type_error"):
                    expected_type = error.get("ctx", {}).get("expected_type", "")
                    error_msg = f"Field '{field_path}': Expected type {expected_type}, got {type(actual_value).__name__}. Actual value: {actual_value}"
                else:
                    error_msg = f"Field '{field_path}': {msg}. Actual value: {actual_value}"

                errors.append(error_msg)

        return errors

    @staticmethod
    def save_feature(
        feature: Feature,
        repo_root: Optional[Path] = None,
    ) -> None:
        """
        Save feature state back to YAML file.

        Parameters
        ----------
        feature : Feature
            Feature to save
        repo_root : Optional[Path]
            Repository root (default: current directory)

        Notes
        -----
        Uses feature.file_path if available, otherwise constructs path
        from feature.id.

        Step 1 (24 October 2026): saving the feature record is bookkeeping and
        never ends a build. A record that fails validation is logged and not
        written (writing it would leave an unreadable file); a failed write
        is retried once, then logged. Nothing here raises.
        """
        for attempt in (1, 2):
            try:
                FeatureLoader._write_feature(feature, repo_root)
                return
            except Exception as exc:  # noqa: BLE001 — bookkeeping, never fatal
                logger.warning(
                    "Could not save feature %s (attempt %d of 2): %s",
                    feature.id, attempt, exc,
                )

    @staticmethod
    def _write_feature(feature: Feature, repo_root: Optional[Path]) -> None:
        repo_root = repo_root or Path.cwd()

        if feature.file_path:
            file_path = feature.file_path
        else:
            file_path = repo_root / FeatureLoader.FEATURES_DIR / f"{feature.id}.yaml"

        # Convert to dictionary
        data = FeatureLoader._feature_to_dict(feature)

        validation_errors = FeatureLoader.validate_yaml(data)
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"Validation error in feature {feature.id}: {error}")
            logger.warning(
                "Feature %s record not written: it does not validate; the "
                "build goes on", feature.id,
            )
            return

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML
        with open(file_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.debug(f"Saved feature to {file_path}")

    @staticmethod
    def _feature_to_dict(feature: Feature) -> Dict[str, Any]:
        """
        Convert Feature to dictionary for YAML serialization.

        Parameters
        ----------
        feature : Feature
            Feature to convert

        Returns
        -------
        Dict[str, Any]
            Dictionary representation
        """
        # Use Pydantic's model_dump for Feature, FeatureOrchestration, and FeatureTask
        data = feature.model_dump(exclude={"file_path", "execution"})

        # Convert Path objects to strings for tasks
        for task_dict in data["tasks"]:
            if "file_path" in task_dict:
                task_dict["file_path"] = str(task_dict["file_path"])

        # Drop ``smoke_gates`` when not configured to keep YAML minimal.
        # A missing key and a null key are equivalent on load, so avoid
        # emitting ``smoke_gates: null`` into feature files.
        if data.get("smoke_gates") is None:
            data.pop("smoke_gates", None)

        # Same law for behavioural_oracle (coordinator cure, D.1a coach):
        # never persist ``behavioural_oracle: null`` into every rewritten
        # feature file — a missing key and a null key load identically.
        if data.get("behavioural_oracle") is None:
            data.pop("behavioural_oracle", None)

        # Drop ``bootstrap_extras`` when empty. Auto-detection lives at
        # bootstrap time (see :func:`derive_bootstrap_extras`) so we
        # never persist an inferred value back to YAML — keeps the
        # operator-declared field unambiguous. (TASK-GK-BS-001)
        if not data.get("bootstrap_extras"):
            data.pop("bootstrap_extras", None)

        # Scenario stamp fields: same missing-key-equals-null law. Never sprout
        # ``routing_law: null`` / empty maps into every rewritten feature
        # file; compact each stamp so ``test_ref: null`` is not persisted.
        if data.get("routing_law") is None:
            data.pop("routing_law", None)
        if not data.get("feature_files"):
            data.pop("feature_files", None)
        if not data.get("scenarios"):
            data.pop("scenarios", None)
        else:
            data["scenarios"] = {
                title: {k: v for k, v in stamp.items() if v is not None}
                for title, stamp in data["scenarios"].items()
            }
        # DELIVERY OWNERSHIP (B9, 19 September 2026): same missing-key-equals-
        # empty law — never sprout an empty `scenario_owners: {}` into every
        # rewritten feature file. When present it is written back verbatim, so a
        # feature that declares ownership keeps it across every rewrite.
        if not data.get("scenario_owners"):
            data.pop("scenario_owners", None)

        # Manually serialize execution (dataclass)
        data["execution"] = {
            "started_at": feature.execution.started_at,
            "completed_at": feature.execution.completed_at,
            "worktree_path": feature.execution.worktree_path,
            "total_turns": feature.execution.total_turns,
            "tasks_completed": feature.execution.tasks_completed,
            "tasks_deferred": feature.execution.tasks_deferred,
            "tasks_failed": feature.execution.tasks_failed,
            "current_wave": feature.execution.current_wave,
            "completed_waves": feature.execution.completed_waves,
            "last_updated": feature.execution.last_updated,
            "archived_at": feature.execution.archived_at,
            "archived_to": feature.execution.archived_to,
        }

        return data

    @staticmethod
    def find_task(feature: Feature, task_id: str) -> Optional[FeatureTask]:
        """
        Find a task by ID within a feature.

        Parameters
        ----------
        feature : Feature
            Feature to search
        task_id : str
            Task ID to find

        Returns
        -------
        Optional[FeatureTask]
            Task if found, None otherwise
        """
        for task in feature.tasks:
            if task.id == task_id:
                return task
        return None

    @staticmethod
    def is_incomplete(feature: Feature) -> bool:
        """
        Check if a feature has incomplete execution state.

        A feature is considered incomplete if:
        - Status is 'in_progress', 'paused', or 'failed'
        - Has any tasks in 'in_progress' or 'failed' status
        - Has executed at least one wave but not all tasks are completed

        Note on 'failed' inclusion (TASK-FIX-RESUME-FAILED): a feature with
        ``status: failed`` and any retryable failed tasks is *resumable*, not
        terminal. Treating it as complete caused ``--resume`` to silently fall
        through to ``_create_new_worktree`` in ``_setup_phase``, destroying
        the existing worktree's checkpoint commits when the user explicitly
        asked to resume. Discovered when re-running FEAT-FG-001 after an
        AB-006-style upstream fix made a previously-stalled task retryable.

        Parameters
        ----------
        feature : Feature
            Feature to check

        Returns
        -------
        bool
            True if feature execution is incomplete (resumable)
        """
        # Check status — 'failed' is incomplete because failed tasks can be
        # retried after an upstream fix.
        if feature.status in ("in_progress", "paused", "failed"):
            return True

        # Check for in-progress or failed tasks at the task level — covers
        # the case where the feature-level status doesn't match (e.g. paused
        # mid-wave with one task failed).
        for task in feature.tasks:
            if task.status in ("in_progress", "failed"):
                return True

        # Check if we have partial completion. 'failed' tasks count as
        # not-yet-completed (they may be retried) so the upper bound here
        # is the count of *completed* tasks rather than tasks in any
        # terminal state.
        if feature.execution.started_at:
            completed_count = sum(
                1 for t in feature.tasks if t.status == "completed"
            )

            # If we started but haven't completed all tasks
            if 0 < completed_count < len(feature.tasks):
                return True

        return False

    @staticmethod
    def get_resume_point(feature: Feature) -> Dict[str, Any]:
        """
        Get the resume point for an incomplete feature.

        Returns information about where to resume execution.

        Parameters
        ----------
        feature : Feature
            Feature to analyze

        Returns
        -------
        Dict[str, Any]
            Resume point information including:
            - wave: Wave number to resume from (1-indexed)
            - task_id: Task ID to resume (if in_progress)
            - turn: Turn to resume from (if in_progress)
            - completed_tasks: List of completed task IDs
            - pending_tasks: List of pending task IDs
        """
        completed_tasks = [t.id for t in feature.tasks if t.status == "completed"]
        pending_tasks = [t.id for t in feature.tasks if t.status == "pending"]
        in_progress_task = None
        resume_turn = 0

        for task in feature.tasks:
            if task.status == "in_progress":
                in_progress_task = task.id
                resume_turn = task.current_turn
                break

        # Determine which wave to resume from
        resume_wave = feature.execution.current_wave or 1
        if feature.execution.completed_waves:
            resume_wave = max(feature.execution.completed_waves) + 1

        return {
            "wave": resume_wave,
            "task_id": in_progress_task,
            "turn": resume_turn,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "worktree_path": feature.execution.worktree_path,
        }

    @staticmethod
    def reset_state(feature: Feature) -> None:
        """
        Reset feature execution state for a fresh start.

        Parameters
        ----------
        feature : Feature
            Feature to reset
        """
        # Reset feature-level state
        feature.status = "planned"
        feature.execution = FeatureExecution()

        # Reset all task states
        for task in feature.tasks:
            task.status = "pending"
            task.result = None
            task.turns_completed = 0
            task.current_turn = 0
            task.started_at = None
            task.completed_at = None


# ============================================================================
# Bootstrap-extras derivation (TASK-GK-BS-001)
# ============================================================================


# Candidate extras to probe when auto-detecting test deps from a smoke gate.
# ``dev`` first because it's the conventional PEP 621 / PyPA name for "all
# the things a contributor needs"; ``test`` second because it's the narrower
# convention some projects prefer. If neither is present we log a warning
# and fall through with no extras (current pre-fix behaviour).
_AUTO_DETECT_EXTRA_CANDIDATES: List[str] = ["dev", "test"]

# Word-boundary match on the literal ``pytest``. Case-insensitive so
# ``Pytest`` / ``PYTEST`` in operator-authored shell commands also fire.
# Constrained to the boundary form so unrelated tokens like
# ``pytestify-runner`` don't trigger.
_PYTEST_COMMAND_PATTERN = re.compile(r"\bpytest\b", re.IGNORECASE)


def _read_pyproject_optional_dependencies(
    project_dir: Path,
) -> Dict[str, Any]:
    """Return ``[project.optional-dependencies]`` from ``project_dir/pyproject.toml``.

    Returns an empty dict on any of:
      - pyproject.toml absent
      - pyproject.toml unparseable (malformed TOML)
      - ``[project.optional-dependencies]`` table absent

    The conservative empty-dict fallback matches the pattern in
    ``environment_bootstrap._pyproject_has_uv_sources``: detection helpers
    swallow parse errors so the orchestrator surfaces them later via the
    actual install command (where pip's error message is more useful than
    a YAML-load wrapping it). (TASK-GK-BS-001)
    """
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.is_file():
        return {}
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # type: ignore[import,no-redef]
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug(
            "Could not parse %s for bootstrap_extras auto-detection: %s",
            pyproject_path,
            exc,
        )
        return {}
    optional = data.get("project", {}).get("optional-dependencies", {})
    return optional if isinstance(optional, dict) else {}


def _extra_provides_pytest(
    optional_deps: Dict[str, Any],
    extra: str,
) -> bool:
    """Return True when the named optional-dependency *extra* lists pytest.

    Used by the Coach-always-needs-pytest branch of
    :func:`derive_bootstrap_extras` (TASK-FIX-BOOTPYTEST01). Unlike the
    smoke-gate branch — which trusts an operator's pytest command and
    installs the canonical extra by *name* — this branch has no operator
    signal, so it only auto-adds an extra that demonstrably carries the
    pytest toolchain. Reusing ``_PYTEST_COMMAND_PATTERN`` (the ``\\bpytest\\b``
    word-boundary match) also accepts pytest plugins such as ``pytest-bdd``
    / ``pytest-asyncio`` as evidence of a test extra, while rejecting a
    ``[dev]`` group that holds only linters (e.g. ``ruff``, ``mypy``).

    Parameters
    ----------
    optional_deps : Dict[str, Any]
        ``[project.optional-dependencies]`` table as returned by
        :func:`_read_pyproject_optional_dependencies`.
    extra : str
        The extra name to inspect (e.g. ``"dev"``).

    Returns
    -------
    bool
        True when ``optional_deps[extra]`` is a list containing at least
        one requirement string matching ``\\bpytest\\b``.
    """
    deps = optional_deps.get(extra)
    if not isinstance(deps, list):
        return False
    return any(
        isinstance(dep, str) and _PYTEST_COMMAND_PATTERN.search(dep)
        for dep in deps
    )


def derive_bootstrap_extras(
    feature: Feature,
    project_dir: Path,
) -> List[str]:
    """Resolve the final extras list for a feature's bootstrap step.

    Resolution order (TASK-GK-BS-001 AC-1/AC-3/AC-5; branch 3 added by
    TASK-FIX-BOOTPYTEST01):

    1. **Operator-declared** (``feature.bootstrap_extras``) — wins if
       non-empty. AC-5: explicit declaration suppresses auto-detection.
    2. **Smoke-gate auto-detection** — when ``feature.smoke_gates`` is
       configured AND ``smoke_gates.command`` references ``pytest`` at a
       word boundary (case-insensitive), probe ``project_dir/pyproject.toml``
       for the canonical test-extra name (``[dev]`` first, then ``[test]``).
       Returns the first match. If a pytest smoke gate is present but
       pyproject declares neither ``[dev]`` nor ``[test]``, log a warning
       naming both candidates (the most actionable operator feedback) and
       fall through to no extras.
    3. **Coach-always-needs-pytest** (TASK-FIX-BOOTPYTEST01) — the Coach's
       independent-test gate runs ``pytest`` in the worktree venv for
       *every* Python task, unconditionally. So even without an operator
       declaration or a pytest smoke gate, if the project declares a
       ``[dev]``/``[test]`` extra that *provides* pytest (see
       :func:`_extra_provides_pytest`), install it — otherwise the Coach's
       pinned interpreter cannot ``import pytest`` on early turns and reports
       "missing pytest dependency" feedback until the Player incidentally
       installs it. Returns the first candidate extra that carries pytest.
    4. **No extras** — when none of the above apply, return an empty list.

    This is a *pure* function — no side effects on ``feature`` — so the
    auto-detection result is never persisted back to YAML. The orchestrator
    re-derives at every bootstrap, which keeps the operator-declared field
    unambiguous.

    Parameters
    ----------
    feature : Feature
        Already-parsed feature (so ``bootstrap_extras`` has been validated
        against the PEP 621 name regex).
    project_dir : Path
        Directory containing ``pyproject.toml`` to probe for auto-detection.
        Typically the worktree root at bootstrap time.

    Returns
    -------
    List[str]
        Extras to install. Empty list means "no extras"
        (equivalent to pre-TASK-GK-BS-001 behaviour).
    """
    # 1. Operator-declared wins.
    if feature.bootstrap_extras:
        return list(feature.bootstrap_extras)

    optional_deps = _read_pyproject_optional_dependencies(project_dir)

    # 2. Smoke-gate auto-detection: an operator-authored pytest smoke gate is
    #    an explicit signal to install the canonical test extra by name.
    smoke_command = (
        feature.smoke_gates.command if feature.smoke_gates is not None else None
    )
    if smoke_command is not None and _PYTEST_COMMAND_PATTERN.search(smoke_command):
        for candidate in _AUTO_DETECT_EXTRA_CANDIDATES:
            if candidate in optional_deps:
                logger.info(
                    "Smoke gate references pytest; auto-adding [%s] to "
                    "bootstrap extras (project: %s).",
                    candidate,
                    project_dir,
                )
                return [candidate]

        # Pytest smoke gate but no candidate extra — surface the gap. Branch 3
        # below cannot help either: it probes the same candidates with a
        # stricter provides-pytest filter, so it would also find nothing.
        logger.warning(
            "Smoke gate command %r references pytest but pyproject at %s "
            "declares neither [dev] nor [test] optional-dependencies. "
            "Smoke gate may fail with 'No module named pytest'. Either add "
            "a [dev] or [test] extra to pyproject.toml, or set "
            "bootstrap_extras: [<your-name>] explicitly in the feature yaml.",
            smoke_command,
            project_dir,
        )
        return []

    # 3. Coach-always-needs-pytest (TASK-FIX-BOOTPYTEST01). The Coach's
    #    independent-test gate runs pytest in the worktree venv for every
    #    Python task, regardless of smoke-gate / operator config. Install the
    #    first [dev]/[test] extra that actually *provides* pytest so the
    #    Coach's pinned interpreter is test-capable from turn 1 — otherwise it
    #    reports "missing pytest dependency" until the Player installs it.
    for candidate in _AUTO_DETECT_EXTRA_CANDIDATES:
        if _extra_provides_pytest(optional_deps, candidate):
            logger.info(
                "Coach runs independent pytest unconditionally; auto-adding "
                "[%s] to bootstrap extras so the worktree venv can import "
                "pytest from turn 1 (project: %s).",
                candidate,
                project_dir,
            )
            return [candidate]

    # 4. No extras.
    return []


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Data models
    "Feature",
    "FeatureTask",
    "FeatureOrchestration",
    "FeatureExecution",
    # Loader
    "FeatureLoader",
    # Helpers
    "derive_bootstrap_extras",
    # Exceptions
    "FeatureNotFoundError",
    "FeatureParseError",
    "FeatureValidationError",
    # Schema constants (for external use)
    "TASK_SCHEMA",
    "FEATURE_SCHEMA",
    "ORCHESTRATION_SCHEMA",
    # Re-exported for convenience
    "TaskType",
    "TASK_TYPE_ALIASES",
]


def _resolve_task_across_lifecycle(repo_root: Path, task_id: str) -> Path | None:
    """Find a task file by ID anywhere in the task lifecycle.

    A feature's ``file_path`` is written once, at planning time, pointing into ``tasks/backlog/``.
    The file then MOVES as the task progresses (``backlog`` -> ``design_approved`` -> ...), and
    nothing rewrites the pin. Validation that only checks the pinned path therefore fails for any
    feature whose tasks actually progressed — and passes only when a stale duplicate happens to
    remain in backlog.

    Measured in api_test on 2026-08-24: FEAT-F811 validated ONLY because copies lingered in both
    ``tasks/backlog/`` and ``tasks/backlog/version-endpoint/``; FEAT-0CAC and FEAT-F2B0 both failed
    with their task sitting correctly in ``tasks/design_approved/``. A green result that depends on
    leftover duplicates is not a check.

    The lifecycle directories are the same list ``TaskLoader.SEARCH_PATHS`` already uses — imported
    rather than restated so the two cannot drift.
    """
    try:
        from guardkit.tasks.task_loader import TaskLoader

        search_paths = TaskLoader.SEARCH_PATHS
    except Exception:  # noqa: BLE001 - loader is optional in some install shapes
        search_paths = ["backlog", "in_progress", "design_approved", "in_review", "blocked"]

    tasks_root = Path(repo_root) / "tasks"
    if not tasks_root.is_dir():
        return None
    for state in search_paths:
        state_dir = tasks_root / state
        if not state_dir.is_dir():
            continue
        # the file may sit directly in the state dir or in a per-feature subdirectory
        for candidate in state_dir.glob(f"**/{task_id}-*.md"):
            return candidate
    return None
