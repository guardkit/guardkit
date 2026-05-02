# Infra Orchestration

## Problem

The GB10 (`promaxgb10-41b1`) hosts a stack of local infrastructure that supports
jarvis and the wider Forge ecosystem: llama-swap (LLM endpoint multiplexer),
graphiti-mcp (knowledge-graph MCP server), and FalkorDB (graphiti's backing
store). The operator receives regular DGX OS updates that require a host
reboot, but there is no clean, idempotent "stop everything → reboot →
start everything" workflow for these services. Worse, the existing
`graphiti-stack-up.sh` / `graphiti-stack-down.sh` scripts currently error
when invoked, and the `graphiti-mcp` container reports `Up 2 days
(unhealthy)` because its embedding/LLM endpoint config still points at the
pre-migration llama-swap URL.

## Solution

Three-deliverable scope, all bundled under a single task to keep the
diagnostic, the repair, and the orchestration scaffold tightly coupled (the
diagnostic informs the script fixes, and the repaired stack scripts are the
building blocks of the orchestration layer):

1. **Deliverable A** — Diagnose `graphiti-stack-{up,down}.sh` failures and the
   `graphiti-mcp` unhealthy state, and repair the embedding/LLM endpoint
   config to point at the migrated llama-swap on `:9000`
   (`nomic-embed` for embeddings, `qwen-graphiti` for the LLM).
2. **Deliverable B** — Make `graphiti-stack-up.sh` and `graphiti-stack-down.sh`
   idempotent and safe to re-run, with documented preconditions /
   postconditions / exit codes.
3. **Deliverable C** — Scaffold a top-level `scripts/infra-up.sh` /
   `scripts/infra-down.sh` (and optional `infra-status.sh`) orchestration
   layer for the LLM-and-graphiti tier, designed for the DGX-OS-update
   reboot workflow, with explicit (but unimplemented) extension hooks for
   the NATS infrastructure tier and the agents tier.

## Subtasks

| ID | Title | Mode |
|----|-------|------|
| TASK-INFRA-001 | graphiti-mcp diagnostic + repair + infra-orchestration scaffold | task-work |

(Single-task feature; subtasks may be carved out during `/task-work` if the
diagnostic uncovers more scope than expected.)

## Discovery Context

- Discovered 2026-05-01 on GB10 (`promaxgb10-41b1`).
- Surfaced during the FEAT-JARVIS-INTERNAL-001 first-real-run validation,
  Phase 4 (graphiti integration phase) — see jarvis-side runbook
  `docs/runbooks/RESULTS-FEAT-JARVIS-INTERNAL-001-first-real-run.md` for the
  observation row.
- Correlation ID of the run that surfaced the issue:
  `a58ec9a7-27c6-485a-beac-e18675639a10`.

## Out of Scope

- NATS infrastructure orchestration (separate future task; scaffold leaves a
  hook).
- Specialist-agent / jarvis container orchestration (separate future task;
  scaffold leaves a hook).
- Any change to llama-swap itself — it is already managed by systemd timers
  and is working. This task only consumes its `:9000` endpoint.
