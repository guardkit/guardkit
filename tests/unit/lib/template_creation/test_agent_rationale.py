"""
Tests for agent rationale generation.

TASK-FIX-RATIONALE-E7F1: Meaningful Agent Rationale
"""

import pytest
import sys
from pathlib import Path

# Add repository root to path for imports
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from installer.core.commands.lib.template_create_orchestrator import _generate_agent_rationale


class TestAgentRationale:
    """Tests for agent rationale generation."""

    def test_rationale_with_technologies(self):
        """Test rationale generation from technologies."""
        rationale = _generate_agent_rationale(
            agent_name="realm-repository-specialist",
            technologies=["Realm", "ErrorOr", "Riok.Mapperly"],
            description=""
        )

        assert "Realm" in rationale
        assert "ErrorOr" in rationale
        assert "Specialized agent for" not in rationale  # Not generic

    def test_rationale_with_patterns(self):
        """Test rationale includes detected patterns."""
        rationale = _generate_agent_rationale(
            agent_name="repository-specialist",
            technologies=["C#"],
            description="",
            detected_patterns=["Repository", "Service Layer", "MVVM"]
        )

        assert "Repository" in rationale

    def test_rationale_with_layers(self):
        """Test rationale includes layer context."""
        rationale = _generate_agent_rationale(
            agent_name="repository-specialist",
            technologies=["C#"],
            description="",
            detected_patterns=["Repository"],
            detected_layers=["Infrastructure", "Domain"]
        )

        assert "Infrastructure" in rationale

    def test_rationale_fallback_to_description(self):
        """Test rationale uses description when no tech."""
        rationale = _generate_agent_rationale(
            agent_name="custom-specialist",
            technologies=[],
            description="Handles complex business validation rules"
        )

        assert "business validation" in rationale.lower()

    def test_rationale_not_generic(self):
        """Test that output is never the generic fallback."""
        test_cases = [
            {"technologies": ["Python"]},
            {"description": "Handles API calls"},
            {"detected_patterns": ["Repository"]},
        ]

        for case in test_cases:
            rationale = _generate_agent_rationale(
                agent_name="test-specialist",
                technologies=case.get("technologies", []),
                description=case.get("description", ""),
                detected_patterns=case.get("detected_patterns"),
            )

            assert "Specialized agent for test specialist" not in rationale

    def test_rationale_for_maui_agents(self):
        """Test rationale for .NET MAUI specific agents."""
        agents = [
            ("maui-mvvm-viewmodel-specialist", ["C#", "MAUI", "CommunityToolkit.Mvvm"]),
            ("realm-repository-specialist", ["C#", "Realm", "ErrorOr"]),
            ("error-or-railway-specialist", ["C#", "ErrorOr"]),
        ]

        for agent_name, technologies in agents:
            rationale = _generate_agent_rationale(
                agent_name=agent_name,
                technologies=technologies,
                description="",
                detected_patterns=["Repository", "MVVM", "Railway-Oriented Programming"]
            )

            # Should mention at least one technology
            assert any(tech in rationale for tech in technologies[:2])
            # Should not be generic
            assert "Specialized agent for" not in rationale or "patterns" in rationale

    def test_rationale_empty_inputs(self):
        """Test rationale with minimal inputs (edge case)."""
        rationale = _generate_agent_rationale(
            agent_name="unknown-specialist",
            technologies=[],
            description=""
        )

        # Should still generate something meaningful
        assert len(rationale) > 0
        assert rationale.endswith(".")

    def test_rationale_technology_limit(self):
        """Test that technology list is limited to 4 items."""
        rationale = _generate_agent_rationale(
            agent_name="test-specialist",
            technologies=["Tech1", "Tech2", "Tech3", "Tech4", "Tech5", "Tech6"],
            description=""
        )

        # Should only include first 4 technologies
        assert "Tech1" in rationale
        assert "Tech2" in rationale
        assert "Tech3" in rationale
        assert "Tech4" in rationale
        assert "Tech5" not in rationale
        assert "Tech6" not in rationale

    def test_rationale_pattern_mapping(self):
        """Test that agent names correctly map to patterns."""
        test_cases = [
            ("repository-specialist", ["Repository"], "Repository"),
            ("viewmodel-specialist", ["MVVM"], "MVVM"),
            ("service-specialist", ["Service Layer"], "Service Layer"),
            ("api-specialist", ["API"], "API"),
        ]

        for agent_name, patterns, expected_pattern in test_cases:
            rationale = _generate_agent_rationale(
                agent_name=agent_name,
                technologies=["Python"],
                description="",
                detected_patterns=patterns
            )

            assert expected_pattern in rationale

    def test_rationale_layer_mapping(self):
        """Test that agent names correctly map to layers."""
        test_cases = [
            ("repository-specialist", ["Infrastructure"], "Infrastructure"),
            ("viewmodel-specialist", ["Presentation"], "Presentation"),
            ("service-specialist", ["Application"], "Application"),
            ("api-specialist", ["API"], "API"),
        ]

        for agent_name, layers, expected_layer in test_cases:
            rationale = _generate_agent_rationale(
                agent_name=agent_name,
                technologies=["Python"],
                description="",
                detected_layers=layers
            )

            assert expected_layer in rationale

    def test_rationale_long_description_truncation(self):
        """Test that long descriptions are truncated properly."""
        long_description = "This is a very long description that exceeds the 60 character limit and should be truncated at a reasonable word boundary"

        rationale = _generate_agent_rationale(
            agent_name="test-specialist",
            technologies=[],
            description=long_description
        )

        # Should be truncated and have ellipsis
        assert "..." in rationale
        assert len(rationale) < len(long_description) + 50  # Some overhead for "Handles" prefix

    def test_rationale_combines_all_parts(self):
        """Test that rationale combines technologies, patterns, and layers."""
        rationale = _generate_agent_rationale(
            agent_name="repository-specialist",
            technologies=["C#", "Entity Framework"],
            description="Handles data access",
            detected_patterns=["Repository"],
            detected_layers=["Infrastructure"]
        )

        # Should have all parts
        assert "C#" in rationale
        assert "Entity Framework" in rationale
        assert "Repository" in rationale
        assert "Infrastructure" in rationale
        # Should be well-formatted
        assert rationale.endswith(".")
        assert rationale.count(".") >= 2  # Multiple sentences
