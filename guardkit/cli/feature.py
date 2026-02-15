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

from guardkit.orchestrator.feature_loader import (
    FeatureLoader,
    FeatureNotFoundError,
    FeatureParseError,
)

console = Console()
logger = logging.getLogger(__name__)


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


def _output_human_errors(
    feature_id: str,
    schema_errors: List[str],
    structural_errors: List[str],
) -> None:
    """Print validation errors with red crosses."""
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
            console.print(f"  [red]\u2717[/red] {error}")


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
                feature_id, repo_root=repo_root
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
