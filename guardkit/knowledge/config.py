"""
Configuration module for Graphiti knowledge graph integration.

Provides YAML-based configuration loading with environment variable overrides
and sensible defaults for graceful degradation when Graphiti is not available.

Configuration File: .guardkit/graphiti.yaml
Environment Variables:
    - GRAPHITI_ENABLED: Enable/disable Graphiti integration
    - GRAPHITI_HOST: Graphiti server host
    - GRAPHITI_PORT: Graphiti server port
    - GRAPHITI_TIMEOUT: Connection timeout in seconds
    - GUARDKIT_CONFIG_DIR: Override config directory location
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import os
import logging

logger = logging.getLogger(__name__)

# Attempt to import yaml, gracefully handle if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed, using default configuration")


@dataclass
class GraphitiSettings:
    """Configuration for Graphiti connection loaded from YAML.

    Attributes:
        enabled: Whether Graphiti integration is enabled
        host: Graphiti server hostname
        port: Graphiti server port
        timeout: Connection timeout in seconds
        embedding_model: OpenAI embedding model to use
        group_ids: Default group IDs for knowledge graph organization

    Raises:
        ValueError: If port is out of valid range (1-65535)
        ValueError: If timeout is not positive
        ValueError: If host is empty
        TypeError: If values have incorrect types
    """
    enabled: bool = True
    host: str = "localhost"
    port: int = 8000
    timeout: float = 30.0
    embedding_model: str = "text-embedding-3-small"
    group_ids: List[str] = field(default_factory=lambda: [
        "product_knowledge",
        "command_workflows",
        "architecture_decisions",
    ])

    def __post_init__(self):
        """Validate settings after initialization."""
        # Type validation
        if not isinstance(self.enabled, bool):
            raise TypeError(f"enabled must be bool, got {type(self.enabled).__name__}")
        if not isinstance(self.host, str):
            raise TypeError(f"host must be str, got {type(self.host).__name__}")
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise TypeError(f"port must be int, got {type(self.port).__name__}")
        if not isinstance(self.timeout, (int, float)) or isinstance(self.timeout, bool):
            raise TypeError(f"timeout must be float, got {type(self.timeout).__name__}")

        # Convert timeout to float if int
        if isinstance(self.timeout, int):
            object.__setattr__(self, 'timeout', float(self.timeout))

        # Value validation
        if not self.host:
            raise ValueError("host cannot be empty")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")


def get_config_path(base_dir: Optional[Path] = None) -> Path:
    """Get the path to graphiti.yaml configuration file.

    Args:
        base_dir: Base directory to use. Defaults to current working directory.
                  If provided, constructs path as base_dir/.guardkit/graphiti.yaml

    Returns:
        Path to the graphiti.yaml configuration file.

    Examples:
        >>> get_config_path()
        PosixPath('/current/dir/.guardkit/graphiti.yaml')

        >>> get_config_path(Path('/project'))
        PosixPath('/project/.guardkit/graphiti.yaml')
    """
    # Check GUARDKIT_CONFIG_DIR env var first
    config_dir_env = os.environ.get("GUARDKIT_CONFIG_DIR")
    if config_dir_env:
        return Path(config_dir_env) / "graphiti.yaml"

    # Use provided base_dir or current working directory
    if base_dir is None:
        base_dir = Path.cwd()

    return base_dir / ".guardkit" / "graphiti.yaml"


def _parse_bool(value: str) -> bool:
    """Parse a string value to boolean.

    Args:
        value: String value to parse

    Returns:
        True for 'true', '1', 'yes', 'on' (case-insensitive)
        False for 'false', '0', 'no', 'off' (case-insensitive)

    Raises:
        ValueError: If value cannot be parsed as boolean
    """
    value_lower = value.lower().strip()
    if value_lower in ('true', '1', 'yes', 'on'):
        return True
    elif value_lower in ('false', '0', 'no', 'off'):
        return False
    else:
        raise ValueError(f"Cannot parse '{value}' as boolean")


def _coerce_type(value, target_type: type, field_name: str):
    """Coerce a value to the target type with validation.

    Args:
        value: Value to coerce
        target_type: Target type (bool, int, float, str)
        field_name: Field name for error messages

    Returns:
        Coerced value

    Raises:
        ValueError: If coercion fails
    """
    if value is None:
        return None

    if target_type == bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return _parse_bool(value)
        raise ValueError(f"Cannot coerce {type(value).__name__} to bool for {field_name}")

    if target_type == int:
        if isinstance(value, bool):
            raise ValueError(f"Cannot coerce bool to int for {field_name}")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value)
        raise ValueError(f"Cannot coerce {type(value).__name__} to int for {field_name}")

    if target_type == float:
        if isinstance(value, bool):
            raise ValueError(f"Cannot coerce bool to float for {field_name}")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value)
        raise ValueError(f"Cannot coerce {type(value).__name__} to float for {field_name}")

    if target_type == str:
        return str(value)

    return value


def load_graphiti_config(config_path: Optional[Path] = None) -> GraphitiSettings:
    """Load Graphiti configuration from YAML file.

    Configuration priority (highest to lowest):
    1. Environment variables (GRAPHITI_ENABLED, GRAPHITI_HOST, etc.)
    2. YAML configuration file
    3. Default values

    Args:
        config_path: Path to configuration file. If None, uses get_config_path().

    Returns:
        GraphitiSettings instance with loaded or default configuration.

    Note:
        Returns default settings if:
        - Configuration file not found
        - YAML parsing fails
        - Permission denied
        - PyYAML not installed
    """
    if config_path is None:
        config_path = get_config_path()

    # Start with default values
    config_data = {
        'enabled': True,
        'host': 'localhost',
        'port': 8000,
        'timeout': 30.0,
    }

    # Try to load from YAML file
    if YAML_AVAILABLE and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            if yaml_data and isinstance(yaml_data, dict):
                # Merge YAML data, handling type coercion
                for key in ['enabled', 'host', 'port', 'timeout']:
                    if key in yaml_data and yaml_data[key] is not None:
                        try:
                            if key == 'enabled':
                                config_data[key] = _coerce_type(yaml_data[key], bool, key)
                            elif key == 'host':
                                config_data[key] = _coerce_type(yaml_data[key], str, key)
                            elif key == 'port':
                                config_data[key] = _coerce_type(yaml_data[key], int, key)
                            elif key == 'timeout':
                                config_data[key] = _coerce_type(yaml_data[key], float, key)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid value for {key} in config file: {e}")
                            # Keep default value

        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML configuration: {e}")
        except PermissionError as e:
            logger.warning(f"Permission denied reading configuration: {e}")
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}")
    elif not config_path.exists():
        logger.debug(f"Configuration file not found: {config_path}, using defaults")

    # Apply environment variable overrides
    env_overrides = {
        'GRAPHITI_ENABLED': ('enabled', bool),
        'GRAPHITI_HOST': ('host', str),
        'GRAPHITI_PORT': ('port', int),
        'GRAPHITI_TIMEOUT': ('timeout', float),
    }

    for env_var, (config_key, config_type) in env_overrides.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            try:
                config_data[config_key] = _coerce_type(env_value, config_type, config_key)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid environment variable {env_var}={env_value}: {e}")
                # Keep previous value (from file or default)

    # Create and return settings
    try:
        return GraphitiSettings(**config_data)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid configuration, using defaults: {e}")
        return GraphitiSettings()
