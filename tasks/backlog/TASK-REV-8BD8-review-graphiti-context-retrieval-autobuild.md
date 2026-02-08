---
id: TASK-REV-8BD8
title: Review Graphiti job-specific context retrieval in FEAT-D4CE autobuild output
status: review_complete
task_type: review
review_results:
  score: n/a
  findings_count: 6
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-8BD8-review-report.md
  completed_at: 2026-02-08T16:00:00Z
created: 2026-02-08T14:00:00Z
updated: 2026-02-08T16:00:00Z
priority: high
tags: [graphiti, context-retrieval, autobuild, review, observability]
complexity: 5
---

# Task: Review Graphiti Job-Specific Context Retrieval in FEAT-D4CE AutoBuild Output

## Description

Analyse the FEAT-D4CE autobuild success run output to determine whether job-specific context retrieval using Graphiti is visibly working during autobuild feature orchestration. The `enable_context=True` flag is present in all AutoBuildOrchestrator initializations, but initial grep shows **zero evidence** of Graphiti context retrieval in the run output.

## Review Scope

### Primary Questions

1. **Is Graphiti context retrieval actually executing during autobuild?**
   - `enable_context=True` is set in all orchestrator inits
   - But is the `AutoBuildContextLoader` actually instantiated and passed?
   - Is there a Neo4j/Graphiti connection available during the run?

2. **Why is there no visible output from context retrieval?**
   - Is it silently failing (graceful degradation)?
   - Is the `_context_loader` parameter `None` despite `enable_context=True`?
   - Are there missing log statements for context retrieval operations?

3. **What would working context retrieval look like in the output?**
   - What log messages should appear?
   - What `## Job-Specific Context` prompt sections should be visible?
   - How would we distinguish "no context found" from "retrieval not attempted"?

4. **Is there an observability gap?**
   - Should context retrieval success/failure be logged at INFO level?
   - Should retrieved context categories/counts appear in the progress display?
   - Should the final summary include context retrieval statistics?

### Files to Analyse

- **Run output**: `docs/reviews/ux_design_mode/success_run.md` (the FEAT-D4CE autobuild log)
- **Orchestrator**: `guardkit/orchestrator/autobuild.py` (lines ~2550-2730 for Player/Coach context injection)
- **Context loader**: `guardkit/knowledge/autobuild_context_loader.py`
- **Job context retriever**: `guardkit/knowledge/job_context_retriever.py`
- **Feature orchestrator**: `guardkit/orchestrator/feature_orchestrator.py` (how context_loader is passed to AutoBuildOrchestrator)
- **Agent invoker**: `guardkit/orchestrator/agent_invoker.py` (Player/Coach prompt construction)

### Key Code Paths to Trace

1. `FeatureOrchestrator` → creates `AutoBuildOrchestrator` → passes `context_loader=?`
2. `AutoBuildOrchestrator._invoke_player()` → checks `enable_context and _context_loader is not None`
3. `AutoBuildOrchestrator._invoke_coach()` → checks `enable_context and _context_loader is not None`
4. `AutoBuildContextLoader.get_player_context()` → `JobContextRetriever.retrieve()`
5. Graphiti client initialization / connection availability

## Acceptance Criteria

- [x] Determine whether Graphiti context retrieval is actually executing or silently skipped
- [x] Identify the root cause if context retrieval is not working
- [x] Assess observability: can operators tell if context retrieval is working from logs alone?
- [x] Recommend fixes or improvements (code changes, logging, metrics)
- [x] Produce review report at `.claude/reviews/TASK-REV-8BD8-review-report.md`

## Initial Observations

From preliminary investigation:
- `enable_context=True` appears in all 8 task orchestrator init logs
- Zero grep matches for: `graphiti`, `Graphiti`, `Job-Specific Context`, `context_retriev`, `budget.*tokens`
- Zero grep matches for: `context_loader`, `get_player_context`, `get_coach_context`
- The `JobContextRetriever` has full graceful degradation (returns empty on all exceptions)
- This means silent failure would produce **identical output** to "not called at all"

## Review Mode

Recommended: `/task-review TASK-REV-8BD8 --mode=deep-analysis --depth=comprehensive`
