"""
Target mode configuration for GuardKit planning.

Provides target mode resolution for determining output configuration
based on whether the target is an interactive human user or a local model.

Coverage Target: >=85%
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class TargetMode(Enum):
    """Target mode for planning output configuration."""

    INTERACTIVE = "interactive"
    LOCAL_MODEL = "local-model"
    AUTO = "auto"


@dataclass
class TargetConfig:
    """Configuration for target mode output settings.

    Attributes:
        mode: The resolved target mode.
        model_name: Optional model name from config.
        output_verbosity: Output verbosity level ("standard" or "explicit").
        include_imports: Whether to include import statements.
        include_type_hints: Whether to include type hints.
        structured_coach_blocks: Whether to use structured coach blocks.
    """

    mode: TargetMode
    model_name: Optional[str] = None
    output_verbosity: str = "standard"
    include_imports: bool = False
    include_type_hints: bool = False
    structured_coach_blocks: bool = False


def _create_local_model_config(model_name: Optional[str] = None) -> TargetConfig:
    """Create a TargetConfig for LOCAL_MODEL mode.

    Args:
        model_name: Optional model name to include.

    Returns:
        TargetConfig configured for local model usage.
    """
    return TargetConfig(
        mode=TargetMode.LOCAL_MODEL,
        model_name=model_name,
        output_verbosity="explicit",
        include_imports=True,
        include_type_hints=True,
        structured_coach_blocks=True,
    )


def _create_interactive_config() -> TargetConfig:
    """Create a TargetConfig for INTERACTIVE mode.

    Returns:
        TargetConfig configured for interactive usage.
    """
    return TargetConfig(
        mode=TargetMode.INTERACTIVE,
        model_name=None,
        output_verbosity="standard",
        include_imports=False,
        include_type_hints=False,
        structured_coach_blocks=False,
    )


def _read_config_file(config_path: Path) -> Optional[dict]:
    """Read and parse a YAML config file.

    Args:
        config_path: Path to the config file.

    Returns:
        Parsed config dict or None if file cannot be read/parsed.
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path) as f:
            content = yaml.safe_load(f)
            return content if isinstance(content, dict) else None
    except (yaml.YAMLError, PermissionError, OSError):
        return None


def _resolve_auto_mode(config_path: Path) -> TargetConfig:
    """Resolve AUTO mode by checking config file for autobuild.endpoint.

    Args:
        config_path: Path to the config file.

    Returns:
        TargetConfig resolved to either LOCAL_MODEL or INTERACTIVE.
    """
    config = _read_config_file(config_path)

    if config is None:
        return _create_interactive_config()

    autobuild = config.get("autobuild")
    if not isinstance(autobuild, dict):
        return _create_interactive_config()

    endpoint = autobuild.get("endpoint")
    if endpoint is None:
        return _create_interactive_config()

    # Endpoint exists and is not null - resolve to LOCAL_MODEL
    model_name = autobuild.get("model")
    return _create_local_model_config(model_name=model_name)


def resolve_target(
    flag_value: Optional[str] = None,
    config_path: Path = Path(".guardkit/config.yaml"),
) -> TargetConfig:
    """Resolve target mode from flag or config file.

    Args:
        flag_value: Optional flag value ("interactive", "local-model", "auto").
                   Case-insensitive. None defaults to AUTO behavior.
        config_path: Path to config file for AUTO mode resolution.

    Returns:
        TargetConfig with appropriate settings for the resolved mode.

    Raises:
        ValueError: If flag_value is invalid (not one of the valid modes).
    """
    # Handle None as AUTO mode
    if flag_value is None:
        return _resolve_auto_mode(config_path)

    # Normalize flag value to lowercase
    normalized = flag_value.lower()

    # Handle empty string as invalid
    if normalized == "":
        raise ValueError("Invalid target mode: ")

    # Match against valid modes
    if normalized == "interactive":
        return _create_interactive_config()
    elif normalized == "local-model":
        return _create_local_model_config()
    elif normalized == "auto":
        return _resolve_auto_mode(config_path)
    else:
        raise ValueError(f"Invalid target mode: {flag_value}")
