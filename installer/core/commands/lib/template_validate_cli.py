"""
Template Validate CLI

Command-line interface for comprehensive template validation.
"""

import sys
import importlib
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
# Path: .../installer/core/commands/lib/template_validate_cli.py
# Need to go up to .../installer level (4 parents)
cli_path = Path(__file__).resolve()
installer_dir = cli_path.parent.parent.parent.parent
sys.path.insert(0, str(installer_dir))

# Import using importlib to bypass 'global' keyword issue
_validation_module = importlib.import_module('global.lib.template_validation')
ValidateConfig = _validation_module.ValidateConfig
TemplateValidateOrchestrator = _validation_module.TemplateValidateOrchestrator


def parse_args(args: List[str]) -> Optional[ValidateConfig]:
    """Parse command-line arguments"""
    if not args or '--help' in args or '-h' in args:
        print_usage()
        return None

    # Required: template path
    template_path = Path(args[0])
    if not template_path.exists():
        print(f"Error: Template path does not exist: {template_path}")
        return None

    if not template_path.is_dir():
        print(f"Error: Template path must be a directory: {template_path}")
        return None

    # Parse optional arguments
    sections = None
    resume_session_id = None
    interactive = True
    auto_fix = False
    verbose = False
    output_dir = None

    i = 1
    while i < len(args):
        arg = args[i]

        if arg == '--sections':
            if i + 1 >= len(args):
                print("Error: --sections requires a value")
                return None
            sections = [args[i + 1]]
            i += 2
        elif arg == '--resume':
            if i + 1 >= len(args):
                print("Error: --resume requires a session ID")
                return None
            resume_session_id = args[i + 1]
            i += 2
        elif arg == '--non-interactive':
            interactive = False
            i += 1
        elif arg == '--auto-fix':
            auto_fix = True
            i += 1
        elif arg == '--verbose' or arg == '-v':
            verbose = True
            i += 1
        elif arg == '--output-dir':
            if i + 1 >= len(args):
                print("Error: --output-dir requires a path")
                return None
            output_dir = Path(args[i + 1])
            i += 2
        else:
            print(f"Unknown argument: {arg}")
            return None

    return ValidateConfig(
        template_path=template_path,
        sections=sections,
        interactive=interactive,
        resume_session_id=resume_session_id,
        output_dir=output_dir,
        auto_fix=auto_fix,
        verbose=verbose,
    )


def print_usage():
    """Print usage information"""
    print("""
Template Validate - Comprehensive Template Audit

Usage:
  /template-validate <template-path> [options]

Arguments:
  <template-path>         Path to template directory to validate

Options:
  --sections <spec>       Comma-separated or range of sections (e.g., 1,4,7 or 1-7)
  --resume <session-id>   Resume previous audit session
  --non-interactive       Run in batch mode without prompts
  --auto-fix              Automatically apply fixes where possible
  --verbose, -v           Enable verbose output
  --output-dir <path>     Custom output directory for reports
  --help, -h              Show this help message

Examples:
  # Full audit (all sections)
  /template-validate ./installer/core/templates/react-typescript

  # Specific sections only
  /template-validate ./templates/my-template --sections 1,4,7,12

  # Section range
  /template-validate ./templates/my-template --sections 1-7

  # Resume previous audit
  /template-validate ./templates/my-template --resume abc12345

  # Non-interactive mode
  /template-validate ./templates/my-template --non-interactive

For more information, see:
  installer/core/commands/template-validate.md
""")


def main():
    """Main CLI entry point"""
    # Parse command-line arguments (skip script name)
    config = parse_args(sys.argv[1:])

    if config is None:
        sys.exit(0)

    try:
        # Create and run orchestrator
        orchestrator = TemplateValidateOrchestrator(config)
        result = orchestrator.run()

        # Print final summary
        print("\n" + "=" * 60)
        print("Audit Complete!")
        print("=" * 60)
        print(f"Overall Score: {result.overall_score:.1f}/10 ({result.grade})")
        print(f"Recommendation: {result.recommendation.value.upper()}")
        print(f"Sections Completed: {len(result.section_results)}")
        if result.critical_issues:
            print(f"Critical Issues: {len(result.critical_issues)}")
        print(f"Duration: {result.audit_duration_seconds / 60:.1f} minutes")

        # Exit with appropriate code
        if result.overall_score >= 8.0:
            sys.exit(0)
        elif result.overall_score >= 6.0:
            sys.exit(1)
        else:
            sys.exit(2)

    except KeyboardInterrupt:
        print("\n\nAudit interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nError during audit: {e}")
        if config.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


if __name__ == '__main__':
    main()
