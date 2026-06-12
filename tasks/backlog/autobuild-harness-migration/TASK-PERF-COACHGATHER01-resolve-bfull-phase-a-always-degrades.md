---
id: TASK-PERF-COACHGATHER01
title: Resolve B-full Phase-A always-degrades — raise recursion_limit so the gather converges, or formally retire B-full
status: backlog
task_type: fix
created: 2026-06-11T10:05:00Z
updated: 2026-06-11T10:05:00Z
priority: medium
complexity: 5
parent_task: TASK-ARCH-COACHBFULL
related: [TASK-ARCH-COACHBFULL, TASK-OPS-COACHMOE01, TASK-PERF-COACHSYNTH, TASK-ARCH-COACHSPLIT, TASK-OPS-COACH31B]
implementation_mode: task-work
intensity: standard
tags: [autobuild, coach, b-full, gather, performance, recursion-limit, promotion-criteria]
---

# Task: Resolve B-full Phase-A always-degrades

## Why this task exists

TASK-OPS-COACHMOE01 (2026-06-11) ran the live A/B with `GUARDKIT_COACH_GATHER=1`
(B-full) and found the **tool-using Phase-A gather degrades to B-min on 100% of
turns, for *both* substrates** (MoE and g31): every turn logged
`Recursion limit of 12 reached … degrading to B-min synthesis`. The gather never
converges to a verdict-relevant investigation before tripping
`_COACH_GATHER_RECURSION_LIMIT` (= 12, ≈6 tool round-trips), so B-full currently
adds wall-time with **zero investigation value** — the verdict is always synthesised
from the deterministic bundle alone, exactly as B-min would have.

This directly **fails two of TASK-ARCH-COACHBFULL's own promotion criteria**:

- **P-2** ("the gather phase is observed *actually running* … not silently always-
  degrading to B-min") — **violated**: it degrades 100% of the time.
- **P-5** ("per-turn latency is acceptable as the default") — **violated**: B-full
  doubles g31 calls/turn and, with `GATHER=1`, the wasted Phase-A overhead dominated
  the turn (COACHMOE01: approve turns ran 124–293s with `GATHER=1` vs the ~24–40s
  B-min synthesis the gate measured).

So B-full is presently **dead weight when enabled** — the COACHBFULL investment
(restoring the investigating Coach) does not pay off, and the promotion track is
blocked. This task forces the decision the COACHMOE01 follow-ups (b) named: *either
make Phase-A converge, or formally retire B-full pursuit and ship B-min-only.*

## Investigate first (this is the load-bearing step)

Before choosing a fork, determine **WHY Phase-A hits the recursion ceiling every
time**. Read the COACHMOE01 gather transcripts
(`docs/state/TASK-OPS-COACHMOE01/run-AB-artifacts/`, the llama-swap log + any
Phase-A turn dumps). Distinguish:

- **(i) Genuine deep investigation truncated** — the Coach is productively reading
  files / running tests and simply needs more than ~6 round-trips to cover the ACs.
  → raising the limit *helps* (Option A is viable).
- **(ii) Unproductive looping** — the Coach repeats reads, thrashes, or never moves
  toward a conclusion. → raising the limit just wastes more time and context
  (Option A is futile; Option B is correct).

The `_COACH_GATHER_RECURSION_LIMIT` comment claims "a genuine focused investigation
(a handful of reads) concludes well below this; only a runaway trips it." COACHMOE01
falsifies that claim for this codebase's Coach prompt depth — the task is to find out
which of (i)/(ii) is true and act on it.

## The decision fork

### Option A — make Phase-A converge

Raise/scale `_COACH_GATHER_RECURSION_LIMIT`
([`agent_invoker.py:622`](../../../guardkit/orchestrator/agent_invoker.py), env
`GUARDKIT_COACH_GATHER_RECURSION_LIMIT`) — and/or tune the gather prompt to reach a
conclusion sooner — so Phase-A genuinely concludes (two distinct g31/MoE calls per
Coach turn: a real tool-bound gather *then* the toolless synthesis), satisfying P-2.

**Hard constraint:** more tool cycles ⇒ more context growth ⇒ the F20 / run-22 TP05
98 K-overflow surface. The per-tool-result truncation
(`_COACH_GATHER_MAX_TOOL_RESULT_CHARS` = 12000) and the
`langgraph_harness.py` `recursion_limit` bound were sized *together* (worst case
`RECURSION_LIMIT × MAX_TOOL_RESULT_CHARS` ≈ under the 98 K window). Any raise MUST be
re-checked against that budget — a larger limit may require a smaller per-result
truncation to stay under the window. Validate on the live substrate that Phase-A
converges **without** a 400 overflow.

### Option B — formally retire B-full, ship B-min-only

Accept `GATHER=0` (B-min-only) as the **permanent** shipped default (it is already
the runtime default), and:
- Mark TASK-ARCH-COACHBFULL's promotion track **closed as "not pursued"** with
  COACHMOE01 as the cited evidence (Phase-A does not converge at acceptable cost on
  this codebase's Coach prompt depth), so the criteria don't sit open indefinitely.
- Quantify the B-min-only per-turn speedup end-to-end (COACHMOE01 follow-up (a)) —
  the MoE's ~30–60s synthesis vs g31's 3.5–6.5 min — so the operational default is
  evidence-backed.
- Decide whether to keep the B-full code path behind the flag as documented-but-
  dormant (cheap, reversible) or remove it (reduces the 53 K-LOC surface). Default
  recommendation: **keep behind the flag** unless it carries maintenance cost, since
  a converging Phase-A may become viable post-fine-tune.

## Acceptance criteria

- [ ] AC-1: A written root-cause for the 100%-degrade, classified (i) truncated-but-
  productive vs (ii) unproductive-loop, with transcript evidence from the COACHMOE01
  artifacts (or a fresh `GATHER=1` probe run).
- [ ] AC-2: A decision (Option A or B) justified by AC-1.
- [ ] AC-3 (if Option A): the new recursion limit (and any prompt/truncation change)
  is implemented, re-checked against the 98 K-window budget, and a live validation
  run shows Phase-A **converges** (two distinct Coach LLM calls per turn observed in
  the llama-swap log) on ≥2 Coach turns **without** a context-overflow 400 — i.e.
  P-2 is now satisfiable.
- [ ] AC-3 (if Option B): `GATHER=0` confirmed as the documented permanent default;
  TASK-ARCH-COACHBFULL promotion criteria marked closed-not-pursued with the
  COACHMOE01 citation; the B-min-only per-turn speedup quantified and recorded.
- [ ] AC-4: No regression — `GATHER=0` runs are byte-for-byte unaffected by any
  change (the fix touches only the B-full path / its defaults / its docs).
- [ ] AC-5: Existing harness + Coach tests stay green
  (`tests/orchestrator/`, guardkitfactory `tests/.../test_langgraph_harness*`).

## Scope boundary

- **Not** TASK-PERF-COACHSYNTH (that bounds the *synthesis* call latency / keeps g31
  resident). This task is specifically about the *Phase-A gather* convergence vs
  retirement. They compose: COACHSYNTH's resident-model work is what would make
  Option A's doubled-call latency tolerable (P-5).
- **Not** a change to `GATHER`'s default (it is already OFF). This decides the
  *future* of the B-full path, not the current shipped posture.
- **Not** the generalization question (TASK-OPS-COACHGEN01) — that fixes the config
  and varies the task set; this fixes the task set and decides the gather config.

## Notes

- Priority is **medium**, not high: the shipped default is already `GATHER=0`, so
  there is no live false-result risk — B-full is opt-in and currently no worse than
  B-min (just slower) when opted into. The cost of inaction is an open promotion
  track and a dormant, non-functional investigation feature.
- Surfaced in [`docs/retro/player-coach-why-so-hard-verdict.md`](../../../docs/retro/player-coach-why-so-hard-verdict.md)
  (Update 2026-06-11, "What is genuinely still open") and recommended directly by
  TASK-OPS-COACHMOE01 §Decision follow-up (b).
