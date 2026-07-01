---
id: TASK-MEM08-012
title: "Read-enrichment: domain_tags filter fix + BuildOutcomePayload 003 + relay rebuild"
task_type: feature
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 5
implementation_mode: task-work
complexity: 5
target_repo: fleet-memory  # + guardkit (retrieval is in-process via editable fleet_memory)
depends_on:
  - TASK-MEM08-005
---

# TASK-MEM08-012 — Read-enrichment for typed records

> **Why this exists.** TASK-MEM08-005 made guardkit's **write** path real and proven (typed
> `build_outcome`/`adr` records land in `public.store`, audited by natural key, DLQ empty).
> But **reads** of those typed records return 0 hits. This task closes that so the cutover
> delivers its purpose: retrievable task-outcome lessons / ADRs. It is intentionally split
> from the write path because it requires a **relay image rebuild** (operational risk to the
> hard-won `fleet-memory-relay`, see FEAT-HARV ack_wait recovery).

## Problem (two independent gaps)

1. **`domain_tags` filter mismatch (no rebuild needed).** `fleet_memory.retrieval`
   `_matches_domain_tags` reads a **top-level** `domain_tags`, but `DeterministicWriter`
   only nests `domain_tags` inside the embedded `content` JSON. guardkit's GROI read for
   `task_outcomes` resolves to `payload_type=build_outcome` + `domain_tags=["task"]`
   (`fleet_memory_mapping`), so the tag filter deselects every build_outcome → 0 hits.
   Retrieval runs **in-process** via the editable `../fleet-memory`, so this is fixable
   without a relay rebuild. Options (pick one, with a test):
   - retrieval reads `domain_tags` from the `content` JSON (most faithful), or
   - writer also stores top-level `domain_tags` (needs rebuild), or
   - guardkit GROI sends `domain_tags=[]` for migrated groups (least precise).
2. **TASK-MEM08-003 payload extension (needs relay rebuild).** `BuildOutcomePayload` is
   still `status` + `duration_seconds`; `extra="ignore"` drops the `task_id`/`lessons`/
   `approach` guardkit already publishes (forward-compat). Add them as optional fields in
   `../fleet-memory/src/fleet_memory/payloads/models.py`, ensure they participate in the
   embedded content, **rebuild + redeploy** the `fleet-memory-relay` image.

## Acceptance criteria

- **AC-012-1**: After the fix, a GROI read for `task_outcomes` (and `adrs`) returns the
  matching typed records written by the soak (no longer 0), verified against the live store.
- **AC-012-2**: `BuildOutcomePayload` accepts/stores `task_id`/`lessons`/`approach`
  (back-compatible); a build_outcome written with `lessons="…"` is retrievable by a query
  matching that prose. fleet-memory's own payload tests cover the new fields.
- **AC-012-3**: Relay image rebuilt + redeployed without regressing the existing harvest
  corpus (679 chunks) or the ack_wait/max_deliver tuning; DLQ stays empty.
- **AC-012-4**: Re-soak proves write→read round-trip for build_outcome + adr (extends the
  TASK-MEM08-005 audit note).

## Notes

- Soak records from 005 (`*SOAK*`/`*SMOKE*`/`ADR_SOAK01`) can be reused as read fixtures or
  cleaned first.
- Relay is a **baked image** (`fleet_memory` 0.1.0, `faststream run fleet_memory.app:app`,
  no bind-mount) — confirm the build/redeploy procedure before touching it.
- See `docs/design/specs/memory-cutover/TASK-MEM08-005-dual-write-soak-audit.md` §"Known
  follow-up" for the full diagnosis + file:line references.
