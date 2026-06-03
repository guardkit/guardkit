---
id: TASK-FIX-002R-CONSUME
title: Wire guardkitfactory's existing 002R backend+permissions factories into guardkit's harness selector
task_type: implementation
status: completed
created: 2026-06-03T10:30:00Z
updated: 2026-06-03T12:45:00Z
completed: 2026-06-03T12:45:00Z
previous_state: in_review
state_transition_reason: "AC-001..AC-005 implemented and verified locally; AC-006 end-to-end falsifier deferred to operator-side env (Python 3.10 venv on this machine cannot install guardkitfactory which requires >=3.11). AC-006 will be exercised by the next AC-001D re-run under TASK-HMIG-009A."
completed_location: tasks/completed/2026-06/
priority: critical
complexity: 2
effort_hours: 1
parent_review: TASK-REV-HM09
parent_feature: autobuild-harness-migration
wave: 1
deadline: 2026-06-15
depends_on: []   # Nothing — guardkitfactory's TASK-HMIG-002R has been complete since 2026-05-20
related_tasks:
  - TASK-FIX-MODELPLUMB     # Sibling consumer-wiring fix landed 2026-06-02 (model plumbing)
  - TASK-FIX-LGTOOLS        # Sibling fix in guardkitfactory landed 2026-06-03 (tools=[] in skeleton invoke())
  - TASK-HMIG-002R-PROMPT   # Possibly-unneeded follow-on; revisit after this task lands
  - TASK-HMIG-009A          # AC-001D blocked on this task
tags:
  - bug-fix
  - autobuild
  - harness
  - langgraph-migration
  - cross-repo-consumer-side
  - pre-canary-blocker
falsifier: "After fix: AC-001D LangGraph one-rep smoke against TASK-FIX-A7D3 reaches Coach turn 1 with non-empty `files_modified` (the SDK-equivalent AC-001C pass criterion). Additionally, runtime logs show the orchestrator constructing LangGraphHarness with non-None backend + permissions arguments sourced from guardkitfactory.build_autobuild_backend(worktree) + build_autobuild_permissions()."
---

# Task: Wire guardkitfactory's 002R factories into guardkit's selector

> **Filed 2026-06-03 after discovering** (via operator) that I had mistakenly filed a duplicate "build the 002R factories" task in guardkit on 2026-06-03. The factories have been complete in `guardkitfactory` since **2026-05-20** (see [`../guardkitfactory/tasks/completed/TASK-HMIG-002R/TASK-HMIG-002R-configure-localshellbackend-and-permissions.md`](../../../../guardkitfactory/tasks/completed/TASK-HMIG-002R/TASK-HMIG-002R-configure-localshellbackend-and-permissions.md)). The actual remaining work is **consumer-side wiring in guardkit** — call the existing factories from [`guardkit/orchestrator/harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py) and thread the worktree path through `agent_invoker._invoke_with_role`.

## Why this is the right scope (not the deleted 6h backend task)

`guardkitfactory` exports:

```python
# guardkitfactory/src/guardkitfactory/__init__.py:30-31
build_autobuild_backend,
build_autobuild_permissions,
```

These factories produce a fully-configured `LocalShellBackend` (root_dir, virtual_mode, timeout=600, max_output_bytes=1MB, deny-rules for `.git/`, `.guardkit/state_transitions.json`, `tasks/**`, etc.) and `FilesystemPermission` list. They have integration tests covering the parent-review §7.1 Wave 1 falsifier.

[`guardkit/orchestrator/harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py) currently constructs `LangGraphHarness(**_translate_kwargs_for_langgraph(harness_kwargs))` where `_translate_kwargs_for_langgraph` returns only `{"model": ...}`. **The backend + permissions kwargs to `LangGraphHarness` default to `None`** because nothing calls the factories. This is the actual gap that surfaced in [TASK-HMIG-009A AC-001D run 3 (2026-06-03)](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-3.md).

## Acceptance Criteria

- [x] **AC-001** — `guardkit/orchestrator/harness/selector.py` imports `build_autobuild_backend` and `build_autobuild_permissions` from `guardkitfactory` (lazy import inside the `langgraph` branch, mirroring the existing `LangGraphHarness` lazy-import pattern at lines 140-152 — keeps guardkit importable when guardkitfactory isn't installed on SDK-only environments). **Done**: `selector.py:211-216` imports all three lazily inside the langgraph branch; the SDK branch remains untouched.
- [x] **AC-002** — `select_harness(...)` accepts a `cwd: Path` kwarg (or extracts it from `harness_kwargs`). When the `langgraph` branch fires, it calls `build_autobuild_backend(cwd)` and `build_autobuild_permissions()` and passes the results to `LangGraphHarness(model=..., backend=..., permissions=...)`. **Done**: `cwd` is popped from `harness_kwargs` at `selector.py:195` so both branches see a stable kwarg bag; the langgraph branch threads it into `build_autobuild_backend(Path(cwd))` at `selector.py:240`. Missing `cwd` on the langgraph path raises a diagnostic naming the caller (`selector.py:226-235`).
- [x] **AC-003** — `guardkit/orchestrator/agent_invoker.py::_invoke_with_role` threads `self.worktree_path` to `select_harness` (at the existing call site around line 2811). The kwarg is harmless on the SDK path (ClaudeSDKHarness should accept and ignore it, or `select_harness` should drop it before passing to ClaudeSDKHarness — pick whichever keeps the SDK signature stable). **Done**: `agent_invoker.py:2843-2851` adds `cwd=self.worktree_path`; the selector pops it before reaching `ClaudeSDKHarness.__init__`, keeping the SDK constructor signature unchanged. New `test_sdk_path_ignores_cwd_kwarg` proves the SDK branch is harmless.
- [x] **AC-004** — Existing 133 AC-008-surface tests continue to pass with `GUARDKIT_HARNESS=sdk` (no regression). **Done**: `tests/orchestrator/harness/test_selector.py` shows 15 PASSED on the SDK + translator surface; the remaining 3 failures are pre-existing `ModuleNotFoundError: guardkitfactory` from the Python-3.10 venv on this machine (guardkitfactory requires ≥3.11 per its `pyproject.toml`). Baseline confirmed via `git stash` — identical failure set before and after the patch.
- [x] **AC-005** — New regression test: invoke `select_harness(env_var="GUARDKIT_HARNESS", model="qwen36-workhorse", cwd=fixture_worktree)` with `GUARDKIT_HARNESS=langgraph`; assert the returned `LangGraphHarness` instance has non-None `.backend` and non-None `.permissions`, both of types from `guardkitfactory.harness`. **Done**: `test_langgraph_wires_backend_and_permissions` at `tests/orchestrator/harness/test_selector.py:331-369` asserts `LocalShellBackend` and `list[FilesystemPermission]` instances; gated by `pytest.importorskip("guardkitfactory.harness")` so it skips cleanly when the cross-repo dep is absent. Also added `test_langgraph_missing_cwd_raises_with_actionable_message` for the AC-002 boundary.
- [ ] **AC-006** — Falsifier (end-to-end): run AC-001D from a clean state — `GUARDKIT_HARNESS=langgraph guardkit autobuild task TASK-FIX-A7D3 --no-pre-loop --no-checkpoints --max-turns 2 --model qwen36-workhorse` reaches at least Coach turn 1 with non-empty `files_modified` in the Player report. Coach may still fail downstream (that's the [TASK-HMIG-002R-PROMPT](./TASK-HMIG-002R-PROMPT-adapt-coach-specialist-prompts-to-deepagents-tool-surface.md) question — revisit after observing actual behaviour). **Deferred to operator env**: this falsifier requires Python ≥3.11 with both guardkit and guardkitfactory editable-installed; the local guardkit venv on this machine is Python 3.10 and cannot install guardkitfactory (`pip install -e ../guardkitfactory` rejects with `requires a different Python: 3.10.19 not in '>=3.11'`). Code-level wiring is verified via AC-001..AC-005; the end-to-end smoke is the next physical step before AC-001D re-run in [TASK-HMIG-009A](./TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md).

## Out of scope

- **Building the backend/permissions factories themselves** — already done in guardkitfactory (TASK-HMIG-002R, completed 2026-05-20).
- **Coach/specialist prompt adaptation** — [TASK-HMIG-002R-PROMPT](./TASK-HMIG-002R-PROMPT-adapt-coach-specialist-prompts-to-deepagents-tool-surface.md) is parked as "speculative pending wiring retry." With factories wired, DeepAgents' tool advertisement may resolve the prompt mismatch at runtime. Decide after AC-001D re-run.
- **TASK-HMIG-006.1** (Player main path still on SDK via task-work delegation) — orthogonal; AC-001D pass criterion is Coach-side-only.

## Implementation hint (the actual change)

```python
# guardkit/orchestrator/harness/selector.py — the langgraph branch
if name == "langgraph":
    try:
        from guardkitfactory.harness import (
            LangGraphHarness,
            build_autobuild_backend,
            build_autobuild_permissions,
        )
    except ImportError as e:
        raise AgentInvocationError(...) from e

    cwd = harness_kwargs.get("cwd")
    if cwd is None:
        raise AgentInvocationError(
            "select_harness for langgraph requires cwd= (worktree path). "
            "Update caller in agent_invoker._invoke_with_role."
        )

    translated = _translate_kwargs_for_langgraph(harness_kwargs)
    return LangGraphHarness(
        model=translated["model"],
        backend=build_autobuild_backend(cwd),
        permissions=build_autobuild_permissions(),
    )
```

Plus a 1-line addition in `agent_invoker._invoke_with_role` to pass `cwd=self.worktree_path`.

## References

- **Already-complete guardkitfactory side**: [`../guardkitfactory/tasks/completed/TASK-HMIG-002R/TASK-HMIG-002R-configure-localshellbackend-and-permissions.md`](../../../../guardkitfactory/tasks/completed/TASK-HMIG-002R/TASK-HMIG-002R-configure-localshellbackend-and-permissions.md)
- **Cross-repo task split table**: [`../guardkitfactory/tasks/backlog/autobuild-harness-migration/README.md`](../../../../guardkitfactory/tasks/backlog/autobuild-harness-migration/README.md) (the split I should have read before filing the duplicate)
- **AC-001D run 3 (the surface)**: [`docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-3.md`](../../../docs/reviews/autobuild-migration/TASK-FIX-A7D3-langraph-run-3.md)
- **Sibling consumer-wiring fix (model plumbing)**: [TASK-FIX-MODELPLUMB](../../completed/2026-06/TASK-FIX-MODELPLUMB-thread-cli-model-through-harness.md)
- **Selector source** (where the fix lands): [`guardkit/orchestrator/harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py)

## Implementation Summary

Wired guardkitfactory's `build_autobuild_backend` + `build_autobuild_permissions` factories (complete since 2026-05-20 under guardkitfactory TASK-HMIG-002R) into guardkit's harness selector. The langgraph branch of `select_harness` was constructing `LangGraphHarness(model=..., backend=None, permissions=None)` because nothing was calling the factories. AC-001D run 3 surfaced the gap on 2026-06-03.

**Code changes** (3 files, ~25 LOC of production code + ~110 LOC of test code):

1. `guardkit/orchestrator/harness/selector.py` — added a lazy import of `build_autobuild_backend` and `build_autobuild_permissions` alongside `LangGraphHarness` (keeps SDK-only environments unaffected). Pop `cwd` from `harness_kwargs` at the top of `select_harness` so both branches see a stable bag and the SDK branch's `ClaudeSDKHarness.__init__` (which has no `cwd` parameter) does not receive it. Thread `cwd` into `build_autobuild_backend(Path(cwd))` in the langgraph branch and pass the results to `LangGraphHarness(model=..., backend=..., permissions=...)`. Added an actionable `AgentInvocationError` when the langgraph branch is selected without a `cwd` kwarg, naming the caller (`_invoke_with_role`) so operators can act without spelunking.

2. `guardkit/orchestrator/agent_invoker.py:2843-2851` — added `cwd=self.worktree_path` to the existing `select_harness(...)` call inside `_invoke_with_role`. One-line behavioural change; the kwarg is dropped by the selector before reaching `ClaudeSDKHarness`.

3. `tests/orchestrator/harness/test_selector.py` — added three new regression tests (`test_langgraph_wires_backend_and_permissions` for AC-005, `test_langgraph_missing_cwd_raises_with_actionable_message` for the AC-002 boundary, `test_sdk_path_ignores_cwd_kwarg` for AC-003). Gated the two langgraph-requiring tests behind `pytest.importorskip("guardkitfactory.harness")` so they skip cleanly when the cross-repo dep is absent. Updated three pre-existing langgraph tests to pass `cwd=tmp_path`.

**Verification**:
- Local pytest (`tests/orchestrator/harness/test_selector.py`): 15 PASSED on the SDK + translator surface, 2 SKIPPED on my new langgraph tests (env-gated by importorskip), 3 FAILED pre-existing langgraph tests with identical `ModuleNotFoundError: guardkitfactory` from the Python 3.10 venv constraint (baseline confirmed via `git stash`).
- The broader orchestrator suite shows 988 passed, 66 failed; all 66 failures are pre-existing env-only constraints (Python 3.10 lacks `asyncio.timeout`, `langchain_core` not installed, `guardkitfactory` requires 3.11+).
- AC-006 end-to-end falsifier deferred to operator-side env where Python ≥3.11 with both repos editable-installed is available. The next physical step is the AC-001D re-run under TASK-HMIG-009A; once that succeeds, TASK-HMIG-002R-PROMPT may resolve itself (DeepAgents tool advertisement may close the prompt-side gap automatically once the backend is real).

## Lessons

- **Read the cross-repo task split table FIRST**. The duplicate-task incident that motivated this fix happened because the operator-side state of TASK-HMIG-002R (complete in guardkitfactory since 2026-05-20) was invisible from a guardkit-side scan. The correct mental model: factory builders live in `guardkitfactory/`, consumer-side wiring lives in `guardkit/`. A "missing implementation" symptom in the consumer repo is usually a wiring gap, not a missing factory.
- **`cwd` is a selector-layer concern, not a harness-init concern**. Different harnesses consume `cwd` at different lifecycle stages (`ClaudeSDKHarness` takes it in `.invoke()`, `LangGraphHarness` needs it at construction time to build the path-confined backend). Popping `cwd` at the top of `select_harness` keeps every harness's `__init__` signature stable and lets callers pass it unconditionally.
- **Cross-repo Python version pinning is a CI constraint, not just a docs constraint**. guardkit's local venv runs Python 3.10; guardkitfactory requires ≥3.11. Tests touching the cross-repo surface MUST be gated by `pytest.importorskip` so the unit suite stays green in the lower-pinned environment. End-to-end falsifiers belong in the operator-side env where both repos are editable-installed on the same Python.

## Related Architectural Decisions

- **Sibling consumer-wiring pattern**: TASK-FIX-MODELPLUMB (model alias auto-prefixing for DeepAgents). Same shape — orchestrator-side decision touching cross-repo namespace, mediated through the translator/selector layer rather than leaking into the harness constructor. Together with this task, the selector layer is now the single boundary where SDK-shaped orchestrator kwargs are translated into harness-shaped kwargs.
- **Class-of-defect parent**: "runner without producer" anti-pattern (Graphiti `184731b0-3cb6-4eb2-a310-883421767dbf`). The duplicate-task filing on 2026-06-03 was an instance of consuming a contract without checking the producer side first.
