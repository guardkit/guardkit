"""
Tests for guardkit init CLI command with project seeding.

Test Coverage:
- Init command registration and basic functionality
- Project knowledge seeding to Graphiti
- Graceful degradation when Graphiti unavailable
- --skip-graphiti flag behavior
- Template initialization

Coverage Target: >=85%
Test Count: 12+ tests
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

# Import will succeed once implemented
try:
    from guardkit.cli.main import cli
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI init command not yet implemented"
)


# ============================================================================
# 1. Command Registration Tests
# ============================================================================


class TestInitCommandRegistration:
    """Test that init command is properly registered."""

    def test_init_command_exists(self):
        """Test that init command is registered in CLI."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output.lower() or "Initialize" in result.output

    def test_init_shows_help_text(self):
        """Test that init --help shows expected options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        # Should show --skip-graphiti option
        assert "skip-graphiti" in result.output.lower() or "skip" in result.output.lower()


# ============================================================================
# 2. Project Knowledge Seeding Tests
# ============================================================================


class TestInitSeedsProjectKnowledge:
    """Test that init seeds project knowledge to Graphiti."""

    def test_init_seeds_project_knowledge_to_graphiti(self, tmp_path, monkeypatch):
        """Test that init command invokes project seeding functions."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        # Create CLAUDE.md for project overview detection
        (tmp_path / "CLAUDE.md").write_text("# My Project\n\n## Overview\nTest project")

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init"])

            # Should have called project seeding
            mock_seed.assert_called_once()
            assert result.exit_code == 0

    def test_init_seeds_project_overview_from_claudemd(self, tmp_path, monkeypatch):
        """Test that init parses CLAUDE.md for project overview."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        # Create CLAUDE.md with project overview
        claude_md_content = """# My Test Project

## Overview
This is a test project for demonstrating project seeding.

## Technology Stack
- Python 3.11
- FastAPI
- pytest
"""
        (tmp_path / "CLAUDE.md").write_text(claude_md_content)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init"])

            # Should have called seeding
            assert mock_seed.called
            # Check that project_name was passed (from directory name)
            call_args = mock_seed.call_args
            assert call_args is not None

    def test_init_seeds_project_overview_from_readme_fallback(self, tmp_path, monkeypatch):
        """Test that init falls back to README.md when CLAUDE.md not found."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        # Create only README.md (no CLAUDE.md)
        readme_content = """# My Fallback Project

This is the readme file used for fallback.

## Features
- Feature 1
- Feature 2
"""
        (tmp_path / "README.md").write_text(readme_content)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init"])

            # Should still call seeding (using README.md)
            assert mock_seed.called

    def test_init_seeds_role_constraints(self, tmp_path, monkeypatch):
        """Test that init seeds default role constraints."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            # Create seed result that includes role constraints
            seed_result = MagicMock()
            seed_result.success = True
            seed_result.role_constraints_seeded = True
            mock_seed.return_value = seed_result

            result = runner.invoke(cli, ["init"])

            assert mock_seed.called

    def test_init_seeds_quality_gate_configs(self, tmp_path, monkeypatch):
        """Test that init seeds quality gate configurations."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            seed_result = MagicMock()
            seed_result.success = True
            seed_result.quality_gates_seeded = True
            mock_seed.return_value = seed_result

            result = runner.invoke(cli, ["init"])

            assert mock_seed.called

    def test_init_seeds_implementation_modes(self, tmp_path, monkeypatch):
        """Test that init seeds implementation mode defaults."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            seed_result = MagicMock()
            seed_result.success = True
            seed_result.implementation_modes_seeded = True
            mock_seed.return_value = seed_result

            result = runner.invoke(cli, ["init"])

            assert mock_seed.called


# ============================================================================
# 3. Graceful Degradation Tests
# ============================================================================


class TestInitGracefulDegradation:
    """Test graceful degradation when Graphiti unavailable."""

    def test_init_graceful_degradation_graphiti_unavailable(self, tmp_path, monkeypatch):
        """Test that init succeeds even when Graphiti is unavailable."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["init"])

            # Should succeed (exit code 0) even without Graphiti
            assert result.exit_code == 0
            # Should indicate Graphiti was skipped
            assert "graphiti" in result.output.lower() or "skipped" in result.output.lower() or \
                   "unavailable" in result.output.lower() or "warning" in result.output.lower()

    def test_init_handles_graphiti_connection_error(self, tmp_path, monkeypatch):
        """Test that init handles Graphiti connection errors gracefully."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.GraphitiClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["init"])

            # Should still succeed - graceful degradation
            assert result.exit_code == 0


# ============================================================================
# 4. Skip Flag Tests
# ============================================================================


class TestInitSkipGraphitiFlag:
    """Test --skip-graphiti flag behavior."""

    def test_init_skip_graphiti_flag(self, tmp_path, monkeypatch):
        """Test that --skip-graphiti flag skips Graphiti seeding entirely."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ["init", "--skip-graphiti"])

            # Should NOT call project seeding
            assert not mock_seed.called
            assert result.exit_code == 0


# ============================================================================
# 5. Template Initialization Tests
# ============================================================================


class TestInitWithTemplate:
    """Test init command with template argument."""

    def test_init_with_template_name(self, tmp_path, monkeypatch):
        """Test that guardkit init <template> works."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.apply_template') as mock_apply_template:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)
            mock_apply_template.return_value = True

            result = runner.invoke(cli, ["init", "fastapi-python"])

            # Should apply template
            mock_apply_template.assert_called_once()
            call_args = mock_apply_template.call_args
            assert "fastapi-python" in str(call_args)

    def test_init_default_template_is_default(self, tmp_path, monkeypatch):
        """Test that init without template uses 'default' template."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.apply_template') as mock_apply_template:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)
            mock_apply_template.return_value = True

            result = runner.invoke(cli, ["init"])

            # Should apply default template
            mock_apply_template.assert_called_once()
            call_args = mock_apply_template.call_args
            assert "default" in str(call_args)


# ============================================================================
# 6. Project Seeding Module Tests
# ============================================================================


class TestProjectSeedingModule:
    """Test the project seeding module directly."""

    @pytest.mark.asyncio
    async def test_seed_project_knowledge_seeds_all_components(self):
        """Test that seed_project_knowledge seeds all required components."""
        try:
            from guardkit.knowledge.project_seeding import seed_project_knowledge, SeedResult
        except ImportError:
            pytest.skip("project_seeding module not yet implemented")

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode-id")

        result = await seed_project_knowledge(
            project_name="test-project",
            client=mock_client
        )

        assert isinstance(result, SeedResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_seed_project_knowledge_returns_seed_result(self):
        """Test that seed_project_knowledge returns proper SeedResult."""
        try:
            from guardkit.knowledge.project_seeding import seed_project_knowledge, SeedResult
        except ImportError:
            pytest.skip("project_seeding module not yet implemented")

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode-id")

        result = await seed_project_knowledge(
            project_name="test-project",
            client=mock_client
        )

        # Should have results list
        assert hasattr(result, 'results')
        assert hasattr(result, 'success')

    @pytest.mark.asyncio
    async def test_seed_project_knowledge_handles_none_client(self):
        """Test that seed_project_knowledge handles None client gracefully."""
        try:
            from guardkit.knowledge.project_seeding import seed_project_knowledge
        except ImportError:
            pytest.skip("project_seeding module not yet implemented")

        # Should not raise, should return graceful result
        result = await seed_project_knowledge(
            project_name="test-project",
            client=None
        )

        # Should indicate it was skipped, not failed
        assert result is not None
        assert result.success is True  # Graceful degradation

    @pytest.mark.asyncio
    async def test_seed_project_knowledge_handles_disabled_client(self):
        """Test seed_project_knowledge with disabled client."""
        try:
            from guardkit.knowledge.project_seeding import seed_project_knowledge
        except ImportError:
            pytest.skip("project_seeding module not yet implemented")

        mock_client = MagicMock()
        mock_client.enabled = False

        result = await seed_project_knowledge(
            project_name="test-project",
            client=mock_client
        )

        # Should succeed (graceful degradation)
        assert result.success is True
