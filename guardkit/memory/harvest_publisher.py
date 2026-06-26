"""NATS harvest publisher integration.

Connect as the provisioned `guardkit` NATS user and publish MemoryEpisodeV1
episodes through nats_core.NATSClient.publish_episode, handling 900KB rejections
per-episode and maintaining idempotency through deterministic episode IDs.
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nats_core.client import NATSClient
from nats_core.config import NATSConfig
from pydantic import SecretStr

if TYPE_CHECKING:
    from nats_core.events import MemoryEpisodeV1

logger = logging.getLogger(__name__)


@dataclass
class PublishSummary:
    """Summary of episode publishing results.

    Attributes:
        published: Number of episodes successfully published.
        skipped_oversized: Number of episodes skipped due to >900KB size.
        counts_per_type: Count of published episodes by episode_type.
    """

    published: int
    skipped_oversized: int
    counts_per_type: dict[str, int]


def read_nats_password() -> str:
    """Read GUARDKIT_NATS_PASSWORD from environment.

    Returns:
        The NATS password string.

    Raises:
        ValueError: If GUARDKIT_NATS_PASSWORD is missing or blank, with an
            actionable error message naming the variable and where to set it.
    """
    password = os.environ.get("GUARDKIT_NATS_PASSWORD")

    if password is None:
        msg = (
            "GUARDKIT_NATS_PASSWORD environment variable is not set. "
            "Set it in your shell environment or in nats-infrastructure/.env"
        )
        raise ValueError(msg)

    if not password.strip():
        msg = (
            "GUARDKIT_NATS_PASSWORD environment variable is blank. "
            "Provide a valid password in nats-infrastructure/.env or your "
            "shell environment"
        )
        raise ValueError(msg)

    return password


def build_nats_client(password: str) -> NATSClient:
    """Build NATSClient with guardkit harvest configuration.

    Args:
        password: The NATS password for the guardkit user.

    Returns:
        Configured NATSClient instance ready for connection.
    """
    config = NATSConfig(
        url="nats://127.0.0.1:4222",
        user="guardkit",
        password=SecretStr(password),
        name="guardkit-harvest",
    )
    return NATSClient(config, source_id="guardkit-harvest")


async def publish_episodes(
    episodes: list[MemoryEpisodeV1],
    client: NATSClient | None = None,
) -> PublishSummary:
    """Publish memory episodes to NATS with 900KB guard and idempotent retry.

    Connects to NATS, publishes each episode, and disconnects. Oversized episodes
    (>900KB) are caught per-episode, logged with actionable guidance, and skipped
    without aborting the run. Idempotency is server-side via deterministic
    episode_id → Nats-Msg-Id JetStream deduplication.

    Args:
        episodes: List of MemoryEpisodeV1 episodes to publish.
        client: Optional pre-configured NATSClient (primarily for testing).
            If None, builds a client from GUARDKIT_NATS_PASSWORD environment.

    Returns:
        PublishSummary with counts of published, skipped, and per-type statistics.

    Raises:
        ValueError: If GUARDKIT_NATS_PASSWORD is missing/blank (when client=None).
        RuntimeError: If connection or other unexpected errors occur.
    """
    if client is None:
        password = read_nats_password()
        client = build_nats_client(password)

    published = 0
    skipped_oversized = 0
    type_counts: Counter[str] = Counter()

    try:
        await client.connect()

        for episode in episodes:
            try:
                await client.publish_episode(episode)
                published += 1
                type_counts[episode.episode_type] += 1
                logger.debug(
                    "Published episode %s (type=%s, size=%d bytes)",
                    episode.episode_id,
                    episode.episode_type,
                    len(episode.body.encode()),
                )
            except ValueError as e:
                # Catch oversized episode error per-episode
                if "exceeding the" in str(e) and "byte" in str(e):
                    skipped_oversized += 1
                    logger.warning(
                        "Skipped oversized episode %s (type=%s, size=%d bytes): %s. "
                        "Chunk the content upstream to stay under 900KB.",
                        episode.episode_id,
                        episode.episode_type,
                        len(episode.body.encode()),
                        str(e),
                    )
                else:
                    # Re-raise other ValueErrors
                    raise

    finally:
        # Always disconnect, even if errors occurred
        await client.disconnect()

    return PublishSummary(
        published=published,
        skipped_oversized=skipped_oversized,
        counts_per_type=dict(type_counts),
    )
