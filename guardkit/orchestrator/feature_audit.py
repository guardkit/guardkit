from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FeatureAuditRow:
    """Audit information for a single feature YAML file.

    Attributes:
        feature_id: Identifier of the feature (e.g., ``FEAT-FAUD``).
        declared_status: The ``status`` value declared in the YAML.
        inferred_status: Status inferred from task completion.
        tasks_total: Number of tasks defined for the feature.
        tasks_completed: Number of tasks that have a completed markdown file.
        tasks_pending: Number of tasks that are not yet completed.
        is_stale: ``True`` when ``declared_status`` differs from ``inferred_status``.
    """

    feature_id: str
    declared_status: str
    inferred_status: str
    tasks_total: int
    tasks_completed: int
    tasks_pending: int
    is_stale: bool


def _load_feature_yaml(yaml_path: Path) -> dict | None:
    """Load a feature YAML file safely.

    Returns ``None`` if the file cannot be parsed or does not contain a mapping.
    """
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.debug("YAML %s did not contain a dict; skipping", yaml_path)
            return None
        return data
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse YAML %s: %s", yaml_path, exc)
        return None
    except Exception as exc:  # pragma: no cover – unexpected I/O errors
        logger.error("Error reading %s: %s", yaml_path, exc)
        return None


def _task_identifier(task: object) -> str:
    """Return the task-id string for a feature's task entry.

    Feature YAMLs declare ``tasks`` as a list of mappings
    (``{"id": "TASK-XXX-YYYY", "name": ..., "file_path": ...}``). Older or
    hand-written forms may use a bare id string. Extract the id either way,
    returning ``""`` when no id is present.
    """
    if isinstance(task, dict):
        return str(task.get("id") or "")
    return str(task or "")


def _task_is_completed(task: object, completed_dir: Path) -> bool:
    """True when a markdown file for ``task`` exists under ``completed_dir``."""
    task_id = _task_identifier(task)
    if not task_id:
        return False
    return any(completed_dir.rglob(f"*{task_id}*.md"))


def _infer_from_counts(completed: int, total: int) -> str:
    """Map (completed, total) task counts to a feature status string."""
    if total == 0:
        return "planned"
    if completed == total:
        return "completed"
    if completed == 0:
        return "planned"
    return "in_progress"


def infer_status_for_feature(feature_dict: dict, repo_root: Path) -> str:
    """Infer the overall status of a feature based on its tasks.

    ``feature_dict["tasks"]`` is a list of task mappings (each carrying an
    ``id`` key); a task counts as completed when a markdown file containing its
    id exists anywhere under ``repo_root / "tasks" / "completed"``.

    Returns one of ``"completed"``, ``"planned"`` or ``"in_progress"``.
    """
    tasks = feature_dict.get("tasks", [])
    if not isinstance(tasks, (list, tuple)):
        tasks = []
    completed_dir = repo_root / "tasks" / "completed"
    completed = sum(1 for task in tasks if _task_is_completed(task, completed_dir))
    return _infer_from_counts(completed, len(tasks))


def audit_features(repo_root: Path) -> List[FeatureAuditRow]:
    """Audit all feature YAML files under ``repo_root/.guardkit/features``.

    Returns a list of :class:`FeatureAuditRow` objects. Files that cannot be parsed
    or lack a ``tasks`` key are ignored.
    """
    feature_dir = repo_root / ".guardkit" / "features"
    rows: List[FeatureAuditRow] = []
    for yaml_path in feature_dir.glob("*.yaml"):
        feature_dict = _load_feature_yaml(yaml_path)
        if feature_dict is None:
            continue
        feature_id = feature_dict.get("id", yaml_path.stem)
        declared_status = str(feature_dict.get("status", "unknown"))
        tasks = feature_dict.get("tasks", [])
        if not isinstance(tasks, (list, tuple)):
            tasks = []
        total = len(tasks)
        completed_dir = repo_root / "tasks" / "completed"
        completed = sum(1 for task in tasks if _task_is_completed(task, completed_dir))
        inferred = _infer_from_counts(completed, total)
        pending = total - completed
        is_stale = declared_status != inferred
        rows.append(
            FeatureAuditRow(
                feature_id=feature_id,
                declared_status=declared_status,
                inferred_status=inferred,
                tasks_total=total,
                tasks_completed=completed,
                tasks_pending=pending,
                is_stale=is_stale,
            )
        )
    return rows
