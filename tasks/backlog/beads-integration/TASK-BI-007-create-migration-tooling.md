---
id: TASK-BI-007
title: Create migration tooling for existing tasks
status: backlog
priority: 2
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 4
conductor_workspace: wave4-1
complexity: 5
estimated_hours: 2-3
tags:
  - migration
  - tooling
  - phase-4
blocking_ids:
  - TASK-BI-003
  - TASK-BI-006
---

# Create Migration Tooling for Existing Tasks

## Objective

Create a migration script that allows users to migrate existing markdown tasks to Beads, and vice versa, with full data preservation.

## Context

Users with existing GuardKit projects using markdown tasks need a smooth path to Beads. The migration should preserve all task data including dependencies, metadata, and history.

## Implementation Details

### Location

Create: `scripts/migrate-tasks.py`

### Migration Script

```python
#!/usr/bin/env python3
"""
Migrate tasks between GuardKit backends.

Usage:
  python3 scripts/migrate-tasks.py --to beads [--dry-run]
  python3 scripts/migrate-tasks.py --to markdown [--dry-run]
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "installer/core"))

from backends import MarkdownBackend, BeadsBackend, Task
from backends.base import TaskStatus

class TaskMigrator:
    """Migrate tasks between backends."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.markdown = MarkdownBackend(self.project_root)
        self.beads = BeadsBackend(self.project_root)
        self.id_mapping: Dict[str, str] = {}  # old_id -> new_id

    def migrate_to_beads(self, dry_run: bool = False) -> Dict[str, any]:
        """Migrate all markdown tasks to Beads."""

        # Check Beads availability
        if not self.beads.is_available():
            return {
                "success": False,
                "error": "Beads (bd) not installed. Install with: brew install bd"
            }

        # Collect all markdown tasks
        tasks = self._collect_markdown_tasks()

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "task_count": len(tasks),
                "tasks": [{"id": t.id, "title": t.title} for t in tasks]
            }

        # Initialize Beads if needed
        self.beads.initialize()

        # Migrate tasks (parents first)
        migrated = []
        errors = []

        # Sort by parent_id (None first) to ensure parents exist before children
        sorted_tasks = sorted(tasks, key=lambda t: (t.parent_id or "", t.id))

        for task in sorted_tasks:
            try:
                new_task = self._migrate_task_to_beads(task)
                self.id_mapping[task.id] = new_task.id
                migrated.append({
                    "old_id": task.id,
                    "new_id": new_task.id,
                    "title": task.title
                })
            except Exception as e:
                errors.append({
                    "id": task.id,
                    "error": str(e)
                })

        # Re-establish dependencies with new IDs
        self._migrate_dependencies()

        # Save ID mapping for reference
        self._save_id_mapping()

        return {
            "success": len(errors) == 0,
            "migrated": len(migrated),
            "errors": errors,
            "id_mapping": self.id_mapping
        }

    def migrate_to_markdown(self, dry_run: bool = False) -> Dict[str, any]:
        """Migrate Beads tasks back to markdown."""

        if not self.beads.is_available():
            return {"success": False, "error": "Beads not available"}

        # Get all Beads tasks with guardkit label
        tasks = self.beads.list_ready()  # This filters by guardkit label

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "task_count": len(tasks)
            }

        # Initialize markdown backend
        self.markdown.initialize()

        migrated = []
        for task in tasks:
            new_task = self.markdown.create(task)
            self.id_mapping[task.id] = new_task.id
            migrated.append({
                "old_id": task.id,
                "new_id": new_task.id
            })

        return {
            "success": True,
            "migrated": len(migrated)
        }

    def _collect_markdown_tasks(self) -> List[Task]:
        """Collect all tasks from markdown backend."""
        tasks = []
        tasks_dir = self.project_root / "tasks"

        for state_dir in self.markdown.STATE_DIRS:
            state_path = tasks_dir / state_dir
            if not state_path.exists():
                continue

            for task_file in state_path.rglob("*.md"):
                if task_file.name.startswith("README") or task_file.name.startswith("IMPLEMENTATION"):
                    continue

                task = self.markdown.get(task_file.stem)
                if task:
                    tasks.append(task)

        return tasks

    def _migrate_task_to_beads(self, task: Task) -> Task:
        """Migrate single task to Beads."""
        # Clear ID so Beads assigns new one
        old_id = task.id
        task.id = ""

        # Update parent_id if already migrated
        if task.parent_id and task.parent_id in self.id_mapping:
            task.parent_id = self.id_mapping[task.parent_id]

        # Create in Beads
        new_task = self.beads.create(task)

        # Store legacy ID in notes
        # (Already handled by _update_notes with spec_ref pattern)

        return new_task

    def _migrate_dependencies(self):
        """Re-establish dependencies using new IDs."""
        for old_id, new_id in self.id_mapping.items():
            task = self.beads.get(new_id)
            if task and task.blocking_ids:
                for old_blocker_id in task.blocking_ids:
                    new_blocker_id = self.id_mapping.get(old_blocker_id)
                    if new_blocker_id:
                        self.beads.add_dependency(new_id, new_blocker_id)

    def _save_id_mapping(self):
        """Save ID mapping for future reference."""
        import json
        mapping_file = self.project_root / ".guardkit" / "migration-mapping.json"
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        mapping_file.write_text(json.dumps(self.id_mapping, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Migrate GuardKit tasks between backends")
    parser.add_argument("--to", required=True, choices=["beads", "markdown"],
                       help="Target backend")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview migration without making changes")
    parser.add_argument("--project", type=Path, default=Path.cwd(),
                       help="Project root directory")

    args = parser.parse_args()

    migrator = TaskMigrator(args.project)

    if args.to == "beads":
        result = migrator.migrate_to_beads(dry_run=args.dry_run)
    else:
        result = migrator.migrate_to_markdown(dry_run=args.dry_run)

    if result.get("dry_run"):
        print(f"DRY RUN: Would migrate {result['task_count']} tasks")
        return

    if result["success"]:
        print(f"✅ Migrated {result['migrated']} tasks")
        if result.get("id_mapping"):
            print(f"   ID mapping saved to .guardkit/migration-mapping.json")
    else:
        print(f"❌ Migration failed: {result.get('error')}")
        for err in result.get("errors", []):
            print(f"   {err['id']}: {err['error']}")


if __name__ == "__main__":
    main()
```

### Rollback Support

```python
def rollback_migration(self):
    """Rollback a previous migration using saved mapping."""
    import json

    mapping_file = self.project_root / ".guardkit" / "migration-mapping.json"
    if not mapping_file.exists():
        return {"success": False, "error": "No migration mapping found"}

    mapping = json.loads(mapping_file.read_text())

    # Original tasks still exist in tasks/ directory
    # Just update config to use markdown backend
    from lib.config import set_backend
    set_backend("markdown", self.project_root)

    return {"success": True, "message": "Switched back to markdown backend"}
```

## Acceptance Criteria

- [ ] `--dry-run` previews migration without changes
- [ ] Markdown → Beads migration preserves all fields
- [ ] Dependencies migrated with new IDs
- [ ] ID mapping saved for reference
- [ ] Rollback support via config switch
- [ ] Clear error messages for failures
- [ ] Integration test for full migration cycle

## Testing

```python
# tests/scripts/test_migration.py
def test_dry_run_shows_task_count(temp_markdown_project):
    migrator = TaskMigrator(temp_markdown_project)
    result = migrator.migrate_to_beads(dry_run=True)
    assert result["dry_run"] == True
    assert result["task_count"] >= 0

@pytest.mark.skipif(not BeadsBackend().is_available(), reason="bd not installed")
def test_full_migration(temp_markdown_project):
    # Create some test tasks
    backend = MarkdownBackend(temp_markdown_project)
    backend.initialize()
    backend.create(Task(id="", title="Test 1"))
    backend.create(Task(id="", title="Test 2"))

    # Migrate
    migrator = TaskMigrator(temp_markdown_project)
    result = migrator.migrate_to_beads()

    assert result["success"]
    assert result["migrated"] == 2
```

## Dependencies

- TASK-BI-003 (BeadsBackend)
- TASK-BI-006 (CLI updates)

## Notes

- Original markdown files preserved (not deleted)
- User must manually delete after verification
- Consider adding `--delete-source` flag for cleanup
