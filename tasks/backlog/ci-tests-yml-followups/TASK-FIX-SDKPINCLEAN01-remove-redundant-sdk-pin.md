---
id: TASK-FIX-SDKPINCLEAN01
title: Remove now-redundant per-test GUARDKIT_HARNESS=sdk pin in test_sdk_environment_parity
status: backlog
task_type: fix
created: 2026-06-17T00:00:00Z
updated: 2026-06-17T00:00:00Z
priority: low
related: [TASK-HMIG-011]
implementation_mode: task-work
tags: [ci, tests, cleanup, tech-debt]
---

# Task: Remove the redundant per-test sdk pin

## Why this task exists

The HMIG-011 CI-green fix (commit `4d478818`) added a **module-level autouse**
fixture `_pin_sdk_harness` to `tests/unit/test_sdk_environment_parity.py`, which
pins `GUARDKIT_HARNESS=sdk` for every test in the module. That makes the
pre-existing **per-test** `monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")` inside
`TestRunIndependentTestsSdkFallback::test_sdk_first_dispatch` (≈ line 380)
redundant / dead. Harmless (both pin the same value) but untidy; the adversarial
review flagged it.

## Acceptance criteria

- [ ] **AC-001:** remove the now-redundant
  `monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")` line from
  `test_sdk_first_dispatch` (the module autouse fixture already pins it).
- [ ] **AC-002:** keep the `monkeypatch` fixture parameter if the test still uses
  it for other `setenv`/`setattr`/`setitem` calls; drop it only if fully unused.
- [ ] **AC-003:** `test_sdk_first_dispatch` (and the full
  `test_sdk_environment_parity.py` module) still pass.

## Notes

- Purely cosmetic; bundle into any nearby test-hygiene pass. No production code.
- Context: `.github/workflows/tests.yml` runs without guardkitfactory/langchain,
  so SDK-path tests are pinned to the sdk substrate (the module autouse fixture).
