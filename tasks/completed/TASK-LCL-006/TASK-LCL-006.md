---
id: TASK-LCL-006
title: Env-var resolution with AGENT_MODELS__* naming in orchestrator _create_model
status: completed
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
completed_location: tasks/completed/TASK-LCL-006/
previous_state: in_review
state_transition_reason: "Task completion finalised via /task-complete."
priority: high
tags: [templates, langchain-deepagents-orchestrator, provider-resolution, les1-pmev-parity]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: task-work
wave: 2
conductor_workspace: langchain-template-lessons-wave2-3
complexity: 4
---

# Task: Env-var resolution with AGENT_MODELS__* naming in orchestrator _create_model

## Description

The orchestrator template's `_DEFAULT_CONFIG` hard-codes `anthropic:claude-sonnet-4-6`
and `anthropic:claude-haiku-4-5` (agent.py.template:37-42). There is no
env-var override layer — an operator who has configured a local provider
will silently fall through to Anthropic if the YAML is malformed. This is
the PMEV/CRMV bug class from LES1 §3.

Introduce an env-var resolution layer (`AGENT_MODELS__REASONING_MODEL`,
`AGENT_MODELS__IMPLEMENTATION_MODEL`) with precedence: **env > yaml >
hardcoded default**. Document the precedence in the config header.

## Evidence

`installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/agent.py.template:118-144`
builds the orchestrator purely from YAML config; no `os.environ.get` on the
model keys.

## Acceptance Criteria

- [ ] `_build_agent()` (or a new helper) resolves `reasoning_model` in precedence: `AGENT_MODELS__REASONING_MODEL` env → `orchestrator.reasoning_model` in YAML → `_DEFAULT_CONFIG["orchestrator"]["reasoning_model"]`.
- [ ] Same precedence applied to `implementation_model` via `AGENT_MODELS__IMPLEMENTATION_MODEL`.
- [ ] Resolution happens in `_build_agent()` (or a dedicated `_resolve_models()` helper) — not inside `create_orchestrator()` — to keep `create_orchestrator()` a pure function of its arguments.
- [ ] `orchestrator-config.yaml.template` header comment documents the precedence and names the env vars explicitly.
- [ ] Log at INFO: "Resolved reasoning_model=X (source=env|yaml|default)" so operators can see which layer won.
- [ ] Unit tests (in `tests/test_scaffold.py` or equivalent) cover all three precedence paths with clean monkeypatching of `os.environ`.
- [ ] Tests cover the case where env var is set to an empty string (should fall through to yaml, not use the empty string).

## Files

- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/agent.py.template`
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/orchestrator-config.yaml.template`
- Test scaffold (new or updated) — depends on whether this template has a tests/ dir; if not, add one.

## Interface Contract

Env var naming adopts LES1 canonical form `AGENT_MODELS__REASONING_MODEL`
(double-underscore path-flattening convention used throughout LES1 §3).
Downstream agents / operators rely on this exact name.

## Links

- Review: [TASK-REV-LES1 report §HIGH-3, §LOW-2](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
- LES1 §3 PMEV/CRMV — [cross-agent-lessons-from-specialist-agent.md](../../../../specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md)

## Implementation Summary

**Files modified:**
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/agent.py.template`
  - Added `import os` and env-var constants `_ENV_REASONING_MODEL`, `_ENV_IMPLEMENTATION_MODEL` (canonical LES1 §3 PMEV names).
  - Added `_resolve_model(env_var, yaml_value, default_value, key_name)` helper: precedence env > yaml > default, with empty/None values falling through. Emits INFO log `Resolved {key}={value} (source=env|yaml|default)`.
  - Refactored `_load_config` to return `{}` on missing/malformed input (rather than `dict(_DEFAULT_CONFIG)`) so `_resolve_model` can distinguish "yaml provided" from "fell through to default" in its INFO log.
  - Rewired `_build_agent` to resolve both `reasoning_model` and `implementation_model` through `_resolve_model` before calling `create_orchestrator`.
- `installer/core/templates/langchain-deepagents-orchestrator/templates/other/other/orchestrator-config.yaml.template`
  - Expanded header comment to document resolution precedence (env > yaml > default), name the canonical env vars, and describe the empty-string fallthrough contract.

**Files created:**
- `installer/core/templates/langchain-deepagents-orchestrator/templates/testing/tests/test_scaffold.py.template`
  - New tests/ directory for the orchestrator template (none existed before).
  - `TestResolveModelPrecedence` — env/yaml/default paths (3 tests).
  - `TestEmptyEnvFallsThrough` — empty env var does not clobber yaml; empty env + empty yaml falls through to default (2 tests).
  - `TestBuildAgentUsesResolvedModels` — end-to-end integration with `monkeypatch.setenv` / `monkeypatch.setattr(module, "create_orchestrator", ...)` verifying both keys wire correctly and partial-empty envs behave cell-by-cell (4 tests).
  - Tests use a `conftest`-style `agent_module` fixture that stubs out `agents.create_orchestrator` so they run without the DeepAgents / LangChain runtime stack.

**Verification performed (not committed):**
- Rendered both updated `.template` files with `{{ProjectName}}=scratch`; `py_compile` passed for every rendered `.py`.
- Direct-loaded the rendered `agent.py` with `importlib.util.spec_from_file_location` (bypassing the package's pre-existing `__init__` import chain issue — out of scope, same class as LCL-001 but for orch template) and ran 10 behavioural checks covering all three precedence paths, empty-env fallthrough on each key, `_build_agent` integration, and `_load_config` no-longer-backfills-defaults contract. All 10 passed.
- Confirmed INFO log output matches AC verbatim: `Resolved reasoning_model=my-provider:my-model (source=env)`, `(source=yaml)`, `(source=default)`.

**Scope notes:**
- Task acceptance criterion about ainvoke-style system-message checks does not apply here (covered separately by LCL-005).
- The pre-existing `scratch.tools` import failure in `templates/other/tools/orchestrator_tools.py.template` is the LCL-001 bug class replayed in the orchestrator template — **not** LCL-006 scope. Should be tracked as a separate task.
- Smoke-test suite (`tests/integration/test_template_render_import.py`) has one pre-existing `XPASS(strict)` on `langchain-deepagents::scratch.player` — stale xfail marker that should be removed now that LCL-001 merged. Not LCL-006 scope.

**AC checklist:**
- [x] `_build_agent()` resolves `reasoning_model` via env > yaml > default.
- [x] Same precedence for `implementation_model`.
- [x] Resolution in `_build_agent()` (via `_resolve_model()` helper), not inside `create_orchestrator()`.
- [x] YAML header comment documents precedence + names env vars.
- [x] INFO log `Resolved X=Y (source=env|yaml|default)` — format verified.
- [x] Unit tests cover all three precedence paths with `os.environ` monkeypatching.
- [x] Tests cover empty-string env var falls through to yaml.
