---
id: TASK-MEM09-002
title: WS-1 — graph_export pipeline (FalkorDB Episodic → fleet-memory documents)
status: in_review
created: '2026-07-01'
updated: '2026-07-01'
priority: high
feature_id: FEAT-MEM-09
implementation_mode: task-work
wave: 1
complexity: 5
task_type: feature
tags: [memory-cutover, fleet-memory, migration, FEAT-MEM-09]
depends_on: [TASK-MEM09-001]
---

# TASK-MEM09-002 — graph_export pipeline (WS-1)

> Migrate the raw Graphiti Episodic (source) prose from FalkorDB into fleet-memory as
> scoped-retrievable typed documents. The Qwen2.5-extracted Entity/edge layer is NOT
> migrated (fleet-memory is pure-embeddings). Operator decision (2026-07-01): option 2 —
> preserve group-scoped retrieval, so migrated prose must carry domain_tags, which
> required adding a prose field to fleet-memory's DocumentPayload (WS-1a).

## Design decision (why typed documents, not chunks)

fleet-memory retrieval EXCLUDES plain prose chunks from group-scoped reads
(`search(group_ids=[...])` filters by payload_type + domain_tags; chunks carry neither).
The typed `document` payload had no prose field, so it could not carry the text
retrievably. WS-1a adds `DocumentPayload.content`; WS-1b emits typed documents carrying
prose (`content`) + the source group's `domain_tags` — both semantically searchable and
group-scoped. Uniform `payload_type="document"`; group identity lives in `domain_tags`.

## Acceptance criteria

- [x] **WS-1a (fleet-memory, `68218dd`):** optional `content: str | None = None` on
      `DocumentPayload`; embedded content_json carries prose + domain_tags (round-trip
      verified). 2 tests; 518 unit green. Backward-compatible.
- [x] **WS-1b (guardkit, `a027fec0`):** `guardkit/memory/graph_export.py`
      (`graph_name_to_project_group`, `build_document_episode`, `build_export_episodes`
      pure builder, `read_falkordb_episodics` live reader) + `guardkit memory migrate-graph`
      CLI (`--project`/`--all-projects`/`--dry-run`/`--limit`/`--host`/`--port`).
- [x] retire-disposition groups skipped; unmapped group names fall back to a document
      tagged by the sanitised group name (fail-open, never silently dropped).
- [x] Idempotent: `episode_id = natural_key` (`document:{project}:{identifier}`), uuid-based
      identifier → JetStream dedup on re-runs. Reuses `publish_episodes` + `sanitize_identifier`.
- [x] Self-contained: does NOT modify `build_memory_episode` (zero regression to existing
      document writes).
- [x] Unit tests (15) incl. real-DocumentPayload validation of built bodies; 391
      memory/CLI/knowledge tests green.
- [x] Live dry-run: `migrate-graph --dry-run --project guardkit` builds 499 document
      episodes from 27 guardkit graphs, 0 errors.

## Remaining before the LIVE (non-dry-run) migration

1. **Rebuild the fleet-memory relay image** (WS-1a `DocumentPayload.content`). BasePayload
   is `extra="ignore"`, so an un-rebuilt relay SILENTLY DROPS `content`.
   `cd ../fleet-memory && docker compose -f deploy/relay/docker-compose.yml up -d --build`.
2. **WS-2 read-side:** `FleetMemoryClient.search` must add `"document"` to the resolved
   `payload_types` for group-scoped reads (else migrated docs, which are payload_type
   `document`, won't match a read that resolved to e.g. `adr`). Then verify scoped reads
   return migrated content against the live store.

## Notes

Part of FEAT-MEM-09 (`.guardkit/features/FEAT-MEM-09.yaml`). Next: WS-2 (`TASK-MEM09-003`)
runs the live migration (after the relay rebuild) + the read-side change + the optional
WS-2b distillation of the ~274 high-value nodes.
