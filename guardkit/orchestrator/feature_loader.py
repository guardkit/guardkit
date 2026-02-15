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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, ValidationError
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Schema Documentation (for error messages)
# ============================================================================

TASK_SCHEMA = """
Task Schema:
  id: str (required)        # e.g., "TASK-AUTH-001"
  file_path: str (required) # Path to task markdown file
  name: str                 # Human-readable name (defaults to id)
  complexity: int           # 1-10 (default: 5)
  dependencies: list        # Task IDs this depends on
  status: str               # pending/in_progress/completed/failed/skipped
  implementation_mode: str  # task-work/direct/manual
  estimated_minutes: int    # Default: 30
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

        # Check prefix match (e.g., TASK-AUTH-001 matches TASK-AUTH-002)
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
        Task identifier (e.g., "TASK-AUTH-001")
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
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str = ""
    file_path: Path = Path("")
    complexity: int = Field(default=5, ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = "pending"
    implementation_mode: Literal["direct", "task-work", "manual"] = "task-work"
    estimated_minutes: int = 30
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
    file_path: Optional[Path] = None


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

    @staticmethod
    def load_feature(
        feature_id: str,
        repo_root: Optional[Path] = None,
        features_dir: Optional[Path] = None,
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
            feature = FeatureLoader._parse_feature(data)
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
    def _parse_feature(data: Dict[str, Any]) -> Feature:
        """
        Parse feature dictionary into Feature dataclass.

        Parameters
        ----------
        data : Dict[str, Any]
            Raw YAML data

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

        return errors

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
        - Status is 'in_progress' or 'paused'
        - Has any tasks in 'in_progress' status
        - Has executed at least one wave but not all tasks are done

        Parameters
        ----------
        feature : Feature
            Feature to check

        Returns
        -------
        bool
            True if feature execution is incomplete
        """
        # Check status
        if feature.status in ("in_progress", "paused"):
            return True

        # Check for in-progress tasks
        for task in feature.tasks:
            if task.status == "in_progress":
                return True

        # Check if we have partial completion
        if feature.execution.started_at:
            completed_count = sum(
                1 for t in feature.tasks if t.status == "completed"
            )
            failed_count = sum(
                1 for t in feature.tasks if t.status == "failed"
            )

            # If we started but haven't finished all tasks
            if 0 < (completed_count + failed_count) < len(feature.tasks):
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
    # Exceptions
    "FeatureNotFoundError",
    "FeatureParseError",
    "FeatureValidationError",
    # Schema constants (for external use)
    "TASK_SCHEMA",
    "FEATURE_SCHEMA",
    "ORCHESTRATION_SCHEMA",
]
