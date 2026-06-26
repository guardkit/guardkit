"""
Tests for guardkit memory CLI commands.

Test Coverage:
- memory harvest command with --dry-run flag
- memory harvest with walker and publisher integration
- Error handling for missing NATS credentials
- Rich output formatting
- Exit code behavior

Coverage Target: >=85%
Test Count: 10+ tests
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.memory.harvest_walker import HarvestResult
from guardkit.memory.harvest_publisher import PublishSummary


class TestMemoryHarvestCommand:
    """Test guardkit memory harvest command."""

    def test_memory_group_exists(self):
        """Test that memory command group is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["memory", "--help"])
        assert result.exit_code == 0
        assert "memory" in result.output.lower()

    def test_harvest_command_exists(self):
        """Test that harvest command is registered under memory group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["memory", "harvest", "--help"])
        assert result.exit_code == 0
        assert "harvest" in result.output.lower() or "Harvest" in result.output

    def test_dry_run_executes_walker_only(self, tmp_path):
        """Test that --dry-run runs walker without connecting to NATS."""
        runner = CliRunner()

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Mock walker result
        mock_result = HarvestResult(
            episodes=[],
            skipped_oversized=[],
            skipped_empty=0,
            counts_per_type={"doc-feature": 5, "doc-guide": 3},
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_result
        ) as mock_walker, patch(
            "guardkit.cli.memory.publish_episodes", new_callable=AsyncMock
        ) as mock_publisher:

            result = runner.invoke(
                cli, ["memory", "harvest", "--dry-run", "--docs-root", str(tmp_path)]
            )

            # Walker should be called
            mock_walker.assert_called_once()

            # Publisher should NOT be called in dry-run mode
            mock_publisher.assert_not_called()

            # Should exit 0
            assert result.exit_code == 0
            assert "Dry run complete" in result.output

    def test_dry_run_no_nats_password_required(self, tmp_path, monkeypatch):
        """Test that --dry-run does not require GUARDKIT_NATS_PASSWORD."""
        runner = CliRunner()

        # Clear NATS password env var
        monkeypatch.delenv("GUARDKIT_NATS_PASSWORD", raising=False)

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock walker result
        mock_result = HarvestResult(
            episodes=[],
            skipped_oversized=[],
            skipped_empty=0,
            counts_per_type={},
        )

        with patch("guardkit.cli.memory.walk_harvest_dirs", return_value=mock_result):
            result = runner.invoke(
                cli, ["memory", "harvest", "--dry-run", "--docs-root", str(tmp_path)]
            )

            # Should succeed without NATS password
            assert result.exit_code == 0
            assert "Dry run complete" in result.output

    def test_harvest_runs_walker_then_publisher(self, tmp_path, monkeypatch):
        """Test that harvest (without --dry-run) runs walker then publisher."""
        runner = CliRunner()

        # Set NATS password
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password")

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock results
        mock_harvest = HarvestResult(
            episodes=[MagicMock()],  # 1 episode
            skipped_oversized=[],
            skipped_empty=0,
            counts_per_type={"doc-feature": 1},
        )

        mock_publish = PublishSummary(
            published=1, skipped_oversized=0, counts_per_type={"doc-feature": 1}
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_harvest
        ) as mock_walker, patch(
            "guardkit.cli.memory.publish_episodes", new_callable=AsyncMock
        ) as mock_publisher:

            mock_publisher.return_value = mock_publish

            result = runner.invoke(
                cli, ["memory", "harvest", "--docs-root", str(tmp_path)]
            )

            # Both walker and publisher should be called
            mock_walker.assert_called_once()
            mock_publisher.assert_called_once()

            # Should exit 0
            assert result.exit_code == 0
            assert "Harvest complete" in result.output

    def test_harvest_fails_without_nats_password(self, tmp_path, monkeypatch):
        """Test that harvest fails with actionable error when NATS password missing."""
        runner = CliRunner()

        # Clear NATS password
        monkeypatch.delenv("GUARDKIT_NATS_PASSWORD", raising=False)

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock walker result
        mock_result = HarvestResult(
            episodes=[MagicMock()],
            skipped_oversized=[],
            skipped_empty=0,
            counts_per_type={},
        )

        with patch("guardkit.cli.memory.walk_harvest_dirs", return_value=mock_result):
            result = runner.invoke(
                cli, ["memory", "harvest", "--docs-root", str(tmp_path)]
            )

            # Should exit non-zero
            assert result.exit_code == 1

            # Should contain helpful error message
            assert "GUARDKIT_NATS_PASSWORD" in result.output

    def test_harvest_reports_oversized_skips(self, tmp_path, monkeypatch):
        """Test that oversized docs are reported in output."""
        runner = CliRunner()

        # Set NATS password
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password")

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock walker with oversized skips
        mock_harvest = HarvestResult(
            episodes=[],
            skipped_oversized=[
                ("docs/large-doc.md", 1024 * 1024),  # 1MB
                ("docs/huge-doc.md", 2 * 1024 * 1024),  # 2MB
            ],
            skipped_empty=0,
            counts_per_type={},
        )

        mock_publish = PublishSummary(
            published=0, skipped_oversized=0, counts_per_type={}
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_harvest
        ), patch(
            "guardkit.cli.memory.publish_episodes",
            new_callable=AsyncMock,
            return_value=mock_publish,
        ):

            result = runner.invoke(
                cli, ["memory", "harvest", "--docs-root", str(tmp_path)]
            )

            # Should report oversized skips
            assert "Skipped 2 oversized documents" in result.output
            assert "docs/large-doc.md" in result.output or "large-doc" in result.output

            # Should still exit 0 (oversized is not fatal)
            assert result.exit_code == 0

    def test_harvest_auto_detects_repo_root(self, tmp_path, monkeypatch):
        """Test that harvest auto-detects repo root when --docs-root not provided."""
        runner = CliRunner()

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Set NATS password
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password")

        # Mock results
        mock_harvest = HarvestResult(
            episodes=[], skipped_oversized=[], skipped_empty=0, counts_per_type={}
        )

        mock_publish = PublishSummary(
            published=0, skipped_oversized=0, counts_per_type={}
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_harvest
        ) as mock_walker, patch(
            "guardkit.cli.memory.publish_episodes",
            new_callable=AsyncMock,
            return_value=mock_publish,
        ):

            result = runner.invoke(cli, ["memory", "harvest"])

            # Walker should be called with auto-detected root
            mock_walker.assert_called_once()
            call_args = mock_walker.call_args[0]
            assert str(call_args[0]) == str(tmp_path)

            assert result.exit_code == 0

    def test_harvest_fails_gracefully_without_git_repo(self):
        """Test that harvest fails with clear error when not in git repo."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["memory", "harvest", "--dry-run"])

            # Should exit non-zero
            assert result.exit_code == 1

            # Should contain helpful error message
            assert "repository root" in result.output.lower() or "git" in result.output.lower()

    def test_harvest_prints_episode_counts_by_type(self, tmp_path, monkeypatch):
        """Test that harvest prints episode counts grouped by type."""
        runner = CliRunner()

        # Set NATS password
        monkeypatch.setenv("GUARDKIT_NATS_PASSWORD", "test-password")

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Mock results with multiple types
        counts = {
            "doc-feature": 10,
            "doc-guide": 5,
            "doc-adr": 3,
        }

        mock_harvest = HarvestResult(
            episodes=[MagicMock() for _ in range(18)],  # Total episodes
            skipped_oversized=[],
            skipped_empty=2,
            counts_per_type=counts,
        )

        mock_publish = PublishSummary(
            published=18, skipped_oversized=0, counts_per_type=counts
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_harvest
        ), patch(
            "guardkit.cli.memory.publish_episodes",
            new_callable=AsyncMock,
            return_value=mock_publish,
        ):

            result = runner.invoke(
                cli, ["memory", "harvest", "--docs-root", str(tmp_path)]
            )

            # Should display counts table
            assert "Episodes by Type" in result.output or "doc-feature" in result.output
            assert "10" in result.output  # doc-feature count
            assert "5" in result.output  # doc-guide count
            assert result.exit_code == 0

    def test_harvest_uses_env_file_for_credentials(self, tmp_path):
        """Test that --env-file loads NATS credentials correctly."""
        runner = CliRunner()

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create .env file with password
        env_file = tmp_path / ".env"
        env_file.write_text("GUARDKIT_NATS_PASSWORD=from-env-file\n")

        # Mock results
        mock_harvest = HarvestResult(
            episodes=[], skipped_oversized=[], skipped_empty=0, counts_per_type={}
        )

        mock_publish = PublishSummary(
            published=0, skipped_oversized=0, counts_per_type={}
        )

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs", return_value=mock_harvest
        ), patch(
            "guardkit.cli.memory.publish_episodes",
            new_callable=AsyncMock,
            return_value=mock_publish,
        ) as mock_publisher:

            result = runner.invoke(
                cli,
                [
                    "memory",
                    "harvest",
                    "--docs-root",
                    str(tmp_path),
                    "--env-file",
                    str(env_file),
                ],
            )

            # Should succeed (loaded password from env file)
            assert result.exit_code == 0

            # Verify publisher was called
            mock_publisher.assert_called_once()

    def test_harvest_walker_error_exits_non_zero(self, tmp_path):
        """Test that walker error exits with non-zero code."""
        runner = CliRunner()

        # Create fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with patch(
            "guardkit.cli.memory.walk_harvest_dirs",
            side_effect=RuntimeError("Walker explosion"),
        ):

            result = runner.invoke(
                cli, ["memory", "harvest", "--dry-run", "--docs-root", str(tmp_path)]
            )

            # Should exit non-zero
            assert result.exit_code == 1
            assert "Walker error" in result.output or "error" in result.output.lower()
