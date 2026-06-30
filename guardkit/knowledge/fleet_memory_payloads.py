"""Build typed fleet-memory ``MemoryEpisodeV1`` episodes from guardkit episode data.

The fleet-memory relay (``fleet_memory.relay.service.RelayService.ingest``) routes an
incoming ``MemoryEpisodeV1`` by ``content_format``:

- ``content_format="json"`` (with ``payload_type`` set) → the typed path
  (``_ingest_json``): the JSON ``body`` is parsed and fed to the registered payload
  model (``payload_model(**json.loads(body))``), then written by ``DeterministicWriter``
  with a stable ``natural_key`` and idempotent content-hash upsert. This is the path
  that produces type-filterable, natural-keyed records.
- ``content_format="markdown"``/``"text"`` → the prose path (``_ingest_prose``): the body
  is chunked and embedded (no ``natural_key``). This is what the harvest used.

This module is guardkit's single source of truth for translating a
``(group_id → GroupMapping)`` plus the call-site ``episode_body`` (a ``json.dumps(dict)``
string) into the correct typed ``body`` so guardkit's dual-writes land as retrievable
records. Identifiers are sanitised to fleet-memory's ``^[a-zA-Z0-9_]+$`` contract
(``fleet_memory.payloads.base.BasePayload`` rejects hyphens with
``IdentifierValidationError`` → relay ``PoisonEpisodeError`` → DLQ).

See TASK-MEM08-003/004. Relay routing: ``fleet_memory/relay/service.py``. Payload models:
``fleet_memory/payloads/models.py``. Store key: ``uuid5(NS, "{type}:{project}:{id}")``.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

from guardkit.knowledge.fleet_memory_mapping import GroupMapping

logger = logging.getLogger(__name__)


def sanitize_identifier(value: str) -> str:
    """Coerce a guardkit id (e.g. ``"TASK-FIX-A1B2"``) to fleet-memory's identifier
    contract ``^[a-zA-Z0-9_]+$``.

    fleet-memory's ``BasePayload`` validates ``project`` and ``identifier`` against
    ``IDENTIFIER_PATTERN`` (underscores only — no hyphens, colons or spaces); a
    non-conforming identifier raises ``IdentifierValidationError``, which the relay maps
    to ``PoisonEpisodeError`` and routes to the DLQ. Guardkit must therefore sanitise
    before publishing. The mapping is deterministic so writes, reads and audits agree on
    the same key (``"TASK-1234"`` → ``"TASK_1234"`` → natural_key
    ``"build_outcome:guardkit:TASK_1234"``).
    """
    if not value:
        return "unknown"
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return cleaned or "unknown"


def _extract(text: Optional[str], pattern: str) -> Optional[str]:
    """Return the first regex match in ``text`` (used to recover an id from an episode
    name like ``"OUT-1A2B: TASK-1234 - title"``)."""
    match = re.search(pattern, text or "")
    return match.group(0) if match else None


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _join_lines(value: Any) -> Optional[str]:
    """Flatten a list-of-strings (e.g. ``lessons_learned``) into embeddable prose."""
    if isinstance(value, (list, tuple)):
        joined = "\n".join(str(item) for item in value if item)
        return joined or None
    if isinstance(value, str):
        return value or None
    return None


def _parse_dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


# --- Per-payload-type body builders ------------------------------------------------
#
# Each builder returns (type_specific_body_fields, raw_identifier, source_ref,
# occurred_at). The common BasePayload fields (project, identifier, source_ref,
# domain_tags) are added by build_memory_episode. The body must contain exactly the
# fields the registered fleet-memory payload model declares; unknown fields are dropped
# by the model's ``extra="ignore"`` config (so forward-compat fields like the post-003
# build_outcome task_id/lessons/approach are safe to send before the relay supports them).


def _build_outcome(data: dict, name: str) -> tuple[dict, str, Optional[str], Optional[datetime]]:
    """``task_outcomes`` (TaskOutcome.to_episode_body) → ``build_outcome`` payload."""
    task_id = data.get("task_id") or _extract(name, r"TASK-[\w-]+") or name
    duration_minutes = data.get("duration_minutes")
    duration_seconds = _coerce_int(duration_minutes) * 60 if duration_minutes is not None else 0
    body = {
        "status": "success" if data.get("success") else "failure",
        "duration_seconds": duration_seconds,
        # TASK-MEM08-003 enrichment fields. Dropped by the current relay's
        # BuildOutcomePayload (extra="ignore"); persisted once 003 + image rebuild land.
        "task_id": task_id,
        "lessons": _join_lines(data.get("lessons_learned")),
        "approach": data.get("approach_used"),
    }
    source_ref = data.get("feature_id") or task_id
    return body, task_id, source_ref, _parse_dt(data.get("completed_at"))


def _build_adr(data: dict, name: str) -> tuple[dict, str, Optional[str], Optional[datetime]]:
    """``adrs``/``project_decisions``/``architecture_decisions`` → ``adr`` payload."""
    adr_id = data.get("id") or _extract(name, r"ADR-\d+|DECISION-[\w-]+") or name
    body = {
        "decision": data.get("decision") or data.get("title") or "(no decision recorded)",
        "status": data.get("status") or "accepted",
    }
    source_ref = data.get("source_task_id") or adr_id
    return body, adr_id, source_ref, _parse_dt(data.get("created_at"))


def _build_warning(data: dict, name: str) -> tuple[dict, str, Optional[str], Optional[datetime]]:
    """``failure_patterns``/``failed_approaches`` → ``warning`` payload."""
    ident = (
        data.get("id")
        or _extract(name, r"FAIL-[\w-]+|PATTERN-[\w-]+")
        or name
    )
    body = {
        "severity": str(data.get("severity") or "medium"),
        "message": str(
            data.get("message") or data.get("summary") or data.get("description") or name
        ),
    }
    source_ref = data.get("source_task_id") or data.get("task_id") or ident
    return body, ident, source_ref, _parse_dt(data.get("created_at"))


# payload_type → type-specific body builder. Types with no builder (e.g. ``document``,
# ``seed_module``) fall back to the prose/chunk path, which is the right home for raw
# document text (DocumentPayload declares no prose field, so a JSON-typed document would
# embed only structural metadata).
_BODY_BUILDERS: dict[str, Callable[[dict, str], tuple]] = {
    "build_outcome": _build_outcome,
    "adr": _build_adr,
    "warning": _build_warning,
}


def _parse_episode_body(episode_body: str) -> dict:
    """Call sites pass ``json.dumps(dict)``; tolerate raw prose by wrapping it."""
    try:
        data = json.loads(episode_body)
    except (TypeError, json.JSONDecodeError):
        return {"content": episode_body}
    return data if isinstance(data, dict) else {"content": episode_body}


def build_memory_episode(
    mapping: GroupMapping,
    name: str,
    episode_body: str,
    source: str = "user_added",
) -> Any:
    """Build a typed ``MemoryEpisodeV1`` for the fleet-memory relay.

    Returns a ``nats_core.events.MemoryEpisodeV1`` ready to publish, or ``None`` if the
    episode cannot be built. Does not raise — callers fail open.

    Structured types (build_outcome/adr/warning) are emitted on the JSON typed path with
    a sanitised ``identifier`` and an ``episode_id`` equal to the natural key
    (``"{payload_type}:{project}:{identifier}"``) so JetStream dedup and the relay's
    deterministic record identity (``uuid5`` of that natural key) align. All other
    migrate types fall back to the markdown/chunk path.
    """
    from nats_core.events import MemoryEpisodeV1  # write-path dep (guardkit `memory` extra)

    data = _parse_episode_body(episode_body)
    project = mapping.project
    payload_type = mapping.payload_type
    builder = _BODY_BUILDERS.get(payload_type)

    if builder is None:
        return _build_prose_episode(mapping, name, episode_body, source, data)

    try:
        type_fields, raw_identifier, source_ref, occurred_at = builder(data, name)
    except Exception as exc:  # pragma: no cover - defensive; builders are total
        logger.warning("Failed to build %s body for %r: %s", payload_type, name, exc)
        return None

    identifier = sanitize_identifier(raw_identifier)
    natural_key = f"{payload_type}:{project}:{identifier}"
    body = {
        "project": project,
        "identifier": identifier,
        "source_ref": source_ref or identifier,
        "domain_tags": list(mapping.domain_tags),
        **type_fields,
    }

    return MemoryEpisodeV1(
        episode_id=natural_key,  # deterministic → Nats-Msg-Id dedup; mirrors relay uuid5 input
        project_id=project,  # subject segment memory.episode.{project_id}.{episode_type}
        episode_type=payload_type,  # subject segment (build_outcome/adr/warning are NATS-safe)
        content_format="json",  # → relay typed path (_ingest_json)
        payload_type=payload_type,
        body=json.dumps(body),
        name=name,
        source=source,
        source_ref=source_ref or identifier,
        occurred_at=occurred_at,
    )


def _build_prose_episode(
    mapping: GroupMapping,
    name: str,
    episode_body: str,
    source: str,
    data: dict,
) -> Any:
    """Fallback for non-structured migrate types (document, seed_module, …): publish the
    text on the markdown/chunk path so it is embedded and retrievable (no natural_key)."""
    from nats_core.events import MemoryEpisodeV1

    content = data.get("content") if isinstance(data, dict) else None
    body_text = content if isinstance(content, str) and content.strip() else episode_body
    identifier = sanitize_identifier(name)
    payload_type = mapping.payload_type or "document"
    natural_key = f"{payload_type}:{mapping.project}:{identifier}"

    return MemoryEpisodeV1(
        episode_id=natural_key,
        project_id=mapping.project,
        episode_type=payload_type,  # NATS-safe subject segment
        content_format="markdown",  # → relay prose/chunk path (_ingest_prose)
        payload_type=None,
        body=body_text,
        name=name,
        source=source,
    )
