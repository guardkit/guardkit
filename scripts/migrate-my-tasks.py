#!/usr/bin/env python3
"""
Migrate YOUR tasks to hash-based IDs.
Personal use only - handles specific formats in this repo.

Usage:
  python3 scripts/migrate-my-tasks.py --dry-run   # Preview changes
  python3 scripts/migrate-my-tasks.py --execute   # Actually migrate
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add installer/global/lib to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "lib"))

from id_generator import generate_task_id, validate_task_id


# Task directories to process
TASK_DIRECTORIES = [
    'tasks/backlog',
    'tasks/in_progress',
    'tasks/in_review',
    'tasks/blocked',
    'tasks/completed'
]

# Backup and state directories
BACKUP_BASE = '.claude/state/backup'
STATE_DIR = '.claude/state'


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.tasks_found = 0
        self.tasks_migrated = 0
        self.files_renamed = 0
        self.cross_references_updated = 0
        self.errors: List[str] = []
        self.migrations: List[Tuple[str, str]] = []  # (old_id, new_id)
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None

    def add_migration(self, old_id: str, new_id: str):
        """Record a successful migration."""
        self.migrations.append((old_id, new_id))
        self.tasks_migrated += 1

    def add_error(self, error: str):
        """Record an error."""
        self.errors.append(error)

    def finish(self):
        """Mark migration as finished."""
        self.end_time = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float:
        """Calculate migration duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


def extract_id_from_frontmatter(file_path: Path) -> Optional[str]:
    """
    Extract task ID from frontmatter.

    Args:
        file_path: Path to markdown file

    Returns:
        Task ID or None if not found
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Match frontmatter block
        frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)

        # Extract id field
        id_match = re.search(r'^id:\s*(.+)$', frontmatter, re.MULTILINE)
        if id_match:
            return id_match.group(1).strip()

        return None
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None


def scan_task_files() -> Dict[str, Path]:
    """
    Scan all .md files in tasks/ and extract IDs.

    Returns:
        Dictionary mapping old_id -> file_path
    """
    task_map = {}

    for dir_name in TASK_DIRECTORIES:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            continue

        for md_file in dir_path.glob('*.md'):
            old_id = extract_id_from_frontmatter(md_file)
            if old_id and old_id.startswith('TASK-'):
                # Check if this is already a hash-based ID
                if validate_task_id(old_id):
                    # Already migrated - skip
                    continue
                task_map[old_id] = md_file

    return task_map


def generate_id_mapping(old_ids: List[str]) -> Dict[str, str]:
    """
    Generate new hash IDs for all old IDs.

    Args:
        old_ids: List of old task IDs

    Returns:
        Dictionary mapping old_id -> new_id
    """
    mapping = {}
    existing_ids: Set[str] = set()

    for old_id in sorted(old_ids):  # Sort for deterministic generation
        # Generate new hash-based ID
        new_id = generate_task_id(existing_ids=existing_ids)
        mapping[old_id] = new_id
        existing_ids.add(new_id)

    return mapping


def update_frontmatter(content: str, old_id: str, new_id: str) -> str:
    """
    Update frontmatter with new ID and add legacy_id field.

    Args:
        content: File content
        old_id: Old task ID
        new_id: New task ID

    Returns:
        Updated content
    """
    # Find frontmatter block
    frontmatter_match = re.search(r'^(---\n)(.*?)(\n---)', content, re.DOTALL | re.MULTILINE)
    if not frontmatter_match:
        return content

    start_marker = frontmatter_match.group(1)
    frontmatter = frontmatter_match.group(2)
    end_marker = frontmatter_match.group(3)

    # Update id field
    frontmatter = re.sub(
        r'^id:\s*.+$',
        f'id: {new_id}',
        frontmatter,
        flags=re.MULTILINE
    )

    # Add legacy_id field if not present
    if 'legacy_id:' not in frontmatter:
        # Insert after id field
        frontmatter = re.sub(
            r'^(id:\s*.+)$',
            f'\\1\nlegacy_id: {old_id}',
            frontmatter,
            flags=re.MULTILINE
        )

    # Reconstruct content
    new_frontmatter_block = start_marker + frontmatter + end_marker
    return content.replace(
        frontmatter_match.group(0),
        new_frontmatter_block
    )


def update_cross_references(content: str, id_mapping: Dict[str, str]) -> Tuple[str, int]:
    """
    Update cross-references to other tasks in content.

    Args:
        content: File content
        id_mapping: Mapping of old_id -> new_id

    Returns:
        Tuple of (updated content, number of replacements)
    """
    replacements = 0

    for old_id, new_id in id_mapping.items():
        # Count occurrences before replacement
        count = content.count(old_id)
        if count > 0:
            # Replace all occurrences
            content = content.replace(old_id, new_id)
            replacements += count

    return content, replacements


def migrate_file(
    file_path: Path,
    old_id: str,
    new_id: str,
    id_mapping: Dict[str, str],
    dry_run: bool = False
) -> Tuple[bool, int]:
    """
    Migrate single file: update frontmatter, body, rename.

    Args:
        file_path: Path to task file
        old_id: Old task ID
        new_id: New task ID
        id_mapping: Full mapping for cross-reference updates
        dry_run: If True, don't make changes

    Returns:
        Tuple of (success, cross_references_updated)
    """
    try:
        # Read content
        content = file_path.read_text(encoding='utf-8')

        # Split into frontmatter and body
        frontmatter_match = re.search(r'^(---\n.*?\n---\n)(.*)', content, re.DOTALL | re.MULTILINE)
        if frontmatter_match:
            frontmatter = frontmatter_match.group(1)
            body = frontmatter_match.group(2)

            # Update frontmatter only
            frontmatter = update_frontmatter(frontmatter, old_id, new_id)

            # Update cross-references only in body (not frontmatter)
            body, xref_count = update_cross_references(body, id_mapping)

            # Recombine
            content = frontmatter + body
        else:
            # No frontmatter found, update entire content
            content = update_frontmatter(content, old_id, new_id)
            content, xref_count = update_cross_references(content, id_mapping)

        if not dry_run:
            # Write back
            file_path.write_text(content, encoding='utf-8')

            # Rename file
            new_filename = file_path.name.replace(old_id, new_id, 1)
            new_path = file_path.parent / new_filename
            file_path.rename(new_path)

        return True, xref_count

    except Exception as e:
        print(f"Error migrating {file_path}: {e}", file=sys.stderr)
        return False, 0


def backup_tasks(stats: MigrationStats) -> Optional[Path]:
    """
    Create backup before migration.

    Args:
        stats: Migration statistics tracker

    Returns:
        Path to backup directory or None on failure
    """
    try:
        # Create backup directory with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        backup_dir = Path(BACKUP_BASE) / f'tasks-pre-hash-migration-{timestamp}'
        backup_dir.parent.mkdir(parents=True, exist_ok=True)

        # Copy tasks directory
        shutil.copytree('tasks', backup_dir)

        print(f"✅ Backup created: {backup_dir}")
        return backup_dir

    except Exception as e:
        error = f"Failed to create backup: {e}"
        stats.add_error(error)
        print(f"❌ {error}", file=sys.stderr)
        return None


def create_rollback_script(backup_path: Path, dry_run: bool = False) -> bool:
    """
    Generate rollback script.

    Args:
        backup_path: Path to backup directory
        dry_run: If True, don't create script

    Returns:
        True on success
    """
    try:
        script_path = Path(STATE_DIR) / 'rollback-migration.sh'

        script_content = f"""#!/bin/bash
# Rollback hash ID migration
# Run this if migration goes wrong

set -e

echo "🔄 Rolling back task ID migration..."

# Delete new hash-based tasks
rm -rf tasks/

# Restore from backup
cp -r {backup_path} tasks/

echo "✅ Rollback complete"
echo "📋 Verify: ls tasks/backlog/ | head -5"
"""

        if not dry_run:
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(script_content)
            script_path.chmod(0o755)
            print(f"✅ Rollback script created: {script_path}")

        return True

    except Exception as e:
        print(f"❌ Failed to create rollback script: {e}", file=sys.stderr)
        return False


def print_migration_report(stats: MigrationStats, dry_run: bool):
    """
    Print migration report.

    Args:
        stats: Migration statistics
        dry_run: Whether this was a dry run
    """
    mode = "DRY RUN" if dry_run else "MIGRATION"

    print("\n" + "=" * 80)
    print(f"TASK ID {mode} REPORT")
    print("=" * 80)
    print(f"Date: {stats.start_time.isoformat()}")
    if stats.end_time:
        print(f"Duration: {stats.duration_seconds:.1f} seconds")
    print()

    print("SUMMARY")
    print(f"  Tasks found: {stats.tasks_found}")
    print(f"  Tasks migrated: {stats.tasks_migrated}")
    print(f"  Files renamed: {stats.files_renamed}")
    print(f"  Cross-references updated: {stats.cross_references_updated}")
    print(f"  Errors: {len(stats.errors)}")
    print()

    if stats.migrations:
        # Show sample migrations (up to 5)
        print("SAMPLE MIGRATIONS")
        for old_id, new_id in stats.migrations[:5]:
            print(f"  {old_id} → {new_id}")
        if len(stats.migrations) > 5:
            print(f"  ... and {len(stats.migrations) - 5} more")
        print()

    if not dry_run:
        print("BACKUP")
        print(f"  Location: {BACKUP_BASE}/tasks-pre-hash-migration-*/")
        print()

        print("ROLLBACK")
        print(f"  To undo: bash {STATE_DIR}/rollback-migration.sh")
        print()

        print("NEXT STEPS")
        print("  1. Verify a few migrated tasks look correct")
        print('  2. Run: grep -r "TASK-[0-9]" tasks/  # Should find none (or very few)')
        print("  3. If all good, delete backup after 30 days")
        print("  4. If issues, run rollback script immediately")
    else:
        print("TO PROCEED:")
        print("  python3 scripts/migrate-my-tasks.py --execute")

    print("=" * 80)

    # Print errors if any
    if stats.errors:
        print("\nERRORS:")
        for error in stats.errors:
            print(f"  ❌ {error}")


def main():
    """Main migration logic."""
    parser = argparse.ArgumentParser(
        description='Migrate task IDs to hash-based format'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without making them'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the migration'
    )

    args = parser.parse_args()

    # Require either --dry-run or --execute
    if not args.dry_run and not args.execute:
        parser.error("Must specify either --dry-run or --execute")

    dry_run = args.dry_run

    # Initialize stats
    stats = MigrationStats()

    print(f"\n{'🔍 DRY RUN MODE' if dry_run else '🚀 EXECUTING MIGRATION'}")
    print()

    # Step 1: Backup (only if not dry run)
    backup_path = None
    if not dry_run:
        print("Step 1: Creating backup...")
        backup_path = backup_tasks(stats)
        if not backup_path:
            print("❌ Migration aborted due to backup failure")
            return 1
        print()
    else:
        print("Step 1: Backup (skipped in dry run)")
        print()

    # Step 2: Scan task files
    print("Step 2: Scanning task files...")
    task_map = scan_task_files()
    stats.tasks_found = len(task_map)
    print(f"  Found {stats.tasks_found} tasks to migrate")
    print()

    if stats.tasks_found == 0:
        print("✅ No tasks need migration (all already using hash-based IDs)")
        return 0

    # Step 3: Generate ID mapping
    print("Step 3: Generating new hash IDs...")
    old_ids = list(task_map.keys())
    id_mapping = generate_id_mapping(old_ids)
    print(f"  Generated {len(id_mapping)} new IDs")
    print()

    # Step 4: Migrate files
    print("Step 4: Migrating files...")
    total_xrefs = 0

    for old_id, file_path in task_map.items():
        new_id = id_mapping[old_id]
        success, xref_count = migrate_file(
            file_path,
            old_id,
            new_id,
            id_mapping,
            dry_run=dry_run
        )

        if success:
            stats.add_migration(old_id, new_id)
            stats.files_renamed += 1
            total_xrefs += xref_count

            if not dry_run:
                print(f"  ✅ {old_id} → {new_id}")
        else:
            stats.add_error(f"Failed to migrate {old_id}")

    stats.cross_references_updated = total_xrefs
    print(f"  Updated {total_xrefs} cross-references")
    print()

    # Step 5: Create rollback script
    if not dry_run and backup_path:
        print("Step 5: Creating rollback script...")
        create_rollback_script(backup_path, dry_run=False)
        print()
    else:
        print("Step 5: Rollback script (skipped in dry run)")
        print()

    # Finish and print report
    stats.finish()
    print_migration_report(stats, dry_run)

    return 0 if len(stats.errors) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
