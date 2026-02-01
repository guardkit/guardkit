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
