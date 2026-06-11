---
id: TASK-INFRA-XREPOCONTRACT
title: CI smoke-test for the guardkit↔guardkitfactory harness contract boundary
status: completed
task_type: feature
created: 2026-06-10T00:00:00Z
updated: 2026-06-11T00:00:00Z
completed: 2026-06-11T00:00:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs met; seam test green (15 passed, 0.38s); CI workflow added; design rules cross-linked"
completed_location: tasks/completed/autobuild-harness-migration/
priority: high
complexity: 4
parent_task: TASK-HMIG-010
related: [TASK-FIX-BACKENDKWARG, TASK-FIX-MAXPARALLEL01, TASK-FIX-CTOUT01, TASK-HMIG-006]
implementation_mode: task-work
tags: [autobuild, harness, cross-repo, ci, contract]
---

# Task: CI smoke-test for the guardkit↔guardkitfactory harness contract

## Why this task exists

Cross-repo contract drift between guardkit (orchestrator) and guardkitfactory
(LangGraph harness/backend) keeps costing a **full run to discover**, because
unit tests **mock guardkitfactory** and never exercise the real call
signatures. The recurrences:

- **Run-24**: `selector.py` passes `max_tool_result_chars` to
  `build_autobuild_backend()`, which doesn't accept it → TypeError on every SDK
  invocation, 25s crash (TASK-FIX-BACKENDKWARG).
- The **F1/F9/F10/F12/F19** model-threading family (HMIG): `model=` not threaded
  at every call site of the migrated harness boundary.
- **TASK-FIX-CTOUT01** cancel-asymmetry: a new substrate's `cancel()` not honoured.

The run-23 retro's recommendation #5 named this exactly: *"audit ALL invocation
sites of a migrated contract boundary"* + a CI check. This task builds it.

## The fix

A **cross-repo integration smoke-test** (runnable in CI against the pinned
guardkitfactory) that exercises the real harness/backend construction + the
substrate contract — NOT mocks:

1. **Construct the LangGraph harness end-to-end** via the real `select_harness`
   path with `GUARDKIT_HARNESS=langgraph`, passing the **exact kwargs the
   selector actually forwards** (incl. `max_tool_result_chars`, `cwd`, `model`,
   permissions/backend). A signature mismatch fails here, in seconds, in CI.
2. **Assert the substrate contract** each `HarnessAdapter` must satisfy: it
   implements `invoke`, `invoke_synthesis`, and `cancel`; `model=` is threaded;
   `invoke`/`invoke_synthesis` are async generators yielding the
   `HarnessEvent` taxonomy. (Codify the `harness-cancellation-contract.md` grep
   signature as a test.)
3. **Pin the contract**: the test imports `build_autobuild_backend` /
   `LangGraphHarness` from the *installed* guardkitfactory and checks the
   parameters the orchestrator depends on are present
   (`inspect.signature`), so a version skew is a red CI build, not a runtime
   25s crash.

Keep it fast and dependency-light (construction + signature assertions; mock the
actual LLM endpoint so no GB10 is needed). Mark `@pytest.mark.integration` /
`seam` so it runs in CI but is skippable locally without the langchain stack.

## Acceptance criteria

- [x] **AC-1**: a CI-runnable test constructs the real LangGraph harness +
  backend through `select_harness` with the selector's actual kwargs; a kwarg the
  factory doesn't accept fails the test (reproduce the run-24 TypeError class).
  → `TestRealConstructionThroughSelector` in
  `tests/orchestrator/harness/test_xrepo_contract_seam.py`; `_real_selector_kwargs`
  mirrors `agent_invoker.py:3586-3612`. `test_unknown_kwarg_surfaces_as_typeerror`
  pins the run-24 TypeError class.
- [x] **AC-2**: the test asserts every `HarnessAdapter` substrate implements
  `invoke`, `invoke_synthesis`, `cancel` and threads `model=` — a new substrate
  missing one fails CI (codifies the cancellation-contract + model-threading
  rules).
  → `TestSubstrateContract` walks `HarnessAdapter.__subclasses__()`;
  `test_cancel_is_overridden_not_abc_noop` codifies the `rg "async def cancel"`
  signature; `test_model_is_threaded_into_constructor` covers F1/F9/F10/F12/F19.
- [x] **AC-3 (signature pin)**: the test verifies, via `inspect.signature`, that
  `build_autobuild_backend` / harness constructors accept the parameters the
  orchestrator passes — guardkit↔guardkitfactory version skew → red CI.
  → `TestSignaturePin` (backend `max_tool_result_chars`, `LangGraphHarness.__init__`
  model/backend/permissions/recursion_limit, `invoke` param names).
- [x] **AC-4**: the test is fast (<~10s), needs no live LLM/GB10 (endpoint
  mocked), and is wired into the CI job that gates merges.
  → 15 tests in 0.39s, no LLM hit (string model stored, never invoked).
  `.github/workflows/seam-tests.yml` checks out the sibling guardkitfactory repo,
  installs both, runs the seam module on `pull_request`/`push` to `main`.
  `importorskip` makes it skip cleanly in a bare guardkit venv.
- [x] **AC-5**: documented in the test module + cross-linked from
  `harness-cancellation-contract.md` / `namespace-hygiene.md` as the enforcement
  for the migrated-contract-boundary meta-rule.
  → module docstring + "CI enforcement" / sibling-rule notes added to both rules.

## Notes

- This is the **durable class fix**; TASK-FIX-BACKENDKWARG is the acute instance.
- Meta-frame: the harness migration is a migrated contract boundary; every such
  boundary needs all invocation sites audited + a CI guard (retro rec #5).
- Sibling design rules: `harness-cancellation-contract.md`, `namespace-hygiene.md`
  (both are "local decision touching an externally-defined contract").
