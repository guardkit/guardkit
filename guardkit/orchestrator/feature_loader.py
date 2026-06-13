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

logger = logging.getLogger(__name__)


# ============================================================================
# Schema Documentation (for error messages)
# ============================================================================

TASK_SCHEMA = """
Task Schema:
  id: str (required)        # e.g., "TASK-XXX-YYYY"
  file_path: str (required) # Path to task markdown file
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
  name: str (required)      # Human-readable name
  description: str          # Feature description
  tasks: list               # List of task objects
  orchestration: dict       # Parallel execution configuration
"""

ORCHESTRATION_SCHEMA = """
Orchestration Schema:
  parallel_groups: list     # Lists of task IDs per wave
  estimated_duration_minutes: int
  recommended_parallel: int # Recommended max parallel tasks
"""


# ============================================================================
# Error Message Helpers
# ============================================================================


def _find_similar_ids(target: str, candidates: set, max_distance: int = 2) -> List[str]:
    """
    Find task IDs similar to the target from a set of candidates.

    Uses simple matching logic: prefix matching and character difference count.
    Returns up to 3 similar IDs sorted by similarity.

    Parameters
    ----------
    target : str
        The unknown task ID to find matches for
    candidates : set
        Set of valid task IDs to search
    max_distance : int
        Maximum character differences allowed (default: 2)

    Returns
    -------
    List[str]
        List of similar task IDs (up to 3), sorted by similarity
    """
    similar = []
    target_lower = target.lower()

    for candidate in candidates:
        candidate_lower = candidate.lower()

        # Check prefix match (e.g., TASK-XXX-001 matches TASK-XXX-002)
        # Extract prefix up to last number segment
        target_prefix = target_lower.rsplit("-", 1)[0] if "-" in target_lower else target_lower
        candidate_prefix = candidate_lower.rsplit("-", 1)[0] if "-" in candidate_lower else candidate_lower

        if target_prefix == candidate_prefix:
            similar.append((0, candidate))  # Priority 0 for prefix match
            continue

        # Check character difference count (simple edit distance approximation)
        if len(target) == len(candidate):
            diff_count = sum(1 for a, b in zip(target_lower, candidate_lower) if a != b)
            if diff_count <= max_distance:
                similar.append((diff_count, candidate))
                continue

        # Check if one contains the other (substring match)
        if target_lower in candidate_lower or candidate_lower in target_lower:
            similar.append((1, candidate))

    # Sort by similarity score (lower is better), then alphabetically
    similar.sort(key=lambda x: (x[0], x[1]))

    # Return up to 3 matches, extracting just the IDs
    return [item[1] for item in similar[:3]]


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
    complexity: int = Field(default=5, ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed", "skipped", "deferred"] = "pending"
    implementation_mode: Literal["direct", "task-work", "manual"] = "task-work"
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
    recommended_parallel : int
        Recommended max parallel tasks
    """

    model_config = ConfigDict(extra="ignore")

    parallel_groups: List[List[str]] = Field(default_factory=list)
    estimated_duration_minutes: int = 0
    recommended_parallel: int = 1


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
        Seconds before the subprocess is killed. Bounded [1, 600] to keep
        ``/feature-build`` deterministic. Default: 120.
    exit5_is_hard_fail : bool
        Treat pytest exit code 5 (no tests collected) as a hard failure.
        Default ``False`` — exit 5 is treated as a soft "gate not wired"
        warning and the feature build continues. Set to ``True`` for strict
        gate enforcement (TASK-FIX-SG05).
    """

    # ``extra="forbid"`` ensures malformed configuration (typos, unknown
    # keys) is rejected before ``/feature-build`` starts, per AC.
    model_config = ConfigDict(extra="forbid")

    after_wave: Union[int, List[int], Literal["all"]]
    command: str = Field(min_length=1)
    expected_exit: int = 0
    timeout: int = Field(default=120, ge=1, le=600)
    exit5_is_hard_fail: bool = False

    @field_validator("after_wave", mode="before")
    @classmethod
    def _validate_after_wave(cls, v: Any) -> Any:
        """Reject invalid after_wave shapes before Pydantic's type coercion.

        ``mode="before"`` runs on the raw input, so we can reject ``True``
        before it is coerced to ``1`` (bool is a subclass of int in Python).
        """
        if isinstance(v, bool):
            raise ValueError("after_wave must be int, list of ints, or 'all'")
        if isinstance(v, int):
            if v < 1:
                raise ValueError("after_wave must be >= 1 (waves are 1-indexed)")
            return v
        if isinstance(v, list):
            if not v:
                raise ValueError("after_wave list cannot be empty")
            for item in v:
                if isinstance(item, bool) or not isinstance(item, int):
                    raise ValueError(
                        "after_wave list must contain positive integers"
                    )
                if item < 1:
                    raise ValueError(
                        "after_wave list must contain positive integers"
                    )
            return v
        if v == "all":
            return v
        raise ValueError("after_wave must be int, list of ints, or 'all'")


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
        Current feature status
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
    name: str
    description: str = ""
    created: str = ""
    status: Literal["planned", "in_progress", "completed", "failed", "paused"] = "planned"
    complexity: int = 5
    estimated_tasks: int = 0
    tasks: List[FeatureTask] = Field(default_factory=list)
    orchestration: FeatureOrchestration = Field(default_factory=FeatureOrchestration)
    execution: FeatureExecution = Field(default_factory=FeatureExecution)
    smoke_gates: Optional[SmokeGates] = None
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
    file_path: Optional[Path] = None

    @field_validator("evidence_repos")
    @classmethod
    def _validate_evidence_repos(cls, v: List[Any]) -> List[Any]:
        """Reject malformed ``evidence_repos`` declarations at parse time.

        Each entry must be a non-empty path string, or a mapping carrying a
        ``path`` (string) and an optional ``test_command`` (string). Failing
        loudly here is the namespace-hygiene / seam-test posture: a feature
        that declares cross-repo evidence must not be silently degraded to
        absent-signal by a typo (TASK-AB-XREPOEV01).
        """
        if not isinstance(v, list):
            raise ValueError("evidence_repos must be a list")
        for entry in v:
            if isinstance(entry, str):
                if not entry.strip():
                    raise ValueError("evidence_repos entries must be non-empty paths")
                continue
            if isinstance(entry, dict):
                path = entry.get("path") or entry.get("repo")
                if not isinstance(path, str) or not path.strip():
                    raise ValueError(
                        "evidence_repos mapping entries require a non-empty "
                        f"'path' string; got {entry!r}"
                    )
                test_command = entry.get("test_command") or entry.get("tests")
                if test_command is not None and not isinstance(test_command, str):
                    raise ValueError(
                        "evidence_repos 'test_command' must be a string; got "
                        f"{test_command!r}"
                    )
                continue
            raise ValueError(
                "evidence_repos entries must be a path string or a mapping "
                f"with a 'path' key; got {entry!r}"
            )
        return v

    @field_validator("bootstrap_extras")
    @classmethod
    def _validate_bootstrap_extras(cls, v: List[str]) -> List[str]:
        """Validate each entry is a syntactically valid PEP 621 extra name.

        Per PEP 621 / PyPA spec, optional-dependency keys are restricted to
        the same character class as project names: letters, digits, dots,
        hyphens, underscores. Reject anything else at parse time so the
        operator sees a useful error from ``/feature-build`` instead of a
        cryptic pip error during bootstrap. (TASK-GK-BS-001 AC-1)
        """
        if not isinstance(v, list):
            raise ValueError("bootstrap_extras must be a list of strings")
        pattern = re.compile(r"^[A-Za-z0-9._-]+$")
        for entry in v:
            if not isinstance(entry, str):
                raise ValueError(
                    f"bootstrap_extras entries must be strings; got {entry!r}"
                )
            if not pattern.match(entry):
                raise ValueError(
                    f"bootstrap_extras contains invalid PEP 621 extra name: "
                    f"{entry!r}. Names must match ^[A-Za-z0-9._-]+$"
                )
        return v


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


class SchemaValidationError(FeatureParseError):
    """Raised when a feature YAML schema section is malformed.

    Subclass of ``FeatureParseError`` so existing ``except FeatureParseError``
    handlers continue to work. Used specifically for schema-level violations
    (e.g. malformed ``smoke_gates``) that must be surfaced before
    ``/feature-build`` starts — see TASK-SMK-F703A.
    """

    pass


class SmokeGatePathError(SchemaValidationError):
    """Raised when ``smoke_gates.command`` references a non-existent path.

    Subclass of ``SchemaValidationError`` (and therefore
    ``FeatureParseError``) so existing handlers in the orchestrator
    pre-flight chain continue to work, but distinguishable for tests
    and post-mortem triage that want to tell a path-existence miss
    apart from a Pydantic schema violation. See TASK-FPSG-005 (L4 —
    defense-in-depth) and the parent review TASK-REV-DEA8.
    """

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

    @staticmethod
    def load_feature(
        feature_id: str,
        repo_root: Optional[Path] = None,
        features_dir: Optional[Path] = None,
        validate_paths: bool = True,
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
            When True (default), the L4 pre-flight check raises
            :class:`SmokeGatePathError` if ``smoke_gates.command``
            references a non-existent path. When False, the pre-flight
            is skipped so callers (e.g. ``cli/feature.py validate``)
            can let :func:`validate_feature` aggregate path errors with
            other structural errors instead of failing fast at parse
            time. See TASK-FPSG-004 (L3d).

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
            return feature
        except FeatureParseError:
            # Re-raise with schema hints intact
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
            Repository root used for ``smoke_gates.command`` path-existence
            pre-flight (TASK-FPSG-005). When ``None``, path validation is
            skipped — used only by callers that have no repo context (e.g.
            in-memory parsing for tests).
        validate_paths : bool
            When True (default), runs the L4 pre-flight which raises
            :class:`SmokeGatePathError` for stale ``smoke_gates.command``
            paths. When False, the pre-flight is skipped so a downstream
            :func:`validate_feature` call can aggregate path errors with
            other structural errors. Used by ``cli/feature.py validate``
            (TASK-FPSG-004 L3d) so the user sees every structural issue
            in one report instead of bouncing off a fail-fast raise.

        Returns
        -------
        Feature
            Parsed Feature instance

        Raises
        ------
        FeatureParseError
            If required fields are missing, with schema hints
        """
        # Validate required fields at feature level
        required_fields = ["id", "name"]

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

        # Parse optional smoke_gates (TASK-SMK-F703A). Key absent → None.
        # Malformed key → SchemaValidationError before /feature-build starts.
        smoke_gates_data = data.get("smoke_gates")
        smoke_gates: Optional[SmokeGates] = None
        if smoke_gates_data is not None:
            try:
                smoke_gates = SmokeGates.model_validate(smoke_gates_data)
            except ValidationError as e:
                raise SchemaValidationError(
                    f"Invalid smoke_gates configuration:\n{e}"
                ) from e
            # TASK-FPSG-005 (L4 — defense-in-depth): path-existence
            # pre-flight. Catches stale `tests/cli`-style paths at load
            # time, before the orchestrator bootstraps the worktree and
            # blows ~17 minutes on Wave 1 only to fail on the smoke gate.
            # Skipped when repo_root is unavailable (in-memory parses)
            # or when ``validate_paths`` is False (TASK-FPSG-004 L3d:
            # ``cli/feature.py validate`` aggregates path errors with
            # other structural errors instead of raising).
            if repo_root is not None and validate_paths:
                FeatureLoader._validate_smoke_gates_paths(
                    smoke_gates, repo_root
                )

        # Parse execution (may not exist) - keep as dataclass
        exec_data = data.get("execution", {})
        execution = FeatureExecution(
            started_at=exec_data.get("started_at"),
            completed_at=exec_data.get("completed_at"),
            worktree_path=exec_data.get("worktree_path"),
            total_turns=exec_data.get("total_turns", 0),
            tasks_completed=exec_data.get("tasks_completed", 0),
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
                "name": data["name"],
                "description": data.get("description", ""),
                "created": created_str,
                "status": data.get("status", "planned"),
                "complexity": data.get("complexity", 5),
                "estimated_tasks": data.get("estimated_tasks", len(tasks)),
                "tasks": tasks,
                "orchestration": orchestration,
                "execution": execution,
                "smoke_gates": smoke_gates,
                "bootstrap_extras": data.get("bootstrap_extras", []),
            })
        except ValidationError as e:
            raise FeatureParseError(
                f"Invalid feature data:\n{e}"
            ) from e

    @staticmethod
    def _validate_smoke_gates_paths(
        smoke_gates: SmokeGates,
        repo_root: Path,
    ) -> None:
        """Pre-flight: assert ``smoke_gates.command`` paths exist under ``repo_root``.

        L4 of the four-layer smoke-gate validation chain (TASK-FPSG-005).
        L3a–L3d catch the YAML at authoring time (``feature-plan`` Step 8.5,
        ``--validate-smoke-gates``, ``feature validate``); this layer is the
        runtime safety net that fires when a YAML is hand-edited after
        ``/feature-plan`` finishes and slipped past every authoring check.

        Without this check, a stale ``tests/cli`` path is only discovered
        once ``run_smoke_gate`` runs after Wave 1 — typically ~17 minutes
        of wasted compute on the worktree bootstrap and Wave 1 tasks.

        Path resolution uses ``repo_root`` to match the ``cwd`` that
        ``run_smoke_gate`` will use at execution time
        (see ``feature_orchestrator.py``: ``cwd=Path(worktree.path)`` —
        the worktree shares the same git tree as ``repo_root``, so paths
        that exist in one exist in the other).

        Non-pytest commands (e.g. ``python3 .guardkit/smoke/foo.py``)
        are a no-op: the shared parser returns ``[]`` and nothing is
        validated. This matches TASK-FPSG-002's ``--validate-smoke-gates``
        behaviour — only pytest paths are checked.

        Parameters
        ----------
        smoke_gates : SmokeGates
            Already-validated Pydantic model (Pydantic guarantees
            ``command`` is a non-empty string).
        repo_root : Path
            Repository root the paths are resolved against.

        Raises
        ------
        SmokeGatePathError
            When at least one positional pytest path does not exist
            under ``repo_root``. Message includes every missing path,
            the repo root, and the available test roots so the agent
            has enough context to fix the YAML in one edit.
        """
        # Imports kept local so the lib/ helper stays decoupled from
        # the orchestrator import graph (avoids a circular import if
        # the helper ever needs to reference ``SmokeGates``).
        from guardkit.lib.pytest_argv import (
            format_smoke_gate_path_error,
            parse_positional_paths,
        )
        from installer.core.commands.lib.smoke_gates_nudge import (
            discover_test_roots,
        )

        paths = parse_positional_paths(smoke_gates.command)
        if not paths:
            return

        missing = [p for p in paths if not (repo_root / p).exists()]
        if not missing:
            return

        available_roots = discover_test_roots(repo_root)
        raise SmokeGatePathError(
            format_smoke_gate_path_error(missing, repo_root, available_roots)
        )

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
        # Validate required fields with helpful error messages
        required_fields = ["id", "file_path"]

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

        # Check task files exist and are valid
        for task in feature.tasks:
            task_file = repo_root / task.file_path
            if task_file.is_dir():
                errors.append(
                    f"Task file_path is a directory, not a file: {task.id} at {task.file_path}"
                )
            elif not str(task.file_path).endswith(".md"):
                errors.append(
                    f"Task file_path does not end with .md: {task.id} at {task.file_path}"
                )
            elif "tasks" not in Path(task.file_path).parts:
                errors.append(
                    f"Task file_path does not contain 'tasks' directory: {task.id} at {task.file_path}"
                )
            elif not task_file.exists():
                errors.append(f"Task file not found: {task.id} at {task.file_path}")

        # Check orchestration has all tasks
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

        # Check dependencies are valid
        for task in feature.tasks:
            for dep_id in task.dependencies:
                if dep_id not in all_task_ids:
                    error_msg = f"Task {task.id} has unknown dependency: {dep_id}"
                    similar_ids = _find_similar_ids(dep_id, all_task_ids)
                    if similar_ids:
                        suggestions = ", ".join(similar_ids)
                        error_msg += f". Did you mean: {suggestions}?"
                    errors.append(error_msg)

        # Check for circular dependencies
        circular = FeatureLoader._detect_circular_dependencies(feature)
        if circular:
            errors.append(f"Circular dependency detected: {' -> '.join(circular)}")

        # Check for intra-wave dependencies (tasks depending on others in same wave)
        wave_errors = FeatureLoader.validate_parallel_groups(feature)
        errors.extend(wave_errors)

        # Validate task_type in task file frontmatter (fail-fast on invalid values)
        for task in feature.tasks:
            task_file = repo_root / task.file_path
            if task_file.exists() and task_file.is_file():
                task_type_error = FeatureLoader._validate_task_type_in_file(
                    task.id, task_file
                )
                if task_type_error:
                    errors.append(task_type_error)

        # TASK-FPSG-004 (L3d): smoke-gate command path validation. Same
        # rules as TASK-FPSG-002's --validate-smoke-gates and L4
        # pre-flight; the message is produced via the shared
        # ``format_smoke_gate_path_error`` formatter so the error wording
        # is byte-identical regardless of which defense layer surfaces
        # it. This collects-without-raising path lets callers (e.g.
        # ``cli/feature.py validate``) aggregate path errors alongside
        # orchestration / dependency / task_type errors in one report.
        smoke_gate_path_error = FeatureLoader._validate_smoke_gate_paths_for_validate(
            feature, repo_root
        )
        if smoke_gate_path_error:
            errors.append(smoke_gate_path_error)

        return errors

    @staticmethod
    def _validate_smoke_gate_paths_for_validate(
        feature: Feature,
        repo_root: Path,
    ) -> Optional[str]:
        """Collect-without-raising smoke-gate path check for ``validate_feature``.

        Mirrors :meth:`_validate_smoke_gates_paths` (which raises) but
        returns the formatted error message instead, so it can be added
        to the :func:`validate_feature` errors list. Output is generated
        by the shared ``format_smoke_gate_path_error`` formatter, so the
        message body is byte-identical to L3b (``--validate-smoke-gates``)
        and L4 (``_parse_feature`` pre-flight). See TASK-FPSG-004 (L3d).

        Parameters
        ----------
        feature : Feature
            Already-parsed feature.
        repo_root : Path
            Repo root the command paths are resolved against.

        Returns
        -------
        Optional[str]
            Formatted error message when at least one path is missing,
            ``None`` when there is nothing to validate (no smoke_gates
            block, no command, non-pytest command, or all paths exist).
        """
        if feature.smoke_gates is None:
            return None

        # Lazy imports — match the pattern used in
        # ``_validate_smoke_gates_paths`` (avoids circular imports if the
        # helper ever needs to reference ``SmokeGates``).
        from guardkit.lib.pytest_argv import (
            format_smoke_gate_path_error,
            parse_positional_paths,
        )
        from installer.core.commands.lib.smoke_gates_nudge import (
            discover_test_roots,
        )

        paths = parse_positional_paths(feature.smoke_gates.command)
        if not paths:
            return None

        missing = [p for p in paths if not (repo_root / p).exists()]
        if not missing:
            return None

        available_roots = discover_test_roots(repo_root)
        return format_smoke_gate_path_error(
            missing, repo_root, available_roots
        )

    @staticmethod
    def _detect_circular_dependencies(feature: Feature) -> Optional[List[str]]:
        """
        Detect circular dependencies in task graph.

        Parameters
        ----------
        feature : Feature
            Feature to check

        Returns
        -------
        Optional[List[str]]
            Circular dependency chain if found, None otherwise
        """
        # Build adjacency list
        graph = {t.id: t.dependencies for t in feature.tasks}
        visited = set()
        rec_stack = set()
        path = []

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            for dep_id in graph.get(task_id, []):
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep_id)
                    path.append(dep_id)  # Close the cycle
                    return True

            path.pop()
            rec_stack.remove(task_id)
            return False

        for task_id in graph:
            if task_id not in visited:
                if dfs(task_id):
                    return path

        return None

    @staticmethod
    def _validate_task_type_in_file(task_id: str, task_file: Path) -> Optional[str]:
        """
        Validate task_type in a task file's YAML frontmatter.

        Reads the frontmatter from the task file and checks that the task_type
        field (if present) is a valid TaskType enum value or alias.

        Parameters
        ----------
        task_id : str
            Task identifier (for error messages)
        task_file : Path
            Path to the task markdown file

        Returns
        -------
        Optional[str]
            Error message string if invalid, None if valid or no task_type set
        """
        try:
            content = task_file.read_text(encoding="utf-8")
        except OSError:
            return None  # Cannot read file - structural validator handles this

        # Must start with YAML frontmatter delimiter
        if not content.startswith("---"):
            return None

        # Find the closing --- delimiter
        try:
            end_idx = content.index("---", 3)
        except ValueError:
            return None  # No closing delimiter - not valid frontmatter

        frontmatter_str = content[3:end_idx]
        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError:
            return None  # YAML parse error - not our concern here

        if not isinstance(frontmatter, dict):
            return None

        task_type_str = frontmatter.get("task_type")
        if task_type_str is None:
            return None  # Missing task_type defaults to feature - acceptable

        # Check TaskType enum values first
        try:
            TaskType(task_type_str)
            return None  # Valid enum value
        except ValueError:
            pass

        # Check aliases
        if task_type_str in TASK_TYPE_ALIASES:
            return None  # Valid alias

        # Invalid value - build actionable error message
        valid_values = ", ".join(t.value for t in TaskType)
        valid_aliases = ", ".join(sorted(TASK_TYPE_ALIASES.keys()))
        return (
            f"Task {task_id} has invalid task_type: '{task_type_str}'. "
            f"Valid values: {valid_values}. "
            f"Valid aliases: {valid_aliases}. "
            f"Fix: Update task_type in {task_file}"
        )

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
        return errors

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

        Raises
        ------
        FeatureValidationError
            If feature data fails validation before writing

        Notes
        -----
        Uses feature.file_path if available, otherwise constructs path
        from feature.id.
        """
        repo_root = repo_root or Path.cwd()

        if feature.file_path:
            file_path = feature.file_path
        else:
            file_path = repo_root / FeatureLoader.FEATURES_DIR / f"{feature.id}.yaml"

        # Convert to dictionary
        data = FeatureLoader._feature_to_dict(feature)

        # Validate before writing
        validation_errors = FeatureLoader.validate_yaml(data)
        if validation_errors:
            # Log warnings for each error
            for error in validation_errors:
                logger.warning(f"Validation error in feature {feature.id}: {error}")

            # Raise exception to block write
            error_summary = "\n  - ".join(validation_errors)
            raise FeatureValidationError(
                f"Feature validation failed for {feature.id}:\n  - {error_summary}"
            )

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

        # Drop ``bootstrap_extras`` when empty. Auto-detection lives at
        # bootstrap time (see :func:`derive_bootstrap_extras`) so we
        # never persist an inferred value back to YAML — keeps the
        # operator-declared field unambiguous. (TASK-GK-BS-001)
        if not data.get("bootstrap_extras"):
            data.pop("bootstrap_extras", None)

        # Manually serialize execution (dataclass)
        data["execution"] = {
            "started_at": feature.execution.started_at,
            "completed_at": feature.execution.completed_at,
            "worktree_path": feature.execution.worktree_path,
            "total_turns": feature.execution.total_turns,
            "tasks_completed": feature.execution.tasks_completed,
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
