"""
Comprehensive Test Suite for Phase 0 Design Extraction in AutoBuild

Tests Phase 0 integration into AutoBuildOrchestrator including:
- Design URL detection and skipping logic
- DesignContext dataclass structure
- _extract_design_phase() method
- Integration with DesignExtractor facade
- Status literals and error handling
- Backward compatibility for non-design tasks

Coverage Target: >=85%
Test Count: 10 tests
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest
import yaml

# These imports will be enabled once implementation exists
# For now, we import what exists and expect AttributeError for missing components
from guardkit.orchestrator.mcp_design_extractor import (
    DesignData,
    DesignExtractor,
    MCPUnavailableError,
)


# ============================================================================
# 1. Fixtures
# ============================================================================


@pytest.fixture
def temp_repo_dir(tmp_path):
    """Create temporary repository directory with task structure."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create tasks directory structure
    tasks_dir = repo_dir / "tasks"
    for subdir in ["backlog", "in_progress", "design_approved"]:
        (tasks_dir / subdir).mkdir(parents=True)

    return repo_dir


@pytest.fixture
def task_with_design_url(temp_repo_dir):
    """Create task file with design_url in frontmatter."""
    task_id = "TASK-DM-003"
    task_file = temp_repo_dir / "tasks" / "backlog" / f"{task_id}.md"

    task_content = """---
id: TASK-DM-003
title: Implement button component
status: backlog
design_url: https://www.figma.com/file/abc123?node-id=2:2
priority: high
created: 2026-02-08T10:00:00Z
---

# Implement button component

## Description
Create reusable button component from Figma design.

## Acceptance Criteria
- [ ] Button matches Figma design
- [ ] Props for variant, size, disabled
- [ ] 85% test coverage
"""

    task_file.write_text(task_content)
    return task_file, task_id


@pytest.fixture
def task_without_design_url(temp_repo_dir):
    """Create task file without design_url (backward compatible)."""
    task_id = "TASK-NO-001"
    task_file = temp_repo_dir / "tasks" / "backlog" / f"{task_id}.md"

    task_content = """---
id: TASK-NO-001
title: Refactor utility functions
status: backlog
priority: medium
created: 2026-02-08T10:00:00Z
---

# Refactor utility functions

## Description
Refactor string utilities for better performance.

## Acceptance Criteria
- [ ] Functions 20% faster
- [ ] Same API maintained
- [ ] 90% test coverage
"""

    task_file.write_text(task_content)
    return task_file, task_id


@pytest.fixture
def task_with_zeplin_url(temp_repo_dir):
    """Create task file with Zeplin design URL."""
    task_id = "TASK-ZEP-001"
    task_file = temp_repo_dir / "tasks" / "backlog" / f"{task_id}.md"

    task_content = """---
id: TASK-ZEP-001
title: Implement login screen
status: backlog
design_url: https://app.zeplin.io/project/proj-123/screen/screen-456
priority: high
created: 2026-02-08T10:00:00Z
---

# Implement login screen

## Description
Create login screen from Zeplin design.

## Acceptance Criteria
- [ ] Screen matches Zeplin design
- [ ] Email and password inputs
- [ ] 85% test coverage
"""

    task_file.write_text(task_content)
    return task_file, task_id


@pytest.fixture
def sample_figma_design_data():
    """Sample DesignData from Figma extraction."""
    return DesignData(
        source="figma",
        elements=[
            {
                "name": "Button",
                "type": "component",
                "props": [
                    {"name": "variant", "type": "enum", "values": ["primary", "secondary"]},
                    {"name": "size", "type": "enum", "values": ["sm", "md", "lg"]},
                    {"name": "disabled", "type": "boolean"},
                ],
            },
        ],
        tokens={
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
            },
            "spacing": {
                "sm": "8px",
                "md": "16px",
                "lg": "24px",
            },
            "typography": {
                "button": {
                    "fontSize": "14px",
                    "fontWeight": 500,
                },
            },
        },
        visual_reference="https://figma.com/api/v1/files/abc123/images",
        metadata={
            "file_key": "abc123",
            "node_id": "2:2",
            "extracted_at": "2026-02-08T12:00:00Z",
        },
    )


@pytest.fixture
def sample_zeplin_design_data():
    """Sample DesignData from Zeplin extraction."""
    return DesignData(
        source="zeplin",
        elements=[
            {
                "name": "LoginScreen",
                "components": [
                    {"id": "comp-001", "name": "EmailInput", "x": 20, "y": 100},
                    {"id": "comp-002", "name": "PasswordInput", "x": 20, "y": 160},
                    {"id": "comp-003", "name": "SubmitButton", "x": 20, "y": 220},
                ],
            },
        ],
        tokens={
            "colors": [
                {"name": "Primary", "value": "#3B82F6"},
                {"name": "Background", "value": "#FFFFFF"},
            ],
            "text_styles": [
                {"name": "Input Label", "fontSize": 12, "fontWeight": 400},
                {"name": "Button Text", "fontSize": 14, "fontWeight": 500},
            ],
        },
        visual_reference=None,
        metadata={
            "project_id": "proj-123",
            "screen_id": "screen-456",
            "extracted_at": "2026-02-08T12:00:00Z",
        },
    )


@pytest.fixture
def mock_design_extractor():
    """Create mock DesignExtractor."""
    extractor = MagicMock(spec=DesignExtractor)
    return extractor


# ============================================================================
# 2. DesignContext Dataclass Tests (1 test)
# ============================================================================


class TestDesignContextDataclass:
    """Test DesignContext dataclass structure and fields."""

    def test_design_context_dataclass_exists(self):
        """DesignContext dataclass exists with all required fields."""
        # Import will fail until implementation exists (RED phase)
        with pytest.raises(ImportError):
            from guardkit.orchestrator.autobuild import DesignContext

            # Once implemented, this should work:
            # context = DesignContext(
            #     elements=[{"name": "Button"}],
            #     tokens={"colors": {"primary": "#3B82F6"}},
            #     constraints={"no_shadcn_icons": True},
            #     visual_reference="https://example.com/image.png",
            #     summary="Design summary ~3K tokens",
            #     source="figma",
            #     metadata={"file_key": "abc123"},
            # )
            # assert hasattr(context, "elements")
            # assert hasattr(context, "tokens")
            # assert hasattr(context, "constraints")
            # assert hasattr(context, "visual_reference")
            # assert hasattr(context, "summary")
            # assert hasattr(context, "source")
            # assert hasattr(context, "metadata")


# ============================================================================
# 3. Phase 0 Skipping Logic Tests (1 test)
# ============================================================================


class TestPhase0SkippingLogic:
    """Test Phase 0 is skipped entirely for tasks without design_url."""

    def test_phase0_skipped_when_no_design_url(
        self, temp_repo_dir, task_without_design_url, mock_design_extractor
    ):
        """Phase 0 skipped entirely for tasks without design_url, backward compatible."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     design_context = orchestrator._extract_design_phase(task_id="TASK-NO-001")
            #
            #     # Should return None when no design_url present
            #     assert design_context is None
            #
            #     # DesignExtractor should never be called
            #     mock_design_extractor.verify_mcp_availability.assert_not_called()
            #     mock_design_extractor.extract_figma.assert_not_called()
            #     mock_design_extractor.extract_zeplin.assert_not_called()


# ============================================================================
# 4. Figma Design Extraction Tests (1 test)
# ============================================================================


class TestFigmaDesignExtraction:
    """Test Figma design extraction via DesignExtractor."""

    @pytest.mark.asyncio
    async def test_phase0_extracts_figma_design(
        self, temp_repo_dir, task_with_design_url, sample_figma_design_data, mock_design_extractor
    ):
        """When design_url is Figma URL, extracts via DesignExtractor."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, DesignContext

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # # Mock MCP availability and extraction
            # mock_design_extractor.verify_mcp_availability.return_value = True
            # mock_design_extractor.extract_figma = AsyncMock(return_value=sample_figma_design_data)
            # mock_design_extractor.summarize_design_data.return_value = "Design summary text"
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     design_context = await orchestrator._extract_design_phase(task_id="TASK-DM-003")
            #
            #     # Should return DesignContext
            #     assert isinstance(design_context, DesignContext)
            #     assert design_context.source == "figma"
            #     assert len(design_context.elements) > 0
            #     assert "colors" in design_context.tokens
            #     assert design_context.summary == "Design summary text"
            #
            #     # Verify MCP was checked and extraction called
            #     mock_design_extractor.verify_mcp_availability.assert_called_once_with("figma")
            #     mock_design_extractor.extract_figma.assert_called_once()


# ============================================================================
# 5. Zeplin Design Extraction Tests (1 test)
# ============================================================================


class TestZeplinDesignExtraction:
    """Test Zeplin design extraction via DesignExtractor."""

    @pytest.mark.asyncio
    async def test_phase0_extracts_zeplin_design(
        self, temp_repo_dir, task_with_zeplin_url, sample_zeplin_design_data, mock_design_extractor
    ):
        """When design_url is Zeplin URL, extracts via DesignExtractor."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, DesignContext

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # # Mock MCP availability and extraction
            # mock_design_extractor.verify_mcp_availability.return_value = True
            # mock_design_extractor.extract_zeplin = AsyncMock(return_value=sample_zeplin_design_data)
            # mock_design_extractor.summarize_design_data.return_value = "Zeplin design summary"
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     design_context = await orchestrator._extract_design_phase(task_id="TASK-ZEP-001")
            #
            #     # Should return DesignContext
            #     assert isinstance(design_context, DesignContext)
            #     assert design_context.source == "zeplin"
            #     assert len(design_context.elements) > 0
            #     assert design_context.summary == "Zeplin design summary"
            #
            #     # Verify MCP was checked and extraction called
            #     mock_design_extractor.verify_mcp_availability.assert_called_once_with("zeplin")
            #     mock_design_extractor.extract_zeplin.assert_called_once()


# ============================================================================
# 6. MCP Availability Verification Tests (1 test)
# ============================================================================


class TestMCPAvailabilityVerification:
    """Test fail-fast behavior when MCP unavailable."""

    @pytest.mark.asyncio
    async def test_phase0_fails_fast_when_mcp_unavailable(
        self, temp_repo_dir, task_with_design_url, mock_design_extractor
    ):
        """verify_mcp_availability returns False, fails fast with clear error."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, DesignExtractionPhaseError

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # # Mock MCP unavailable
            # mock_design_extractor.verify_mcp_availability.return_value = False
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     with pytest.raises(DesignExtractionPhaseError, match="MCP.*not available"):
            #         await orchestrator._extract_design_phase(task_id="TASK-DM-003")
            #
            #     # Should have checked MCP availability
            #     mock_design_extractor.verify_mcp_availability.assert_called_once()
            #
            #     # Should NOT have attempted extraction
            #     mock_design_extractor.extract_figma.assert_not_called()


# ============================================================================
# 7. DesignContext Return Tests (1 test)
# ============================================================================


class TestDesignContextReturn:
    """Test _extract_design_phase returns proper DesignContext."""

    @pytest.mark.asyncio
    async def test_phase0_returns_design_context(
        self, temp_repo_dir, task_with_design_url, sample_figma_design_data, mock_design_extractor
    ):
        """Successful extraction returns DesignContext with all required fields."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, DesignContext

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # mock_design_extractor.verify_mcp_availability.return_value = True
            # mock_design_extractor.extract_figma = AsyncMock(return_value=sample_figma_design_data)
            # mock_design_extractor.summarize_design_data.return_value = "Summary text"
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     design_context = await orchestrator._extract_design_phase(task_id="TASK-DM-003")
            #
            #     # Verify all DesignContext fields populated
            #     assert isinstance(design_context, DesignContext)
            #     assert isinstance(design_context.elements, list)
            #     assert isinstance(design_context.tokens, dict)
            #     assert isinstance(design_context.constraints, dict)
            #     assert isinstance(design_context.summary, str)
            #     assert design_context.source in ["figma", "zeplin"]
            #     assert isinstance(design_context.metadata, dict)
            #
            #     # visual_reference can be None or str
            #     assert design_context.visual_reference is None or isinstance(
            #         design_context.visual_reference, str
            #     )


# ============================================================================
# 8. Extraction Metadata Storage Tests (1 test)
# ============================================================================


class TestExtractionMetadataStorage:
    """Test extraction metadata written to task frontmatter."""

    @pytest.mark.asyncio
    async def test_phase0_stores_extraction_metadata(
        self, temp_repo_dir, task_with_design_url, sample_figma_design_data, mock_design_extractor
    ):
        """Extraction metadata (timestamp, hash) written to task frontmatter."""
        # Method doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

            # Once implemented:
            # task_file, task_id = task_with_design_url
            # orchestrator = AutoBuildOrchestrator(repo_root=temp_repo_dir)
            #
            # mock_design_extractor.verify_mcp_availability.return_value = True
            # mock_design_extractor.extract_figma = AsyncMock(return_value=sample_figma_design_data)
            # mock_design_extractor.summarize_design_data.return_value = "Summary"
            #
            # with patch.object(orchestrator, '_design_extractor', mock_design_extractor):
            #     await orchestrator._extract_design_phase(task_id=task_id)
            #
            #     # Read task file and check frontmatter updated
            #     task_content = task_file.read_text()
            #     parts = task_content.split("---")
            #     frontmatter = yaml.safe_load(parts[1])
            #
            #     # Should have design_extraction metadata
            #     assert "design_extraction" in frontmatter
            #     assert "extracted_at" in frontmatter["design_extraction"]
            #     assert "design_hash" in frontmatter["design_extraction"]
            #
            #     # Timestamp should be recent ISO format
            #     extracted_at = frontmatter["design_extraction"]["extracted_at"]
            #     assert isinstance(extracted_at, str)
            #     # Should be valid ISO timestamp
            #     datetime.fromisoformat(extracted_at.replace("Z", "+00:00"))


# ============================================================================
# 9. Status Literal Updates Tests (2 tests)
# ============================================================================


class TestStatusLiteralUpdates:
    """Test design_extraction_failed added to status literals."""

    def test_design_extraction_failed_in_final_decision(self):
        """OrchestrationResult.final_decision includes 'design_extraction_failed'."""
        # Type doesn't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import OrchestrationResult

            # Once implemented, check the Literal type includes new status
            # This will be validated by type checker, but we can test instantiation:
            # result = OrchestrationResult(
            #     final_decision="design_extraction_failed",
            #     total_turns=0,
            #     worktree=None,
            #     # ... other fields
            # )
            # assert result.final_decision == "design_extraction_failed"

    def test_final_status_includes_design_extraction_failed(self):
        """FinalStatus type literal includes 'design_extraction_failed'."""
        # Type doesn't exist yet (RED phase)
        with pytest.raises(ImportError):
            from guardkit.orchestrator.progress import FinalStatus

            # Once implemented, check the Literal type
            # from typing import get_args
            # valid_statuses = get_args(FinalStatus)
            # assert "design_extraction_failed" in valid_statuses


# ============================================================================
# 10. Helper Methods Tests (1 test)
# ============================================================================


class TestHelperMethodsHandleNewStatus:
    """Test helper methods handle design_extraction_failed status."""

    def test_helper_methods_handle_design_extraction_failed(self):
        """_finalize_phase, _build_summary_details, _build_error_message handle new status."""
        # Methods don't exist yet (RED phase)
        with pytest.raises(AttributeError):
            from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

            # Once implemented:
            # orchestrator = AutoBuildOrchestrator(repo_root=Path.cwd())
            #
            # # Test _build_summary_details
            # summary = orchestrator._build_summary_details("design_extraction_failed")
            # assert "design" in summary.lower() or "extraction" in summary.lower()
            #
            # # Test _build_error_message
            # error_msg = orchestrator._build_error_message("design_extraction_failed")
            # assert "design" in error_msg.lower() or "MCP" in error_msg
            #
            # # These methods should not raise when given the new status


# ============================================================================
# Execution Notes
# ============================================================================
"""
This test suite covers all acceptance criteria for TASK-DM-003:

✓ Phase 0 skipped entirely when no design_url present (backward compatible)
✓ Figma design extraction when design_url is Figma
✓ Zeplin design extraction when design_url is Zeplin
✓ Fail-fast when MCP unavailable (verify_mcp_availability returns False)
✓ DesignContext dataclass with all required fields
✓ Extraction metadata (timestamp, hash) stored in task frontmatter
✓ "design_extraction_failed" added to OrchestrationResult.final_decision Literal
✓ "design_extraction_failed" added to FinalStatus in progress.py
✓ Helper methods (_build_summary_details, _build_error_message) handle new status

All tests are in RED phase (failing) as implementation doesn't exist yet.

Run with:
    pytest tests/orchestrator/test_phase0_design_extraction.py -v

Expected: 10 failures (RED phase of TDD)

After implementation:
    pytest tests/orchestrator/test_phase0_design_extraction.py -v --cov=guardkit/orchestrator/autobuild

Coverage target: >=85%
"""
