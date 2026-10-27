#!/usr/bin/env python3
"""
Generate Structured YAML Feature Files

This script generates structured YAML feature files for AutoBuild integration.
It can be executed directly via Bash from slash commands.

Usage:
    python3 generate_feature_yaml.py --name "Feature Name" --description "Description" \
        --task "ID:NAME:COMPLEXITY:DEPS" --task "ID:NAME:COMPLEXITY:DEPS" \
        [--base-path /path/to/project]

Example:
    python3 generate_feature_yaml.py \
        --name "Implement OAuth2" \
        --description "Add OAuth2 authentication" \
        --task "TASK-001:Create auth service:5:" \
        --task "TASK-002:Add OAuth provider:6:TASK-001" \
        --task "TASK-003:Add tests:3:TASK-001,TASK-002"
"""

import argparse
import glob as globmod
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import time

try:
    from installer.core.commands.lib.wave_overlap_detector import (
        compute_wave_overlaps,
        format_overlap_warning_summary,
        infer_task_files,
        serialize_overlapping_groups,
        warnings_to_dict,
    )
    WAVE_OVERLAP_DETECTOR_AVAILABLE = True
except ImportError:
    WAVE_OVERLAP_DETECTOR_AVAILABLE = False


@dataclass
class TaskSpec:
    """
    Specification for a single task within a feature.

    Aligned with FeatureTask Pydantic model in feature_loader.py.
    """
    id: str
    name: str
    complexity: int
    file_path: str = ""  # Path to task markdown file (required by FeatureLoader)
    dependencies: List[str] = field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = "pending"
    description: str = ""
    implementation_mode: Literal["direct", "task-work", "manual"] = "task-work"
    estimated_minutes: int = 60

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "file_path": self.file_path,  # Required by FeatureLoader
            "complexity": self.complexity,
            "dependencies": self.dependencies,
            "status": self.status,
            "description": self.description,
            "implementation_mode": self.implementation_mode,
            "estimated_minutes": self.estimated_minutes,
        }


@dataclass
class FeatureFile:
    """Structured feature file for AutoBuild consumption."""
    id: str
    name: str
    description: str
    tasks: List[TaskSpec] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    status: str = "planned"
    created: Optional[datetime] = None
    estimated_duration_minutes: int = 0
    recommended_parallel: int = 2

    def __post_init__(self):
        if self.created is None:
            self.created = datetime.now()

    @property
    def complexity(self) -> int:
        if not self.tasks:
            return 1
        scores = [t.complexity for t in self.tasks]
        avg = sum(scores) / len(scores)
        max_score = max(scores)
        task_penalty = min(len(self.tasks) * 0.2, 2)
        return min(10, max(1, int((avg * 0.6 + max_score * 0.4) + task_penalty)))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created": self.created.isoformat() if self.created else None,
            "status": self.status,
            "complexity": self.complexity,
            "estimated_tasks": len(self.tasks),
            "tasks": [t.to_dict() for t in self.tasks],
            "orchestration": {
                "parallel_groups": self.parallel_groups,
                "estimated_duration_minutes": self.estimated_duration_minutes,
                "recommended_parallel": self.recommended_parallel,
            },
        }


def generate_feature_id() -> str:
    """Generate a unique feature ID."""
    timestamp = str(time.time()).encode()
    hash_bytes = hashlib.sha256(timestamp).hexdigest()[:4].upper()
    return f"FEAT-{hash_bytes}"


def estimate_duration(complexity: int) -> int:
    """Estimate duration in minutes based on complexity."""
    base_minutes = 15
    scaling = 1.5
    return int(base_minutes * (scaling ** (complexity - 1)))


# Import shared slug utility - re-exported for backward compatibility
from installer.core.lib.slug_utils import slugify_task_name  # noqa: F401


def build_task_file_path(
    task_id: str,
    feature_slug: str,
    base_path: str = "tasks/backlog",
    task_name: str = ""
) -> str:
    """
    Build standardized task file path from components.

    Centralizes path construction logic for DRY compliance.

    Args:
        task_id: Task identifier (e.g., "TASK-001")
        feature_slug: Feature directory name (e.g., "oauth2"). Empty for flat structure.
        base_path: Base tasks directory (default: "tasks/backlog")
        task_name: Task name for filename suffix (e.g., "Create auth service").
                   If provided, generates filename like "TASK-001-create-auth-service.md"

    Returns:
        Relative path to task file

    Examples:
        >>> build_task_file_path("TASK-001", "oauth2", task_name="Create auth service")
        'tasks/backlog/oauth2/TASK-001-create-auth-service.md'
        >>> build_task_file_path("TASK-001", "oauth2")
        'tasks/backlog/oauth2/TASK-001.md'
        >>> build_task_file_path("TASK-001", "")
        'tasks/backlog/TASK-001.md'
    """
    # Build filename with optional name suffix
    if task_name:
        name_slug = slugify_task_name(task_name)
        filename = f"{task_id}-{name_slug}.md"
    else:
        filename = f"{task_id}.md"

    if feature_slug:
        # Guard: don't double the slug if base_path already ends with it
        stripped = base_path.rstrip('/')
        if stripped.endswith(f"/{feature_slug}") or stripped == feature_slug:
            return f"{base_path}/{filename}"
        return f"{base_path}/{feature_slug}/{filename}"
    else:
        return f"{base_path}/{filename}"


def discover_task_file(
    task_id: str,
    feature_slug: str,
    base_path: str = "tasks/backlog",
    project_root: str = ".",
) -> Optional[str]:
    """
    Discover an actual task file on disk by globbing for the task ID prefix.

    Instead of deriving the file path from the task name (which may not match
    what Claude actually created), this function finds the real file on disk.

    Args:
        task_id: Task identifier (e.g., "TASK-HLTH-003")
        feature_slug: Feature directory name (e.g., "fastapi-health-app")
        base_path: Base tasks directory (default: "tasks/backlog")
        project_root: Project root directory for resolving paths

    Returns:
        Relative path to the discovered file, or None if not found.

    Raises:
        ValueError: If multiple files match the same task ID prefix.

    Examples:
        >>> discover_task_file("TASK-001", "oauth2", project_root="/my/project")
        'tasks/backlog/oauth2/TASK-001-create-auth-service.md'
    """
    # Build the search directory
    if feature_slug:
        stripped = base_path.rstrip('/')
        if stripped.endswith(f"/{feature_slug}") or stripped == feature_slug:
            search_dir = Path(project_root) / base_path
        else:
            search_dir = Path(project_root) / base_path / feature_slug
    else:
        search_dir = Path(project_root) / base_path

    # Glob for files matching the task ID prefix
    pattern = str(search_dir / f"{task_id}*.md")
    matches = globmod.glob(pattern)

    if len(matches) == 1:
        # Return path relative to project root
        abs_path = Path(matches[0])
        try:
            return str(abs_path.relative_to(Path(project_root)))
        except ValueError:
            return str(abs_path)
    elif len(matches) > 1:
        match_list = ", ".join(str(Path(m).name) for m in matches)
        raise ValueError(
            f"Multiple files match {task_id} in {search_dir}: {match_list}"
        )
    else:
        return None


def parse_task_string(
    task_str: str,
    feature_slug: str = "",
    task_base_path: str = "tasks/backlog",
    acceptance_criteria_count: int = 0,
) -> TaskSpec:
    """
    Parse a task string in format: ID:NAME:COMPLEXITY:DEPS

    Args:
        task_str: Task string in format "ID:NAME:COMPLEXITY:DEPS"
        feature_slug: Feature directory name for file path derivation (optional)
        task_base_path: Base path for task files (default: "tasks/backlog")
        acceptance_criteria_count: Number of acceptance criteria (optional).
            Tasks with >=2 AC default to task-work regardless of complexity.

    Returns:
        TaskSpec with all fields populated, including file_path if feature_slug provided

    Examples:
        >>> parse_task_string("TASK-001:Auth service:5:", "oauth2")
        TaskSpec(id="TASK-001", name="Auth service", file_path="tasks/backlog/oauth2/TASK-001-auth-service.md", ...)
    """
    parts = task_str.split(":", 3)

    task_id = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""
    complexity = int(parts[2]) if len(parts) > 2 and parts[2] else 5
    deps_str = parts[3] if len(parts) > 3 else ""

    dependencies = [d.strip() for d in deps_str.split(",") if d.strip()]

    # Determine implementation mode based on complexity and acceptance criteria count
    if complexity <= 3 and acceptance_criteria_count < 2:
        mode = "direct"
    else:
        mode = "task-work"

    # Derive file_path from feature_slug if provided (includes task name in filename)
    file_path = ""
    if feature_slug:
        file_path = build_task_file_path(task_id, feature_slug, task_base_path, task_name=name)

    return TaskSpec(
        id=task_id,
        name=name,
        complexity=complexity,
        file_path=file_path,
        dependencies=dependencies,
        implementation_mode=mode,
        estimated_minutes=estimate_duration(complexity),
    )


def build_parallel_groups(tasks: List[TaskSpec]) -> List[List[str]]:
    """Build parallel execution groups from task dependencies."""
    if not tasks:
        return []

    # Build dependency map
    task_ids = {t.id for t in tasks}
    dep_map = {t.id: set(d for d in t.dependencies if d in task_ids) for t in tasks}

    groups = []
    scheduled = set()

    while len(scheduled) < len(tasks):
        # Find tasks with all dependencies satisfied
        available = []
        for t in tasks:
            if t.id not in scheduled:
                if all(d in scheduled for d in dep_map[t.id]):
                    available.append(t.id)

        if not available:
            # Cycle detected or error - add remaining tasks
            remaining = [t.id for t in tasks if t.id not in scheduled]
            groups.append(remaining)
            break

        groups.append(available)
        scheduled.update(available)

    return groups


def write_yaml(feature: FeatureFile, output_path: Path) -> None:
    """Write feature to YAML file."""
    try:
        import yaml

        output_path.parent.mkdir(parents=True, exist_ok=True)

        feature_dict = feature.to_dict()

        with open(output_path, "w") as f:
            yaml.dump(
                feature_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
    except ImportError:
        # Fallback to JSON if yaml not available
        import json

        output_path.parent.mkdir(parents=True, exist_ok=True)

        feature_dict = feature.to_dict()

        # Change extension to json
        json_path = output_path.with_suffix(".json")

        with open(json_path, "w") as f:
            json.dump(feature_dict, f, indent=2, default=str)

        print(f"Note: PyYAML not installed, wrote JSON to: {json_path}", file=sys.stderr)
        return


def main():
    parser = argparse.ArgumentParser(
        description="Generate structured YAML feature files for AutoBuild",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--name", "-n",
        required=False,
        help="Feature name (required)"
    )

    parser.add_argument(
        "--description", "-d",
        default="",
        help="Feature description"
    )

    parser.add_argument(
        "--task", "-t",
        action="append",
        dest="tasks",
        help="Task in format ID:NAME:COMPLEXITY:DEPS (can be repeated)"
    )

    parser.add_argument(
        "--tasks-json",
        help="JSON file or string containing tasks array"
    )

    parser.add_argument(
        "--base-path", "-p",
        default=".",
        help="Base path for project (default: current directory)"
    )

    parser.add_argument(
        "--feature-id",
        help="Override auto-generated feature ID"
    )

    parser.add_argument(
        "--output", "-o",
        help="Override output path (default: .guardkit/features/FEAT-XXX.yaml)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format instead of YAML"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )

    # New arguments for file path derivation (TASK-FP-002)
    parser.add_argument(
        "--feature-slug",
        default="",
        help="Feature slug for deriving task file paths (e.g., 'dark-mode', 'oauth2')"
    )

    parser.add_argument(
        "--task-base-path",
        default="tasks/backlog",
        help="Base path for task files (default: tasks/backlog)"
    )

    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discover actual task files on disk instead of deriving paths from names. "
             "Globs for {task_id}*.md in the feature directory."
    )

    parser.add_argument(
        "--auto-serialise-overlap",
        dest="auto_serialise_overlap",
        action="store_true",
        default=True,
        help="When tasks within a parallel-execution wave appear to edit overlapping "
             "files (inferred from task descriptions and ACs), split the offending "
             "wave into a sequential follow-on entry instead of warning. "
             "Default: ON (TASK-AB-WAVECTL01; was warn-only under TASK-FIX-A7B3). "
             "Use --no-auto-serialise-overlap to opt out. Plans where the "
             "detector infers no overlapping file sets are unchanged either way."
    )

    parser.add_argument(
        "--no-auto-serialise-overlap",
        dest="auto_serialise_overlap",
        action="store_false",
        help="Opt out of default-on overlap serialisation (TASK-AB-WAVECTL01): "
             "keep the original wave layout and emit the warn-only banner when "
             "overlapping file edits are detected within a wave."
    )

    args = parser.parse_args()

    if not args.name:
        print("Error: --name is required for feature generation", file=sys.stderr)
        sys.exit(2)

    # Parse tasks
    task_specs = []

    # Collect per-task prose for the wave-overlap detector (TASK-FIX-A7B3).
    # The detector's inference reads name + description + ACs to infer
    # source-file edit sets. The --task string form carries name only, so
    # those tasks will only contribute paths the user typed into the title.
    overlap_tasks: List[Dict[str, object]] = []

    if args.tasks:
        for task_str in args.tasks:
            spec = parse_task_string(
                task_str,
                feature_slug=args.feature_slug,
                task_base_path=args.task_base_path
            )
            task_specs.append(spec)
            overlap_tasks.append({
                "id": spec.id,
                "name": spec.name,
                "description": "",
                "acceptance_criteria": [],
            })

    if args.tasks_json:
        # Try to parse as JSON string or file
        try:
            if Path(args.tasks_json).exists():
                with open(args.tasks_json) as f:
                    tasks_data = json.load(f)
            else:
                tasks_data = json.loads(args.tasks_json)

            for t in tasks_data:
                task_id = t.get("id", t.get("task_id", ""))
                task_name = t.get("name", t.get("title", ""))
                complexity = t.get("complexity", 5)
                acceptance_criteria = t.get("acceptance_criteria", []) or []
                ac_count = len(acceptance_criteria)
                mode = "direct" if complexity <= 3 and ac_count < 2 else "task-work"
                overlap_tasks.append({
                    "id": task_id,
                    "name": task_name,
                    "description": t.get("description", ""),
                    "acceptance_criteria": acceptance_criteria,
                })
                # Derive file_path using centralized helper (includes task name in filename)
                file_path = ""
                if args.feature_slug:
                    file_path = build_task_file_path(
                        task_id, args.feature_slug, args.task_base_path,
                        task_name=task_name
                    )
                task_specs.append(TaskSpec(
                    id=task_id,
                    name=task_name,
                    complexity=complexity,
                    file_path=file_path,
                    dependencies=t.get("dependencies", []),
                    description=t.get("description", ""),
                    implementation_mode=mode,
                    estimated_minutes=estimate_duration(complexity),
                ))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error parsing tasks JSON: {e}", file=sys.stderr)
            sys.exit(1)

    if not task_specs:
        print("Error: At least one task required (--task or --tasks-json)", file=sys.stderr)
        sys.exit(1)

    # Validate --feature-slug is non-empty when tasks are provided (TASK-FIX-FP04)
    if not args.feature_slug:
        print(
            "Error: --feature-slug is required for correct task file_path generation.",
            file=sys.stderr,
        )
        print(
            "Example: --feature-slug 'my-feature'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Discover actual task files on disk if --discover is set (TASK-REV-8976)
    if args.discover and args.feature_slug:
        for task in task_specs:
            try:
                discovered = discover_task_file(
                    task.id,
                    args.feature_slug,
                    base_path=args.task_base_path,
                    project_root=args.base_path,
                )
                if discovered:
                    if task.file_path and task.file_path != discovered:
                        print(
                            f"   [discover] {task.id}: derived path differs from disk, using disk path",
                            file=sys.stderr,
                        )
                        print(
                            f"     derived: {task.file_path}",
                            file=sys.stderr,
                        )
                        print(
                            f"     actual:  {discovered}",
                            file=sys.stderr,
                        )
                    task.file_path = discovered
                else:
                    if not task.file_path:
                        # No file found and no derived path - derive one as fallback
                        task.file_path = build_task_file_path(
                            task.id, args.feature_slug, args.task_base_path,
                            task_name=task.name
                        )
                    print(
                        f"   [discover] {task.id}: no file found on disk, using derived path: {task.file_path}",
                        file=sys.stderr,
                    )
            except ValueError as e:
                print(f"Error discovering task file: {e}", file=sys.stderr)
                sys.exit(1)

    # Build parallel groups
    parallel_groups = build_parallel_groups(task_specs)

    # Wave-overlap detection (TASK-FIX-A7B3) — imperative producer callsite.
    # Runs after parallel_groups is computed so it sees the actual wave layout
    # the YAML will carry. Default behaviour is warn-only at the end of stdout
    # (alongside the AC linter / R2 / R3 banners). With
    # --auto-serialise-overlap, the planner rewrites the offending wave into
    # a sequential follow-on entry and notes the split.
    overlap_warnings: List = []
    auto_serialise_notes: List[str] = []
    if WAVE_OVERLAP_DETECTOR_AVAILABLE:
        task_files = {
            t["id"]: infer_task_files(t)
            for t in overlap_tasks
            if t.get("id")
        }
        overlap_warnings = compute_wave_overlaps(parallel_groups, task_files)
        if overlap_warnings and args.auto_serialise_overlap:
            parallel_groups, auto_serialise_notes = serialize_overlapping_groups(
                parallel_groups, overlap_warnings
            )

    # Calculate totals
    total_minutes = sum(t.estimated_minutes for t in task_specs)
    max_parallel = max(len(g) for g in parallel_groups) if parallel_groups else 1
    recommended_parallel = min(max_parallel, 4)

    # Create feature
    feature_id = args.feature_id or generate_feature_id()

    feature = FeatureFile(
        id=feature_id,
        name=args.name,
        description=args.description,
        tasks=task_specs,
        parallel_groups=parallel_groups,
        estimated_duration_minutes=total_minutes,
        recommended_parallel=recommended_parallel,
    )

    # Determine output path
    base_path = Path(args.base_path)

    if args.output:
        output_path = Path(args.output)
    else:
        ext = ".json" if args.json else ".yaml"
        output_path = base_path / ".guardkit" / "features" / f"{feature_id}{ext}"

    feature_dict = feature.to_dict()

    # Write file
    if args.json:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(feature_dict, f, indent=2, default=str)
    else:
        write_yaml(feature, output_path)

    # Output summary
    if not args.quiet:
        print(f"✅ Feature {feature_id} created")
        print(f"📋 Tasks: {len(task_specs)}")
        for i, t in enumerate(task_specs, 1):
            deps_str = f" (deps: {', '.join(t.dependencies)})" if t.dependencies else ""
            print(f"   {t.id}: {t.name} (complexity: {t.complexity}){deps_str}")
        print()
        print(f"🔀 Parallel execution groups: {len(parallel_groups)} waves")
        for i, group in enumerate(parallel_groups, 1):
            print(f"   Wave {i}: [{', '.join(group)}]")
        print()
        print(f"📁 Feature file: {output_path}")
        print(f"⚡ AutoBuild ready: /feature-build {feature_id}")
    else:
        # Quiet mode - just output the feature ID and path
        print(f"{feature_id}:{output_path}")

    # Wave-overlap warning banner — imperative callsite for TASK-FIX-A7B3.
    # Always fires when overlaps were detected above; mode (warn vs auto-
    # serialise) is reflected in the banner copy. Auto-serialise also prints
    # the per-wave split notes so the user can see which tasks moved.
    if WAVE_OVERLAP_DETECTOR_AVAILABLE and not args.quiet and overlap_warnings:
        print()
        print(format_overlap_warning_summary(
            overlap_warnings,
            auto_serialise=args.auto_serialise_overlap,
        ))
        if auto_serialise_notes:
            print()
            for note in auto_serialise_notes:
                print(f"   {note}")


if __name__ == "__main__":
    main()
