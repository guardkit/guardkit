# FEAT-MEM-09 §3.3 W1 — read-consumer settle

Settle + prove the fleet-memory read-enrichment consumers, per the **operator-confirmed** Fork A/B
decisions (2026-07-03). This is the only substantive code work remaining in FEAT-MEM-09 §3.3 — everything
else (delete graphiti impl, factory simplification, docs/rules) is already done (WS-2c + this session).

- **Scope doc:** [`docs/design/specs/memory-cutover/FEAT-MEM-09-3.3-code-scoping-2026-07-03.md`](../../../docs/design/specs/memory-cutover/FEAT-MEM-09-3.3-code-scoping-2026-07-03.md)
- **Shared contract (READ FIRST):** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md)
- **Fork A = Hybrid/repoint** (keep high-value autobuild read-enrichment; drop dead vestiges).
  **Fork B = follows A** (keep `turn_states` as cross-turn context). C & D already resolved by WS-2c.

## Tasks (5)

| Task | Module | Type | Cx | What |
|---|---|---|---:|---|
| TASK-MEM09-CTXLOAD | `knowledge/context_loader.py` | refactor | 5 | Settle the `_load_*` group_id reads; boundary + live tests replace mocked-shim tests |
| TASK-MEM09-JOBCTX | `knowledge/job_context_retriever.py` (+ `autobuild_context_loader.py` delegation) | refactor | 6 | Settle GROI per-category + turn_states reads; split migrate/retire `search()` calls; boundary + live tests |
| TASK-MEM09-FPCTX | `knowledge/feature_plan_context.py` | refactor | 4 | Strip the RETIRE-group reads (keep `feature_specs`/`task_outcomes`); boundary + live tests |
| TASK-MEM09-TURNSTATE | `knowledge/turn_state_operations.py` | refactor | 5 | Verify `turn_states`→`document[turn,state]` capture/load round-trip (Fork B keep); boundary + live tests |
| TASK-MEM09-MODEDET | `planning/mode_detector.py` | refactor | 2 | Remove the dead/ignored `graphiti_client` param + update callers (pure cleanup; no memory read) |

**Waveable:** CTXLOAD, JOBCTX, FPCTX, TURNSTATE, MODEDET are independent (different modules) → one wave, parallelisable.
MODEDET is trivial and could be done first as a warm-up.

## Not tasks here (already settled — LEAVE)

- `outcome_manager.py` / `outcome_queries.py` (`build_outcome`), `failed_approach_manager.py` (`warning`),
  `adr_service.py`/`adr.py` — already on fleet-memory (migrate groups, repointed in FEAT-MEM-08). No W1 work
  beyond what their own tests already cover.
- `/system-plan` and the arch commands — retain fleet-memory access at the **command-spec** level
  (`system-plan.md` calls `memory_search`/`memory_write_payload`); their Python modules are markdown pipelines.
- The instrumentation telemetry enums (`GraphitiQueryType`, `"digest+graphiti"`) — LEAVE (renaming breaks
  stored-telemetry continuity).

## The one thing that makes these autobuild-ready

The **live-store round-trip cannot run in autobuild** (the worktree's store is `DISABLED`). So each task bakes
in TWO tests (see the guide §3): a **boundary test** (real shim+mapping, external MCP edge stubbed — runs in
autobuild, proves the real seam) and a **`@pytest.mark.live` round-trip** (skips in autobuild, run by the
operator with the store enabled — the FEAT-MEM-08 `operator_handoff` split). The autobuild Coach approves on
the boundary test; the operator signs off the live proof post-merge.

## Start

```bash
# per task (recommended — each is tightly scoped):
guardkit autobuild task TASK-MEM09-MODEDET      # warm-up (trivial cleanup)
guardkit autobuild task TASK-MEM09-CTXLOAD
# ... etc.
```

> Not filed as a formal `.guardkit/features/FEAT-MEM-09.yaml` (FEAT-MEM-08/09 were never filed as feature
> YAMLs — see `[[graphiti-cutover-qwen25-removal]]`). Run task-by-task, or `/feature-plan` this folder first
> if you want `guardkit autobuild feature` orchestration.
