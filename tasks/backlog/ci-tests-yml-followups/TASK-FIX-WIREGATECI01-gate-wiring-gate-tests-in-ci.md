---
id: TASK-FIX-WIREGATECI01
title: Gate the guardkitfactory-requiring wiring-gate tests in CI (close the skip coverage gap)
status: backlog
task_type: fix
created: 2026-06-17T00:00:00Z
updated: 2026-06-17T00:00:00Z
priority: medium
related: [TASK-HMIG-011, TASK-AB-WIREGATE01, TASK-INFRA-XREPOCONTRACT]
implementation_mode: task-work
tags: [ci, tests, seam, guardkitfactory, coverage-gap]
---

# Task: Gate the guardkitfactory-requiring wiring-gate tests in CI

## Why this task exists

The HMIG-011 CI-green fix (commit `4d478818`, 2026-06-17) added
`@_requires_guardkitfactory` (skipif on `find_spec("guardkitfactory")`) to the
**7 `TestRunPostWaveWiringGate` tests** in
`tests/unit/orchestrator/test_wiring_gate.py` and the **2 langgraph dispatch
tests** in `tests/orchestrator/harness/test_selector.py`. They patch / construct
guardkitfactory symbols, which `tests.yml` cannot import (it deliberately omits
guardkitfactory + the langchain stack). The skip was the correct way to green
`tests.yml`.

**The gap:** those skipped tests now run in **no CI job**. `seam-tests.yml` runs
an *explicit file list* (`test_xrepo_contract_seam.py`,
`test_bdd_xrepo_contract_seam.py`) that does **not** include `test_wiring_gate.py`.
The selector dimension is fine — its production-relevant claim (real
`LangGraphHarness` construction + `model=` threading) is already gated by
`test_xrepo_contract_seam.py::test_langgraph_constructed_end_to_end_with_real_kwargs`.
But the **7 wiring-gate orchestration tests** verify guardkit-OWNED wave-loop
disposition logic (feedback-retry, replace-not-append, advisory-after-budget,
stop-on-failure) that is now unit-tested **only on developer machines**.

(Adversarial review of the CI-green fix flagged this as the one substantive
follow-up; verdict was otherwise `fix-is-sound`.)

## Acceptance criteria

- [ ] **AC-001 — import-chain check (blocking precondition):** confirm
  `tests/unit/orchestrator/test_wiring_gate.py` (which imports
  `guardkit.orchestrator.feature_orchestrator.FeatureOrchestrator`) does NOT
  `import claude_agent_sdk` at collection time. `seam-tests.yml` installs editable
  guardkitfactory + langchain but **deliberately NOT** `claude-agent-sdk`, and the
  job uses an explicit file list precisely because some modules import the SDK at
  collection. If the wiring-gate import chain pulls the SDK, either (a) add
  `claude-agent-sdk` to the seam job's install, or (b) make the SDK import lazy /
  guarded — document which and why.
- [ ] **AC-002 — gate it:** add `tests/unit/orchestrator/test_wiring_gate.py` to the
  explicit `python -m pytest ...` file list in `.github/workflows/seam-tests.yml`.
  With editable guardkitfactory present there, the 7 `@_requires_guardkitfactory`
  tests un-skip and run.
- [ ] **AC-003 — green:** the seam job stays green (the 7 tests pass with
  guardkitfactory installed — verified locally during the CI-green fix).
- [ ] **AC-004 — do NOT regress seam:** do **not** naively add
  `tests/orchestrator/test_agent_invoker_langgraph.py` to the seam job — it has a
  pre-existing `test_env_var_routes_to_langgraph` "no `cwd=`" failure and is
  `importorskip("langchain_core")`-gated, so it WOULD run under seam and turn it
  red. Track/fix that separately (see Notes).

## Notes

- The pre-existing `test_agent_invoker_langgraph.py::test_env_var_routes_to_langgraph`
  "no cwd" red is called out in the 2026-06-16 handoff doc as a deferred
  pre-existing failure; gate it only after that node is fixed or deselected.
- Background on the CI substrate contract:
  `.github/workflows/tests.yml` (no guardkitfactory/langchain) vs
  `seam-tests.yml` (sibling-repo checkout + editable install). Originating
  commits: `4d478818` (the skips), `4831563a` (flaky-test follow-up).
- Sibling rule family: `.claude/rules/harness-cancellation-contract.md`,
  `evidence-boundary-narrower-than-write-surface.md` — the cross-repo seam CI
  enforcement these tests belong to.
