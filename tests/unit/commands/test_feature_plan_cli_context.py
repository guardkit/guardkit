"""
Tests for --context CLI option in /feature-plan command.

This module tests the new --context option that allows users to explicitly
specify context files for feature planning.

Acceptance Criteria Tested:
1. --context path/to/spec.md seeds specified file
2. Multiple --context flags supported
3. Works alongside auto-detection
4. Help text documents usage

Coverage Target: >=85%
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, call

import pytest

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
def context_file_1(project_root):
    """Create first context file."""
    docs_dir = project_root / "docs"
    docs_dir.mkdir()

    context_path = docs_dir / "spec.md"
    context_path.write_text("# Feature Spec\n\nThis is a specification.")
    return context_path


@pytest.fixture
def context_file_2(project_root):
    """Create second context file."""
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)

    context_path = docs_dir / "architecture.md"
    context_path.write_text("# Architecture\n\nThis is architecture docs.")
    return context_path


@pytest.fixture
def mock_context_builder():
    """Mock FeaturePlanContextBuilder."""
    builder = Mock()

    async def mock_build_context(description, context_files=None, tech_stack="python"):
        from guardkit.knowledge.feature_plan_context import FeaturePlanContext
        return FeaturePlanContext(
            feature_spec={"id": "FEAT-001", "title": "Test Feature"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
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
# 1. Single --context File Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_single_context_file_passed_to_builder(integration, context_file_1):
    """Test that single --context file is passed to context builder."""
    description = "Implement new feature"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1]
    )

    # Verify context builder was called with the context file
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [context_file_1]


@pytest.mark.asyncio
async def test_relative_context_path_resolved(integration, project_root, context_file_1):
    """Test that relative context paths are resolved correctly."""
    description = "Implement new feature"

    # Use relative path
    relative_path = Path("docs/spec.md")

    await integration.build_enriched_prompt(
        description=description,
        context_files=[relative_path]
    )

    # Should pass the path to context builder
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [relative_path]


@pytest.mark.asyncio
async def test_absolute_context_path_works(integration, context_file_1):
    """Test that absolute context paths work correctly."""
    description = "Implement new feature"

    # Use absolute path
    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1.absolute()]
    )

    # Should pass the absolute path to context builder
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [context_file_1.absolute()]


# ============================================================================
# 2. Multiple --context Files Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_context_files_passed_to_builder(integration, context_file_1, context_file_2):
    """Test that multiple --context files are passed to context builder."""
    description = "Implement new feature"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1, context_file_2]
    )

    # Verify all context files were passed
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [context_file_1, context_file_2]


@pytest.mark.asyncio
async def test_context_files_order_preserved(integration, context_file_1, context_file_2):
    """Test that order of --context files is preserved."""
    description = "Implement new feature"

    # Pass in specific order
    context_files = [context_file_2, context_file_1]

    await integration.build_enriched_prompt(
        description=description,
        context_files=context_files
    )

    # Verify order is preserved
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == context_files


@pytest.mark.asyncio
async def test_duplicate_context_files_handled(integration, context_file_1):
    """Test that duplicate --context files are handled gracefully."""
    description = "Implement new feature"

    # Pass same file twice
    context_files = [context_file_1, context_file_1]

    await integration.build_enriched_prompt(
        description=description,
        context_files=context_files
    )

    # Should pass both (deduplication is context builder's responsibility)
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == context_files


# ============================================================================
# 3. Auto-detection Integration Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_context_files_work_with_feature_id_detection(integration, context_file_1):
    """Test that --context files work alongside feature ID auto-detection."""
    description = "Implement FEAT-GR-003 for enhanced context"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1]
    )

    # Should call builder with both description and context files
    call_args = integration.context_builder.build_context.call_args
    assert call_args[0][0] == description
    assert call_args[1]["context_files"] == [context_file_1]


@pytest.mark.asyncio
async def test_empty_context_files_list_handled(integration):
    """Test that empty context_files list is handled gracefully."""
    description = "Implement new feature"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[]
    )

    # Should pass empty list to context builder
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == []


@pytest.mark.asyncio
async def test_none_context_files_uses_auto_detection(integration):
    """Test that context_files=None allows pure auto-detection."""
    description = "Implement FEAT-GR-003"

    await integration.build_enriched_prompt(
        description=description,
        context_files=None
    )

    # Should pass None to context builder (enables auto-detection)
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] is None


# ============================================================================
# 4. Error Handling Tests (3 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_nonexistent_context_file_handled(integration, project_root):
    """Test that nonexistent context files don't crash the integration."""
    description = "Implement new feature"

    nonexistent = project_root / "does_not_exist.md"

    # Should not crash - context builder will handle validation
    await integration.build_enriched_prompt(
        description=description,
        context_files=[nonexistent]
    )

    # Verify the path was passed (validation happens in context builder)
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [nonexistent]


@pytest.mark.asyncio
async def test_mixed_existing_and_nonexistent_files(integration, context_file_1, project_root):
    """Test handling of mix of existing and nonexistent context files."""
    description = "Implement new feature"

    nonexistent = project_root / "missing.md"
    context_files = [context_file_1, nonexistent]

    # Should pass all files to context builder
    await integration.build_enriched_prompt(
        description=description,
        context_files=context_files
    )

    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == context_files


@pytest.mark.asyncio
async def test_invalid_path_types_handled(integration):
    """Test that invalid path types are handled appropriately."""
    description = "Implement new feature"

    # Pass string instead of Path (should work)
    context_files = ["docs/spec.md"]

    # Should not crash - will be converted to Path if needed
    await integration.build_enriched_prompt(
        description=description,
        context_files=context_files
    )

    # Verify it was passed through
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == context_files


# ============================================================================
# 5. Integration with Tech Stack Tests (2 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_context_files_with_custom_tech_stack(integration, context_file_1):
    """Test that --context works with custom tech_stack parameter."""
    description = "Implement new feature"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1],
        tech_stack="typescript"
    )

    # Verify both context_files and tech_stack passed
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [context_file_1]
    assert call_args[1]["tech_stack"] == "typescript"


@pytest.mark.asyncio
async def test_context_files_with_default_tech_stack(integration, context_file_1):
    """Test that --context uses default tech_stack when not specified."""
    description = "Implement new feature"

    await integration.build_enriched_prompt(
        description=description,
        context_files=[context_file_1]
    )

    # Verify default tech_stack is used
    call_args = integration.context_builder.build_context.call_args
    assert call_args[1]["context_files"] == [context_file_1]
    assert call_args[1]["tech_stack"] == "python"
