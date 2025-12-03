#!/usr/bin/env python3
"""
Rename Script: Taskwright -> GuardKit

Performs bulk text replacement across the codebase with case handling.
Preserves git history by using git mv for file renames.

Usage:
    python3 scripts/rename-taskwright-to-guardkit.py [--dry-run] [--verbose]

Options:
    --dry-run   Preview changes without modifying files
    --verbose   Show detailed progress information
"""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ChangeRecord:
    """Record of a single change made."""
    file_path: str
    change_type: str  # 'content', 'rename'
    old_value: str
    new_value: str
    line_number: Optional[int] = None
    occurrence_count: int = 1


@dataclass
class ChangeReport:
    """Aggregated report of all changes."""
    files_modified: list = field(default_factory=list)
    files_renamed: list = field(default_factory=list)
    files_skipped: list = field(default_factory=list)
    total_replacements: int = 0
    changes: list = field(default_factory=list)
    errors: list = field(default_factory=list)


# Replacement patterns in order of specificity (most specific first)
REPLACEMENTS = [
    # GitHub URLs and organization names (most specific)
    ('taskwright-dev/taskwright', 'guardkit/guardkit'),
    ('taskwright-dev', 'guardkit'),

    # CLI aliases with word boundaries
    (r'\btwi\b', 'gki'),
    (r'\btw\b', 'gk'),

    # Case variations (order matters: longer/specific first)
    ('TASKWRIGHT', 'GUARDKIT'),
    ('Taskwright', 'GuardKit'),
    ('taskwright', 'guardkit'),
]

# Files and directories to exclude
EXCLUDE_PATTERNS = [
    'tasks/completed/',
    'tasks/archived/',
    '.claude/reviews/',
    '.git/',
    '__pycache__/',
    '*.pyc',
    '.DS_Store',
    'node_modules/',
    'venv/',
    '.venv/',
    'dist/',
    'build/',
    '*.egg-info/',
]

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.svg',
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.bz2', '.7z',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.class',
    '.sqlite', '.db',
}

# File rename patterns
FILE_RENAMES = [
    ('taskwright.sln', 'guardkit.sln'),
    ('taskwright.marker.json', 'guardkit.marker.json'),
    ('taskwright-workflow.md', 'guardkit-workflow.md'),
    ('taskwright-vs-requirekit.md', 'guardkit-vs-requirekit.md'),
]


def is_excluded(path: Path, exclude_patterns: list) -> bool:
    """Check if a path matches any exclusion pattern."""
    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern.endswith('/'):
            # Directory pattern
            if pattern[:-1] in path_str or path_str.startswith(pattern[:-1]):
                return True
        elif '*' in pattern:
            # Glob pattern
            import fnmatch
            if fnmatch.fnmatch(path.name, pattern):
                return True
        else:
            # Exact match
            if pattern in path_str:
                return True
    return False


def is_binary(path: Path) -> bool:
    """Check if a file is binary based on extension or content."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    # Check for null bytes in first 8KB
    try:
        with open(path, 'rb') as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                return True
    except (IOError, OSError):
        return True

    return False


def apply_replacements(content: str, replacements: list) -> tuple[str, int]:
    """Apply all replacement patterns to content.

    Returns:
        Tuple of (modified_content, replacement_count)
    """
    total_count = 0

    for old, new in replacements:
        if old.startswith(r'\b'):
            # Regex pattern with word boundaries
            pattern = re.compile(old)
            matches = len(pattern.findall(content))
            if matches > 0:
                content = pattern.sub(new, content)
                total_count += matches
        else:
            # Simple string replacement
            count = content.count(old)
            if count > 0:
                content = content.replace(old, new)
                total_count += count

    return content, total_count


def process_file(path: Path, report: ChangeReport, dry_run: bool, verbose: bool) -> bool:
    """Process a single file for content replacements.

    Returns:
        True if file was modified, False otherwise.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except UnicodeDecodeError:
        # Skip files that can't be decoded as UTF-8
        report.files_skipped.append(str(path))
        if verbose:
            print(f"  Skipped (encoding): {path}")
        return False
    except (IOError, OSError) as e:
        report.errors.append(f"Error reading {path}: {e}")
        return False

    modified_content, replacement_count = apply_replacements(original_content, REPLACEMENTS)

    if replacement_count > 0:
        if not dry_run:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
            except (IOError, OSError) as e:
                report.errors.append(f"Error writing {path}: {e}")
                return False

        report.files_modified.append(str(path))
        report.total_replacements += replacement_count
        report.changes.append(ChangeRecord(
            file_path=str(path),
            change_type='content',
            old_value='(multiple patterns)',
            new_value='(see replacements)',
            occurrence_count=replacement_count
        ))

        if verbose:
            print(f"  Modified: {path} ({replacement_count} replacements)")

        return True

    return False


def rename_file(old_path: Path, new_name: str, report: ChangeReport, dry_run: bool, verbose: bool) -> bool:
    """Rename a file using git mv to preserve history.

    Returns:
        True if file was renamed, False otherwise.
    """
    new_path = old_path.parent / new_name

    if not old_path.exists():
        return False

    if new_path.exists():
        report.errors.append(f"Cannot rename {old_path}: {new_path} already exists")
        return False

    if not dry_run:
        try:
            # Use git mv to preserve history
            result = subprocess.run(
                ['git', 'mv', str(old_path), str(new_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                # Fall back to regular rename if git mv fails
                old_path.rename(new_path)
        except (subprocess.SubprocessError, OSError) as e:
            report.errors.append(f"Error renaming {old_path}: {e}")
            return False

    report.files_renamed.append((str(old_path), str(new_path)))
    report.changes.append(ChangeRecord(
        file_path=str(old_path),
        change_type='rename',
        old_value=old_path.name,
        new_value=new_name
    ))

    if verbose:
        print(f"  Renamed: {old_path.name} -> {new_name}")

    return True


def find_files_to_process(root: Path, exclude_patterns: list) -> list[Path]:
    """Find all files that should be processed."""
    files = []

    for path in root.rglob('*'):
        if path.is_file():
            if is_excluded(path, exclude_patterns):
                continue
            if is_binary(path):
                continue
            files.append(path)

    return sorted(files)


def generate_report(report: ChangeReport, output_path: Path, dry_run: bool):
    """Generate a markdown report of all changes."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mode = "DRY RUN" if dry_run else "EXECUTED"

    content = f"""# GuardKit Rename Report

**Generated**: {timestamp}
**Mode**: {mode}

## Summary

| Metric | Count |
|--------|-------|
| Files Modified | {len(report.files_modified)} |
| Files Renamed | {len(report.files_renamed)} |
| Files Skipped | {len(report.files_skipped)} |
| Total Replacements | {report.total_replacements} |
| Errors | {len(report.errors)} |

## Replacement Patterns Applied

| Original | Replacement |
|----------|-------------|
| `taskwright-dev/taskwright` | `guardkit/guardkit` |
| `taskwright-dev` | `guardkit` |
| `\\btwi\\b` | `gki` |
| `\\btw\\b` | `gk` |
| `TASKWRIGHT` | `GUARDKIT` |
| `Taskwright` | `GuardKit` |
| `taskwright` | `guardkit` |

## Files Modified

"""

    if report.files_modified:
        for f in report.files_modified:
            content += f"- `{f}`\n"
    else:
        content += "_No files modified_\n"

    content += "\n## Files Renamed\n\n"

    if report.files_renamed:
        for old, new in report.files_renamed:
            content += f"- `{old}` -> `{new}`\n"
    else:
        content += "_No files renamed_\n"

    content += "\n## Files Skipped\n\n"

    if report.files_skipped:
        for f in report.files_skipped[:20]:  # Limit to first 20
            content += f"- `{f}`\n"
        if len(report.files_skipped) > 20:
            content += f"\n_... and {len(report.files_skipped) - 20} more_\n"
    else:
        content += "_No files skipped_\n"

    content += "\n## Errors\n\n"

    if report.errors:
        for error in report.errors:
            content += f"- {error}\n"
    else:
        content += "_No errors_\n"

    content += f"""

---

## Next Steps

1. Review changes: `git diff`
2. Run validation: `./scripts/validate-rename.sh`
3. Test installation: `./installer/scripts/install.sh`
4. Commit changes: `git add -A && git commit -m "Rename Taskwright to GuardKit"`

## Rollback

If needed, restore from backup branch:
```bash
git checkout backup/pre-guardkit-rename-YYYYMMDD-HHMMSS
```
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description='Rename Taskwright to GuardKit across the codebase'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed progress information'
    )
    args = parser.parse_args()

    # Colors for terminal output
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    RED = '\033[0;31m'
    NC = '\033[0m'

    print(f"{BLUE}{'=' * 57}{NC}")
    print(f"{BLUE}  GuardKit Rename Script{NC}")
    print(f"{BLUE}{'=' * 57}{NC}")
    print()

    if args.dry_run:
        print(f"{YELLOW}DRY RUN MODE - No files will be modified{NC}")
        print()

    # Find project root (directory containing .git)
    root = Path.cwd()
    while root != root.parent:
        if (root / '.git').exists():
            break
        root = root.parent
    else:
        print(f"{RED}Error: Not in a git repository{NC}")
        sys.exit(1)

    os.chdir(root)
    print(f"Working directory: {root}")
    print()

    report = ChangeReport()

    # Step 1: Find files to process
    print(f"{BLUE}[1/4]{NC} Finding files to process...")
    files = find_files_to_process(root, EXCLUDE_PATTERNS)
    print(f"{GREEN}  Found {len(files)} files to process{NC}")

    # Step 2: Process file contents
    print(f"{BLUE}[2/4]{NC} Processing file contents...")
    modified_count = 0
    for path in files:
        if process_file(path, report, args.dry_run, args.verbose):
            modified_count += 1
    print(f"{GREEN}  Modified {modified_count} files ({report.total_replacements} replacements){NC}")

    # Step 3: Rename files
    print(f"{BLUE}[3/4]{NC} Renaming files...")
    renamed_count = 0
    for old_name, new_name in FILE_RENAMES:
        # Search for files matching the old name
        for path in root.rglob(old_name):
            if not is_excluded(path, EXCLUDE_PATTERNS):
                if rename_file(path, new_name, report, args.dry_run, args.verbose):
                    renamed_count += 1
    print(f"{GREEN}  Renamed {renamed_count} files{NC}")

    # Step 4: Generate report
    print(f"{BLUE}[4/4]{NC} Generating report...")
    report_path = root / '.claude' / 'state' / 'rename-report.md'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(report, report_path, args.dry_run)
    print(f"{GREEN}  Report saved to: {report_path}{NC}")

    # Summary
    print()
    print(f"{GREEN}{'=' * 57}{NC}")
    print(f"{GREEN}  Rename {'Preview' if args.dry_run else 'Complete'}!{NC}")
    print(f"{GREEN}{'=' * 57}{NC}")
    print()
    print(f"Files Modified:     {len(report.files_modified)}")
    print(f"Files Renamed:      {len(report.files_renamed)}")
    print(f"Total Replacements: {report.total_replacements}")
    print(f"Files Skipped:      {len(report.files_skipped)}")
    print(f"Errors:             {len(report.errors)}")
    print()

    if report.errors:
        print(f"{RED}Errors encountered:{NC}")
        for error in report.errors:
            print(f"  - {error}")
        print()

    if args.dry_run:
        print("To apply changes, run without --dry-run:")
        print("  python3 scripts/rename-taskwright-to-guardkit.py")
    else:
        print("Next steps:")
        print("  1. Review changes: git diff")
        print("  2. Run validation: ./scripts/validate-rename.sh")
        print("  3. Commit changes: git add -A && git commit -m 'Rename Taskwright to GuardKit'")
    print()

    # Exit with error code if there were errors
    sys.exit(1 if report.errors else 0)


if __name__ == '__main__':
    main()
