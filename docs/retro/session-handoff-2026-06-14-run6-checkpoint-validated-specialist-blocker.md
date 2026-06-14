# Handoff: run 6 validated the checkpoint fix → new blocker is specialist latency (2026-06-14)

> **Purpose.** Start the next session fresh. Supersedes the "fix the checkpoint
> false-red" goal in
> [`session-handoff-2026-06-14-coach-model-and-checkpoint.md`](session-handoff-2026-06-14-coach-model-and-checkpoint.md)
> — that blocker is **resolved and live-validated**. Evidence:
> [`run6-evidence/`](run6-evidence/).

## TL;DR — what run 6 proved and what's next

1. **Checkpoint false-red is FIXED (validated live).** FEAT-9DDE run 6
   (qwen3-coder-30b Player / gemma4-coach Coach + `DISABLE_THINKING=1`) ran **3
   full turns** with **all checkpoints `tests_passed=True`** and **no false
   `unrecoverable_stall`**. CKPTTESTRED01 + CKPTGATE01 hold end-to-end.
2. **New dominant blocker: specialist latency.** The run ended
   `timeout_budget_exhausted` — the turn-2 `code-reviewer` specialist ran
   **35.6 min (2138s)** then SDK-timed-out, burning >½ the 80-min task budget;
   turn 4 was refused at `remaining=397.4s < min=600s`. **→ TASK-PERF-SPECLAT01
   (high).** Nothing reaches Wave 2 until this is solved.
3. **DIRECTFG01 still NOT live-validated** — Wave 2 never ran (Wave 1 failed,
   `stop_on_failure`). It remains blocked behind SPECLAT01.
4. **Four fixes landed this session** (see below). Two are committed code fixes
   from run-6 forensics; two are filed follow-ups.

## What run 6 surfaced (4 issues, none the old checkpoint bug)

| # | Issue | Status |
|---|---|---|
| 1 | **Specialist latency** — code-reviewer (on `--model` qwen3-coder-30b) 35-min SDKTimeout exhausts the task budget before convergence | **TASK-PERF-SPECLAT01** (high, backlog) |
| 2 | Coach independent test failed 0.0s "No module named pytest" — bootstrap dropped the `[dev]` extra on the incomplete-project path; **COACHCWD01 was NOT the cause (intact)** | **TASK-FIX-BSEXTRAS01** (fixed) |
| 3 | 136 `.local/site-packages` install artefacts swept into `files_modified` → 136 spurious `claim_audit_unmodified` records | **TASK-FIX-EVBINST01** (fixed) |
| 4 | `timeout_budget_exhausted` renders misleading "Unknown error occurred" | **TASK-FIX-TBXMSG01** (low, backlog) |

## Fixes landed this session (committed)

- **TASK-FIX-BSEXTRAS01** — (a) `environment_bootstrap._python_dep_commands`
  now installs requested extras (pytest via `[dev]`) on the
  *incomplete-project* per-dep path, not just the editable `.[dev]` path; (b)
  `coach_validator` classifies an absent test **runner** ("No module named
  pytest" / pytest exit-5) as `signal_absent=True`, never a false-red
  (`absence-of-failure-is-not-success`). Root cause: guardkit-py's import name
  `guardkit_py` ≠ `guardkit/` dir → `_python_pyproject_is_complete()` False →
  per-dep path → `[dev]` silently dropped.
- **TASK-FIX-EVBINST01** — extended
  `agent_invoker._ORCHESTRATOR_MANAGED_PATH_PATTERNS` to strip
  `.local/`/`site-packages/`/`.venv*/` (one constant, fixes both the Player
  report and the Coach claim audit); added `.local/` to `.gitignore`. The
  over-wide direction of
  `evidence-boundary-narrower-than-write-surface.md`.

Tests: +11 regression tests; 595 passed / 7 skipped across the touched modules
+ checkpoint suites, zero regressions.

## Models (unchanged from prior handoff — still good)

| Role | Model | Notes |
|------|-------|-------|
| Player | `qwen3-coder-30b` | converges; **but** specialists also run on this model and are the latency driver (#1). |
| Coach | `gemma4-coach` + `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1` | ~30–90s/turn, self-bounding, valid verdicts. Confirmed live in run 6 (COACHSPLIT `disable_thinking=True`). |

`--help` confirms **specialists run on `--model`** ("specialist invocations
stay on --model"). SPECLAT01 should consider a faster/separate specialist
model and/or a bounded specialist turn budget — consult agent memory
`nvidia-gb10-dgx-spark-forum` first.

## Re-run recipe (for after SPECLAT01) — pre-merge base technique

FEAT-9DDE is merged, so re-running needs the pre-merge base (`740e1585`) so the
producer is absent and the Player has real work. Full recipe in the prior
handoff §"Exact recipe"; the only addition: probe `gemma4-coach` +
`disable_thinking` first (serving config drifts across restarts), and **watch
the specialist wall-clock** — if a single specialist again approaches the
task-timeout, SPECLAT01 isn't solved.

## Key references
- Run-6 evidence: [`run6-evidence/`](run6-evidence/) (stdout log, coach/player
  turn JSONs, checkpoints.json with all-`True` test status, review-summary).
- Prior handoff (models, recipe, checkpoint history):
  [`session-handoff-2026-06-14-coach-model-and-checkpoint.md`](session-handoff-2026-06-14-coach-model-and-checkpoint.md).
- Rules in play: `absence-of-failure-is-not-success.md`,
  `evidence-boundary-narrower-than-write-surface.md`,
  `path-string-mismatch-is-not-dishonesty.md`.
- Tasks: `tasks/completed/TASK-FIX-BSEXTRAS01/`,
  `tasks/completed/TASK-FIX-EVBINST01/`,
  `tasks/backlog/feat-9dde-followups/TASK-PERF-SPECLAT01-*.md`,
  `tasks/backlog/feat-9dde-followups/TASK-FIX-TBXMSG01-*.md`.
