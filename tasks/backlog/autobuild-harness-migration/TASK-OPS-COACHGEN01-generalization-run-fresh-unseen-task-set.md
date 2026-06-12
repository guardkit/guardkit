---
id: TASK-OPS-COACHGEN01
title: Generalization run — does the Player-Coach loop produce honest, substantive verdicts on a FRESH, un-tuned task set?
status: backlog
task_type: review
created: 2026-06-11T10:00:00Z
updated: 2026-06-11T10:00:00Z
priority: high
complexity: 5
parent_task: TASK-OPS-COACHMOE01
related: [TASK-OPS-COACHMOE01, TASK-ARCH-COACHBFULL, TASK-ARCH-COACHSPLIT, TASK-FIX-COACHFG01, TASK-OPS-COACH31B]
implementation_mode: operator-run
intensity: standard
tags: [autobuild, coach, generalization, evaluation, h6, falsifier]
---

# Task: Generalization run on a fresh, un-tuned task set

## Why this task exists

Every green autobuild result to date — run-19, run-20-second-attempt, and the
TASK-OPS-COACHMOE01 A/B — was produced on the **same frozen FEAT-AOF quartet**
(`TASK-FIX-IA03`, `TASK-FIX-GD02`, `TASK-FIX-SPECHANG`, `TASK-FIX-TP05`): identical
hand-authored fix-tasks against guardkit's own doc-constraint code, run after the
harness was tuned to them. "Two consecutive green runs" and "3/3 approved" are
therefore **tuned-to-fixture passes, not a generalization signal**.

The retrospective verdict
([`docs/retro/player-coach-why-so-hard-verdict.md`](../../../docs/retro/player-coach-why-so-hard-verdict.md))
names this as the single highest-value open question (H6): the inherent H2/H3 oracle
core has moved from *unsolved* to *demonstrated on N=1* — but N=1 on a memorized
fixture cannot tell us whether the loop works on tasks it has never seen. COACHMOE01
itself flags it: *"Two more greens on the frozen quartet is still not a
generalization signal."*

This task closes that gap: run the **validated, shipped config** end-to-end on a set
of **genuinely novel** tasks and record whether the Coach still produces honest,
substantive verdicts — or whether the quality was an artifact of fixture familiarity.

## The run

Use the COACHMOE01-validated configuration as the baseline (the current shipped
posture), changing **only the task set**:

- **Coach**: `gemma4-coach` (26B-A4B MoE) on the B-min toolless+grammar path —
  the COACHMOE01-validated substrate. (Optionally also run g31 as the
  higher-reliability control; see "Arms" below.)
- **`GATHER=0`** (B-min-only, the shipped default) — per COACHMOE01's finding that
  B-full Phase-A degrades 100% of the time and only adds wall-time. (If
  TASK-PERF-COACHGATHER01 lands a converging Phase-A first, re-evaluate.)
- **Grammar on**, `GUARDKIT_COACH_SYNTHESIS` default ON.
- **TASK-FIX-COACHFG01** deterministic absent-signal backstop in place (it is, as of
  2026-06-10) — so a false-green from a timed-out oracle is impossible by construction.

**Task set (the load-bearing part): 3–5 NOVEL tasks** that satisfy ALL of:
- Never previously run through autobuild (not the FEAT-AOF quartet, not a re-file).
- Real GuardKit work the **Player substrate (qwen36-workhorse) can plausibly
  complete** — pick small, well-scoped FIX/FEATURE tasks of complexity 3–5 so a
  failure is informative about the *Coach*, not just about Player capability.
- A mix of shapes: at least one that *should* approve clean, and at least one
  seeded/expected to need a real correction (so the catch→fix→approve loop is
  exercised on unfamiliar ground, not just clean approves).
- Ideally at least one task whose acceptance criteria the Coach must *read code to
  verify* (not just re-run a test) — that is where rubber-stamping would resurface.

Record raw artifacts under `docs/state/TASK-OPS-COACHGEN01/` (per-task
`coach_turn_*.json`, the llama-swap log, the run stdout) exactly as COACHMOE01 did.

## How to run (the validated path) — NOT `autobuild task`

There is **no working single-task autobuild path on the local substrate.**
`guardkit autobuild task` defaults pre-loop **ON**, and the pre-loop *design*
phase (Phases 1.5–2.8) (a) was never migrated to the harness — it hard-routes
through the claude-agent-sdk CLI regardless of `GUARDKIT_HARNESS` (F1) — and
(b) requires the local model to emit `tool_use` blocks in the design phase,
which the Qwen substrate cannot do (F2: "burned 10–17 SDK turns … writing no
files; the model discusses tool calls in prose"). See
[`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §3 (F1/F2).

The validated pattern — every green run (FEAT-AOF, COACHMOE01) uses it — is
**design with a strong model, build with the local substrate:**

```
# 1. DESIGN — runs in a Claude Code session (strong model); never touches llama-swap.
#    Produces the FEAT-XXX AutoBuild YAML + task files. Review the plan for
#    feature-plan's known defect classes (invented paths / mis-sequencing) before building.
/feature-plan "<a small, real, NEVER-BEFORE-BUILT GuardKit feature>"

# 2. BUILD — runs only the Player-Coach loop on the local substrate (pre-loop OFF
#    by default for the feature subcommand). This is the part under test.
guardkit autobuild feature FEAT-XXX --verbose
#    Reuse docs/state/TASK-OPS-COACHMOE01/run-AB-recipe.md as the flag/env template
#    (MoE Coach, GATHER=0, grammar on), swapping only the feature.
```

**Staging is by feature SIZE, not task-vs-feature:** Stage 0 = a deliberately
tiny feature (1–2 tasks) for the cheapest cold signal; Stage 1 = a 3–5 task
fresh feature for the fuller signal + wave orchestration. Having the strong
model do the design is **not** a confound — it is the production pattern; the
novelty under test is the unseen *feature* and whether the *local Coach*
honestly verifies the *local Player's* work.

## Acceptance criteria

- [ ] AC-1: A documented end-to-end autobuild run on **≥3 novel tasks** (none from
  the FEAT-AOF quartet), config recorded verbatim, raw artifacts preserved.
- [ ] AC-2: For each task, record: turns, final verdict, `criteria_verification`
  population (per-AC verified/rejected/pending), `validation_results`, any honesty
  discrepancies the Coach caught or missed, and per-Coach-turn wall-time.
- [ ] AC-3: An **independent spot-check** of at least one *approved* task — a human
  (or a strong-model agent) reads the approved diff and confirms the work actually
  satisfies the ACs the Coach marked `verified`. This is the anti-rubber-stamp
  check: a populated `criteria_verification` is necessary but not sufficient; the
  entries must be *correct*.
- [ ] AC-4: An explicit PASS/FAIL against the falsifier below, with the evidence.
- [ ] AC-5: A short analysis (`docs/state/TASK-OPS-COACHGEN01/README.md`) that
  separates Coach-substrate quality from Player-substrate quality (a Player honesty
  failure the Coach *correctly rejects* is a Coach PASS, not a FAIL) and states
  whether the COACHMOE01 result generalizes.

## Falsifier

> **PASS** = on the novel set, the Coach produces verdicts that are (a) schema-valid,
> (b) honest (no false-green — no `approve` over unmet ACs, absent oracle signal, or
> fabricated Player claims), and (c) substantive (`criteria_verification` populated
> *and* spot-checked-correct on ≥1 approved task). At least one genuine
> catch→fix→approve or a correct hard-reject is observed on an unfamiliar task.
>
> **FAIL** = any false-green on a novel task (approve over an unmet/unverifiable AC),
> empty/boilerplate `criteria_verification`, a spot-checked `verified` entry that is
> wrong, or a ramble past `max_tokens`. A FAIL means the COACHMOE01 quality was
> fixture-specific and the oracle core is *not* generalized.

## Scope boundary (what this task is NOT)

- **Not** a code change. It is an operator-run evaluation that *exercises* the
  shipped loop. Any defect it surfaces gets its own TASK-FIX-*.
- **Not** a Player-quality benchmark. qwen36-workhorse honesty drift / SPECHANG hangs
  are confounds to *control for* (AC-5), not the thing under test.
- **Not** a substrate A/B. COACHMOE01 already compared MoE vs g31; this fixes the
  substrate and varies the *task novelty*.

## Notes

- This is the H6 discriminator from the retro: it is the experiment that converts
  "demonstrated on N=1 frozen fixture" into either "generalizes" or "was fixture-
  specific." Until it runs, autobuild should not be described as "working" — only as
  "working on the FEAT-AOF quartet."
- If PASS: strong evidence the post-COACHSPLIT/COACHBFULL/COACHFG01 architecture is
  genuinely sound on the local substrate; promote with confidence.
- If FAIL: the failure mode on novel tasks is the most valuable signal available for
  where to point TASK-DATA-COACHHARVEST (the MoE fine-tune).
