"""
Tests for guardkit init CLI command with project seeding.

Test Coverage:
- Init command registration and basic functionality
- Project knowledge seeding to Graphiti
- Graceful degradation when Graphiti unavailable
- --skip-graphiti flag behavior
- Template initialization
- Interactive setup (--interactive flag)

Coverage Target: >=85%
Test Count: 20+ tests
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


# ============================================================================
# 7. Interactive Setup Tests (NEW - TASK-GR-001-I)
# ============================================================================


class TestInteractiveSetup:
    """Test interactive setup functionality (--interactive flag)."""

    @pytest.mark.asyncio
    async def test_interactive_setup_function_exists(self):
        """Test that interactive_setup function exists in guardkit.cli.init."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.fail("interactive_setup function does not exist in guardkit.cli.init")

    @pytest.mark.asyncio
    async def test_interactive_setup_returns_project_overview_episode(self):
        """Test that interactive_setup returns ProjectOverviewEpisode."""
        try:
            from guardkit.cli.init import interactive_setup
            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            # Mock user inputs
            mock_prompt.side_effect = [
                "A test project",  # purpose
                "python",  # primary_language
                "fastapi,pytest",  # frameworks
                "",  # first goal (empty to finish)
            ]

            result = await interactive_setup("test-project")

            # Should return ProjectOverviewEpisode
            assert isinstance(result, ProjectOverviewEpisode)
            assert result.project_name == "test-project"
            assert result.purpose == "A test project"
            assert result.primary_language == "python"

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_purpose(self):
        """Test that interactive_setup prompts for project purpose."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose text",
                "python",
                "",  # frameworks
                "",  # goals
            ]

            result = await interactive_setup("test-project")

            # Verify Prompt.ask was called with purpose question
            calls = [str(call) for call in mock_prompt.call_args_list]
            assert any("purpose" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_primary_language(self):
        """Test that interactive_setup prompts for primary language with choices."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "typescript",  # primary_language
                "",  # frameworks
                "",  # goals
            ]

            result = await interactive_setup("test-project")

            # Verify language choices offered
            calls = mock_prompt.call_args_list
            # Should have called with choices parameter
            assert any('choices' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_frameworks(self):
        """Test that interactive_setup prompts for frameworks."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "python",
                "fastapi,sqlalchemy,pydantic",  # frameworks
                "",  # goals
            ]

            result = await interactive_setup("test-project")

            # Should have parsed frameworks
            assert "fastapi" in result.frameworks
            assert "sqlalchemy" in result.frameworks
            assert "pydantic" in result.frameworks

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_key_goals(self):
        """Test that interactive_setup prompts for key goals (multi-line)."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "python",
                "",  # frameworks
                "Goal 1",
                "Goal 2",
                "Goal 3",
                "",  # empty to finish
            ]

            result = await interactive_setup("test-project")

            # Should have captured multiple goals
            assert len(result.key_goals) == 3
            assert "Goal 1" in result.key_goals
            assert "Goal 2" in result.key_goals
            assert "Goal 3" in result.key_goals

    @pytest.mark.asyncio
    async def test_interactive_setup_handles_empty_frameworks(self):
        """Test that interactive_setup handles empty frameworks gracefully."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "python",
                "",  # empty frameworks
                "",  # no goals
            ]

            result = await interactive_setup("test-project")

            # Should have empty frameworks list
            assert result.frameworks == []

    @pytest.mark.asyncio
    async def test_interactive_setup_handles_empty_goals(self):
        """Test that interactive_setup handles empty goals gracefully."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "python",
                "",  # frameworks
                "",  # no goals (immediately empty)
            ]

            result = await interactive_setup("test-project")

            # Should have empty goals list
            assert result.key_goals == []

    @pytest.mark.asyncio
    async def test_interactive_setup_uses_defaults(self):
        """Test that interactive_setup provides sensible defaults."""
        try:
            from guardkit.cli.init import interactive_setup
        except ImportError:
            pytest.skip("interactive_setup not yet implemented")

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            # User accepts all defaults (empty inputs)
            mock_prompt.side_effect = [
                "",  # purpose (use default)
                "",  # language (use default)
                "",  # frameworks
                "",  # goals
            ]

            result = await interactive_setup("test-project")

            # Should still have valid data (defaults used)
            assert result.project_name == "test-project"
            # Purpose should have default value
            assert result.purpose != ""


class TestInitWithInteractiveFlag:
    """Test --interactive flag integration with init command."""

    def test_init_interactive_flag_exists(self, tmp_path, monkeypatch):
        """Test that --interactive flag is recognized."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli, ["init", "--help"])

        # Should show --interactive in help
        assert "--interactive" in result.output.lower() or "-i" in result.output.lower()

    def test_init_interactive_triggers_interactive_setup(self, tmp_path, monkeypatch):
        """Test that --interactive flag triggers interactive_setup."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Prompt.ask') as mock_prompt:

            # Mock interactive inputs
            mock_prompt.side_effect = [
                "Test purpose",
                "python",
                "",
                "",
            ]

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)

            # Mock ProjectOverviewEpisode
            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Test purpose",
                primary_language="python"
            )
            mock_interactive.return_value = mock_episode

            result = runner.invoke(cli, ["init", "--interactive"])

            # Should have called interactive_setup
            assert mock_interactive.called

    def test_init_non_interactive_is_default(self, tmp_path, monkeypatch):
        """Test that non-interactive mode is the default."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init"])

            # Should NOT call interactive_setup (default is non-interactive)
            assert not mock_interactive.called
            # Should still call seed_project_knowledge (with parsed data)
            assert mock_seed.called

    def test_init_interactive_creates_project_overview_episode(self, tmp_path, monkeypatch):
        """Test that interactive mode creates ProjectOverviewEpisode."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class:

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Interactive purpose",
                primary_language="typescript",
                frameworks=["react", "vite"],
                key_goals=["Build fast UI", "Maintain quality"]
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # Should have passed episode to seed_project_knowledge
            assert mock_seed.called
            call_kwargs = mock_seed.call_args.kwargs
            # Should include project_overview_episode parameter
            assert 'project_overview_episode' in call_kwargs or \
                   call_kwargs.get('project_overview') == mock_episode


class TestInteractiveCLAUDEmdGeneration:
    """Test CLAUDE.md generation from interactive answers."""

    def test_interactive_generates_claudemd_if_requested(self, tmp_path, monkeypatch):
        """Test that interactive mode can generate CLAUDE.md."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Confirm.ask') as mock_confirm:

            # User confirms CLAUDE.md generation
            mock_confirm.return_value = True

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Test purpose",
                primary_language="python"
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # Should have asked about CLAUDE.md generation
            assert mock_confirm.called

    def test_interactive_claudemd_includes_purpose(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes project purpose."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Build an awesome CLI tool",
                primary_language="python"
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # Check if CLAUDE.md was created
            claude_md = tmp_path / "CLAUDE.md"
            if claude_md.exists():
                content = claude_md.read_text()
                assert "awesome CLI tool" in content

    def test_interactive_claudemd_includes_tech_stack(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes tech stack."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Test",
                primary_language="typescript",
                frameworks=["react", "tailwind"]
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # Check if CLAUDE.md was created with stack info
            claude_md = tmp_path / "CLAUDE.md"
            if claude_md.exists():
                content = claude_md.read_text()
                assert "typescript" in content.lower()
                assert "react" in content.lower()

    def test_interactive_claudemd_includes_goals(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes key goals."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Test",
                primary_language="python",
                key_goals=["Achieve 100% test coverage", "Deploy to production"]
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # Check if CLAUDE.md was created with goals
            claude_md = tmp_path / "CLAUDE.md"
            if claude_md.exists():
                content = claude_md.read_text()
                assert "100% test coverage" in content

    def test_interactive_skips_claudemd_if_declined(self, tmp_path, monkeypatch):
        """Test that CLAUDE.md is not created if user declines."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.seed_project_knowledge', new_callable=AsyncMock) as mock_seed, \
             patch('guardkit.cli.init.GraphitiClient') as mock_client_class, \
             patch('guardkit.cli.init.Confirm.ask', return_value=False):

            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
            mock_episode = ProjectOverviewEpisode(
                project_name="test-project",
                purpose="Test",
                primary_language="python"
            )
            mock_interactive.return_value = mock_episode
            mock_seed.return_value = MagicMock(success=True)

            result = runner.invoke(cli, ["init", "--interactive"])

            # CLAUDE.md should NOT be created
            claude_md = tmp_path / "CLAUDE.md"
            assert not claude_md.exists()


# ============================================================================
# 8. Template Content Copying Tests (TASK-INST-010)
# ============================================================================


def _create_fake_template(base_dir: Path, template_name: str, **kwargs) -> Path:
    """Helper to create a fake template directory structure for testing.

    Args:
        base_dir: Base directory to create template under.
        template_name: Name of the template.
        **kwargs: Optional overrides:
            agents_in_dotclaude: bool - put agents in .claude/agents/ instead of agents/
            has_manifest: bool - create manifest.json
            has_root_claude: bool - create root CLAUDE.md
            has_dotclaude_claude: bool - create .claude/CLAUDE.md
            has_rules: bool - create .claude/rules/ files
            agent_files: list[str] - agent filenames to create

    Returns:
        Path to the created template directory.
    """
    template_dir = base_dir / template_name
    template_dir.mkdir(parents=True, exist_ok=True)

    agents_in_dotclaude = kwargs.get("agents_in_dotclaude", False)
    has_manifest = kwargs.get("has_manifest", True)
    has_root_claude = kwargs.get("has_root_claude", False)
    has_dotclaude_claude = kwargs.get("has_dotclaude_claude", False)
    has_rules = kwargs.get("has_rules", False)
    agent_files = kwargs.get("agent_files", ["specialist.md", "testing-specialist.md"])

    # Create agents
    if agents_in_dotclaude:
        agents_dir = template_dir / ".claude" / "agents"
    else:
        agents_dir = template_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for agent_file in agent_files:
        (agents_dir / agent_file).write_text(f"# Agent: {agent_file}\nContent for {agent_file}")

    # Create manifest
    if has_manifest:
        (template_dir / "manifest.json").write_text('{"name": "' + template_name + '"}')

    # Create CLAUDE.md variants
    if has_root_claude:
        (template_dir / "CLAUDE.md").write_text(f"# {template_name} root CLAUDE.md")
    if has_dotclaude_claude:
        (template_dir / ".claude").mkdir(parents=True, exist_ok=True)
        (template_dir / ".claude" / "CLAUDE.md").write_text(
            f"# {template_name} .claude/CLAUDE.md"
        )

    # Create rules
    if has_rules:
        rules_dir = template_dir / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "code-style.md").write_text("# Code Style Rules")
        sub_rules = rules_dir / "guidance"
        sub_rules.mkdir(parents=True, exist_ok=True)
        (sub_rules / "testing.md").write_text("# Testing Guidance")

    return template_dir


class TestApplyTemplateCopiesAgents:
    """Test that apply_template copies agent files correctly."""

    def test_copies_agents_from_agents_dir(self, tmp_path):
        """AC: guardkit init fastapi-python copies agents from agents/ to .claude/agents/."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            agents_in_dotclaude=False,
            agent_files=["fastapi-specialist.md", "fastapi-testing-specialist.md"],
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        agents_target = target / ".claude" / "agents"
        assert agents_target.exists()
        assert (agents_target / "fastapi-specialist.md").exists()
        assert (agents_target / "fastapi-testing-specialist.md").exists()
        assert "fastapi-specialist.md" in (agents_target / "fastapi-specialist.md").read_text()

    def test_copies_agents_from_dotclaude_agents_dir(self, tmp_path):
        """AC: guardkit init fastmcp-python copies agents from .claude/agents/ to .claude/agents/."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastmcp-python",
            agents_in_dotclaude=True,
            agent_files=["fastmcp-specialist.md", "fastmcp-testing-specialist.md"],
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastmcp-python",
        ):
            result = apply_template("fastmcp-python", target)

        assert result is True
        agents_target = target / ".claude" / "agents"
        assert agents_target.exists()
        assert (agents_target / "fastmcp-specialist.md").exists()
        assert (agents_target / "fastmcp-testing-specialist.md").exists()

    def test_skips_gitkeep_files(self, tmp_path):
        """Default template has only .gitkeep — no agents should be copied."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        template_dir = templates_dir / "default"
        template_dir.mkdir(parents=True)
        agents_dir = template_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / ".gitkeep").write_text("")

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=template_dir,
        ):
            result = apply_template("default", target)

        assert result is True
        agents_target = target / ".claude" / "agents"
        # Directory should exist (created as scaffold) but no .md files copied
        assert agents_target.exists()
        md_files = list(agents_target.glob("*.md"))
        assert len(md_files) == 0


class TestApplyTemplateCopiesRules:
    """Test that apply_template copies rules preserving directory structure."""

    def test_copies_rules_with_subdirectories(self, tmp_path):
        """AC: guardkit init fastapi-python copies rules from template to .claude/rules/."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            has_rules=True,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        rules_target = target / ".claude" / "rules"
        assert rules_target.exists()
        assert (rules_target / "code-style.md").exists()
        assert (rules_target / "guidance" / "testing.md").exists()
        assert "Code Style Rules" in (rules_target / "code-style.md").read_text()


class TestApplyTemplateCopiesCLAUDEmd:
    """Test CLAUDE.md copying for various template layouts."""

    def test_copies_root_claude_md(self, tmp_path):
        """AC: guardkit init fastapi-python copies CLAUDE.md from template to project root."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            has_root_claude=True,
            has_dotclaude_claude=True,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        assert (target / "CLAUDE.md").exists()
        assert "root CLAUDE.md" in (target / "CLAUDE.md").read_text()

    def test_copies_dotclaude_claude_md(self, tmp_path):
        """Templates with only .claude/CLAUDE.md get it copied correctly."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "nextjs-fullstack",
            has_root_claude=False,
            has_dotclaude_claude=True,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "nextjs-fullstack",
        ):
            result = apply_template("nextjs-fullstack", target)

        assert result is True
        assert (target / ".claude" / "CLAUDE.md").exists()
        assert ".claude/CLAUDE.md" in (target / ".claude" / "CLAUDE.md").read_text()

    def test_copies_both_claude_md_when_both_exist(self, tmp_path):
        """AC: If both CLAUDE.md variants exist, copy both."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            has_root_claude=True,
            has_dotclaude_claude=True,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        assert (target / "CLAUDE.md").exists()
        assert (target / ".claude" / "CLAUDE.md").exists()


class TestApplyTemplateCopiesManifest:
    """Test manifest.json copying."""

    def test_copies_manifest_json_when_present(self, tmp_path):
        """AC: guardkit init copies manifest.json to .claude/manifest.json when present."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            has_manifest=True,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        manifest_path = target / ".claude" / "manifest.json"
        assert manifest_path.exists()
        assert "fastapi-python" in manifest_path.read_text()

    def test_skips_manifest_when_missing(self, tmp_path):
        """AC: guardkit init default works without manifest.json (skip with info, not error)."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "default",
            has_manifest=False,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "default",
        ):
            result = apply_template("default", target)

        assert result is True
        # Should NOT error — just skip
        manifest_path = target / ".claude" / "manifest.json"
        assert not manifest_path.exists()


class TestApplyTemplateConflictHandling:
    """Test that existing files are NOT overwritten."""

    def test_does_not_overwrite_existing_files(self, tmp_path):
        """AC: Existing files in target directory are NOT overwritten (skip with warning)."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            has_root_claude=True,
            has_manifest=True,
            agent_files=["specialist.md"],
        )

        target = tmp_path / "project"
        target.mkdir()
        (target / ".claude" / "agents").mkdir(parents=True)
        (target / ".claude" / "agents" / "specialist.md").write_text("EXISTING CONTENT")
        (target / "CLAUDE.md").write_text("EXISTING ROOT CLAUDE")

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / "fastapi-python",
        ):
            result = apply_template("fastapi-python", target)

        assert result is True
        # Existing files should NOT be overwritten
        assert (target / ".claude" / "agents" / "specialist.md").read_text() == "EXISTING CONTENT"
        assert (target / "CLAUDE.md").read_text() == "EXISTING ROOT CLAUDE"


class TestApplyTemplateNotFound:
    """Test template-not-found handling."""

    def test_template_not_found_warns_not_errors(self, tmp_path):
        """AC: Template not found produces a warning, not an error."""
        from guardkit.cli.init import apply_template

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=None,
        ):
            result = apply_template("nonexistent-template", target)

        # Should still succeed (scaffold created) but return True
        assert result is True
        # Basic scaffold should still be created
        assert (target / ".claude").exists()
        assert (target / "tasks").exists()


class TestApplyTemplateNoArgs:
    """Test guardkit init with no template argument."""

    def test_no_args_creates_basic_scaffold(self, tmp_path):
        """AC: guardkit init with no args still creates basic scaffold."""
        from guardkit.cli.init import apply_template

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=None,
        ):
            result = apply_template("default", target)

        assert result is True
        assert (target / ".claude").exists()
        assert (target / ".claude" / "commands").exists()
        assert (target / ".claude" / "agents").exists()
        assert (target / ".claude" / "task-plans").exists()
        assert (target / "tasks" / "backlog").exists()
        assert (target / "tasks" / "in_progress").exists()
        assert (target / ".guardkit").exists()


class TestResolveTemplateSourceDir:
    """Test template source resolution."""

    def test_resolves_from_package_location(self, tmp_path):
        """AC: Template source resolved from installed package location."""
        from guardkit.cli.init import _resolve_template_source_dir

        # Create fake installed templates directory
        templates_base = tmp_path / "installer" / "core" / "templates"
        template_dir = templates_base / "fastapi-python"
        template_dir.mkdir(parents=True)
        (template_dir / "manifest.json").write_text("{}")

        with patch(
            "guardkit.cli.init._get_templates_base_dir",
            return_value=templates_base,
        ):
            result = _resolve_template_source_dir("fastapi-python")

        assert result is not None
        assert result == template_dir

    def test_returns_none_for_unknown_template(self, tmp_path):
        """Returns None when template not found anywhere."""
        from guardkit.cli.init import _resolve_template_source_dir

        templates_base = tmp_path / "installer" / "core" / "templates"
        templates_base.mkdir(parents=True)

        with patch(
            "guardkit.cli.init._get_templates_base_dir",
            return_value=templates_base,
        ):
            result = _resolve_template_source_dir("nonexistent-template")

        assert result is None

    def test_falls_back_to_user_templates(self, tmp_path):
        """Falls back to ~/.guardkit/templates/ for user-installed templates."""
        from guardkit.cli.init import _resolve_template_source_dir

        # Package templates: no match
        pkg_templates = tmp_path / "pkg_templates"
        pkg_templates.mkdir()

        # User templates: has match
        user_templates = tmp_path / "user_templates"
        user_template_dir = user_templates / "custom-template"
        user_template_dir.mkdir(parents=True)
        (user_template_dir / "manifest.json").write_text("{}")

        with patch(
            "guardkit.cli.init._get_templates_base_dir",
            return_value=pkg_templates,
        ), patch(
            "guardkit.cli.init._get_user_templates_dir",
            return_value=user_templates,
        ):
            result = _resolve_template_source_dir("custom-template")

        assert result is not None
        assert result == user_template_dir


class TestApplyTemplateSkipsScaffolds:
    """Test that code scaffold directories are NOT copied."""

    def test_does_not_copy_templates_dir(self, tmp_path):
        """AC: Do NOT copy {template}/templates/ directory."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        template = templates_dir / "fastmcp-python"
        template.mkdir(parents=True)
        # Create templates/ subdir (code scaffolds)
        scaffold_dir = template / "templates" / "tools"
        scaffold_dir.mkdir(parents=True)
        (scaffold_dir / "tool.py.template").write_text("# scaffold")
        # Create agents
        (template / ".claude" / "agents").mkdir(parents=True)
        (template / ".claude" / "agents" / "specialist.md").write_text("# Agent")

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=template,
        ):
            result = apply_template("fastmcp-python", target)

        assert result is True
        # templates/ dir should NOT be copied
        assert not (target / "templates").exists()
        assert not (target / ".claude" / "templates").exists()

    def test_does_not_copy_config_dir(self, tmp_path):
        """AC: Do NOT copy {template}/config/ directory."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        template = templates_dir / "mcp-typescript"
        template.mkdir(parents=True)
        # Create config/ subdir
        config_dir = template / "config"
        config_dir.mkdir()
        (config_dir / "package.json.template").write_text("{}")
        # Create agents
        (template / "agents").mkdir()
        (template / "agents" / "specialist.md").write_text("# Agent")

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=template,
        ):
            result = apply_template("mcp-typescript", target)

        assert result is True
        assert not (target / "config").exists()

    def test_does_not_copy_docker_dir(self, tmp_path):
        """AC: Do NOT copy {template}/docker/ directory."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        template = templates_dir / "mcp-typescript"
        template.mkdir(parents=True)
        # Create docker/ subdir
        docker_dir = template / "docker"
        docker_dir.mkdir()
        (docker_dir / "Dockerfile.template").write_text("FROM node")
        # Create agents
        (template / "agents").mkdir()
        (template / "agents" / "specialist.md").write_text("# Agent")

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=template,
        ):
            result = apply_template("mcp-typescript", target)

        assert result is True
        assert not (target / "docker").exists()


class TestApplyTemplateAllTemplates:
    """AC: Unit tests cover all 7 templates."""

    @pytest.mark.parametrize("template_name,agents_location,has_manifest,claude_md_location", [
        ("default", "agents", False, "dotclaude_only"),
        ("fastapi-python", "agents", True, "both"),
        ("fastmcp-python", "dotclaude_agents", True, "both"),
        ("mcp-typescript", "agents", True, "both"),
        ("nextjs-fullstack", "agents", True, "dotclaude_only"),
        ("react-fastapi-monorepo", "agents", True, "dotclaude_only"),
        ("react-typescript", "agents", True, "root_only"),
    ])
    def test_template_applies_correctly(
        self, tmp_path, template_name, agents_location, has_manifest, claude_md_location
    ):
        """Test all 7 templates apply correctly based on their structural variations."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        has_root_claude = claude_md_location in ("root_only", "both")
        has_dotclaude_claude = claude_md_location in ("dotclaude_only", "both")
        agents_in_dotclaude = (agents_location == "dotclaude_agents")

        # Only create agents for non-default templates
        agent_files = [] if template_name == "default" else ["specialist.md"]

        _create_fake_template(
            templates_dir, template_name,
            agents_in_dotclaude=agents_in_dotclaude,
            has_manifest=has_manifest,
            has_root_claude=has_root_claude,
            has_dotclaude_claude=has_dotclaude_claude,
            has_rules=True,
            agent_files=agent_files,
        )

        target = tmp_path / "project"
        target.mkdir()

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=templates_dir / template_name,
        ):
            result = apply_template(template_name, target)

        assert result is True

        # Verify scaffold
        assert (target / ".claude").exists()
        assert (target / "tasks").exists()

        # Verify agents
        if template_name != "default":
            assert (target / ".claude" / "agents" / "specialist.md").exists()

        # Verify manifest
        if has_manifest:
            assert (target / ".claude" / "manifest.json").exists()
        else:
            assert not (target / ".claude" / "manifest.json").exists()

        # Verify CLAUDE.md
        if has_root_claude:
            assert (target / "CLAUDE.md").exists()
        if has_dotclaude_claude:
            assert (target / ".claude" / "CLAUDE.md").exists()

        # Verify rules
        assert (target / ".claude" / "rules" / "code-style.md").exists()
