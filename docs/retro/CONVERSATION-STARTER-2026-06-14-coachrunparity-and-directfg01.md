# 🚀 Conversation Starter — FEAT-9DDE autobuild validation (handoff 2026-06-14)

> **How to use this doc:** open a fresh session and say *"Read
> `docs/retro/CONVERSATION-STARTER-2026-06-14-coachrunparity-and-directfg01.md`
> and continue."* It is self-contained — you should not need to re-derive
> anything. Deeper detail is cross-linked but not required.
>
> **You are running on the GB10** (`promaxgb10-41b1`), llama-swap on `:9000`.

---

## 🎯 THE ONE THING TO DO NEXT

**Implement `TASK-AB-COACHRUNPARITY01`** — the complete, ready-to-code
implementation design is already in
[`tasks/backlog/feat-9dde-followups/TASK-AB-COACHRUNPARITY01-coach-pytest-vs-smoke-runtime-parity.md`](../../tasks/backlog/feat-9dde-followups/TASK-AB-COACHRUNPARITY01-coach-pytest-vs-smoke-runtime-parity.md)
(see its "Implementation design" section). It is the **only** remaining blocker
to live-validating DIRECTFG01. Then do **run 10** (recipe below) to finally
exercise the DIRECTFG01 Wave-2 gate.

> ⚠️ It is a **core wave-executor change** (a `seed_feedback` param threaded
> through 5 methods + a bounded smoke-gate retry loop). Unit tests cannot fully
> validate it — it needs live autobuild runs. Treat it as its own focused,
> carefully-tested effort. (Ironically it can fail the exact way it fixes:
> "unit-green but runtime-broken.")

---

## 📍 WHERE WE ARE

We are validating the GuardKit **autobuild** pipeline end-to-end using
**FEAT-9DDE** (a 2-task feature: TASK-TSJ-001 = `--json` producer for
`/task-status`; TASK-TSJ-002 = Wave-2 bin-entry/wiring = the **DIRECTFG01**
direct-mode gate under test). Player = `qwen3-coder-30b`, Coach = `gemma4-coach`
+ `disable_thinking`, on the GB10.

**Goal:** live-exercise the **DIRECTFG01** direct-mode AC/wiring/bin-entry gate
(Wave 2). It has never run because Wave 1 kept failing for a *succession of
distinct, now-fixed reasons*. As of end of this session, **Wave 1 converges**
and DIRECTFG01 is blocked by exactly one designed thing (COACHRUNPARITY01).

---

## ✅ VALIDATED LIVE THIS SESSION (all committed to `main`)

| Fix | What it did | Proof |
|-----|-------------|-------|
| **CKPTTESTRED01 / CKPTGATE01** | checkpoint reads gate signal; absent ≠ fail | `tests: pass` every turn of runs 7/8/9; no false `unrecoverable_stall` |
| **SPECLAT01** | bound specialist phase (code-reviewer cap 600s; budget fraction) | capped 1950s→600s; run 7 ran all 5 turns in-budget (run 6 died at turn 3) |
| **BSEXTRAS01** | bootstrap installs `[dev]` extra (pytest) on the incomplete-project path; Coach treats absent runner as `signal_absent` | run 7+: `pip install pytest>=7.4.3` into worktree venv; Coach independent test runs (2.6–3.0s) not 0.0s "No module named pytest" |
| **EVBINST01** | strip `.local/`/`site-packages/`/`.venv*` from the evidence boundary | run 8 Coach issues **144 → 8**; the 136 `.local` `claim_audit_unmodified` records gone |
| **TBXMSG01** | label `timeout_budget_exhausted` (not "Unknown error") | (committed; not exercised this chain — run 8/9 ended other ways) |
| **Wave-1 convergence** | TASK-TSJ-001 Coach-approved | run 8 (turn 2), run 9 (turn 1), `tests: pass, count: 7` |

Commits this session (newest first): `188f8497` (runs 7-9 docs + COACHRUNPARITY01
+ EVBINST02), `dacbed55` SPECLAT01, `ddce6e0c` TBXMSG01, `1787b94b` run-6 docs,
`dbed7e3a` EVBINST01, `3c355324` BSEXTRAS01. (SPECLAT01/TBXMSG01 were implemented
by the operator; BSEXTRAS01/EVBINST01 implemented + tested in-session.)

---

## 🔴 THE BLOCKER — COACHRUNPARITY01 (filed, fully designed)

**Symptom (run 8 & 9):** Wave 1 converges (Coach approves), then the feature's
post-wave **smoke gate** fails because the approved producer **doesn't run
standalone** and **terminates the feature** (Wave 2 / DIRECTFG01 never starts).

**Root cause:** the per-task Coach verifies *only* via `pytest` on task files
(`coach_validator.py:3866-4117`). pytest puts the worktree root on `sys.path`,
so `from installer.core...` resolves; the **standalone runtime invocation** the
smoke gate runs (`python3 installer/core/commands/lib/task_status_json.py …`) is
never exercised by the Coach. So the Coach approves a "passes-tests-but-doesn't-
run" deliverable, and the smoke-gate `break` (`feature_orchestrator.py:2212`)
kills the build with **no feedback to the Player**.

**Run 9 also proved a key fact:** the Player **rewrites the producer from scratch
every turn** (260-line diff), reintroducing runtime bugs pytest misses (run 8:
`ModuleNotFoundError`; run 9: `TypeError: '<' not supported between NoneType and
str`). → **Hand-seeding a fixed producer does NOT work** — the Player overwrites
it. The fix MUST be the feedback loop, not a seeded producer.

**Fix (design ready in the task):** convert the smoke-gate `break` into a
**bounded feedback-and-retry**: inject smoke stderr as the Player's turn-1
feedback (`seed_feedback`: `AutoBuildOrchestrator.__init__` → `self._seed_feedback`
→ `_loop_phase:2369`; threaded up `_execute_task` → `_execute_wave` → wave loop),
re-run the wave up to `GUARDKIT_SMOKE_GATE_MAX_RETRIES` (default 1), replace
`wave_results[-1]`, re-check `stop_on_failure`; exhaustion still terminates
(worktree preserved). Full spec + 6-case test matrix in the task file.

---

## 🧠 KEY LEARNINGS / GOTCHAS (don't relearn these)

1. **The Player rewrites the producer each turn** — seeding a fixed producer is
   futile; only an in-loop feedback path will land runtime fixes.
2. **Coach pytest ≠ runtime** — pytest passing does not mean the deliverable
   runs standalone (the COACHRUNPARITY01 root cause; also the `namespace-hygiene`
   "tests pass / production fails" pattern).
3. **Native `--resume` can't continue a terminal task** — a
   `max_turns_exceeded`/`failed` task has no `autobuild_state` and status ≠
   `in_progress`, so `get_resume_point` returns nothing. To continue producer
   work, seed a `--fresh --base-branch <producer-branch>` run (but see #1).
4. **Coach model probe drifts** — always probe `gemma4-coach` +
   `chat_template_kwargs.enable_thinking=false` returns reasoning-free before a
   run; the serving config changes across restarts.
5. **Specialists run on `--model`** (qwen3-coder-30b) and are slow on the GB10;
   SPECLAT01 bounds them. A faster/separate specialist model is a possible
   future optimization (was deferred from SPECLAT01).
6. **Each autobuild run is ~30–75 min** — launch in background, monitor the log.

---

## 🌳 REPO & RUN STATE (left intentionally for next session)

- **Branches kept** (the producer history): `feat9dde-rerun-base` (`740e1585`,
  pre-merge base — Player builds the producer from scratch), `feat9dde-run8-base`
  (turn-5 producer), `feat9dde-run9-base` (`7bb3e2de`, approved + hand-fixed
  producer). For run 10 use **`feat9dde-rerun-base`** (clean pre-merge base) per
  the recipe.
- **Uncommitted harness state (KEEP):** `.guardkit/features/FEAT-9DDE.yaml`
  (rerun-base, `status: planned`) + `tasks/backlog/task-status-json/TASK-TSJ-00{1,2}-*.md`.
  These are the rerun fixtures, deliberately not committed.
- **No active worktree** — removed after run 9 (`.guardkit/worktrees/FEAT-9DDE`).
  `--fresh` recreates it.
- **Evidence:** `docs/retro/run{6,7,8}-evidence/` (turn JSONs, checkpoints, logs);
  full logs `.guardkit/autobuild/FEAT-9DDE-run{6,7,8,9}-stdout.log`.

**To fully restore host when done with FEAT-9DDE validation:**
```bash
git checkout -- .guardkit/features/FEAT-9DDE.yaml
rm -f tasks/backlog/task-status-json/TASK-TSJ-00{1,2}-*.md
git branch -D feat9dde-rerun-base feat9dde-run8-base feat9dde-run9-base
# (remove any autobuild/FEAT-9DDE worktree+branch if a run left one)
```

---

## 🤖 MODELS & RE-RUN RECIPE (run 10, after COACHRUNPARITY01)

```bash
# 1) Probe (serving config drifts) — Coach MUST come back reasoning-free:
curl -s --max-time 120 http://promaxgb10-41b1:9000/v1/chat/completions \
  -H "Content-Type: application/json" -H "Authorization: Bearer llama-swap-local-key" \
  -d '{"model":"gemma4-coach","chat_template_kwargs":{"enable_thinking":false},"messages":[{"role":"user","content":"Reply one word: READY"}],"max_tokens":200}'

# 2) Launch (background; ~30-75 min):
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 PYTHONUNBUFFERED=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-9DDE --fresh --base-branch feat9dde-rerun-base \
    --model qwen3-coder-30b --coach-model gemma4-coach \
    --max-turns 8 --task-timeout 7200 --sdk-timeout 3600 --no-context --max-parallel 1 \
    > .guardkit/autobuild/FEAT-9DDE-run10-stdout.log 2>&1
```

**Watch for:** Wave-1 converges → **smoke gate** (the COACHRUNPARITY01 test: on
failure it should now feed back to the Player + retry, not terminate) → Wave 1
passes → **Wave 2 / TASK-TSJ-002 → the DIRECTFG01 direct-mode gate** (the
headline). Quick alternative to isolate DIRECTFG01: temporarily delete the
`smoke_gates` block from the rerun-base `FEAT-9DDE.yaml` so Wave 2 runs regardless.

---

## 📋 OPEN FOLLOW-UP TASKS (tasks/backlog/feat-9dde-followups/)

- **TASK-AB-COACHRUNPARITY01** (high) — the blocker; design ready to implement.
- **TASK-FIX-EVBINST02** (low) — strip residual `large_tool_results/` +
  `.claude/task-plans/` `claim_audit` noise (same one-constant pattern as EVBINST01).

---

## 🗺️ FULL RUN-BY-RUN STORY (for depth)

- **Run 6** → `timeout_budget_exhausted` at turn 3 (code-reviewer specialist
  2138s ate the budget) → fixed by **SPECLAT01**.
- **Run 7** → `max_turns_exceeded` (producer not converged in 5 turns; majors
  trended 4→3→2 = converging). BSEXTRAS01 + EVBINST01 validated here (independent
  test runs+passes; noise gone). → seed producer + more turns.
- **Run 8** → **Wave 1 converged (turn 2)**; smoke gate caught the producer not
  running standalone (`ModuleNotFoundError` + datetime JSON crash) → feature
  terminated.
- **Run 9** → seeded a hand-fixed producer (verified smoke gate passes locally);
  **Wave 1 converged turn 1**, but the Player rewrote the producer and
  reintroduced a runtime bug (None-sort `TypeError`) → smoke gate failed again.
  This proved the producer-rewrite fact and confirmed COACHRUNPARITY01 is the
  real fix.

Detailed per-run handoffs:
[`session-handoff-2026-06-14-runs-7-9-directfg01-blocked-by-coachrunparity.md`](session-handoff-2026-06-14-runs-7-9-directfg01-blocked-by-coachrunparity.md),
[`session-handoff-2026-06-14-run6-checkpoint-validated-specialist-blocker.md`](session-handoff-2026-06-14-run6-checkpoint-validated-specialist-blocker.md),
[`session-handoff-2026-06-14-coach-model-and-checkpoint.md`](session-handoff-2026-06-14-coach-model-and-checkpoint.md).

---

## 🔗 KEY REFERENCES

- **Blocker task (with full design):** `tasks/backlog/feat-9dde-followups/TASK-AB-COACHRUNPARITY01-*.md`
- **Injection points:** `autobuild.py:2369` (`_loop_phase` `previous_feedback`),
  `autobuild.py:1076-1114` (`__init__` params), `feature_orchestrator.py:2169-2212`
  (wave-loop smoke gate / `break`), `:2914-3008` (`_execute_task` → orchestrator),
  `:2659` (`_execute_wave`).
- **Rules in play:** `.claude/rules/absence-of-failure-is-not-success.md`,
  `evidence-boundary-narrower-than-write-surface.md`, `namespace-hygiene.md`
  (tests-pass/production-fails), `feature-build-invariants.md` (never-auto-merge,
  preserve-worktrees).
- **GB10 model-serving:** agent memory `nvidia-gb10-dgx-spark-forum`.
