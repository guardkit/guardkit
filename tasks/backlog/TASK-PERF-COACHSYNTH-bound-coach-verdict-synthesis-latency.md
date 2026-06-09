---
id: TASK-PERF-COACHSYNTH
title: Bound Coach verdict-synthesis latency — keep g31 resident + cap the synthesis prompt
status: backlog
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-09T00:00:00Z
priority: medium
complexity: 5
parent_task: TASK-HMIG-010
related: [TASK-ARCH-COACHSPLIT, TASK-FIX-COACHTESTTO, TASK-OPS-COACH31B, TASK-ARCH-COACHBFULL]
implementation_mode: task-work
---

# Task: Bound Coach verdict-synthesis latency

## Why this task exists

TASK-FIX-COACHTESTTO removed the 3×300s independent-test timeouts from the
Coach loop — yet **run-20's wall-time (52m31s) was essentially identical to
run-19's (52m04s)**. The ~15 min that should have been saved was **entirely
absorbed by the verdict-synthesis call growing slower per task**. GB10
llama-swap wire data for run-20's three Coach turns:

| Coach turn | verdict status | verdict size | synthesis duration |
|---|---|---|---|
| task 1 | 200 | 7954 B | **4m55s** |
| task 2 | 200 | 9793 B | **7m33s** |
| task 3 | 200 | 11267 B | **10m05s** |

So the toolless g31 verdict synthesis (TASK-ARCH-COACHSPLIT D-3) is now the
**dominant and growing** cost of a Coach turn. It passed this run (10 min ≪
the 3600s `--sdk-timeout`), but the **monotonic growth** is a scaling risk: a
feature with more/larger tasks could push a verdict toward the timeout.

Two compounding causes, both visible in the llama-swap log:

1. **g31 cold-loads on *every* Coach turn.** Between Coach turns the Player
   runs and llama-swap evicts g31 for the default set (`set=coach31` …
   `evict=[gemma4-31b]` … `set=coach31`, repeated each turn), so every
   verdict pays the ~50 GB g31 reload before generating.
2. **The synthesis input/output grows across the feature** — later tasks
   carry more context (cumulative `peer_changed_files`, a larger worktree →
   bigger deterministic `CoachEvidenceBundle`), and with `--reasoning auto`
   + the 16 384 `max_tokens` budget, g31 generates progressively more
   (verdict bytes 7954 → 11267).

This is a **performance/scaling** task, not a correctness fix — run-19 and
run-20 both passed 3/3 first-pass approve.

## Levers (investigate both; the implementer with full GB10 access decides)

- **Lever A — keep g31 resident across the run.** Avoid the per-turn ~50 GB
  cold-load by not evicting g31 between Coach turns (llama-swap set policy
  and/or the orchestrator's per-turn model-set request). Interacts with GB10
  unified-memory budget — the `coach31` minimal set (`qw & g31`) was chosen
  for memory headroom (TASK-OPS-COACH31B); keeping g31 pinned while the
  Player runs (Player only needs `qw`, already in `coach31`) may avoid the
  switch to the heavier default set entirely. Verify the memory math.
- **Lever B — bound the synthesis prompt.** Cap the evidence/context fed to
  the toolless synthesis call so per-task verdict input (and thus generation
  time) does not grow unbounded: extend the existing truncation discipline
  (`_COACH_BDD_DISCOVERIES_LIMIT` etc. in `_render_evidence_bundle_section`)
  to `peer_changed_files`, accumulated context, and overall prompt size in
  `agent_invoker._build_coach_prompt`. Truncation MUST mark what was dropped
  (respect `.claude/rules/absence-of-failure-is-not-success.md` — never
  silently drop oracle signal).
- **Lever C — cap generation.** Consider a synthesis-specific `max_tokens` /
  `reasoning_mode` tune if reasoning_content growth (not input) is the driver.

## Acceptance criteria

- [ ] **AC-1 (root-cause split)**: decompose each verdict's latency into
  cold-load vs prompt-eval vs generation (instrument the synthesis call or
  read llama.cpp server timings). Quantify how much of the 4m55→10m05 growth
  is the per-turn cold-load (Lever A) vs growing generation (Lever B/C), with
  the synthesis input token count per task.
- [ ] **AC-2 (g31 resident)**: a config/policy change so g31 is NOT cold-
  loaded on every Coach turn — verified in the llama-swap log (no per-turn
  `evict=[gemma4-31b]` + reload). Report the per-turn latency reduction.
- [ ] **AC-3 (bounded synthesis input)**: the synthesis prompt size is bounded
  (evidence bundle + context + peer_changed_files capped), truncation is
  marked, and per-task verdict latency no longer grows unbounded. Document the
  cap + rationale.
- [ ] **AC-4 (scaling falsifier)**: on a ≥5-task feature (or a synthetic
  large-worktree task), the last Coach verdict's synthesis latency stays
  within a bounded multiple of the first (target < 2×) and well under
  `sdk_timeout`. If a hard ceiling is found instead, document it.
- [ ] **AC-5 (no quality regression)**: verdict correctness preserved —
  re-run FEAT-AOF and confirm 3/3 first-pass approve, schema-valid verdicts,
  no new false-rejects.

## Notes

- Empirical source: run-20 GB10 llama-swap wire data + the run-19↔run-20
  wall-time wash. Snapshots: `docs/state/TASK-REV-HMIG/run-20-artifacts/`.
- Coordinate the GB10 side with TASK-OPS-COACH31B (the run-15 recipe + the
  `coach31` matrix set + keepalive policy).
- Independent of TASK-ARCH-COACHBFULL, but note B-full adds a SECOND g31
  call per Coach turn (the tool-using gather) — so Lever A (resident g31)
  becomes more valuable if B-full lands. Sequence accordingly.
- Surfaced while reviewing the run-20 snapshot commit (2026-06-09).
