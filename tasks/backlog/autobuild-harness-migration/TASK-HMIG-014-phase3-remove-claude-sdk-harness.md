---
id: TASK-HMIG-014
title: Phase 3 — remove ClaudeSDKHarness + claude-agent-sdk dependency from guardkit (OPTIONAL cleanup)
task_type: refactor
status: backlog
created: 2026-06-18T15:30:00Z
updated: 2026-06-18T15:30:00Z
priority: low
complexity: 4
parent_task: TASK-HMIG-011
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
tags:
  - autobuild
  - langgraph-migration
  - dependency-cleanup
  - optional
effort_hours: 4
falsifier: >
  After this task, guardkit no longer imports ClaudeSDKHarness and the
  claude-agent-sdk dependency is removed from pyproject/requirements, AND the
  autobuild suite is still green on the LangGraph default. If any SDK-path code
  or the claude-agent-sdk dep still exists in guardkit, the task is not done.
  NOTE: this task is OPTIONAL — see "Why optional" — and MUST NOT be started
  while any consumer still relies on `GUARDKIT_HARNESS=sdk`.
---

# Task: Phase 3 — remove the Claude Agent SDK harness from guardkit (optional)

## Provenance

Post-cutover follow-up filed by **TASK-HMIG-011 AC-008** (LangGraph cutover
ceremony, completed 2026-06-18). The parent review §7.5 deferred Claude Code
dependency removal to "post-2026-06-15 as Phase 3"; this is that task.

The `TASK-HMIG-012` slot named in HMIG-011's "Post-cutover follow-ups" was
already taken (Stage-2 substrate investigation), so this is filed as
`TASK-HMIG-014` (`-013` is the gemma4-26b coach swap).

## Why optional (read before starting)

The flip to the LangGraph default (TASK-HMIG-011, 2026-06-16) kept the SDK
adapter **in-repo as a free emergency-revert path** (`GUARDKIT_HARNESS=sdk`).
The original driver for *removing* it — the Anthropic API-key validation cutoff
(originally 2026-06-15) that would have broken the SDK path for local-model use —
**was cancelled**. So the SDK fallback now costs only ~250 LOC of maintenance and
buys genuine revert optionality. Removal is a **cleanup, not a deadline item**.

**Do NOT start this task while any consumer still pins `GUARDKIT_HARNESS=sdk`.**
Removing the adapter is irreversible-ish (revert optionality is the whole point
of keeping it). Confirm no active SDK-path reliance first.

## Scope (when/if undertaken)

- Remove `ClaudeSDKHarness` and the `_invoke_with_role` SDK body (~250 LOC).
- Remove the `claude-agent-sdk` dependency from `pyproject.toml` /
  `requirements*.txt` / the `[autobuild]` extra.
- Collapse `selector.py` to LangGraph-only (drop the `"sdk"` branch +
  `DEFAULT_HARNESS` becomes moot, or assert langgraph).
- Update / delete the SDK-path tests that opt into `GUARDKIT_HARNESS=sdk`
  (selector, coach-timeout, sdk-session-config, task-work-interface,
  generator-close, sdk-environment-parity, agent-invoker lazy-import) and the
  cross-repo seam test's SDK-substrate assertions.
- Update docs (CLAUDE.md AutoBuild section, `selector.py` docstring) to drop the
  opt-back-to-SDK guidance and the rollback-to-sdk procedure.

## Acceptance Criteria

- [ ] **AC-001** — Pre-flight: confirm no consumer (jarvis / forge /
  dataset-factory / local recipes) still sets `GUARDKIT_HARNESS=sdk`. If any
  does, STOP and escalate — do not remove the fallback.
- [ ] **AC-002** — `ClaudeSDKHarness` + the SDK `_invoke_with_role` body removed;
  `rg "ClaudeSDKHarness|claude_agent_sdk" guardkit/` returns no production hits.
- [ ] **AC-003** — `claude-agent-sdk` removed from `pyproject.toml` /
  `requirements*.txt` / extras; a fresh install no longer pulls it.
- [ ] **AC-004** — `selector.py` simplified to LangGraph-only; the cross-repo
  seam test (`tests/orchestrator/harness/test_xrepo_contract_seam.py`) updated so
  it no longer asserts an SDK substrate.
- [ ] **AC-005** — Autobuild suite green on the LangGraph default; docs updated
  (drop opt-back-to-SDK + rollback-to-sdk).

## References

- Parent: [`TASK-HMIG-011`](./TASK-HMIG-011-cutover-ceremony-flip-default-harness.md)
  ("Post-cutover follow-ups" + "Out of scope" §); parent review TASK-REV-HMIG §7.5.
- Flip point / rollback: `guardkit/orchestrator/harness/selector.py:49`
  (`DEFAULT_HARNESS`).
- Other post-cutover follow-ups (NOT this task): F6 substrate Player-honesty
  mitigation; TASK-HMIG-002R-PERMS restoration; TASK-HMIG-009B optional 18-rep
  canary; ADR-ARCH-031 / -032 drafting — all enumerated in HMIG-011.
