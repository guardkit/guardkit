---
id: TASK-PERF-COACHTURNBUDGET
title: Bound Coach-turn latency so the B-full catch→fix cycle fits in the task budget
status: completed
task_type: feature
created: 2026-06-10T00:00:00Z
updated: 2026-06-10T00:00:00Z
previous_state: in_review
completed: 2026-06-10T00:00:00Z
completed_location: tasks/completed/2026-06/
state_transition_reason: "code complete; Lever 2 (synthesis reasoning-budget knob) + Lever 3 (B-full budget docs) landed + unit-tested; AC-1 (ops/TASK-OPS-COACH31B) + AC-2/AC-4/AC-5 (live GB10 falsifier) deferred as out-of-code-scope follow-ups"
priority: high
complexity: 5
parent_task: TASK-HMIG-010
related: [TASK-PERF-COACHSYNTH, TASK-ARCH-COACHBFULL, TASK-OPS-COACH31B, TASK-FIX-MAXPARALLEL01]
implementation_mode: task-work
intensity: strict
---

# Task: Bound Coach-turn latency so the catch→fix cycle fits in budget

## Why this task exists

Run-23 is the run where the Coach **grew teeth** — TP05's B-full Coach caught a
real Player regression (`feedback`, AC-002/003/004 `rejected`, a **critical
`TypeError` in `specialist_invocations.py:924`**) instead of rubber-stamping.
That is the win the whole arc was chasing.

**But the loop could not act on it.** TP05's Coach turn took **41m43s** (the
synthesis hit the 16 384 `max_tokens` ceiling — a 60 KB response — on dense
gemma4:31b), which **exhausted the 80-min task budget before turn 2 could
apply the fix** → `TIMEOUT_BUDGET_EXHAUSTED`. So the Coach found the bug and
then the loop ran out of time to let the Player fix it. A reviewer that catches
bugs but starves the fix cycle is only half a loop.

TASK-PERF-COACHSYNTH bounded the **gather** (Lever A — done; F20-context
overflow). Its **synthesis-latency levers were deferred** (resident g31, bound
synthesis prompt, cap generation). Run-23 proves they are now load-bearing:
the 41-min turn is the synthesis, not the gather.

## The tension to respect (do NOT make the Coach lazy)

The 41 minutes bought something real — a **thorough investigation that caught a
TypeError**. The fix is **not** "cap `max_tokens` low" (that would truncate the
`criteria_verification` + `issues` that *are* the bug report). The latency is
mostly **(a)** g31 cold-loading ~50 GB every Coach turn and **(b)** dense-31B
generating ~16 K tokens of `reasoning_content` + verdict under `--reasoning
auto`. Cut the latency **without** cutting the verdict substance or the
investigation depth.

## Levers

- **Lever 1 — keep g31 resident (biggest fixed win).** Stop llama-swap evicting
  g31 between Coach turns (the `coach31` set is `qw & g31`; the Player only needs
  `qw`). Removes the per-turn ~50 GB reload. (= COACHSYNTH AC-3, unshipped.)
- **Lever 2 — tune synthesis generation.** Stop the synthesis grinding to the
  16 384 ceiling on a complex task: cap/curtail `reasoning_content` (e.g.
  `--reasoning` budget or a lower synthesis `max_tokens` that still fits a full
  verdict), so generation stops when the verdict is done, not at the token cap.
  Verify `criteria_verification` + `issues` survive intact (no truncation).
- **Lever 3 — give B-full turns enough budget for ≥2 turns.** A catch→fix cycle
  is *two* Coach turns. If a single B-full turn can be ~40 min, an 80-min
  `--task-timeout` cannot fit two. Either cut per-turn latency (Levers 1–2) until
  two turns fit, OR raise the B-full `--task-timeout` as an explicit interim
  (document the number and why). Real fix is latency; budget bump is a stopgap.

## Acceptance criteria

- [ ] **AC-1 (resident g31)** — **OPS, out of code scope.** g31 is not cold-loaded
  every Coach turn (llama-swap log shows no per-turn `evict=[gemma4-31b]` + reload).
  llama-swap keepalive on the GB10 — tracked under **TASK-OPS-COACH31B** (same lever
  COACHSYNTH deferred as its AC-3). Not a change in either repo.
- [ ] **AC-2 (turn fits the fix cycle)** — **LIVE RUN, out of code scope.** A B-full
  Coach turn (gather + synthesis) on a TP05-class task completes within a bound that
  leaves room for a **second** turn inside `--task-timeout` (target: one turn ≤ ~50%
  of the task budget). The *code knobs* to hit this bound landed (Lever 2 + Lever 3
  below); the empirical "completes within bound" measurement is the AC-4 falsifier run.
- [x] **AC-3 (substance preserved)** — *code landed; live confirmation is AC-4.* The
  reasoning-curtailment lever (Lever 2) caps the `reasoning_content` phase via a
  per-request `reasoning_budget` field **without** touching `max_tokens`
  (`GUARDKIT_COACH_SYNTHESIS_MAX_TOKENS`, default 16384, stays independent of the
  gather's `max_tokens_coach`), so the verdict's `criteria_verification` + `issues`
  are NOT truncated — the AC-3 tension. Unit-tested: `test_does_not_lower_max_tokens`,
  `test_merges_with_grammar_string_path` (`tests/harness/test_langgraph_harness_synthesis.py`,
  guardkitfactory). The "no longer grinds to `max_tokens` on a complex task" half is
  confirmed empirically at AC-4.
- [ ] **AC-4 (catch→fix falsifier — the real one)** — **LIVE RUN, out of code scope.**
  A re-run where the Coach catches a real Player bug (turn 1 `feedback`) **and turn 2
  actually runs and applies a fix within budget** — the run-23 failure inverted. Run
  on the GB10 with `GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET` set (Lever 2) and a
  B-full-sized `--task-timeout` (Lever 3); also confirms the `reasoning_budget`
  wire-field is honoured by the deployed llama.cpp build. (Mirrors COACHSYNTH's
  deferred live falsifier AC-5.)
- [ ] **AC-5 (depth preserved)** — **LIVE RUN, out of code scope.** The Coach still
  catches the run-23-class `TypeError` (don't trade bug-detection for speed). Verified
  as part of the AC-4 run — the reasoning budget curtails *thinking*, not the
  tool-using gather depth (which Lever A/COACHSYNTH bounds separately).

## Implementation (run by /task-work, 2026-06-10)

**Decision (user, strict checkpoint):** Lever 2 + Lever 3, mirror COACHSYNTH; add a
**default-off** per-request reasoning-curtailment code field. AC-1 (ops) + AC-2/AC-4/AC-5
(live GB10) explicitly deferred — they need the GB10 substrate, not a code change.

**guardkitfactory** (`../guardkitfactory`) — Lever 2, primary deliverable:
- `harness/langgraph_harness.py` — `_SYNTHESIS_REASONING_BUDGET_ENV`
  (`GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET`) + `_synthesis_reasoning_budget()` helper
  (mirrors `_synthesis_max_tokens()`; unset/empty/non-int → `None` → field omitted →
  behaviour unchanged). `_build_synthesis_model` merges `grammar` +`reasoning_budget`
  into a single None-able `extra_body` so both construction paths (injected
  `BaseChatModel.bind(...)` and the production chat-completions `ChatOpenAI`) carry it;
  log line + bind-failure warning updated.
- `tests/harness/test_langgraph_harness_synthesis.py` — `TestSynthesisReasoningBudget`
  (8 tests): default-off omits field; int injects `reasoning_budget`; merges with
  grammar; `max_tokens` untouched (AC-3); `-1` unlimited honoured; non-int → unset;
  injected-model bind; helper returns None when unset.

**guardkit** (this repo) — Lever 3, config/doc (no default bump, by design — a global
default change would affect non-B-full runs):
- `guardkit/cli/autobuild.py` — `--task-timeout` help text now notes the B-full ≥2-turn
  (catch→fix) budgeting consideration and points at the deep-dive.
- `docs/deep-dives/autobuild_local_vllm.md` — new "B-full Coach latency budgeting"
  section documenting all three levers, the run-23 evidence, and the recommended
  "one turn ≤ ~50% of budget" target.

**Test status:** guardkitfactory harness suite **70 passed** (8 new), 0 regressions.
guardkit `test_cli_autobuild.py` **68 passed**; `--task-timeout` help renders on
`autobuild feature`. Broad guardkit orchestrator collection errors are pre-existing
env gaps (`langchain_core` / SDK not installed in the guardkit venv — those modules
live in the guardkitfactory venv where the synthesis tests ran green), unrelated to
this change.

**Cross-repo install note:** co-versioned with guardkitfactory, like COACHSYNTH. Deploy
the guardkitfactory `langgraph_harness.py` change alongside this repo. The new env knob
is default-off, so deploying either repo first is safe.

## Notes

- This is the **synthesis-latency half** of TASK-PERF-COACHSYNTH (gather bound =
  Lever A, completed; this = Levers B/C/D). Filed separately because COACHSYNTH is
  already `completed` and the gather bound is validated-ish.
- Evidence: run-23 (`docs/state/TASK-REV-HMIG/run-23-artifacts/`) — TP05 41m43s /
  60 KB synthesis → `TIMEOUT_BUDGET_EXHAUSTED` before turn 2.
- Coordinate Lever 1 with TASK-OPS-COACH31B (the `coach31` set + keepalive policy
  on the GB10).
- Pairs with TASK-FIX-MAXPARALLEL01 (keep Coach calls sequential → no F20) — that
  fixes *availability*; this fixes *throughput* (the fix cycle).
