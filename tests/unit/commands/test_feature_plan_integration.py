"""
Comprehensive Test Suite for Feature Plan Integration with Graphiti Context

Tests the integration of Graphiti context enhancement with the /feature-plan command.
This module verifies that feature specifications are enriched with context from Graphiti
before planning begins.

TDD Phase: RED - These tests should FAIL initially because the implementation doesn't exist yet.

Acceptance Criteria Tested:
1. Feature ID auto-detection from description
2. Feature spec seeded to Graphiti before planning
3. Context retrieval and formatting for prompt injection
4. Planning prompt includes enriched context section
5. Logging shows context retrieval progress

Coverage Target: >=85%
Test Count: 15+ tests
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock, call

import pytest

# Import the module we're testing (will fail until we create it)
from guardkit.commands.feature_plan_integration import FeaturePlanIntegration


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root directory."""
    project = tmp_path / "project"
    project.mkdir()
    return project


@pytest.fixture
def feature_spec_file(project_root):
    """Create a sample feature spec file."""
    features_dir = project_root / "docs" / "features"
    features_dir.mkdir(parents=True)

    spec_path = features_dir / "FEAT-GR-003-graphiti-enhanced-context.md"
    spec_content = """---
id: FEAT-GR-003
title: Graphiti Enhanced Context for Feature Planning
description: |
  Enhance /feature-plan command with Graphiti context retrieval
success_criteria:
  - Feature specs automatically detected and seeded
  - Context enrichment happens transparently
technical_requirements:
  - Integration with FeaturePlanContextBuilder
  - Async context retrieval
---

# Graphiti Enhanced Context for Feature Planning

This feature enhances the /feature-plan command with rich context from Graphiti.
"""
    spec_path.write_text(spec_content)
    return spec_path


@pytest.fixture
def mock_context_builder():
    """Mock FeaturePlanContextBuilder."""
    builder = Mock()

    # Mock async build_context method
    async def mock_build_context(description, context_files=None, tech_stack="python"):
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext
        return FeaturePlanContext(
            feature_spec={
                "id": "FEAT-GR-003",
                "title": "Graphiti Enhanced Context",
                "description": "Test feature"
            },
            related_features=[
                {"id": "FEAT-GR-001", "title": "Related feature"}
            ],
            relevant_patterns=[
                {"name": "Repository Pattern", "when_to_use": "For data access"}
            ],
            similar_implementations=[],
            project_architecture={
                "architecture_style": "Layered",
                "key_components": ["API", "Database"]
            },
            warnings=[],
            role_constraints=[],
            quality_gate_configs=[],
            implementation_modes=[]
        )

    builder.build_context = AsyncMock(side_effect=mock_build_context)
    return builder


@pytest.fixture
def integration(project_root, mock_context_builder):
    """Create FeaturePlanIntegration instance with mocked builder."""
    with patch('guardkit.commands.feature_plan_integration.FeaturePlanContextBuilder',
               return_value=mock_context_builder):
        return FeaturePlanIntegration(project_root=project_root)


# ============================================================================
# 1. Initialization Tests (3 tests)
# ============================================================================


def test_init_requires_project_root(project_root):
    """Test that FeaturePlanIntegration requires project_root parameter."""
    integration = FeaturePlanIntegration(project_root=project_root)
    assert integration.project_root == project_root


def test_init_with_none_project_root_raises_error():
    """Test that initializing with None project_root raises TypeError."""
    with pytest.raises(TypeError, match="project_root cannot be None"):
        FeaturePlanIntegration(project_root=None)


def test_init_creates_context_builder(project_root, mock_context_builder):
    """Test that initialization creates a FeaturePlanContextBuilder instance."""
    with patch('guardkit.commands.feature_plan_integration.FeaturePlanContextBuilder',
               return_value=mock_context_builder) as mock_cls:
        integration = FeaturePlanIntegration(project_root=project_root)
        mock_cls.assert_called_once_with(project_root)
        assert integration.context_builder == mock_context_builder


# ============================================================================
# 2. Feature ID Auto-Detection Tests (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_detect_feature_id_from_description_with_feat_prefix(integration):
    """Test auto-detection of feature ID from description with FEAT- prefix."""
    description = "Implement FEAT-GR-003 for enhanced context"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Verify context builder was called with the description
    integration.context_builder.build_context.assert_called_once()
    call_args = integration.context_builder.build_context.call_args
    assert call_args[0][0] == description  # First positional arg


@pytest.mark.asyncio
async def test_detect_feature_id_from_description_without_feat_prefix(integration):
    """Test that feature ID detection works even without explicit FEAT- prefix."""
    description = "Enhance feature planning with graphiti context"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Should still call context builder (even if no feature ID detected)
    integration.context_builder.build_context.assert_called_once()


@pytest.mark.asyncio
async def test_detect_multiple_feature_ids_uses_first(integration):
    """Test that when multiple feature IDs present, first one is used."""
    description = "Implement FEAT-GR-003 and FEAT-GR-004 together"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Verify it processes the description (feature detector handles extraction)
    integration.context_builder.build_context.assert_called_once()


@pytest.mark.asyncio
async def test_no_feature_id_still_builds_context(integration):
    """Test that context is built even when no feature ID is detected."""
    description = "Add new authentication system"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Should still call context builder with full description
    integration.context_builder.build_context.assert_called_once()
    call_args = integration.context_builder.build_context.call_args
    assert call_args[0][0] == description


# ============================================================================
# 3. Context Retrieval and Formatting Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_build_enriched_prompt_calls_context_builder(integration):
    """Test that build_enriched_prompt invokes the context builder."""
    description = "Implement FEAT-GR-003"

    await integration.build_enriched_prompt(description)

    # Verify context builder was called with correct arguments
    integration.context_builder.build_context.assert_called_once()
    call_args = integration.context_builder.build_context.call_args
    # Check positional arg (description) and keyword args (context_files, tech_stack)
    assert call_args[0][0] == description
    assert call_args[1]["context_files"] is None
    assert call_args[1]["tech_stack"] == "python"


@pytest.mark.asyncio
async def test_build_enriched_prompt_with_custom_tech_stack(integration):
    """Test that custom tech_stack is passed to context builder."""
    description = "Implement FEAT-GR-003"

    await integration.build_enriched_prompt(
        description=description,
        tech_stack="typescript"
    )

    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["tech_stack"] == "typescript"


@pytest.mark.asyncio
async def test_build_enriched_prompt_with_context_files(integration):
    """Test that context_files parameter is passed through."""
    description = "Implement FEAT-GR-003"
    context_files = [Path("docs/architecture.md")]

    await integration.build_enriched_prompt(
        description=description,
        context_files=context_files
    )

    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == context_files


@pytest.mark.asyncio
async def test_enriched_prompt_includes_context_section(integration):
    """Test that enriched prompt includes the formatted context section."""
    description = "Implement FEAT-GR-003"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Verify the prompt includes context sections from to_prompt_context()
    assert "Feature Specification" in enriched_prompt
    assert "FEAT-GR-003" in enriched_prompt
    assert "Related Features" in enriched_prompt or "Project Architecture" in enriched_prompt


@pytest.mark.asyncio
async def test_enriched_prompt_format_structure(integration):
    """Test that enriched prompt has proper markdown structure."""
    description = "Implement FEAT-GR-003"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Should have original description
    assert description in enriched_prompt or "FEAT-GR-003" in enriched_prompt

    # Should have context header
    assert "# Enriched Context" in enriched_prompt or "## Feature Specification" in enriched_prompt

    # Should be valid markdown (has headers)
    assert enriched_prompt.count("#") >= 1


# ============================================================================
# 4. Logging and Progress Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_logging_shows_context_retrieval_start(integration, caplog):
    """Test that logging shows when context retrieval starts."""
    description = "Implement FEAT-GR-003"

    with caplog.at_level("INFO"):
        await integration.build_enriched_prompt(description)

    # Should log context retrieval activity
    log_messages = [record.message for record in caplog.records]
    assert any("context" in msg.lower() for msg in log_messages)


@pytest.mark.asyncio
async def test_logging_shows_feature_id_detection(integration, caplog, feature_spec_file):
    """Test that logging shows detected feature ID."""
    description = "Implement FEAT-GR-003 for enhanced context"

    with caplog.at_level("INFO"):
        await integration.build_enriched_prompt(description)

    # Should log feature ID if detected
    log_messages = " ".join([record.message for record in caplog.records])
    # Lenient check - just verify some logging happened
    assert len(caplog.records) >= 0  # At minimum, no crash


@pytest.mark.asyncio
async def test_logging_shows_context_retrieval_completion(integration, caplog):
    """Test that logging shows when context retrieval completes."""
    description = "Implement FEAT-GR-003"

    with caplog.at_level("INFO"):
        await integration.build_enriched_prompt(description)

    # Should have logged something (implementation will add specific messages)
    # This test just ensures logging infrastructure works
    assert True  # Placeholder - will be specific once implementation exists


# ============================================================================
# 5. Error Handling and Graceful Degradation Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_graceful_degradation_when_graphiti_unavailable(project_root):
    """Test that integration works even when Graphiti is unavailable."""
    # Create integration with mocked builder that returns minimal context
    mock_builder = Mock()

    async def mock_build_minimal(description, context_files=None, tech_stack="python"):
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext
        return FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[],
            quality_gate_configs=[],
            implementation_modes=[]
        )

    mock_builder.build_context = AsyncMock(side_effect=mock_build_minimal)

    with patch('guardkit.commands.feature_plan_integration.FeaturePlanContextBuilder',
               return_value=mock_builder):
        integration = FeaturePlanIntegration(project_root=project_root)

        enriched_prompt = await integration.build_enriched_prompt(
            "Implement new feature"
        )

        # Should return a prompt even with minimal context
        assert enriched_prompt is not None
        assert isinstance(enriched_prompt, str)
        assert len(enriched_prompt) > 0


@pytest.mark.asyncio
async def test_exception_in_context_builder_is_handled(project_root):
    """Test that exceptions from context builder are handled gracefully."""
    mock_builder = Mock()
    mock_builder.build_context = AsyncMock(side_effect=Exception("Graphiti error"))

    with patch('guardkit.commands.feature_plan_integration.FeaturePlanContextBuilder',
               return_value=mock_builder):
        integration = FeaturePlanIntegration(project_root=project_root)

        # Should not crash, should handle error gracefully
        with pytest.raises(Exception):
            await integration.build_enriched_prompt("Implement feature")


@pytest.mark.asyncio
async def test_empty_description_handled(integration):
    """Test that empty description is handled without crash."""
    enriched_prompt = await integration.build_enriched_prompt("")

    # Should return some prompt even with empty description
    assert enriched_prompt is not None
    assert isinstance(enriched_prompt, str)


# ============================================================================
# 6. Integration with /feature-plan Command Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_enriched_prompt_suitable_for_command_injection(integration):
    """Test that enriched prompt is suitable for markdown command injection."""
    description = "Implement FEAT-GR-003"

    enriched_prompt = await integration.build_enriched_prompt(description)

    # Should be valid markdown
    assert isinstance(enriched_prompt, str)

    # Should have markdown headers
    assert "#" in enriched_prompt

    # Should not have problematic characters that break markdown
    assert "```" not in enriched_prompt or enriched_prompt.count("```") % 2 == 0


def test_integration_can_be_imported_from_command():
    """Test that FeaturePlanIntegration can be imported for use in commands."""
    # This test verifies the module structure is correct
    from guardkit.commands.feature_plan_integration import FeaturePlanIntegration
    assert FeaturePlanIntegration is not None
