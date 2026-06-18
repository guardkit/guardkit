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

That leaves the 2 below still open here.

| Task | Priority | What | Class |
|---|---|---|---|
| [TASK-AB-BOOTPY01](TASK-AB-BOOTPY01-pin-uv-venv-interpreter-to-requires-python.md) | medium | Pin `uv venv` interpreter to `requires-python` | bootstrap trap |
| [TASK-AB-COACHVENV01](TASK-AB-COACHVENV01-refresh-coach-venv-on-intrawave-dep-change.md) | medium | Refresh Coach venv on intra-wave dependency change | false-red stall |

**Recommended order:** the two remaining bootstrap/BDD items are operator-friction
fixes. (Both high-impact correctness items — TASK-GK-PA-003 and TASK-AB-WIREGATE01 —
are done; see above.)

**Not filed (borderline / usage):** TASK-AB-COACHSUBPROC01 (make `coach.test_execution:
subprocess` the default / auto-fallback) — noted in the report §4 as a candidate, not yet
a committed task.
