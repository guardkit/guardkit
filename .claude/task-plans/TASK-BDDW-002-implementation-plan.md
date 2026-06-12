# Implementation Plan: TASK-BDDW-002

## Task
Multi-stack BDD reachability — route .NET to reqnroll, JS to cucumber-js

## Plan Status
**Implemented** - Player completed Phase 3 on 2026-06-12.

## Implementation

### Files Modified
1. `guardkitfactory/src/guardkitfactory/bdd/plugins/reqnroll_plugin.py` — Implemented `discover()` method: checks `stack.language in ("dotnet", "csharp")`, presence of `.sln`/`.csproj` files, and `dotnet` CLI availability.
2. `guardkitfactory/src/guardkitfactory/bdd/plugins/cucumber_js_plugin.py` — Implemented `discover()` method: checks `stack.language in ("javascript", "typescript")`, `package.json` with cucumber dependency, and `npx`/`cucumber-js` CLI availability.

### Files Created
1. `tests/unit/orchestrator/quality_gates/test_bdd_multi_stack_routing.py` — 11 tests covering:
   - Python → PytestBDDPlugin routing
   - .NET → ReqnrollPlugin routing
   - C# → ReqnrollPlugin routing
   - JavaScript → CucumberJSPlugin routing
   - TypeScript → CucumberJSPlugin routing
   - Factory discover returns first matching plugin
   - Unknown language returns None
   - Python without pytest_bdd returns None
   - .NET without project files returns None
   - JS without cucumber dependency returns None
   - .NET without dotnet CLI returns None

## Acceptance Criteria
- [x] AC-2: Multi-stack reachability — .NET routes to ReqnrollPlugin, JS routes to CucumberJSPlugin
- [x] AC-2b: Unsupported stack returns None (absent signal)
- [x] AC-3: All tests pass with zero errors

## Test Results
11 tests passed, 0 failed. Coach validation filter (`pytest tests/ -k "bdd and (reqnroll or cucumber or stack_profile)" -v`) passes.

## Notes
This plan was auto-generated because the task was created via /feature-plan
with pre-loop disabled (enable_pre_loop=False).
The detailed specifications are in the task markdown file.
