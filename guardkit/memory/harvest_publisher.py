"""NATS harvest publisher integration.

Connect as the provisioned `guardkit` NATS user and publish MemoryEpisodeV1
episodes through nats_core.NATSClient.publish_episode, handling 900KB rejections
per-episode and maintaining idempotency through deterministic episode IDs.
"""

from __future__ import annotations

import asyncio
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

PUBLISH_TEARDOWN_TIMEOUT_SECONDS = 5.0

#: How long the dial may take. Bounded for the same reason the hang-up is: the
#: caller is a build's last line, and nats-py retries a refused connection for
#: about two minutes before giving up. Measured on 2026-09-13: a build's outcome
#: write spent 120s failing against a caller ceiling of 20s, so every outcome
#: was reported as "the memory writer did not complete (TimeoutError)" — which
#: reads as slowness and was really a refused connection to the wrong host.
PUBLISH_CONNECT_TIMEOUT_SECONDS = 8.0

#: Where the broker is, when nobody says otherwise. This module ran with the
#: loopback address WRITTEN IN for the life of the repository, which was true
#: while everything ran on the host. Since the factory moved inside each
#: repository's sandbox (2026-09-07) loopback there has no broker, so every
#: build outcome was published into a closed port and the memory corpus stopped
#: growing without one line saying so.
DEFAULT_NATS_URL = "nats://127.0.0.1:4222"

def address_without_secrets(url: str) -> str:
    """``host:port`` from a broker URL, with any credentials removed.

    A NATS URL may carry ``user:password@`` and this module puts the address
    into log lines and error messages. Printing it whole would write a password
    into every build log — which is exactly what the first cut of this change
    did on 2026-09-13 before it ever shipped.
    """
    scheme, separator, rest = url.partition("://")
    if not separator:
        scheme, rest = "", url
    host_and_port = rest.rsplit("@", 1)[-1]
    return f"{scheme}://{host_and_port}" if scheme else host_and_port


#: The variable the rest of the memory subsystem already reads
#: (``fleet_memory_client``), so the publisher and the reader agree on where
#: the bus is rather than each keeping its own opinion.
NATS_URL_ENV = "FLEET_MEMORY_NATS_URL"
"""How long a publish run may spend hanging up before it walks away.

Closing the connection is not free. ``NATSClient.disconnect`` calls
``nc.drain()`` (``nats_core/client.py``), and nats-py's drain waits on the
server with its own default of THIRTY seconds. So a broker that accepts the
connection and then stalls used to hold the caller for half a minute AFTER the
caller's own deadline had already passed — the autobuild terminal's 20-second
capture ceiling turned into a ~50-second hold on the build's last line.

Five seconds is a generous hang-up for a healthy local broker and a short one
for a sick one. Overrunning it costs nothing that matters: the episode bytes
are already written to the socket by then, and the process is exiting the
publish either way. The overrun is logged in plain words rather than waited on.
"""


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


def broker_address() -> str:
    """Where the bus is, as a URL carrying no credentials.

    Takes host and port from the shared setting and drops anything before the
    ``@``: that variable holds the fleet-memory user's DSN, and this publisher
    connects as ``guardkit`` with its own password.
    """
    configured = os.getenv(NATS_URL_ENV, "").strip()
    return address_without_secrets(configured) if configured else DEFAULT_NATS_URL


def build_nats_client(password: str) -> NATSClient:
    """Build NATSClient with guardkit harvest configuration.

    Args:
        password: The NATS password for the guardkit user.

    Returns:
        Configured NATSClient instance ready for connection.
    """
    config = NATSConfig(
        # Only WHERE the broker is comes from the environment. The identity
        # stays guardkit's own: the variable holds fleet-memory's DSN, whose
        # embedded credentials are a different user's and must not be borrowed.
        url=broker_address(),
        user="guardkit",
        password=SecretStr(password),
        name="guardkit-harvest",
    )
    return NATSClient(config, source_id="guardkit-harvest")


async def _disconnect_bounded(client: NATSClient) -> None:
    """Hang up, with a deadline, and say so if the deadline was reached.

    A drain that never answers must not become the caller's problem: by the time
    this runs the episodes are already on the wire, so waiting longer buys
    nothing and holds a build's last line open. The overrun (and any error from
    the close itself) is logged once and swallowed — a teardown must not be the
    thing that raises out of a ``finally``, where it would mask the real error.
    """
    try:
        await asyncio.wait_for(
            client.disconnect(), timeout=PUBLISH_TEARDOWN_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.warning(
            "NATS did not finish closing within %.1fs; walking away. The "
            "episodes were already written to the socket, so this affects "
            "nothing but the wait.",
            PUBLISH_TEARDOWN_TIMEOUT_SECONDS,
        )
    except asyncio.CancelledError:
        # The caller's own deadline fired. Do not swallow the cancellation.
        raise
    except Exception as exc:
        logger.warning("Closing the NATS connection failed: %s", exc)


async def publish_episodes(
    episodes: list[MemoryEpisodeV1],
    client: NATSClient | None = None,
) -> PublishSummary:
    """Publish memory episodes to NATS with 900KB guard and idempotent retry.

    Connects to NATS, publishes each episode, and disconnects. Oversized episodes
    (>900KB) are caught per-episode, logged with actionable guidance, and skipped
    without aborting the run. Idempotency is server-side via deterministic
    episode_id → Nats-Msg-Id JetStream deduplication.

    Hanging up is bounded by ``PUBLISH_TEARDOWN_TIMEOUT_SECONDS``: a stalled
    broker cannot hold the caller for nats-py's 30-second drain default after
    the caller's own deadline has passed.

    Note on that deduplication: the id is whatever the caller put in
    ``episode.episode_id``. The harvest wants it per-CONTENT so re-runs collapse.
    A build-outcome capture wants it per-WRITE so a rebuild is not swallowed, and
    scopes it before calling here (``fleet_memory_payloads.with_broker_dedup_scope``).

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
        try:
            await asyncio.wait_for(
                client.connect(), timeout=PUBLISH_CONNECT_TIMEOUT_SECONDS
            )
        except Exception as exc:
            # NAME THE ADDRESS. "the memory writer did not complete" reads as
            # slowness; the real fault was a refused connection to a host with
            # no broker on it, and that detail was thrown away for six days.
            # CancelledError is not an Exception, so the caller's own deadline
            # still passes straight through here untouched.
            where = broker_address()
            raise RuntimeError(
                f"could not reach the bus at {where} within "
                f"{PUBLISH_CONNECT_TIMEOUT_SECONDS:.0f}s "
                f"({type(exc).__name__}). Nothing was published. Set "
                f"{NATS_URL_ENV} if the broker is somewhere else."
            ) from exc

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
        # Always disconnect, even if errors occurred — but never wait on it
        # longer than PUBLISH_TEARDOWN_TIMEOUT_SECONDS.
        await _disconnect_bounded(client)

    return PublishSummary(
        published=published,
        skipped_oversized=skipped_oversized,
        counts_per_type=dict(type_counts),
    )
