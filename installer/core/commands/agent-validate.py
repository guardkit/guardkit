#!/usr/bin/env python3
"""
/agent-validate command implementation.

Validates agent files against GitHub best practices and GuardKit standards.
"""

import argparse
import sys
from pathlib import Path

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
lib_path = Path(__file__).resolve().parent / 'lib'
sys.path.insert(0, str(lib_path))

from agent_validator import AgentValidator, ValidationConfig
from agent_validator.formatters import ConsoleFormatter, JSONFormatter, MinimalFormatter

# TASK-FIX-7C3D: Import file I/O utilities
import importlib
_file_io_module = importlib.import_module('installer.core.lib.utils.file_io')
safe_write_file = _file_io_module.safe_write_file


def main():
    """Main entry point for agent-validate command."""
    parser = argparse.ArgumentParser(
        description="Validate agent file quality against best practices"
    )
    parser.add_argument(
        "agent_file",
        type=Path,
        help="Path to agent markdown file"
    )
    parser.add_argument(
        "--format",
        choices=["console", "json", "minimal"],
        default="console",
        help="Output format (default: console)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum acceptable score (0.0-10.0, default: 0.0 for info only)"
    )
    parser.add_argument(
        "--exit-on-fail",
        action="store_true",
        help="Exit with code 1 if score below threshold"
    )
    parser.add_argument(
        "--suggest-fixes",
        action="store_true",
        help="Include auto-fix suggestions in output"
    )
    parser.add_argument(
        "--auto-enhance",
        action="store_true",
        help="Auto-invoke /agent-enhance if below threshold"
    )
    parser.add_argument(
        "--checks",
        nargs="+",
        help="Specific checks to run (e.g., structure example_density boundaries)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Detailed diagnostic output"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write report to file instead of stdout"
    )

    args = parser.parse_args()

    # Validate agent file exists
    if not args.agent_file.exists():
        print(f"Error: Agent file not found: {args.agent_file}", file=sys.stderr)
        sys.exit(1)

    if not args.agent_file.is_file():
        print(f"Error: Path is not a file: {args.agent_file}", file=sys.stderr)
        sys.exit(1)

    # Create config
    config = ValidationConfig(
        threshold=args.threshold,
        output_format=args.format,
        check_categories=args.checks,
        auto_enhance=args.auto_enhance,
        suggest_fixes=args.suggest_fixes,
        verbose=args.verbose
    )

    try:
        # Validate
        validator = AgentValidator(config)
        report = validator.validate(args.agent_file)

        # Format output
        if args.format == "console":
            formatter = ConsoleFormatter()
        elif args.format == "json":
            formatter = JSONFormatter()
        else:
            formatter = MinimalFormatter()

        output = formatter.format(report)

        # Write output with error handling (TASK-FIX-7C3D)
        if args.output_file:
            success, error_msg = safe_write_file(args.output_file, output)
            if not success:
                print(f"Error writing report: {error_msg}", file=sys.stderr)
                sys.exit(2)
            print(f"Report written to: {args.output_file}")
        else:
            print(output)

        # Auto-enhance if requested and below threshold
        if args.auto_enhance and report.overall_score < args.threshold:
            print("\n🔧 Running auto-enhancement...")
            print("⚠️  Note: /agent-enhance integration not yet implemented")
            # TODO: Call /agent-enhance command
            # subprocess.run(['agent-enhance', str(args.agent_file)])

        # Exit code
        if args.exit_on_fail and report.overall_score < args.threshold:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Error during validation: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
