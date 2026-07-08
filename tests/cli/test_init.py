"""
Tests for guardkit init CLI command.

Post-FEAT-MEM-09 graphiti-code cutover: `guardkit init` no longer seeds
Graphiti / writes graphiti.yaml / writes MCP config / performs LLM-reachability
checks. It ONLY: applies the template, installs the features/conftest.py bridge,
optionally runs interactive CLAUDE.md generation, and prints a summary.

Test Coverage:
- Init command registration and basic functionality
- Template application (apply_template, extends chain, pattern layer, base-only)
- Template source resolution
- Interactive setup (--interactive flag) -> _ProjectInfo -> CLAUDE.md
- Logger suppression (httpx/httpcore)

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
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
        """Test that init --help shows the surviving options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        # Should show the kept options
        assert "--interactive" in result.output
        assert "--base-only" in result.output


# ============================================================================
# 2. Plain init invocation
# ============================================================================


class TestInitInvocation:
    """Test the plain `guardkit init [template]` invocation."""

    def test_init_succeeds(self, tmp_path, monkeypatch):
        """Test that `guardkit init` succeeds (exit code 0)."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        # Scaffold should be created
        assert (tmp_path / ".claude").exists()
        assert (tmp_path / "tasks").exists()

    def test_init_prints_success_summary(self, tmp_path, monkeypatch):
        """Test that init prints its success summary and next steps."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert "initialized successfully" in result.output.lower()
        assert "task-create" in result.output

    def test_init_does_not_write_graphiti_yaml(self, tmp_path, monkeypatch):
        """Test that init no longer writes .guardkit/graphiti.yaml."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert not (tmp_path / ".guardkit" / "graphiti.yaml").exists()

    def test_init_does_not_write_mcp_json(self, tmp_path, monkeypatch):
        """Test that init no longer writes .mcp.json."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert not (tmp_path / ".mcp.json").exists()


# ============================================================================
# 3. Template Initialization Tests
# ============================================================================


class TestInitWithTemplate:
    """Test init command with template argument."""

    def test_init_with_template_name(self, tmp_path, monkeypatch):
        """Test that guardkit init <template> works."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init.apply_template") as mock_apply_template:
            mock_apply_template.return_value = True

            result = runner.invoke(cli, ["init", "fastapi-python"])

            assert result.exit_code == 0
            # Should apply template
            mock_apply_template.assert_called_once()
            call_args = mock_apply_template.call_args
            assert "fastapi-python" in str(call_args)

    def test_init_default_template_is_default(self, tmp_path, monkeypatch):
        """Test that init without template uses 'default' template."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init.apply_template") as mock_apply_template:
            mock_apply_template.return_value = True

            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            # Should apply default template
            mock_apply_template.assert_called_once()
            call_args = mock_apply_template.call_args
            assert "default" in str(call_args)


# ============================================================================
# 4. Interactive Setup Tests
# ============================================================================


class TestInteractiveSetup:
    """Test interactive setup functionality (--interactive flag)."""

    @pytest.mark.asyncio
    async def test_interactive_setup_function_exists(self):
        """Test that interactive_setup function exists in guardkit.cli.init."""
        try:
            from guardkit.cli.init import interactive_setup  # noqa: F401
        except ImportError:
            pytest.fail("interactive_setup function does not exist in guardkit.cli.init")

    @pytest.mark.asyncio
    async def test_interactive_setup_returns_project_info(self):
        """Test that interactive_setup returns a _ProjectInfo dataclass."""
        from guardkit.cli.init import interactive_setup, _ProjectInfo

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            # Mock user inputs
            mock_prompt.side_effect = [
                "A test project",  # purpose
                "python",  # primary_language
                "fastapi,pytest",  # frameworks
                "",  # first goal (empty to finish)
            ]

            result = await interactive_setup("test-project")

            # Should return the local _ProjectInfo dataclass (FEAT-MEM-09)
            assert isinstance(result, _ProjectInfo)
            assert result.project_name == "test-project"
            assert result.purpose == "A test project"
            assert result.primary_language == "python"

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_purpose(self):
        """Test that interactive_setup prompts for project purpose."""
        from guardkit.cli.init import interactive_setup

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose text",
                "python",
                "",  # frameworks
                "",  # goals
            ]

            await interactive_setup("test-project")

            # Verify Prompt.ask was called with purpose question
            calls = [str(call) for call in mock_prompt.call_args_list]
            assert any("purpose" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_primary_language(self):
        """Test that interactive_setup prompts for primary language with choices."""
        from guardkit.cli.init import interactive_setup

        with patch('guardkit.cli.init.Prompt.ask') as mock_prompt:
            mock_prompt.side_effect = [
                "Purpose",
                "typescript",  # primary_language
                "",  # frameworks
                "",  # goals
            ]

            await interactive_setup("test-project")

            # Verify language choices offered
            calls = mock_prompt.call_args_list
            # Should have called with choices parameter
            assert any('choices' in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_interactive_setup_prompts_for_frameworks(self):
        """Test that interactive_setup prompts for frameworks."""
        from guardkit.cli.init import interactive_setup

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
        from guardkit.cli.init import interactive_setup

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
        from guardkit.cli.init import interactive_setup

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
        from guardkit.cli.init import interactive_setup

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
        from guardkit.cli.init import interactive_setup

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

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Test purpose",
                primary_language="python",
                frameworks=[],
                key_goals=[],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            # Should have called interactive_setup
            assert mock_interactive.called

    def test_init_non_interactive_is_default(self, tmp_path, monkeypatch):
        """Test that non-interactive mode is the default."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive:

            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            # Should NOT call interactive_setup (default is non-interactive)
            assert not mock_interactive.called


class TestInteractiveCLAUDEmdGeneration:
    """Test CLAUDE.md generation from interactive answers."""

    def test_interactive_generates_claudemd_if_requested(self, tmp_path, monkeypatch):
        """Test that interactive mode can generate CLAUDE.md."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask') as mock_confirm:

            # User confirms CLAUDE.md generation
            mock_confirm.return_value = True

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Test purpose",
                primary_language="python",
                frameworks=[],
                key_goals=[],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            # Should have asked about CLAUDE.md generation
            assert mock_confirm.called

    def test_interactive_claudemd_includes_purpose(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes project purpose."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Build an awesome CLI tool",
                primary_language="python",
                frameworks=[],
                key_goals=[],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            # CLAUDE.md should be created with the purpose
            claude_md = tmp_path / "CLAUDE.md"
            assert claude_md.exists()
            assert "awesome CLI tool" in claude_md.read_text()

    def test_interactive_claudemd_includes_tech_stack(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes tech stack."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Test",
                primary_language="typescript",
                frameworks=["react", "tailwind"],
                key_goals=[],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            claude_md = tmp_path / "CLAUDE.md"
            assert claude_md.exists()
            content = claude_md.read_text()
            assert "typescript" in content.lower()
            assert "react" in content.lower()

    def test_interactive_claudemd_includes_goals(self, tmp_path, monkeypatch):
        """Test that generated CLAUDE.md includes key goals."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask', return_value=True):

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Test",
                primary_language="python",
                frameworks=[],
                key_goals=["Achieve 100% test coverage", "Deploy to production"],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            claude_md = tmp_path / "CLAUDE.md"
            assert claude_md.exists()
            assert "100% test coverage" in claude_md.read_text()

    def test_interactive_skips_claudemd_if_declined(self, tmp_path, monkeypatch):
        """Test that CLAUDE.md is not created if user declines."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        from guardkit.cli.init import _ProjectInfo

        with patch('guardkit.cli.init.interactive_setup', new_callable=AsyncMock) as mock_interactive, \
             patch('guardkit.cli.init.Confirm.ask', return_value=False):

            mock_interactive.return_value = _ProjectInfo(
                project_name="test-project",
                purpose="Test",
                primary_language="python",
                frameworks=[],
                key_goals=[],
            )

            result = runner.invoke(cli, ["init", "--interactive"])

            assert result.exit_code == 0
            # CLAUDE.md should NOT be created
            claude_md = tmp_path / "CLAUDE.md"
            assert not claude_md.exists()


# ============================================================================
# 5. Template Content Copying Tests (TASK-INST-010)
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

    def test_copies_ext_md_files(self, tmp_path):
        """AC: -ext.md files are copied alongside core agent files (TASK-ISF-003)."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        _create_fake_template(
            templates_dir, "fastapi-python",
            agents_in_dotclaude=False,
            agent_files=[
                "fastapi-specialist.md",
                "fastapi-specialist-ext.md",
                "fastapi-testing-specialist.md",
                "fastapi-testing-specialist-ext.md",
            ],
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
        # Both core and ext files should be present
        assert (agents_target / "fastapi-specialist.md").exists()
        assert (agents_target / "fastapi-specialist-ext.md").exists()
        assert (agents_target / "fastapi-testing-specialist.md").exists()
        assert (agents_target / "fastapi-testing-specialist-ext.md").exists()


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

    def test_no_user_template_fallback(self, tmp_path):
        """DF-011: the ~/.guardkit/templates user-override fallback was removed.

        A template that exists only outside the packaged templates base dir must
        NOT resolve — there is exactly one resolution path now.
        """
        from guardkit.cli.init import _resolve_template_source_dir

        pkg_templates = tmp_path / "pkg_templates"
        pkg_templates.mkdir()

        # A stray template elsewhere on disk must be invisible.
        stray = tmp_path / "user_templates" / "custom-template"
        stray.mkdir(parents=True)

        with patch(
            "guardkit.cli.init._get_templates_base_dir",
            return_value=pkg_templates,
        ):
            result = _resolve_template_source_dir("custom-template")

        assert result is None


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


# ============================================================================
# 6. Base-Only Tests
# ============================================================================


class TestBaseOnlyFlag:
    """Test the --base-only flag and apply_template(base_only=...) behavior."""

    def _create_extends_chain(self, templates_dir: Path):
        """Create a base template and an extension template that extends it."""
        base = templates_dir / "base-template"
        base.mkdir(parents=True)
        (base / "manifest.json").write_text('{"name": "base-template"}')
        (base / "agents").mkdir()
        (base / "agents" / "base-specialist.md").write_text("# base agent")

        ext = templates_dir / "ext-template"
        ext.mkdir(parents=True)
        (ext / "manifest.json").write_text(
            '{"name": "ext-template", "extends": "base-template"}'
        )
        (ext / "agents").mkdir()
        (ext / "agents" / "ext-specialist.md").write_text("# ext agent")
        return base, ext

    def test_base_only_flag_in_help(self):
        """--base-only option appears in init --help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--base-only" in result.output

    def test_base_only_installs_only_base(self, tmp_path):
        """apply_template(base_only=True) installs only the base of an extends chain."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        base, ext = self._create_extends_chain(templates_dir)

        target = tmp_path / "project"
        target.mkdir()

        def _resolve(name):
            return templates_dir / name if (templates_dir / name).is_dir() else None

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            side_effect=_resolve,
        ):
            result = apply_template("ext-template", target, base_only=True)

        assert result is True
        agents_target = target / ".claude" / "agents"
        # Only the base agent should be installed
        assert (agents_target / "base-specialist.md").exists()
        assert not (agents_target / "ext-specialist.md").exists()

    def test_without_base_only_installs_full_chain(self, tmp_path):
        """apply_template without base_only installs base + extension."""
        from guardkit.cli.init import apply_template

        templates_dir = tmp_path / "templates"
        base, ext = self._create_extends_chain(templates_dir)

        target = tmp_path / "project"
        target.mkdir()

        def _resolve(name):
            return templates_dir / name if (templates_dir / name).is_dir() else None

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            side_effect=_resolve,
        ):
            result = apply_template("ext-template", target)

        assert result is True
        agents_target = target / ".claude" / "agents"
        # Both agents should be installed
        assert (agents_target / "base-specialist.md").exists()
        assert (agents_target / "ext-specialist.md").exists()


class TestResolveExtendsChain:
    """Test _resolve_extends_chain."""

    def test_single_template_no_extends(self, tmp_path):
        """A template with no extends field returns [template_name]."""
        from guardkit.cli.init import _resolve_extends_chain

        templates_dir = tmp_path / "templates"
        tpl = templates_dir / "solo"
        tpl.mkdir(parents=True)
        (tpl / "manifest.json").write_text('{"name": "solo"}')

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=tpl,
        ):
            chain = _resolve_extends_chain("solo")

        assert chain == ["solo"]

    def test_extends_chain_ordered_base_first(self, tmp_path):
        """A template that extends another returns [base, extension]."""
        from guardkit.cli.init import _resolve_extends_chain

        templates_dir = tmp_path / "templates"
        base = templates_dir / "base-template"
        base.mkdir(parents=True)
        (base / "manifest.json").write_text('{"name": "base-template"}')
        ext = templates_dir / "ext-template"
        ext.mkdir(parents=True)
        (ext / "manifest.json").write_text(
            '{"name": "ext-template", "extends": "base-template"}'
        )

        def _resolve(name):
            return templates_dir / name if (templates_dir / name).is_dir() else None

        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            side_effect=_resolve,
        ):
            chain = _resolve_extends_chain("ext-template")

        assert chain == ["base-template", "ext-template"]


# ============================================================================
# 7. conftest bridge Tests
# ============================================================================


class TestInitConftestBridge:
    """Test that init installs the features/conftest.py BDD bridge when applicable."""

    def test_init_installs_conftest_bridge_when_reported(self, tmp_path, monkeypatch):
        """When install_features_conftest_bridge returns True, init reports it."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch(
            "guardkit.cli.init.install_features_conftest_bridge",
            return_value=True,
        ) as mock_bridge:
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            mock_bridge.assert_called_once()
            assert "features/conftest.py BDD bridge" in result.output

    def test_init_silent_when_bridge_not_installed(self, tmp_path, monkeypatch):
        """When the bridge is a no-op (returns False), no bridge line is printed."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch(
            "guardkit.cli.init.install_features_conftest_bridge",
            return_value=False,
        ) as mock_bridge:
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            mock_bridge.assert_called_once()
            assert "features/conftest.py BDD bridge" not in result.output


# ============================================================================
# 8. Logger Suppression Tests (TASK-IGR-001)
# ============================================================================


class TestLoggerSuppression:
    """Test that noisy third-party loggers are suppressed during init."""

    def test_httpx_logger_suppressed_in_non_verbose_mode(self, tmp_path, monkeypatch):
        """httpx INFO logs should be suppressed when verbose is False."""
        import logging

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        with patch("guardkit.cli.init.apply_template", return_value=True):
            runner.invoke(cli, ["init"])

        assert logging.getLogger("httpx").level >= logging.WARNING

    def test_httpcore_logger_suppressed_in_non_verbose_mode(self, tmp_path, monkeypatch):
        """httpcore INFO logs should be suppressed when verbose is False."""
        import logging

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        with patch("guardkit.cli.init.apply_template", return_value=True):
            runner.invoke(cli, ["init"])

        assert logging.getLogger("httpcore").level >= logging.WARNING

    def test_verbose_flag_preserves_log_levels(self, tmp_path, monkeypatch):
        """With --verbose, third-party loggers should NOT be suppressed."""
        import logging

        # Reset loggers to default (NOTSET = 0) before test
        logging.getLogger("httpx").setLevel(logging.NOTSET)
        logging.getLogger("httpcore").setLevel(logging.NOTSET)

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        with patch("guardkit.cli.init.apply_template", return_value=True):
            runner.invoke(cli, ["init", "--verbose"])

        # Loggers should remain at their default level (NOTSET = 0, allows all)
        assert logging.getLogger("httpx").level < logging.WARNING
        assert logging.getLogger("httpcore").level < logging.WARNING

    def test_warning_and_error_logs_still_visible(self, tmp_path, monkeypatch):
        """WARNING and ERROR level logs should pass through even when suppressed."""
        import logging

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        with patch("guardkit.cli.init.apply_template", return_value=True):
            runner.invoke(cli, ["init"])

        # Level is WARNING, so WARNING and above pass through
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.isEnabledFor(logging.WARNING)
        assert httpx_logger.isEnabledFor(logging.ERROR)
        assert not httpx_logger.isEnabledFor(logging.INFO)

    def test_verbose_flag_in_help(self):
        """The --verbose / -v flag should appear in help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert "--verbose" in result.output or "-v" in result.output


# ============================================================================
# 9. Pattern-Layer Summary Tests (TASK-INIT-D4E7)
# ============================================================================


class TestPatternLayerCount:
    """Unit tests for _count_pattern_layer_files helper."""

    def test_counts_template_suffix_files(self, tmp_path, monkeypatch):
        """Template with .template files in templates/ returns correct count."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-a"
        (tpl_dir / "templates" / "sub").mkdir(parents=True)
        (tpl_dir / "templates" / "a.template").write_text("x")
        (tpl_dir / "templates" / "sub" / "b.template").write_text("y")

        monkeypatch.setattr(
            init_mod,
            "_resolve_template_source_dir",
            lambda name: tpl_dir if name == "tpl-a" else None,
        )

        assert init_mod._count_pattern_layer_files(["tpl-a"]) == 2

    def test_counts_j2_suffix_files(self, tmp_path, monkeypatch):
        """Template with .j2 files in templates/ returns correct count."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-b"
        (tpl_dir / "templates").mkdir(parents=True)
        (tpl_dir / "templates" / "goal.md.j2").write_text("x")
        (tpl_dir / "templates" / "pipeline.py.j2").write_text("y")
        (tpl_dir / "templates" / "notes.md").write_text("z")  # should NOT count

        monkeypatch.setattr(
            init_mod,
            "_resolve_template_source_dir",
            lambda name: tpl_dir if name == "tpl-b" else None,
        )

        assert init_mod._count_pattern_layer_files(["tpl-b"]) == 2

    def test_empty_templates_dir_returns_zero(self, tmp_path, monkeypatch):
        """Template with empty templates/ subdirectory returns zero."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-c"
        (tpl_dir / "templates").mkdir(parents=True)

        monkeypatch.setattr(
            init_mod,
            "_resolve_template_source_dir",
            lambda name: tpl_dir if name == "tpl-c" else None,
        )

        assert init_mod._count_pattern_layer_files(["tpl-c"]) == 0

    def test_no_templates_dir_returns_zero(self, tmp_path, monkeypatch):
        """Template without templates/ subdirectory returns zero."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-d"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "agents").mkdir()  # has other stuff, but no templates/

        monkeypatch.setattr(
            init_mod,
            "_resolve_template_source_dir",
            lambda name: tpl_dir if name == "tpl-d" else None,
        )

        assert init_mod._count_pattern_layer_files(["tpl-d"]) == 0

    def test_unreadable_templates_dir_does_not_crash(self, tmp_path, monkeypatch):
        """OSError during traversal is swallowed and logged."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-e"
        (tpl_dir / "templates").mkdir(parents=True)
        (tpl_dir / "templates" / "a.template").write_text("x")

        monkeypatch.setattr(
            init_mod,
            "_resolve_template_source_dir",
            lambda name: tpl_dir if name == "tpl-e" else None,
        )

        class _RaisingPath:
            """Proxy Path that raises OSError on rglob."""

            def __init__(self, inner):
                self._inner = inner

            def __truediv__(self, other):
                return _RaisingPath(self._inner / other)

            def is_dir(self):
                return self._inner.is_dir()

            def rglob(self, pattern):
                raise OSError("simulated permission denied")

        def _resolve(name):
            if name != "tpl-e":
                return None

            class _Wrapper:
                def __truediv__(self, other):
                    return _RaisingPath(tpl_dir / other)

            return _Wrapper()

        monkeypatch.setattr(init_mod, "_resolve_template_source_dir", _resolve)

        assert init_mod._count_pattern_layer_files(["tpl-e"]) == 0

    def test_dedupes_across_chain(self, tmp_path, monkeypatch):
        """Two template names resolving to the same dir are counted once."""
        from guardkit.cli import init as init_mod

        tpl_dir = tmp_path / "tpl-shared"
        (tpl_dir / "templates").mkdir(parents=True)
        (tpl_dir / "templates" / "a.template").write_text("x")
        (tpl_dir / "templates" / "b.j2").write_text("y")

        monkeypatch.setattr(
            init_mod, "_resolve_template_source_dir", lambda name: tpl_dir
        )

        # Both chain entries point at the same dir; should count files once.
        assert init_mod._count_pattern_layer_files(["alias-1", "alias-2"]) == 2


class TestInitPatternLayerSummary:
    """Test that `guardkit init` summary surfaces pattern-layer count."""

    def test_summary_emits_line_when_pattern_layer_present(
        self, tmp_path, monkeypatch
    ):
        """Summary emits pattern-layer line when templates/ has .template/.j2 files."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init._count_pattern_layer_files", return_value=7):
            result = runner.invoke(cli, ["init"])

            # Collapse whitespace to tolerate rich-console line wrapping.
            normalized = " ".join(result.output.split())

            assert result.exit_code == 0
            assert "Pattern layer:" in normalized
            assert "7 scaffold file(s)" in normalized
            assert "not rendered at init time" in normalized
            assert "docs/guides/template-two-layer-model.md" in normalized

    def test_summary_omits_line_when_no_pattern_layer(self, tmp_path, monkeypatch):
        """Summary does NOT emit pattern-layer line when count is zero."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch("guardkit.cli.init._count_pattern_layer_files", return_value=0):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Pattern layer:" not in result.output

    def test_summary_does_not_crash_when_count_raises(self, tmp_path, monkeypatch):
        """Init remains exit-0 if pattern-layer counting raises unexpectedly."""
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        with patch(
            "guardkit.cli.init._count_pattern_layer_files",
            side_effect=RuntimeError("boom"),
        ):
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0
            assert "Pattern layer:" not in result.output
