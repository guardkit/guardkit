# autobuild-retro-fixes

Still-open guardkit autobuild defects surfaced by **cloud (Claude Agent SDK)** autobuild
runs on an older guardkit (lpa-platform-poc + fleet-memory, 2026-06-13/14), after
cross-referencing all 11 retros against current main.

**Source analysis:** [`docs/retro/autobuild-retro-xref-2026-06-17.md`](../../../docs/retro/autobuild-retro-xref-2026-06-17.md)
(9 of ~16 issues already fixed in current guardkit; these were the 5 that remained).

**Done (completed):**
- TASK-GK-PA-003 — plan-audit resolves markdown-link hrefs + path-suffix matches;
  completed at [`tasks/completed/TASK-GK-PA-003/`](../../completed/TASK-GK-PA-003/TASK-GK-PA-003.md).
- TASK-AB-WIREGATE01 — post-wave mocked-seam + composition-root wiring gate
  (the only correctness gap); completed at
  [`tasks/completed/TASK-AB-WIREGATE01/`](../../completed/TASK-AB-WIREGATE01/TASK-AB-WIREGATE01.md).
  Cross-repo: new `CTOR_ARITY` analysis in `guardkitfactory.wiring` + post-wave gate
  in guardkit `feature_orchestrator.py`; companion rule
  [`per-task-green-is-not-feature-green.md`](../../../.claude/rules/per-task-green-is-not-feature-green.md).
- TASK-AB-BDDNEUTRAL01 — neutral BDD verdict on absent feature file + auto-install
  conftest bridge; completed at
  [`tasks/completed/TASK-AB-BDDNEUTRAL01/`](../../completed/TASK-AB-BDDNEUTRAL01/TASK-AB-BDDNEUTRAL01.md).
  Exit-4 "not found" (uncollectable `.feature`) → neutral, not a stacking false-red
  (F584 preserved via a positive-evidence discriminator); bridge auto-installed at
  `WorktreeManager.create()` + `guardkit init`.

- TASK-AB-BOOTPY01 — pin `uv venv` interpreter to `requires-python`; completed
  2026-06-17 at [`tasks/completed/TASK-AB-BOOTPY01/`](../../completed/TASK-AB-BOOTPY01/TASK-AB-BOOTPY01.md)
  (commit `5b6bead26`).
- TASK-AB-COACHVENV01 — refresh Coach venv on intra-wave dependency change; completed
  2026-06-17 at [`tasks/completed/TASK-AB-COACHVENV01/`](../../completed/TASK-AB-COACHVENV01/TASK-AB-COACHVENV01.md)
  (commit `a9c0022cc`).

**All five follow-ups from the 2026-06-17 xref are now landed.** This folder is kept as
a pointer; new autobuild-reliability work from the 2026-07-04 xref is filed under
[`tasks/backlog/autobuild-reliability/`](../autobuild-reliability/) — see
[`docs/retro/autobuild-retro-xref-2026-07-04.md`](../../../docs/retro/autobuild-retro-xref-2026-07-04.md).

**TASK-AB-COACHSUBPROC01** (make `coach.test_execution: subprocess` the default) was
judged borderline by the 2026-06-17 xref and not filed; the 2026-07-04 xref found the
SDK path failing on ~100% of invocations across every repo/vintage and **revived it** —
now filed in `tasks/backlog/autobuild-reliability/`.
