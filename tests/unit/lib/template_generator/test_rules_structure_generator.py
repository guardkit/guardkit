"""
Unit tests for RulesStructureGenerator slim guidance generation.

TASK-GA-001: Tests for slim guidance file generation with boundaries extraction.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from installer.core.lib.template_generator.rules_structure_generator import RulesStructureGenerator
from installer.core.lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
)


@pytest.fixture
def mock_analysis():
    """Create mock CodebaseAnalysis for testing."""
    analysis = Mock(spec=CodebaseAnalysis)
    analysis.codebase_path = "/fake/path"

    # Technology
    tech = Mock(spec=TechnologyInfo)
    tech.primary_language = "Python"
    tech.framework_list = ["FastAPI"]
    tech.testing_framework_list = ["pytest"]
    analysis.technology = tech

    # Architecture
    arch = Mock(spec=ArchitectureInfo)
    arch.architectural_style = "Layered"
    arch.patterns = []
    arch.layers = []  # Add layers to avoid PathPatternInferrer failure
    analysis.architecture = arch

    analysis.example_files = []

    return analysis


@pytest.fixture
def mock_agent():
    """Create mock agent metadata."""
    agent = Mock()
    agent.name = "react-state-specialist"
    agent.purpose = "React state management"
    agent.technologies = ["react", "typescript"]
    agent.capabilities = ["hooks", "state", "context"]
    return agent


@pytest.fixture
def enhanced_agent_content():
    """Sample enhanced agent content for testing."""
    return """---
name: react-state-specialist
description: React hooks and state management implementation specialist
stack: [react, typescript]
capabilities:
  - React hooks implementation (useState, useEffect, useCallback)
  - TanStack Query for server state
  - State management patterns (Context, Zustand)
---

## Quick Start

Example code here...

## Boundaries

### ALWAYS
- ✅ Use TanStack Query for server state (correct tool for server data)
- ✅ Use local state for UI state (component-level concerns)
- ✅ Use Context for shared UI state (theme, auth status)
- ✅ Use Zustand for complex client state (when Context insufficient)
- ✅ Keep state as local as possible (minimize prop drilling)

### NEVER
- ❌ Never use client state for server data (use TanStack Query instead)
- ❌ Never lift state unnecessarily (premature optimization)
- ❌ Never create global state for temporary UI (local state sufficient)
- ❌ Never ignore memo optimization (for expensive computations)
- ❌ Never mutate state directly (use setState/store actions)

### ASK
- ⚠️ Context vs Zustand decision: Ask for complex state with frequent updates
- ⚠️ State normalization: Ask for nested data structures
- ⚠️ Performance optimization: Ask when re-renders are problematic

## When to Use This Agent

Use the react-state-specialist when:
- Implementing custom hooks
- Managing local component state
- Setting up Context providers
- Implementing Zustand stores
- Optimizing component re-renders
- Managing UI state (modals, filters, etc.)

## Capabilities

Detailed capabilities...

## Best Practices

More content...
"""


def test_extract_boundaries(mock_analysis, enhanced_agent_content):
    """Test that boundaries are correctly extracted from enhanced agent."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    boundaries = generator._extract_boundaries(enhanced_agent_content)

    assert "## Boundaries" in boundaries
    assert "### ALWAYS" in boundaries
    assert "### NEVER" in boundaries
    assert "### ASK" in boundaries
    assert "✅ Use TanStack Query for server state" in boundaries
    assert "❌ Never use client state for server data" in boundaries
    assert "⚠️ Context vs Zustand decision" in boundaries


def test_extract_frontmatter_field(mock_analysis, enhanced_agent_content):
    """Test extraction of frontmatter fields."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    description = generator._extract_frontmatter_field(enhanced_agent_content, "description")
    assert "React hooks and state management" in description

    stack = generator._extract_frontmatter_field(enhanced_agent_content, "stack")
    assert "react" in stack.lower()


def test_extract_capability_summary(mock_analysis, enhanced_agent_content):
    """Test that first 5 capabilities are extracted."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    capabilities = generator._extract_capability_summary(enhanced_agent_content, max_items=5)

    # Should extract from "When to Use This Agent" section
    assert "Implementing custom hooks" in capabilities
    assert "Managing local component state" in capabilities

    # Check it's limited to 5 items
    lines = [line for line in capabilities.split('\n') if line.strip().startswith('-')]
    assert len(lines) <= 5


def test_create_slim_guidance(mock_analysis, enhanced_agent_content):
    """Test that slim guidance is created with correct structure."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    slim_guidance = generator._create_slim_guidance(
        agent_name="react-state-specialist",
        enhanced_content=enhanced_agent_content,
        paths_filter='["**/*store*", "**/*context*"]'
    )

    # Check frontmatter
    assert "---" in slim_guidance
    assert 'paths: ["**/*store*", "**/*context*"]' in slim_guidance
    assert "agent: react-state-specialist" in slim_guidance

    # Check sections present
    assert "# React State Specialist" in slim_guidance
    assert "## Purpose" in slim_guidance
    assert "## Technologies" in slim_guidance
    assert "## Boundaries" in slim_guidance
    assert "## When to Use This Agent" in slim_guidance
    assert "## See Also" in slim_guidance

    # Check references to full agent
    assert "agents/react-state-specialist.md" in slim_guidance


def test_create_slim_guidance_size(mock_analysis, enhanced_agent_content):
    """Test that generated slim guidance is under 3KB."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    slim_guidance = generator._create_slim_guidance(
        agent_name="react-state-specialist",
        enhanced_content=enhanced_agent_content,
        paths_filter='["**/*store*", "**/*context*"]'
    )

    size = len(slim_guidance.encode('utf-8'))
    assert size < 3000, f"Slim guidance size {size} exceeds 3KB limit"


def test_extract_boundaries_missing_section(mock_analysis):
    """Test boundaries extraction when section is missing."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    content_without_boundaries = """---
name: test-agent
---

## Some Section

Content here.
"""

    boundaries = generator._extract_boundaries(content_without_boundaries)
    assert boundaries == ""


def test_extract_section(mock_analysis):
    """Test generic section extraction."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    content = """
## First Section

Content of first section.

## Second Section

Content of second section.

## Third Section

More content.
"""

    section = generator._extract_section(content, "## Second Section")
    assert "## Second Section" in section
    assert "Content of second section" in section
    assert "## Third Section" not in section


def test_create_slim_guidance_has_references(mock_analysis, enhanced_agent_content):
    """Test that slim guidance references full agent file."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[],
        output_path=Path("/fake/output")
    )

    slim_guidance = generator._create_slim_guidance(
        agent_name="react-state-specialist",
        enhanced_content=enhanced_agent_content,
        paths_filter='["**/*store*"]'
    )

    assert "## See Also" in slim_guidance
    assert "agents/react-state-specialist.md" in slim_guidance


def test_generate_guidance_rules_with_enhanced_content(mock_analysis, mock_agent, enhanced_agent_content, tmp_path, monkeypatch):
    """Test that _generate_guidance_rules uses slim generation for enhanced agents."""
    # Create a temporary agent file
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    agent_file = agents_dir / "react-state-specialist.md"
    agent_file.write_text(enhanced_agent_content)

    # Create generator with temp path
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[mock_agent],
        output_path=tmp_path
    )

    # Mock the path inferrer
    mock_inferrer = Mock()
    mock_inferrer.infer_for_agent = Mock(return_value='["**/*store*"]')
    generator.path_inferrer = mock_inferrer

    # Generate guidance
    guidance = generator._generate_guidance_rules(mock_agent)

    # Should generate slim guidance, not full content
    assert len(guidance.encode('utf-8')) < 3000
    assert "## Boundaries" in guidance
    assert "## See Also" in guidance
    assert "agents/react-state-specialist.md" in guidance


def test_generate_guidance_rules_without_enhanced_content(mock_analysis, mock_agent):
    """Test that _generate_guidance_rules falls back to stub for non-enhanced agents."""
    generator = RulesStructureGenerator(
        analysis=mock_analysis,
        agents=[mock_agent],
        output_path=Path("/fake/output")
    )

    # Mock the path inferrer
    mock_inferrer = Mock()
    mock_inferrer.infer_for_agent = Mock(return_value='["**/*store*"]')
    generator.path_inferrer = mock_inferrer

    # Generate guidance (no enhanced agent file exists)
    guidance = generator._generate_guidance_rules(mock_agent)

    # Should use stub generation
    assert "# react-state-specialist" in guidance
    assert "## Purpose" in guidance
    assert "## Capabilities" in guidance
    # Should not have boundaries (stub doesn't include them)
    assert "## Boundaries" not in guidance
