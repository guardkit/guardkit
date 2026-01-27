"""Security Configuration Schema for AutoBuild Security Gate.

This module provides configuration classes for security validation during AutoBuild.
Supports task-level, feature-level, and global configuration with proper precedence.

Configuration Hierarchy (highest to lowest priority):
    1. Task frontmatter (task.security)
    2. Feature YAML (feature.security)
    3. Global config (.guardkit/config.yaml → autobuild.security)
    4. Environment variable (GUARDKIT_SECURITY_SKIP=1 → SKIP level)

Example:
    >>> from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
    >>>
    >>> # Default config
    >>> config = SecurityConfig()
    >>> config.level
    <SecurityLevel.STANDARD: 'standard'>
    >>>
    >>> # From task frontmatter
    >>> task = {"security": {"level": "strict", "force_full_review": True}}
    >>> config = SecurityConfig.from_task(task)
    >>> config.level
    <SecurityLevel.STRICT: 'strict'>
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class SecurityLevel(str, Enum):
    """Security validation level for AutoBuild tasks.

    Attributes:
        STRICT: Full security review, blocks on any finding
        STANDARD: Standard security checks with configurable thresholds
        MINIMAL: Quick security scan, non-blocking warnings
        SKIP: Skip all security validation
    """

    STRICT = "strict"
    STANDARD = "standard"
    MINIMAL = "minimal"
    SKIP = "skip"


# Default categories to exclude from security scans (too noisy for AutoBuild)
DEFAULT_EXCLUDE_CATEGORIES: List[str] = [
    "dos",
    "rate-limiting",
    "resource-management",
    "open-redirect",
]

# Default file patterns to exclude from security scans
DEFAULT_EXCLUDE_PATTERNS: List[str] = [
    "*.md",
    "*.test.*",
    "docs/**",
    "**/fixtures/**",
]


def load_global_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load global GuardKit configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to .guardkit/config.yaml

    Returns:
        Configuration dictionary, or empty dict if file doesn't exist
    """
    if config_path is None:
        config_path = Path(".guardkit/config.yaml")

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return {}


@dataclass
class SecurityConfig:
    """Security configuration for AutoBuild tasks.

    Supports parsing from task frontmatter, feature YAML, and global config
    with proper precedence rules (task > feature > global).

    Attributes:
        level: Security validation level (STRICT, STANDARD, MINIMAL, SKIP)
        skip_checks: List of specific check IDs to skip
        force_full_review: Force full security review even for simple changes
        quick_check_timeout: Timeout in seconds for quick security check
        full_review_timeout: Timeout in seconds for full security review
        block_on_critical: Block task if critical vulnerabilities found
        exclude_categories: Security categories to exclude from scans
        exclude_patterns: File patterns to exclude from scans
    """

    level: SecurityLevel = SecurityLevel.STANDARD
    skip_checks: List[str] = field(default_factory=list)
    force_full_review: bool = False
    quick_check_timeout: int = 30
    full_review_timeout: int = 300
    block_on_critical: bool = True
    exclude_categories: List[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDE_CATEGORIES.copy()
    )
    exclude_patterns: List[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDE_PATTERNS.copy()
    )

    @classmethod
    def from_task(cls, task: Dict[str, Any]) -> "SecurityConfig":
        """Create SecurityConfig from task frontmatter.

        Args:
            task: Task dictionary with optional 'security' section

        Returns:
            SecurityConfig parsed from task, or defaults if no security section
        """
        security = task.get("security", {})
        if not security:
            return cls()

        return cls._parse_config(security)

    @classmethod
    def from_feature(cls, feature: Dict[str, Any], task_id: str) -> "SecurityConfig":
        """Create SecurityConfig from feature YAML.

        Args:
            feature: Feature dictionary with optional 'security' section
            task_id: Current task ID (used for force_full_review list check)

        Returns:
            SecurityConfig parsed from feature, or defaults if no security section
        """
        security = feature.get("security", {})
        if not security:
            return cls()

        config = cls._parse_config(security)

        # Handle force_full_review as list of task IDs
        force_full = security.get("force_full_review")
        if isinstance(force_full, list):
            config.force_full_review = task_id in force_full
        elif isinstance(force_full, bool):
            config.force_full_review = force_full

        return config

    @classmethod
    def from_global(cls, config_path: Optional[Path] = None) -> "SecurityConfig":
        """Create SecurityConfig from global config file.

        Checks GUARDKIT_SECURITY_SKIP env var first (if "1", returns SKIP level).
        Then loads from .guardkit/config.yaml if exists.

        Args:
            config_path: Optional path to config file

        Returns:
            SecurityConfig from global config, or defaults
        """
        # Check environment variable first
        if os.environ.get("GUARDKIT_SECURITY_SKIP") == "1":
            return cls(level=SecurityLevel.SKIP)

        # Load global config
        global_config = load_global_config(config_path)
        security = global_config.get("autobuild", {}).get("security", {})

        if not security:
            return cls()

        return cls._parse_config(security)

    @classmethod
    def merge(
        cls,
        task_config: Optional["SecurityConfig"],
        feature_config: Optional["SecurityConfig"],
        global_config: Optional["SecurityConfig"],
    ) -> "SecurityConfig":
        """Merge configurations with precedence: task > feature > global.

        For scalar values, uses first non-default value in precedence order.
        For lists (exclude_categories, exclude_patterns), concatenates unique values.

        Args:
            task_config: Task-level config (highest priority)
            feature_config: Feature-level config
            global_config: Global config (lowest priority)

        Returns:
            Merged SecurityConfig
        """
        default = cls()
        configs = [
            c for c in [task_config, feature_config, global_config] if c is not None
        ]

        if not configs:
            return default

        # Build merged config
        merged = cls()

        # Scalar fields: use first non-default value
        for config in configs:
            if config.level != default.level and merged.level == default.level:
                merged.level = config.level

            if config.skip_checks and not merged.skip_checks:
                merged.skip_checks = config.skip_checks.copy()

            if config.force_full_review and not merged.force_full_review:
                merged.force_full_review = config.force_full_review

            if (
                config.quick_check_timeout != default.quick_check_timeout
                and merged.quick_check_timeout == default.quick_check_timeout
            ):
                merged.quick_check_timeout = config.quick_check_timeout

            if (
                config.full_review_timeout != default.full_review_timeout
                and merged.full_review_timeout == default.full_review_timeout
            ):
                merged.full_review_timeout = config.full_review_timeout

            if (
                config.block_on_critical != default.block_on_critical
                and merged.block_on_critical == default.block_on_critical
            ):
                merged.block_on_critical = config.block_on_critical

        # List fields: concatenate unique values from all configs
        all_categories: List[str] = []
        all_patterns: List[str] = []

        for config in configs:
            for cat in config.exclude_categories:
                if cat not in all_categories:
                    all_categories.append(cat)
            for pat in config.exclude_patterns:
                if pat not in all_patterns:
                    all_patterns.append(pat)

        merged.exclude_categories = all_categories
        merged.exclude_patterns = all_patterns

        return merged

    @classmethod
    def _parse_config(cls, security: Dict[str, Any]) -> "SecurityConfig":
        """Parse security section into SecurityConfig.

        Args:
            security: Security configuration dictionary

        Returns:
            Parsed SecurityConfig
        """
        # Parse level
        level_value = security.get("level", SecurityLevel.STANDARD)
        if isinstance(level_value, str):
            level = SecurityLevel(level_value)
        elif isinstance(level_value, SecurityLevel):
            level = level_value
        else:
            level = SecurityLevel.STANDARD

        # Parse other fields with defaults
        return cls(
            level=level,
            skip_checks=security.get("skip_checks", []),
            force_full_review=security.get("force_full_review", False),
            quick_check_timeout=security.get("quick_check_timeout", 30),
            full_review_timeout=security.get("full_review_timeout", 300),
            block_on_critical=security.get("block_on_critical", True),
            exclude_categories=security.get(
                "exclude_categories", DEFAULT_EXCLUDE_CATEGORIES.copy()
            ),
            exclude_patterns=security.get(
                "exclude_patterns", DEFAULT_EXCLUDE_PATTERNS.copy()
            ),
        )


__all__ = [
    "SecurityLevel",
    "SecurityConfig",
    "DEFAULT_EXCLUDE_CATEGORIES",
    "DEFAULT_EXCLUDE_PATTERNS",
    "load_global_config",
]
