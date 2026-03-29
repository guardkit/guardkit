# Completion Report: TASK-TI-021

## Summary

Fixed `coach.py.template` to use `create_agent()` instead of `create_deep_agent()`, enforcing the D5 invariant ("Coach has NO tools ever") at the factory level.

## Changes

### `installer/core/templates/langchain-deepagents/templates/other/agents/coach.py.template`
- Replaced `from deepagents import create_deep_agent` with `from langchain.agents import create_agent`
- Added `{{ProjectName}}` middleware imports: `MemoryMiddleware`, `PatchToolCallsMiddleware`, `FilesystemBackend`
- Added `AnthropicPromptCachingMiddleware` from `langchain_anthropic`
- Removed `tools` parameter from `create_coach()` signature (D5 invariant)
- Built curated middleware stack replacing implicit `FilesystemMiddleware` injection
- `MemoryMiddleware` handles AGENTS.md via `FilesystemBackend`
- Always passes `tools=[]` to `create_agent()`

### `tests/templates/langchain-deepagents/test_coach_template.py` (new)
- 17 static analysis tests using AST parsing and content matching
- D5 invariant tests (no tools param, tools=[], no tools variable)
- Factory function tests (create_agent used, no create_deep_agent)
- Middleware stack tests (correct middleware present, no FilesystemMiddleware)
- Placeholder tests ({{ProjectName}} used, no hardcoded deepagents)
- Template structure tests (docstring, contract, params)

## Test Results

- 17/17 new tests pass
- 359/359 total template tests pass (no regressions)

## Quality Gates

- Compilation: PASSED
- Tests: 17/17 PASSED (100%)
- Regressions: 0
