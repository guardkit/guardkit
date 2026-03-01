# ADR-ARCH-001: Temporal Superseding Mechanism

- **Date**: 2026-03
- **Status**: Accepted
- **Task**: TASK-SAD-001

## Context

The `/arch-refine` and `/design-refine` commands need to update existing architecture decisions (ADRs) in the Graphiti knowledge graph while preserving version history. The key question is whether Graphiti's `upsert_episode()` with a stable `entity_id` allows prior versions to remain queryable after an update, or whether a more complex graph-native versioning scheme is needed.

### Options Evaluated

- **Option A**: Soft superseding via data-level encoding — create new episode with metadata tracking (entity_id, source_hash, previous_uuid, updated_at). Rely on Graphiti's existing behavior of preserving old episodes.
- **Option B**: Native graph edge support — add explicit `SUPERSEDES` edges between episode versions in the graph database, requiring custom Cypher queries and graph schema changes.

## Investigation Findings

### 1. Graphiti Preserves Old Episodes

The existing `upsert_episode()` implementation (ADR-GR-001) uses an "invalidate + create" strategy:

1. `episode_exists()` searches for a matching `entity_id` via semantic search
2. If found with identical `source_hash` → skip (content unchanged)
3. If found with different content → create a **new** episode via `add_episode()`
4. The old episode is **NOT deleted** — it remains in the graph

This means both old and new versions coexist in the knowledge graph after an update.

### 2. Old Content IS Retrievable via Semantic Search

Since old episodes are preserved, they remain queryable via `client.search()`. A semantic query matching old content (e.g., "REST API") will return the old episode alongside the new one. Both versions are visible to consumers.

### 3. entity_id Metadata Search Has Limitations

`episode_exists()` uses semantic search internally and iterates results to find matching `entity_id` in metadata. When multiple episodes share the same `entity_id`:

- The first match found is returned (depends on semantic ranking)
- There is no guarantee of returning the **latest** version
- `source_hash` matching reliably identifies exact content duplicates

### 4. Existing Metadata Infrastructure Is Sufficient

The current `EpisodeMetadata` dataclass already supports:
- `entity_id` — stable identifier across versions
- `source_hash` — SHA-256 content deduplication
- `created_at` / `updated_at` — temporal ordering
- `UpsertResult.previous_uuid` — version lineage tracking

## Decision

**Use Option A: Soft superseding via data-level encoding.**

The existing `upsert_episode()` behaviour already provides the foundation for temporal superseding:

1. **Preservation**: Old episodes remain in the graph (Graphiti's default behaviour)
2. **Deduplication**: `source_hash` prevents redundant episodes for unchanged content
3. **Lineage**: `UpsertResult.previous_uuid` tracks which episode was replaced
4. **Temporal ordering**: `created_at` (preserved) and `updated_at` (set on update) enable version sorting
5. **Discoverability**: Both old and new versions are findable via semantic search

For `/arch-refine` and `/design-refine`, the workflow is:

```
1. Generate new ADR content
2. Call upsert_episode(entity_id="adr-XXX", ...)
3. If content changed: new episode created, old preserved
4. UpsertResult.previous_uuid links new → old version
5. Consumers use updated_at to identify current version
```

No graph schema changes, custom Cypher queries, or `SUPERSEDES` edges are required.

## Consequences

**Positive:**
- Zero infrastructure changes — works with existing Graphiti capabilities
- Both versions remain searchable (no data loss)
- `previous_uuid` provides explicit version chain
- `source_hash` deduplication prevents unnecessary updates
- Consistent with existing ADR-GR-001 upsert strategy

**Negative:**
- Old episodes accumulate over time (no automatic cleanup)
- `episode_exists()` may return old version if ranked higher by semantic search
- No explicit `status=superseded` marking on old episodes (consumers must compare `updated_at`)
- Version chain is stored in `UpsertResult` (transient) not persisted in graph edges

**Mitigations:**
- Future: Add periodic cleanup for episodes older than N days with same `entity_id`
- Future: Persist `superseded_by` in episode metadata for explicit status
- For `/arch-refine`: Use `updated_at` comparison to identify current version

## Verification

Verified via 17 unit tests in `tests/knowledge/test_temporal_superseding.py`:
- Upsert create/update/skip flows
- Old content retrievability via semantic search
- entity_id metadata search behaviour
- Preservation behaviour (no deletion on update)
- Graceful degradation
- Full end-to-end superseding flow
