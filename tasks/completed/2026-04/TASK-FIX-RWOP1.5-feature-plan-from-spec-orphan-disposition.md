---
id: TASK-FIX-RWOP1.5
title: /feature-plan --from-spec orphan chain — 8-helper disposition (wire or delete)
status: completed
task_type: review
review_mode: decision
review_depth: quick
decision_required: true
decision_outcome: DELETE
created: 2026-04-22T00:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
priority: low
complexity: 3
tags: [runner-without-producer, feature-plan, from-spec, dead-flag, cleanup, rwop1]
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
related_to: TASK-REV-RWOP1
related_tasks:
  - TASK-REV-RWOP1
decision_doc: .claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md
test_results:
  status: passed
  last_run: 2026-04-22T23:15:00Z
  summary: "172 failed (all pre-existing, identical to baseline), 9118 passed (baseline 9427 − 309 moved tests), 130 skipped. Live tests/integration/feature_plan/ suite: 56/56 passing."
follow_ups:
  - TASK-FIX-RWOP1.6  # Add lint-ac coverage for live (non-from-spec) feature-plan path
  - TASK-FIX-RWOP1.7  # Align wider docs footprint (docs/guides/two-phase-workflow.md, docs/reference/feature-plan.md, .guardkit/features/FEAT-FP-002.yaml)
  - Housekeeping-2026-07-21  # Delete _scratch/planning/ after 90-day grace window
---

# Task: /feature-plan --from-spec orphan chain disposition

## Problem Statement

[TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
Finding #8 identified that the `--from-spec` execution block in
[installer/core/commands/feature-plan.md](../../../installer/core/commands/feature-plan.md)
lines 247-278 describes 9 sequential steps, 8 of which call
`guardkit.planning.*` helpers that have **zero non-test callers**:

| Helper | Location | Caller |
|---|---|---|
| `parse_research_template` | `guardkit/planning/spec_parser.py` | tests only (2 files) |
| `resolve_target` | `guardkit/planning/target_mode.py` | tests only |
| `enrich_task` | `guardkit/planning/task_metadata.py` | tests only |
| `render_task_markdown` | `guardkit/planning/task_metadata.py` | tests only |
| `generate_adrs` | `guardkit/planning/adr_generator.py` | tests only |
| `generate_quality_gates` | `guardkit/planning/quality_gate_generator.py` | tests only |
| `extract_warnings` | `guardkit/planning/warnings_extractor.py` | tests only |
| `generate_seed_script` | `guardkit/planning/seed_script_generator.py` | tests only |

The CRITICAL EXECUTION INSTRUCTIONS section of `feature-plan.md`
(lines 1934-2533) never mentions `--from-spec` — Claude is never told
to run these functions. This is a pre-existing orphan chain that
predates R1/R2/R3 and is **not cohort-blocking** (the cohort does not
use `--from-spec`). But it is the densest single concentration of
the runner-without-producer pattern in the repo (8 orphans in ~32
lines of spec prose) and is worth resolving for repo hygiene.

Two plausible hypotheses:

1. **Intent**: the `--from-spec` flag is aspirational and was
   design-documented ahead of implementation; the work to wire it
   never landed.
2. **Extract**: the `guardkit.planning.*` helpers are building blocks
   for a future feature (possibly a standalone `guardkit plan spec`
   CLI); the prose in `feature-plan.md` documented them prematurely
   under the wrong command.

Either way: the status quo of "prose-only CLI flag that does nothing"
is the worst of both worlds.

## Scope

### In-Scope

Pick ONE of three paths:

1. **WIRE**: create
   `installer/core/commands/lib/feature_plan_from_spec.py` as a CLI
   entry that imports and sequences the 8 helpers in the order the
   prose specifies. Add it to
   [installer/core/commands/bin-entries.txt](../../../installer/core/commands/bin-entries.txt).
   Update `feature-plan.md` lines 247-278 to say `Execute: python3
   ~/.agentecflow/bin/feature-plan-from-spec ...` with the appropriate
   flag wiring. This is the same TASK-FIX-3C9D / TASK-FIX-B1E4 shape:
   prose points at a bin entry; bin entry is the producer.

2. **DELETE**: remove the `--from-spec` flag handling from
   `feature-plan.md` lines 247-278 entirely. Move the 8 helper
   modules to `guardkit/_scratch/planning/` (or delete them outright
   if tests don't reveal downstream usage). Keep the tests only if
   they're covering logic used elsewhere; otherwise delete.

3. **EXTRACT**: move the 8 helpers into a separate `guardkit plan
   spec` CLI subcommand under `guardkit/cli/plan.py` (new file). Add
   the subcommand to the main `guardkit` CLI entry tree. Update the
   feature-plan.md prose to reference the new `guardkit plan spec`
   subcommand rather than an inline `--from-spec` flag. This is
   useful if the helpers are genuine building blocks that just live
   under the wrong door.

### Out-of-Scope

- Changes to the helper modules' internal logic — all eight pass
  their existing integration tests.
- Merging this with any other part of the `/feature-plan` flow —
  these helpers are currently decoupled from Steps 1-10, and that's
  fine.
- Integration with the post-TASK-FIX-RWOP1.1 Step 11 flow — the
  helpers pre-date Step 11 design and have no scenario-linking
  behaviour to integrate.

## Acceptance Criteria

- [ ] Path (WIRE / DELETE / EXTRACT) chosen and rationale captured in
      `.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md`
      (~200 words is sufficient).
- [ ] Chosen path executed: either bin entry + imperative wired (WIRE),
      or prose + helpers removed (DELETE), or helpers moved + separate
      CLI subcommand (EXTRACT).
- [ ] Post-execution grep of the runner-without-producer signature
      for these 8 helpers returns either: all wired (WIRE/EXTRACT) or
      all absent from the codebase (DELETE).
- [ ] `/feature-plan` unit + integration suite remains green
      (regression: no accidental coupling broken).

## Implementation Notes

- **Suggested path**: DELETE. The `--from-spec` block is older than
  the current `/feature-plan` Step 11 tagging flow; it references a
  "research template" format that may or may not be in active use.
  Before committing to WIRE or EXTRACT, grep for any actual use of
  the `--from-spec` flag in git history or shell history — if it has
  never been used in anger, DELETE is the cleanest choice.
- If DELETE: preserve the helper logic for 90 days in
  `guardkit/_scratch/planning/` with a `README.md` noting why it was
  moved. Gives anyone who actually uses `--from-spec` a window to
  complain before outright deletion.
- Do NOT run this work until after TASK-FIX-RWOP1.1 and RWOP1.2 land.
  Cohort readiness is the priority; this is hygiene.

## Related

- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
  §Finding #8 + §Per-file findings (feature-plan.md) From-spec Steps 2-9
- Feature orchestrator guide:
  [FEAT-RWOP1-IMPLEMENTATION-GUIDE.md](../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md)
- Design-rule candidate (Graphiti): *"runner without producer
  anti-pattern"* — uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`
