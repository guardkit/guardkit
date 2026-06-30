# TASK-MEM08-005 — Dual-write soak audit (published == stored)

**Date:** 2026-06-30 · **Branch:** `autobuild/FEAT-MEM-08` · **Operator:** Richard Woollcott

## Outcome: PASS — guardkit writes land in fleet-memory, audited by natural key, DLQ empty.

The soak verifies the **production write path** end-to-end: real `capture_task_outcome`
(the function `guardkit task-complete` calls) and `ADRService.create_adr`, with the
backend selected by the cutover flag, publish typed `MemoryEpisodeV1` episodes that the
running `fleet-memory-relay` ingests into Postgres (`public.store` + `public.store_vectors`).

## What had to be fixed first (the soak's premise was false)

The handoff named 005 as the next step, but the soak could not have passed as-was: the
**fleet-memory write path was a stub** — the exact mirror of the read-path stub that 007
caught (per-task-green-is-not-feature-green). Three defects, all fixed on this branch:

1. **Write stub.** `FleetMemoryClient.add_episode` built a generic dict and
   `logger.info("Would publish…")` — it never called `nats_core.publish_episode`.
   Replaced with a real typed publish:
   - New `guardkit/knowledge/fleet_memory_payloads.py` — `build_memory_episode()` maps
     each `(group_id → GroupMapping)` + the call-site `episode_body` to the correct typed
     `MemoryEpisodeV1` (`content_format="json"`, `payload_type`, JSON `body` matching the
     relay's payload registry). Identifiers are sanitised to fleet-memory's
     `^[a-zA-Z0-9_]+$` rule (`TASK-1234` → `TASK_1234`; a hyphen would be a DLQ poison).
   - `add_episode` now publishes via the proven harvest path
     (`harvest_publisher.publish_episodes`, connect as the `guardkit` NATS user, 900KB
     guard, idempotent by `episode_id`=natural key), fail-open.
2. **ADR mapping gap.** `ADRService.create_adr` writes the literal group_id `"adrs"`,
   which `resolve("adrs")` returned `None` for — so every ADR silently no-op'd. Added
   `"adrs" → adr` to `GROUP_ID_MAP`.
3. **Backend-selection wiring gap (the cutover was inert).** Nothing read
   `.guardkit/graphiti.yaml` `backend: fleet_memory` (009's flip) — `init_memory_client`
   had no production caller, so `_backend` stayed `"graphiti"` and **every** read/write
   routed to the (now-disabled) graphiti client. `007` "passed" only because its harness
   called `init_memory_client` explicitly. Added lazy config-driven selection:
   `get_memory_client()` now auto-inits from `GUARDKIT_MEMORY_BACKEND` → graphiti.yaml
   `backend:` → `"graphiti"`. Verified live: `capture_task_outcome` resolved a
   `FleetMemoryClient (enabled=True)`.

Unit coverage added/updated (75 pass): `test_fleet_memory_payloads.py` (builder + sanitise,
bodies validated against the real fleet-memory models), rewritten
`TestFleetMemoryClientAddEpisode` (asserts the real publish shape — kills the false-green),
`TestBackendAutoInit` (config-driven selection). Full knowledge + planning dirs: 472 passed
(pre-existing `frontmatter`/`jinja2` collection errors in the fleet-memory venv are unrelated).

## Soak evidence

**Mode:** `backend=fleet_memory` (single-write), **not** `dual`.
**Rationale (operator decision):** a genuine dual-write soak requires Graphiti **enabled**,
but FalkorDB (`whitestocks:6379`) is **down** and Graphiti is being decommissioned
(FEAT-MEM-09); reads are already cut to fleet-memory (011). Re-animating a
decommissioning-bound, extraction-broken backend to exercise a leg that no longer matters
was rejected. The soak therefore proves the load-bearing path (guardkit → NATS → relay →
Postgres) directly. Rollback during the window is unaffected (set `backend: graphiti`).

**Driver:** real entry points — `capture_task_outcome` ×3 + `ADRService.create_adr` ×1
(plus one earlier single-publish smoke). Backend resolved live as `FleetMemoryClient`.

**Audit — published == stored (by natural key), all embedded:**

| natural_key | store rows | vector rows |
|---|---|---|
| `build_outcome:guardkit:TASK_MEM08_SMOKE1` | 1 | 1 |
| `build_outcome:guardkit:TASK_MEM08_SOAKA` | 1 | 1 |
| `build_outcome:guardkit:TASK_MEM08_SOAKB` | 1 | 1 |
| `build_outcome:guardkit:TASK_MEM08_SOAKC` | 1 | 1 |
| `adr:guardkit:ADR_SOAK01` | 1 | 1 |

- `public.store` prefix counts: `build_outcome` 1→4 (this session) and an earlier smoke =
  4 distinct; `adr` 0→1. Published (5) == stored (5).
- Store key = `uuid5(NS=6ba7b810-…, natural_key)`; value carries top-level `natural_key`,
  `payload_type`, `project`, `identifier`, `content`. Idempotent upsert by natural key.
- Relay: 4 `Received` = 4 `Processed` (clean ack-after-commit), no `Poison`/`reject` lines.

**AC-005-1 (published == stored):** ✅ 5/5 by natural key.
**AC-005-2 (no silent divergence; DLQ empty):** ✅ `memory.dlq.>` = **0 messages**
(JetStream `stream_info` subjects_filter), no poison rejections logged.
**AC-005-3 (audit recorded):** ✅ this note.

## Read-enrichment (TASK-MEM08-012) — RESOLVED 2026-06-30

The two fleet-memory-side gaps that limited *retrieval* of the new typed records are now
closed; the full write→read round-trip is proven.

1. **`domain_tags` filter mismatch — FIXED (no rebuild).** Retrieval's `_matches_domain_tags`
   read only a top-level `domain_tags`, but `DeterministicWriter` nests it inside `content`,
   so a GROI read for `task_outcomes` (`domain_tags=["task"]`) filtered out every
   build_outcome → 0 hits. Fixed in `../fleet-memory` (`fix(retrieval): domain_tags filter
   reads tags nested in content JSON`, commit `ca3f817`): new `_item_domain_tags` resolves
   tags top-level-first then from the embedded `content` JSON; chunks (prose content) yield
   `[]`. Pure retrieval-side (runs in-process via the editable install) — no relay rebuild.
   18 search-core tests pass.
2. **TASK-MEM08-003 payload extension — already in source; relay REBUILT.**
   `BuildOutcomePayload` already declared `task_id`/`lessons`/`approach` in `../fleet-memory`
   source (committed `e5a134c`, tested `test_payloads.py:349`), but the *running* relay was a
   stale baked image that dropped them (`extra="ignore"`). Rebuilt + redeployed via
   `deploy/relay/docker-compose.yml` (`docker compose up -d --build`, new image
   `4fe44bfb`); `.env.deploy` (ack_wait=1200/max_deliver=5/embed) preserved; corpus intact
   (684 rows, NAS-external); "FastStream app started successfully".

**Round-trip evidence (re-soak, AC-012-1/2/4):** a real `capture_task_outcome`
(`TASK-MEM08-RESOAK1`, `OUT-4DB24CAE`) landed with `task_id`/`lessons`/`approach` in the
stored `content`; a GROI read for `task_outcomes` (`domain_tags=["task"]`) returned it (was
0 pre-fix); and a prose query (`"pomegranate-sentinel …"`) retrieved the embedded `lessons`
text — proving the enrichment fields are embedded and searchable. ADR GROI read
(`adrs` → `adr` + `domain_tags=["decision"]`) also returns its record.

**010 CLI sign-off (unblocked by the requires-python bump, commit `5cca36f8`):**
`uv sync --extra memory --python 3.12` resolves; `guardkit memory status` → REACHABLE
(fleet-memory); `guardkit memory search` returns hits. The `mcp__fleet_memory__memory_search`
MCP-tool check remains a fresh-session step (MCP servers load at session start).

The write path AND read-enrichment are now both complete and proven end-to-end.

## Repro / verify

```bash
cd <repo-root>; set -a; . ./.env; set +a
export GUARDKIT_NATS_PASSWORD=$(grep ^GUARDKIT_NATS_PASSWORD= ../nats-infrastructure/.env | cut -d= -f2-)
export FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory PYTHONPATH="$PWD"
# audit a key:
psql "$FLEET_MEMORY_PG_DSN" -tAc \
  "select count(*) from public.store where prefix='fleet_memory.guardkit.build_outcome' \
   and value->>'natural_key'='build_outcome:guardkit:TASK_MEM08_SOAKA';"   # -> 1
```

Note: the soak records (`*SOAK*`, `*SMOKE*`, `ADR_SOAK01`) are synthetic; delete from the
store if corpus hygiene is preferred.
