"""Export FalkorDB (Graphiti) Episodic nodes to fleet-memory as scoped documents.

WS-1b of FEAT-MEM-09. Reads each FalkorDB graph's ``Episodic`` (raw source) nodes and
builds typed ``DocumentPayload`` ``MemoryEpisodeV1`` episodes carrying the node's prose
in ``content`` plus the source group's ``domain_tags`` — so the migrated prose is BOTH
semantically searchable AND group-scoped (WS-1a added ``DocumentPayload.content``).

Design notes:
- The Qwen2.5-EXTRACTED layer (``Entity`` nodes + ``RELATES_TO``/``MENTIONS`` edges) is
  NOT exported — fleet-memory is pure-embeddings; the raw ``Episodic`` prose is the
  migratable source. High-fact-density recovery for the high-value graphs is a separate
  optional distillation pass (WS-2b), not this bulk export.
- Every migrated node becomes ``payload_type="document"``; the source group identity is
  carried in ``domain_tags`` (from ``fleet_memory_mapping`` for mapped groups, or the
  sanitised group name for unmapped ones — fail-open, never silently drop content).
- ``disposition="retire"`` groups are skipped (already covered by the FEAT-HARV harvest
  corpus — no double-ingest).
- Publishing reuses ``harvest_publisher.publish_episodes`` unchanged (per-episode 900KB
  guard + idempotent ``episode_id`` = ``natural_key`` → JetStream dedup).

This module does NO NATS work and NO FalkorDB writes — it reads and constructs episodes.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Optional

from nats_core.events import MemoryEpisodeV1

from guardkit.knowledge.fleet_memory_mapping import resolve
from guardkit.knowledge.fleet_memory_payloads import sanitize_identifier

logger = logging.getLogger(__name__)


@dataclass
class GraphExportResult:
    """Result of building export episodes from FalkorDB graphs.

    Attributes:
        episodes: Typed DocumentPayload MemoryEpisodeV1 episodes ready to publish.
        graphs_scanned: Number of graphs read.
        skipped_retired: Episodic nodes skipped because their group is retire-disposition.
        skipped_empty: Nodes skipped for empty/whitespace content.
        skipped_no_group: Graphs skipped because the name has no ``project__group`` shape.
        counts_per_project: Episode count by (sanitised) project.
    """

    episodes: list[MemoryEpisodeV1] = field(default_factory=list)
    graphs_scanned: int = 0
    skipped_retired: int = 0
    skipped_empty: int = 0
    skipped_no_group: int = 0
    counts_per_project: dict[str, int] = field(default_factory=dict)


def graph_name_to_project_group(graph_name: str) -> Optional[tuple[str, str]]:
    """Split a FalkorDB graph name into ``(project, group_id)``.

    Graphiti graph names follow ``{project}__{group_id}`` (e.g.
    ``guardkit__project_decisions`` → ``("guardkit", "project_decisions")``,
    ``lpa-platform__project_overview`` → ``("lpa_platform", "project_overview")``).
    The project segment is sanitised to fleet-memory's identifier contract
    (``^[a-zA-Z0-9_]+$``). Names with no ``__`` (bare system/misc graphs like
    ``guardkit``, ``product_knowledge``, ``role:architect``) return ``None`` — they are
    not per-project knowledge and are handled by the harvest corpus or ignored.

    Args:
        graph_name: FalkorDB graph name.

    Returns:
        ``(project, group_id)`` or ``None`` if the name is not project-scoped.
    """
    if "__" not in graph_name:
        return None
    project_raw, group_id = graph_name.split("__", 1)
    project = sanitize_identifier(project_raw)
    if not project or not group_id:
        return None
    return project, group_id


def _domain_tags_for(group_id: str) -> Optional[list[str]]:
    """Resolve the domain_tags to carry for a migrated group, or ``None`` to skip.

    - Mapped + migrate → the mapping's domain_tags (group-scoped retrieval preserved).
    - Mapped + retire → ``None`` (skip; harvest corpus covers it).
    - Unmapped → ``[sanitised group_id]`` (fail-open: preserve, never silently drop).
    """
    mapping = resolve(group_id)
    if mapping is not None:
        if mapping.disposition == "retire":
            return None
        return list(mapping.domain_tags)
    # Unmapped group name (e.g. project_knowledge, successful_fixes): keep it, tagged by
    # its own sanitised name so a future read can scope to it.
    return [sanitize_identifier(group_id).lower()]


def _parse_created_at(value: Any) -> datetime:
    """Best-effort parse of a FalkorDB ``created_at`` into a tz-aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def build_document_episode(
    project: str,
    group_id: str,
    node: dict,
) -> Optional[MemoryEpisodeV1]:
    """Build a typed ``DocumentPayload`` episode from one Episodic node, or ``None``.

    Returns ``None`` when the group is retire-disposition or the content is empty. The
    episode's ``body`` is the JSON DocumentPayload the relay's ``_ingest_json`` validates
    (prose in ``content`` + ``domain_tags``); ``episode_id`` is the ``natural_key`` for
    idempotent JetStream dedup on re-runs.

    Args:
        project: Sanitised fleet-memory project.
        group_id: Source Graphiti group_id (unsanitised; resolved for disposition/tags).
        node: Episodic node properties — reads ``content``/``name``/``uuid``/``created_at``.

    Returns:
        A typed ``MemoryEpisodeV1`` document, or ``None`` to skip.
    """
    domain_tags = _domain_tags_for(group_id)
    if domain_tags is None:
        return None  # retire-disposition group → skip

    content = node.get("content")
    if not isinstance(content, str) or not content.strip():
        return None  # empty content → skip

    # Identifier: prefer the node's stable uuid so re-runs are idempotent; fall back to
    # name. Sanitised to fleet-memory's ^[a-zA-Z0-9_]+$ contract.
    raw_identifier = node.get("uuid") or node.get("name") or content[:40]
    identifier = sanitize_identifier(str(raw_identifier))
    name = str(node.get("name") or identifier)
    source_ref = sanitize_identifier(group_id).lower() or "graphiti"

    natural_key = f"document:{project}:{identifier}"
    body = {
        "project": project,
        "identifier": identifier,
        "source_ref": source_ref,
        "domain_tags": domain_tags,
        "content": content,
    }

    return MemoryEpisodeV1(
        episode_id=natural_key,  # deterministic → Nats-Msg-Id dedup; mirrors relay uuid5 input
        project_id=project,
        episode_type="document",  # NATS-safe subject segment
        content_format="json",  # → relay typed path (DocumentPayload)
        payload_type="document",
        body=json.dumps(body),
        name=name,
        source="graphiti-migration",
        source_ref=source_ref,
        occurred_at=_parse_created_at(node.get("created_at")),
    )


def build_export_episodes(
    graphs: Iterable[tuple[str, Iterable[dict]]],
) -> GraphExportResult:
    """Build export episodes from an iterable of ``(graph_name, episodic_nodes)``.

    Pure and side-effect-free (no FalkorDB, no NATS) so it is unit-testable with
    synthetic graph data. The live FalkorDB reader (``read_falkordb_episodics``) supplies
    the ``graphs`` iterable.

    Args:
        graphs: Iterable of ``(graph_name, iterable_of_node_property_dicts)``.

    Returns:
        GraphExportResult with the built episodes and skip statistics.
    """
    result = GraphExportResult()
    per_project: Counter[str] = Counter()

    for graph_name, nodes in graphs:
        result.graphs_scanned += 1
        pg = graph_name_to_project_group(graph_name)
        if pg is None:
            result.skipped_no_group += 1
            logger.debug("Skipping non-project graph %r", graph_name)
            continue
        project, group_id = pg

        for node in nodes:
            episode = build_document_episode(project, group_id, node)
            if episode is None:
                # Distinguish retire vs empty for the report.
                if _domain_tags_for(group_id) is None:
                    result.skipped_retired += 1
                else:
                    result.skipped_empty += 1
                continue
            result.episodes.append(episode)
            per_project[project] += 1

    result.counts_per_project = dict(per_project)
    return result


def read_falkordb_episodics(
    host: str,
    port: int = 6379,
    project_filter: Optional[str] = None,
    limit_per_graph: Optional[int] = None,
) -> Iterator[tuple[str, list[dict]]]:
    """Yield ``(graph_name, episodic_node_dicts)`` from FalkorDB.

    Connects to FalkorDB, lists graphs, and for each graph whose name is project-scoped
    (and matches ``project_filter`` when given) runs ``MATCH (n:Episodic) RETURN
    properties(n)``. Only the raw Episodic (source) layer is read — never the extracted
    Entity/edge layer.

    Args:
        host: FalkorDB host (e.g. ``whitestocks``).
        port: FalkorDB port (default 6379).
        project_filter: If set, only graphs whose sanitised project equals this value
            (e.g. ``"guardkit"``) are read.
        limit_per_graph: Optional cap on Episodic nodes per graph (for dry-runs).

    Yields:
        ``(graph_name, [node_property_dict, ...])`` per matching graph.
    """
    from falkordb import FalkorDB

    db = FalkorDB(host=host, port=port)
    for graph_name in db.list_graphs():
        pg = graph_name_to_project_group(graph_name)
        if pg is None:
            continue
        project, _group_id = pg
        if project_filter is not None and project != project_filter:
            continue
        query = "MATCH (n:Episodic) RETURN properties(n) AS props"
        if limit_per_graph is not None:
            query += f" LIMIT {int(limit_per_graph)}"
        try:
            res = db.select_graph(graph_name).query(query)
        except Exception as exc:  # pragma: no cover - defensive against a bad graph
            logger.warning("FalkorDB read failed for graph %r: %s", graph_name, exc)
            continue
        nodes = [row[0] for row in res.result_set if isinstance(row[0], dict)]
        yield graph_name, nodes
