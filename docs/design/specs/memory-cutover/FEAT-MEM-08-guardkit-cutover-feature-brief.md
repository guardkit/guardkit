# FEAT-MEM-08 — Guardkit Graphiti→fleet-memory cutover (feature brief)

**Date:** 2026-06-28
**Status:** Ready for `/feature-plan` (run from this repo, guardkit). Pass this file via `--context`.
**Repo:** guardkit (this is the cutover — repoint guardkit's knowledge reads + writes off Graphiti).
**Part of:** the post-Graphiti memory migration. Authoritative plan:
`fleet-memory/docs/migration/graphiti-cutover-and-decommission-plan.md` (§2 is the spec for this feature).
**Gate:** ✅ **FEAT-MEM-05 parity PASSED** (`fleet-memory/docs/evals/FEAT-MEM-05-parity-eval-2026-06-27.md`):
fleet-memory retrieval scored 2.38 vs Graphiti 1.06 and was ≥ Graphiti on 16/16 probe queries. Cutover unblocked.

## Why now / what this unblocks

fleet-memory (deterministic, LLM-free Postgres+pgvector) is proven at/above parity with Graphiti for
guardkit's reads. This feature moves guardkit's **writes** (task outcomes, decisions, ADRs) and **reads**
(coach-context, feature-plan-context, CLI search) to fleet-memory, and the reads must **demonstrably fire in
real pipeline runs** (the GROI anti-criterion — don't just build a client; wire it in and prove it). Once
guardkit is cut over, FEAT-MEM-09 can pull `qwen-graphiti` (Qwen2.5) from the box.

## `/feature-plan` input

```
/feature-plan "Cut guardkit's knowledge layer over from Graphiti to fleet-memory. WRITES: repoint
/task-complete outcome capture + adr_service + outcome_manager to publish fleet-memory MemoryEpisodeV1
(build_outcome / adr typed payloads) instead of mcp__graphiti__add_memory; dual-write to BOTH Graphiti and
fleet-memory behind a flag during a soak so we can audit published==stored. READS: wire the coach-context and
feature-plan-context builders (the GROI reads) to fleet-memory memory_search(project='guardkit', query, …) and
PROVE a real pipeline run reads from fleet-memory (log evidence). Add an adapter
guardkit/knowledge/fleet_memory_client.py exposing the same shape graphiti_client.py call-sites use, switched
by a config flag, so callers change by swapping the factory not every call. Point .mcp.json's memory server at
python -m fleet_memory.mcp (FLEET_MEMORY_* env) and rename the /task-complete tool calls
mcp__graphiti__add_memory -> mcp__fleet_memory__memory_write_payload, mcp__graphiti__search_* ->
mcp__fleet_memory__memory_search. Fold reads/writes into the existing 'guardkit memory' CLI group (search,
capture-outcome, status); keep 'guardkit graphiti' as a deprecated warn+delegate alias during soak. Produce
the group_id->payload mapping table FIRST — it drives everything. Leave graphiti.yaml enabled:false during soak
for rollback." --context docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md
```

## The one thing to internalise (from the plan §1)

**This is NOT a 1:1 API swap.** Graphiti `search()` returns LLM-extracted **facts/edges**; fleet-memory
`memory_search()` returns **one token-budgeted context block** of source passages. A write-only/audit consumer
migrates trivially; a consumer that reasons over graph edges must accept a flat context block (the parity eval
says it's good enough for guardkit's reads — but keep the token budget generous so the relevant heading lands).

## Proposed waves (plan §2d)

1. **W1 — mapping + adapter (no behaviour change).** The `group_id → (project, payload_type, domain_tags)`
   mapping table (guardkit's 19 system + 9 project groups → fleet-memory identity); `fleet_memory_client.py`
   adapter (`add_episode`→publish/`write_payload`, `search`→`memory_search`) + config; unit tests.
2. **W2 — writes (dual-write soak).** Repoint `/task-complete` (Tier-0 + Tier-1), `outcome_manager`,
   `adr_service` to fleet-memory, **dual-writing to both** behind a flag; audit published==stored.
3. **W3 — reads (GROI).** Wire `memory_search` into the coach-context / feature-plan-context readers and
   **prove a real run reads from fleet-memory** (log evidence). This is the anti-criterion that sank prior
   "reads exist on paper" attempts — it is the acceptance gate for the feature.
4. **W4 — CLI + cleanup.** `guardkit memory search/status`; deprecate `guardkit graphiti` (warn+delegate);
   flip `.mcp.json`; docs/rules update.

## Write-side mapping (plan §2a)

| guardkit write (today) | source | fleet-memory target |
|---|---|---|
| Task outcome → `guardkit__task_outcomes` (free text) | `/task-complete` Tier-0 `mcp__graphiti__add_memory`; Tier-1 `guardkit graphiti capture-outcome`; `outcome_manager.capture_task_outcome` | **`build_outcome`** typed payload (task_id→identifier, status, duration, lessons/approach in body) — recommended over prose for structured retrieval; may need 1–2 extra fields on the type |
| Architectural decision → `guardkit__project_decisions` | `/task-complete` Tier-0; `adr_service` | **`adr`** payload (decision, status, rationale, supersedes) — direct fit |
| ADRs (feature-build) | `cli graphiti seed-adrs`, `adr_service` | **`adr`** payload |
| Docs / feature-specs / context | `cli graphiti add-context` | **reindex** (FEAT-MEM-07 / `guardkit memory harvest`) → `document`/typed — largely already covered by the harvest |
| System seeding (product_knowledge, command_workflows…) | `cli graphiti seed`, `seed-system` | **Candidate to RETIRE, not migrate** — most overlaps the harvested corpus |

> **The `group_id → payload` mapping table is the core design task — produce it first.** guardkit's 19 system
> + 9 project groups collapse onto fleet-memory's (`project`, `payload_type`, `domain_tags`). Most project
> groups → `project="guardkit"` + a payload_type/domain_tag; system groups → a `guardkit_system` project or
> domain_tags.

## Read-side mapping (plan §2b)

| guardkit read (today) | fleet-memory target |
|---|---|
| `cli graphiti search/show/verify/status` | `guardkit memory search` over `memory_search` |
| Coach-context builder, feature-plan-context (the GROI reads) | `memory_search(project="guardkit", query, payload_types, token_budget)` → context block injected into the prompt |
| `graph_stats`/topology | not reproduced (no graph topology) — drop or replace with store counts |

## fleet-memory replacement surface (the contract to call)

- **MCP server:** `python -m fleet_memory.mcp` (stdio). Tools: `memory_search`, `memory_write_payload`,
  `memory_supersede`; resource `memory://projects`. (Present at `fleet-memory/src/fleet_memory/mcp/`.)
- **Write paths:** NATS publish `MemoryEpisodeV1` to `memory.episode.{project_id}.{episode_type}` (prose →
  chunk+embed; JSON → typed payload) via `nats_core.publish_episode` as the `guardkit` NATS user (already
  provisioned, password `GUARDKIT_NATS_PASSWORD` in `nats-infrastructure/.env`); **or** the `memory_write_payload`
  MCP tool; **or** `DeterministicWriter` in-proc.
- **7 typed payloads:** `adr`, `review_report`, `build_outcome`, `pattern`, `warning`, `seed_module`,
  `document`; natural key `type:project:identifier`; `domain_tags` facets; `supersedes` links.
- **Config:** `FLEET_MEMORY_*` env (PG DSN, EMBED_URL/MODEL/DIMS, NATS_URL). **No LLM config.**

## Live integration points this must repoint (verified 2026-06-28)

- `.guardkit/graphiti.yaml` → fleet-memory config; currently **`enabled: true`** (set `false` during soak for rollback).
- `.mcp.json` → still points at the graphiti HTTP server (`promaxgb10-41b1:8004/mcp`); repoint to `python -m fleet_memory.mcp`.
- `guardkit/knowledge/graphiti_client.py` → add the `fleet_memory_client.py` adapter branch behind a flag.
- `/task-complete` outcome capture (Tier-0 `mcp__graphiti__add_memory`, Tier-1 `guardkit graphiti capture-outcome`).
- `guardkit/cli/graphiti.py` command group → `guardkit memory` group (which already has `harvest`).
- `guardkit/planning/coach_context_builder.py` + the feature-plan context reader (the GROI reads).

## Eval result feeding the design (2026-06-28)

Parity **PASS** overall, but note for the read-side: fleet-memory returns the **best source passage**, which is
highly actionable when a dedicated doc exists. Two weak spots to design around: a genuine **corpus gap** on
narrow how-to queries (e.g. "SDK vs subprocess" — neither system answered), and passages can bury the answer in
surrounding prose → **keep the `memory_search` token budget generous** so the relevant heading is included.
Runtime knowledge (task_outcomes, failure_patterns) is **not in the corpus yet** — it arrives via this feature's
W2 writes, so early read quality on outcome-type queries improves *after* the dual-write soak accumulates.

## Prerequisites / state

- ✅ **Corpus baseline is clean** (2026-06-28): re-harvested with the curated taxonomy (docs/reviews
  run-captures excluded) → 125 docs, stream + store rebuilt pristine. The relay runs as a managed container
  (`fleet-memory/deploy/relay/`), embedder Qwen3-Embedding-0.6B/1024.
- The `guardkit` NATS publisher user + the fleet-memory MCP server already exist.

## Risks / open decisions (plan §2e)

- Typed vs prose for task outcomes — **recommend typed `build_outcome`**.
- **Dual-write soak** before cutting reads over (audit every Graphiti write also lands in fleet-memory).
- Seeded system knowledge — **retire what the harvest already covers**, don't migrate.
- Retrieval parity already passed; if the flat context block underperforms for some job, that feeds back to
  **retrieval design**, NOT to unfreezing Graphiti.

## Downstream

FEAT-MEM-08 (this) → **FEAT-MEM-09** decommission (Option B, guardkit-first recommended): soak → freeze
FalkorDB → pull `qwen-graphiti` from the llama-swap preload + `qg` matrix-var → archive. The other 4 Graphiti
consumers (forge/jarvis/specialist-agent/study-tutor) are **soft** and migrate on their own timelines.

## References

- Authoritative plan: `fleet-memory/docs/migration/graphiti-cutover-and-decommission-plan.md` (§2)
- Parity eval: `fleet-memory/docs/evals/FEAT-MEM-05-parity-eval-2026-06-27.md`
- fleet-memory MCP + writers: `fleet-memory/src/fleet_memory/{mcp/,relay/,writer/,reindex/publisher.py}`
- Publisher contract + the guardkit NATS user: `guardkit/docs/design/specs/memory-publisher/P4-harvest-publisher-feature-brief.md`
- Harvest (already in `guardkit memory`): `guardkit/guardkit/memory/`, `guardkit/guardkit/cli/memory.py`
