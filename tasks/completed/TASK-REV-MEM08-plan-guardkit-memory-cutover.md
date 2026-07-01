---
id: TASK-REV-MEM08
title: "Plan: Cut guardkit's knowledge layer over from Graphiti to fleet-memory"
task_type: review
status: review_complete
priority: high
feature_id: FEAT-MEM-08
created: 2026-06-28
clarification:
  context_a:
    timestamp: 2026-06-28
    decisions:
      focus: all
      tradeoff: quality
  context_b:
    timestamp: 2026-06-28
    decisions:
      approach: dual-write-soak-then-prove-reads
      execution: detect
      testing: standard
      build_outcome_field_gap: extend-fleet-memory-payload-cross-repo
      live_proof_tasking: split-code-autobuilt-proof-operator-handoff
---

# Plan: Guardkit Graphiti → fleet-memory cutover (FEAT-MEM-08)

> Decision review for the guardkit-side cutover. Source brief:
> [`docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md`](../../docs/design/specs/memory-cutover/FEAT-MEM-08-guardkit-cutover-feature-brief.md).
> Authoritative plan: `fleet-memory/docs/migration/graphiti-cutover-and-decommission-plan.md` §2.
> Gate: ✅ FEAT-MEM-05 parity PASSED (fleet-memory 2.38 vs Graphiti 1.06, ≥ on 16/16 probes).

## Decision: IMPLEMENT (4 waves, 10 tasks)

Move guardkit's knowledge **writes** (task outcomes, decisions, ADRs) and **reads**
(coach-context, feature-plan-context, CLI search) off Graphiti onto fleet-memory
(deterministic, LLM-free Postgres+pgvector), dual-writing during a soak, and **prove the
reads fire in a real pipeline run** (the GROI anti-criterion — the acceptance gate).

### Verified integration surface (2026-06-28, both repos read)

| Concern | Verified location |
|---|---|
| Write call-sites | `outcome_manager.capture_task_outcome` → `add_episode(group_id="task_outcomes")`; `adr_service.create_adr` → `add_episode(group_id="adrs")`; `/task-complete` Tier-0 `mcp__graphiti__add_memory`, Tier-1 `guardkit graphiti capture-outcome` (`cli/graphiti.py`) |
| Client factory | `guardkit/knowledge/graphiti_client.py` — `get_graphiti()` / `init_graphiti()`; write `add_episode(name, episode_body, group_id, source, entity_type)`; read `search(query, group_ids, num_results) -> List[Dict{fact,uuid,score}]` |
| group_ids | `guardkit/_group_defs.py` — **9 project + 20 system** groups (brief said 19/9; actual 20/9) |
| GROI reads | `planning/coach_context_builder.py` (→ AutoBuild coach prompt); `knowledge/feature_plan_context.py` (→ /feature-plan). **All readers consume flat `fact` text + score only — never edges/nodes → 100% compatible with fleet-memory's flat context block.** Other readers (context_loader, job_context_retriever, impact_analysis, graphiti_arch) same shape. |
| Evidence hook | `knowledge/query_logger.py` → `.guardkit/graphiti-query-log.jsonl` (logs every search/add_episode) — basis for "prove a real run reads from fleet-memory" |
| fleet-memory contract | MCP `memory_search(project, query, payload_types, domain_tags, token_budget) -> {context_block, coverage_score, contributing_types, tokens_used}`; `memory_write_payload(payload_dict) -> natural_key`; `memory_supersede`. NATS `nats_core.publish_episode(MemoryEpisodeV1)` → `memory.episode.{project}.{type}`, user `guardkit`/`GUARDKIT_NATS_PASSWORD`. Config `FLEET_MEMORY_*` (PG_DSN, EMBED_URL/MODEL/DIMS, NATS_URL). **No LLM config.** |
| Payload gap | `BuildOutcomePayload` = `status` + `duration_seconds` only; `BasePayload` is `extra="ignore"` → extra `task_id`/`lessons`/`approach` **silently dropped**. ADRPayload = `decision` + `status`. |

### Resolved forks (user decisions, 2026-06-28)

1. **Task-outcome payload (extra=ignore gap):** **Extend fleet-memory `BuildOutcomePayload`**
   with optional `task_id`/`lessons`/`approach` — a W1 task in the sibling **fleet-memory** repo.
   Feature declares `evidence_repos: [../fleet-memory]` so the cross-repo write is collected by
   the Coach (see `.claude/rules/evidence-boundary-narrower-than-write-surface.md`).
2. **Live-proof tasking:** **Split** — autobuild code+unit tests (mocked fleet-memory) vs.
   `operator_handoff` live-proof tasks (dual-write soak audit, "prove a real run reads", cutover
   sign-off). The soak/proof ACs are `observed_at_runtime` and cannot be satisfied by the
   Player↔Coach loop.

### Risks / non-goals

- **Not a 1:1 API swap.** Graphiti `search()` returns LLM-extracted facts/edges; `memory_search()`
  returns one token-budgeted context block. Verified all guardkit readers already consume flat text
  → migration is read-shape-compatible. Keep the token budget **generous** (relevant heading must land).
- **Retire, don't migrate, system seeds** the harvest already covers (the mapping task decides which).
- **Rollback:** leave `.guardkit/graphiti.yaml` `enabled: false` during the soak; the dual-write flag
  and `guardkit graphiti` warn+delegate alias keep the old path one flag away.
- Early read quality on outcome-type queries improves **after** the W2 dual-write soak accumulates.

### Downstream

FEAT-MEM-08 (this) unblocks **FEAT-MEM-09** decommission (guardkit-first): soak → freeze FalkorDB →
pull `qwen-graphiti` from llama-swap → archive. See [[graphiti-cutover-qwen25-removal]].

**Feature structure:** `tasks/backlog/memory-cutover/` · YAML `.guardkit/features/FEAT-MEM-08.yaml`
