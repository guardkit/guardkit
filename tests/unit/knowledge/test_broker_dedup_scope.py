"""A rebuild's outcome must not be swallowed by the broker's duplicate window.

THE DEFECT THESE TESTS PIN. Guardkit publishes a build outcome with
``Nats-Msg-Id`` set to ``episode.episode_id`` (nats-core ``client.py``:
``publish_episode`` → ``nc.publish(subject, data, headers={"Nats-Msg-Id":
episode.episode_id})``), and that id was the episode's PER-TASK natural key
(``build_outcome:guardkit:TASK_X``). Two builds of the same task inside
JetStream's duplicate window therefore carried the SAME message id: the second
publish was accepted at the socket, dropped by the server, and guardkit logged
a green "published" line over the top of it. The rebuild's outcome — which is
usually the one that matters, because it is the one that ran last — silently
never existed.

THE CURE THESE TESTS PIN. The message id is scoped per WRITE; the payload, and
therefore the store's upsert key, stays per TASK. So:

- two captures of one task ⇒ two distinct message ids (both arrive),
- retries inside ONE capture ⇒ one message id (still deduped),
- the store's key and latest-write-wins semantics ⇒ unchanged.

Nothing here touches a broker, a store, or the network: the NATS connection
object is faked, so the real ``publish_episode`` runs and its headers are
inspected without a socket.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from guardkit.knowledge.fleet_memory_mapping import resolve
from guardkit.knowledge.fleet_memory_payloads import (
    build_memory_episode,
    with_broker_dedup_scope,
)

pytest.importorskip("nats_core")

from nats_core.client import NATSClient  # noqa: E402
from nats_core.config import NATSConfig  # noqa: E402


TOKEN = "OUT-1A2B3C4D"


def _outcome_episode(task_id: str = "TASK-DEDUP-001"):
    """A real typed build_outcome episode, built by the production builder."""
    mapping = resolve("task_outcomes")
    assert mapping is not None, "task_outcomes must stay mapped for this test"
    return build_memory_episode(
        mapping,
        name=f"OUT-XXXX: {task_id} - a build",
        episode_body=json.dumps(
            {"task_id": task_id, "success": True, "duration_minutes": 3}
        ),
        project="guardkit",
    )


def _prose_episode():
    """A markdown episode — the path where episode_id IS the record identity."""
    mapping = resolve("task_outcomes")
    assert mapping is not None
    from guardkit.knowledge.fleet_memory_payloads import _build_prose_episode

    return _build_prose_episode(
        mapping,
        name="a document",
        episode_body="some prose",
        source="user_added",
        data={"content": "some prose"},
        project="guardkit",
    )


# ============================================================================
# The scoping function itself
# ============================================================================


class TestWithBrokerDedupScope:
    """One write, one message id — and nothing else moves."""

    def test_typed_episode_gets_a_per_write_message_id(self):
        episode = _outcome_episode()
        natural_key = episode.episode_id

        scoped = with_broker_dedup_scope(episode, TOKEN)

        assert scoped.episode_id == f"{natural_key}.{TOKEN}"

    def test_the_original_episode_is_not_mutated(self):
        episode = _outcome_episode()
        natural_key = episode.episode_id

        with_broker_dedup_scope(episode, TOKEN)

        # The caller still holds the natural key — it is what add_episode hands
        # back and what a reader looks the record up by.
        assert episode.episode_id == natural_key

    def test_nothing_but_the_message_id_changes(self):
        """The store reads the BODY. If scoping touched it, semantics moved."""
        episode = _outcome_episode()
        scoped = with_broker_dedup_scope(episode, TOKEN)

        before = episode.model_dump()
        after = scoped.model_dump()
        assert before.pop("episode_id") != after.pop("episode_id")
        assert before == after
        # And the body — the relay's typed path builds the record key from
        # THESE fields (project/identifier), never from episode_id.
        assert json.loads(scoped.body) == json.loads(episode.body)

    def test_prose_episodes_are_left_alone(self):
        """There ``episode_id`` is the chunk key: scoping would DUPLICATE."""
        episode = _prose_episode()

        scoped = with_broker_dedup_scope(episode, TOKEN)

        assert scoped is episode
        assert scoped.episode_id == episode.episode_id

    def test_no_token_means_no_scoping(self):
        """The harvest wants collapse-by-content, and asks for it by omission."""
        episode = _outcome_episode()

        assert with_broker_dedup_scope(episode, "") is episode

    def test_a_missing_episode_is_returned_as_is(self):
        assert with_broker_dedup_scope(None, TOKEN) is None


# ============================================================================
# The header nats-core actually stamps
# ============================================================================


class _FakeConnection:
    """Stands in for the live ``nats.aio.client.Client``. Records, sends nothing."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, subject, data, headers=None):
        self.published.append((subject, dict(headers or {})))


def _client_with_fake_connection() -> tuple[NATSClient, _FakeConnection]:
    client = NATSClient(
        NATSConfig(url="nats://127.0.0.1:9", name="test"), source_id="test"
    )
    connection = _FakeConnection()
    # No connect() — the point is to run the REAL publish_episode without one.
    client._nc = connection
    return client, connection


class TestTheMessageIdIsWhatTheBrokerDedupesOn:
    """Pins the link this whole cure rests on, instead of asserting it in prose."""

    def test_publish_episode_stamps_the_episode_id_as_the_message_id(self):
        client, connection = _client_with_fake_connection()
        episode = _outcome_episode()

        asyncio.run(client.publish_episode(episode))

        _subject, headers = connection.published[0]
        assert headers["Nats-Msg-Id"] == episode.episode_id

    def test_two_writes_of_one_task_are_two_messages_to_the_broker(self):
        client, connection = _client_with_fake_connection()
        episode = _outcome_episode()

        asyncio.run(client.publish_episode(with_broker_dedup_scope(episode, "OUT-A")))
        asyncio.run(client.publish_episode(with_broker_dedup_scope(episode, "OUT-B")))

        ids = [headers["Nats-Msg-Id"] for _subject, headers in connection.published]
        assert ids[0] != ids[1], ids
        # Same subject, same task, same natural key underneath both.
        assert all(i.startswith(episode.episode_id + ".") for i in ids)

    def test_a_retry_inside_one_write_is_still_one_message(self):
        """The token is minted once per capture, so a resend collapses."""
        client, connection = _client_with_fake_connection()
        episode = with_broker_dedup_scope(_outcome_episode(), TOKEN)

        asyncio.run(client.publish_episode(episode))
        asyncio.run(client.publish_episode(episode))  # the retry

        ids = [headers["Nats-Msg-Id"] for _subject, headers in connection.published]
        assert ids[0] == ids[1], ids


# ============================================================================
# The write path end to end (publish faked at the harvest publisher)
# ============================================================================


def _client_under_test():
    from guardkit.knowledge.fleet_memory_client import (
        FleetMemoryClient,
        FleetMemoryConfig,
    )

    client = FleetMemoryClient(
        FleetMemoryConfig(
            enabled=True,
            postgres_dsn="postgresql://test:test@localhost:5433/test",
            embed_url="http://localhost:9000/v1",
            embed_model="embed",
            embed_dims=768,
            nats_url="nats://127.0.0.1:9",
        )
    )
    client._nats_available = True
    return client


class _RecordingPublisher:
    """Replaces ``publish_episodes``: records the episodes, sends nothing."""

    def __init__(self) -> None:
        self.episodes: list = []

    async def __call__(self, episodes, client=None):
        from guardkit.memory.harvest_publisher import PublishSummary

        self.episodes.extend(episodes)
        return PublishSummary(
            published=len(episodes), skipped_oversized=0, counts_per_type={}
        )


class TestCaptureHandsTheBrokerOneIdPerWrite:
    """Driven through the real ``capture_task_outcome_verified``."""

    def _capture(self, monkeypatch, publisher, task_id="TASK-DEDUP-010"):
        from guardkit.knowledge import outcome_manager
        from guardkit.knowledge.entities.outcome import OutcomeType

        client = _client_under_test()
        monkeypatch.setattr(
            "guardkit.memory.harvest_publisher.publish_episodes", publisher
        )
        monkeypatch.setattr(
            outcome_manager, "get_memory_client", lambda: client
        )
        return asyncio.run(
            outcome_manager.capture_task_outcome_verified(
                outcome_type=OutcomeType.TASK_COMPLETED,
                task_id=task_id,
                task_title="a build",
                task_requirements="do the thing",
                success=True,
                summary="it worked",
            )
        )

    def test_two_captures_of_one_task_publish_two_message_ids(self, monkeypatch):
        publisher = _RecordingPublisher()

        first = self._capture(monkeypatch, publisher)
        second = self._capture(monkeypatch, publisher)

        first_id, second_id = (e.episode_id for e in publisher.episodes)
        assert first_id != second_id, (first_id, second_id)
        # ...and each is its own capture's id, so an operator can join the log
        # line to the message the broker saw.
        assert first_id.endswith(first.outcome_id)
        assert second_id.endswith(second.outcome_id)

    def test_the_key_handed_back_is_the_per_task_natural_key(self, monkeypatch):
        """The store's identity must NOT move: latest write still wins."""
        publisher = _RecordingPublisher()

        first = self._capture(monkeypatch, publisher)
        second = self._capture(monkeypatch, publisher)

        assert first.episode_key == second.episode_key
        assert first.episode_key == "build_outcome:guardkit:TASK_DEDUP_010"
        # The scoped id never leaks into what the caller reports.
        assert first.outcome_id not in first.episode_key

    def test_the_published_body_is_identical_for_both_writes_but_for_time(
        self, monkeypatch
    ):
        """Same task, same identifier — the record the relay keys on is one record."""
        publisher = _RecordingPublisher()

        self._capture(monkeypatch, publisher)
        self._capture(monkeypatch, publisher)

        bodies = [json.loads(e.body) for e in publisher.episodes]
        assert bodies[0]["identifier"] == bodies[1]["identifier"]
        assert bodies[0]["project"] == bodies[1]["project"]
