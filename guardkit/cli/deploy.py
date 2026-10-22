"""``guardkit deploy`` — give a project the factory's deployment setup.

    guardkit deploy init --env-id <id> --live-port <n> --candidate-port <n>
                         --health-path /health [--project-dir .]

Copies GuardKit's deployment kit into ``<project>/deploy/`` (profile,
settings and the scripts that implement the factory's deployment contract),
never overwriting an existing file, then validates ``deploy/profile.yaml`` as
a ``deploy-profile``. The project still writes its own root ``compose.yaml``
(see the copied ``deploy/README.md``).

Exit codes: 0 done and the profile is valid; 1 the profile is invalid; 2 a
value was refused or the kit is missing (nothing written).
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from guardkit.qa.formats import QAFormatError, validate_instance
from guardkit.templates.deploy_kit import DeployKitError, install_deploy_kit

console = Console()


@click.group()
def deploy() -> None:
    """Deployment setup for the software factory (a generic Compose kit)."""


@deploy.command("init")
@click.option("--env-id", required=True, help="Environment id, e.g. myapp (lower-case, letters, digits, '-').")
@click.option("--live-port", required=True, type=int, help="Loopback port of the live app.")
@click.option("--candidate-port", required=True, type=int, help="Loopback port of the candidate check.")
@click.option("--health-path", required=True, help="Path that answers HTTP 200 when the app is up, e.g. /health.")
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="The project root (the folder holding compose.yaml).",
)
def init(
    env_id: str,
    live_port: int,
    candidate_port: int,
    health_path: str,
    project_dir: Path,
) -> None:
    """Copy the deployment kit into PROJECT_DIR/deploy and validate the profile."""
    if not project_dir.is_dir():
        console.print(f"[bold red]✗[/bold red] project folder not found: {project_dir}")
        sys.exit(2)
    try:
        result = install_deploy_kit(
            project_dir,
            env_id=env_id,
            live_port=live_port,
            candidate_port=candidate_port,
            health_path=health_path,
        )
    except DeployKitError as exc:
        console.print(f"[bold red]✗[/bold red] {exc}", highlight=False)
        sys.exit(2)

    for rel in result.written:
        console.print(f"  wrote   {rel}", highlight=False)
    for rel in result.skipped:
        console.print(f"  skipped {rel} (already exists, left as it is)", highlight=False)

    profile = result.profile_path
    assert profile is not None
    try:
        validate_instance("deploy-profile", profile)
    except QAFormatError as exc:
        console.print("[bold red]✗ deploy/profile.yaml is not a valid deploy-profile[/bold red]")
        console.print(str(exc), highlight=False)
        sys.exit(1)
    console.print(f"[bold green]✓[/bold green] {profile} is a valid deploy-profile", highlight=False)
    if not (project_dir / "compose.yaml").is_file():
        console.print(
            "  next: add a root compose.yaml whose public service publishes "
            "127.0.0.1:${APP_PORT} (see deploy/README.md)",
            highlight=False,
        )
