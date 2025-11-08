---
id: TASK-052
title: Create migration script for existing tasks (solo use)
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: medium
tags: [infrastructure, hash-ids, migration, personal]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create migration script for existing tasks (solo use)

## Description

Create a simplified migration script that converts YOUR existing tasks from old ID formats to new hash-based IDs while preserving all data and relationships.

**Scope**: Personal use only - handles specific formats found in this repository:
- Simple sequential: TASK-004, TASK-015, TASK-042
- Letter suffixes: TASK-004A, TASK-001B
- Hierarchical: TASK-030B-1, TASK-030E-1
- Namespace: TASK-DOCS-001

**Not building**: Generic user-facing migration tool, extensive documentation, multi-project support

## Acceptance Criteria

- [ ] Migrate all YOUR tasks in all directories (backlog, in_progress, in_review, blocked, completed)
- [ ] Generate hash-based IDs for all tasks
- [ ] Preserve old IDs in `legacy_id` field
- [ ] Update cross-references within task bodies
- [ ] Create migration log (simple text file)
- [ ] Generate rollback script (simple bash)
- [ ] Dry-run mode for validation
- [ ] Zero data loss (all fields preserved)
- [ ] ~30-50 tasks total (your current count)

## Test Requirements

- [ ] Dry-run test on actual task directories (no changes)
- [ ] Backup verification (all files backed up)
- [ ] Rollback test (restore from backup)
- [ ] Manual verification of 5-10 migrated tasks
- [ ] Cross-reference check (grep for old IDs after migration)
- [ ] Basic Python script tests (runs without errors)

## Implementation Notes

### File Location
Create new file: `scripts/migrate-my-tasks.py` (single self-contained script)

**Why not installer/**: This is personal use only, not part of the distributed tool

### Migration Process (Simplified)

**Phase 1: Backup**
```bash
cp -r tasks/ .claude/state/backup/tasks-pre-hash-migration/
```

**Phase 2: Scan & Map**
1. Find all `*.md` files in `tasks/`
2. Extract current ID from frontmatter
3. Generate hash ID (no prefix inference - keep simple)
4. Create mapping dict: `{"TASK-042": "TASK-a3f8", ...}`

**Phase 3: Update Files**
For each task file:
1. Update frontmatter: `id: TASK-042` → `id: TASK-a3f8`, add `legacy_id: TASK-042`
2. Update cross-references in body (simple regex replace)
3. Rename file: `TASK-042-title.md` → `TASK-a3f8-title.md`

**Phase 4: Generate Rollback**
Create simple script:
```bash
#!/bin/bash
rm -rf tasks/
cp -r .claude/state/backup/tasks-pre-hash-migration/ tasks/
```

**Phase 5: Report**
Print simple summary:
- Tasks migrated: 42
- Files renamed: 42
- Cross-references updated: 15
- Rollback: `bash .claude/state/rollback-migration.sh`

### Key Functions (Simple)

```python
#!/usr/bin/env python3
"""
Migrate YOUR tasks to hash-based IDs.
Personal use only - handles specific formats in this repo.

Usage:
  python3 scripts/migrate-my-tasks.py --dry-run  # Preview changes
  python3 scripts/migrate-my-tasks.py --execute  # Actually migrate
"""

import os
import re
import yaml
from pathlib import Path
from installer.global.lib.id_generator import generate_task_id

def backup_tasks():
    """Create backup before migration."""
    # cp -r tasks/ .claude/state/backup/tasks-pre-migration/

def scan_task_files() -> dict:
    """
    Scan all .md files in tasks/ and extract IDs.
    Returns: {old_id: file_path}
    """
    task_map = {}
    for md_file in Path("tasks").rglob("*.md"):
        # Read frontmatter, extract id
        old_id = extract_id_from_frontmatter(md_file)
        if old_id and old_id.startswith("TASK-"):
            task_map[old_id] = md_file
    return task_map

def generate_id_mapping(old_ids: list) -> dict:
    """Generate new hash IDs for all old IDs."""
    mapping = {}
    for old_id in old_ids:
        new_id = generate_task_id()  # No prefix, keep simple
        mapping[old_id] = new_id
    return mapping

def migrate_file(file_path: Path, old_id: str, new_id: str, id_mapping: dict):
    """Migrate single file: update frontmatter, body, rename."""
    content = file_path.read_text()

    # Update frontmatter
    content = update_frontmatter(content, old_id, new_id)

    # Update cross-references in body
    for old, new in id_mapping.items():
        content = content.replace(old, new)

    # Write back
    file_path.write_text(content)

    # Rename file
    new_filename = file_path.name.replace(old_id, new_id)
    file_path.rename(file_path.parent / new_filename)

def create_rollback_script(backup_path: Path):
    """Generate simple rollback script."""
    script = f"""#!/bin/bash
# Rollback hash ID migration
set -e
echo "Rolling back migration..."
rm -rf tasks/
cp -r {backup_path} tasks/
echo "Rollback complete. Please verify manually."
"""
    Path(".claude/state/rollback-migration.sh").write_text(script)
    os.chmod(".claude/state/rollback-migration.sh", 0o755)
```

### No Prefix Inference (Keep It Simple)

**Decision**: Don't infer prefixes during migration. Keep all migrated tasks without prefixes.

**Rationale**:
- You're the only user - you know your own tasks
- Can manually add prefixes later if needed
- Simpler code, fewer edge cases
- Avoid guessing wrong prefix

**Examples**:
```
TASK-042       → TASK-a3f8     (no prefix)
TASK-DOCS-001  → TASK-b2c4     (no prefix, despite "DOCS")
TASK-030B-1    → TASK-f1a3     (no prefix, despite "030B")
```

If you want prefixes after migration, manually edit specific tasks or create new ones with prefixes.

### Migration Report (Simplified)

```
================================================================================
TASK ID MIGRATION - YOUR TASKS
================================================================================
Date: 2025-01-08T10:00:00Z
Duration: 15 seconds

SUMMARY
  Tasks found: 42
  Tasks migrated: 42
  Files renamed: 42
  Cross-references updated: 8
  Errors: 0

SAMPLE MIGRATIONS
  TASK-003 → TASK-a3f8
  TASK-004 → TASK-b2c4
  TASK-030B-1 → TASK-f1a3
  TASK-DOCS-001 → TASK-c5e7

BACKUP
  Location: .claude/state/backup/tasks-pre-hash-migration/

ROLLBACK
  To undo: bash .claude/state/rollback-migration.sh

NEXT STEPS
  1. Verify a few migrated tasks look correct
  2. Run: grep -r "TASK-[0-9]" tasks/  # Should find none
  3. If all good, delete backup after 30 days
  4. If issues, run rollback script immediately
================================================================================
```

### Rollback Script (Simple)

```bash
#!/bin/bash
# Rollback hash ID migration
# Run this if migration goes wrong

set -e

echo "🔄 Rolling back task ID migration..."

# Delete new hash-based tasks
rm -rf tasks/

# Restore from backup
cp -r .claude/state/backup/tasks-pre-hash-migration/ tasks/

echo "✅ Rollback complete"
echo "📋 Verify: ls tasks/backlog/ | head -5"
```

**That's it!** No per-file restoration, no complex logic. Just nuke and restore from backup.

### Dry-Run Mode (Preview Changes)

```bash
python3 scripts/migrate-my-tasks.py --dry-run

# Output:
🔍 DRY RUN - No changes will be made

MIGRATION PREVIEW
  Found: 42 tasks
  Will migrate: 42 tasks
  Will rename: 42 files
  Cross-references: ~8 instances

SAMPLE MIGRATIONS
  TASK-003 → TASK-a3f8
  TASK-004 → TASK-b2c4
  TASK-030B-1 → TASK-f1a3
  TASK-DOCS-001 → TASK-c5e7

To proceed:
  python3 scripts/migrate-my-tasks.py --execute
```

## Dependencies

- TASK-046: Hash ID generator (must be completed)
- TASK-047: ID validation (must be completed)
- TASK-051: Updated frontmatter schema (must be completed)

## Related Tasks

- TASK-053: Update documentation
- TASK-055: Integration testing

## Test Execution Log

[Automatically populated by /task-work]
