# Implementation Plan: TASK-BDDW-001

## Task
Wire factory BDD plugin discovery into the Coach evidence path (core, Python end-to-end)

## Plan Status
**Completed** - Player turn 1
Completed: 2026-06-12

## Implementation

### Files Modified
- `guardkit/orchestrator/quality_gates/coach_validator.py` — Added BDD factory bridge

### Files Created
- `tests/integration/orchestrator/test_bdd_factory_bridge.py` — Integration tests

### Changes to coach_validator.py

1. **Lazy import of guardkitfactory.bdd** (lines ~95-180):
   - `try/except ImportError` guard for `BDDRunResult`, `discover`, `StackProfile`
   - `_FACTORY_AVAILABLE` flag set at module load time
   - `_factory_available_cache` for runtime caching

2. **Stack profile detection** (`_detect_stack_profile()`):
   - Maps worktree's `project.template` to `StackProfile` strings
   - Python templates: `python`, `fastapi-python`, `django-python`, `flask-python` → `"python"`
   - .NET templates: `.net`, `aspnet-core`, `csharp` → `"dotnet"`
   - JS templates: `node-js`, `javascript`, `typescript` → `"javascript"`

3. **BDDRunResult → bundle.bdd mapping** (`_map_bdd_run_result_to_bundle()`):
   - Preserves `scenarios_attempted` verbatim (never coerces to 0)
   - Maps all fields: `scenarios_attempted`, `scenarios_passed`, `scenarios_failed`, `scenarios_pending`, `failures`, `pending`, `feature_files`
   - Handles both dataclass and dict input for failures/pending

4. **Factory discovery and invocation** (`_run_factory_bdd()`):
   - Calls `discover(stack_profile)` to find the plugin
   - Invokes `plugin.run(worktree_path)` to get `BDDRunResult`
   - Maps result to `bundle.bdd` shape
   - Falls back gracefully when factory unavailable, stack unknown, or discovery fails

5. **CoachValidator.gather_evidence() modification** (lines ~2271-2310):
   - Resets factory cache at start of each gather
   - When `bdd_results` is empty and factory is available: attempts factory discovery
   - When factory returns results: uses them as `bdd_dict`
   - When factory unavailable or returns None: `bdd_dict` stays `None` (absent signal)
   - When Player already produced `bdd_results`: uses them as-is

### Tests
- 8 integration tests covering: mapping, preservation, factory discovery, fallback, stack mapping

## Notes
- Legacy `bdd_runner.py` preserved as Player path's BDD oracle
- CoachValidator uses factory discovery as independent verification
- Lazy import ensures `pip install guardkit-py` without `[autobuild]` still works
