---
id: TASK-QAV-007
title: First real feature shipped with a declared L4 behavioural oracle (FEAT-MEM-05 parity harness as the instance)
task_type: feature
priority: medium
status: backlog
created: 2026-07-05T12:20:00+01:00
tags: [qa-verifier, behavioural-oracle, dogfood, fleet-memory]
---

# Task: Ship the first real feature that declares an L4 behavioural oracle

## Context

QAV Phase 0 is code-complete on main (L1 wiring June; L2 anti-stub + L3
coverage merged `888906f2`; L4 behavioural-oracle guard AND producer merged
`fe949bb0`, 2026-07-04). The L4 oracle has so far been validated only
against the fs-01 fixture case (FEAT-MEM-04 false green, verdict-flip
proven in TASK-QAV-006 run 1) and a deliberate in-build AC-3 independence
proof. **No real feature has yet shipped with a declared oracle** — the
gate has never run over live, novel work end-to-end.

The intended first instance (per the 2 July QAV starter §oracle and the
consolidation doc): a **fleet-memory feature declaring the FEAT-MEM-05
parity harness** as its behavioural oracle. Note the harness has since
been *run* once as the FEAT-MEM-08 cutover gate ("FEAT-MEM-05 parity
PASSED", `tasks/backlog/memory-cutover/README.md`) — what has NOT happened
is a feature *declaring* it through the L4 convention so the Coach
consumes it as independent evidence during an autobuild run.

## Acceptance criteria

- [ ] AC-1: An autobuild feature run (GB10 recipe per
  `docs/retro/qa-verifier-state-consolidation-2026-07-04.md` §1/§3) where at
  least one task's worktree carries a declared behavioural oracle at the
  merged convention path, authored INDEPENDENTLY of the Player (pre-seeded
  or operator-authored), and the Coach evidence bundle shows
  `behavioural_oracle` populated (`ran=true`) for that task.
- [ ] AC-2: The oracle demonstrably gates: either it passes and the
  approval cites it, or a ran-and-failed run flips approve→feedback
  (persisted to disk per the deterministic-verdict-override rule).
- [ ] AC-3: Missing-vs-failed policy revisit recorded: consolidation §2
  says "failed oracle = hard RED; absent = WARN in v0, revisit once one
  real feature has shipped with an oracle" — this task IS that revisit
  trigger. Append the outcome (keep or change) to the consolidation doc.
- [ ] AC-4: Assumptions manifest
  (`features/qav-behavioural-gates/qav-behavioural-gates_assumptions.yaml`)
  updated where the live run confirms/contradicts ASSUM-003/005/006.

## Notes

- Candidate vehicle: the next fleet-memory-touching feature (or a small
  guardkit feature with a natural round-trip seam) — do not invent a
  synthetic feature just to tick this; wait for the next real one.
- Related: TASK-QAV-004 (oracle runner), TASK-QAV-006 (producer),
  `.claude/rules/activate-by-artefact-not-opt-in-flag.md`,
  `.claude/rules/deterministic-verdict-override-must-persist-to-disk.md`.
- Origin: Fable-window guardkit-lane leftover, 2026-07-05 session
  (fable-window-execution-plan-2026-07-04.md).
