# Feature: Graphiti Command Integration

**Parent Review:** TASK-REV-C7EB
**Problem:** Graphiti integration exists at the module level but is not wired into most commands. Standard `/task-work` has a complete unused infrastructure (FEAT-GR-006). `/task-review --capture-knowledge` terminates at a stub. `/feature-plan` reads but never seeds.
**Solution:** Wire existing infrastructure into commands, fix stubs, add missing write paths, unify configuration.

## Tasks

| ID | Title | Priority | Complexity | Wave |
|----|-------|----------|------------|------|
| TASK-FIX-GCI0 | Fix Graphiti client lifecycle at integration points | Critical | 3 | 0 |
| TASK-FIX-GCI1 | Wire Graphiti context into standard /task-work | High | 5 | 1 | **COMPLETED** |
| TASK-FIX-GCI2 | Implement run_abbreviated() for review knowledge capture | High | 4 | 1 | **COMPLETED** |
| TASK-FIX-GCI3 | Wire --capture-knowledge flag in task-review CLI | High | 2 | 2 |
| TASK-FIX-GCI4 | Implement feature spec seeding in /feature-plan | Medium | 3 | 2 |
| TASK-FIX-GCI5 | Add [Graphiti] structured logging | Low | 2 | 3 |
| TASK-FIX-GCI6 | Clarify library_context spec language in task-create | Low | 1 | 3 |
| TASK-FIX-GCI7 | Unify --enable-context flag across commands | Medium | 3 | 3 |

## Execution Strategy

### Wave 0: Prerequisite Fix (must complete first)
- **TASK-FIX-GCI0**: Fix 3 client lifecycle bugs inherited from GCW6 lazy-init:
  1. `await get_graphiti()` syntax error in `graphiti_context_loader.py` (blocks GCI1)
  2. Deferred-init in `InteractiveCaptureSession.__init__` (blocks GCI2)
  3. Deferred-init in `FeaturePlanContextBuilder.__init__` (blocks GCI4)

### Wave 1: Core Wiring (parallel, depends on Wave 0)
- **TASK-FIX-GCI1**: Wire `GraphitiContextLoader` into task-work Phase 1/2 (~200 lines)
- **TASK-FIX-GCI2**: Implement `run_abbreviated()` in interactive_capture.py (~100 lines)

### Wave 2: Dependent Integrations (parallel, depends on Wave 1)
- **TASK-FIX-GCI3**: Wire `--capture-knowledge` CLI flag (depends on GCI2 being functional)
- **TASK-FIX-GCI4**: Add feature spec seeding to `FeaturePlanContextBuilder`

### Wave 3: Polish (parallel, depends on Wave 1-2)
- **TASK-FIX-GCI5**: Structured logging across all Graphiti integration points
- **TASK-FIX-GCI6**: Spec language clarification (docs only)
- **TASK-FIX-GCI7**: Unify `--enable-context/--no-context` flag across all commands

## Risk Assessment

- **Wave 0**: Low risk - targeted fixes (remove `await`, convert to lazy properties), full graceful degradation preserved
- **Wave 1**: Low risk - wiring existing tested components; graceful degradation ensures no regressions
- **Wave 2**: Low risk - additive features with error handling
- **Wave 3**: Zero risk - logging, docs, and CLI flag additions only
