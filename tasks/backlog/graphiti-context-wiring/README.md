# Feature: Graphiti Context Wiring Fix

**Parent Review:** TASK-REV-8BD8
**Problem:** Graphiti context retrieval is completely inert in production - `AutoBuildContextLoader` is never instantiated or passed to `AutoBuildOrchestrator` by any caller.
**Solution:** Fix observability gaps, auto-initialize context loader, wire up callers, add progress display stats.

## Tasks

| ID | Title | Priority | Complexity | Wave |
|----|-------|----------|------------|------|
| TASK-FIX-GCW1 | Fix init log to include context_loader state | High | 1 | 1 |
| TASK-FIX-GCW2 | Add INFO-level log when context retrieval is skipped | Medium | 1 | 1 |
| TASK-FIX-GCW3 | Auto-initialize AutoBuildContextLoader when enable_context=True | High | 3 | 2 |
| TASK-FIX-GCW4 | Wire context_loader in FeatureOrchestrator and CLI callers | High | 3 | 2 |
| TASK-FIX-GCW5 | Add context retrieval stats to progress display | Low | 3 | 3 |
| TASK-FIX-GCW6 | Fix Graphiti client lifecycle - singleton never initialized in autobuild | High | 4 | 4 |

## Execution Strategy

### Wave 1: Observability (parallel, no dependencies) - COMPLETED
- **TASK-FIX-GCW1**: Fix init log (1 line change)
- **TASK-FIX-GCW2**: Add skip log (4 lines each, 2 locations)

### Wave 2: Core Fix (parallel, depends on Wave 1) - COMPLETED
- **TASK-FIX-GCW3**: Auto-init context_loader in `__init__()` (~15 lines)
- **TASK-FIX-GCW4**: Wire `enable_context` flag through callers (~10 lines)

### Wave 3: Enhancement (depends on Wave 2) - COMPLETED
- **TASK-FIX-GCW5**: Progress display stats (moderate scope)

### Wave 4: Client Lifecycle (depends on Wave 2) - BACKLOG
- **TASK-FIX-GCW6**: Fix singleton initialization + address dual client strategy

## Risk Assessment

- **Wave 1**: Zero risk - logging only, no behavior change
- **Wave 2**: Low risk - additive changes, graceful degradation ensures no regressions if Graphiti unavailable
- **Wave 3**: Low risk - UI enhancement only
- **Wave 4**: Low-medium risk - changes client initialization, but graceful degradation preserved
