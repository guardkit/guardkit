---
id: TASK-FIX-3C9D
title: Wire the AC linter into /feature-plan execution (not just its spec prose)
status: backlog
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: high
complexity: 3
tags: [autobuild, r1, remediation, ac-linter, feature-plan, runner-without-producer, non-deterministic-activation]
parent_review: TASK-REV-4D190
parent_task: TASK-AC-53445
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 1
conductor_workspace: r2-pipeline-closure-wave1-r1-wire
depends_on: [TASK-FIX-7B2E]
priority_history:
  - value: high
    set_at: 2026-04-22T00:00:00Z
    reason: "Filed as blocking remediation when TASK-FIX-7B2E static verdict was 'not wired'"
  - value: medium
    set_at: 2026-04-22T00:00:00Z
    reason: "Dropped after TASK-FIX-7B2E dynamic verification showed R1 activates via Claude-as-runtime interpretation (6/6 fixture ACs fired). Still worth doing to make activation deterministic and harden against a stricter future runtime, but no longer blocks COH-RUN1."
  - value: high
    set_at: 2026-04-22T00:00:00Z
    reason: "Retro-grep of FEAT-JARVIS-001 planner history showed 0 matches for the linter header; R1 is non-deterministic in practice (fires in some Claude sessions, not others), so the structural fix is again on the critical path for COH-RUN1 to have reliable R1 coverage. The priority drop was based on incomplete evidence (one positive dynamic test); the retro-grep supersedes it."
---

# Task: Wire the AC linter into /feature-plan execution

## Problem Statement

TASK-FIX-7B2E dynamic verification (2026-04-22) confirmed that the R1
assertable-AC linter shipped by TASK-AC-53445 **does fire under
Claude-as-runtime interpretation** — today's `/feature-plan` run emitted
the `AC-quality review: 25 unverifiable acceptance criteria detected`
header with 6/6 fixture ACs flagged. However, the static evidence below
remains correct: the spec has no imperative callsite, no execution-trace
reference, and no producer script invoking the linter. The R1 activation
is therefore **behaviourally functional but structurally fragile**.

A retro grep of `jarvis/docs/history/feature-plan-FEAT-JARVIS-001-history.md`
(captured ~10 hours after TASK-AC-53445 landed) returned **zero matches**
for the `AC-quality review:` header. So activation is non-deterministic
across Claude-as-runtime invocations of the same spec.

This task is therefore downgraded from "unblock COH-RUN1" (medium
priority to the cohort) to "make R1 activation deterministic and
runtime-agnostic" (a pure hardening / correctness improvement). No
longer blocks COH-RUN1; still worth doing.

Verification report: `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`

Evidence summary (static — unchanged from original filing; retained because
these are the gaps TASK-FIX-3C9D still needs to close):

1. Step 10.5 of `installer/core/commands/feature-plan.md` (lines 2241-2315)
   documents the linter post-step in prose, including the self-describing
   invariant *"Runs unconditionally. There is no opt-in flag; the linter
   always executes."* (line 2243). The dynamic run confirmed Claude-
   as-runtime reads this prose as instruction; it does not guarantee a
   non-Claude executor or a stricter Claude session would.
2. Step 10.5 contains **no imperative instruction** — only descriptive
   prose ("the post-step collects…", "Calls `lint_plan_warnings(tasks)`").
3. Step 10.5 is **absent from both execution traces** in the same file
   (lines 2370-2395 and 2397-2461). Traces run 1→…→8→8.5→9.
4. Step 10.5 self-references a "Step 10" and "Step 11" that do not exist
   — the whole 10/10.5/11 block was appended without integration.
5. No runtime Python caller of `lint_plan_warnings` exists anywhere
   outside the module itself and its tests.

## Root-cause pattern — "runner without producer"

This is the same architectural failure mode TASK-REV-4D190 Addendum A
identified for R2, in a narrower shape: a verifier whose runtime is
described in a command spec but not plumbed into that spec's executable
path. R1 (this task) and R2 back-to-back exhibit the pattern. See Graphiti
episode *"Design rule candidate: runner without producer anti-pattern"*.

Addressing this task closes R1 specifically; a parallel lineage-level fix
(e.g. a pre-commit check that every documented verifier has an imperative
callsite) is out of scope here and deliberately deferred to a follow-up.

## Scope

### In-Scope

Pick one of two wiring options — both are single-file-ish changes.

**Option A (lighter touch): imperative instruction in the spec.**
1. Edit `installer/core/commands/feature-plan.md` Step 10.5 to add an
   imperative `Execute:` block alongside the existing prose:

   ```
   Execute:
     python3 -c 'import json, sys; from guardkit.orchestrator.quality_gates.ac_linter import lint_plan_warnings, format_warning_summary; tasks = json.load(open(sys.argv[1])); w = lint_plan_warnings(tasks); print(format_warning_summary(w))' <tasks-json-path>
   ```

   (or a dedicated `guardkit ac-lint <feature-yaml>` CLI entry point if
   preferred — see Option B variant.)

2. Insert a new bullet in both execution traces (lines 2370-2395 and
   2397-2461) between step 8.5 (validate) and step 9 (completion summary):

   ```
   8.7. Run AC-quality review (warn-mode v1):
      - Execute: guardkit ac-lint <feature-yaml>
      - Print the warning summary to planner output
      - Non-blocking
   ```

3. Add the linter step to the "REMEMBER: Your job is to…" duty list
   (lines 2332-2340).

**Option B (structural, preferred): move the linter call into `generate-feature-yaml`.**
1. Extend `~/.agentecflow/bin/generate-feature-yaml` (or whichever
   installer artifact generates it) to invoke `lint_plan_warnings` over
   the task list it just emitted and print `format_warning_summary()`
   output to stdout before exiting.
2. Remove the descriptive-only Step 10.5 prose from `feature-plan.md` or
   slim it to a one-liner pointing at the script's behaviour.
3. The spec's existing imperative *"Execute: python3 ~/.agentecflow/bin/generate-feature-yaml …"*
   now transitively runs the linter.

Option B is preferred because it collapses "runner without producer" at
its root — the runtime path and the docs path become the same line.
Option A preserves the current module split but adds a second imperative.

### Out-of-Scope

- Changing classifier patterns (`_MANUAL_PATTERNS`, `_FILE_CONTENT_PATTERNS`).
  The TASK-AC-53445 non-goal on pre-tuning still holds for v1 warn-mode.
- Graduating to block-mode v2.
- Adding a frontmatter opt-in flag (explicit non-goal in TASK-AC-53445).
- Generalised lineage-level guard (pre-commit / lint rule for "every
  documented verifier has an imperative callsite"). Separate follow-up.

## Acceptance Criteria

- [ ] After this task lands, a fresh `/feature-plan` run against
      `tests/fixtures/r1-verification/prose-ac-spec.md` emits the
      `AC-quality review: N unverifiable acceptance criteria detected`
      header with N ≥ 3 **deterministically** — i.e., the header is
      produced by an imperative callsite (Option A `Execute:` line, or
      Option B `generate-feature-yaml` invocation), not by Claude-as-
      runtime interpretation of descriptive prose. Verify by re-running
      at least twice (different sessions) and confirming the header
      appears both times.
- [ ] The `/feature-plan` command spec's execution trace(s) explicitly
      reference the AC-linter step (imperative `Execute:` or transitively
      via the `generate-feature-yaml` invocation).
- [ ] The existing linter tests (`tests/unit/test_criteria_classifier.py`
      + `tests/integration/feature_plan/test_ac_linter_warning_flow.py`)
      still pass. Test count unchanged unless Option B adds an
      end-to-end test.
- [ ] Option-B only: an end-to-end test that drives
      `generate-feature-yaml` against a prose-AC input and asserts the
      warning summary in stdout.
- [ ] `UNVERIFIABLE_CONFIDENCE_THRESHOLD` value is not modified (still
      0.6 — pre-tuning remains out of scope).
- [ ] TASK-FIX-7B2E's verification report
      (`.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`) gains a
      §"Post-remediation re-verification" section capturing the dynamic
      output. The pre-remediation §"Dynamic verification result" section
      (2026-04-22 run, 6/6 ACs fired via Claude-as-runtime) is retained
      as the baseline; the new section records whether remediation
      moved activation from non-deterministic to deterministic.

## Implementation Notes

- The author of TASK-AC-53445 clearly intended the linter to run
  unconditionally (spec line 2243). This task is closing the gap between
  that intent and the implementation — not disagreeing with the intent.
- If Option B is chosen, consider whether the same script should also
  honour block-mode v2 in future by returning a non-zero exit code when
  a `--block` flag is passed. Not required for this task; just keep the
  call site clean so v2 is a one-line flip.
- Cohort impact: this task must land before jarvis/forge/study-tutor
  cohort runs, otherwise those runs will again produce the "silence"
  signal that motivated TASK-FIX-7B2E in the first place.
- A re-review of TASK-AC-53445 under the "runner without producer" lens
  is a worthwhile follow-up to check for other Step-10.5-like orphans —
  out of scope here, file separately if something is found.

## Related

- Verification report: `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`
- Parent verification task: `TASK-FIX-7B2E`
- Original R1 delivery: `tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` §R1
- Predecessor review: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` §6 R1
- Command spec under repair: `installer/core/commands/feature-plan.md` §Step 10.5
- Graphiti episode: *"Design rule candidate: runner without producer anti-pattern"*
