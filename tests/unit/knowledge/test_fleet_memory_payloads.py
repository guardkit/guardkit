"""Unit tests for fleet_memory_payloads.build_memory_episode + sanitize_identifier.

Proves guardkit builds typed ``MemoryEpisodeV1`` episodes whose JSON body is accepted by
the REAL fleet-memory payload registry (a pre-DLQ contract check), with identifiers
sanitised to fleet-memory's ``^[a-zA-Z0-9_]+$`` rule and natural keys that match the
relay's deterministic record identity.

Coverage Target: >=85%

See: TASK-MEM08-003/004; relay routing fleet_memory/relay/service.py::_ingest_json.
"""

from __future__ import annotations

import json

import pytest

from guardkit.knowledge.fleet_memory_mapping import GroupMapping, resolve
from guardkit.knowledge.fleet_memory_payloads import (
    build_memory_episode,
    sanitize_identifier,
)

# The real fleet-memory payload registry — used to assert each built body validates.
fm_registry = pytest.importorskip("fleet_memory.payloads.registry")
fm_identity = pytest.importorskip("fleet_memory.writer.identity")


def _map(payload_type, tags, disposition="migrate"):
    return GroupMapping(
        project="guardkit",
        payload_type=payload_type,
        domain_tags=list(tags),
        disposition=disposition,
    )


# ============================================================================
# sanitize_identifier
# ============================================================================


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("TASK-1234", "TASK_1234"),
        ("TASK-FIX-A1B2", "TASK_FIX_A1B2"),
        ("ADR-0001", "ADR_0001"),
        ("already_ok", "already_ok"),
        ("with spaces & colons:1", "with_spaces_colons_1"),
        ("---", "unknown"),
        ("", "unknown"),
    ],
)
def test_sanitize_identifier(raw, expected):
    assert sanitize_identifier(raw) == expected


def test_sanitized_identifier_matches_fleet_memory_contract():
    """Sanitised ids must satisfy fleet-memory's identifier pattern (no DLQ poison)."""
    import re

    pattern = re.compile(r"^[a-zA-Z0-9_]+$")
    for raw in ("TASK-1234", "TASK-FIX-A1B2", "ADR-0001", "weird:/id name"):
        assert pattern.match(sanitize_identifier(raw))


# ============================================================================
# build_memory_episode — structured (json) types
# ============================================================================


def test_build_outcome_shape_and_validates():
    body = {
        "task_id": "TASK-1234",
        "success": True,
        "duration_minutes": 5,
        "approach_used": "TDD",
        "lessons_learned": ["pin env", "verify nonce"],
        "feature_id": "FEAT-X",
        "completed_at": "2026-06-29T10:00:00+00:00",
    }
    ep = build_memory_episode(
        _map("build_outcome", ["task"]),
        name="OUT-1: TASK-1234 - OAuth2",
        episode_body=json.dumps(body),
    )
    assert ep.content_format == "json"
    assert ep.payload_type == "build_outcome"
    assert ep.episode_type == "build_outcome"  # NATS-safe subject segment
    assert ep.project_id == "guardkit"
    assert ep.episode_id == "build_outcome:guardkit:TASK_1234"

    sent = json.loads(ep.body)
    assert sent["identifier"] == "TASK_1234"
    assert sent["status"] == "success"
    assert sent["duration_seconds"] == 300
    assert sent["domain_tags"] == ["task"]
    assert sent["source_ref"] == "FEAT-X"

    # Validates against the REAL BuildOutcomePayload (would be a DLQ poison otherwise).
    model = fm_registry.get_model_for_type("build_outcome")
    inst = model(**sent)
    assert inst.natural_key == "build_outcome:guardkit:TASK_1234"
    # The publish episode_id equals the relay's deterministic uuid5 input (the natural key).
    assert ep.episode_id == inst.natural_key


def test_build_outcome_failure_status_and_zero_duration():
    ep = build_memory_episode(
        _map("build_outcome", ["task"]),
        name="OUT-2: TASK-9 - failed",
        episode_body=json.dumps({"task_id": "TASK-9", "success": False}),
    )
    sent = json.loads(ep.body)
    assert sent["status"] == "failure"
    assert sent["duration_seconds"] == 0  # required int present even when unknown


def test_build_adr_validates():
    ep = build_memory_episode(
        _map("adr", ["decision"]),
        name="adr_ADR-0001",
        episode_body=json.dumps(
            {"id": "ADR-0001", "decision": "Adopt fleet-memory", "status": "accepted"}
        ),
    )
    assert ep.payload_type == "adr"
    sent = json.loads(ep.body)
    assert sent["identifier"] == "ADR_0001"
    inst = fm_registry.get_model_for_type("adr")(**sent)
    assert inst.natural_key == "adr:guardkit:ADR_0001"


def test_build_adr_missing_decision_falls_back():
    """ADR 'decision' is required by the model; a missing one gets a safe placeholder."""
    ep = build_memory_episode(
        _map("adr", ["decision"]),
        name="adr_ADR-0002",
        episode_body=json.dumps({"id": "ADR-0002", "title": "Untitled"}),
    )
    sent = json.loads(ep.body)
    # Validates (decision + status both present, non-empty)
    inst = fm_registry.get_model_for_type("adr")(**sent)
    assert inst.decision  # non-empty
    assert inst.status == "accepted"


def test_build_warning_validates():
    ep = build_memory_episode(
        _map("warning", ["failure", "approach"]),
        name="failed_approach_FAIL-7",
        episode_body=json.dumps({"id": "FAIL-7", "summary": "retry storm", "severity": "high"}),
    )
    assert ep.payload_type == "warning"
    sent = json.loads(ep.body)
    inst = fm_registry.get_model_for_type("warning")(**sent)
    assert inst.natural_key == "warning:guardkit:FAIL_7"
    assert inst.severity == "high"
    assert inst.message == "retry storm"


def test_store_key_is_recomputable_uuid5():
    """The audit can locate a record by recomputing uuid5(NS, natural_key)."""
    ep = build_memory_episode(
        _map("build_outcome", ["task"]),
        name="OUT: TASK-1234",
        episode_body=json.dumps({"task_id": "TASK-1234", "success": True}),
    )
    key = fm_identity.record_identity(ep.episode_id)
    assert str(key)  # a valid UUID string
    assert key.version == 5


# ============================================================================
# build_memory_episode — prose fallback + edge cases
# ============================================================================


def test_document_type_uses_prose_chunk_path():
    """document (no structured builder) → markdown/chunk path (prose embedded)."""
    ep = build_memory_episode(
        _map("document", ["architecture"]),
        name="System Overview",
        episode_body="# System Overview\n\nThe orchestrator coordinates waves.",
    )
    assert ep.content_format == "markdown"
    assert ep.payload_type is None  # chunk path has no typed payload
    assert "System Overview" in ep.body


def test_non_json_body_tolerated():
    """A non-JSON episode_body is wrapped, not crashed, for structured types."""
    ep = build_memory_episode(
        _map("build_outcome", ["task"]),
        name="TASK-5 raw",
        episode_body="not json at all",
    )
    # Identifier recovered from the name; still a valid build_outcome.
    sent = json.loads(ep.body)
    assert sent["identifier"] == "TASK_5"


def test_resolve_adrs_maps_to_adr():
    """The ADRService runtime group_id 'adrs' resolves (was an unmapped no-op)."""
    mapping = resolve("adrs")
    assert mapping is not None
    assert mapping.payload_type == "adr"
    assert mapping.disposition == "migrate"
