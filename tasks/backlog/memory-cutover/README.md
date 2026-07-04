# FEAT-MEM-08 — Guardkit Graphiti → fleet-memory cutover

Cut guardkit's knowledge layer (writes + reads) over from Graphiti to **fleet-memory** (deterministic,
LLM-free Postgres+pgvector), dual-writing during a soak and **proving the reads fire in a real run**.
Unblocks **FEAT-MEM-09** (decommission Graphiti / pull `qwen-graphiti`).

- **Review:** TASK-REV-MEM08 · **Feature ID:** FEAT-MEM-08 · **Gate:** ✅ FEAT-MEM-05 parity PASSED
- **Brief:** [`docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md`](../../../docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md)
- **Guide (diagrams + §4 contracts):** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md)

## Tasks (10 · 8 waves)

| Task | Title | Type | Cx | Wave |
|---|---|---|---|---|
| TASK-MEM08-001 | group_id → fleet-memory identity mapping table | declarative | 4 | 1 |
| TASK-MEM08-002 | fleet_memory_client.py adapter + config | feature | 6 | 2 |
| TASK-MEM08-003 | extend fleet-memory BuildOutcomePayload **[cross-repo]** | declarative | 3 | 2 |
| TASK-MEM08-004 | dual-write repoint (outcome/adr/task-complete) | feature | 7 | 3 |
| TASK-MEM08-005 | dual-write soak audit (published==stored) **⚙️ operator** | operator_handoff | 3 | 4 |
| TASK-MEM08-006 | wire memory_search into GROI readers | feature | 6 | 5 |
| TASK-MEM08-007 | **PROVE a real run reads** (acceptance gate) **⚙️ operator** | operator_handoff | 3 | 6 |
| TASK-MEM08-008 | guardkit memory CLI + deprecate guardkit graphiti | feature | 5 | 6 |
| TASK-MEM08-009 | flip .mcp.json + tool renames + config + docs | feature | 4 | 7 |
| TASK-MEM08-010 | cutover verification + sign-off **⚙️ operator** | operator_handoff | 3 | 8 |

⚙️ = `operator_handoff` (live NATS/Postgres + human observation; AutoBuild skips, verified post-merge).

## Key decisions (resolved 2026-06-28)

1. **Task-outcome payload:** extend fleet-memory `BuildOutcomePayload` with `task_id`/`lessons`/`approach`
   (cross-repo) — `BasePayload` is `extra="ignore"`, so unextended fields would be silently dropped.
2. **Live proof:** split autobuild code from `operator_handoff` proof tasks (soak / prove-reads / sign-off).

## Start

```bash
/feature-build FEAT-MEM-08          # autonomous; pauses at operator gates (W4/W6/W8)
# or task-by-task:
/task-work TASK-MEM08-001           # mapping table first — it drives everything
```

Rollback at every stage: `backend=graphiti` + re-enable `.guardkit/graphiti.yaml` + `guardkit graphiti`
warn+delegate alias. Graphiti stays authoritative until TASK-MEM08-010 sign-off.
