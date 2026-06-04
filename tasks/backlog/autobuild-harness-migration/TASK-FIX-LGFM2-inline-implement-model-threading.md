---
id: TASK-FIX-LGFM2
title: Thread `_model_name` to `select_harness` in `_invoke_task_work_implement`
status: backlog
task_type: bug
created: 2026-06-04T21:00:00Z
updated: 2026-06-04T21:00:00Z
priority: critical
complexity: 2
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 0.5
blocks:
  - TASK-HMIG-010
falsifier: "After landing, run 3 of `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` under GUARDKIT_HARNESS=langgraph shows `model='openai:qwen36-workhorse'` (not `model=None`) at every harness invocation site, including the main inline-implement Player path. A regression test asserts that AgentInvoker._invoke_task_work_implement constructs the harness with model=self._model_name when self._model_name is non-None."
tags:
  - autobuild
  - langgraph-migration
  - bugfix
  - sibling-of-f9
---

# Task: Thread `_model_name` to `select_harness` in `_invoke_task_work_implement`

## Description

Surfaced by TASK-HMIG-010 run 2 (2026-06-04T19:33, see [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md)). After TASK-FIX-LGFM (commit `683823cc`) threaded `--model` from the CLI through `FeatureOrchestrator → AutoBuildOrchestrator → AgentInvoker._model_name`, run 2 still failed at Player turn 1 with the same `LangGraphHarnessError: ... model=None: "Could not resolve authentication method..."` shape.

Root cause: `AgentInvoker` has **two** `select_harness()` call sites. TASK-FIX-MODELPLUMB added the model threading to one of them but not the other.

| Site | Path | model passed to select_harness? |
|---|---|---|
| [`agent_invoker.py:2855`](../../../guardkit/orchestrator/agent_invoker.py) (in `_invoke_with_role`) | Coach + specialist invocations | ✅ YES — `model=model` with `_model_name` fallback at line 2847 |
| [`agent_invoker.py:5730`](../../../guardkit/orchestrator/agent_invoker.py) (in `_invoke_task_work_implement`) | Main inline-implement Player | ❌ NO — `select_harness(...)` called with no `model=` kwarg |

This explains run-2's split signature:
- Line 139 (main Player via `_invoke_task_work_implement`): `model=None` → Anthropic auth fail
- Line 350 (test-orchestrator specialist via `run_specialist → _invoke_with_role`): `model='openai:qwen36-workhorse'` → routes to llama-swap correctly

This is **sibling-of-F9** (which was itself sibling-of-F1). Same class-of-defect: a migration path closed for some entry points but missed for others. F1 was Player-Coach-loop vs pre-loop. F9 was task vs feature CLI subcommand. F10 is `_invoke_with_role` vs `_invoke_task_work_implement` inside the AgentInvoker.

Recorded as **F10** in [`docs/state/TASK-REV-HMIG/feature-run-incidents.md`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md).

## Symptom

```
ERROR:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK UNEXPECTED ERROR: LangGraphHarnessError
ERROR:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Error message: LangGraphHarness:
  agent.ainvoke failed for role='player' model=None: "Could not resolve authentication method..."
```

Identical to F9's symptom because the root mechanism is identical (model=None → DeepAgents picks Anthropic provider → Anthropic auth fail).

## Root cause (specific code references)

[`guardkit/orchestrator/agent_invoker.py:5730-5751`](../../../guardkit/orchestrator/agent_invoker.py):

```python
harness = select_harness(
    sdk_timeout_seconds=self.sdk_timeout_seconds,
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
    permission_mode="acceptEdits",
    max_turns=effective_max_turns,
    resume_session_id=self._last_session_id,
    sdk_debug_dir=_sdk_debug_dir,
    cleanup_handler_installer=_install_sdk_cleanup_handler,
    setting_sources=["project"],
    cwd=self.worktree_path,
    # ← MISSING: model=self._model_name,
)
```

Compare to [`agent_invoker.py:2855-2875`](../../../guardkit/orchestrator/agent_invoker.py) (the working `_invoke_with_role` path):

```python
if model is None:
    model = self._model_name   # ← MODELPLUMB fallback

harness = select_harness(
    ...
    model=model,                # ← The line that's missing in the other site
    ...
)
```

## Acceptance Criteria

- [ ] AC-001: Add `model=self._model_name,` to the `select_harness(...)` call at [`agent_invoker.py:5730`](../../../guardkit/orchestrator/agent_invoker.py) (between `setting_sources` and `cwd` to match the kwarg ordering in the working site).
- [ ] AC-002: Add a unit-test regression mirroring the LGFM tests: assert that when `AgentInvoker(model_name="qwen36-workhorse")` invokes `_invoke_task_work_implement`, the harness is constructed with `model="qwen36-workhorse"`.
- [ ] AC-003: Live smoke (HMIG-010 run 3): `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse` reaches the main Player's `harness.invoke` with `model='openai:qwen36-workhorse'` (not None). Failure mode shifts to F11 (next layer) or substrate-quality findings.

## Implementation Notes

- This is the simplest possible fix — copy the kwarg from line 2863. Total diff is a single line plus a regression test.
- Do NOT add the `if model is None: model = self._model_name` fallback at this site — the main Player path has no per-call model override, so direct `model=self._model_name` is sufficient and cleaner.
- After this lands, expect run 3 to fire **F11** (DeepAgents conversation history offload to read-only `/conversation_history/` root path). That's [TASK-FIX-CHO01](TASK-FIX-CHO01-deepagents-conversation-history-offload-path.md), parallel sibling blocker.

## References

- Run-2 failure log: [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-2.md) (lines 139, 350)
- LGFM (the predecessor fix): commit `683823cc` (TASK-FIX-LGFM), `tasks/completed/`
- MODELPLUMB (the original fallback pattern): [`agent_invoker.py:2840-2847`](../../../guardkit/orchestrator/agent_invoker.py)
- F1 sibling: [`canary-analysis.md §3.F1`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
- F9 sibling: [`feature-run-incidents.md I-001`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md)
- Blocked task: [TASK-HMIG-010](../../in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Sibling blocker: [TASK-FIX-CHO01](TASK-FIX-CHO01-deepagents-conversation-history-offload-path.md)

## Notes

The recurring shape suggests a **broader systemic rule** worth seeding into `.claude/rules/`: *when a migration moves a contract behind a substrate boundary, audit ALL invocation sites of the boundary, not just the ones the migration's stated scope covers.* F1 missed pre-loop; F9 missed feature subcommand; F10 missed inline-implement. Three instances. Worth a rule.
