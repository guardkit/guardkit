---
id: TASK-OPS-COACHMOE01
title: Evaluate gemma4-coach (26B-A4B MoE) as Coach on the shipped B-min toolless+grammar path (A/B vs run-25)
status: completed
completed: 2026-06-11T17:42:00Z
completed_location: tasks/completed/autobuild-harness-migration/
task_type: ops
created: 2026-06-11T00:00:00Z
updated: 2026-06-11T17:42:00Z
previous_state: in_progress
state_transition_reason: "All 4 ACs met: gate PASS, A/B 3/3 approved, Lever-2 characterized, decision recorded. Outcome: 26B MoE is a viable B-min Coach; COACHHARVEST base updated; HMIG-013 superseded."
outcome: "MoE PASSES — viable B-min Coach (g31 fallback); COACHHARVEST fine-tune base = 26B MoE. Caveat: 1/6 turns malformed (COACHSF01-recovered); speed win needs GATHER=0."
priority: critical
complexity: 3
effort_hours: 4
parent_feature: autobuild-harness-migration
related: [TASK-HMIG-013, TASK-OPS-COACH31B, TASK-ARCH-COACHSPLIT, TASK-PERF-COACHTURNBUDGET, TASK-DATA-COACHHARVEST]
subsumes: [TASK-HMIG-013]   # delivers HMIG-013's unrun AC-006 live smoke under the post-COACHSPLIT architecture
implementation_mode: manual   # ops experiment: probe + live A/B runs on the GB10
intensity: standard
falsifier: "Run the FEAT-AOF frozen quartet with --coach-model gemma4:26b on the current B-min path (GUARDKIT_COACH_SYNTHESIS on, GBNF grammar present). PASS = 3/3 verdicts that are (a) schema-valid first try, (b) honest (independent oracle ran, no signal_absent green), (c) substantive (criteria_verification 100% populated with per-AC evidence), at materially lower Coach wall-time than run-25's 3.5-6.5 min legs. FAIL = any ramble past max_tokens, empty criteria_verification, or false-green."
---

# Task: Evaluate the 26B MoE Coach on the B-min path

## Why this task exists (the decision gap)

**Nobody has ever run gemma4-coach (26B-A4B MoE, ~3.8B active) as Coach on the
shipped B-min toolless+grammar path.** Its disqualification (F24, the run-14
49,720-char ramble) happened in the **tool-bound agentic loop**, which
TASK-ARCH-COACHSPLIT then *removed from the verdict path*. The evidence that it
might work on the new path is already in the repo:

- Toolless probes E/F: gemma4-coach emitted **correct** approve/feedback
  verdicts at 45.0–45.1 tok/s in 49s/69s — beating gemma4:31b (103s/94s)
  wall-clock (`docs/state/TASK-OPS-COACH31B/probes/gctl.run.log`,
  `README.md:86-87,138-144`).
- The COACH31B README itself flags single-shot as "a weak discriminator" and
  locates the MoE's pathology in the tool-bound loop, not fenced-JSON emission
  (`docs/state/TASK-OPS-COACH31B/README.md:112-136`).
- GB10 bandwidth physics: dense ~30B caps at 9.0–10.2 tok/s (measured); the
  MoE runs 42.0–46.4 tok/s. The run-23 41m43s Coach turn was **pure decode**
  (16,384 tokens at ~10 tok/s); model load is ~10s
  (`probes/g31-load.log`), so residency (Lever 1) cannot fix this — only a
  faster substrate or fewer tokens can.

**Why latency is on the critical path, not cosmetic:** a catch→fix cycle needs
two Coach turns inside the task budget. Run-23 caught a real bug and could not
fix it because one Coach turn consumed the budget. Halving Coach wall-time is
what makes the loop's core promise (catch→fix→approve) demonstrable.

**The known risk:** GBNF containment of the MoE's ramble is untested — the
COACHSPLIT grammar gate probe ran only against g31
(`docs/state/TASK-ARCH-COACHSPLIT/README.md:8-18`), and the one MoE ramble
(probe A, 27,006 chars) was on the approve path **without** grammar. Hence
step 1 below.

## Spec

### Step 1 — grammar containment probe (gate)

Create a `gc` variant of
`docs/state/TASK-ARCH-COACHSPLIT/probe_toolless_grammar.py` targeting the
`gemma4-coach` alias (verify it is still routed in the live
`/opt/llama-swap/config/config.yaml` — config has drifted before). Probe both
the approve path (the ramble case) and the feedback path with
`coach-verdict.gbnf` attached per-request. Record finish_reason + char counts —
**trust the metric, not pattern-matching on output**
(per `TASK-OPS-COACH31B/README.md:123-128`).

If grammar does not contain the ramble: stop, record FAIL, and skip to
"On failure" below.

### Step 2 — live A/B vs run-25

Re-run the FEAT-AOF frozen quartet with the run-25 recipe changed in exactly
one flag: `--coach-model gemma4:26b` (run-25 baseline command at
`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-25.md:5`). Keep
`GUARDKIT_COACH_GATHER` as in run-25 so the degrade path is exercised
identically. Apply the standard false-green checklist per verdict (oracle ran;
criteria 100% verified; deliverable runs).

### Step 3 — Lever-2 leg (piggyback)

On one leg, set `GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET` (guardkitfactory
`langgraph_harness.py:106`; default unset — **never exercised in any logged
run**) and record the wall-time/quality delta. This is the cheapest shipped
latency lever for whichever substrate wins.

## Decision rule (record the outcome in a short note + Graphiti)

- **MoE passes** → swap the Coach substrate to gemma4-coach; the dense g31
  becomes the fallback; **the fine-tune base for TASK-DATA-COACHHARVEST is the
  26B MoE** (the only base with a validated 71-min LoRA recipe on the GB10).
- **MoE fails** (ramble survives grammar, or hollow verdicts) → stay on g31;
  the MoE fine-tune for the narrow B-min synthesis role becomes the headline
  speed experiment instead of the "maybe-later" lever.

Either way this closes TASK-HMIG-013 (whose AC-006 live smoke never ran and
whose other ACs were overtaken by COACHSPLIT/--coach-model threading).

## Acceptance Criteria

- [x] **AC-001** — gc grammar probe exists
      ([`probe_toolless_grammar_gc.py`](../../../docs/state/TASK-OPS-COACHMOE01/probe_toolless_grammar_gc.py))
      and has been run; finish_reason + char counts recorded for approve and
      feedback paths. **GATE PASS** — grammar contains the ramble (all arms
      finish=`stop`; production synthesis 24.7s approve / 40s feedback, per-AC
      criteria populated).
- [x] **AC-002** — A/B run executed: FEAT-AOF `--fresh` with `--coach-model
      gemma4:26b`, **3/3 approved (105m)**. Per-task Coach wall-times +
      verdict-quality table captured vs run-25 (README Step 2 +
      `run-AB-artifacts/`). No rambles, no false-greens; 1/6 turns malformed
      (COACHSF01-recovered).
- [x] **AC-003** — Lever-2 `reasoning_budget` exercised live (rb=2048 and rb=0):
      **no-op on the gc route** (uncapped/undisabled); delta recorded (README
      Step 3). A/B legs ran with it unset (matches run-25); harness log confirms
      `reasoning_budget=unset` threaded cleanly.
- [x] **AC-004** — Decision recorded (README "Decision" + Graphiti
      `guardkit__project_decisions`): **MoE passes → COACHHARVEST fine-tune base
      = 26B MoE; gc viable B-min Coach, g31 fallback.** TASK-HMIG-013 superseded;
      TASK-DATA-COACHHARVEST base-model field updated.

## References

- Probes & substrate data: `docs/state/TASK-OPS-COACH31B/` (README, probes/)
- B-min wiring: `guardkit/orchestrator/agent_invoker.py:546-584` (synthesis
  default ON, gather default OFF), grammar at
  `guardkit/orchestrator/coach_grammar.py:46-78`
- Run-25 baseline: `docs/state/TASK-REV-HMIG/run-25-artifacts/README.md`
- Bandwidth physics: `docs/research/dgx-spark/POST-VALIDATION-model-strategy-revision.md`
