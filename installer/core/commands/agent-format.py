#!/usr/bin/env python3
"""
/agent-format Command - Format agents with GitHub best practices

Usage:
    /agent-format <path> [options]

Examples:
    /agent-format installer/core/agents/architectural-reviewer.md
    /agent-format installer/core/agents/*.md --report
    /agent-format architectural-reviewer.md --dry-run
"""

import sys
import argparse
from pathlib import Path
from glob import glob
import shutil
import time

# === BEGIN: Repository Root Resolution ===
# Ensure repository root is in sys.path for installer.* imports
# This allows the script to work when executed via symlink from any directory
def _add_repo_to_path():
    """Add repository root to sys.path if not already present."""
    script_path = Path(__file__).resolve()
    # Navigate: commands/ -> global/ -> installer/ -> guardkit/ (4 levels up)
    repo_root = script_path.parent.parent.parent.parent
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

_add_repo_to_path()
# === END: Repository Root Resolution ===

# Add lib directory to path (resolve symlink for correct path)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'lib'))

from agent_formatting import (
    parse_agent,
    calculate_metrics,
    AgentFormatter,
    FormatValidator,
    ValidationReporter,
)

# TASK-FIX-7C3D: Import file I/O utilities
from installer.core.lib.utils.file_io import safe_write_file


def resolve_paths(path_pattern: str) -> list[Path]:
    """
    Resolve path pattern to list of agent files.

    Args:
        path_pattern: File path, glob pattern, or directory

    Returns:
        List of resolved Path objects
    """
    path = Path(path_pattern)

    # Check if it's a directory
    if path.is_dir():
        return sorted(path.glob('*.md'))

    # Check if it's a file
    if path.is_file():
        return [path]

    # Try glob pattern
    matched_files = glob(path_pattern)
    if matched_files:
        return sorted([Path(f) for f in matched_files])

    return []


def process_agent(
    agent_path: Path, args: argparse.Namespace
) -> tuple[bool, str, object]:
    """
    Process a single agent file.

    Args:
        agent_path: Path to agent file
        args: Command line arguments

    Returns:
        Tuple of (success, message, validation_result)
    """
    try:
        if args.verbose:
            print(f'\n{"="*60}')
            print(f'Processing: {agent_path.name}')
            print(f'{"="*60}')

        # Parse agent
        agent = parse_agent(agent_path)

        # Calculate current metrics
        current_metrics = calculate_metrics(agent)

        if args.validate_only:
            # Just show current metrics
            reporter = ValidationReporter()

            # Create fake validation result for reporting
            from agent_formatting.validator import ValidationResult

            validation = ValidationResult(
                success=True,
                issues=[],
                metrics_before=current_metrics,
                metrics_after=current_metrics,
            )

            report = reporter.generate_report(validation, agent_path, dry_run=False)
            print(f'\n[VALIDATE ONLY] {agent_path.name}\n')
            print(report)

            return True, 'Validation complete', validation

        # Format agent
        formatter = AgentFormatter()
        formatted_content = formatter.format(agent, current_metrics)

        # Validate formatting
        validator = FormatValidator()
        validation = validator.validate(agent, formatted_content)

        if not validation.success:
            return False, f'Validation failed: {"; ".join(validation.issues)}', validation

        # Generate report
        reporter = ValidationReporter()
        report = reporter.generate_report(validation, agent_path, dry_run=args.dry_run)

        if args.report or args.verbose:
            print(f'\n{report}\n')

        # Apply changes (unless dry run)
        if not args.dry_run:
            # Create backup if requested
            if args.backup:
                backup_path = agent_path.with_suffix('.md.bak')
                shutil.copy2(agent_path, backup_path)
                if args.verbose:
                    print(f'Backup created: {backup_path}')

            # Write formatted content with error handling (TASK-FIX-7C3D)
            success, error_msg = safe_write_file(agent_path, formatted_content)
            if not success:
                return False, f'Failed to write formatted content: {error_msg}', validation

            before_status = validation.metrics_before.get_status()
            after_status = validation.metrics_after.get_status()

            return True, f'{before_status} → {after_status}', validation
        else:
            print('[DRY RUN] No changes applied\n')
            return True, 'Dry run complete', validation

    except Exception as e:
        return False, f'Error: {str(e)}', None


def print_summary(results: list[tuple[Path, bool, str, object]]):
    """
    Print summary of batch operation.

    Args:
        results: List of (path, success, message, validation) tuples
    """
    total = len(results)
    successful = sum(1 for _, success, _, _ in results if success)
    failed = total - successful

    print(f'\n{"="*60}')
    print('SUMMARY')
    print(f'{"="*60}')
    print(f'Total: {total} agents')
    print(f'Successful: {successful}')
    print(f'Failed: {failed}')

    if failed > 0:
        print('\nFailed agents:')
        for path, success, message, _ in results:
            if not success:
                print(f'  - {path.name}: {message}')

    # Status distribution
    validations = [v for _, _, _, v in results if v is not None]
    if validations:
        pass_count = sum(
            1 for v in validations if v.metrics_after.get_status() == 'PASS'
        )
        warn_count = sum(
            1 for v in validations if v.metrics_after.get_status() == 'WARN'
        )
        fail_count = sum(
            1 for v in validations if v.metrics_after.get_status() == 'FAIL'
        )

        print(f'\nQuality Status Distribution:')
        print(f'  ✅ PASS: {pass_count} ({pass_count/len(validations)*100:.1f}%)')
        print(f'  ⚠️  WARN: {warn_count} ({warn_count/len(validations)*100:.1f}%)')
        print(f'  ❌ FAIL: {fail_count} ({fail_count/len(validations)*100:.1f}%)')


def main(args: list[str] = None) -> int:
    """
    Main entry point for /agent-format command.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        prog='agent-format',
        description='Format agent documentation with GitHub best practices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s installer/core/agents/architectural-reviewer.md
  %(prog)s installer/core/agents/*.md --report
  %(prog)s architectural-reviewer.md --dry-run --verbose
  %(prog)s installer/core/agents/ --validate-only
        ''',
    )

    parser.add_argument('path', help='Agent file, glob pattern, or directory')

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying',
    )

    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed validation report',
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Check quality metrics only, no formatting',
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create .bak backup before formatting (default: true)',
    )

    parser.add_argument(
        '--no-backup',
        dest='backup',
        action='store_false',
        help='Disable backup creation',
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true', help='Show detailed progress'
    )

    parser.add_argument(
        '--fail-on-warn',
        action='store_true',
        help='Exit with error on warnings',
    )

    parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])

    # Resolve paths
    paths = resolve_paths(parsed_args.path)

    if not paths:
        print(f'❌ No agents found matching: {parsed_args.path}', file=sys.stderr)
        return 1

    print(f'Found {len(paths)} agent(s) to process')

    # Process each agent
    results = []
    start_time = time.time()

    for i, path in enumerate(paths, 1):
        if not parsed_args.verbose and len(paths) > 1:
            print(f'[{i}/{len(paths)}] Processing {path.name}...', end=' ')

        success, message, validation = process_agent(path, parsed_args)
        results.append((path, success, message, validation))

        if not parsed_args.verbose and len(paths) > 1:
            status_icon = '✅' if success else '❌'
            print(f'{status_icon} {message}')

    elapsed_time = time.time() - start_time

    # Print summary for batch operations
    if len(paths) > 1:
        print_summary(results)
        print(f'\nTime: {elapsed_time:.1f} seconds')
        print(f'Avg: {elapsed_time/len(paths):.1f} seconds/agent')

    # Determine exit code
    all_successful = all(success for _, success, _, _ in results)

    if not all_successful:
        return 1

    # Check for warnings if --fail-on-warn
    if parsed_args.fail_on_warn:
        validations = [v for _, _, _, v in results if v is not None]
        has_warnings = any(
            v.metrics_after.get_status() in ['WARN', 'FAIL'] for v in validations
        )
        if has_warnings:
            return 4  # Exit code 4 for quality warnings

    return 0


if __name__ == '__main__':
    sys.exit(main())
