# Implementation Plan: TASK-BDDW-002

## Task
Multi-stack BDD reachability — route .NET to reqnroll, JS to cucumber-js

## Plan Status
**Implemented** - Player completed Phase 3 on 2026-06-12 (turn 2).

## Implementation

### Files Modified
1. `tests/unit/orchestrator/quality_gates/test_bdd_multi_stack_routing.py` — Rewrote with 11 complete tests. Previous version had only 2 broken tests (assertions were wrong because pytest-bdd was installed in the environment). Fixed subprocess mocking by patching at the plugin module level.

### Files Created
(none — test file already existed but was rewritten)

## Acceptance Criteria
- [x] AC-2: Multi-stack reachability — .NET routes to ReqnrollPlugin, JS routes to CucumberJSPlugin
- [x] AC-2b: Unsupported stack returns None (absent signal)
- [x] AC-3: All tests pass with zero errors

## Test Results
11 tests passed, 0 failed. Coach validation filter (`pytest tests/ -k "bdd and (reqnroll or cucumber or stack_profile)" -v`) passes with 5 matching tests.

## Notes
The plugins (reqnroll_plugin.py, cucumber_js_plugin.py, pytest_bdd_plugin.py) already exist in the guardkitfactory sibling repo. This task only required writing/fixing the per-stack selection tests.
