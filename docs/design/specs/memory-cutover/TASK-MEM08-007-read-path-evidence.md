# TASK-MEM08-007 — GROI read-proof evidence: ❌ FAIL (fleet-memory reads are stubbed)

**Date:** 2026-06-29
**Gate:** TASK-MEM08-007 (prove a real run reads from fleet-memory — feature acceptance gate)
**Result:** ❌ **FAIL** (initial run) → ✅ **RESOLVED** by TASK-MEM08-011 (commit `422d8b1e`).
See the Resolution section at the bottom. The W4 live flip (009) / sign-off (010) /
FEAT-MEM-09 decommission were correctly blocked until reads were made real.

## What was verified GOOD (connection layer is solid)
- Embedder: live alias `embed` (Qwen3-Embedding-0.6B) returns **1024** dims; `.mcp.json` +
  `graphiti.yaml` corrected 768→1024 (commits `5a0423d2`).
- Store: `whitestocks.tailebf801.ts.net:5433/fleet_memory` reachable; `store_vectors.embedding
  :: vector(1024)`; **679 corpus rows** (all under one namespace `fleet_memory.guardkit.chunk`
  — harvested docs only; no `build_outcome`/`feature_spec`/`warning` payloads yet).
- Config wiring: `backend=fleet_memory` + `.env` env-indirection loads correctly
  (`embed`/`1024`/NAS DSN). Secrets out of git (commit `bf8fb7c4`).

## Findings — read path defects (all in `guardkit/knowledge/fleet_memory_client.py`)
1. **`FleetMemoryClient.search()` is a STUB.** It hardcodes `context_block = ""` and returns
   `[]` unconditionally — it never calls `memory_search` / queries the store. Verbatim:
   *"For now, return empty list to gracefully degrade … In real implementation, would use
   MCP client to call the tool."* Every GROI query therefore returns `result_count = 0`,
   violating **AC-007-1** (`result_count > 0`). This is an `anti-stub.md` violation (a
   `return []` primary deliverable) and the "reads exist on paper" failure this gate targets.
2. **`FleetMemoryClient` is missing the consumer interface.** No `enabled` property, no
   `initialize()` / `health_check()` / `close()` — but `FeaturePlanContextBuilder.build_context`
   (`feature_plan_context.py:384`, `self.graphiti_client.enabled`) and `guardkit memory
   status`/`search` all call them. **Runtime evidence:**
   `AttributeError: 'FleetMemoryClient' object has no attribute 'enabled'` — the reader crashes
   before reaching search. (The `enabled` property at line 80 belongs to `DualWriteClient`.)
3. **`_check_mcp_available()` checks `import nats_core`** — the *write* dependency — not the
   read `memory_search` MCP tool. The availability gate is wrong for reads.
4. **`_load_fleet_config_from_env` defaults are `nomic-embed` / `768` / `localhost:5433`** —
   all wrong for the live 1024 NAS corpus; silently mis-embeds when env is unset.

## How this passed the per-task gates
TASK-MEM08-002 (adapter) and TASK-MEM08-006 ("wire memory_search into GROI readers") were
approved by the per-task Coach. Their unit tests pass against **mocked** clients (which supply
`.enabled` and a fake `search`), so the stub + interface gap never surfaced — a textbook
`per-task-green-is-not-feature-green` (mocked primary seam = absent integration evidence).

## Remediation
**TASK-MEM08-011** (filed): implement real fleet-memory reads + the missing interface +
fix the availability check and config defaults; then re-run this gate.

## Scope note — the MCP-tool surface is separate
The fleet-memory MCP server (`mcp__fleet_memory__memory_search`, exposed via `.mcp.json`) is a
*different* read surface that Claude Code agents call directly; it may function independently of
this defect. The failure here is specifically the **Python adapter** path used by the automated
GROI readers (`feature_plan_context`, `coach_context_builder`) and the `guardkit memory` CLI.

---

## Resolution — ✅ PASS (TASK-MEM08-011, commit `422d8b1e`, 2026-06-29)

`FleetMemoryClient` now reads for real, reusing `fleet_memory.retrieval.search` +
`assemble_context` (the exact functions the `memory_search` MCP tool wraps — single
source of truth, no drift). Added the consumer interface (`enabled`, `initialize`,
`health_check`, `close`), fixed the availability check (imports `fleet_memory.retrieval`,
not `nats_core`), and corrected the env defaults to `embed`/`1024`. fleet-memory is now an
editable sibling in guardkit's `memory` extra (requires Python ≥3.12).

**Live verification (3.12, NAS store, 679-row corpus):**
- `build_context()` (the real `/feature-plan` reader) → `graphiti-query-log.jsonl`:
  8 entries, `source=fleet_memory_client`, `result_counts=[0,1,0,1,1,1,0,0]` →
  **`result_count > 0` (AC-007-1 ✓)**; a real 266-char context block injected (AC-007-2 ✓).
- Broad `search()` (the `guardkit memory search` path) → 1 hit, score **0.901**, real
  corpus content (an ADR on llama-swap embeddings) (AC-007-3 ✓).
- `initialize()=True`, `health_check()=True`, `enabled=True` (interface ✓).
- Unit suite: 47 passed (real-path coverage; fakes so 3.11 CI passes without the dep).

**Differential note (expected):** queries whose `group_ids` map to payload types absent
from the corpus (`task_outcomes`→`build_outcome`, `feature_specs`→`document`,
`failure_patterns`→`warning`) return 0 — those payloads arrive with the 005 dual-write
soak. Queries with no/unmapped payload filter hit the 679 harvested `chunk` docs and
return content. Reads are functional; richer GROI enrichment grows as the soak populates
the mapped payload types.

**Gate status:** TASK-MEM08-007 now PASSES. Next: 005 soak → merge → 010 sign-off →
FEAT-MEM-09.
