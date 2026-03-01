"""
Configuration module for Graphiti knowledge graph integration.

Provides YAML-based configuration loading with environment variable overrides
and sensible defaults for graceful degradation when Graphiti is not available.

Configuration File: .guardkit/graphiti.yaml
Environment Variables:
    - GRAPHITI_ENABLED: Enable/disable Graphiti integration
    - NEO4J_URI: Neo4j Bolt URI (e.g., 'bolt://localhost:7687')
    - NEO4J_USER: Neo4j username
    - NEO4J_PASSWORD: Neo4j password
    - GRAPHITI_TIMEOUT: Connection timeout in seconds
    - GUARDKIT_CONFIG_DIR: Override config directory location
    - GRAPH_STORE: Graph database backend ('neo4j' or 'falkordb')
    - FALKORDB_HOST: FalkorDB host (default: 'localhost')
    - FALKORDB_PORT: FalkorDB port (default: 6379)
    - LLM_PROVIDER: LLM provider for entity extraction ('openai', 'vllm', 'ollama')
    - LLM_BASE_URL: LLM provider base URL (e.g., 'http://host:8000/v1')
    - LLM_MODEL: LLM model name (e.g., 'Qwen/Qwen3-Coder-30B-A3B')
    - EMBEDDING_PROVIDER: Embedding provider ('openai', 'vllm', 'ollama')
    - EMBEDDING_BASE_URL: Embedding provider base URL (e.g., 'http://host:8001/v1')

    # Deprecated (kept for backwards compatibility):
    - GRAPHITI_HOST: Deprecated - use NEO4J_URI instead
    - GRAPHITI_PORT: Deprecated - use NEO4J_URI instead
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
        neo4j_uri: Neo4j Bolt URI (e.g., 'bolt://localhost:7687')
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        timeout: Connection timeout in seconds
        embedding_model: Embedding model to use (provider-dependent)
        project_id: Project ID for namespace prefixing (optional)
        group_ids: Default group IDs for knowledge graph organization
        graph_store: Graph database backend ('neo4j' or 'falkordb')
        falkordb_host: FalkorDB host for connection
        falkordb_port: FalkorDB port for connection
        llm_provider: LLM provider for entity extraction ('openai', 'vllm', 'ollama')
        llm_base_url: LLM provider base URL (required for vllm/ollama)
        llm_model: LLM model name (required for vllm/ollama)
        embedding_provider: Embedding provider ('openai', 'vllm', 'ollama')
        embedding_base_url: Embedding provider base URL (required for vllm/ollama)
        host: Deprecated - use neo4j_uri instead
        port: Deprecated - use neo4j_uri instead

    Raises:
        ValueError: If timeout is not positive
        ValueError: If neo4j_uri is empty
        ValueError: If project_id is invalid (>50 chars)
        ValueError: If graph_store is not 'neo4j' or 'falkordb'
        ValueError: If llm_provider is not 'openai', 'vllm', or 'ollama'
        ValueError: If embedding_provider is not 'openai', 'vllm', or 'ollama'
        TypeError: If values have incorrect types
    """
    enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
    embedding_model: str = "text-embedding-3-small"
    project_id: Optional[str] = None  # Project ID for namespace prefixing
    group_ids: List[str] = field(default_factory=lambda: [
        "product_knowledge",
        "command_workflows",
        "architecture_decisions",
    ])
    graph_store: str = "neo4j"  # 'neo4j' or 'falkordb'
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379
    # LLM provider settings for entity extraction
    llm_provider: str = "openai"          # 'openai' | 'vllm' | 'ollama'
    llm_base_url: Optional[str] = None    # e.g., 'http://host:8000/v1'
    llm_model: Optional[str] = None       # e.g., 'Qwen/Qwen3-Coder-30B-A3B'
    # Embedding provider settings for vector search
    embedding_provider: str = "openai"    # 'openai' | 'vllm' | 'ollama'
    embedding_base_url: Optional[str] = None  # e.g., 'http://host:8001/v1'
    # Deprecated fields for backwards compatibility
    host: str = "localhost"
    port: int = 8000

    def __post_init__(self):
        """Validate settings after initialization."""
        # Type validation
        if not isinstance(self.enabled, bool):
            raise TypeError(f"enabled must be bool, got {type(self.enabled).__name__}")
        if not isinstance(self.neo4j_uri, str):
            raise TypeError(f"neo4j_uri must be str, got {type(self.neo4j_uri).__name__}")
        if not isinstance(self.neo4j_user, str):
            raise TypeError(f"neo4j_user must be str, got {type(self.neo4j_user).__name__}")
        if not isinstance(self.neo4j_password, str):
            raise TypeError(f"neo4j_password must be str, got {type(self.neo4j_password).__name__}")
        if not isinstance(self.timeout, (int, float)) or isinstance(self.timeout, bool):
            raise TypeError(f"timeout must be float, got {type(self.timeout).__name__}")
        if not isinstance(self.graph_store, str):
            raise TypeError(f"graph_store must be str, got {type(self.graph_store).__name__}")
        if not isinstance(self.falkordb_host, str):
            raise TypeError(f"falkordb_host must be str, got {type(self.falkordb_host).__name__}")
        if not isinstance(self.falkordb_port, int) or isinstance(self.falkordb_port, bool):
            raise TypeError(f"falkordb_port must be int, got {type(self.falkordb_port).__name__}")
        if not isinstance(self.host, str):
            raise TypeError(f"host must be str, got {type(self.host).__name__}")
        if not isinstance(self.port, int) or isinstance(self.port, bool):
            raise TypeError(f"port must be int, got {type(self.port).__name__}")
        if not isinstance(self.llm_provider, str):
            raise TypeError(f"llm_provider must be str, got {type(self.llm_provider).__name__}")
        if self.llm_base_url is not None and not isinstance(self.llm_base_url, str):
            raise TypeError(f"llm_base_url must be str or None, got {type(self.llm_base_url).__name__}")
        if self.llm_model is not None and not isinstance(self.llm_model, str):
            raise TypeError(f"llm_model must be str or None, got {type(self.llm_model).__name__}")
        if not isinstance(self.embedding_provider, str):
            raise TypeError(f"embedding_provider must be str, got {type(self.embedding_provider).__name__}")
        if self.embedding_base_url is not None and not isinstance(self.embedding_base_url, str):
            raise TypeError(f"embedding_base_url must be str or None, got {type(self.embedding_base_url).__name__}")

        # Convert timeout to float if int
        if isinstance(self.timeout, int):
            object.__setattr__(self, 'timeout', float(self.timeout))

        # Value validation
        if not self.neo4j_uri:
            raise ValueError("neo4j_uri cannot be empty")
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")
        if self.graph_store not in ("neo4j", "falkordb"):
            raise ValueError(f"graph_store must be 'neo4j' or 'falkordb', got '{self.graph_store}'")
        if self.falkordb_port < 1 or self.falkordb_port > 65535:
            raise ValueError(f"falkordb_port must be between 1 and 65535, got {self.falkordb_port}")
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        valid_providers = ("openai", "vllm", "ollama")
        if self.llm_provider not in valid_providers:
            raise ValueError(f"llm_provider must be one of {valid_providers}, got '{self.llm_provider}'")
        if self.embedding_provider not in valid_providers:
            raise ValueError(f"embedding_provider must be one of {valid_providers}, got '{self.embedding_provider}'")

        # Validate project_id if provided
        if self.project_id is not None and self.project_id != "":
            if not isinstance(self.project_id, str):
                raise TypeError(f"project_id must be str, got {type(self.project_id).__name__}")
            if len(self.project_id) > 50:
                raise ValueError(f"project_id must be <= 50 characters, got {len(self.project_id)}")
            # Validate format - only allow characters that normalize_project_id can handle
            # Reject characters that would be completely stripped (like @, #, etc.)
            import re
            if re.search(r'[@#$%^&*()+=\[\]{}|\\;:\'",.<>?/~`]', self.project_id):
                raise ValueError(f"project_id contains invalid characters: '{self.project_id}'")


def _find_project_root(start: Path) -> Optional[Path]:
    """Walk up from *start* looking for a directory containing .guardkit/.

    Similar to how git locates .git/ — this allows CLI commands to work
    when invoked from a subdirectory or even from outside the project
    (as long as the project is an ancestor of cwd).

    Args:
        start: Directory to begin the search from.

    Returns:
        The first ancestor directory (including *start* itself) that
        contains a ``.guardkit`` subdirectory, or None if not found.
    """
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".guardkit").is_dir():
            return parent
    return None


def get_config_path(base_dir: Optional[Path] = None) -> Path:
    """Get the path to graphiti.yaml configuration file.

    Resolution order:
    1. GUARDKIT_CONFIG_DIR environment variable (if set)
    2. Explicit *base_dir* argument
    3. Walk up from cwd looking for a .guardkit/ directory
    4. Fall back to cwd/.guardkit/graphiti.yaml (original behaviour)

    Args:
        base_dir: Base directory to use. If None, auto-detects by walking
                  up from cwd to find .guardkit/.

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

    # Use provided base_dir or auto-detect project root
    if base_dir is None:
        # Strategy 1: Walk up from cwd (works from subdirectories)
        project_root = _find_project_root(Path.cwd())
        if project_root is not None:
            base_dir = project_root
        else:
            # Strategy 2: Use guardkit package location (works from anywhere
            # when guardkit is installed as editable/development install)
            try:
                import guardkit as _pkg
                pkg_dir = Path(_pkg.__file__).resolve().parent.parent
                if (pkg_dir / ".guardkit").is_dir():
                    base_dir = pkg_dir
                else:
                    base_dir = Path.cwd()
            except Exception:
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
    1. Environment variables (NEO4J_URI, NEO4J_USER, etc.)
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
        'neo4j_uri': 'bolt://localhost:7687',
        'neo4j_user': 'neo4j',
        'neo4j_password': 'password123',
        'timeout': 30.0,
        'project_id': None,  # Project ID for namespace prefixing
        'graph_store': 'neo4j',
        'falkordb_host': 'localhost',
        'falkordb_port': 6379,
        'llm_provider': 'openai',
        'llm_base_url': None,
        'llm_model': None,
        'embedding_provider': 'openai',
        'embedding_base_url': None,
        'embedding_model': 'text-embedding-3-small',
        'host': 'localhost',  # Deprecated
        'port': 8000,  # Deprecated
    }

    # Try to load from YAML file
    if YAML_AVAILABLE and config_path.exists():
        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f)

            if yaml_data and isinstance(yaml_data, dict):
                # Merge YAML data, handling type coercion
                field_types = {
                    'enabled': bool,
                    'neo4j_uri': str,
                    'neo4j_user': str,
                    'neo4j_password': str,
                    'timeout': float,
                    'project_id': str,  # Project ID for namespace prefixing
                    'graph_store': str,
                    'falkordb_host': str,
                    'falkordb_port': int,
                    'llm_provider': str,
                    'llm_base_url': str,
                    'llm_model': str,
                    'embedding_provider': str,
                    'embedding_base_url': str,
                    'embedding_model': str,
                    'host': str,
                    'port': int,
                }
                optional_none_fields = {'project_id', 'llm_base_url', 'llm_model', 'embedding_base_url'}
                for key, target_type in field_types.items():
                    if key in yaml_data and yaml_data[key] is not None:
                        try:
                            value = _coerce_type(yaml_data[key], target_type, key)
                            # Treat empty string as None for Optional fields
                            if key in optional_none_fields and value == '':
                                value = None
                            config_data[key] = value
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
        logger.warning(
            f"Configuration file not found: {config_path}, using defaults. "
            f"Run this command from your project directory or set GUARDKIT_CONFIG_DIR."
        )

    # Apply environment variable overrides
    env_overrides = {
        'GRAPHITI_ENABLED': ('enabled', bool),
        'NEO4J_URI': ('neo4j_uri', str),
        'NEO4J_USER': ('neo4j_user', str),
        'NEO4J_PASSWORD': ('neo4j_password', str),
        'GRAPHITI_TIMEOUT': ('timeout', float),
        'GUARDKIT_PROJECT_ID': ('project_id', str),  # Project ID for namespace prefixing
        'GRAPH_STORE': ('graph_store', str),
        'FALKORDB_HOST': ('falkordb_host', str),
        'FALKORDB_PORT': ('falkordb_port', int),
        'LLM_PROVIDER': ('llm_provider', str),
        'LLM_BASE_URL': ('llm_base_url', str),
        'LLM_MODEL': ('llm_model', str),
        'EMBEDDING_PROVIDER': ('embedding_provider', str),
        'EMBEDDING_BASE_URL': ('embedding_base_url', str),
        'EMBEDDING_MODEL': ('embedding_model', str),
        # Deprecated env vars (kept for backwards compatibility)
        'GRAPHITI_HOST': ('host', str),
        'GRAPHITI_PORT': ('port', int),
    }

    optional_none_env_fields = {'project_id', 'llm_base_url', 'llm_model', 'embedding_base_url'}
    for env_var, (config_key, config_type) in env_overrides.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            try:
                value = _coerce_type(env_value, config_type, config_key)
                # Treat empty string as None for Optional fields
                if config_key in optional_none_env_fields and value == '':
                    value = None
                config_data[config_key] = value
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid environment variable {env_var}={env_value}: {e}")
                # Keep previous value (from file or default)

    # Create and return settings
    # Let ValueError propagate for truly invalid configuration (like invalid project_id)
    return GraphitiSettings(**config_data)
