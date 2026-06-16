"""
Feature CLI commands.

This module provides Click commands for feature YAML management,
including pre-flight validation before running autobuild feature.

Example:
    $ guardkit feature validate FEAT-AC1A
    $ guardkit feature validate FEAT-AC1A --json
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import click
import yaml
from rich.console import Console
from rich.table import Table

from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    FeatureNotFoundError,
    FeatureParseError,
)

console = Console()
logger = logging.getLogger(__name__)

from guardkit.orchestrator.feature_audit import audit_features, FeatureAuditRow


# ============================================================================
# Feature Command Group
# ============================================================================


@click.group()
def feature():
    """Feature management commands.

    Commands for validating and inspecting feature YAML files
    used by AutoBuild feature mode.
    """
    pass



# ============================================================================
# Validate Command
# ============================================================================


def _find_feature_file(feature_id: str, repo_root: Path) -> Path:
    """Locate a feature YAML file by ID.

    Parameters
    ----------
    feature_id : str
        Feature identifier (e.g., "FEAT-AC1A")
    repo_root : Path
        Repository root directory

    Returns
    -------
    Path
        Path to the feature YAML file

    Raises
    ------
    FeatureNotFoundError
        If the feature file does not exist
    """
    features_dir = repo_root / FeatureLoader.FEATURES_DIR

    feature_file = features_dir / f"{feature_id}.yaml"
    if not feature_file.exists():
        feature_file = features_dir / f"{feature_id}.yml"

    if not feature_file.exists():
        raise FeatureNotFoundError(
            f"Feature file not found: {feature_id}\n"
            f"Searched in: {features_dir}\n"
            f"Create feature with: /feature-plan \"your feature description\""
        )

    return feature_file


def _load_raw_yaml(feature_file: Path) -> Dict[str, Any]:
    """Load raw YAML data from a feature file.

    Parameters
    ----------
    feature_file : Path
        Path to the YAML file

    Returns
    -------
    Dict[str, Any]
        Parsed YAML data

    Raises
    ------
    FeatureParseError
        If the file contains invalid YAML
    """
    try:
        with open(feature_file, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise FeatureParseError(
            f"Failed to parse YAML: {feature_file}\nError: {e}"
        )

    if not isinstance(data, dict):
        raise FeatureParseError(
            f"Feature YAML must be a mapping, got {type(data).__name__}: {feature_file}"
        )

    return data


def _output_json(
    feature_id: str,
    valid: bool,
    schema_errors: List[str],
    structural_errors: List[str],
    error_type: str = "",
    error_message: str = "",
) -> None:
    """Output validation results as JSON to stdout."""
    result: Dict[str, Any] = {
        "feature_id": feature_id,
        "valid": valid,
        "errors": schema_errors + structural_errors,
        "schema_errors": schema_errors,
        "structural_errors": structural_errors,
    }
    if error_type:
        result["error_type"] = error_type
        result["error_message"] = error_message
    click.echo(json.dumps(result, indent=2))


def _output_human_success(feature_id: str) -> None:
    """Print success message with green checkmark."""
    console.print(f"[green]\u2713[/green] Feature {feature_id} is valid")


_SMOKE_GATE_PATH_ERROR_PREFIX = (
    "smoke_gates.command references non-existent path"
)


def _output_human_errors(
    feature_id: str,
    schema_errors: List[str],
    structural_errors: List[str],
) -> None:
    """Print validation errors with red crosses.

    Smoke-gate path errors (TASK-FPSG-004 / L3d) are emitted through
    plain ``click.echo`` rather than Rich's ``console.print`` so the
    formatted message stays byte-identical with what
    ``generate-feature-yaml --validate-smoke-gates`` (L3b) writes to
    stderr. Rich wraps long lines (e.g. tmp_path repo roots) at the
    terminal width, which would otherwise break byte-equality across
    the two defense layers \u2014 agents comparing wording would see two
    different messages.
    """
    console.print(f"[red]\u2717[/red] Feature {feature_id} has validation errors:\n")

    if schema_errors:
        console.print("[bold]Schema errors:[/bold]")
        for error in schema_errors:
            console.print(f"  [red]\u2717[/red] {error}")

    if structural_errors:
        if schema_errors:
            console.print()
        console.print("[bold]Structural errors:[/bold]")
        for error in structural_errors:
            if error.startswith(_SMOKE_GATE_PATH_ERROR_PREFIX):
                # Verbatim emission keeps L3d byte-identical with L3b.
                click.echo(error)
            else:
                console.print(f"  [red]\u2717[/red] {error}")


# Incomplete validate definition removed

@feature.command()
@click.argument("feature_id")
@click.option(
    "--json",
    "output_json_flag",
    is_flag=True,
    default=False,
    help="Output results as JSON for CI integration.",
)
def validate(feature_id: str, output_json_flag: bool) -> None:
    """Validate a feature YAML file.

    Performs two levels of validation:

    \b
    1. Schema compliance - validates against Pydantic models
    2. Structural integrity - checks task files exist, orchestration is complete

    \b
    Exit codes:
        0  Feature is valid
        1  Validation errors found
        2  Feature file not found or cannot be parsed
    """
    repo_root = Path.cwd()

    # Step 1: Find and load raw YAML
    try:
        feature_file = _find_feature_file(feature_id, repo_root)
        raw_data = _load_raw_yaml(feature_file)
    except FeatureNotFoundError as e:
        if output_json_flag:
            _output_json(feature_id, False, [], [], "not_found", str(e))
        else:
            console.print(f"[red]\u2717[/red] {e}")
        sys.exit(2)
    except FeatureParseError as e:
        if output_json_flag:
            _output_json(feature_id, False, [], [], "parse_error", str(e))
        else:
            console.print(f"[red]\u2717[/red] {e}")
        sys.exit(2)

    # Step 2: Schema validation (Pydantic)
    schema_errors = FeatureLoader.validate_yaml(raw_data)

    # Step 3: Structural validation (only if schema passes)
    structural_errors: List[str] = []
    if not schema_errors:
        try:
            loaded_feature = FeatureLoader.load_feature(
                feature_id, repo_root=repo_root, validate_paths=False
            )
            structural_errors = FeatureLoader.validate_feature(
                loaded_feature, repo_root=repo_root
            )
        except (FeatureParseError, FeatureNotFoundError) as e:
            structural_errors = [str(e)]

    # Step 4: Output results
    all_errors = schema_errors + structural_errors

    if output_json_flag:
        _output_json(feature_id, not all_errors, schema_errors, structural_errors)
    elif all_errors:
        _output_human_errors(feature_id, schema_errors, structural_errors)
    else:
        _output_human_success(feature_id)

    sys.exit(1 if all_errors else 0)

# ============================================================================
# Audit Command
# ============================================================================

@click.command()
@click.option(
    "--fix",
    is_flag=True,
    default=False,
    help="Rewrite stale feature status fields to inferred status.",
)
def audit(fix: bool) -> None:
    """Audit all features and optionally fix stale statuses.

    Prints a table with columns:
    Feature | Declared | Inferred | Tasks (completed/total) | Stale?
    Stale rows are marked with a ⚠. A summary line reports the count of stale features.
    With ``--fix`` the status field of each stale feature YAML is updated to the inferred status.
    """
    repo_root = Path.cwd()
    rows: List[FeatureAuditRow] = audit_features(repo_root)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Feature")
    table.add_column("Declared")
    table.add_column("Inferred")
    table.add_column("Tasks (c/t)")
    table.add_column("Stale?")

    stale_count = 0
    for r in rows:
        stale_marker = "⚠" if r.is_stale else ""
        if r.is_stale:
            stale_count += 1
        tasks_display = f"{r.tasks_completed}/{r.tasks_total}"
        table.add_row(r.feature_id, r.declared_status, r.inferred_status, tasks_display, stale_marker)

    console.print(table)
    if stale_count:
        console.print(f"{stale_count} stale feature(s) found.")
    else:
        console.print("No stale features.")

    if fix and stale_count:
        for r in rows:
            if not r.is_stale:
                continue
            yaml_path = repo_root / ".guardkit" / "features" / f"{r.feature_id}.yaml"
            try:
                data = _load_raw_yaml(yaml_path)
                if data is None:
                    continue
                data["status"] = r.inferred_status
                with open(yaml_path, "w") as f:
                    yaml.safe_dump(data, f, sort_keys=False)
                console.print(f"Updated {r.feature_id}: status set to {r.inferred_status}")
            except Exception as e:
                console.print(f"[red]Error fixing {yaml_path.name}: {e}[/red]")
        # Reconciled the stale statuses; exit success so CI proceeds.
        sys.exit(0)

    # AC-004: non-zero exit when stale features remain and --fix was not used,
    # so `guardkit feature audit` can gate CI. Clean (no stale) => exit 0.
    sys.exit(1 if stale_count else 0)


# Register subcommands
feature.add_command(validate)
feature.add_command(audit)


