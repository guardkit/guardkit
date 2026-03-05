"""
Tests for 'guardkit graphiti seed-system' CLI command.

Coverage Target: >=85%
Test Count: 8 tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

try:
    from guardkit.cli.main import cli
    from guardkit.cli.graphiti import graphiti

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI graphiti command not available",
)


def _make_mock_client(enabled: bool = True, initialized: bool = True):
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.enabled = enabled
    client.initialize = AsyncMock(return_value=initialized)
    client.close = AsyncMock()
    return client


def _make_mock_settings(enabled: bool = True):
    """Create mock GraphitiSettings."""
    settings = MagicMock()
    settings.enabled = enabled
    settings.graph_store = "falkordb"
    settings.falkordb_host = "localhost"
    settings.falkordb_port = 6379
    return settings


class TestSeedSystemCommand:
    """Test guardkit graphiti seed-system command."""

    def test_command_exists_in_help(self):
        """Test that seed-system command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["graphiti", "seed-system", "--help"])
        assert result.exit_code == 0
        assert "seed-system" in result.output.lower() or "Seed template" in result.output

    def test_seed_system_invokes_seed_system_content(self):
        """Test that the command invokes the seeding function."""
        runner = CliRunner()

        from guardkit.knowledge.system_seeding import (
            SystemSeedResult,
            SystemSeedComponentResult,
        )

        mock_result = SystemSeedResult(
            success=True,
            template_name="default",
            total_episodes=5,
        )
        mock_result.add_result(
            SystemSeedComponentResult(
                component="template_content",
                success=True,
                episodes_created=3,
            )
        )

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.seed_system_content",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_seed, patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (
                _make_mock_client(),
                _make_mock_settings(),
            )

            result = runner.invoke(cli, ["graphiti", "seed-system"])

            mock_seed.assert_called_once()
            assert result.exit_code == 0

    def test_force_flag_passes_through(self):
        """Test that --force is forwarded to seeding."""
        runner = CliRunner()

        from guardkit.knowledge.system_seeding import SystemSeedResult

        mock_result = SystemSeedResult(success=True)

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.seed_system_content",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_seed, patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (
                _make_mock_client(),
                _make_mock_settings(),
            )

            runner.invoke(cli, ["graphiti", "seed-system", "--force"])

            call_kwargs = mock_seed.call_args.kwargs
            assert call_kwargs.get("force") is True

    def test_template_flag_passes_through(self):
        """Test that --template is forwarded to seeding."""
        runner = CliRunner()

        from guardkit.knowledge.system_seeding import SystemSeedResult

        mock_result = SystemSeedResult(success=True)

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.seed_system_content",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_seed, patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (
                _make_mock_client(),
                _make_mock_settings(),
            )

            runner.invoke(
                cli, ["graphiti", "seed-system", "--template", "fastapi-python"]
            )

            call_kwargs = mock_seed.call_args.kwargs
            assert call_kwargs.get("template_name") == "fastapi-python"

    def test_handles_disabled_graphiti(self):
        """Test that disabled Graphiti shows message and exits."""
        runner = CliRunner()

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (
                _make_mock_client(enabled=False),
                _make_mock_settings(enabled=False),
            )

            result = runner.invoke(cli, ["graphiti", "seed-system"])

            assert "disabled" in result.output.lower()

    def test_handles_connection_error(self):
        """Test that connection errors are handled gracefully."""
        runner = CliRunner()

        client = _make_mock_client()
        client.initialize = AsyncMock(side_effect=Exception("Connection refused"))

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (client, _make_mock_settings())

            result = runner.invoke(cli, ["graphiti", "seed-system"])

            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_skips_when_already_seeded(self):
        """Test that existing marker causes early exit."""
        runner = CliRunner()

        with patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=True
        ):
            result = runner.invoke(cli, ["graphiti", "seed-system"])

            assert "already seeded" in result.output.lower()

    def test_displays_results_summary(self):
        """Test that completion shows component summary."""
        runner = CliRunner()

        from guardkit.knowledge.system_seeding import (
            SystemSeedResult,
            SystemSeedComponentResult,
        )

        mock_result = SystemSeedResult(
            success=True,
            template_name="fastapi-python",
        )
        mock_result.add_result(
            SystemSeedComponentResult(
                component="template_content",
                success=True,
                episodes_created=3,
            )
        )
        mock_result.add_result(
            SystemSeedComponentResult(
                component="role_constraints",
                success=True,
                episodes_created=2,
            )
        )
        mock_result.add_result(
            SystemSeedComponentResult(
                component="implementation_modes",
                success=True,
                episodes_created=3,
            )
        )

        with patch(
            "guardkit.cli.graphiti._get_client_and_config"
        ) as mock_get, patch(
            "guardkit.knowledge.system_seeding.seed_system_content",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "guardkit.knowledge.system_seeding.is_system_seeded", return_value=False
        ):
            mock_get.return_value = (
                _make_mock_client(),
                _make_mock_settings(),
            )

            result = runner.invoke(cli, ["graphiti", "seed-system"])

            assert "complete" in result.output.lower()
            assert "template_content" in result.output
            assert "role_constraints" in result.output
            assert "implementation_modes" in result.output
