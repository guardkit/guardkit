---
id: TASK-COH-RUN1
title: Fire forge + study-tutor autobuild cohort runs with R1/R2/R3 activation verified
status: backlog
task_type: operation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: high
complexity: 5
tags: [autobuild, cohort, forge, study-tutor, r1, r2, r3, preflight, post-remediation]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 3
conductor_workspace: r2-pipeline-closure-wave3-cohort-run
depends_on:
  - TASK-FIX-7B2E
  - TASK-FIX-3C9D
  - TASK-BDD-JBKF
  - TASK-FP-LINK
  - TASK-FP-NDG1
  - TASK-FP-NDG2
---

# Task: Fire forge + study-tutor cohort runs with R1/R2/R3 activation verified

## Problem Statement

Parent review TASK-REV-4D012 sequenced the post-remediation cohort as "jarvis first, then forge + study-tutor in parallel after jarvis clears cleanly." Jarvis cleared cleanly by the no-regression criterion (TASK-REV-4D190), but the three remediations never activated. This task fires the second and third cohort members with all three remediations explicitly activated and verified before autobuild starts, so we finally get real data on whether R1/R2/R3 work when they are supposed to.

Per the user's stated sequencing (do the linker and nudge tasks first), R2 should auto-activate via `/feature-plan` (TASK-FP-LINK) by the time this runs. Pre-flight verifies this rather than falling back to manual tagging.

## Scope

### In-Scope

**Pre-flight verification** (must all pass before autobuild starts; any failure blocks the run and files a targeted follow-on):

1. **R1 check:** Pre-flight must (a) confirm **TASK-FIX-3C9D** has landed (structural fix — imperative invocation in `/feature-plan`'s execution trace, not just descriptive prose), and (b) grep the forge and study-tutor `/feature-plan` stdout for `AC-quality review:` before autobuild starts. If the header is absent, R1 did not activate on this specific `/feature-plan` invocation — block the run until it does. Rationale: TASK-FIX-7B2E's dynamic test fired the linter in one Claude session, but the retro-grep of FEAT-JARVIS-001's planner history showed zero matches, so R1 activation via prose-only spec is non-deterministic across sessions. A prior success does not transfer to future invocations; each cohort `/feature-plan` must be grep-verified in situ. TASK-FIX-3C9D replaces the prose with an imperative callsite that removes the interpretation variance — without it, this pre-flight is the only way to avoid flying blind.
2. **R2 check:** after `/feature-plan` completes for each feature, `grep -l '@task:' features/*.feature` must return the feature file for both forge and study-tutor. If TASK-FP-LINK has not shipped, fall back to manual tagging + record the exception.
3. **R3 check:** both feature YAML files must contain a non-empty `smoke_gates:` block. If absent, author adds one before autobuild starts. (TASK-FP-NDG2's nudge should fire automatically if missing.)

**Cohort execution:**

4. Run `guardkit autobuild feature FEAT-FORGE-XXX` and `guardkit autobuild feature FEAT-STUDY-TUTOR-XXX` in parallel (separate Conductor workspaces, separate worktrees).
5. Do **not** intervene mid-run. If one fails, let it fail — the data is the point.

**Post-run analysis:**

6. For each cohort member, capture:
   - Task completion counts, first-pass approval rate, wall time.
   - How many tasks had `bdd_results` in their `task_work_results.json`. What the three-state breakdown was.
   - How many smoke gates fired, and did any block/stop the run.
   - Any AC-linter warnings that surfaced during `/feature-plan`.
   - Post-autobuild patch count within 24–72h (same measurement window as TASK-REV-4D012's specialist-agent baseline).
7. Produce a combined review report comparing forge + study-tutor + jarvis against TASK-REV-4D012's baseline matrix. This is the first run that actually tests whether R1/R2/R3 catch the PEX-014..020 class of bug when exercised.

### Out-of-Scope

- Changes to forge or study-tutor *content* (feature description, requirements — those belong to their respective projects).
- Fixes to R1/R2/R3 implementations discovered during the run (file as separate follow-on tasks, don't patch in-flight).
- A parallel run of TASK-REV-4D190 for jarvis (jarvis is done; the revised decision is in the report).

## Acceptance Criteria

- [ ] R1 pre-flight passed: (a) TASK-FIX-3C9D landed, and (b) `AC-quality review:` header observed in `/feature-plan` stdout for **both** forge and study-tutor invocations. Waivers are not accepted — post-TASK-FIX-7B2E we know activation is session-dependent, so in-situ grep is required.
- [ ] R2 pre-flight passed: both feature files have `@task:<TASK-ID>` tags (preferably via TASK-FP-LINK; fallback = manual tagging + exception recorded).
- [ ] R3 pre-flight passed: both feature YAMLs have non-empty `smoke_gates:` blocks.
- [ ] Both autobuild runs completed or failed. Do not mark this task blocked on a failed autobuild — a failed run *is* valid data.
- [ ] Per-remediation activation evidence documented: does `bdd_results` appear in `task_work_results.json` files? Did smoke gates fire between waves? Did the AC linter surface anything?
- [ ] Post-autobuild patch count recorded at T+24h and T+72h.
- [ ] Combined report written to `docs/reviews/TASK-COH-RUN1-forge-study-tutor-cohort-review.md` with:
  - Baseline matrix row for each of forge and study-tutor.
  - Per-remediation activation evidence.
  - Comparison to jarvis (TASK-REV-4D190) and specialist-agent PEX-014..020 (TASK-REV-4D012).
  - Explicit answer to the carry-over question: *did R3 catch a composition failure that per-task Coach missed?* (yes / no / not applicable because no composition failure occurred on these cohort members).
- [ ] Any defects in R1/R2/R3 surfaced during the run filed as separate tasks linked to this one.

## Implementation Notes

- **Pre-flight grep commands (document these in the run log):**
  ```bash
  # R2 check
  grep -l '@task:' /path/to/forge/features/*.feature
  grep -l '@task:' /path/to/study-tutor/features/*.feature
  # R3 check
  grep -E '^smoke_gates:' /path/to/forge/.guardkit/features/FEAT-*.yaml
  grep -E '^smoke_gates:' /path/to/study-tutor/.guardkit/features/FEAT-*.yaml
  ```
- **Do not run the two cohort members sequentially unless there is a shared-resource constraint (FalkorDB throughput, LLM rate limits). Parallel execution is the stated design; running sequentially loses timing data.**
- Use the same Graphiti group IDs as the jarvis run so the post-run Graphiti query can span all three cohort members in one search.
- If R3 smoke gates fire and block a wave, that is a **success** for this task even though the autobuild "failed." Frame the report accordingly.
- If R2 flags a task for a failing scenario (not a pending one), the Coach should reject and the task enters normal Player-Coach retry. Document these as R2 wins, not R2 noise.
- **Expected negative finding if it occurs:** if R2 flags pending scenarios as failures (three-state model broken), this is a P0 defect against TASK-BDD-E8954. Halt the cohort, file the bug, fix, re-run.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§Go/no-go criteria, §Follow-on tasks)
- Predecessor: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` (§7 "Cohort order", §3 baseline matrix)
- Precursor feature completion: all of TASK-FIX-7B2E, TASK-BDD-JBKF, TASK-FP-LINK, TASK-FP-NDG1, TASK-FP-NDG2 must be done (this task's `depends_on`).
- Sibling cohort data: FEAT-JARVIS-001 autobuild state at `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/`
