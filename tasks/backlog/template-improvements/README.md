# Feature: DeepAgents Template Improvements

## Problem Statement

After 11 runs and 31 fixes across the agentic-dataset-factory pipeline, analysis shows that 84% of fixes (26/31) could have been prevented by better template scaffolding. The fixes cluster into 6 root cause categories: validation/schema gaps (29%), prompt engineering (23%), SDK/framework misunderstanding (19%), orchestration logic (13%), model-specific quirks (10%), and test/observability gaps (6%).

## Solution Approach

Two-template strategy — the distinction is the **evaluation model**, not complexity:

1. **`langchain-deepagents`** (base template) — Production-grade adversarial cooperation (Orchestrator + Player + Coach) with binary accept/reject evaluation against fixed criteria. Enhanced with JsonExtractor, observability, factory guards, domain validator, and pre-flight validation. Works for **verifiable domains** (code generation, data synthesis, schema conformance). Currently running in production (agentic-dataset-factory).
2. **`langchain-deepagents-weighted-evaluation`** (extends base) — Adds configurable weighted multi-criteria evaluation via GOAL.md quality contracts. Makes **subjective quality gradable** — the Anthropic insight applied to creative content. Adds: Pydantic CoachVerdict with per-criterion scoring, GOAL.md parser, configurable intensity (full/light/solo), HITL checkpoint hooks, sprint contract negotiation.

## Priority

- **P0 (Wave 1)**: Top 3 improvements — JsonExtractor + Prompt template + Gated writes (**COMPLETED**)
- **P1 (Wave 2)**: Factory allowlisting + Validators + Observability + Model docs (**COMPLETED**)
- **P2 (Wave 3)**: Pre-flight validation script (`guardkit validate`) (**IN PROGRESS**: TI-008)
- **P0-FIX (Wave 3.5)**: SDK alignment fixes from TASK-REV-32D2 — align template with proven agentic-dataset-factory patterns (**NEW — GATES Wave 4**)
- **P3 (Wave 4)**: Adversarial template scaffold and components

## Subtask Summary

| ID | Title | Wave | Method | Priority | Status |
|----|-------|------|--------|----------|--------|
| TASK-TI-001 | JsonExtractor class | 1 | task-work | P0 | COMPLETED |
| TASK-TI-002 | Prompt engineering template | 1 | task-work | P0 | COMPLETED |
| TASK-TI-003 | Orchestrator-gated writes scaffold | 1 | task-work | P0 | COMPLETED |
| TASK-TI-004 | Factory tool allowlisting | 2 | task-work | P1 | COMPLETED |
| TASK-TI-005 | Type-aware domain validator | 2 | task-work | P1 | COMPLETED |
| TASK-TI-006 | Observability logging scaffold | 2 | direct | P1 | COMPLETED |
| TASK-TI-007 | Model compatibility matrix | 2 | direct | P1 | COMPLETED |
| TASK-TI-008 | Pre-flight validation script | 3 | task-work | P2 | IN PROGRESS |
| **TASK-TI-020** | **Fix factory_guards.py — memory via MemoryMiddleware** | **3.5** | **task-work** | **P0-FIX** | **BACKLOG** |
| **TASK-TI-019** | **Fix player.py.template — create_agent()** | **3.5** | **task-work** | **P0-FIX** | **BACKLOG** |
| **TASK-TI-021** | **Fix coach.py.template — create_agent()** | **3.5** | **task-work** | **P0-FIX** | **BACKLOG** |
| **TASK-TI-022** | **Fix agent.py.template — align entrypoint** | **3.5** | **task-work** | **P0-FIX** | **BACKLOG** |
| **TASK-TI-023** | **Document ainvoke() contract** | **3.5** | **direct** | **P1** | **BACKLOG** |
| **TASK-TI-024** | **Populate stub pattern rules** | **3.5** | **task-work** | **P2** | **BACKLOG** |
| TASK-TI-009 | Weighted-evaluation template scaffold | 4 | task-work | P3 | BACKLOG |
| TASK-TI-010 | Three-role orchestrator scaffold | 4 | task-work | P3 | BACKLOG |
| TASK-TI-011 | Canonical pipeline module | 4 | task-work | P3 | BACKLOG |
| TASK-TI-012 | Domain configuration schema + GOAL.md parser | 4 | task-work | P3 | BACKLOG |
| TASK-TI-013 | Weighted Coach prompt template | 4 | task-work | P3 | BACKLOG |
| TASK-TI-014 | Configurable adversarial intensity | 4 | task-work | P3 | BACKLOG |
| TASK-TI-015 | HITL checkpoint hooks | 4 | task-work | P3 | BACKLOG |
| TASK-TI-016 | Sprint contract negotiation | 4 | task-work | P3 | BACKLOG |
| **TASK-TI-025** | **Register weighted-evaluation template in installer** | **4** | **task-work** | **P1** | **BACKLOG** |
| **TASK-TI-026** | **Document two-template architecture** | **4** | **direct** | **P1** | **BACKLOG** |
| **TASK-TI-027** | **Implement template extends mechanism** | **4** | **task-work** | **P1** | **BACKLOG** |

## Wave 3.5 — SDK Alignment Fixes (TASK-REV-32D2)

These tasks align the base template with the proven `agentic-dataset-factory` production code. They MUST complete before Wave 4 begins.

**Execution order** (dependency chain):

```
Parallel group 1 (all independent — use Conductor):
  TI-020  (factory_guards memory fix)
  TI-019  (player factory — calls create_agent() directly, not via factory_guards)
  TI-021  (coach factory — calls create_agent() directly, not via factory_guards)
  TI-023  (ainvoke contract docs)

Sequential after group 1:
  TI-022  (entrypoint — needs player + coach factories done)
  TI-024  (stub pattern rules — needs all factories settled)
```

**Parallel execution**: TI-020 + TI-019 + TI-021 + TI-023 all in parallel, then TI-022, then TI-024.

**Why no dependency between TI-019/TI-021 and TI-020**: The player and coach factories adopt the proven `agentic-dataset-factory` pattern — they call `create_agent()` directly with their own `MemoryMiddleware`, not via `create_restricted_agent()`. TI-020 fixes the shared utility independently.

**Source**: All fixes proven in production — `agentic-dataset-factory` currently executing 26-hour run using these patterns.

## Provenance

- **Parent Review**: TASK-REV-TRF12
- **Design Review**: TASK-REV-32D2 (SDK-validated, exemplar cross-referenced)
- **Feature ID**: FEAT-TI
- **Review Report**: `.claude/reviews/TASK-REV-TRF12-review-report.md`, `.claude/reviews/TASK-REV-32D2-review-report.md`
