---
id: TASK-REV-DE4F
title: "Gap analysis: Graphiti integration completeness across AutoBuild and GuardKit commands"
status: backlog
created: 2026-02-08T12:00:00Z
updated: 2026-02-08T12:00:00Z
priority: high
tags: [graphiti, gap-analysis, review, integration, autobuild]
task_type: review
complexity: 7
---

# Task: Gap Analysis - Graphiti Integration Completeness

## Description

Perform a comprehensive gap analysis of the Graphiti integration across AutoBuild and all GuardKit commands to verify that all identified gaps from prior reviews (TASK-REV-C7EB, TASK-REV-0E58, TASK-REV-8BD8) have been addressed by the completed fix tasks, and to identify any **remaining or newly discovered gaps**.

### Critical Context

A major discovery during the fix implementation cycle was that **`init_graphiti()` was never actually called** in production paths. This meant that although extensive Graphiti integration code existed across the codebase (~30+ files, ~8000+ lines), **none of it was actually executing**. The TASK-FIX-GCW6 lazy-init fix addressed this for the singleton pattern, but this review must verify that the fix is effective end-to-end and that no other "dead code" patterns remain.

### Prior Review Chain

| Review | Scope | Key Findings |
|--------|-------|-------------|
| TASK-REV-8BD8 | AutoBuild context retrieval pipeline | `AutoBuildContextLoader` never instantiated in production callers. 5 recommendations (R1-R5). |
| TASK-REV-0E58 | Post-GCW fix verification | All 5 R1-R5 recommendations verified as implemented. Remaining concern: `get_graphiti()` returns None without prior `init_graphiti()`. |
| TASK-REV-C7EB | Command integration points | 7 gaps across 4 commands. `/task-work` standard mode biggest gap. Feature spec seeding missing. `run_abbreviated()` stub. CLI wiring gaps. |

### Completed Fix Tasks (to verify)

**Context Wiring (GCW series):**
- TASK-FIX-GCW1: Init log includes context_loader state
- TASK-FIX-GCW2: INFO-level log when context retrieval skipped
- TASK-FIX-GCW3: Auto-init AutoBuildContextLoader
- TASK-FIX-GCW4: Wire enable_context through FeatureOrchestrator and CLI
- TASK-FIX-GCW5: Context retrieval stats in progress display
- TASK-FIX-GCW6: Lazy-init for `get_graphiti()` singleton (the `init_graphiti()` fix)

**Command Integration (GCI series):**
- TASK-FIX-GCI0: Client lifecycle fixes at 3 integration points (await removal, lazy properties)
- TASK-FIX-GCI1: Wire Graphiti context into standard `/task-work` (GraphitiContextLoader)
- TASK-FIX-GCI2: Fix `run_abbreviated()` stub (full implementation)
- TASK-FIX-GCI3: Wire `--capture-knowledge` CLI flag for `guardkit review`
- TASK-FIX-GCI4: Feature spec seeding in FeaturePlanContextBuilder
- TASK-FIX-GCI5: `[Graphiti]` structured logging across integration points
- TASK-FIX-GCI6: Clarify spec language for `/task-create` library_context
- TASK-FIX-GCI7: Unify `--enable-context/--no-context` flag across commands

### Reference Documentation

- [Graphiti Docs Index](docs/reviews/graphiti_baseline/graphiti_docs_index.md)
- [Graphiti Technical Reference](docs/reviews/graphiti_baseline/graphiti-technical-reference.md)
- [Graphiti Storage Theory](docs/reviews/graphiti_baseline/graphiti-storage-theory.md)
- [Graphiti Architecture](docs/architecture/graphiti-architecture.md)
- [Graphiti Integration Guide](docs/guides/graphiti-integration-guide.md)
- [Episode Metadata Deep Dive](docs/deep-dives/graphiti/episode-metadata.md)
- [ADR-GBF-001: Unified Episode Serialization](docs/architecture/ADR-GBF-001-unified-episode-serialization.md)

## Acceptance Criteria

### Verification of Prior Fixes
- [ ] Verify `init_graphiti()` / lazy-init path actually results in a connected Graphiti client when Neo4j is available
- [ ] Trace the complete lifecycle: config loading -> client initialization -> singleton availability -> each integration point
- [ ] Confirm no remaining "dead code" patterns where Graphiti calls exist but can never execute
- [ ] Verify all 14 fix tasks (GCW1-6 + GCI0-7) are reflected in the current codebase

### Read Path Analysis
- [ ] `/feature-plan` reads from 8 group IDs - verify functional end-to-end
- [ ] `/task-work` (AutoBuild) Player/Coach context retrieval - verify functional
- [ ] `/task-work` (standard) context loading via `GraphitiContextLoader` - verify TASK-FIX-GCI1 wiring
- [ ] `guardkit graphiti capture` gap analysis reads - verify functional

### Write Path Analysis
- [ ] Feature spec seeding from `/feature-plan` (TASK-FIX-GCI4) - verify functional
- [ ] Review knowledge capture via `run_abbreviated()` (TASK-FIX-GCI2) - verify functional
- [ ] AutoBuild turn state and outcome capture - verify functional
- [ ] Interactive capture via `guardkit graphiti capture --interactive` - verify functional

### CLI Integration
- [ ] `--enable-context/--no-context` flag available on: autobuild task, autobuild feature, feature-plan, review
- [ ] `--capture-knowledge/-ck` flag wired in `guardkit review` (TASK-FIX-GCI3)
- [ ] All CLI flags actually reach their target integration points (not just parsed)

### Cross-Cutting Concerns
- [ ] Graceful degradation: all paths handle Graphiti unavailability without crashing
- [ ] `[Graphiti]` structured logging present at all integration points (TASK-FIX-GCI5)
- [ ] No `await` on sync `get_graphiti()` calls (TASK-FIX-GCI0 fix still intact)
- [ ] Lazy properties for Graphiti client in `InteractiveCaptureSession` and `FeaturePlanContextBuilder` (TASK-FIX-GCI0)

### Gap Identification
- [ ] Identify any commands or workflows that SHOULD have Graphiti integration but don't
- [ ] Identify any infrastructure code (modules, classes, methods) that exists but remains unwired
- [ ] Identify any spec-vs-implementation mismatches that weren't caught by prior reviews
- [ ] Check for any regression in previously-fixed integration points

## Test Requirements

- [ ] Review existing test coverage across all Graphiti integration test files
- [ ] Identify any integration scenarios that lack test coverage
- [ ] Verify test count matches expectations from completed task reports

## Implementation Notes

This is a **review task** - no code changes expected. Output is a review report at `.claude/reviews/TASK-REV-DE4F-review-report.md`.

### Review Approach

1. **Bottom-up trace**: Start from `get_graphiti()` and trace every caller through to CLI/command level
2. **Top-down trace**: Start from each CLI command and trace Graphiti-related flags to their implementation
3. **Spec comparison**: Compare each command spec against current implementation
4. **Test audit**: Cross-reference test files against integration points

### Key Files to Analyse

| Category | Files |
|----------|-------|
| Client lifecycle | `guardkit/knowledge/graphiti_client.py` |
| AutoBuild integration | `guardkit/orchestrator/autobuild.py`, `guardkit/knowledge/autobuild_context_loader.py` |
| Feature plan integration | `guardkit/knowledge/feature_plan_context.py`, `guardkit/commands/feature_plan_integration.py` |
| Review integration | `guardkit/knowledge/interactive_capture.py`, `guardkit/cli/review.py` |
| Standard task-work | `installer/core/commands/lib/graphiti_context_loader.py` |
| Context retrieval | `guardkit/knowledge/job_context_retriever.py`, `guardkit/knowledge/budget_calculator.py`, `guardkit/knowledge/task_analyzer.py` |
| CLI layer | `guardkit/cli/autobuild.py`, `guardkit/cli/main.py`, `guardkit/cli/review.py` |
| Progress display | `guardkit/orchestrator/progress.py` |
| Config | `guardkit/knowledge/config.py` |
| Test files | `tests/unit/test_autobuild_context_integration.py`, `tests/unit/test_gci0_client_lifecycle_fixes.py`, `tests/knowledge/test_graphiti_lazy_init.py`, `tests/knowledge/test_interactive_capture.py`, `tests/unit/test_interactive_capture_abbreviated.py`, `tests/unit/knowledge/test_seed_feature_spec.py`, `tests/unit/test_graphiti_structured_logging.py`, `tests/unit/test_cli_review.py`, `tests/unit/test_progress_display.py`, `tests/unit/commands/test_feature_plan_integration.py`, `tests/integration/lib/test_graphiti_context_loader.py` |

## Test Execution Log
[Automatically populated by /task-review]
