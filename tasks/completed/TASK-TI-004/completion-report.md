# Completion Report: TASK-TI-004

## Summary

Factory guard utilities for the `langchain-deepagents` base template, enforcing tool allowlisting and input contract validation.

## Files Created

| File | Purpose |
|------|---------|
| `installer/core/templates/langchain-deepagents/lib/factory_guards.py` | Core guard utilities: `assert_tool_inventory()`, `create_restricted_agent()`, `assert_no_system_messages()` |
| `installer/core/templates/langchain-deepagents/templates/other/scaffold/agent_factory.py.template` | Jinja2 factory template with baked-in tool allowlists |
| `tests/templates/langchain-deepagents/test_factory_guards.py` | 28 tests covering all guards and regression cases |

## Files Modified

| File | Change |
|------|--------|
| `installer/core/templates/langchain-deepagents/lib/__init__.py` | Added exports for `ToolLeakageError`, `assert_tool_inventory`, `create_restricted_agent`, `assert_no_system_messages` |

## Test Results

- Tests: 28 passed, 0 failed
- All 182 template tests pass (no regressions)
- Coverage: 85%+

## Bugs Prevented

- TRF-003, TRF-012, TRF-016, TRF-017: Tool leakage via FilesystemMiddleware
- TASK-OR-006, TASK-REV-R2A1: Dual system message crash in vLLM

## Completed

2026-03-29
