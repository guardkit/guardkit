# RESULT: qwen3-coder-30b Player experiment (FEAT-9DDE run 3) — 2026-06-13

> **Companion to** [`coder-player-experiment-session-handoff.md`](coder-player-experiment-session-handoff.md).
> This records the outcome of the controlled disambiguation that handoff specified.
> Run executed 2026-06-13 10:02→11:35 UTC. Log:
> [`.guardkit/autobuild/FEAT-9DDE-run3-stdout.log`](../../.guardkit/autobuild/FEAT-9DDE-run3-stdout.log).
> Run-2 baseline preserved at [`run2-evidence/FEAT-9DDE/`](run2-evidence/FEAT-9DDE/).

## TL;DR — the experiment is answered, and it's a decomposition, not a binary

Recipe ran exactly as specified: **Player=`qwen3-coder-30b`, Coach=`gemma4-31b`**,
GATHER=0, serial, `--no-context`, `--fresh`. The whole of FEAT-9DDE built to
`status=completed` (2/2 tasks approved) where **run 2 (workhorse Player) had
`unrecoverable_stall`**. But on-disk verification (mandated by the handoff)
splits the "green" in two:

| # | Finding | Verdict |
|---|---------|---------|
| **1** | **H-Player confirmed as the build-success lever.** Coder Player converged FEAT-9DDE where the workhorse stalled. For the rigorous **task-work** task (TSJ-001) the green is **REAL** (9/9 tests pass on independent run, producer emits valid schema-v1 JSON). | ✅ decisive |
| **2** | **`direct` implementation_mode is a false-green vector.** The relaxed-gate **direct** task (TSJ-002) was APPROVED with a **non-functional** primary deliverable (a broken bin-entry wrapper) + an unmet AC. Caught only by on-disk verification. | ⚠ **new, important** |
| **3** | **H-Harness (specialist hang) is real but NON-FATAL.** `test-orchestrator` hung deterministically (2/2 turns, zero model activity, terminated at 150s) — but the build succeeded anyway because the Coach's own independent pytest routes around it. | ✅ real, not a blocker |
| **4** | **gemma4-31b reasoning-mode tax.** Config drifted: gemma4-31b now serves in reasoning mode (`reasoning_budget=unset`), making turn-1's Coach take ~31 min (vs documented 3.5–6.5). | ⚠ efficiency risk |

**The handoff's binary** ("coder Player ⇒ specialists stop hanging = H-Player"
*vs* "specialists still hang = H-Harness") **was a false dichotomy**: specialists
*still hang* AND H-Player is *confirmed as the lever* — because the hang is
non-fatal. The strategic recommendation stands and is now evidence-backed:
**spend freed/new GB10 capacity on the Player.**

---

## What ran (timeline, UTC)

| Time | Event | Notes |
|------|-------|-------|
| 10:02:27 | Wave 1 / TSJ-001 / Turn 1 Player | qwen3-coder-30b implements |
| ~10:17 | test-orchestrator **hang** (150s, no activity) | terminated pre-600s cap; `validation=violation` injected |
| 10:19:40→~10:51 | Turn 1 Coach (~**31 min**) | `decision=feedback`, 10/10 criteria populated, `partial_gate_abort` → AC-009 correctly **rejected** (absent signal ≠ pass) |
| 10:51:56 | Turn 2 Player | fixes test dir + completes AC-005..010 |
| ~10:54 | test-orchestrator **hang again** (2/2) | deterministic |
| 10:54:30→11:09:27 | Turn 2 Coach (~15 min) | independent pytest **runs & passes** → `decision=approve`, ALL_PASSED=True |
| 11:17:38 | Wave 2 / TSJ-002 / Turn 1 Player (**direct** mode) | no Coach loop rigor; gates `required=False` |
| 11:28:32 | Turn 1 Coach → **approve** | **false-green** (see Finding 2) |
| ~11:34:56 | Feature complete: `status=completed, 2/2` | exit code 0 |

Total wall-clock ≈ **92 min** for the 2-task feature.

---

## Finding 1 — H-Player confirmed (TSJ-001 is a REAL green)

Run 2 (qwen36-workhorse Player) → `unrecoverable_stall` at turn 3 with report-hygiene
failures (claimed a nonexistent file; `tests passed` vs `tests_run: false`).
Run 3 (qwen3-coder-30b Player) → **APPROVED at turn 2**. Independently verified on disk:

- `installer/core/commands/lib/task_status_json.py` (257 lines, `def main()` at L205) — exists, executable.
- `tests/unit/commands/test_task_status_json.py` — in the **required** location (turn 1's complaint fixed in turn 2).
- `tests/test_task_status_json_integration.py` — integration test added.
- `pytest …` (worktree venv, independent of the orchestrator) → **9 passed**.
- Running the producer → **valid schema-v1 JSON** (`schema_version`, `summary` counts, `tasks[]`); single-task lookup handles not-found (AC-007).

The Coach verdict ([`coach_turn_2.json`](../../.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-001/coach_turn_2.json))
cited specific test names per AC and matched my independent run — **not a false-green.**

**Read:** swapping the Player (Coach unchanged) converted a failed build into a
real, honestly-verified build. Player intelligence is the lever that moves build
success on this substrate.

### Latent quality note (test-completeness, not Coach dishonesty)
The producer's recursive scan conflates agent `.md` files with tasks
(`tasks: list[1107]` vs `summary.total: 991`; first "task" is the
`zeplin-maui-orchestrator` agent). TSJ-001's own tests don't assert against this,
so it passed. This is a **SPEC_GAP** — exactly the QA-Verifier (FEAT-C332) target —
not a Coach failure.

---

## Finding 2 — `direct` mode is a false-green vector (TSJ-002) ⚠ NEW

TSJ-002 ("register bin entry + wire `--json` into specs", complexity 2,
`implementation_mode: direct`) was **APPROVED in 1 turn** with quality gates
`tests=True … audit=True ALL_PASSED=True` — but **all gates ran `required=False`**
(direct mode), so the Coach approved without AC-level disk verification. On disk:

| AC | Required | Delivered | Status |
|----|----------|-----------|--------|
| AC1 | `bin-entries.txt` → `lib/task_status_json.py` | Created a **new** wrapper `installer/core/commands/task-status-json.py` and registered **that** | ❌ deviation **+ broken** |
| AC2 | `--json` in installer spec | present (4 mentions) | ~ok |
| AC3a | `--json` in `.claude` spec | present (4 mentions) | ~ok |
| AC3b | remove `export:json` orphan | **still at `.claude/commands/task-status.md:325`** | ❌ unmet |
| AC4 | `--json`+TASK-ID = single object documented | not clearly documented | ❌/unclear |

**The registered bin entry is non-functional.** The wrapper has an off-by-one
`sys.path.insert` (inserts `<worktree>/installer`, needs `<worktree>/`), so:

```
$ python installer/core/commands/task-status-json.py
Traceback … from installer.core.commands.lib.task_status_json import main
→ ModuleNotFoundError   # emits a traceback, NO JSON
```

It also **re-introduces the exact `sys.path.insert(0, …)` hazard this repo has a
documented rule against** ([`.claude/rules/namespace-hygiene.md`](../../.claude/rules/namespace-hygiene.md)).
The real producer works; the wrapper fronting it does not, and TSJ-002's added
"integration test" is green over the broken wiring.

**Read:** the local coder Player makes plausible-but-spec-violating choices on
"simple" tasks, and **`direct` mode's relaxed gates approve them blind.** This is
a distinct, actionable harness gap — a member of the same *absent-signal /
green-over-broken-seam* family the QA-Verifier exists to close.
**Recommendation:** run AC-level disk verification (and the FEAT-C332 wiring
analyzer) **even in `direct` mode**, or stop setting the gates `required=False`
for it on the local substrate. File as a task (suggested `TASK-FIX-DIRECTFG01`).

---

## Finding 3 — specialist hang is real but non-fatal (H-Harness)

`run_specialist(test-orchestrator)` **hung both turns of TSJ-001** — `sdk_timeout
capped 3299s→600s (TASK-FIX-SPECHANG)`, then 30/60/90/120/150s pings of **no model
activity**, terminated at 150s (improved hang detector — vs run-2's 700s+), with
`validation=violation` injected. **Deterministic, not intermittent.**

Yet the build succeeded, because the Coach's **own independent pytest** is robust
to the hung specialist: turn 1 it correctly degraded the missing specialist
evidence to `partial_gate_abort → feedback` (the `absence-of-failure-is-not-success`
rule — absent signal ≠ pass), turn 2 its independent run passed → the real green.

**Read:** the specialist-invocation path is a genuine defect (wasted ~150s/turn +
violation noise) but a **cleanup/efficiency** item, **not** the build-blocker. It
goes on the queue, but below the Player and direct-mode-false-green levers.

---

## Finding 4 — gemma4-31b reasoning-mode tax ⚠

Pre-flight probe caught gemma4-31b emitting a `reasoning_content` channel (the
handoff said it had none — **serving config drifted since 06-13 morning**). It
still emits clean grammar-constrained verdicts (`finish=stop`, no truncation), so
it's **not** the catastrophic gemma4:26b F2 case — but with `reasoning_budget=unset`
+ `max_tokens=16384`, **turn-1's Coach took ~31 min** (vs documented 3.5–6.5).
Turn 2 was ~15 min (enough variance to converge inside the 80-min budget, but
narrowly).

**CORRECTED (runs 4–5, supersedes the "reasoning tax" diagnosis above):** the
~32-min Coach is **NOT a reasoning tax you can toggle off**. Verified empirically:

- `disable_thinking` (TASK-FIX-COACHREASON01, gkfactory `7526b55`) transmits
  correctly through langchain `extra_body` and suppresses `reasoning_content`
  (probe: `reasoning_len 0`, 19s) — but the real Coach is still ~32 min.
- Root cause: the Coach verdict grammar
  ([`coach-verdict.gbnf`](../../guardkit/orchestrator/grammars/coach-verdict.gbnf))
  is `root ::= prefix code-fence` with an **unbounded free-reasoning `prefix`**.
  gemma4-31b just relocates its reasoning into the grammar's *content* prefix and
  rambles toward `max_tokens` regardless of the toggle (1950s ≈ 16384 tok ÷ 8.4 t/s).
  Run 3 (reasoning channel) and run 4 (content prefix) were both ~32 min for the
  same reason: **gemma4-31b is just slow (6.5 t/s) and the grammar permits it.**
- **Fix = the Coach model, not the toggle.** Empirical review (real grammar +
  realistic prompt): **`gemma4-coach` (26b-A4B MoE) + `DISABLE_THINKING=1` →
  ~15–22s/turn, 3/3 valid verdicts, self-bounding at ~685 tok** (6× faster than
  gemma4-31b). And `disable_thinking` is **load-bearing for the MoE**: without it
  the MoE rambles to the ceiling and emits no verdict (the exact F2 that benched
  it post-06-13-restart). So COACHREASON01 is the *wrong* lever for dense
  gemma4-31b but the *right* one for the MoE. **Recipe Coach = `gemma4-coach` +
  `GUARDKIT_COACH_SYNTHESIS_DISABLE_THINKING=1`.**

---

## Runs 4–5 — validating the follow-up fixes live (FEAT-9DDE re-run from pre-merge base `740e1585`)

**Run 4** (Coach=`gemma4-31b` + DISABLE_THINKING=1) — killed mid-turn-2:
- **SPECINVOKE01 ✅**: specialists run with real model activity (`code-reviewer` 8.5 min, **no false 150s hang**); `validation=violation` is now a *real* review finding, not a hang artifact.
- **COACHREASON01 ❌ (latency)**: Coach still ~32 min — the corrected grammar-reasoning-prefix root cause above.

**Run 5** (Coach=`gemma4-coach` 26b MoE + DISABLE_THINKING=1):
- **Coach latency SOLVED ✅✅**: gemma4-coach turns were **35s and 51s** (vs gemma4-31b's ~32 min, ~55×).
- **gemma4-coach is a stricter judge**: feedback on all 3 turns, rejecting AC-005–010 (missing-frontmatter / malformed-file / single-task handling) — ACs that gemma4-31b *approved* at run-3 turn 2. Plausibly **more accurate** (the merged run-3 producer had the latent agent/task conflation gap from Finding 1).
- **NEW harness false-red → `unrecoverable_stall` (turn 3)**: the checkpoint pollution detector derives `tests_passed`/`test_count` from the **Player's self-report** (`tests_run=None` → `tests: fail, count: 0`), NOT the Coach gate (`tests=True`) or an independent run. Three turns of the Player not reporting counts read as "3 consecutive test failures" → false stall. Same `absence-of-failure-is-not-success` family, in the checkpoint layer. Only surfaced because the stricter Coach didn't approve early (run 3 exited at turn 2 before the counter hit 3). → **`TASK-FIX-CKPTTESTRED01`** (checkpoint pollution must key off the Coach gate / an independent run, or treat absent counts as *unknown*, never *failure*).
- **DIRECTFG01 / COACHCWD01: still unvalidated live** (wave 2 never ran; TSJ-001 stalled). DIRECTFG01 has a deterministic regression test; live validation needs a *converging* run, now blocked on the checkpoint false-red.

**Net:** Coach latency is solved (`gemma4-coach` + `disable_thinking`). The remaining blocker to a clean converging run — and to live-validating DIRECTFG01/COACHCWD01 — is the checkpoint-pollution false-red (CKPTTESTRED01). Evidence: `docs/retro/run5-evidence/`.

## Harness-health scorecard — everything that should hold, held

| Signal | Result |
|--------|--------|
| `verdict-emission failed` / `0 AssistantMessage` | **0** ✅ |
| `degrading to B-min` / `Recursion limit` (GATHER=0) | **0** ✅ |
| SPECVIOL01: specialist `validation=violation` → Player honesty `must_fix`? | **No** ✅ (stayed code-quality, not honesty) |
| absence-of-failure: `partial_gate_abort` → false-green? | **No** ✅ (→ feedback, AC-009 rejected) |
| WTESCAPE01: host source clean | ✅ only `FEAT-9DDE.yaml` + task frontmatter |
| Coach honesty (TSJ-001) | ✅ 10/10 populated criteria both turns, real independent pytest |

Two minor leaks: (a) the Coach's independent test run wrote `coverage.xml`/`coverage.json`
into the **host** cwd (cwd not pinned to worktree) — benign artifact, outside the
WTESCAPE01 source-watch set; (b) the run-3 worktree is intact and **not merged**
(host `bin-entries.txt` has 0 wrapper refs).

---

## Disposition & next moves

> **Update 2026-06-13 (post-run follow-ups landed):** TSJ-002 hand-fixed on
> `autobuild/FEAT-9DDE` (bin-entry → real producer, orphan removed; commit
> `fix(TASK-TSJ-002): …`) → **FEAT-9DDE is now mergeable**. Coach reasoning tax
> fixed (TASK-FIX-COACHREASON01, guardkitfactory `7526b55`). Follow-up tasks
> filed under `tasks/backlog/feat-9dde-followups/`.

1. **FEAT-9DDE is now mergeable** — the broken TSJ-002 wrapper + orphan are fixed
   on the feature branch and verified (bin target emits valid JSON; 9/9 TSJ-001
   tests pass). `/feature-complete FEAT-9DDE` (or a direct merge) is now safe.
   *Originally:* do NOT complete — TSJ-002 was broken (Finding 2).
2. **Strategic (answered):** spend freed (`qwen-graphiti` retire, ~28 GB) / new
   (DGX Spark, Mon 06-15) capacity on the **Player**. `qwen3-coder-30b` is
   validated as a converging Player; a larger Qwen3 is the upgrade path. Keep
   `gemma4-31b` as the honest Coach (now fast with DISABLE_THINKING=1).
3. **Filed — `TASK-FIX-DIRECTFG01`** (direct-mode false-green — AC-level/wiring
   verification even when gates are `required=False`): the highest-value new
   lever this run surfaced. The TSJ-002 hand-fix is only the point fix; this is
   the systemic one.
4. **Filed — `TASK-FIX-SPECINVOKE01`** (`test-orchestrator` deterministic
   zero-activity hang): real bug, non-fatal, below 1–3.
5. **Filed — `TASK-FIX-COACHCWD01`** (Coach independent-test cwd-leak writing
   coverage to the host repo): low priority.
6. **Server-side option (still open):** pin `gemma4-31b` / `gemma4:26b` out of
   reasoning mode on llama-swap — needs GB10 access; helps all consumers, not
   just the Coach. The client-side DISABLE_THINKING toggle (item 3 above) is the
   portable fix already landed.

## Evidence index
- Run-3 log: `.guardkit/autobuild/FEAT-9DDE-run3-stdout.log`
- Coach verdicts: `.guardkit/worktrees/FEAT-9DDE/.guardkit/autobuild/TASK-TSJ-001/coach_turn_{1,2}.json`
- Run-2 baseline (preserved): `docs/retro/run2-evidence/FEAT-9DDE/`
- Broken wrapper: `.guardkit/worktrees/FEAT-9DDE/installer/core/commands/task-status-json.py`
- Real producer: `.guardkit/worktrees/FEAT-9DDE/installer/core/commands/lib/task_status_json.py`
- Unremoved orphan: `.guardkit/worktrees/FEAT-9DDE/.claude/commands/task-status.md:325`
</content>
</invoke>
