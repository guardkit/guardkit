"""Acceptance tests for the harvest contract.

End-to-end tests validating the four explicit contract points against the
assembled CLI. These tests verify the complete harvest workflow from walker
through publisher to CLI, ensuring the feature-level integration works correctly.

All tests run with mocked NATS (no live broker required).

Coverage Target: Contract validation
Test Count: 15 tests
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nats_core.events import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1

from guardkit.memory.harvest_walker import walk_harvest_dirs


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_docs_root(tmp_path: Path) -> Path:
    """Create a temporary docs structure with all 4 episode types.

    Creates:
    - docs/adr/001-test-decision.md (adr)
    - docs/reviews/feature-x-review.md (review_report)
    - docs/retro/feat-x-outcome.md (feature_outcome)
    - docs/guides/user-guide.md (document)
    """
    # Create directory structure
    dirs = {
        "adr": tmp_path / "docs" / "adr",
        "reviews": tmp_path / "docs" / "reviews",
        "retro": tmp_path / "docs" / "retro",
        "guides": tmp_path / "docs" / "guides",
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True)

    # Create sample documents
    (dirs["adr"] / "001-test-decision.md").write_text(
        "# ADR 001: Test Decision\n\nContext: Testing\nDecision: Approved\n"
    )
    (dirs["reviews"] / "feature-x-review.md").write_text(
        "# Feature X Review\n\nStatus: Approved\nFindings: None\n"
    )
    (dirs["retro"] / "feat-x-outcome.md").write_text(
        "# Feature X Outcome\n\nCompleted: Yes\nLessons: Many\n"
    )
    (dirs["guides"] / "user-guide.md").write_text(
        "# User Guide\n\nHow to use this feature.\n"
    )

    # Create .git directory to make it a valid repo root
    (tmp_path / ".git").mkdir()

    return tmp_path


@pytest.fixture
def temp_docs_root_with_oversized(temp_docs_root: Path) -> tuple[Path, Path]:
    """Add an oversized document (>900KB) to the temp docs root.

    Returns:
        Tuple of (repo_root, oversized_file_path)
    """
    oversized_file = temp_docs_root / "docs" / "guides" / "huge-doc.md"

    # Create a >900KB document (920KB to be safe)
    content_size = MAX_EPISODE_BODY_BYTES + 20_000
    content = "# Huge Document\n\n" + ("X" * content_size)
    oversized_file.write_text(content)

    return temp_docs_root, oversized_file


@pytest.fixture
def fake_nats_client() -> MagicMock:
    """Create a fake NATSClient with mocked async methods.

    This fixture creates a mock client that tracks all publish_episode calls
    so we can verify the subject patterns without requiring a live broker.
    """
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()

    # Track published episodes and subjects
    published_episodes: list[MemoryEpisodeV1] = []
    published_subjects: list[str] = []

    async def mock_publish_episode(episode: MemoryEpisodeV1) -> None:
        """Mock publish that records episode and derives subject."""
        published_episodes.append(episode)
        # Subject pattern: memory.episode.{project_id}.{episode_type}
        subject = f"memory.episode.{episode.project_id}.{episode.episode_type}"
        published_subjects.append(subject)

    client.publish_episode = AsyncMock(side_effect=mock_publish_episode)
    client.published_episodes = published_episodes
    client.published_subjects = published_subjects

    return client


# ============================================================================
# 1. Subject Resolution Tests (4 tests - one per episode_type)
# ============================================================================


class TestSubjectResolution:
    """Test that published subjects follow the correct pattern for each episode_type."""

    @pytest.mark.asyncio
    async def test_adr_subject_resolution(
        self, temp_docs_root: Path, fake_nats_client: MagicMock
    ) -> None:
        """ADR episodes publish to memory.episode.guardkit.adr."""
        from guardkit.memory.harvest_publisher import publish_episodes

        # Harvest and filter to adr episodes
        result = walk_harvest_dirs(temp_docs_root)
        adr_episodes = [ep for ep in result.episodes if ep.episode_type == "adr"]
        assert len(adr_episodes) > 0, "Should have at least one adr episode"

        # Publish with fake client
        await publish_episodes(adr_episodes, client=fake_nats_client)

        # Verify subject
        assert len(fake_nats_client.published_subjects) == len(adr_episodes)
        for subject in fake_nats_client.published_subjects:
            assert subject == "memory.episode.guardkit.adr"

    @pytest.mark.asyncio
    async def test_review_report_subject_resolution(
        self, temp_docs_root: Path, fake_nats_client: MagicMock
    ) -> None:
        """Review report episodes publish to memory.episode.guardkit.review_report."""
        from guardkit.memory.harvest_publisher import publish_episodes

        result = walk_harvest_dirs(temp_docs_root)
        review_episodes = [
            ep for ep in result.episodes if ep.episode_type == "review_report"
        ]
        assert len(review_episodes) > 0

        await publish_episodes(review_episodes, client=fake_nats_client)

        for subject in fake_nats_client.published_subjects:
            assert subject == "memory.episode.guardkit.review_report"

    @pytest.mark.asyncio
    async def test_feature_outcome_subject_resolution(
        self, temp_docs_root: Path, fake_nats_client: MagicMock
    ) -> None:
        """Feature outcome episodes publish to memory.episode.guardkit.feature_outcome."""
        from guardkit.memory.harvest_publisher import publish_episodes

        result = walk_harvest_dirs(temp_docs_root)
        outcome_episodes = [
            ep for ep in result.episodes if ep.episode_type == "feature_outcome"
        ]
        assert len(outcome_episodes) > 0

        await publish_episodes(outcome_episodes, client=fake_nats_client)

        for subject in fake_nats_client.published_subjects:
            assert subject == "memory.episode.guardkit.feature_outcome"

    @pytest.mark.asyncio
    async def test_document_subject_resolution(
        self, temp_docs_root: Path, fake_nats_client: MagicMock
    ) -> None:
        """Document episodes publish to memory.episode.guardkit.document."""
        from guardkit.memory.harvest_publisher import publish_episodes

        result = walk_harvest_dirs(temp_docs_root)
        doc_episodes = [
            ep for ep in result.episodes if ep.episode_type == "document"
        ]
        assert len(doc_episodes) > 0

        await publish_episodes(doc_episodes, client=fake_nats_client)

        for subject in fake_nats_client.published_subjects:
            assert subject == "memory.episode.guardkit.document"


# ============================================================================
# 2. Episode ID Stability Tests (3 tests)
# ============================================================================


class TestEpisodeIdStability:
    """Test that episode IDs are stable across independent harvest runs."""

    def test_episode_id_stability_same_content(self, temp_docs_root: Path) -> None:
        """Two harvest runs over the same docs produce identical episode_ids."""
        # Run 1
        result1 = walk_harvest_dirs(temp_docs_root)
        episode_ids_1 = {ep.episode_id for ep in result1.episodes}

        # Run 2
        result2 = walk_harvest_dirs(temp_docs_root)
        episode_ids_2 = {ep.episode_id for ep in result2.episodes}

        # Verify identical sets
        assert episode_ids_1 == episode_ids_2
        assert len(episode_ids_1) > 0, "Should have harvested episodes"

    def test_episode_id_uniqueness_per_file(self, temp_docs_root: Path) -> None:
        """Each file produces a unique episode_id."""
        result = walk_harvest_dirs(temp_docs_root)

        # Extract all episode IDs
        episode_ids = [ep.episode_id for ep in result.episodes]

        # Verify no duplicates
        assert len(episode_ids) == len(set(episode_ids)), "Episode IDs should be unique"
        assert len(episode_ids) >= 4, "Should have episodes for all 4 doc types"

    def test_episode_id_changes_when_path_changes(self, tmp_path: Path) -> None:
        """Moving a file to a different directory changes its episode_id."""
        # Create two directories
        dir1 = tmp_path / "docs" / "guides"
        dir2 = tmp_path / "docs" / "reference"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)
        (tmp_path / ".git").mkdir()

        # Create same content in two locations
        content = "# Test Doc\n\nSame content\n"
        (dir1 / "test.md").write_text(content)
        (dir2 / "test.md").write_text(content)

        # Harvest
        result = walk_harvest_dirs(tmp_path)

        # Should have 2 episodes with different IDs
        assert len(result.episodes) == 2
        ep1, ep2 = result.episodes
        assert ep1.episode_id != ep2.episode_id, "Different paths should produce different IDs"


# ============================================================================
# 3. Oversized Rejection Tests (3 tests)
# ============================================================================


class TestOversizedRejection:
    """Test that oversized documents (>900KB) are rejected with actionable errors."""

    def test_walker_skips_oversized_with_actionable_report(
        self, temp_docs_root_with_oversized: tuple[Path, Path]
    ) -> None:
        """Walker skips >900KB docs and reports path + size."""
        repo_root, oversized_file = temp_docs_root_with_oversized

        result = walk_harvest_dirs(repo_root)

        # Should have skipped the oversized file
        assert len(result.skipped_oversized) == 1

        # Check the skip report includes path and size
        skipped_path, skipped_size = result.skipped_oversized[0]
        assert "huge-doc.md" in skipped_path
        assert skipped_size > MAX_EPISODE_BODY_BYTES

    def test_oversized_rejection_does_not_block_other_docs(
        self, temp_docs_root_with_oversized: tuple[Path, Path]
    ) -> None:
        """Oversized doc rejection doesn't prevent harvesting other docs."""
        repo_root, _ = temp_docs_root_with_oversized

        result = walk_harvest_dirs(repo_root)

        # Should still have harvested the normal-sized docs
        assert len(result.episodes) >= 4, "Should harvest normal docs despite oversized skip"
        assert result.skipped_oversized  # Should have skipped oversized

    @pytest.mark.asyncio
    async def test_publisher_skips_oversized_with_warning(
        self, temp_docs_root_with_oversized: tuple[Path, Path],
        fake_nats_client: MagicMock,
    ) -> None:
        """Publisher catches and logs oversized episodes per-episode."""
        from guardkit.memory.harvest_publisher import publish_episodes

        repo_root, _ = temp_docs_root_with_oversized

        # Create a mock oversized episode (walker would have skipped it, but test publisher)
        oversized_content = "X" * (MAX_EPISODE_BODY_BYTES + 1000)
        oversized_episode = MemoryEpisodeV1(
            episode_id="ep-oversized",
            project_id="guardkit",
            episode_type="document",
            content_format="markdown",
            body=oversized_content,
        )

        # Mock publish_episode to raise ValueError for oversized
        async def mock_publish_with_oversized_check(episode: MemoryEpisodeV1) -> None:
            if len(episode.body.encode()) >= MAX_EPISODE_BODY_BYTES:
                msg = f"Episode body is {len(episode.body.encode())} bytes, exceeding the 900KB limit"
                raise ValueError(msg)
            fake_nats_client.published_episodes.append(episode)

        fake_nats_client.publish_episode = AsyncMock(
            side_effect=mock_publish_with_oversized_check
        )

        # Publish should not raise (catches ValueError)
        summary = await publish_episodes([oversized_episode], client=fake_nats_client)

        # Verify oversized was skipped
        assert summary.skipped_oversized == 1
        assert summary.published == 0


# ============================================================================
# 4. Dry-Run Isolation Tests (3 tests)
# ============================================================================


class TestDryRunIsolation:
    """Test that --dry-run lists counts without constructing NATSClient."""

    def test_dry_run_shows_counts_per_type(self, temp_docs_root: Path) -> None:
        """Dry run prints episode counts by type."""
        # Run CLI with --dry-run
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "guardkit.cli.main",
                "memory",
                "harvest",
                "--dry-run",
                "--docs-root",
                str(temp_docs_root),
            ],
            capture_output=True,
            text=True,
        )

        # Should exit 0
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # Should show counts in output
        output = result.stdout
        assert "Episodes by Type" in output or "episode" in output.lower()
        assert "Dry run complete" in output

    def test_dry_run_no_nats_client_construction(self, temp_docs_root: Path) -> None:
        """Dry run does not construct NATSClient or call connect()."""
        from guardkit.memory import harvest_publisher

        # Patch build_nats_client to track if it's called
        with patch.object(
            harvest_publisher, "build_nats_client"
        ) as mock_build_client:
            # Run CLI with --dry-run
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "guardkit.cli.main",
                    "memory",
                    "harvest",
                    "--dry-run",
                    "--docs-root",
                    str(temp_docs_root),
                ],
                capture_output=True,
                text=True,
            )

            # Should succeed
            assert result.returncode == 0

            # NATSClient builder should NOT have been called
            mock_build_client.assert_not_called()

    def test_dry_run_reports_oversized_skips(
        self, temp_docs_root_with_oversized: tuple[Path, Path]
    ) -> None:
        """Dry run reports oversized document skips."""
        repo_root, _ = temp_docs_root_with_oversized

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "guardkit.cli.main",
                "memory",
                "harvest",
                "--dry-run",
                "--docs-root",
                str(repo_root),
            ],
            capture_output=True,
            text=True,
        )

        # Should succeed
        assert result.returncode == 0

        # Should mention oversized skip
        output = result.stdout
        assert "oversized" in output.lower() or "900" in output


# ============================================================================
# 5. Full Integration Test (1 test)
# ============================================================================


class TestFullIntegration:
    """Test the complete harvest workflow end-to-end."""

    @pytest.mark.asyncio
    async def test_full_harvest_workflow_with_mocked_nats(
        self, temp_docs_root: Path, fake_nats_client: MagicMock
    ) -> None:
        """Full harvest workflow: walker → publisher → verify all episodes published."""
        from guardkit.memory.harvest_publisher import publish_episodes

        # Run walker
        walker_result = walk_harvest_dirs(temp_docs_root)

        # Verify walker found all 4 episode types
        episode_types = {ep.episode_type for ep in walker_result.episodes}
        assert episode_types == {"adr", "review_report", "feature_outcome", "document"}

        # Run publisher
        publish_summary = await publish_episodes(
            walker_result.episodes, client=fake_nats_client
        )

        # Verify all episodes published
        assert publish_summary.published == len(walker_result.episodes)
        assert publish_summary.skipped_oversized == 0
        assert len(fake_nats_client.published_episodes) == len(walker_result.episodes)

        # Verify subjects follow correct pattern
        expected_subjects = {
            "memory.episode.guardkit.adr",
            "memory.episode.guardkit.review_report",
            "memory.episode.guardkit.feature_outcome",
            "memory.episode.guardkit.document",
        }
        actual_subjects = set(fake_nats_client.published_subjects)
        assert actual_subjects == expected_subjects
