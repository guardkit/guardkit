---
id: TASK-FIX-SDKPINCLEAN01
title: Remove now-redundant per-test GUARDKIT_HARNESS=sdk pin in test_sdk_environment_parity
status: completed
task_type: fix
created: 2026-06-17T00:00:00Z
updated: 2026-06-18T00:00:00Z
completed: 2026-06-18T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-SDKPINCLEAN01/
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

- [x] **AC-001:** remove the now-redundant
  `monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")` line from
  `test_sdk_first_dispatch` (the module autouse fixture already pins it).
- [x] **AC-002:** keep the `monkeypatch` fixture parameter if the test still uses
  it for other `setenv`/`setattr`/`setitem` calls; drop it only if fully unused.
  → `monkeypatch` was used *only* for that one pin, so the parameter was dropped
  from the test signature.
- [x] **AC-003:** `test_sdk_first_dispatch` (and the full
  `test_sdk_environment_parity.py` module) still pass — verified
  `19 passed, 6 skipped` under `GUARDKIT_HARNESS=sdk`.

## Notes

- Purely cosmetic; bundle into any nearby test-hygiene pass. No production code.
- Context: `.github/workflows/tests.yml` runs without guardkitfactory/langchain,
  so SDK-path tests are pinned to the sdk substrate (the module autouse fixture).
