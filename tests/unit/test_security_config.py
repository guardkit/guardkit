"""
TDD RED PHASE: Failing tests for Security Configuration Schema (TASK-SEC-002)

These tests verify:
1. SecurityLevel enum values
2. SecurityConfig dataclass defaults
3. Parsing from task frontmatter
4. Parsing from feature YAML
5. Parsing from global config
6. Configuration merging with precedence (task > feature > global)
7. Default exclude categories and patterns
8. Environment variable override (GUARDKIT_SECURITY_SKIP)

All tests should FAIL initially since the implementation doesn't exist yet.
"""

import os
import pytest
from unittest.mock import patch

# These imports will fail initially - expected in RED phase
from guardkit.orchestrator.security_config import (
    SecurityConfig,
    SecurityLevel,
    DEFAULT_EXCLUDE_CATEGORIES,
    DEFAULT_EXCLUDE_PATTERNS,
)


class TestSecurityLevelEnum:
    """Test SecurityLevel enum values."""

    def test_security_level_enum_values(self):
        """All 4 security levels should exist."""
        assert hasattr(SecurityLevel, 'STRICT')
        assert hasattr(SecurityLevel, 'STANDARD')
        assert hasattr(SecurityLevel, 'MINIMAL')
        assert hasattr(SecurityLevel, 'SKIP')

        assert SecurityLevel.STRICT.value == "strict"
        assert SecurityLevel.STANDARD.value == "standard"
        assert SecurityLevel.MINIMAL.value == "minimal"
        assert SecurityLevel.SKIP.value == "skip"

    def test_security_level_invalid_value(self):
        """Creating SecurityLevel with invalid value should raise error."""
        with pytest.raises((ValueError, KeyError)):
            # Attempt to get invalid level
            SecurityLevel("invalid")


class TestSecurityConfigDefaults:
    """Test SecurityConfig default values."""

    def test_security_config_default_values(self):
        """SecurityConfig should have correct default values."""
        config = SecurityConfig()

        assert config.level == SecurityLevel.STANDARD
        assert config.skip_checks == []
        assert config.force_full_review is False
        assert config.quick_check_timeout == 30
        assert config.full_review_timeout == 300
        assert config.block_on_critical is True
        assert isinstance(config.exclude_categories, list)
        assert isinstance(config.exclude_patterns, list)

    def test_security_config_default_exclude_categories(self):
        """Default exclude categories should include DOS, rate-limiting, resource-management, open-redirect."""
        config = SecurityConfig()

        assert "dos" in config.exclude_categories
        assert "rate-limiting" in config.exclude_categories
        assert "resource-management" in config.exclude_categories
        assert "open-redirect" in config.exclude_categories

        # Verify constant matches
        assert config.exclude_categories == DEFAULT_EXCLUDE_CATEGORIES

    def test_security_config_default_exclude_patterns(self):
        """Default exclude patterns should include *.md, *.test.*, docs/**, **/fixtures/**."""
        config = SecurityConfig()

        assert "*.md" in config.exclude_patterns
        assert "*.test.*" in config.exclude_patterns
        assert "docs/**" in config.exclude_patterns
        assert "**/fixtures/**" in config.exclude_patterns

        # Verify constant matches
        assert config.exclude_patterns == DEFAULT_EXCLUDE_PATTERNS

    def test_default_values_are_independent_instances(self):
        """Each SecurityConfig instance should have independent default lists."""
        config1 = SecurityConfig()
        config2 = SecurityConfig()

        # Modify config1's lists
        config1.exclude_categories.append("test-category")
        config1.exclude_patterns.append("test-pattern")

        # config2 should not be affected
        assert "test-category" not in config2.exclude_categories
        assert "test-pattern" not in config2.exclude_patterns


class TestSecurityConfigFromTask:
    """Test parsing SecurityConfig from task frontmatter."""

    def test_security_config_from_task_empty(self):
        """Empty task dict should return default config."""
        task = {}
        config = SecurityConfig.from_task(task)

        assert config.level == SecurityLevel.STANDARD
        assert config.skip_checks == []
        assert config.force_full_review is False

    def test_security_config_from_task_missing_security_section(self):
        """Task without security section should return default config."""
        task = {
            "task_id": "TASK-001",
            "title": "Test task"
        }
        config = SecurityConfig.from_task(task)

        assert config.level == SecurityLevel.STANDARD
        assert config.skip_checks == []

    def test_security_config_from_task_full(self):
        """Task with full security config should parse all fields."""
        task = {
            "task_id": "TASK-001",
            "security": {
                "level": "strict",
                "skip_checks": ["check1", "check2"],
                "force_full_review": True,
                "quick_check_timeout": 60,
                "full_review_timeout": 600,
                "block_on_critical": False,
                "exclude_categories": ["custom-category"],
                "exclude_patterns": ["*.tmp"]
            }
        }
        config = SecurityConfig.from_task(task)

        assert config.level == SecurityLevel.STRICT
        assert config.skip_checks == ["check1", "check2"]
        assert config.force_full_review is True
        assert config.quick_check_timeout == 60
        assert config.full_review_timeout == 600
        assert config.block_on_critical is False
        assert config.exclude_categories == ["custom-category"]
        assert config.exclude_patterns == ["*.tmp"]

    def test_security_config_from_task_partial(self):
        """Task with partial security config should use defaults for missing fields."""
        task = {
            "security": {
                "level": "minimal",
                "skip_checks": ["test-check"]
            }
        }
        config = SecurityConfig.from_task(task)

        assert config.level == SecurityLevel.MINIMAL
        assert config.skip_checks == ["test-check"]
        # Rest should be defaults
        assert config.force_full_review is False
        assert config.quick_check_timeout == 30
        assert config.block_on_critical is True

    def test_security_config_from_task_level_as_enum(self):
        """Task can specify level as SecurityLevel enum instance."""
        task = {
            "security": {
                "level": SecurityLevel.SKIP
            }
        }
        config = SecurityConfig.from_task(task)

        assert config.level == SecurityLevel.SKIP


class TestSecurityConfigFromFeature:
    """Test parsing SecurityConfig from feature YAML."""

    def test_security_config_from_feature_empty(self):
        """Empty feature dict should return default config."""
        feature = {}
        config = SecurityConfig.from_feature(feature, "TASK-001")

        assert config.level == SecurityLevel.STANDARD
        assert config.force_full_review is False

    def test_security_config_from_feature_full(self):
        """Feature with full security config should parse all fields."""
        feature = {
            "security": {
                "level": "minimal",
                "skip_checks": ["feature-check"],
                "force_full_review": ["TASK-001", "TASK-002"],
                "quick_check_timeout": 45,
                "exclude_categories": ["feature-category"],
                "exclude_patterns": ["*.ignore"]
            }
        }
        config = SecurityConfig.from_feature(feature, "TASK-003")

        assert config.level == SecurityLevel.MINIMAL
        assert config.skip_checks == ["feature-check"]
        assert config.force_full_review is False  # TASK-003 not in list
        assert config.quick_check_timeout == 45
        assert config.exclude_categories == ["feature-category"]
        assert config.exclude_patterns == ["*.ignore"]

    def test_security_config_from_feature_force_full_review_list(self):
        """When task_id is in force_full_review list, force_full_review should be True."""
        feature = {
            "security": {
                "level": "standard",
                "force_full_review": ["TASK-001", "TASK-002", "TASK-003"]
            }
        }
        config = SecurityConfig.from_feature(feature, "TASK-002")

        assert config.force_full_review is True

    def test_security_config_from_feature_force_full_review_boolean(self):
        """Feature can specify force_full_review as boolean for all tasks."""
        feature = {
            "security": {
                "force_full_review": True
            }
        }
        config = SecurityConfig.from_feature(feature, "TASK-001")

        assert config.force_full_review is True

    def test_security_config_from_feature_partial(self):
        """Feature with partial config should use defaults for missing fields."""
        feature = {
            "security": {
                "level": "strict"
            }
        }
        config = SecurityConfig.from_feature(feature, "TASK-001")

        assert config.level == SecurityLevel.STRICT
        assert config.skip_checks == []
        assert config.quick_check_timeout == 30


class TestSecurityConfigFromGlobal:
    """Test parsing SecurityConfig from global autobuild.security config."""

    def test_security_config_from_global_empty(self):
        """No global config file should return default config."""
        with patch('os.path.exists', return_value=False):
            config = SecurityConfig.from_global()

        assert config.level == SecurityLevel.STANDARD
        assert config.skip_checks == []

    def test_security_config_from_global_full(self):
        """Global config with full security section should parse all fields."""
        global_config = {
            "autobuild": {
                "security": {
                    "level": "minimal",
                    "skip_checks": ["global-check"],
                    "quick_check_timeout": 120,
                    "full_review_timeout": 900,
                    "block_on_critical": False,
                    "exclude_categories": ["global-category"],
                    "exclude_patterns": ["*.bak"]
                }
            }
        }

        with patch('guardkit.orchestrator.security_config.load_global_config', return_value=global_config):
            config = SecurityConfig.from_global()

        assert config.level == SecurityLevel.MINIMAL
        assert config.skip_checks == ["global-check"]
        assert config.quick_check_timeout == 120
        assert config.full_review_timeout == 900
        assert config.block_on_critical is False
        assert config.exclude_categories == ["global-category"]
        assert config.exclude_patterns == ["*.bak"]

    def test_security_config_from_global_env_skip(self):
        """GUARDKIT_SECURITY_SKIP=1 environment variable should set level to SKIP."""
        with patch.dict(os.environ, {'GUARDKIT_SECURITY_SKIP': '1'}):
            config = SecurityConfig.from_global()

        assert config.level == SecurityLevel.SKIP

    def test_security_config_from_global_env_skip_precedence(self):
        """GUARDKIT_SECURITY_SKIP should override global config level."""
        global_config = {
            "autobuild": {
                "security": {
                    "level": "strict"
                }
            }
        }

        with patch('guardkit.orchestrator.security_config.load_global_config', return_value=global_config):
            with patch.dict(os.environ, {'GUARDKIT_SECURITY_SKIP': '1'}):
                config = SecurityConfig.from_global()

        assert config.level == SecurityLevel.SKIP

    def test_security_config_from_global_partial(self):
        """Global config with partial security section should use defaults."""
        global_config = {
            "autobuild": {
                "security": {
                    "level": "strict",
                    "block_on_critical": False
                }
            }
        }

        with patch('guardkit.orchestrator.security_config.load_global_config', return_value=global_config):
            config = SecurityConfig.from_global()

        assert config.level == SecurityLevel.STRICT
        assert config.block_on_critical is False
        # Defaults for other fields
        assert config.skip_checks == []
        assert config.quick_check_timeout == 30


class TestSecurityConfigMerge:
    """Test merging SecurityConfig with correct precedence (task > feature > global)."""

    def test_security_config_merge_precedence(self):
        """Task config should override feature, feature should override global."""
        task_config = SecurityConfig(
            level=SecurityLevel.STRICT,
            skip_checks=["task-check"],
            quick_check_timeout=100
        )
        feature_config = SecurityConfig(
            level=SecurityLevel.MINIMAL,
            skip_checks=["feature-check"],
            quick_check_timeout=50,
            full_review_timeout=500
        )
        global_config = SecurityConfig(
            level=SecurityLevel.STANDARD,
            skip_checks=["global-check"],
            quick_check_timeout=30,
            full_review_timeout=300,
            block_on_critical=False
        )

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        # Task overrides feature and global
        assert merged.level == SecurityLevel.STRICT
        assert merged.skip_checks == ["task-check"]
        assert merged.quick_check_timeout == 100

        # Feature overrides global (task didn't specify)
        assert merged.full_review_timeout == 500

        # Global default (neither task nor feature specified)
        assert merged.block_on_critical is False

    def test_security_config_merge_partial_configs(self):
        """Merge should handle partial configs correctly."""
        task_config = SecurityConfig(level=SecurityLevel.SKIP)
        feature_config = SecurityConfig(
            skip_checks=["feature-check"],
            force_full_review=True
        )
        global_config = SecurityConfig(block_on_critical=False)

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        assert merged.level == SecurityLevel.SKIP  # From task
        assert merged.skip_checks == ["feature-check"]  # From feature
        assert merged.force_full_review is True  # From feature
        assert merged.block_on_critical is False  # From global

    def test_security_config_merge_skip_level_shortcuts(self):
        """When level is SKIP, merge should skip all checks."""
        task_config = SecurityConfig(level=SecurityLevel.SKIP)
        feature_config = SecurityConfig(
            level=SecurityLevel.STRICT,
            force_full_review=True,
            block_on_critical=True
        )
        global_config = SecurityConfig(level=SecurityLevel.STANDARD)

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        # SKIP level from task overrides everything
        assert merged.level == SecurityLevel.SKIP

    def test_security_config_merge_exclude_categories_concat(self):
        """Exclude categories should be concatenated from all levels."""
        task_config = SecurityConfig(exclude_categories=["task-cat"])
        feature_config = SecurityConfig(exclude_categories=["feature-cat"])
        global_config = SecurityConfig(exclude_categories=["global-cat"])

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        # Should contain all unique categories
        assert "task-cat" in merged.exclude_categories
        assert "feature-cat" in merged.exclude_categories
        assert "global-cat" in merged.exclude_categories

    def test_security_config_merge_exclude_patterns_concat(self):
        """Exclude patterns should be concatenated from all levels."""
        task_config = SecurityConfig(exclude_patterns=["*.task"])
        feature_config = SecurityConfig(exclude_patterns=["*.feature"])
        global_config = SecurityConfig(exclude_patterns=["*.global"])

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        # Should contain all unique patterns
        assert "*.task" in merged.exclude_patterns
        assert "*.feature" in merged.exclude_patterns
        assert "*.global" in merged.exclude_patterns

    def test_security_config_merge_empty_configs(self):
        """Merging all default configs should return default config."""
        task_config = SecurityConfig()
        feature_config = SecurityConfig()
        global_config = SecurityConfig()

        merged = SecurityConfig.merge(task_config, feature_config, global_config)

        assert merged.level == SecurityLevel.STANDARD
        assert merged.skip_checks == []
        assert merged.force_full_review is False
        assert merged.quick_check_timeout == 30
        assert merged.full_review_timeout == 300
        assert merged.block_on_critical is True

    def test_security_config_merge_none_handling(self):
        """Merge should handle None configs gracefully."""
        task_config = SecurityConfig(level=SecurityLevel.STRICT)

        merged = SecurityConfig.merge(task_config, None, None)

        assert merged.level == SecurityLevel.STRICT
        # Should use defaults for other fields
        assert merged.skip_checks == []
        assert merged.quick_check_timeout == 30


class TestSecurityConfigIntegration:
    """Integration tests for complete SecurityConfig workflow."""

    def test_full_config_chain_task_overrides(self):
        """Complete workflow: task metadata overrides feature and global."""
        # Global config
        global_config = {
            "autobuild": {
                "security": {
                    "level": "standard",
                    "block_on_critical": True,
                    "exclude_categories": ["dos"]
                }
            }
        }

        # Feature config
        feature = {
            "security": {
                "level": "minimal",
                "force_full_review": ["TASK-001"],
                "exclude_categories": ["rate-limiting"]
            }
        }

        # Task config
        task = {
            "task_id": "TASK-001",
            "security": {
                "level": "strict",
                "exclude_categories": ["custom"]
            }
        }

        with patch('guardkit.orchestrator.security_config.load_global_config', return_value=global_config):
            global_cfg = SecurityConfig.from_global()
            feature_cfg = SecurityConfig.from_feature(feature, "TASK-001")
            task_cfg = SecurityConfig.from_task(task)

            final_config = SecurityConfig.merge(task_cfg, feature_cfg, global_cfg)

        # Task level wins
        assert final_config.level == SecurityLevel.STRICT

        # Feature force_full_review applies
        assert final_config.force_full_review is True

        # Global block_on_critical applies (not overridden)
        assert final_config.block_on_critical is True

        # Exclude categories concatenated
        assert "custom" in final_config.exclude_categories
        assert "rate-limiting" in final_config.exclude_categories
        assert "dos" in final_config.exclude_categories

    def test_env_var_override_entire_chain(self):
        """GUARDKIT_SECURITY_SKIP environment variable should override everything."""
        feature = {
            "security": {
                "level": "strict",
                "force_full_review": True
            }
        }

        task = {
            "security": {
                "level": "strict"
            }
        }

        with patch.dict(os.environ, {'GUARDKIT_SECURITY_SKIP': '1'}):
            global_cfg = SecurityConfig.from_global()
            feature_cfg = SecurityConfig.from_feature(feature, "TASK-001")
            task_cfg = SecurityConfig.from_task(task)

            final_config = SecurityConfig.merge(task_cfg, feature_cfg, global_cfg)

        # Global env var sets SKIP level
        assert global_cfg.level == SecurityLevel.SKIP

        # But task still has STRICT
        assert task_cfg.level == SecurityLevel.STRICT

        # Final merge: task wins (STRICT > SKIP in precedence)
        assert final_config.level == SecurityLevel.STRICT
