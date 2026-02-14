# Review Report: TASK-REV-A1E7

## Executive Summary

The `/system-overview` command (and two other spec-driven commands) fails to initialize Graphiti because `load_dotenv()` is only called in the `guardkit` CLI entry point (`guardkit/cli/main.py`). When Claude Code executes spec-driven commands as inline Python, the CLI is never invoked, so `.env` variables like `OPENAI_API_KEY` are absent from `os.environ`.

**Root cause**: Architectural gap between two execution models — CLI (has dotenv) vs spec-driven (no dotenv).

**Recommended fix**: Add `load_dotenv()` to `_try_lazy_init()` in `graphiti_client.py` (Option B). Single-line change, zero risk of side effects, fixes all affected paths at once.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Task ID**: TASK-REV-A1E7
- **Date**: 2026-02-12

---

## AC-001: All Code Paths That Call `get_graphiti()`

### Entry Point Classification

| Entry Point | `load_dotenv()` Called? | `get_graphiti()` Works? |
|---|---|---|
| **CLI path** (`guardkit` CLI → `main.py`) | YES (line 54, module-level) | YES |
| **Spec-driven** (Claude Code inline Python) | NO | NO — `OPENAI_API_KEY` missing |
| **Direct Python import** (scripts, notebooks) | NO | NO — unless user calls `load_dotenv()` manually |
| **Tests** | YES — via conftest.py `monkeypatch.setenv` | YES |
| **AutoBuild** (`FeatureOrchestrator`) | YES — launched via CLI | YES |

### Python Call Sites (production code, excluding tests)

**Category 1: CLI path (`.env` loaded via `main.py`)** — 6 files, ~10 call sites
- `guardkit/cli/system_context.py` — via `get_system_overview()` / `run_impact_analysis()`
- `guardkit/cli/graphiti.py` — all `guardkit graphiti *` subcommands
- `guardkit/orchestrator/autobuild.py` — lines 612-613, 2437-2438
- `guardkit/orchestrator/feature_orchestrator.py` — lines 934, 945
- `guardkit/knowledge/seed_*.py` — all seeding functions (invoked via CLI)
- `guardkit/planning/graphiti_arch.py` — lines 19, 63

**Category 2: Spec-driven path (NO `.env` loading)** — 3 command specs
- `installer/core/commands/system-overview.md` — lines 39-43, 284-287
- `installer/core/commands/impact-analysis.md` — lines 89-92, 430-433
- `installer/core/commands/context-switch.md` — lines 447-449

**Category 3: Internal modules (called from either path)** — 12+ files
- `guardkit/knowledge/context_loader.py` — 4 call sites (lines 157, 330, 429, 517)
- `guardkit/knowledge/interactive_capture.py` — line 112
- `guardkit/knowledge/feature_plan_context.py` — line 312
- `guardkit/knowledge/task_analyzer.py` — line 188
- `guardkit/knowledge/job_context_retriever.py` — line 315
- `guardkit/knowledge/outcome_manager.py` — line 142
- `guardkit/knowledge/failed_approach_manager.py` — 3 call sites
- `guardkit/knowledge/turn_state_operations.py` — 5 call sites
- `guardkit/knowledge/template_sync.py` — 3 call sites
- `guardkit/knowledge/gap_analyzer.py` — line 332
- `guardkit/knowledge/quality_gate_queries.py` — line 38
- `guardkit/integrations/graphiti/project.py` — 5 call sites
- `guardkit/planning/mode_detector.py` — line 12
- `guardkit/planning/coach_context_builder.py` — line 25
- `guardkit/quality_gates/coach_validator.py` — line 554

**Total**: ~40 production `get_graphiti()` call sites across ~20 files.

### Failure Chain for Spec-Driven Commands

```
Claude Code reads system-overview.md spec
  → Executes inline Python: `from guardkit.knowledge.graphiti_client import get_graphiti`
  → `get_graphiti()` called
  → `_factory` is None, `_factory_init_attempted` is False
  → `_try_lazy_init()` called
  → `load_graphiti_config()` succeeds (reads YAML, not .env)
  → `GraphitiClientFactory` created
  → `factory.get_thread_client()` called
  → `client.initialize()` called
  → Line 479: `os.environ.get("OPENAI_API_KEY")` → None ← FAILURE POINT
  → Returns False, client not connected
  → `get_graphiti()` returns client with `enabled=False`
```

---

## AC-002: Spec-Driven Commands Affected by This Gap

### Directly Affected (contain `get_graphiti()` in spec code blocks)

| Command | Spec File | Lines | Severity |
|---|---|---|---|
| `/system-overview` | `installer/core/commands/system-overview.md` | 39-43, 284-287 | HIGH — primary use case is Graphiti query |
| `/impact-analysis` | `installer/core/commands/impact-analysis.md` | 89-92, 430-433 | HIGH — Graphiti provides architecture context |
| `/context-switch` | `installer/core/commands/context-switch.md` | 447-449 | MEDIUM — Graphiti provides project registry |

### Indirectly Affected (reference Graphiti but don't call `get_graphiti()` directly in spec)

| Command | Spec File | How Graphiti is Used |
|---|---|---|
| `/feature-plan` | `installer/core/commands/feature-plan.md` | Via `FeaturePlanContextBuilder` (Python import path) |
| `/task-work` | `installer/core/commands/task-work.md` | Phase 1.7 Graphiti integration (LLM pseudocode) |
| `/feature-build` | `installer/core/commands/feature-build.md` | Via AutoBuild orchestrator (CLI-launched, not affected) |
| `/task-review` | `installer/core/commands/task-review.md` | Knowledge capture (optional, degrades gracefully) |
| `/task-create` | `installer/core/commands/task-create.md` | Context enrichment (optional, degrades gracefully) |

**Key insight**: `/feature-plan` is affected if Claude Code executes `FeaturePlanContextBuilder` as inline Python. However, `/task-work` and `/feature-build` are NOT affected because they launch via the CLI entry point (AutoBuild subprocess).

---

## AC-003: Where Should `load_dotenv()` Be Added?

### Option A: Shared Bootstrap Function

Create a `guardkit.bootstrap` module called from all entry points:

```python
# guardkit/bootstrap.py
from dotenv import load_dotenv
from pathlib import Path

_bootstrapped = False

def bootstrap():
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True
    # Same logic as main.py _load_env_files()
    _load_env_files()
```

**Pros**: Centralized, explicit, testable
**Cons**: Requires updating all entry points; spec-driven commands still need to call it; adds a new module

### Option B: Add `load_dotenv()` to `_try_lazy_init()` (RECOMMENDED)

Add a single `load_dotenv()` call at the top of `_try_lazy_init()` in `graphiti_client.py`:

```python
def _try_lazy_init() -> Optional[GraphitiClient]:
    from dotenv import load_dotenv
    load_dotenv()  # Ensure .env is loaded before checking OPENAI_API_KEY
    # ... rest of existing code
```

**Pros**: Zero new modules, fixes all paths at once, idempotent, no API changes
**Cons**: Slightly unconventional location; `load_dotenv()` is a side effect in an initialization function

### Option C: Add `load_dotenv()` to `GraphitiClient.initialize()`

```python
async def initialize(self) -> bool:
    from dotenv import load_dotenv
    load_dotenv()
    # ... existing code including OPENAI_API_KEY check
```

**Pros**: Closest to the failure point
**Cons**: Called from async context (though `load_dotenv()` is sync, it's fine); called on every `initialize()` (redundant for CLI path); doesn't help if someone checks env vars before calling `initialize()`

### Option D: Add `load_dotenv()` to each spec command block

Update each `.md` spec to include:
```python
from dotenv import load_dotenv
load_dotenv()
```

**Pros**: Explicit per-command
**Cons**: Must update every spec; easy to forget for new specs; duplicated code; spec authors must remember

---

## AC-004: Trade-Off Analysis

| Criterion | Option A (Bootstrap) | Option B (_try_lazy_init) | Option C (initialize) | Option D (Specs) |
|---|---|---|---|---|
| **Files changed** | 3+ (new module + main.py + specs) | 1 | 1 | 3+ spec files |
| **Risk of regression** | Low | Very Low | Very Low | None |
| **Covers all paths** | Only if all entry points call it | YES (all `get_graphiti()` paths) | YES (all init paths) | NO (only updated specs) |
| **Future-proof** | Need to update new entry points | Automatic — any new `get_graphiti()` caller benefits | Automatic | Manual per spec |
| **Side effects** | Explicit bootstrap | Hidden in lazy-init | Hidden in async init | Explicit in spec |
| **Idempotent** | YES | YES (`load_dotenv()` is idempotent) | YES | YES |
| **python-dotenv dependency** | Already a dep | Already a dep | Already a dep | Already a dep |
| **Spec author burden** | None | None | None | Must remember |

### Critical Differentiator

Option B is the only approach where **new code that calls `get_graphiti()` automatically gets `.env` loading for free**. Options A and D require manual wiring for each new entry point or spec. Option C would work but is semantically wrong — `initialize()` is an async method and shouldn't be responsible for environment bootstrapping.

---

## AC-005: Recommended Fix

### Recommendation: Option B — Add `load_dotenv()` to `_try_lazy_init()`

**Implementation** (1 file, ~3 lines changed):

```python
# guardkit/knowledge/graphiti_client.py, in _try_lazy_init()

def _try_lazy_init() -> Optional[GraphitiClient]:
    """Attempt lazy initialization of Graphiti factory from config."""
    global _factory, _factory_init_attempted

    _factory_init_attempted = True

    try:
        # Load .env before checking for API keys (fixes spec-driven command gap)
        from dotenv import load_dotenv
        load_dotenv()

        from guardkit.knowledge.config import load_graphiti_config
        settings = load_graphiti_config()
        # ... rest unchanged
```

**Justification**:

1. **Minimal change** — 2 lines added to 1 file
2. **Self-healing** — Any code path that calls `get_graphiti()` now gets `.env` loading for free, whether it comes from CLI, spec, script, or test
3. **Idempotent** — `load_dotenv()` is a no-op if `.env` is already loaded (CLI path) or doesn't exist
4. **No API changes** — Existing callers work unchanged
5. **Correct semantic location** — `_try_lazy_init()` is the "bootstrap Graphiti from scratch" function; loading environment is part of bootstrapping
6. **python-dotenv already a dependency** — No new dependency needed
7. **Consistent with existing pattern** — `_try_lazy_init()` already calls `load_graphiti_config()` which reads YAML; reading `.env` is the same class of bootstrapping
8. **Zero risk to CLI path** — When `main.py` has already called `load_dotenv()`, the second call in `_try_lazy_init()` is a no-op

**Optional enhancement**: Use the same `_load_env_files()` logic from `main.py` (project-root traversal) instead of bare `load_dotenv()`. However, bare `load_dotenv()` searches upward by default in python-dotenv >=1.0, so this may be unnecessary.

---

## Impact Assessment: Other Integrations

### Not Affected
- **AutoBuild** (`/feature-build`) — Launches via CLI subprocess → `main.py` loads `.env`
- **CLI commands** (`guardkit graphiti *`, `guardkit review`, etc.) — All go through `main.py`
- **Tests** — Use `monkeypatch.setenv` in conftest.py

### Affected (will be fixed by Option B)
- `/system-overview` spec → `get_graphiti()` → `_try_lazy_init()` ← fixed
- `/impact-analysis` spec → `get_graphiti()` → `_try_lazy_init()` ← fixed
- `/context-switch` spec → `get_graphiti()` → `_try_lazy_init()` ← fixed
- `/feature-plan` spec → `FeaturePlanContextBuilder` → `.graphiti_client` property → `get_graphiti()` → `_try_lazy_init()` ← fixed
- Any future spec-driven command using `get_graphiti()` ← fixed

### Edge Case: `init_graphiti()` Path
The `init_graphiti()` async function does NOT go through `_try_lazy_init()`. If someone calls `await init_graphiti(config)` directly without loading `.env` first, `OPENAI_API_KEY` would still be missing. However, `init_graphiti()` requires an explicit `GraphitiConfig`, so the caller is already doing explicit setup and can be expected to handle `.env` loading themselves. This is an acceptable gap.

---

## Appendix: The Two Execution Models

### Model 1: CLI (Python execution)
```
User → `guardkit system-overview`
  → `main.py` (module-level: `_load_env_files()` → `load_dotenv()`)
  → Click group → `system_overview()` function
  → `get_system_overview()` → `SystemPlanGraphiti` → `get_graphiti()`
  → OPENAI_API_KEY present ✓
```

### Model 2: Spec-Driven (Claude Code execution)
```
User → `/system-overview` slash command
  → Claude Code reads `installer/core/commands/system-overview.md`
  → Claude Code executes Python from code blocks as inline Python
  → `from guardkit.knowledge.graphiti_client import get_graphiti`
  → `get_graphiti()` → `_try_lazy_init()`
  → OPENAI_API_KEY NOT present ✗ (no `load_dotenv()` in this path)
```

After fix (Option B):
```
User → `/system-overview` slash command
  → Claude Code reads spec, executes inline Python
  → `get_graphiti()` → `_try_lazy_init()` → `load_dotenv()` ← NEW
  → OPENAI_API_KEY present ✓
```

---

## Recommended Follow-Up Task

Create: `TASK-FIX-A1E7 "Add load_dotenv() to _try_lazy_init() in graphiti_client.py"`

**Scope**:
- Add `from dotenv import load_dotenv; load_dotenv()` to `_try_lazy_init()`
- Add 2-3 unit tests verifying `.env` loading happens during lazy init
- Verify existing tests still pass (dotenv is idempotent)

**Estimated complexity**: 2/10 (simple, low risk)
