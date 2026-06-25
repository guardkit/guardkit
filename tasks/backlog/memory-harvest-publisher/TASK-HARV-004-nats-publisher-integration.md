---
id: TASK-HARV-004
title: NATS publisher integration (connect as guardkit, publish episodes)
task_type: feature
status: backlog
created: 2026-06-25T00:00:00Z
updated: 2026-06-25T00:00:00Z
complexity: 5
parent_review: TASK-REV-HARV
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
wave: 2
implementation_mode: task-work
depends_on: []
consumer_context:
  - task: TASK-HARV-003
    consumes: MemoryEpisodeV1
    framework: "nats_core.NATSClient.publish_episode"
    driver: "nats-core (pydantic MemoryEpisodeV1 envelope)"
    format_note: "project_id='guardkit' (underscores only, no hyphens or relay DLQs); episode_type matches ^[a-zA-Z0-9][a-zA-Z0-9\\-_]*$; content_format in {markdown,text,json}; body non-empty and <=900KB; episode_id deterministic ep-<sha256[:16]>"
---

# TASK-HARV-004: NATS publisher integration

## Objective

Connect as the provisioned `guardkit` NATS user and publish a list of
`MemoryEpisodeV1` through `nats_core.NATSClient.publish_episode`, handling the 900 KB
rejection per-episode and staying idempotent/resumable. **Consumes** the
`MemoryEpisodeV1` contract produced by TASK-HARV-003.

## Context

The broker user `guardkit` is already provisioned and verified live (publish rights on
`memory.episode.>`; no JetStream admin). The harvest's only identity job is to read
`GUARDKIT_NATS_PASSWORD` and build the `NATSConfig`. Idempotency is server-side:
JetStream dedupes on `Nats-Msg-Id = episode_id`, so re-publishing is a safe no-op.

## Acceptance Criteria

- [ ] `guardkit/memory/harvest_publisher.py` reads `GUARDKIT_NATS_PASSWORD` from the
      environment (optionally from an `--env-file` pointing at
      `nats-infrastructure/.env`); a missing/blank password raises an **actionable**
      error naming the variable and where to set it (does not connect with a blank pw).
- [ ] Builds `NATSConfig(url="nats://127.0.0.1:4222", user="guardkit",
      password=SecretStr(<pw>), name="guardkit-harvest")` and
      `NATSClient(cfg, source_id="guardkit-harvest")`.
- [ ] Publish lifecycle: `await client.connect()` → for each episode
      `await client.publish_episode(ep)` → `await client.disconnect()`
      (**`.disconnect()`, not `.close()`**).
- [ ] A `publish_episode` `ValueError` (body > 900 KB) is caught **per episode**: that
      episode is skipped and recorded with an actionable message (path/episode_id +
      size + "chunk upstream"); the loop continues — one oversized doc never aborts the
      run.
- [ ] Idempotent / resumable: no client-side dedupe state; correctness relies on the
      deterministic `episode_id` → `Nats-Msg-Id` JetStream dedupe. Re-running publishes
      the same ids.
- [ ] Does **not** hand-roll NATS publishing, subject construction, or the
      `Nats-Msg-Id` header — those are owned by `publish_episode`.
- [ ] Returns a publish summary: `published`, `skipped_oversized`, `counts_per_type`.
- [ ] Unit tests use a **fake/mock `NATSClient`** (no live broker) asserting:
      `connect` → N × `publish_episode` → `disconnect` ordering; the >900 KB episode is
      skipped with the actionable error; the run never aborts on a single oversized
      item.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Seam Tests

The following seam test validates the integration contract with the producer task
(TASK-HARV-003). Implement it to verify the boundary before integration.

```python
"""Seam test: verify MemoryEpisodeV1 contract from TASK-HARV-003."""
import re

import pytest
from nats_core.events import MemoryEpisodeV1, MAX_EPISODE_BODY_BYTES

_EPISODE_TYPE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]*$")


@pytest.mark.seam
@pytest.mark.integration_contract("MemoryEpisodeV1")
def test_memory_episode_v1_contract(sample_episode: MemoryEpisodeV1):
    """Verify a walker-produced episode matches the publish contract.

    Contract: project_id='guardkit' (no hyphens), episode_type subject-safe,
    content_format prose|json, body non-empty and <=900KB, episode_id ep-<hash>.
    Producer: TASK-HARV-003.
    """
    ep = sample_episode
    assert ep.project_id == "guardkit"
    assert "-" not in ep.project_id, "hyphen in project_id is DLQ poison"
    assert _EPISODE_TYPE_RE.match(ep.episode_type), ep.episode_type
    assert ep.content_format in {"markdown", "text", "json"}
    assert ep.body.strip(), "empty body must be filtered upstream"
    assert len(ep.body.encode()) <= MAX_EPISODE_BODY_BYTES
    assert ep.episode_id.startswith("ep-")


@pytest.mark.seam
@pytest.mark.integration_contract("MemoryEpisodeV1")
def test_subject_resolves_to_guardkit_namespace(sample_episode: MemoryEpisodeV1):
    """The helper must resolve memory.episode.guardkit.<episode_type>."""
    from nats_core.topics import Topics  # adjust import to the real module

    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=sample_episode.project_id,
        episode_type=sample_episode.episode_type,
    )
    assert subject == f"memory.episode.guardkit.{sample_episode.episode_type}"
```

## Implementation Notes

- A working reference for build-and-publish is
  `../fleet-memory/src/fleet_memory/reindex/publisher.py` (it publishes
  `content_format="json"`; the harvest mostly publishes `markdown`).
- `nats server check connection` as `guardkit` prints a `CRITICAL` round-trip warning —
  expected for a scoped publisher, **not** a fault. A plain `publish_episode` works.

## Coach Validation

```bash
pytest tests/ -v -k harvest_publisher
```
