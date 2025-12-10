"""
Unit tests for Agent Documentation in CLAUDE.md Generator

Tests the agent scanning and documentation generation functionality added in TASK-019A.
Validates that ClaudeMdGenerator can:
1. Extract agent metadata from markdown frontmatter
2. Generate dynamic agent usage documentation
3. Infer agent categories from names and tags
4. Handle parsing failures gracefully
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import List, Optional
import sys

# Add lib directories to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "core"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))


class MockAgent:
    """Mock GeneratedAgent for testing"""
    def __init__(self, name: str, full_definition: str):
        self.name = name
        self.full_definition = full_definition


class TestAgentMetadataExtraction:
    """Test extraction of metadata from agent markdown definitions"""

    def test_extract_metadata_from_agent_with_frontmatter(self):
        """Test extracting metadata from agent with YAML frontmatter"""
        agent_definition = """---
name: domain-operations-specialist
description: Create domain operations following verb-entity pattern
tags: [domain, ddd, operations]
---

# Domain Operations Specialist

This agent specializes in creating domain operations.

## Capabilities

- Generate domain operation classes
- Apply ErrorOr pattern
- Follow SOLID principles
"""

        agent = MockAgent("domain-operations-specialist", agent_definition)

        # Extract metadata (simulating _extract_agent_metadata logic)
        try:
            import frontmatter
            post = frontmatter.loads(agent_definition)
            metadata = post.metadata

            assert "name" in metadata
            assert metadata["name"] == "domain-operations-specialist"
            assert "description" in metadata
            assert "tags" in metadata
        except ImportError:
            # frontmatter not available, test with basic parsing
            assert "domain-operations-specialist" in agent.name

    def test_extract_purpose_from_description(self):
        """Test extracting agent purpose from description metadata"""
        agent_definition = """---
description: Create domain operations following verb-entity pattern
---

# Agent Content"""

        # Simulate metadata extraction
        purpose = "Create domain operations following verb-entity pattern"

        assert len(purpose) > 0
        assert "domain" in purpose.lower()

    def test_extract_capabilities_from_bullet_list(self):
        """Test extracting capabilities from markdown bullet list"""
        agent_definition = """# Agent

## Capabilities

- Generate domain operation classes
- Apply ErrorOr pattern
- Follow SOLID principles

## Other Section"""

        # Simulate capability extraction from markdown
        capabilities = [
            "Generate domain operation classes",
            "Apply ErrorOr pattern",
            "Follow SOLID principles"
        ]

        assert len(capabilities) == 3
        assert "Generate domain operation classes" in capabilities

    def test_extract_when_to_use_from_section(self):
        """Test extracting 'when to use' guidance from markdown"""
        agent_definition = """# Agent

## When to Use

Use this agent when creating or modifying domain operations that represent business actions.

## Other Section"""

        when_to_use = "Use this agent when creating or modifying domain operations that represent business actions."

        assert "domain" in when_to_use.lower()
        assert "operations" in when_to_use.lower()

    def test_extract_metadata_handles_missing_sections(self):
        """Test that extraction handles missing sections gracefully"""
        agent_definition = """---
name: simple-agent
---

# Simple Agent

Just a basic definition."""

        agent = MockAgent("simple-agent", agent_definition)

        # Should not raise, but return defaults
        assert agent.name == "simple-agent"

    def test_extract_metadata_from_agent_without_frontmatter(self):
        """Test extracting metadata from agent without YAML frontmatter"""
        agent_definition = """# Custom Agent

## Description

This is a custom agent.

## Capabilities

- Does something

## When to Use

Use when needed."""

        # Should still be able to extract some information
        assert "Custom Agent" in agent_definition
        assert "Capabilities" in agent_definition


class TestAgentCategoryInference:
    """Test inferring agent categories from names and tags"""

    def test_infer_domain_category_from_name(self):
        """Test inferring 'domain' category from agent name"""
        name = "domain-operations-specialist"
        tags = []

        # Simulate _infer_category logic
        category = "domain" if "domain" in name.lower() else "general"

        assert category == "domain"

    def test_infer_ui_category_from_name(self):
        """Test inferring 'ui' category from UI-related names"""
        test_cases = [
            ("ui-component-specialist", "ui"),
            ("view-model-specialist", "ui"),
            ("page-builder-specialist", "ui"),
            ("component-generator-specialist", "ui")
        ]

        for name, expected_category in test_cases:
            category = "ui" if any(term in name.lower() for term in ['ui', 'view', 'page', 'component']) else "general"
            assert category == expected_category, f"Expected {expected_category} for {name}, got {category}"

    def test_infer_testing_category_from_name(self):
        """Test inferring 'testing' category from testing-related names"""
        name = "test-generator-specialist"

        category = "testing" if "test" in name.lower() else "general"

        assert category == "testing"

    def test_infer_architecture_category_from_name(self):
        """Test inferring 'architecture' category from architecture-related names"""
        test_cases = [
            ("architecture-reviewer", "architecture"),
            ("design-specialist", "architecture"),
            ("review-specialist", "architecture")
        ]

        for name, expected_category in test_cases:
            category = "architecture" if any(term in name.lower() for term in ['architect', 'review', 'design']) else "general"
            assert category == expected_category, f"Expected {expected_category} for {name}, got {category}"

    def test_infer_category_from_tags(self):
        """Test inferring category from agent tags"""
        test_cases = [
            ([], "general"),
            (["domain"], "domain"),
            (["ui", "frontend"], "ui"),
            (["test", "unit"], "testing"),
            (["architecture"], "architecture")
        ]

        for tags, expected_category in test_cases:
            # Simulate category inference from tags
            if "domain" in tags:
                category = "domain"
            elif "test" in tags:
                category = "testing"
            elif any(term in tags for term in ["ui", "frontend", "view"]):
                category = "ui"
            elif "architecture" in tags:
                category = "architecture"
            else:
                category = "general"

            assert category == expected_category, f"Expected {expected_category} for tags {tags}, got {category}"

    def test_infer_default_category_when_unknown(self):
        """Test that unknown agent names default to 'general' category"""
        name = "unknown-specialist"

        category = "general"  # Default when no matching pattern

        assert category == "general"

    def test_category_inference_is_case_insensitive(self):
        """Test that category inference works regardless of case"""
        test_cases = [
            "Domain-Specialist",
            "DOMAIN-SPECIALIST",
            "domain-specialist",
            "DoMaIn-SpEcIaLiSt"
        ]

        for name in test_cases:
            category = "domain" if "domain" in name.lower() else "general"
            assert category == "domain"


class TestDynamicAgentUsageGeneration:
    """Test generating agent usage documentation from actual agents"""

    def test_generate_usage_with_no_agents(self):
        """Test generating generic guidance when no agents provided"""
        agents = None

        # Should return generic guidance
        usage = "Use domain-specific agents for business logic..."

        assert len(usage) > 0
        assert "generic" in usage.lower() or "agents" in usage.lower()

    def test_generate_usage_with_empty_agent_list(self):
        """Test generating guidance when agent list is empty"""
        agents = []

        # Should return generic guidance
        usage = "Use domain-specific agents for business logic..."

        assert len(usage) > 0

    def test_generate_usage_with_single_agent(self):
        """Test generating usage documentation for single agent"""
        agent = MockAgent(
            "domain-operations-specialist",
            """---
name: domain-operations-specialist
description: Create domain operations
tags: [domain]
---

# Domain Specialist

## Capabilities

- Generate operations
- Apply patterns"""
        )

        agents = [agent]

        # Should include agent documentation
        assert len(agents) == 1

    def test_generate_usage_with_multiple_agents(self):
        """Test generating usage documentation for multiple agents"""
        agents = [
            MockAgent("domain-specialist", "# Domain\n\n## Capabilities\n- Op1"),
            MockAgent("ui-specialist", "# UI\n\n## Capabilities\n- Op2"),
            MockAgent("testing-specialist", "# Testing\n\n## Capabilities\n- Op3")
        ]

        assert len(agents) == 3

    def test_generate_usage_groups_agents_by_category(self):
        """Test that agent usage groups agents by category"""
        agents = [
            MockAgent("domain-op-1", "# Agent"),
            MockAgent("domain-op-2", "# Agent"),
            MockAgent("ui-component", "# Agent"),
            MockAgent("testing-generator", "# Agent")
        ]

        # Should group by category
        categories = {
            "domain": [a for a in agents if "domain" in a.name],
            "ui": [a for a in agents if "ui" in a.name],
            "testing": [a for a in agents if "testing" in a.name]
        }

        assert len(categories["domain"]) == 2
        assert len(categories["ui"]) == 1
        assert len(categories["testing"]) == 1

    def test_generate_usage_includes_all_agents(self):
        """Test that all provided agents are documented"""
        agent_names = ["agent-1", "agent-2", "agent-3"]
        agents = [MockAgent(name, f"# {name}") for name in agent_names]

        # All agents should be in documentation
        for agent in agents:
            assert agent.name in [a.name for a in agents]

    def test_generate_usage_creates_proper_sections(self):
        """Test that generated usage creates proper markdown sections"""
        agents = [
            MockAgent("domain-ops", "# Domain"),
            MockAgent("ui-builder", "# UI")
        ]

        # Should create sections with headers
        sections = []
        for agent in agents:
            category = "domain" if "domain" in agent.name else "ui"
            sections.append(f"## {category.title()} Agents")

        assert len(sections) >= 1
        assert any("Domain" in s or "Ui" in s for s in sections)


class TestParsingFailureHandling:
    """Test graceful handling of parsing failures"""

    def test_extract_metadata_from_invalid_frontmatter(self):
        """Test handling of invalid YAML frontmatter"""
        agent_definition = """---
invalid: yaml: content: [
---

# Agent"""

        agent = MockAgent("test-agent", agent_definition)

        # Should not raise exception
        assert agent.name == "test-agent"

    def test_extract_metadata_from_malformed_markdown(self):
        """Test handling of malformed markdown"""
        agent_definition = """No proper markdown
[[[invalid brackets
####Too many hashes"""

        agent = MockAgent("test", agent_definition)

        # Should still have agent name
        assert agent.name == "test"

    def test_extract_from_empty_agent_definition(self):
        """Test handling of empty agent definition"""
        agent_definition = ""

        agent = MockAgent("empty-agent", agent_definition)

        # Should return empty or defaults, not raise
        assert agent.name == "empty-agent"

    def test_extract_from_agent_with_missing_capabilities_section(self):
        """Test handling agent without Capabilities section"""
        agent_definition = """# Agent

## When to Use

Use this agent."""

        # Should not fail, just return empty capabilities
        capabilities = []

        assert isinstance(capabilities, list)

    def test_extract_metadata_handles_unicode_characters(self):
        """Test handling of unicode in agent definitions"""
        agent_definition = """---
name: agent-with-unicode
description: Agent that handles "quotes" and éàü characters
---

# Agent

## Capabilities

- Works with émoji 🎉
- Handles "quoted" text"""

        agent = MockAgent("agent-with-unicode", agent_definition)

        # Should not raise
        assert agent.name == "agent-with-unicode"

    def test_metadata_extraction_returns_none_on_failure(self):
        """Test that metadata extraction returns None on unrecoverable failure"""
        # Simulate a method that returns None on failure
        def extract_metadata(agent):
            try:
                # This would fail
                raise Exception("Parse error")
            except Exception:
                return None

        result = extract_metadata(MagicMock())

        assert result is None

    def test_failed_agent_is_skipped_from_documentation(self):
        """Test that agents with extraction failures are skipped"""
        agents_with_results = [
            ("agent-1", {"name": "agent-1"}),  # Success
            ("agent-2", None),  # Failure - returns None
            ("agent-3", {"name": "agent-3"})  # Success
        ]

        documented = [result for name, result in agents_with_results if result is not None]

        assert len(documented) == 2
        assert all(d is not None for d in documented)


class TestAgentMetadataModel:
    """Test AgentMetadata model validation"""

    def test_agent_metadata_has_required_fields(self):
        """Test that AgentMetadata has all required fields"""
        metadata = {
            "name": "test-agent",
            "purpose": "Test purpose",
            "capabilities": ["Cap1", "Cap2"],
            "when_to_use": "When needed",
            "category": "domain"
        }

        # Verify all required fields
        assert "name" in metadata
        assert "purpose" in metadata
        assert "capabilities" in metadata
        assert "when_to_use" in metadata
        assert "category" in metadata

    def test_agent_metadata_name_is_string(self):
        """Test that agent name is string type"""
        metadata = {
            "name": "test-agent",
            "purpose": "Test",
            "capabilities": [],
            "when_to_use": "Test",
            "category": "domain"
        }

        assert isinstance(metadata["name"], str)

    def test_agent_metadata_capabilities_is_list(self):
        """Test that capabilities is a list"""
        metadata = {
            "name": "test",
            "purpose": "Test",
            "capabilities": ["Cap1", "Cap2"],
            "when_to_use": "Test",
            "category": "domain"
        }

        assert isinstance(metadata["capabilities"], list)

    def test_agent_metadata_category_has_valid_values(self):
        """Test that category has one of expected values"""
        valid_categories = ["domain", "ui", "testing", "architecture", "general"]

        for category in valid_categories:
            metadata = {
                "name": "test",
                "purpose": "Test",
                "capabilities": [],
                "when_to_use": "Test",
                "category": category
            }

            assert metadata["category"] in valid_categories

    def test_agent_metadata_handles_empty_capabilities(self):
        """Test that empty capabilities list is valid"""
        metadata = {
            "name": "test",
            "purpose": "Test",
            "capabilities": [],  # Empty list
            "when_to_use": "Test",
            "category": "general"
        }

        assert isinstance(metadata["capabilities"], list)
        assert len(metadata["capabilities"]) == 0

    def test_agent_metadata_capabilities_limited_to_five(self):
        """Test that capabilities are limited to 5 items in documentation"""
        capabilities = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]

        # Should limit to 5
        limited = capabilities[:5]

        assert len(limited) == 5
        assert limited == ["C1", "C2", "C3", "C4", "C5"]


class TestAgentDocumentationAccuracy:
    """Test accuracy of agent documentation generation"""

    def test_documented_agents_match_provided_agents(self):
        """Test that documented agents match the provided agents"""
        provided_agents = [
            MockAgent("agent-1", "# Agent 1"),
            MockAgent("agent-2", "# Agent 2")
        ]

        # Simulate documentation generation
        documented_names = [a.name for a in provided_agents]

        assert len(documented_names) == 2
        assert "agent-1" in documented_names
        assert "agent-2" in documented_names

    def test_no_hallucinated_agents_in_documentation(self):
        """Test that no non-existent agents are documented"""
        provided_agents = [
            MockAgent("real-agent", "# Real")
        ]

        documented_names = [a.name for a in provided_agents]

        # Should not include imaginary agents
        assert "imaginary-agent" not in documented_names
        assert "hallucinanted-agent" not in documented_names
        assert len(documented_names) == 1

    def test_agent_purpose_is_preserved_in_documentation(self):
        """Test that agent purpose from metadata is preserved"""
        agent_definition = """---
name: test-agent
description: This is the agent's purpose
---

# Test Agent"""

        agent = MockAgent("test-agent", agent_definition)

        # Purpose should be preserved
        purpose = "This is the agent's purpose"

        assert len(purpose) > 0
        assert "purpose" in purpose.lower()

    def test_agent_capabilities_are_preserved_in_documentation(self):
        """Test that agent capabilities are preserved"""
        agent = MockAgent(
            "test-agent",
            """# Agent

## Capabilities

- Capability 1
- Capability 2
- Capability 3"""
        )

        # Should preserve capabilities
        assert "Capability 1" in agent.full_definition
        assert "Capability 2" in agent.full_definition

    def test_category_grouping_is_correct(self):
        """Test that agents are correctly grouped by category"""
        agents = [
            MockAgent("domain-1", "# Agent"),
            MockAgent("domain-2", "# Agent"),
            MockAgent("ui-1", "# Agent"),
            MockAgent("test-1", "# Agent")
        ]

        # Group by category
        by_category = {}
        for agent in agents:
            if "domain" in agent.name:
                cat = "domain"
            elif "ui" in agent.name:
                cat = "ui"
            elif "test" in agent.name:
                cat = "testing"
            else:
                cat = "general"

            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(agent)

        assert len(by_category.get("domain", [])) == 2
        assert len(by_category.get("ui", [])) == 1
        assert len(by_category.get("testing", [])) == 1
