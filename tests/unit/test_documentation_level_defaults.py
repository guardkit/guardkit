"""
Unit tests for documentation level default behavior.

TASK-FB-FIX-018: Default documentation level to minimal, lift only on explicit flag.

Tests verify that:
1. Default is always 'minimal' regardless of complexity
2. Explicit flags (--docs=standard, --docs=comprehensive) override default
3. Settings.json default still works
4. Force-comprehensive triggers still work
5. Complexity no longer affects documentation level selection
"""

import pytest
from typing import Dict, Any, Optional


def determine_documentation_level(
    docs_flag: Optional[str],
    task_context: Dict[str, Any],
    settings_default_level: str = "auto",
    force_triggers: Optional[Dict[str, list]] = None
) -> tuple[str, str]:
    """
    Determine documentation level based on configuration hierarchy.

    This mirrors the logic in task-work.md Step 2.5.

    Configuration hierarchy (highest to lowest priority):
    1. Command-line flag (--docs=minimal|standard|comprehensive)
    2. Force-comprehensive triggers (security, compliance, breaking changes)
    3. Settings.json default
    4. Default: minimal (use --docs=standard to lift)

    Args:
        docs_flag: Value of --docs flag if provided
        task_context: Task context with title, description, complexity
        settings_default_level: Default level from settings.json
        force_triggers: Dict with security_keywords, compliance_keywords, breaking_changes

    Returns:
        Tuple of (documentation_level, reason)
    """
    if force_triggers is None:
        force_triggers = {}

    # Check force-comprehensive triggers
    task_text = (
        task_context.get("title", "") + " " +
        task_context.get("description", "")
    ).lower()

    security_keywords = force_triggers.get(
        "security_keywords",
        ["auth", "password", "encryption", "security"]
    )
    compliance_keywords = force_triggers.get(
        "compliance_keywords",
        ["gdpr", "hipaa", "compliance", "audit"]
    )
    breaking_keywords = force_triggers.get(
        "breaking_changes",
        ["breaking", "migration", "deprecated"]
    )

    force_comprehensive = (
        any(kw in task_text for kw in security_keywords) or
        any(kw in task_text for kw in compliance_keywords) or
        any(kw in task_text for kw in breaking_keywords)
    )

    documentation_level = None
    reason = None

    # Priority 1: Command-line flag (highest)
    if docs_flag:
        documentation_level = docs_flag
        reason = f"explicit flag (--docs={docs_flag})"

    # Priority 2: Force-comprehensive triggers
    elif force_comprehensive:
        documentation_level = "comprehensive"
        reason = "force trigger (security/compliance/breaking keywords)"

    # Priority 3: Settings.json default_level
    elif settings_default_level != "auto":
        documentation_level = settings_default_level
        reason = "settings.json default"

    # Priority 4: Default to minimal (lowest)
    else:
        documentation_level = "minimal"
        reason = "default (use --docs=standard to lift)"

    return documentation_level, reason


class TestDocumentationLevelDefaults:
    """Tests for default documentation level behavior."""

    def test_default_is_minimal_for_low_complexity(self):
        """Default should be minimal even for low complexity tasks."""
        task_context = {
            "title": "Simple fix",
            "description": "Fix a typo",
            "complexity": 2
        }

        level, reason = determine_documentation_level(
            docs_flag=None,
            task_context=task_context
        )

        assert level == "minimal"
        assert "default" in reason

    def test_default_is_minimal_for_high_complexity(self):
        """Default should be minimal even for high complexity tasks.

        This is the key change from the old behavior where complexity >= 4
        would default to 'standard'.
        """
        task_context = {
            "title": "Complex refactoring",
            "description": "Refactor the entire data processing module",
            "complexity": 8
        }

        level, reason = determine_documentation_level(
            docs_flag=None,
            task_context=task_context
        )

        assert level == "minimal"
        assert "default" in reason

    def test_docs_standard_flag_overrides_default(self):
        """Explicit --docs=standard should override the minimal default."""
        task_context = {
            "title": "Any task",
            "description": "Does not matter",
            "complexity": 5
        }

        level, reason = determine_documentation_level(
            docs_flag="standard",
            task_context=task_context
        )

        assert level == "standard"
        assert "explicit flag" in reason

    def test_docs_comprehensive_flag_overrides_default(self):
        """Explicit --docs=comprehensive should override the minimal default."""
        task_context = {
            "title": "Any task",
            "description": "Does not matter",
            "complexity": 3
        }

        level, reason = determine_documentation_level(
            docs_flag="comprehensive",
            task_context=task_context
        )

        assert level == "comprehensive"
        assert "explicit flag" in reason

    def test_force_comprehensive_still_works(self):
        """Security/compliance keywords should still force comprehensive mode."""
        task_context = {
            "title": "Add authentication",
            "description": "Implement password encryption for user auth",
            "complexity": 4
        }

        level, reason = determine_documentation_level(
            docs_flag=None,
            task_context=task_context
        )

        assert level == "comprehensive"
        assert "force trigger" in reason

    def test_settings_default_still_works(self):
        """Settings.json default_level should still be respected."""
        task_context = {
            "title": "Regular task",
            "description": "Nothing special",
            "complexity": 5
        }

        level, reason = determine_documentation_level(
            docs_flag=None,
            task_context=task_context,
            settings_default_level="standard"
        )

        assert level == "standard"
        assert "settings.json default" in reason

    def test_flag_takes_precedence_over_settings(self):
        """Command-line flag should override settings.json default."""
        task_context = {
            "title": "Regular task",
            "description": "Nothing special",
            "complexity": 5
        }

        level, reason = determine_documentation_level(
            docs_flag="minimal",
            task_context=task_context,
            settings_default_level="comprehensive"
        )

        assert level == "minimal"
        assert "explicit flag" in reason

    def test_complexity_no_longer_affects_selection(self):
        """Complexity should no longer affect documentation level selection.

        Previously:
        - complexity 1-3 -> minimal
        - complexity 4+ -> standard

        Now:
        - All complexities -> minimal (unless flag/settings/triggers override)
        """
        # Test range of complexities
        for complexity in range(1, 11):
            task_context = {
                "title": f"Task with complexity {complexity}",
                "description": "Generic task",
                "complexity": complexity
            }

            level, reason = determine_documentation_level(
                docs_flag=None,
                task_context=task_context
            )

            assert level == "minimal", f"Expected minimal for complexity {complexity}"
            assert "default" in reason


class TestForceComprehensiveTriggers:
    """Tests for force-comprehensive trigger behavior."""

    @pytest.mark.parametrize("keyword", [
        "auth", "password", "encryption", "security",
        "gdpr", "hipaa", "compliance", "audit",
        "breaking", "migration", "deprecated"
    ])
    def test_individual_keywords_trigger_comprehensive(self, keyword):
        """Each security/compliance/breaking keyword should trigger comprehensive."""
        task_context = {
            "title": f"Task with {keyword}",
            "description": "Testing keyword triggers",
            "complexity": 2
        }

        level, reason = determine_documentation_level(
            docs_flag=None,
            task_context=task_context
        )

        assert level == "comprehensive"
        assert "force trigger" in reason

    def test_explicit_flag_overrides_force_trigger(self):
        """Explicit flag should take precedence over force triggers.

        Even if task has security keywords, --docs=minimal should be respected.
        """
        task_context = {
            "title": "Add authentication",
            "description": "Security task",
            "complexity": 5
        }

        level, reason = determine_documentation_level(
            docs_flag="minimal",
            task_context=task_context
        )

        assert level == "minimal"
        assert "explicit flag" in reason


class TestConfigurationHierarchy:
    """Tests for the full configuration hierarchy."""

    def test_hierarchy_order(self):
        """Verify the priority order: flag > triggers > settings > default."""
        task_context = {
            "title": "Security task with auth",
            "description": "Testing hierarchy",
            "complexity": 8
        }

        # All overrides present - flag wins
        level, _ = determine_documentation_level(
            docs_flag="minimal",
            task_context=task_context,
            settings_default_level="comprehensive"
        )
        assert level == "minimal"

        # No flag, triggers active - triggers win
        level, _ = determine_documentation_level(
            docs_flag=None,
            task_context=task_context,
            settings_default_level="standard"
        )
        assert level == "comprehensive"

        # No flag, no triggers, settings present - settings win
        neutral_context = {
            "title": "Normal task",
            "description": "No keywords",
            "complexity": 8
        }
        level, _ = determine_documentation_level(
            docs_flag=None,
            task_context=neutral_context,
            settings_default_level="standard"
        )
        assert level == "standard"

        # Nothing set - default (minimal) wins
        level, _ = determine_documentation_level(
            docs_flag=None,
            task_context=neutral_context,
            settings_default_level="auto"
        )
        assert level == "minimal"
