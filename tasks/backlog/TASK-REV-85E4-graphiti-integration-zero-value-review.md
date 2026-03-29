---
id: TASK-REV-85E4
title: "Graphiti Integration Review - Zero Value Delivery Despite Working Infrastructure"
status: review_complete
review_mode: architectural
review_depth: comprehensive
review_results:
  score: 45
  findings_count: 5
  recommendations_count: 11
  decision: implement
  implementation_feature: FEAT-GMR
  subtasks_created: 10
  subtasks_path: tasks/backlog/graphiti-mcp-restoration/
  report_path: .claude/reviews/TASK-REV-85E4-review-report.md
  completed_at: 2026-03-29T11:00:00Z
created: 2026-03-29T10:30:00Z
updated: 2026-03-29T10:30:00Z
priority: high
tags: [graphiti, knowledge-graph, architecture, integration, review]
task_type: review
complexity: 7
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Review: Graphiti Integration - Zero Value Delivery Despite Working Infrastructure

## Problem Statement

Graphiti knowledge graph infrastructure is fully operational (FalkorDB, vLLM endpoints, embedding service, Python client, seeded data) but delivers **zero practical value** in the core GuardKit workflow. The integration that was built to solve the "letterbox problem" (LLMs lacking big-picture architectural context) is entirely bypassed through universal graceful degradation patterns.

### The Letterbox Problem (Why Graphiti Exists)

Historical AutoBuild and task reviews show a recurring pattern:
- Fixes that contradict the intended architecture
- Changes that undo work from previous fixes
- Implementations that go down rabbit holes due to lack of big-picture context
- The LLM's narrow context window means it can't see the full project picture

Graphiti was built to solve this by providing:
- Past architectural decisions and their rationale
- Previous task outcomes and lessons learned
- Big-picture system architecture context
- Pattern of what works and what doesn't in this project

**None of this is currently being delivered to the workflows that need it.**

### Root Cause Hypothesis

Every command integration follows the same pattern:
```
IF graphiti_available → try to load context
IF unavailable OR error → set context = None → PROCEED UNCHANGED
```

This means the workflow with Graphiti is **functionally identical** to the workflow without it. The "graceful degradation" is so graceful it's indistinguishable from absence.

## Scope of Review

### 1. Command Integration Audit

Audit each core workflow command for Graphiti integration depth:

| Command | Current Integration | Expected Value |
|---------|-------------------|----------------|
| `/task-work` | Phase 1.7 context loading (no-op if empty) | Past decisions, similar task outcomes, architecture context should inform Phase 2 planning |
| `/task-review` | None | Past review findings, architectural patterns should inform review criteria |
| `/task-create` | None | Similar past tasks, complexity patterns from history |
| `/task-complete` | None | Should capture task outcomes, lessons learned for future reference |
| `/feature-plan` | Optional enrichment + post-gen seeding | Similar features, past failures should shape planning |
| `/feature-spec` | None | Past specifications, domain patterns |
| `/feature-build` | None | Turn history, past build failures |
| `/system-overview` | Tier 1 check only | Should BE the source of architectural truth |
| `/system-plan` | Post-gen seeding only | Past decisions should inform new plans |
| `/impact-analysis` | Tier 1 check only | Past impacts, ripple effects from history |

### 2. AutoBuild Integration Audit (Confirmed Working — Reference Implementation)

AutoBuild (Player-Coach workflow) has **confirmed working Graphiti integration** based on debug output from multiple successful runs across projects. This is the reference implementation for fixing everything else.

#### Evidence from Debug Logs

Multiple successful runs in `docs/reviews/` confirm real context loading:

- **`docs/reviews/agentic-dataset-factory/feature-FEAT-5606-run-2-success.md`**: Shows `[Graphiti] Loading Player context (turn 1)...` → embedding requests to `promaxgb10-41b1:8001/v1/embeddings` → `[Graphiti] Context loaded in 0.8s` → `[Graphiti] Player context: 5 categories, 2337/5200 tokens`
- **`docs/reviews/agentic-dataset-factory/feature-FEAT-FBBC-success.md`**, **`feature-FEAT-5AC9-success.md`**, **`feature-FEAT-945D-success.md`**, **`feature-F59D-success.md`**: Additional successful runs with context loading
- **`docs/reviews/autobuild-fixes/run_1_analysis.md`**: Documents F3 failure mode (FalkorDB asyncio event loop corruption under parallel load) — proving context loading is real enough to fail under stress
- **`docs/reviews/failing-graphiti/run-1.md`**: Shows failure modes when Graphiti max_tokens limits are exceeded — again proving real queries are happening
- **`docs/reviews/gb10_local_autobuild/`**: 12 additional runs showing local AutoBuild execution with Graphiti

#### Architecture to Trace (C4 Level)

The working architecture follows this chain — trace it fully during review:

```
FeatureOrchestrator
  → Graphiti factory pre-init (TCP check to FalkorDB at whitestocks:6379)
  → Per-thread GraphitiClient creation (lazy init on consumer's event loop)
  → FalkorDB workarounds applied (PR #1170, issue #1272)
  │
  └─ AutoBuildOrchestrator (per task, in thread)
       → AutoBuildContextLoader (guardkit/knowledge/autobuild_context_loader.py)
         → JobContextRetriever (guardkit/knowledge/job_context_retriever.py)
           → GraphitiClient.search() with embeddings via vLLM
           → Results scored, categorized, token-budgeted
         → Formatted prompt_text injected into Player/Coach SDK invocation
```

Key files to audit:
- `guardkit/knowledge/autobuild_context_loader.py` — `get_player_context()`, `get_coach_context()`
- `guardkit/knowledge/job_context_retriever.py` — `retrieve()` method, category logic
- `guardkit/orchestrator/autobuild.py` — factory storage, per-thread loader creation
- `guardkit/orchestrator/feature_orchestrator.py` — Graphiti factory pre-init, TCP pre-flight
- `guardkit/knowledge/graphiti_client.py` — `search()` method, connection management
- `guardkit/knowledge/falkordb_workaround.py` — upstream bug workarounds

#### Review Checklist

- **Verify**: Confirm context is genuinely fetched AND injected into prompts (not just loaded and discarded)
- **Assess quality**: Are the 5 categories returned by `get_player_context()` actually useful? Do they influence Player implementation decisions or Coach review criteria?
- **Trace the prompt injection**: Where does `result.prompt_text` end up? Is it prepended to the Player's task-work prompt? Does the Player actually read/use it?
- **Compare with commands**: What does AutoBuild do differently from `/task-work`, `/feature-plan` etc. that makes its integration actually work? (Hypothesis: AutoBuild has a dedicated `AutoBuildContextLoader` while commands use ad-hoc context loading that degrades to nothing)
- **Token budgeting**: How does the 5200-token budget work? Is it effective or wasteful?
- **Parallel execution issues**: Document the FalkorDB asyncio event loop corruption (F3) and whether current workarounds resolve it
- **Turn continuation**: How does `turn_state_operations.load_turn_continuation_context()` work for cross-turn learning? Does it actually use local files (TASK-RFX-5FED optimization) or still hit Graphiti?
- **Identify replicable patterns**: Can the `AutoBuildContextLoader` pattern be generalized for core commands? What's the minimum viable adaptation?

If AutoBuild's integration genuinely delivers value (context influences outcomes), it becomes the template for fixing everything else. If it loads context but doesn't measurably improve outcomes, that's a different problem to solve.

### 3. Agent Integration Audit

No agents currently query Graphiti. Assess which agents should:
- `code-reviewer` — should know past architectural violations
- `architectural-reviewer` — should know intended architecture
- `software-architect` — should know ADRs and design rationale
- `autobuild-coach` — should know past task failure patterns
- `autobuild-player` — should have big-picture context

### 4. Stub Detection

Identify functions that claim Graphiti integration but are stubs:
- Empty context loaders
- Functions that return `{}` or `None` on any error
- "Integration points" that never actually query the graph
- Seeding functions that generate commands but don't execute them

### 5. Data Quality Assessment

Evaluate what's actually in the knowledge graph:
- Is the seeded data useful and queryable?
- Are search results actionable (not just generic facts)?
- Is the data structured for the queries workflows need?
- Are group_ids properly partitioned?

### 6. Write Path Assessment

Evaluate what should be automatically captured:
- Task completion outcomes (what worked, what didn't)
- Architectural decisions made during reviews
- Build failures and their root causes
- Pattern discoveries during implementation

## Acceptance Criteria

- [ ] AC-1: Complete audit of all 10+ core commands with Graphiti integration status (real vs stub vs absent)
- [ ] AC-2: Audit AutoBuild integration — trace the full architecture from `FeatureOrchestrator` → `AutoBuildContextLoader` → `JobContextRetriever` → `GraphitiClient`, verify context is injected into Player/Coach prompts (not just loaded), assess whether the 5-category token-budgeted context actually influences outcomes, and document the parallel execution failure modes (FalkorDB asyncio F3)
- [ ] AC-3: Identify all stub functions in the Graphiti integration layer with file locations and line numbers
- [ ] AC-4: Assess data quality — run representative searches and evaluate whether results would actually help planning
- [ ] AC-5: Map the "read path" — what queries each command SHOULD make and what decisions those results should influence
- [ ] AC-6: Map the "write path" — what events SHOULD automatically capture knowledge (task completion, review findings, build outcomes)
- [ ] AC-7: Identify the minimum viable integration — which 2-3 commands would deliver the most value if Graphiti actually worked
- [ ] AC-8: Produce prioritized recommendations with estimated complexity for making Graphiti deliver real value
- [ ] AC-9: Assess whether the current graph schema/seeded data supports the queries workflows actually need
- [ ] AC-10: Document AutoBuild as the reference pattern — produce a concrete adaptation guide showing how `AutoBuildContextLoader`'s architecture (factory pre-init → per-thread client → `JobContextRetriever` → token-budgeted categories → prompt injection) can be replicated for core commands, with specific recommendations for `/task-work` and `/feature-plan` as first targets
- [ ] AC-11: Cross-reference AutoBuild debug logs across `docs/reviews/agentic-dataset-factory/`, `docs/reviews/gb10_local_autobuild/`, `docs/reviews/autobuild-fixes/`, and `docs/reviews/failing-graphiti/` to build a complete picture of when context loading succeeds vs fails, and what conditions cause degradation

## Context

### What Works
- FalkorDB running on whitestocks:6379 (survived power cut)
- vLLM LLM endpoint on promaxgb10-41b1:8000 (Qwen2.5-14B)
- vLLM embedding endpoint on promaxgb10-41b1:8001 (nomic-embed-text-v1.5)
- GraphitiClient connects, searches, returns scored results
- Knowledge graph has seeded data (product_knowledge, architecture_decisions, project groups)
- **AutoBuild context loading is confirmed working** — debug logs show real embedding requests, 0.8s load times, 5 categories with 2337/5200 token budgets injected into Player prompts across multiple successful feature builds (FEAT-5606, FEAT-FBBC, FEAT-5AC9, FEAT-945D, F59D)
- AutoBuild architecture: `FeatureOrchestrator` → factory pre-init → per-thread `AutoBuildContextLoader` → `JobContextRetriever` → `GraphitiClient.search()` → token-budgeted prompt injection

### What Doesn't Work
- No command actually uses Graphiti results to change its behaviour
- Phase 1.7 in task-work loads context that goes nowhere
- All integrations gracefully degrade to "do nothing"
- No automatic knowledge capture from task outcomes
- No agents query the graph
- Stubs throughout the integration layer

### Historical Context
- Weeks of effort on FalkorDB setup, vLLM integration, workarounds for upstream bugs
- Multiple tasks completed for Graphiti client, seeding, MCP server
- The infrastructure works — the application-level integration does not
- Reviews of AutoBuild show the exact "letterbox problem" Graphiti was meant to solve

## Review Modes Suggested

- **Architectural Review**: How should Graphiti integrate into the command pipeline?
- **Code Audit**: Find all stubs and no-op integrations
- **Data Quality Review**: Is the graph data useful for the queries we need?

## Implementation Notes

This review should produce a clear roadmap for making Graphiti deliver on its promise:
1. Which commands get value first (likely `/task-work` and `/feature-plan`)
2. What the read path looks like (specific queries → specific planning decisions)
3. What the write path looks like (specific events → specific knowledge capture)
4. What stubs need real implementation vs what should be removed
5. Whether the current graph schema needs restructuring
