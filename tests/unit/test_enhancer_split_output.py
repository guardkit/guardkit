"""
Unit Tests for Enhancer Split Output Support

TASK-PD-003: Tests for split-file enhancement mode
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add lib directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../installer/core/lib/agent_enhancement'))

from enhancer import SingleAgentEnhancer
from models import EnhancementResult, SplitContent


class TestEnhancementResultDataclass:
    """Test EnhancementResult dataclass properties."""

    def test_files_property_with_split_output(self):
        """Test files property returns both core and extended files in split mode."""
        result = EnhancementResult(
            success=True,
            agent_name="test-agent",
            sections=["section1"],
            templates=["template1"],
            examples=["example1"],
            diff="diff content",
            core_file=Path("core.md"),
            extended_file=Path("extended.md"),
            split_output=True
        )

        assert result.files == [Path("core.md"), Path("extended.md")]
        assert len(result.files) == 2

    def test_files_property_with_single_file_output(self):
        """Test files property returns only core file in single-file mode."""
        result = EnhancementResult(
            success=True,
            agent_name="test-agent",
            sections=["section1"],
            templates=["template1"],
            examples=["example1"],
            diff="diff content",
            core_file=Path("core.md"),
            extended_file=None,
            split_output=False
        )

        assert result.files == [Path("core.md")]
        assert len(result.files) == 1

    def test_files_property_with_error_case(self):
        """Test files property returns empty list when core_file is None (error case)."""
        result = EnhancementResult(
            success=False,
            agent_name="test-agent",
            sections=[],
            templates=[],
            examples=[],
            diff="",
            error="Enhancement failed",
            core_file=None,
            extended_file=None,
            split_output=False
        )

        assert result.files == []
        assert len(result.files) == 0


class TestEnhancerSplitOutput:
    """Test SingleAgentEnhancer split output functionality."""

    @pytest.fixture
    def mock_enhancer(self):
        """Create enhancer with mocked dependencies."""
        enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

        # Mock applier with both methods
        mock_applier = Mock()
        mock_applier.apply = Mock()
        mock_applier.apply_with_split = Mock(return_value=SplitContent(
            core_path=Path("agent.md"),
            extended_path=Path("agent-ext.md"),
            core_sections=["title", "quick_start"],
            extended_sections=["detailed_examples"]
        ))
        mock_applier.generate_diff = Mock(return_value="mock diff")

        enhancer._applier = mock_applier

        # Mock metadata loading
        enhancer._load_agent_metadata = Mock(return_value={
            "name": "test-agent",
            "description": "Test agent"
        })

        # Mock template discovery
        enhancer._discover_relevant_templates = Mock(return_value=[
            Path("template1.template")
        ])

        # Mock enhancement generation
        enhancer._generate_enhancement = Mock(return_value={
            "sections": ["title", "quick_start", "detailed_examples"],
            "title": "Test Agent",
            "quick_start": "Quick start content",
            "detailed_examples": "Detailed examples"
        })

        return enhancer

    def test_enhance_with_split_output_default(self, mock_enhancer, tmp_path):
        """Test enhancement with split output (default behavior)."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nContent")
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        result = mock_enhancer.enhance(agent_file, template_dir)

        # Verify split output was used
        assert result.success is True
        assert result.split_output is True
        assert result.core_file == Path("agent.md")
        assert result.extended_file == Path("agent-ext.md")

        # Verify apply_with_split was called
        mock_enhancer.applier.apply_with_split.assert_called_once()
        mock_enhancer.applier.apply.assert_not_called()

        # Verify files property
        assert len(result.files) == 2
        assert Path("agent.md") in result.files
        assert Path("agent-ext.md") in result.files

    def test_enhance_with_single_file_mode(self, mock_enhancer, tmp_path):
        """Test enhancement with single-file mode (backward compatible)."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nContent")
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        result = mock_enhancer.enhance(agent_file, template_dir, split_output=False)

        # Verify single-file mode was used
        assert result.success is True
        assert result.split_output is False
        assert result.core_file == agent_file
        assert result.extended_file is None

        # Verify apply was called (not apply_with_split)
        mock_enhancer.applier.apply.assert_called_once()
        mock_enhancer.applier.apply_with_split.assert_not_called()

        # Verify files property
        assert len(result.files) == 1
        assert agent_file in result.files

    def test_enhance_missing_apply_with_split_method(self, mock_enhancer, tmp_path):
        """Test error when apply_with_split not available (TASK-PD-001 not complete)."""
        # Remove apply_with_split method to simulate missing dependency
        delattr(mock_enhancer.applier, 'apply_with_split')

        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nContent")
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        result = mock_enhancer.enhance(agent_file, template_dir, split_output=True)

        # Verify error result
        assert result.success is False
        assert result.error is not None
        assert "TASK-PD-001" in result.error
        assert "apply_with_split" in result.error
        assert result.core_file is None
        assert result.extended_file is None

    def test_enhance_dry_run_with_split_output(self, tmp_path):
        """Test dry-run mode with split output (no files created)."""
        enhancer = SingleAgentEnhancer(strategy="static", dry_run=True, verbose=False)

        # Mock dependencies
        enhancer._load_agent_metadata = Mock(return_value={
            "name": "test-agent",
            "description": "Test agent"
        })
        enhancer._discover_relevant_templates = Mock(return_value=[Path("template1.template")])
        enhancer._generate_enhancement = Mock(return_value={
            "sections": ["title"],
            "title": "Test Agent"
        })

        mock_applier = Mock()
        mock_applier.generate_diff = Mock(return_value="mock diff")
        enhancer._applier = mock_applier

        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nContent")
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        result = enhancer.enhance(agent_file, template_dir, split_output=True)

        # Verify result paths are derived but no methods called
        assert result.success is True
        assert result.core_file == agent_file
        assert result.extended_file == tmp_path / "test-agent-ext.md"
        assert result.split_output is True

        # Verify no apply methods were called (dry-run)
        mock_applier.apply.assert_not_called()
        if hasattr(mock_applier, 'apply_with_split'):
            mock_applier.apply_with_split.assert_not_called()

    def test_enhance_dry_run_with_single_file(self, tmp_path):
        """Test dry-run mode with single-file output."""
        enhancer = SingleAgentEnhancer(strategy="static", dry_run=True, verbose=False)

        # Mock dependencies
        enhancer._load_agent_metadata = Mock(return_value={
            "name": "test-agent",
            "description": "Test agent"
        })
        enhancer._discover_relevant_templates = Mock(return_value=[Path("template1.template")])
        enhancer._generate_enhancement = Mock(return_value={
            "sections": ["title"],
            "title": "Test Agent"
        })

        mock_applier = Mock()
        mock_applier.generate_diff = Mock(return_value="mock diff")
        enhancer._applier = mock_applier

        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("# Test Agent\n\nContent")
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        result = enhancer.enhance(agent_file, template_dir, split_output=False)

        # Verify result
        assert result.success is True
        assert result.core_file == agent_file
        assert result.extended_file is None
        assert result.split_output is False

        # Verify no apply methods were called (dry-run)
        mock_applier.apply.assert_not_called()
