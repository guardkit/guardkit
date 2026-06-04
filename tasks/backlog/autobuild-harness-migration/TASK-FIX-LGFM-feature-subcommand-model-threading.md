---
id: TASK-FIX-LGFM
title: Thread --model from `guardkit autobuild feature` to LangGraph harness
status: in_progress
task_type: bug
created: 2026-06-04T20:30:00Z
updated: 2026-06-04T20:45:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
priority: critical
complexity: 3
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 1
blocks:
  - TASK-HMIG-010
falsifier: "After landing, `guardkit autobuild feature {FEAT-XXX} --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph reaches Player turn 1 without raising `LangGraphHarnessError: ... model=None: \"Could not resolve authentication method...\"`. A regression test asserts that invoking the feature subcommand with `--model X` results in `model=X` being passed to `AutoBuildOrchestrator.__init__` (mirrors the falsifier test pattern from TASK-HMIG-006.4 for F1)."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - sibling-of-f1
---

# Task: Thread --model from feature subcommand to LangGraph harness

## Description

Surfaced by TASK-HMIG-010 run 1 (2026-06-04T19:12, ~28s). The `guardkit autobuild feature` CLI subcommand does not accept a `--model` flag and does not thread a model name through to `FeatureOrchestrator → AutoBuildOrchestrator → AgentInvoker → LangGraphHarness`. The sibling `guardkit autobuild task` subcommand does (added by TASK-FIX-MODELPLUMB at [`guardkit/cli/autobuild.py:206-210`](../../../guardkit/cli/autobuild.py)).

With `model=None` reaching the LangGraph harness, DeepAgents instantiates its default provider (Anthropic via `langchain_anthropic`), which then demands `ANTHROPIC_API_KEY`. The operator's `OPENAI_BASE_URL` + `OPENAI_API_KEY` env vars (correct for llama-swap routing) are silently ignored because no OpenAI-style chat model is ever instantiated.

This is a **sibling-of-F1 class defect** in the canary-analysis.md naming scheme: a migration path closed for one CLI entry point (`task`, via TASK-FIX-MODELPLUMB) but not for its sibling entry point (`feature`). Same shape as F1 (pre-loop bypasses harness adapter — closed for the loop, missed for the pre-loop, until TASK-HMIG-006.4).

Recorded as **F9** in [`docs/state/TASK-REV-HMIG/feature-run-incidents.md`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md).

## Symptom

```
ERROR:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK UNEXPECTED ERROR: LangGraphHarnessError
ERROR:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Error message: LangGraphHarness:
  agent.ainvoke failed for role='player' model=None: "Could not resolve authentication method.
  Expected either api_key or auth_token to be set. Or for one of the `X-Api-Key` or
  `Authorization` headers to be explicitly omitted"
```

Full traceback: `langchain_anthropic/chat_models.py:1532` → `anthropic._base_client._build_headers` → `_validate_headers` raises `TypeError`.

## Root cause (specific code references)

`guardkit/cli/autobuild.py`:
- **Line 196–559** (`task` subcommand): has `@click.option("--model", default="claude-sonnet-4-5-20250929", ...)` at line 206 and threads it through to `AutoBuildOrchestrator` at line 555 with the comment *"TASK-FIX-MODELPLUMB: thread --model to harness construction (load-bearing for LangGraph)"*.
- **Line 646–1049** (`feature` subcommand): has NO `--model` option. The `feature()` function signature at line 813 does not include a `model` parameter. No model name flows through.

`guardkit/orchestrator/autobuild.py:1051`:
```python
# TASK-FIX-MODELPLUMB: CLI --model threaded through to AgentInvoker
# then used as default when invoke_coach / _invoke_with_role /
# specialist invocations don't specify their own model. Load-bearing
# for the LangGraph harness path (DeepAgents needs a real model
# factory; model=None fails construction with "'function' object has
# no attribute 'name'"). Decorative-but-harmless for the SDK path
# (routes via ANTHROPIC_BASE_URL).
self._model_name: Optional[str] = model
```

So `self._model_name = None` from the feature path → LangGraph harness receives None → DeepAgents picks Anthropic by default → auth fails.

## Acceptance Criteria

- [ ] AC-001: Add `@click.option("--model", default="claude-sonnet-4-5-20250929", help="Claude model to use", show_default=True)` to the `feature` subcommand in [`guardkit/cli/autobuild.py`](../../../guardkit/cli/autobuild.py) (around line 813's signature).
- [ ] AC-002: Add `model: str` parameter to the `feature()` function signature.
- [ ] AC-003: Thread the `model` value through to `FeatureOrchestrator.__init__` (add `model: Optional[str]` if it isn't there yet).
- [ ] AC-004: `FeatureOrchestrator` threads `model` through to `AutoBuildOrchestrator.__init__` (which already accepts it — see [`guardkit/orchestrator/autobuild.py:1051`](../../../guardkit/orchestrator/autobuild.py)).
- [ ] AC-005: Regression test asserts that invoking the feature subcommand with `--model qwen36-workhorse` results in `model="qwen36-workhorse"` reaching `AutoBuildOrchestrator`. Pattern: mirror the falsifier test that TASK-HMIG-006.4 added for F1 (zero `claude_agent_sdk.subprocess_cli` lines under `GUARDKIT_HARNESS=langgraph`). The equivalent here: zero `LangGraphHarnessError: ... model=None` lines when a `--model X` arg is supplied.
- [ ] AC-006: Live smoke: `GUARDKIT_HARNESS=langgraph OPENAI_BASE_URL=... OPENAI_API_KEY=... guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` reaches Player turn 1 without the auth error. Worktree state from the failed 010 run-1 may need clearing first (`guardkit autobuild feature FEAT-AOF --fresh` does this automatically, but verify `.guardkit/worktrees/FEAT-AOF` and `.guardkit/autobuild/FEAT-AOF/` are reset).

## Implementation Notes

- The fix is mechanical — the precedent (TASK-FIX-MODELPLUMB) is already in the codebase at [`guardkit/cli/autobuild.py:206`](../../../guardkit/cli/autobuild.py). Copy the option definition, parameter declaration, and propagation pattern.
- Check whether `FeatureOrchestrator.__init__` already has a `model` parameter that's just not wired to the CLI. If yes, only the CLI side needs editing. If no, add the parameter and propagate.
- The default `claude-sonnet-4-5-20250929` matches the task subcommand. Operator overrides for local-Qwen via `--model qwen36-workhorse`.
- Audit `FeatureOrchestrator` for any per-task model overrides (the task subcommand has them; the feature subcommand should too). Likely the per-task feature YAML model fields would be wired here if/when the YAML schema is extended.

## References

- Failure log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-1.md) (line 134 = the auth error)
- Sibling rule: F1 pattern in [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3.F1
- F1 fix precedent: TASK-HMIG-006.4 (commit `f2c240a7`) — added falsifier test `test_langgraph_design_phase_never_calls_sdk`
- Task subcommand precedent: TASK-FIX-MODELPLUMB at [`guardkit/cli/autobuild.py:206-555`](../../../guardkit/cli/autobuild.py)
- Orchestrator-side comment: [`guardkit/orchestrator/autobuild.py:1044-1051`](../../../guardkit/orchestrator/autobuild.py) (load-bearing nature of model threading for LangGraph)
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md) (TBD: will be in blocked/ after this task is filed)

## Notes

This finding is the kind of substrate-level gap TASK-HMIG-010 was designed to surface. Per AC-006 of HMIG-010, this is **non-recoverable** at the operator level (requires code edits to the harness/CLI path), so HMIG-010 is BLOCKED until this lands.

After this lands:
1. Re-run `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under the same env vars.
2. Resume the HMIG-010 falsifier evaluation from where it stopped (AC-002 onward).
3. The HMIG-010 wall-clock budget allows for this 1-2h delay; deadline 2026-06-15 still comfortable.
