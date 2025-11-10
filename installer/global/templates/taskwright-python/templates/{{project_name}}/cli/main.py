"""CLI entry point for {{ProjectName}}."""
import argparse
import sys
from typing import List, Optional

from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.orchestrator.orchestrator import Orchestrator


def setup_container() -> DIContainer:
    """Setup dependency injection container.

    Returns:
        Configured DI container
    """
    container = DIContainer()

    # Register services
    # Example:
    # container.register("config", load_config())
    # container.register_factory("analyzer_agent", lambda: AnalyzerAgent(container))

    # Register orchestrator
    container.register_factory(
        "orchestrator",
        lambda: Orchestrator(container)
    )

    return container


def print_success(message: str) -> None:
    """Print success message.

    Args:
        message: Message to print
    """
    print(f"✓ {message}")


def print_error(message: str) -> None:
    """Print error message.

    Args:
        message: Error message to print
    """
    print(f"✗ Error: {message}", file=sys.stderr)


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        prog="{{project-name}}",
        description="{{ProjectDescription}}"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="{{project-name}} 0.1.0"
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

    # Example command
    example_parser = subparsers.add_parser(
        "example",
        help="Example command"
    )
    example_parser.add_argument(
        "path",
        help="Path to process"
    )

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Show help if no command provided
    if not parsed_args.command:
        parser.print_help()
        return 0

    # Initialize container and orchestrator
    try:
        container = setup_container()
        orchestrator = container.get("orchestrator")

        # Execute workflow based on command
        result = orchestrator.execute_workflow(
            workflow_name=parsed_args.command,
            context=vars(parsed_args)
        )

        if result.success:
            print_success(f"{parsed_args.command.capitalize()} completed successfully")
            return 0
        else:
            print_error(result.error or "Unknown error")
            return 1

    except Exception as e:
        print_error(str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
