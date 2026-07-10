---
id: TASK-LBL-005
title: "Wire EXECUTE hooks into the three disposition markdown commands"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: documentation
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 4
implementation_mode: direct
complexity: 2
dependencies: [TASK-LBL-004]
tags: [observability, labels, obs-6, commands]
---

# Task: Wire EXECUTE hooks into the three disposition markdown commands

## Description

Add the automatic half of the hybrid writer surface (ASSUM-007): imperative
`**EXECUTE** (Bash)` blocks calling `guardkit label record` at the three
disposition landing points. Follow the proven TASK-FIX-3C9D shape — the
existing precedent is `installer/core/commands/task-review.md:647-664`
(EXECUTE + binary fallback + parse contract). A prose instruction alone is NOT
acceptable (`.claude/rules/structural-defence-beats-prompt-instruction.md`).

## Landing points and hook content

1. **`installer/core/commands/task-review.md`** — Phase 5 `[A]ccept` branch
   (~line 1124): after review acceptance,
   `guardkit label record --task-id {reviewed_task_id} --source task-review --source-ref {review_task_id} --non-blocking`
   (when the review's verdict overturns a coach approval, the operator may
   override with `--verdict-class operator_caught` — document this in the hook).
2. **`installer/core/commands/task-complete.md`** — finalize step: only for
   tasks whose id/`task_type` indicates a fix (`TASK-FIX-*`),
   `guardkit label record --task-id {fixed_task_id} --source task-fix --source-ref {task_id} --non-blocking`.
   Note: fleet decision DF-018 will later demote task-complete to a shared
   routine — hook here now; the call migrates into that routine when it ships.
3. **`installer/core/commands/feature-complete.md`** — merge-review disposition:
   for each task the merge review flags,
   `guardkit label record --task-id {task_id} --feature-id {feature_id} --source merge-review --source-ref merge-review:{feature_id} --non-blocking`.

Each hook MUST include, mirroring the Phase 0 precedent:
- **BINARY FALLBACK**: retry with `guardkit-py label record ...` if the wrapper
  does not dispatch the subcommand.
- **NON-BLOCKING language**: "label failure is a WARNING; the disposition
  completes regardless" (the sidecar is an observer, never a gate).
- The frozen disposition-source → verdict-class mapping table (copy from
  TASK-LBL-004) so the command doc and the CLI cannot drift apart in meaning.

## Acceptance Criteria

- [ ] All three markdown commands contain an imperative EXECUTE block invoking `guardkit label record` with the correct --source for their disposition, plus binary fallback and non-blocking language
- [ ] The mapping table appears (or is referenced) at each hook site consistently with the CLI's frozen table
- [ ] No hook can block its parent disposition: every invocation passes --non-blocking
- [ ] The manual-path documentation (operator/live-gate labels via `guardkit label record --source operator|live-gate`) is added to the relevant command help or a short section in `docs/guides/` referenced from the hooks

## Test Requirements

- [ ] Grep-able assertions (documentation task — no runtime tests): `rg -c "guardkit label record" installer/core/commands/{task-review,task-complete,feature-complete}.md` returns ≥1 per file

## Implementation Notes

- This task edits markdown command specs only; the CLI contract is frozen by
  TASK-LBL-004 — do not invent new flags here.
