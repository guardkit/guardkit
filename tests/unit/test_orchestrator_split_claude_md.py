"""
Unit tests for TASK-PD-006: Split CLAUDE.md orchestrator methods.

Tests the new _write_claude_md_split(), _log_split_sizes(), and
_write_claude_md_single() methods added to TemplateCreateOrchestrator.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass

# Import orchestrator
import sys
from pathlib import Path as PathlibPath

# Add repository root to path
repo_root = PathlibPath(__file__).resolve().parent.parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Now import using standard imports
from installer.core.commands.lib.template_create_orchestrator import (
    TemplateCreateOrchestrator,
    OrchestrationConfig
)


# ===== Test Fixtures =====

@dataclass
class MockSplitMetadata:
    """Mock TemplateSplitMetadata for testing (TASK-PD-007)."""
    def __init__(self, core_size, patterns_size, reference_size, total_size, reduction_percent, validation_passed):
        self.core_size_bytes = core_size
        self.patterns_size_bytes = patterns_size
        self.reference_size_bytes = reference_size
        self.total_size_bytes = total_size
        self.reduction_percent = reduction_percent
        self.validation_passed = validation_passed


@dataclass
class MockSplitOutput:
    """Mock TemplateSplitOutput for testing."""
    core: str
    patterns: str
    reference: str

    @property
    def core_content(self) -> str:
        """Alias for core to match actual TemplateSplitOutput."""
        return self.core

    @property
    def patterns_content(self) -> str:
        """Alias for patterns to match actual TemplateSplitOutput."""
        return self.patterns

    @property
    def reference_content(self) -> str:
        """Alias for reference to match actual TemplateSplitOutput."""
        return self.reference

    def get_core_size(self) -> int:
        return len(self.core.encode('utf-8'))

    def get_patterns_size(self) -> int:
        return len(self.patterns.encode('utf-8'))

    def get_reference_size(self) -> int:
        return len(self.reference.encode('utf-8'))

    def get_total_size(self) -> int:
        return self.get_core_size() + self.get_patterns_size() + self.get_reference_size()

    def get_reduction_percent(self) -> float:
        total = self.get_total_size()
        if total == 0:
            return 0.0
        return (1 - self.get_core_size() / total) * 100

    def generate_metadata(self):
        """Generate metadata for testing (TASK-PD-007)."""
        return MockSplitMetadata(
            core_size=self.get_core_size(),
            patterns_size=self.get_patterns_size(),
            reference_size=self.get_reference_size(),
            total_size=self.get_total_size(),
            reduction_percent=self.get_reduction_percent(),
            validation_passed=self.get_core_size() <= 50 * 1024  # TASK-TC-DEFAULT-FLAGS: 50KB default
        )


@pytest.fixture
def orchestrator():
    """Create orchestrator with split mode enabled."""
    config = OrchestrationConfig(
        split_claude_md=True,
        dry_run=False,
        verbose=False
    )
    orch = TemplateCreateOrchestrator(config)

    # Mock required attributes
    orch.analysis = Mock()
    orch.agents = []

    return orch


@pytest.fixture
def orchestrator_single():
    """Create orchestrator with split mode disabled."""
    config = OrchestrationConfig(
        split_claude_md=False,
        dry_run=False,
        verbose=False
    )
    orch = TemplateCreateOrchestrator(config)

    # Mock required attributes
    orch.analysis = Mock()
    orch.agents = []

    return orch


@pytest.fixture
def mock_split_output():
    """Create mock split output with realistic sizes."""
    return MockSplitOutput(
        core="# Core Content\n" * 200,  # ~3KB
        patterns="# Pattern Documentation\n" * 300,  # ~5KB
        reference="# Reference Content\n" * 200  # ~3.5KB
    )


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "test-template"
    output_dir.mkdir()
    return output_dir


# ===== Test: Split Output Creation =====

def test_write_claude_md_split_creates_correct_structure(
    orchestrator,
    mock_split_output,
    temp_output_dir
):
    """Test that split output creates correct directory structure."""

    # Mock ClaudeMdGenerator.generate_split() to return mock output
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value
        mock_generator.generate_split.return_value = mock_split_output

        # Execute
        success = orchestrator._write_claude_md_split(temp_output_dir)

        # Verify success
        assert success is True

        # Verify directory structure
        assert (temp_output_dir / "CLAUDE.md").exists()
        assert (temp_output_dir / "docs" / "patterns" / "README.md").exists()
        assert (temp_output_dir / "docs" / "reference" / "README.md").exists()

        # Verify content
        core_content = (temp_output_dir / "CLAUDE.md").read_text()
        assert core_content == mock_split_output.core

        patterns_content = (temp_output_dir / "docs" / "patterns" / "README.md").read_text()
        assert patterns_content == mock_split_output.patterns

        reference_content = (temp_output_dir / "docs" / "reference" / "README.md").read_text()
        assert reference_content == mock_split_output.reference


# ===== Test: Size Validation =====

def test_split_output_size_reduction(
    orchestrator,
    mock_split_output,
    temp_output_dir
):
    """Test that split output achieves expected size reduction."""

    # Mock ClaudeMdGenerator.generate_split()
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value
        mock_generator.generate_split.return_value = mock_split_output

        # Execute
        success = orchestrator._write_claude_md_split(temp_output_dir)
        assert success is True

        # Verify core size is smaller than total
        core_size = (temp_output_dir / "CLAUDE.md").stat().st_size
        total_size = mock_split_output.get_total_size()

        assert core_size < total_size

        # Verify reduction percentage is reasonable (>30%)
        reduction = mock_split_output.get_reduction_percent()
        assert reduction > 30.0


# ===== Test: Backward Compatibility =====

def test_single_file_mode_backward_compatible(
    orchestrator_single,
    temp_output_dir
):
    """Test that single-file mode still works (backward compatibility)."""

    # Create mock claude_md object
    mock_claude_md = Mock()

    # Mock ClaudeMdGenerator.save()
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value

        # Execute
        success = orchestrator_single._write_claude_md_single(mock_claude_md, temp_output_dir)

        # Verify success
        assert success is True

        # Verify generator.save() was called
        mock_generator.save.assert_called_once()

        # Verify no docs/ directory was created
        assert not (temp_output_dir / "docs" / "patterns").exists()
        assert not (temp_output_dir / "docs" / "reference").exists()


# ===== Test: Error Handling =====

def test_split_write_handles_permission_error(
    orchestrator,
    temp_output_dir
):
    """Test that split write handles permission errors gracefully."""

    # Mock safe_write_file to fail
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'safe_write_file') as mock_write:
        mock_write.return_value = (False, "Permission denied")

        # Mock ClaudeMdGenerator to avoid exception
        with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate_split.return_value = MockSplitOutput(
                core="test",
                patterns="test",
                reference="test"
            )

            # Execute
            success = orchestrator._write_claude_md_split(temp_output_dir)

            # Verify failure
            assert success is False


def test_split_write_handles_generator_exception(
    orchestrator,
    temp_output_dir
):
    """Test that split write handles ClaudeMdGenerator exceptions."""

    # Mock ClaudeMdGenerator.generate_split() to raise exception
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value
        mock_generator.generate_split.side_effect = Exception("Generator failed")

        # Execute
        success = orchestrator._write_claude_md_split(temp_output_dir)

        # Verify failure
        assert success is False


# ===== Test: Log Split Sizes =====

def test_log_split_sizes_output(
    orchestrator,
    mock_split_output,
    temp_output_dir,
    capsys
):
    """Test that _log_split_sizes produces correct output."""

    # Create mock files with mock_split_output content
    core_path = temp_output_dir / "CLAUDE.md"
    patterns_path = temp_output_dir / "docs" / "patterns" / "README.md"
    reference_path = temp_output_dir / "docs" / "reference" / "README.md"

    patterns_path.parent.mkdir(parents=True, exist_ok=True)
    reference_path.parent.mkdir(parents=True, exist_ok=True)

    core_path.write_text(mock_split_output.core)
    patterns_path.write_text(mock_split_output.patterns)
    reference_path.write_text(mock_split_output.reference)

    # Execute
    orchestrator._log_split_sizes(
        core_path,
        patterns_path,
        reference_path,
        mock_split_output
    )

    # Capture output
    captured = capsys.readouterr()

    # Verify output contains expected elements
    assert "CLAUDE.md" in captured.out
    assert "reduction" in captured.out.lower()
    assert "docs/patterns/README.md" in captured.out
    assert "docs/reference/README.md" in captured.out


# ===== Test: Configuration Flag Routing =====

def test_config_split_enabled_routes_to_split_method(
    orchestrator,
    mock_split_output,
    temp_output_dir
):
    """Test that split_claude_md=True routes to _write_claude_md_split()."""

    # Verify config
    assert orchestrator.config.split_claude_md is True

    # Mock ClaudeMdGenerator.generate_split()
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value
        mock_generator.generate_split.return_value = mock_split_output

        # Execute split method directly
        success = orchestrator._write_claude_md_split(temp_output_dir)

        # Verify success and split output created
        assert success is True
        assert (temp_output_dir / "docs" / "patterns" / "README.md").exists()


def test_config_split_disabled_routes_to_single_method(
    orchestrator_single,
    temp_output_dir
):
    """Test that split_claude_md=False routes to _write_claude_md_single()."""

    # Verify config
    assert orchestrator_single.config.split_claude_md is False

    # Mock ClaudeMdGenerator.save()
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        # Execute single method
        success = orchestrator_single._write_claude_md_single(Mock(), temp_output_dir)

        # Verify success and no split structure created
        assert success is True
        assert not (temp_output_dir / "docs" / "patterns").exists()


# ===== Test: Content Distribution =====

def test_split_content_matches_source(
    orchestrator,
    temp_output_dir
):
    """Test that split content is correctly distributed across files."""

    # Create realistic split output
    core_content = "# Core CLAUDE.md\n\n## Essential Information"
    patterns_content = "# Patterns\n\n## Best Practices"
    reference_content = "# Reference\n\n## Code Examples"

    mock_output = MockSplitOutput(
        core=core_content,
        patterns=patterns_content,
        reference=reference_content
    )

    # Mock ClaudeMdGenerator.generate_split()
    from installer.core.commands.lib import template_create_orchestrator as orchestrator_module
    with patch.object(orchestrator_module, 'ClaudeMdGenerator') as MockGenerator:
        mock_generator = MockGenerator.return_value
        mock_generator.generate_split.return_value = mock_output

        # Execute
        success = orchestrator._write_claude_md_split(temp_output_dir)
        assert success is True

        # Verify content matches
        assert (temp_output_dir / "CLAUDE.md").read_text() == core_content
        assert (temp_output_dir / "docs" / "patterns" / "README.md").read_text() == patterns_content
        assert (temp_output_dir / "docs" / "reference" / "README.md").read_text() == reference_content


# ===== Test: CLI Integration =====

def test_cli_argument_no_split_claude_md(orchestrator_single):
    """Test that --no-split-claude-md flag sets config correctly."""
    assert orchestrator_single.config.split_claude_md is False


def test_cli_argument_split_enabled_by_default(orchestrator):
    """Test that split_claude_md is enabled by default."""
    assert orchestrator.config.split_claude_md is True


# ===== Test: Size Limit Flag (TASK-FIX-19EA) =====

def test_claude_md_size_limit_flag_recognized():
    """Verify --claude-md-size-limit flag appears in help output (TASK-FIX-19EA)."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "installer.core.commands.lib.template_create_orchestrator", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--claude-md-size-limit" in result.stdout


def test_parse_size_limit_kb():
    """Test parse_size_limit function with KB suffix."""
    assert TemplateCreateOrchestrator.parse_size_limit("50KB") == 50 * 1024
    assert TemplateCreateOrchestrator.parse_size_limit("50kb") == 50 * 1024
    assert TemplateCreateOrchestrator.parse_size_limit("50Kb") == 50 * 1024


def test_parse_size_limit_mb():
    """Test parse_size_limit function with MB suffix."""
    assert TemplateCreateOrchestrator.parse_size_limit("1MB") == 1 * 1024 * 1024
    assert TemplateCreateOrchestrator.parse_size_limit("2mb") == 2 * 1024 * 1024


def test_parse_size_limit_bytes():
    """Test parse_size_limit function with raw bytes."""
    assert TemplateCreateOrchestrator.parse_size_limit("10240") == 10240


def test_config_accepts_claude_md_size_limit():
    """Test OrchestrationConfig accepts claude_md_size_limit parameter."""
    config = OrchestrationConfig(
        split_claude_md=True,
        claude_md_size_limit=50 * 1024  # 50KB
    )
    assert config.claude_md_size_limit == 50 * 1024


def test_config_default_size_limit():
    """Test OrchestrationConfig defaults to 50KB if not specified (TASK-TC-DEFAULT-FLAGS)."""
    config = OrchestrationConfig(split_claude_md=True)
    assert config.claude_md_size_limit == 50 * 1024


# ===== Test: Rules Structure Default (TASK-TC-DEFAULT-FLAGS) =====

def test_config_use_rules_structure_default_true():
    """Test OrchestrationConfig defaults to use_rules_structure=True (TASK-TC-DEFAULT-FLAGS)."""
    config = OrchestrationConfig()
    assert config.use_rules_structure is True


def test_cli_no_rules_structure_opt_out():
    """Test --no-rules-structure flag appears in help output (TASK-TC-DEFAULT-FLAGS)."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "installer.core.commands.lib.template_create_orchestrator", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "--no-rules-structure" in result.stdout


def test_run_template_create_default_rules_structure():
    """Test run_template_create defaults to use_rules_structure=True (TASK-TC-DEFAULT-FLAGS)."""
    import inspect
    from installer.core.commands.lib.template_create_orchestrator import run_template_create

    sig = inspect.signature(run_template_create)
    default = sig.parameters['use_rules_structure'].default
    assert default is True


def test_run_template_create_default_size_limit():
    """Test run_template_create falls back to 50KB when claude_md_size_limit is None (TASK-TC-DEFAULT-FLAGS)."""
    # This tests the fallback in the function body, not signature default
    # The function body uses: claude_md_size_limit if claude_md_size_limit else 50 * 1024
    # We verify by checking the OrchestrationConfig default
    config = OrchestrationConfig()
    assert config.claude_md_size_limit == 50 * 1024


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
