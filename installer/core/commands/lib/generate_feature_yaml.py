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
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import time


@dataclass
class TaskSpec:
    """Specification for a single task within a feature."""
    id: str
    name: str
    complexity: int
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    description: str = ""
    implementation_mode: str = "task-work"
    estimated_minutes: int = 60

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
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


def parse_task_string(task_str: str) -> TaskSpec:
    """
    Parse a task string in format: ID:NAME:COMPLEXITY:DEPS

    DEPS is comma-separated list of dependency IDs (optional)
    """
    parts = task_str.split(":", 3)

    task_id = parts[0] if len(parts) > 0 else ""
    name = parts[1] if len(parts) > 1 else ""
    complexity = int(parts[2]) if len(parts) > 2 and parts[2] else 5
    deps_str = parts[3] if len(parts) > 3 else ""

    dependencies = [d.strip() for d in deps_str.split(",") if d.strip()]

    # Determine implementation mode based on complexity
    if complexity <= 3:
        mode = "direct"
    else:
        mode = "task-work"

    return TaskSpec(
        id=task_id,
        name=name,
        complexity=complexity,
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
        required=True,
        help="Feature name"
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

    args = parser.parse_args()

    # Parse tasks
    task_specs = []

    if args.tasks:
        for task_str in args.tasks:
            task_specs.append(parse_task_string(task_str))

    if args.tasks_json:
        # Try to parse as JSON string or file
        try:
            if Path(args.tasks_json).exists():
                with open(args.tasks_json) as f:
                    tasks_data = json.load(f)
            else:
                tasks_data = json.loads(args.tasks_json)

            for t in tasks_data:
                complexity = t.get("complexity", 5)
                mode = "direct" if complexity <= 3 else "task-work"
                task_specs.append(TaskSpec(
                    id=t.get("id", t.get("task_id", "")),
                    name=t.get("name", t.get("title", "")),
                    complexity=complexity,
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

    # Build parallel groups
    parallel_groups = build_parallel_groups(task_specs)

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

    # Write file
    if args.json:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(feature.to_dict(), f, indent=2, default=str)
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


if __name__ == "__main__":
    main()
