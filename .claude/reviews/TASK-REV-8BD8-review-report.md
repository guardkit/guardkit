# Review Report: TASK-REV-8BD8

## Review: Graphiti Job-Specific Context Retrieval in FEAT-D4CE AutoBuild Output

## Executive Summary

**Graphiti context retrieval is NOT executing during autobuild.** The feature is entirely inert in production despite `enable_context=True` appearing in all orchestrator init logs. The root cause is a **missing wiring bug**: `AutoBuildContextLoader` is never instantiated or passed to `AutoBuildOrchestrator` by any caller (neither FeatureOrchestrator nor CLI). The guard condition `self.enable_context and self._context_loader is not None` is always `False` because `_context_loader` is always `None`.

This is compounded by a significant **observability gap**: the init log reports `enable_context=True` without reporting `context_loader=None`, creating a false impression that context retrieval is configured and active.

**Severity: Medium** - Feature is completely non-functional but graceful degradation means no runtime failures or regressions. However, the AutoBuild system is missing all Graphiti-sourced context (role constraints, quality gate configs, turn states, implementation modes) that was designed to improve Player/Coach decision quality.

---

## Review Details

- **Mode**: Deep Analysis
- **Depth**: Comprehensive
- **Reviewer**: Claude (code trace analysis)
- **Date**: 2026-02-08
- **Run Analyzed**: FEAT-D4CE (UX Design Mode autobuild, `docs/reviews/ux_design_mode/success_run.md`)

---

## Findings

### Finding 1: `AutoBuildContextLoader` is Never Instantiated in Production

**Severity: Critical (for the feature)**

The class `AutoBuildContextLoader` (defined in `guardkit/knowledge/autobuild_context_loader.py`) is **never constructed** outside of:
- Docstring examples (lines 19, 100)
- Unit tests (`tests/unit/test_autobuild_context_integration.py`)

**Evidence:**
```
$ grep -r "AutoBuildContextLoader(" --include="*.py" guardkit/
guardkit/knowledge/autobuild_context_loader.py:19:    loader = AutoBuildContextLoader(graphiti=graphiti_client)  # docstring
guardkit/knowledge/autobuild_context_loader.py:100:        loader = AutoBuildContextLoader(graphiti=client)      # docstring
```

No production code ever calls `AutoBuildContextLoader(graphiti=...)`.

### Finding 2: Neither Caller Passes `context_loader` to `AutoBuildOrchestrator`

**Severity: Critical (for the feature)**

There are two production callers of `AutoBuildOrchestrator()`:

**Caller 1: `FeatureOrchestrator._execute_task()`** ([feature_orchestrator.py:1247-1255](guardkit/orchestrator/feature_orchestrator.py#L1247-L1255))
```python
task_orchestrator = AutoBuildOrchestrator(
    repo_root=self.repo_root,
    max_turns=self.max_turns,
    resume=False,
    existing_worktree=worktree,
    worktree_manager=self._worktree_manager,
    sdk_timeout=effective_sdk_timeout,
    enable_pre_loop=effective_enable_pre_loop,
)
# Missing: enable_context=True (defaults to True anyway)
# Missing: context_loader=<AutoBuildContextLoader instance>  <-- THE BUG
```

**Caller 2: CLI `task` command** ([cli/autobuild.py:367-378](guardkit/cli/autobuild.py#L367-L378))
```python
orchestrator = AutoBuildOrchestrator(
    repo_root=Path.cwd(),
    max_turns=max_turns,
    resume=resume,
    enable_pre_loop=enable_pre_loop,
    development_mode=effective_mode,
    sdk_timeout=effective_sdk_timeout,
    skip_arch_review=effective_skip_arch_review,
    enable_checkpoints=enable_checkpoints,
    rollback_on_pollution=rollback_on_pollution,
    ablation_mode=ablation_mode,
)
# Missing: context_loader=<AutoBuildContextLoader instance>  <-- THE BUG
```

### Finding 3: Guard Condition Always Evaluates to False

**Severity: Critical (for the feature)**

The guard at [autobuild.py:2573](guardkit/orchestrator/autobuild.py#L2573) (Player) and [autobuild.py:2724](guardkit/orchestrator/autobuild.py#L2724) (Coach):
```python
if self.enable_context and self._context_loader is not None:
```

Since `_context_loader` defaults to `None` at [autobuild.py:552](guardkit/orchestrator/autobuild.py#L552) and is never set by any caller:
- `self.enable_context` = `True` (default)
- `self._context_loader` = `None` (never provided)
- `True and (None is not None)` = `True and False` = **`False`**

Context retrieval is **never attempted**.

### Finding 4: Misleading Init Log (Observability Gap)

**Severity: High**

The init log at [autobuild.py:570-585](guardkit/orchestrator/autobuild.py#L570-L585) reports:
```
enable_context=True, verbose=False
```

But does **not** report `context_loader=None`. In the FEAT-D4CE run output, all 8 task initializations show `enable_context=True`, creating the false impression that context retrieval is active:

```
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized: ..., enable_context=True, verbose=False
```

Compare with `existing_worktree` which IS logged clearly:
```
existing_worktree=provided
```

The `context_loader` state should follow the same pattern.

### Finding 5: Graceful Degradation Masks the Bug

**Severity: Medium**

The entire Graphiti context pipeline uses aggressive graceful degradation:

1. `AutoBuildContextLoader.get_player_context()` returns `_empty_result()` if `self.retriever is None` (line 184-187)
2. `JobContextRetriever._query_category()` returns `[], 0` on any exception (line 996-998)
3. `AutoBuildOrchestrator._invoke_player()` catches exceptions and sets `context_prompt = ""` (line 2597-2600)

This is good for resilience but means silent failure produces **identical output** to "not called at all" - zero runtime indicators in logs, output, or results.

### Finding 6: No Graphiti Connection Check at Startup

**Severity: Low**

Even if `AutoBuildContextLoader` were provided, there's no startup check for Neo4j/Graphiti availability. The loader's `retriever` property at [autobuild_context_loader.py:141-149](guardkit/knowledge/autobuild_context_loader.py#L141-L149) creates `JobContextRetriever` lazily:
```python
@property
def retriever(self) -> Optional[JobContextRetriever]:
    if self._retriever is None and self.graphiti is not None:
        self._retriever = JobContextRetriever(self.graphiti)
    return self._retriever
```

If `graphiti` is `None` (no Neo4j connection), this silently returns `None`, which triggers `_empty_result()`. No warning is logged at init time about the missing Graphiti connection.

---

## Root Cause Analysis

The root cause is an **incomplete integration**: the Graphiti context retrieval pipeline was built end-to-end (FEAT-GR-006, tasks GR6-001 through GR6-012) but the final wiring step - instantiating `AutoBuildContextLoader` and passing it to `AutoBuildOrchestrator` - was never completed in the production callers.

The code was designed with DI in mind (`context_loader: Optional[AutoBuildContextLoader] = None`), and unit tests validate the integration thoroughly using mocked loaders. But the "real" callers (FeatureOrchestrator and CLI) were never updated to:
1. Initialize a Graphiti client
2. Create an `AutoBuildContextLoader` with it
3. Pass it via `context_loader=loader`

This is a classic "last mile" integration gap - all the building blocks exist but were never connected.

---

## Answers to Task Questions

### Q1: Is Graphiti context retrieval actually executing during autobuild?

**No.** It is completely skipped because `_context_loader is None`. The guard `self.enable_context and self._context_loader is not None` at lines 2573 and 2724 of `autobuild.py` always evaluates to `False`.

### Q2: Why is there no visible output from context retrieval?

Because retrieval is **never attempted** (Finding 3). The code path that would log context retrieval details (`logger.debug` at lines 2592-2596 for Player, 2750-2754 for Coach) is never reached. The `enable_context=True` flag is a no-op without a `context_loader`.

### Q3: What would working context retrieval look like in the output?

If working correctly, you would see (at DEBUG level):
```
DEBUG:guardkit.orchestrator.autobuild:Retrieved Player context for TASK-DM-001 turn 1: 2500/4000 tokens, 6 categories
DEBUG:guardkit.orchestrator.autobuild:Retrieved Coach context for TASK-DM-001 turn 1: 1200/4000 tokens, 3 categories
```

And if `verbose=True`:
```
INFO:guardkit.orchestrator.autobuild:Context retrieval details:
=== Context Retrieval Details ===
Task: TASK-DM-001
Budget: 2500/4000 tokens
Categories populated: 6
  - feature_context: 2 items
  - similar_outcomes: 3 items
  ...
=================================
```

The Player prompt would also contain a `## Job-Specific Context` section (from `RetrievedContext.to_prompt()` at [job_context_retriever.py:136](guardkit/knowledge/job_context_retriever.py#L136)).

### Q4: Is there an observability gap?

**Yes, a significant one.** Three gaps identified:

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| Init log shows `enable_context=True` but not `context_loader=None/provided` | Operators think context retrieval is active when it's dead | Add `context_loader={'provided' if context_loader else 'None'}` to init log |
| No INFO-level log when context retrieval is skipped due to missing loader | Silent skip with no evidence | Add `logger.info("Context retrieval skipped: context_loader not provided")` at guard check |
| No startup validation of Graphiti availability | Silent degradation to empty context | Add `logger.warning("Graphiti not available")` during AutoBuildContextLoader init |

---

## Recommendations

### R1: Wire `AutoBuildContextLoader` in Production Callers (Priority: High)

Add Graphiti client initialization and `AutoBuildContextLoader` creation to both callers:

**FeatureOrchestrator** - Add to `__init__()` or `_execute_task()`:
```python
# Initialize context loader (if Graphiti available)
context_loader = None
if enable_context:
    try:
        from guardkit.knowledge import get_graphiti
        graphiti = await get_graphiti()
        if graphiti:
            context_loader = AutoBuildContextLoader(graphiti=graphiti, verbose=verbose)
    except Exception as e:
        logger.warning(f"Graphiti unavailable, context retrieval disabled: {e}")
```

Then pass to `AutoBuildOrchestrator`:
```python
task_orchestrator = AutoBuildOrchestrator(
    ...,
    context_loader=context_loader,
)
```

**CLI** - Similar pattern in `guardkit/cli/autobuild.py`.

### R2: Fix Init Log to Include `context_loader` State (Priority: High)

Change [autobuild.py:583](guardkit/orchestrator/autobuild.py#L583) from:
```python
f"enable_context={self.enable_context}, "
```
To:
```python
f"enable_context={self.enable_context}, "
f"context_loader={'provided' if self._context_loader else 'None'}, "
```

### R3: Add INFO-Level Log When Context Retrieval Is Skipped (Priority: Medium)

At [autobuild.py:2573](guardkit/orchestrator/autobuild.py#L2573) add an `else` branch:
```python
if self.enable_context and self._context_loader is not None:
    # ... existing retrieval code ...
elif self.enable_context:
    logger.info(f"Context retrieval enabled but context_loader not provided for {task_id}")
```

Same at [autobuild.py:2724](guardkit/orchestrator/autobuild.py#L2724) for Coach.

### R4: Add Context Retrieval Stats to Progress Display (Priority: Low)

Add to the turn summary in `ProgressDisplay`:
- Context: `retrieved (6 categories, 2500 tokens)` or `skipped (no loader)` or `disabled`

### R5: Consider Auto-Initialization Pattern (Priority: Low)

Instead of requiring callers to construct `AutoBuildContextLoader`, have `AutoBuildOrchestrator` create one automatically when `enable_context=True`:

```python
# In AutoBuildOrchestrator.__init__():
if self.enable_context and self._context_loader is None:
    try:
        from guardkit.knowledge import get_graphiti_sync
        graphiti = get_graphiti_sync()
        if graphiti:
            self._context_loader = AutoBuildContextLoader(graphiti=graphiti, verbose=self.verbose)
            logger.info("Auto-initialized context_loader with Graphiti")
        else:
            logger.info("Graphiti not available, context retrieval will be skipped")
    except Exception as e:
        logger.info(f"Could not auto-initialize context_loader: {e}")
```

This eliminates the "last mile" wiring problem entirely.

---

## Acceptance Criteria Assessment

| Criteria | Status | Notes |
|----------|--------|-------|
| Determine whether Graphiti context retrieval is actually executing or silently skipped | **DONE** | Silently skipped - `_context_loader` is always `None` |
| Identify the root cause if context retrieval is not working | **DONE** | Missing wiring: `AutoBuildContextLoader` never instantiated in production callers |
| Assess observability: can operators tell if context retrieval is working from logs alone? | **DONE** | No - init log is misleading (`enable_context=True`), no skip logs |
| Recommend fixes or improvements | **DONE** | 5 recommendations (R1-R5) |
| Produce review report | **DONE** | This report |

---

## Files Analyzed

| File | Purpose | Key Lines |
|------|---------|-----------|
| [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py) | Creates AutoBuildOrchestrator for feature tasks | 1247-1255 (no context_loader) |
| [cli/autobuild.py](guardkit/cli/autobuild.py) | Creates AutoBuildOrchestrator for CLI | 367-378 (no context_loader) |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | AutoBuildOrchestrator with context guards | 441-552 (init), 2573 (Player guard), 2724 (Coach guard) |
| [autobuild_context_loader.py](guardkit/knowledge/autobuild_context_loader.py) | AutoBuildContextLoader class | 124-461 (never instantiated in prod) |
| [job_context_retriever.py](guardkit/knowledge/job_context_retriever.py) | JobContextRetriever with Graphiti queries | 288-1117 (never reached) |
| [success_run.md](docs/reviews/ux_design_mode/success_run.md) | FEAT-D4CE run output | Lines 60,64,257,260,468,471,772,878 (init logs) |

---

## Impact Assessment

- **Current Impact**: Zero. AutoBuild works fine without Graphiti context - it just doesn't benefit from cross-session knowledge, turn learning, or quality gate configs from the knowledge graph.
- **Future Impact**: High. As Graphiti captures more project knowledge, the context retrieval feature will become increasingly valuable for improving Player implementation quality and Coach validation accuracy. Fixing this wiring gap is a prerequisite.
- **Risk of Fix**: Low. The fix is additive (wiring up an existing, well-tested pipeline). Graceful degradation ensures no regressions if Graphiti is unavailable.
