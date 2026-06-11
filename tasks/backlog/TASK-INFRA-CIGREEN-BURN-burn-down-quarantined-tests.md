---
id: TASK-INFRA-CIGREEN-BURN
title: Burn down the CI test quarantine (518 pre-existing red tests)
status: backlog
task_type: fix
created: 2026-06-11T00:00:00Z
updated: 2026-06-11T00:00:00Z
priority: medium
parent_task: TASK-INFRA-CIGREEN
related: [TASK-HMIG-010]
implementation_mode: task-work
tags: [ci, tests, tech-debt, quarantine]
---

# Task: Burn down the CI test quarantine

## Why this task exists

TASK-INFRA-CIGREEN landed a merge-gating test CI (`.github/workflows/tests.yml`)
over the ~14,041 passing tests. To get there it **quarantined 518 pre-existing
red tests** (`tests/quarantine.txt`, skipped by `tests/conftest.py`) that had
rotted while the suite was ungated. The gate now catches *new* regressions; this
task burns the quarantine back down to zero so the *old* failures are gated too.

Full triage + per-bucket counts: `docs/state/TASK-INFRA-CIGREEN/triage.md`.

## How to work the list

```bash
# Run a quarantined module's real (red) behaviour:
GUARDKIT_NO_QUARANTINE=1 pytest tests/<module> -o addopts="" -q
# Fix the tests/code, then delete those node-id lines from tests/quarantine.txt.
# The gate immediately enforces them.
```

## Acceptance criteria (one bucket per sub-deliverable; do in priority order)

- [ ] **E — stale mocks (~182, highest value)**: update mocks in
  `tests/unit/test_autobuild_orchestrator.py`, `test_autobuild_task_type.py`,
  and peers to the current orchestrator signatures (return ints/awaitables where
  the code compares/awaits). Remove their quarantine lines.
- [ ] **B — SSIM (~21)**: `importorskip("skimage")` in
  `tests/orchestrator/test_visual_comparator.py`; add a `viz` extra
  (`scikit-image`, `pillow`). Remove quarantine lines.
- [ ] **C — FalkorDB (~12)**: `importorskip("falkordb")` / `requires_falkordb`
  marker on the affected `tests/knowledge/**` modules.
- [ ] **D — SDK-in-subprocess (~32)**: make the coach subprocess inherit the
  SDK-bearing interpreter (or skip cleanly when the child can't import the SDK).
- [ ] **A — foreign-machine paths (~74)**: rewrite hardcoded
  `/Users/.../ai-engineer/...` paths to repo-relative, or delete the obsolete
  duplicate-file assertions (`test_task_011e/011f/007`).
- [ ] **F — doc/template drift (~110)**: per module, regenerate the missing
  scaffold (maui-appshell, fastmcp-python) or delete the obsolete assertion.
- [ ] **Done**: `tests/quarantine.txt` contains only the header; the gate is
  green with `GUARDKIT_NO_QUARANTINE=1`.

## Notes

- Consider `pytest-xdist` (`-n auto`) in `tests.yml` once the suite is fully
  green, so the gate stays fast (full run is ~2.8 min single-process). Noted as
  a follow-up in the parent task.
