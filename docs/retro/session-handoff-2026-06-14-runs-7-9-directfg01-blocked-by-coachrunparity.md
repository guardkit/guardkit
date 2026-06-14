# Handoff: runs 7–9 — all checkpoint/specialist/bootstrap/evidence fixes validated; Wave-1 converges; DIRECTFG01 now blocked only by COACHRUNPARITY01 (2026-06-14)

> **Purpose.** Start the next session fresh. Supersedes
> [`session-handoff-2026-06-14-run6-checkpoint-validated-specialist-blocker.md`](session-handoff-2026-06-14-run6-checkpoint-validated-specialist-blocker.md).
> Evidence: [`run7-evidence/`](run7-evidence/), [`run8-evidence/`](run8-evidence/),
> and `.guardkit/autobuild/FEAT-9DDE-run{7,8,9}-stdout.log`.

## TL;DR — the one thing to do next

**Implement TASK-AB-COACHRUNPARITY01** (high; full implementation design is in the
task file, ready to code). It is the *only* remaining blocker to live-validating
DIRECTFG01. Everything else in the FEAT-9DDE validation chain now works.

## What is now VALIDATED LIVE (runs 7–9)

| Fix | Evidence |
|-----|----------|
| **CKPTTESTRED01 / CKPTGATE01** (checkpoint) | `tests: pass` on every turn of runs 7, 8, 9; no false stall |
| **SPECLAT01** (specialist latency) | code-reviewer capped 1950s→600s; run 7 used all 5 turns in-budget (run 6 died at turn 3); graceful 60s clamp as budget tightens |
| **BSEXTRAS01** (bootstrap [dev] extra) | run 7+: bootstrap installs `pytest>=7.4.3` into the worktree venv; Coach independent test runs (2.6–3.0s) instead of run-6's 0.0s "No module named pytest" |
| **EVBINST01** (evidence-boundary install noise) | run 8 Coach issues 144 → 8; the 136 `.local`/site-packages `claim_audit_unmodified` records gone |
| **Wave-1 convergence** | runs 8 (turn 2) and 9 (turn 1) — TASK-TSJ-001 Coach-approved, `tests: pass, count: 7` |

## The run-by-run progression (each blocker fixed, next surfaced)

- **Run 6** → `timeout_budget_exhausted` at turn 3 (specialist latency) → SPECLAT01.
- **Run 7** → `max_turns_exceeded` (producer not converged in 5 turns; majors
  trended 4→3→2, i.e. converging) → seed the producer + more turns.
- **Run 8** → **Wave 1 converged (turn 2)**, then the post-wave **smoke gate**
  caught that the approved producer doesn't run standalone
  (`ModuleNotFoundError: No module named 'installer'` + a datetime JSON crash).
  Feature terminated; Wave 2 / DIRECTFG01 never ran.
- **Run 9** → seeded a hand-fixed producer (dual-mode import + `json default=str`,
  verified passing the smoke gate locally). **Wave 1 converged turn 1**, but the
  smoke gate failed *again* with a NEW bug: **the Player rewrote the producer
  (260-line diff) and introduced `TypeError: '<' not supported between NoneType
  and str`** (None-sort). pytest passed; the smoke gate caught the runtime crash.

## The remaining blocker — COACHRUNPARITY01 (filed, fully designed)

**Root cause:** the per-task Coach verifies only via `pytest` on task files
(`coach_validator.py:3866-4117`). pytest puts the worktree root on `sys.path`, so
`from installer.core...` resolves; the **standalone runtime invocation** (what the
smoke gate runs) is never exercised by the Coach. So the Coach approves a
"passes-tests-but-doesn't-run" producer, and the smoke-gate failure **terminates
the feature with no feedback to the Player** (`feature_orchestrator.py:2212`
`break`). Run 9 also proved **the Player rewrites the producer each turn**, so
hand-seeding a fixed producer can't get past the smoke gate.

**Fix (design ready in the task):** convert the smoke-gate `break` into a
**bounded feedback-and-retry** — inject the smoke stderr as the Player's turn-1
feedback (`seed_feedback` param: `AutoBuildOrchestrator.__init__` →
`self._seed_feedback` → `_loop_phase:2369`; threaded up through `_execute_task`
→ `_execute_wave`), re-run the wave up to `GUARDKIT_SMOKE_GATE_MAX_RETRIES`
(default 1), replace `wave_results[-1]`, re-check `stop_on_failure`; exhaustion
still terminates (worktree preserved). **High blast radius** (core wave executor;
needs live-run validation, not just unit tests — ironically the same
"unit-green but runtime-broken" trap this fix addresses). Full spec + test matrix
in `tasks/backlog/feat-9dde-followups/TASK-AB-COACHRUNPARITY01-*.md`.

## Path to finally exercising DIRECTFG01 (after COACHRUNPARITY01)

DIRECTFG01 is the Wave-2 (TASK-TSJ-002) direct-mode AC/wiring/bin-entry gate; it
only runs once Wave 1 passes the smoke gate. Two routes once COACHRUNPARITY01
lands: (a) the Player iterates to a runnable producer via the new feedback loop →
Wave 2 runs; or (b) for a quick isolated check, temporarily remove the
`smoke_gates` block from the validation `FEAT-9DDE.yaml` so Wave 2 runs regardless
(harness shortcut; smoke gate isn't the thing under test).

## Run state KEPT for next session (per operator choice)

- Worktree `.guardkit/worktrees/FEAT-9DDE` removed after run 9; branches kept:
  `feat9dde-rerun-base` (740e1585, pre-merge base), `feat9dde-run8-base`
  (turn-5 producer), `feat9dde-run9-base` (approved + hand-fixed producer,
  commit `7bb3e2de`).
- `.guardkit/features/FEAT-9DDE.yaml` left in rerun-base state (`status: planned`)
  and `tasks/backlog/task-status-json/TASK-TSJ-00{1,2}-*.md` restored — these are
  the rerun harness state (NOT committed). Restore via
  `git checkout -- .guardkit/features/FEAT-9DDE.yaml` + `rm` the two task files +
  `git branch -D feat9dde-*` when done.

## Re-run recipe (run 10, after COACHRUNPARITY01)

```bash
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 PYTHONUNBUFFERED=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-9DDE --fresh --base-branch feat9dde-rerun-base \
    --model qwen3-coder-30b --coach-model gemma4-coach \
    --max-turns 8 --task-timeout 7200 --sdk-timeout 3600 --no-context --max-parallel 1 \
    > .guardkit/autobuild/FEAT-9DDE-run10-stdout.log 2>&1
```
(Probe `gemma4-coach`+`disable_thinking` reasoning-free first; serving config drifts.)

## Follow-up task inventory (all in tasks/backlog/feat-9dde-followups/)

- **TASK-AB-COACHRUNPARITY01** (high) — the blocker above; design ready.
- **TASK-FIX-EVBINST02** (low) — strip `large_tool_results/` + `.claude/task-plans/`
  residual claim_audit noise (same class as EVBINST01).
- Done this chain: BSEXTRAS01, EVBINST01, SPECLAT01, TBXMSG01 (committed to main).

## Key references
- Result docs: `docs/retro/run{6,7,8}-evidence/`, run logs
  `.guardkit/autobuild/FEAT-9DDE-run{6,7,8,9}-stdout.log`.
- Rules in play: `absence-of-failure-is-not-success.md`,
  `evidence-boundary-narrower-than-write-surface.md`, `namespace-hygiene.md`
  (tests-pass/production-fails), `feature-build-invariants.md`.
