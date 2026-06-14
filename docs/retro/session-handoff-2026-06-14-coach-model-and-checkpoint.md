# Handoff: Coach-model resolved → fix the checkpoint false-red → finish live validation (2026-06-14)

> **Purpose.** Start the next session fresh without this chat's history.
> Self-contained: what's done, the models we settled on, the one open blocker,
> the exact recipe, and what to watch. Supersedes the Coach guidance in
> [`coder-player-experiment-session-handoff.md`](coder-player-experiment-session-handoff.md);
> full analysis in
> [`coder-player-experiment-RESULT-2026-06-13.md`](coder-player-experiment-RESULT-2026-06-13.md).

## TL;DR — what to do next

1. **Implement `TASK-FIX-CKPTTESTRED01`** (high) —
   [`tasks/backlog/feat-9dde-followups/TASK-FIX-CKPTTESTRED01-*.md`](../../tasks/backlog/feat-9dde-followups/).
   This is the ONE blocker to a converging autobuild run. The checkpoint
   pollution detector reads the Player's *absent* test-counts (`tests_run=None`)
   as "tests failed" and false-stalls after 3 strict-Coach feedback turns.
2. **Then one FEAT-9DDE re-run** (recipe below) to **live-validate DIRECTFG01 +
   COACHCWD01** — both currently rest on green deterministic regression tests but
   have never been exercised end-to-end (every run so far ended before wave 2).
3. Optional anytime: **push** the session's commits (`git push origin main`) —
   nothing is pushed yet; and the server-side "pin gemma out of reasoning mode on
   llama-swap" win (needs GB10 access).

## Models we settled on (use these)

| Role | Model | Notes |
|------|-------|-------|
| **Player** | **`qwen3-coder-30b`** | Validated: converges where `qwen36-workhorse` stalled (H-Player confirmed). |
| **Coach** | **`gemma4-coach`** (= gemma4:26b-A4B MoE) **+ `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1`** | **~35–51s/turn, self-bounding, valid verdicts. THIS is the fix.** |
| ~~Coach fallback~~ | ~~`gemma4-31b`~~ | **Avoid** — ~32 min/turn (NOT a reasoning tax you can toggle off; it reasons in the verdict grammar's unbounded prefix regardless). |

- **`DISABLE_THINKING=1` is load-bearing for the MoE Coach.** Without it the MoE
  rambles to the token ceiling and emits no parseable verdict (the F2
  non-emission that benched it). It does *nothing* for dense gemma4-31b.
- Env: **GB10 `promaxgb10-41b1`**, llama-swap OpenAI-compatible on `:9000`,
  `OPENAI_API_KEY=llama-swap-local-key`. Models load on demand. **Probe before
  launching** (the serving config drifts across restarts):
  ```bash
  curl -s --max-time 10 http://promaxgb10-41b1:9000/v1/models | python3 -c "import json,sys;print(', '.join(m['id'] for m in json.load(sys.stdin)['data']))"
  # gemma4-coach with enable_thinking=false MUST come back reasoning-free + a clean answer:
  curl -s --max-time 120 http://promaxgb10-41b1:9000/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer llama-swap-local-key" \
    -d '{"model":"gemma4-coach","chat_template_kwargs":{"enable_thinking":false},"messages":[{"role":"user","content":"Reply one word: READY"}],"max_tokens":200}' \
    | python3 -c "import json,sys;c=json.load(sys.stdin)['choices'][0];m=c['message'];print('content=',repr((m.get('content') or '')[:20]),'reasoning_len=',len(m.get('reasoning_content') or ''),c.get('finish_reason'))"
  ```

## What's DONE this session (all committed; NOT pushed)

**guardkit `main`** (newest first): `12f51e3b` file CKPTTESTRED01 · `ddf3cff3`
runs-4/5 result docs · `a50ef3ff` COACHCWD01 test · `d916cf43` SPECINVOKE01 ·
`69d79a6c` DIRECTFG01 · `f9c4070b` hermetic test fix · `8228231e` FEAT-9DDE
finalize · `d089bb04` **FEAT-9DDE merged** · `79630e56` TSJ-002 fix.
**guardkitfactory `main`**: `7526b55` COACHREASON01 (disable_thinking) · `895afd7`
SPECINVOKE01 (harness callback).

- **FEAT-9DDE (`--json` flag for /task-status) is MERGED to main** and finalized
  (tasks → `tasks/completed/2026-06/`, feature → `merged`). Producer works, 11/11
  tests pass.
- **Experiment answer: H-Player confirmed** — the coder Player converged the
  feature where the workhorse stalled.
- **Follow-up fixes landed & unit-green** (115 guardkit + 121 guardkitfactory):
  - **SPECINVOKE01 ✅ live-validated** — specialists now run with real model
    activity (no false 150s hang); a `validation=violation` is now a *real*
    review finding.
  - **COACHREASON01 ✅ committed** — `DISABLE_THINKING` toggle; load-bearing for
    the MoE Coach (above).
  - **DIRECTFG01 / COACHCWD01 — committed + unit-green, but NOT live-validated**
    (no run reached wave 2 / a clean independent-test run yet).
- **Coach latency SOLVED** via the model review → `gemma4-coach` + disable_thinking
  (~55× faster than gemma4-31b).

## The ONE open blocker — TASK-FIX-CKPTTESTRED01

**Run 5 (gemma4-coach Coach) ended `unrecoverable_stall` at turn 3 — a FALSE
RED, not a real failure.** The checkpoint pollution detector
(`guardkit/orchestrator/worktree_checkpoints.py`) derives `tests_passed`/
`test_count` from the **Player's self-report** (`tests_run=None` →
`tests: fail, count: 0`), NOT from the Coach gate (which said `tests=True`) or an
independent run. Three turns of the Player not reporting counts read as "3
consecutive test failures" → stall. It only surfaced because the faster, stricter
gemma4-coach gives feedback through the full turn budget (run 3's lenient
gemma4-31b approved at turn 2, exiting before the counter hit 3).

Fix = source checkpoint test-status from a real signal (Coach gate / independent
run) or treat absent counts as *unknown*, never *failure*. It's the
`absence-of-failure-is-not-success` family in the checkpoint layer. Full spec +
evidence in the task file; preserved artifacts in `docs/retro/run5-evidence/`.

## Exact recipe for the validation re-run (after CKPTTESTRED01)

FEAT-9DDE is now **merged**, so re-running needs the **pre-merge base** technique
(worktree branches from `740e1585` so the producer is absent and the Player has
real work — orchestrator/harness fixes run from the host editable install
regardless of worktree base).

```bash
cd /home/richardwoollcott/Projects/appmilla_github/guardkit
BASE=740e1585
T1=tasks/backlog/task-status-json/TASK-TSJ-001-implement-task-status-json-producer.md
T2=tasks/backlog/task-status-json/TASK-TSJ-002-register-bin-entry-and-wire-specs.md

# 1) reset FEAT-9DDE to a buildable state (uncommitted; restored after the run)
git branch -f feat9dde-rerun-base $BASE
git show $BASE:.guardkit/features/FEAT-9DDE.yaml > .guardkit/features/FEAT-9DDE.yaml
git show "$BASE:$T1" > "$T1"; git show "$BASE:$T2" > "$T2"

# 2) probe models (see above), then LAUNCH in background, tee to a log
GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1 \
PYTHONUNBUFFERED=1 GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-9DDE \
    --fresh --base-branch feat9dde-rerun-base --model qwen3-coder-30b --coach-model gemma4-coach \
    --task-timeout 4800 --sdk-timeout 3600 --no-context --max-parallel 1 \
    2>&1 | tee .guardkit/autobuild/FEAT-9DDE-run6-stdout.log

# 3) AFTER the run, restore the merged host state:
git checkout -- .guardkit/features/FEAT-9DDE.yaml
rm -f "$T1" "$T2"                                   # canonical copies live in tasks/completed/2026-06/
git worktree remove .guardkit/worktrees/FEAT-9DDE --force
git branch -D autobuild/FEAT-9DDE feat9dde-rerun-base
```

## What to watch on the validation run

- **Coach speed**: `disable_thinking=True` in the COACHSPLIT log line + Coach
  turns ~35–60s (NOT 32 min). If slow, the Coach model regressed — re-probe.
- **SPECINVOKE01**: no `hang detected`; specialists run with activity (they're
  now the ~13-min/turn wall-clock driver).
- **CKPTTESTRED01 fixed**: checkpoint must NOT log `tests: fail, count: 0` when
  the Coach gate says `tests=True`; no false `unrecoverable_stall`.
- **Convergence → wave 2 → DIRECTFG01**: when TSJ-002 (direct mode) runs, the
  Coach must do real AC/wiring verification (catch a false-green, or cleanly
  approve a correct deliverable). **This is the headline DIRECTFG01 live test.**
- **COACHCWD01**: no `coverage.xml`/`coverage.json` left in the **host** repo
  root after the Coach's independent test run (it should write to the worktree).
- **gemma4-coach is stricter than gemma4-31b** — expect it to reject AC-005–010
  (missing-frontmatter / malformed / single-task) if the Player's producer is
  incomplete. That's a feature (more accurate), but means convergence needs the
  Player to actually satisfy those ACs.

## Follow-up task inventory

- **Open / high**: `TASK-FIX-CKPTTESTRED01` (the blocker above).
- **Done this session**: `TASK-FIX-DIRECTFG01`, `TASK-FIX-SPECINVOKE01`,
  `TASK-FIX-COACHCWD01` (→ `tasks/completed/`), `TASK-FIX-COACHREASON01`
  (record in `feat-9dde-followups/`).
- **Server-side, anytime**: pin `gemma4-coach` / `gemma4:26b` (and gemma4-31b)
  out of reasoning mode on llama-swap — helps all consumers, needs GB10 access;
  the client-side `DISABLE_THINKING` toggle is the portable substitute.

## Key references

- Result writeup (full analysis, runs 3–5): `docs/retro/coder-player-experiment-RESULT-2026-06-13.md`
- Prior experiment handoff: `docs/retro/coder-player-experiment-session-handoff.md`
- Run logs: `.guardkit/autobuild/FEAT-9DDE-run{3,4,5}-stdout.log`
- Evidence: `docs/retro/run{2,3,5}-evidence/`
- Coach verdict grammar (the unbounded reasoning prefix): `guardkit/orchestrator/grammars/coach-verdict.gbnf`
- disable_thinking impl: `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py` (`_synthesis_disable_thinking`, env `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING`)
- Sibling rule for the checkpoint false-red: `.claude/rules/absence-of-failure-is-not-success.md`
- GB10 real-world usage: agent memory `nvidia-gb10-dgx-spark-forum`
</content>
