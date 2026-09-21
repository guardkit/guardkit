"""Unit tests for FEAT-MEM-09 WS-0 — per-project scoping of fleet-memory reads/writes.

Proves the ``project`` dimension threads end-to-end instead of the old hardcoded
``"guardkit"``:
- ``build_memory_episode(project=...)`` sets the natural_key / project_id / body project
  on both the structured (json) and prose (markdown) paths.
- **A missing name writes NOTHING** (2026-09-21). The three tests that pinned the old
  fallback to ``"guardkit"`` — on the structured path, on the prose path, and on
  ``FleetMemoryConfig`` — moved with the change and now pin the refusal instead.
- ``FleetMemoryConfig.project`` has no default; ``GUARDKIT_MEMORY_PROJECT`` hands a name
  over on purpose through the env factory.
- ``FleetMemoryClient`` threads ``self.config.project`` into the write path.

Coverage Target: >=85%

See: docs/design/specs/memory-cutover/FEAT-MEM-09-fleet-migration-investigation.md (WS-0).
"""

from __future__ import annotations

import json

import pytest

from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryConfig,
    _load_fleet_config_from_env,
)
from guardkit.knowledge.fleet_memory_mapping import GroupMapping
from guardkit.knowledge.fleet_memory_payloads import build_memory_episode

# Write path builds a real MemoryEpisodeV1 (guardkit `memory` extra / nats_core).
pytest.importorskip("nats_core.events")
fm_registry = pytest.importorskip("fleet_memory.payloads.registry")


def _map(payload_type, tags, disposition="migrate"):
    return GroupMapping(
        payload_type=payload_type,
        domain_tags=list(tags),
        disposition=disposition,
    )


# ============================================================================
# build_memory_episode — project threading (structured json path)
# ============================================================================


def test_structured_episode_uses_explicit_project():
    """An explicit project scopes the natural_key / project_id / body, not 'guardkit'."""
    ep = build_memory_episode(
        _map("build_outcome", ["task"]),
        name="OUT-1: TASK-1234 - OAuth2",
        episode_body=json.dumps({"task_id": "TASK-1234", "success": True}),
        project="jarvis",
    )
    assert ep.project_id == "jarvis"
    assert ep.episode_id == "build_outcome:jarvis:TASK_1234"
    sent = json.loads(ep.body)
    assert sent["project"] == "jarvis"
    # Still validates against the REAL payload model under a non-guardkit project.
    inst = fm_registry.get_model_for_type("build_outcome")(**sent)
    assert inst.natural_key == "build_outcome:jarvis:TASK_1234"
    assert ep.episode_id == inst.natural_key


def test_structured_episode_with_no_name_writes_nothing(caplog):
    """MOVED 2026-09-21: project=None used to be filed under "guardkit"."""
    with caplog.at_level("ERROR"):
        ep = build_memory_episode(
            _map("adr", ["decision"]),
            name="adr_ADR-0001",
            episode_body=json.dumps(
                {"id": "ADR-0001", "decision": "Adopt fleet-memory", "status": "accepted"}
            ),
            project=None,
        )
    assert ep is None
    assert "no memory name was given" in caplog.text


def test_structured_episode_with_an_empty_name_writes_nothing():
    """An empty or blank name is refused exactly like a missing one."""
    for blank in ("", "   "):
        ep = build_memory_episode(
            _map("adr", ["decision"]),
            name="adr_ADR-0009",
            episode_body=json.dumps(
                {"id": "ADR-0009", "decision": "x", "status": "accepted"}
            ),
            project=blank,
        )
        assert ep is None


def test_the_name_cannot_be_omitted_at_all():
    """There is no default to omit it into: the call itself is a TypeError."""
    with pytest.raises(TypeError):
        build_memory_episode(
            _map("adr", ["decision"]),
            name="adr_ADR-0010",
            episode_body=json.dumps(
                {"id": "ADR-0010", "decision": "x", "status": "accepted"}
            ),
        )


# ============================================================================
# build_memory_episode — project threading (prose / markdown path)
# ============================================================================


def test_prose_episode_uses_explicit_project():
    """The document (prose) path scopes project_id + natural_key by the explicit project."""
    ep = build_memory_episode(
        _map("document", ["overview"]),
        name="project_overview_doc",
        episode_body=json.dumps({"content": "GuardKit is an AI software factory."}),
        project="study_tutor",
    )
    assert ep.content_format == "markdown"
    assert ep.project_id == "study_tutor"
    assert ep.episode_id == "document:study_tutor:project_overview_doc"


def test_prose_episode_with_no_name_writes_nothing():
    """MOVED 2026-09-21: the prose path used to fall back to "guardkit" too."""
    ep = build_memory_episode(
        _map("document", ["overview"]),
        name="another_doc",
        episode_body=json.dumps({"content": "prose"}),
        project=None,
    )
    assert ep is None


# ============================================================================
# FleetMemoryConfig / env factory
# ============================================================================


def test_config_has_no_project_by_default():
    """MOVED 2026-09-21: this used to assert the default was "guardkit"."""
    assert FleetMemoryConfig().project is None


def test_env_factory_reads_the_name_handed_over(monkeypatch, tmp_path):
    import guardkit.knowledge.fleet_memory_client as fmc

    monkeypatch.setenv("GUARDKIT_MEMORY_PROJECT", "forge")
    monkeypatch.chdir(tmp_path)
    fmc.reset_memory_project()
    try:
        cfg = _load_fleet_config_from_env()
    finally:
        fmc.reset_memory_project()
    assert cfg.project == "forge"


def test_env_factory_has_no_name_when_nothing_says_one(monkeypatch, tmp_path):
    """MOVED 2026-09-21: this used to assert the name fell back to "guardkit"."""
    import guardkit.knowledge.fleet_memory_client as fmc

    monkeypatch.delenv("GUARDKIT_MEMORY_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)  # a folder that declares nothing
    fmc.reset_memory_project()
    try:
        cfg = _load_fleet_config_from_env()
    finally:
        fmc.reset_memory_project()
    assert cfg.project is None


# ============================================================================
# FleetMemoryClient threads config.project into the write path
# ============================================================================


@pytest.mark.asyncio
async def test_client_threads_config_project_into_write(monkeypatch):
    """add_episode passes self.config.project to build_memory_episode."""
    import guardkit.knowledge.fleet_memory_client as fmc
    import guardkit.knowledge.fleet_memory_payloads as fmp

    captured: dict = {}

    def fake_build(mapping, name, episode_body, source="user_added", *, project):
        captured["project"] = project

        class _Ep:
            episode_id = f"build_outcome:{project}:TASK_1"

        return _Ep()

    class _Summary:
        published = 1
        skipped_oversized = 0

    async def fake_publish(episodes):
        return _Summary()

    monkeypatch.setattr(fmp, "build_memory_episode", fake_build)
    monkeypatch.setattr(
        "guardkit.memory.harvest_publisher.publish_episodes", fake_publish
    )

    client = fmc.FleetMemoryClient(FleetMemoryConfig(enabled=True, project="jarvis"))
    client._nats_available = True

    key = await client.add_episode(
        name="OUT: TASK-1",
        episode_body=json.dumps({"task_id": "TASK-1", "success": True}),
        group_id="task_outcomes",
    )

    assert captured["project"] == "jarvis"
    assert key == "build_outcome:jarvis:TASK_1"
