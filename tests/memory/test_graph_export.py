"""Unit tests for graph_export — FalkorDB Episodic → fleet-memory documents (WS-1b).

Proves the pure builder path (no FalkorDB, no NATS) produces typed DocumentPayload
episodes carrying prose + the source group's domain_tags, skips retire-disposition and
empty nodes, scopes per project, and that the built body validates against the REAL
fleet-memory DocumentPayload model (a pre-DLQ contract check).

Coverage Target: >=85%

See: docs/design/specs/memory-cutover/FEAT-MEM-09-fleet-migration-investigation.md (WS-1b).
"""

from __future__ import annotations

import json

import pytest

from guardkit.memory.graph_export import (
    build_document_episode,
    build_export_episodes,
    graph_name_to_project_group,
)

# The built episode body must validate against the REAL DocumentPayload (with content).
pytest.importorskip("nats_core.events")
fm_registry = pytest.importorskip("fleet_memory.payloads.registry")


def _node(content="some prose content", name="n1", uuid="uuid-abc", created_at=None):
    return {"content": content, "name": name, "uuid": uuid, "created_at": created_at}


# ============================================================================
# graph_name_to_project_group
# ============================================================================


@pytest.mark.parametrize(
    "graph_name,expected",
    [
        ("guardkit__project_decisions", ("guardkit", "project_decisions")),
        ("lpa-platform__project_overview", ("lpa_platform", "project_overview")),
        ("study-tutor__task_outcomes", ("study_tutor", "task_outcomes")),
        ("guardkit", None),  # bare system/misc graph
        ("role:architect", None),  # no "__"
        ("product_knowledge", None),  # bare shared group
    ],
)
def test_graph_name_to_project_group(graph_name, expected):
    assert graph_name_to_project_group(graph_name) == expected


# ============================================================================
# build_document_episode
# ============================================================================


def test_migrate_group_builds_typed_document_with_prose_and_tags():
    ep = build_document_episode("guardkit", "project_decisions", _node(content="A decision."))
    assert ep is not None
    assert ep.content_format == "json"
    assert ep.payload_type == "document"
    assert ep.episode_type == "document"
    assert ep.project_id == "guardkit"
    assert ep.episode_id == "document:guardkit:uuid_abc"  # sanitised uuid, natural key

    body = json.loads(ep.body)
    assert body["content"] == "A decision."
    # project_decisions maps to domain_tags ["project"] (fleet_memory_mapping).
    assert body["domain_tags"] == ["project"]

    # Validates against the REAL DocumentPayload (would be DLQ poison otherwise).
    model = fm_registry.get_model_for_type("document")
    inst = model(**body)
    assert inst.natural_key == "document:guardkit:uuid_abc"
    assert inst.content == "A decision."
    assert inst.domain_tags == ["project"]


def test_retire_group_is_skipped():
    # guardkit_templates is retire-disposition (harvest corpus covers it).
    assert build_document_episode("guardkit", "guardkit_templates", _node()) is None


def test_empty_content_is_skipped():
    assert build_document_episode("guardkit", "project_decisions", _node(content="   ")) is None
    assert build_document_episode("guardkit", "project_decisions", _node(content=None)) is None


def test_unmapped_group_falls_back_to_document_tagged_by_group_name():
    # 'project_knowledge' / 'successful_fixes' exist in the live graph but not in the
    # 29-group map → fail-open document tagged by the sanitised group name (not dropped).
    ep = build_document_episode("guardkit", "successful_fixes", _node(content="a fix"))
    assert ep is not None
    body = json.loads(ep.body)
    assert body["domain_tags"] == ["successful_fixes"]
    assert body["content"] == "a fix"


def test_identifier_prefers_uuid_then_name():
    ep = build_document_episode(
        "guardkit", "project_overview", _node(uuid=None, name="My Doc Name")
    )
    assert ep is not None
    # name sanitised → identifier
    assert ep.episode_id == "document:guardkit:My_Doc_Name"


def test_project_is_used_in_natural_key():
    ep = build_document_episode("jarvis", "project_overview", _node())
    assert ep.project_id == "jarvis"
    assert ep.episode_id.startswith("document:jarvis:")


# ============================================================================
# build_export_episodes
# ============================================================================


def test_build_export_episodes_counts_and_skips():
    graphs = [
        # migrate group, 2 good nodes + 1 empty
        (
            "guardkit__project_decisions",
            [_node(uuid="u1"), _node(uuid="u2"), _node(uuid="u3", content="")],
        ),
        # retire group → all skipped
        ("guardkit__guardkit_templates", [_node(uuid="u4"), _node(uuid="u5")]),
        # non-project graph → skipped whole
        ("product_knowledge", [_node(uuid="u6")]),
        # another project
        ("jarvis__project_overview", [_node(uuid="u7")]),
    ]
    result = build_export_episodes(graphs)

    assert len(result.episodes) == 3  # 2 guardkit + 1 jarvis
    assert result.graphs_scanned == 4
    assert result.skipped_retired == 2
    assert result.skipped_empty == 1
    assert result.skipped_no_group == 1
    assert result.counts_per_project == {"guardkit": 2, "jarvis": 1}


def test_build_export_episodes_empty_input():
    result = build_export_episodes([])
    assert result.episodes == []
    assert result.graphs_scanned == 0


def test_all_built_episodes_are_real_memory_episodes():
    graphs = [("guardkit__failure_patterns", [_node(uuid="uX", content="a failure")])]
    result = build_export_episodes(graphs)
    ep = result.episodes[0]
    # failure_patterns is a MIGRATE group (warning) → still exported as a document
    # carrying the group's domain_tags [failure, pattern].
    body = json.loads(ep.body)
    assert body["domain_tags"] == ["failure", "pattern"]
    fm_registry.get_model_for_type("document")(**body)  # validates or raises
