---
id: TASK-COH-RUN1
title: Fire forge + study-tutor autobuild cohort runs with R1/R2/R3 activation verified
status: backlog
task_type: operation
created: 2026-04-22T00:00:00Z
updated: 2026-04-23T00:00:00Z
priority: high
complexity: 5
tags: [autobuild, cohort, forge, study-tutor, jarvis-reverify, r1, r2, r3, preflight, post-remediation]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: operation
wave: 3
conductor_workspace: r2-pipeline-closure-wave3-cohort-run
depends_on:
  - TASK-FIX-7B2E
  - TASK-FIX-3C9D
  - TASK-BDD-JBKF
  - TASK-FP-LINK
  - TASK-FP-NDG1
  - TASK-FP-NDG2
  - TASK-FIX-RWOP1.1
  - TASK-FIX-RWOP1.2
dependency_status:
  all_completed: true
  as_of: 2026-04-23
  note: All 8 dependencies landed by 2026-04-23; cohort is structurally cleared to proceed once Phase 0 prep artefacts exist.
---

> **2026-04-22 update (TASK-REV-RWOP1):** Added `TASK-FIX-RWOP1.1`
> (wire Step 11 BDD-scenario linking / `@task:` tagging) and
> `TASK-FIX-RWOP1.2` (fold Step 10.6 + 10.7 nudges into
> `generate_feature_yaml.py`) as new hard dependencies. The
> runner-without-producer sweep
> ([docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md))
> found the Step 11 auto-tagging mechanism + both fallback nudges
> are orphan. Running this cohort without those fixes would reproduce
> the R1 contamination pattern in R2 shape (features ship un-`@task:`-
> tagged → BDD oracle collects zero scenarios → silent green).
>
> **New pre-flight additions** (beyond the R1/R2/R3 checks below):
>
> - **R2 pre-flight (additive):** for each cohort member, grep the
>   generated `.feature` files for `@task:` tags. Require at least
>   one `@task:` tag per scenario in a feature that has tasks, OR
>   the R2 nudge banner ("BDD oracle activation…") fired as a console
>   warning in the captured `/feature-plan` stdout. Either signal is
>   acceptable evidence of R2 activation; silence is not.
> - **R3 pre-flight (additive):** similarly grep for the R3 smoke-
>   gates nudge banner when the cohort member's feature YAML has no
>   smoke-gate configuration. Silence indicates R3 nudge is still
>   not firing — block the run.

> **2026-04-23 update (Phase 0 prep added):** All 8 dependencies are
> completed as of this date. Before the existing pre-flight checks
> can run, the cohort members need **prepared artefacts** — captured
> `/feature-plan` stdout + generated `.feature` files +
> `.guardkit/features/FEAT-*.yaml`. Those didn't exist in forge or
> study-tutor when the task was filed, and don't exist now. A new
> **Phase 0 — Prep** section below documents the install + per-project
> `/feature-plan` runs that produce those artefacts. The existing
> pre-flight checks are re-labelled **Phase 1 — Pre-flight verification**
> and operate on Phase 0's outputs. Cohort execution becomes **Phase 2**;
> post-run analysis becomes **Phase 3**.
>
> **Jarvis** is added as an optional Phase 0 re-verification anchor
> (not part of the cohort-proper). Its original `/feature-plan` did
> NOT fire R1 per TASK-FIX-7B2E §"Retro grep of FEAT-JARVIS-001";
> re-running it post-TASK-FIX-RWOP1.1/1.2 is the cleanest direct
> evidence that the structural fix eliminated Claude-as-runtime
> variance. Worth including in the prep evidence bundle even though
> it doesn't change cohort scope.
>
> **This task is an operation, not code work** — do NOT invoke
> `/task-work` on it. Execute Phase 0 → Phase 1 → Phase 2 → Phase 3
> manually (or via a thin operator script). The `task-work` phase
> machinery (plan / arch-review / impl / test / code-review) doesn't
> fit an autobuild fire-and-observe operation.

# Task: Fire forge + study-tutor cohort runs with R1/R2/R3 activation verified

## Problem Statement

Parent review TASK-REV-4D012 sequenced the post-remediation cohort as "jarvis first, then forge + study-tutor in parallel after jarvis clears cleanly." Jarvis cleared cleanly by the no-regression criterion (TASK-REV-4D190), but the three remediations never activated. This task fires the second and third cohort members with all three remediations explicitly activated and verified before autobuild starts, so we finally get real data on whether R1/R2/R3 work when they are supposed to.

Per the user's stated sequencing (do the linker and nudge tasks first), R2 should auto-activate via `/feature-plan` (TASK-FP-LINK) by the time this runs. Pre-flight verifies this rather than falling back to manual tagging.

## Scope

### In-Scope

**Phase 0 — Prep** (produce the artefacts the pre-flight checks operate on):

0.1. **Propagate GuardKit to consumer repos.** From the `guardkit`
     repo root, run:
     ```bash
     ./installer/scripts/install.sh
     ```
     Confirm `~/.agentecflow/bin/generate-feature-yaml` resolves to
     the current `installer/core/commands/lib/generate_feature_yaml.py`
     (post TASK-FIX-B1E4 manifest entry):
     ```bash
     ls -la ~/.agentecflow/bin/generate-feature-yaml
     ```
     This propagates every RWOP1 fix to the consumer projects —
     Step 11 BDD linking (TASK-FIX-RWOP1.1), Step 10.6 + 10.7 nudges
     folded into the producer (TASK-FIX-RWOP1.2), AC linter wiring
     (TASK-FIX-3C9D), plus the `validate_agent_invocations` and
     `execute_phase_5_5_plan_audit` producers (TASK-FIX-RWOP1.3.1 /
     1.3.2).

0.2. **Per-project `/feature-plan` runs.** In each cohort-member
     repo, run `/feature-plan <description>` with the project's
     prepared feature description. Capture the planner stdout
     verbatim (every line — no selective filtering). This stdout
     is the primary evidence source for the Phase 1 pre-flight
     checks below.

0.3. **Artefact capture.** For each project, save evidence under
     this repo at
     `docs/reviews/TASK-COH-RUN1-prep/{project}/`:

     - `feature-plan-stdout.log` — the full captured planner output.
     - `verification.md` — a short results table with the four grep
       outcomes (see Phase 1 for the precise commands). Include
       project path, feature-plan invocation command, timestamps,
       and Claude session identifier if available (to preserve the
       "which Claude runtime variant ran this" evidence for any
       future retrospective).
     - Symlinks or path references to the generated
       `features/*.feature` and `.guardkit/features/FEAT-*.yaml`
       files in the consumer repo (avoid duplicating — the
       guardkit repo is the evidence ledger, not the artefact
       cache).

0.4. **Optional: jarvis re-verification anchor.** Jarvis's original
     `/feature-plan` did NOT fire R1 per TASK-FIX-7B2E §"Retro grep
     of FEAT-JARVIS-001". Re-running `/feature-plan` on jarvis
     post-TASK-FIX-RWOP1.1/1.2 yields the cleanest possible direct
     evidence that the structural fixes eliminated the
     Claude-as-runtime variance. Include jarvis as a third prep
     target. In `docs/reviews/TASK-COH-RUN1-prep/jarvis/verification.md`
     record a **before / after** comparison row:
     `original_jarvis_FEAT-001 (pre-RWOP1): 0 R1 signals` vs
     `re-run_jarvis (post-RWOP1): <observed signals>`. This is
     separately valuable for TASK-REV-STKB Workstream A
     (retrospective on why stack-blindness slipped through — shows
     the deterministic wiring mechanism works when it's actually
     applied).

0.5. **Gate.** If any project's `/feature-plan` run crashes, stalls,
     or produces no `.feature` file, STOP. Do not proceed to Phase 1.
     File a defect task against whichever remediation failed and
     halt the cohort. The goal of Phase 0 is to catch regressions
     before autobuild burns hours of compute; silent failure here
     is the loudest warning you will get.

**Phase 1 — Pre-flight verification** (must all pass before
Phase 2 starts; any failure blocks the run and files a targeted
follow-on):

1. **R1 check:** Pre-flight must (a) confirm **TASK-FIX-3C9D** has landed (structural fix — imperative invocation in `/feature-plan`'s execution trace, not just descriptive prose), and (b) grep the forge and study-tutor `/feature-plan` stdout (captured in Phase 0.3) for `AC-quality review:` before autobuild starts. If the header is absent, R1 did not activate on this specific `/feature-plan` invocation — block the run until it does. Rationale: TASK-FIX-7B2E's dynamic test fired the linter in one Claude session, but the retro-grep of FEAT-JARVIS-001's planner history showed zero matches, so R1 activation via prose-only spec is non-deterministic across sessions. A prior success does not transfer to future invocations; each cohort `/feature-plan` must be grep-verified in situ. TASK-FIX-3C9D replaces the prose with an imperative callsite that removes the interpretation variance — without it, this pre-flight is the only way to avoid flying blind.
2. **R2 check:** after `/feature-plan` completes for each feature, `grep -l '@task:' features/*.feature` must return the feature file for both forge and study-tutor. If tags are absent AND the R2 nudge banner ("BDD oracle activation…") did NOT appear in the captured stdout, that's a compound failure — Step 11 wiring didn't fire AND the fallback nudge didn't warn. Block the run and file a regression against TASK-FIX-RWOP1.1 / RWOP1.2.
3. **R3 check:** both feature YAML files must contain a non-empty `smoke_gates:` block. If absent, the R3 nudge banner should have appeared in the captured `/feature-plan` stdout asking the author to add one. Author adds the block before Phase 2 starts. If the nudge did NOT appear AND `smoke_gates:` is missing, that's an RWOP1.2 regression — file it.

**Phase 2 — Cohort execution:**

4. Run `guardkit autobuild feature FEAT-FORGE-XXX` and `guardkit autobuild feature FEAT-STUDY-TUTOR-XXX` in parallel (separate Conductor workspaces, separate worktrees). Do NOT include jarvis in this phase — jarvis is a Phase 0 evidence anchor, not a cohort member.
5. Do **not** intervene mid-run. If one fails, let it fail — the data is the point.

**Phase 3 — Post-run analysis:**

6. For each cohort member, capture under
   `docs/reviews/TASK-COH-RUN1-run/{project}/`:
   - Task completion counts, first-pass approval rate, wall time.
   - How many tasks had `bdd_results` in their `task_work_results.json`. What the three-state breakdown was.
   - How many smoke gates fired, and did any block/stop the run.
   - Any AC-linter warnings that surfaced during `/feature-plan` (from the Phase 0 stdout + any surfaced during autobuild's in-flight `/feature-plan` re-invocations).
   - Presence of `validate_agent_invocations` outputs + `plan_audit` block in each task's `task_work_results.json` (new since RWOP1.3.1/1.3.2).
   - Post-autobuild patch count within 24–72h (same measurement window as TASK-REV-4D012's specialist-agent baseline).
7. Produce a combined review report comparing forge + study-tutor + jarvis against TASK-REV-4D012's baseline matrix. This is the first run that actually tests whether R1/R2/R3 catch the PEX-014..020 class of bug when exercised. Cite Phase 0 prep artefacts as the activation-evidence source; cite Phase 3 run artefacts as the effectiveness-evidence source. Keep activation vs effectiveness reported separately per the TASK-REV-4D190 methodology ("separately assess regression and activation").

### Out-of-Scope

- Changes to forge or study-tutor *content* (feature description, requirements — those belong to their respective projects).
- Fixes to R1/R2/R3 implementations discovered during the run (file as separate follow-on tasks, don't patch in-flight).
- A parallel run of TASK-REV-4D190 for jarvis (jarvis is done; the revised decision is in the report).

## Acceptance Criteria

### Phase 0 — Prep

- [ ] `./installer/scripts/install.sh` ran cleanly; `~/.agentecflow/bin/generate-feature-yaml` confirmed to resolve to the current source.
- [ ] `/feature-plan` ran in each of forge + study-tutor without crashing; planner stdout captured verbatim to `docs/reviews/TASK-COH-RUN1-prep/{project}/feature-plan-stdout.log`.
- [ ] `verification.md` filed per project with the four grep results (R1 header, R2 `@task:` tags, R2 nudge banner, R3 nudge banner).
- [ ] Jarvis re-verification row included (optional but recommended): before/after comparison showing whether R1 signal now appears post-RWOP1.1/1.2 where it didn't originally.

### Phase 1 — Pre-flight verification

- [ ] R1 pre-flight passed: (a) TASK-FIX-3C9D landed, and (b) `AC-quality review:` header observed in `/feature-plan` stdout for **both** forge and study-tutor invocations. Waivers are not accepted — post-TASK-FIX-7B2E we know activation is session-dependent, so in-situ grep is required.
- [ ] R2 pre-flight passed: both feature files have `@task:<TASK-ID>` tags (preferably via TASK-FIX-RWOP1.1's wired Step 11; fallback = R2 nudge banner observed + manual tagging + exception recorded).
- [ ] R3 pre-flight passed: both feature YAMLs have non-empty `smoke_gates:` blocks (preferably authored after the RWOP1.2 nudge banner fired; manual authoring without nudge signal is permitted but recorded as an RWOP1.2 degradation flag).

### Phase 2 — Cohort execution

- [ ] Both autobuild runs completed or failed. Do not mark this task blocked on a failed autobuild — a failed run *is* valid data.

### Phase 3 — Post-run analysis

- [ ] Per-remediation activation evidence documented: does `bdd_results` appear in `task_work_results.json` files? Did smoke gates fire between waves? Did the AC linter surface anything during autobuild's in-flight `/feature-plan` runs? Did the new `validate_agent_invocations` + `plan_audit` producers populate those fields?
- [ ] Post-autobuild patch count recorded at T+24h and T+72h.
- [ ] Combined report written to `docs/reviews/TASK-COH-RUN1-forge-study-tutor-cohort-review.md` with:
  - Baseline matrix row for each of forge and study-tutor.
  - Phase 0 activation evidence (per-signal, per-project) clearly separated from Phase 3 effectiveness evidence. Per TASK-REV-4D190 methodology, do NOT collapse "remediations activated" and "remediations caught bugs" into one column.
  - Comparison to jarvis (TASK-REV-4D190 original + jarvis Phase 0 re-verification) and specialist-agent PEX-014..020 (TASK-REV-4D012).
  - Explicit answer to the carry-over question: *did R3 catch a composition failure that per-task Coach missed?* (yes / no / not applicable because no composition failure occurred on these cohort members).
- [ ] Any defects in R1/R2/R3 surfaced during the run filed as separate tasks linked to this one.

## Implementation Notes

### Phase 0 commands (for the run log)

```bash
# 0.1 — propagate guardkit to consumers
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
./installer/scripts/install.sh
ls -la ~/.agentecflow/bin/generate-feature-yaml

# 0.3 — artefact capture per project (repeat for forge, study-tutor, jarvis)
mkdir -p docs/reviews/TASK-COH-RUN1-prep/{forge,study-tutor,jarvis}

# After running /feature-plan in each consumer repo (step 0.2),
# save the captured stdout:
cp <captured-output> docs/reviews/TASK-COH-RUN1-prep/forge/feature-plan-stdout.log
# ...etc per project
```

### Phase 1 grep commands (document each result in verification.md)

```bash
PREP=docs/reviews/TASK-COH-RUN1-prep

# R1: AC linter activation header
grep -n 'AC-quality review:' $PREP/forge/feature-plan-stdout.log
grep -n 'AC-quality review:' $PREP/study-tutor/feature-plan-stdout.log

# R2 structural (Step 11 wiring worked → scenarios tagged)
grep -l '@task:' /path/to/forge/features/*.feature
grep -l '@task:' /path/to/study-tutor/features/*.feature

# R2 fallback (nudge banner fired — only expected if @task: tags absent)
grep -n 'BDD oracle activation' $PREP/forge/feature-plan-stdout.log
grep -n 'BDD oracle activation' $PREP/study-tutor/feature-plan-stdout.log

# R3 structural (feature YAML has smoke_gates configured)
grep -E '^smoke_gates:' /path/to/forge/.guardkit/features/FEAT-*.yaml
grep -E '^smoke_gates:' /path/to/study-tutor/.guardkit/features/FEAT-*.yaml

# R3 fallback (nudge banner — expected if smoke_gates: absent)
grep -n 'smoke gates activation' $PREP/forge/feature-plan-stdout.log
grep -n 'smoke gates activation' $PREP/study-tutor/feature-plan-stdout.log
```

### Phase 0 jarvis re-verification details

Jarvis is the highest-signal Phase 0 target because:

- Original `/feature-plan` on FEAT-JARVIS-001 produced **zero** `AC-quality review:` matches (TASK-FIX-7B2E §"Retro grep"). Post-RWOP1.1/1.2 it should produce ≥ 1 match deterministically.
- If the re-run *still* produces zero matches, that is a P0 defect against TASK-FIX-RWOP1.1/1.2 landing — not a jarvis-specific issue. Halt and investigate before proceeding to Phase 1 for forge/study-tutor.
- Capture the before/after in `docs/reviews/TASK-COH-RUN1-prep/jarvis/verification.md` as explicit evidence for TASK-REV-STKB's Workstream A retrospective.

### General notes

- **Do not run the two cohort members sequentially in Phase 2 unless there is a shared-resource constraint (FalkorDB throughput, LLM rate limits). Parallel execution is the stated design; running sequentially loses timing data.**
- Use the same Graphiti group IDs as the jarvis run so the post-run Graphiti query can span all three cohort-scope members in one search.
- If R3 smoke gates fire and block a wave, that is a **success** for this task even though the autobuild "failed." Frame the report accordingly.
- If R2 flags a task for a failing scenario (not a pending one), the Coach should reject and the task enters normal Player-Coach retry. Document these as R2 wins, not R2 noise.
- **Expected negative finding if it occurs:** if R2 flags pending scenarios as failures (three-state model broken), this is a P0 defect against TASK-BDD-E8954. Halt the cohort, file the bug, fix, re-run.
- **Do NOT invoke `/task-work` on this task** — the phase machinery (plan / arch-review / impl / test / code-review) doesn't fit a fire-and-observe autobuild operation. Execute the phases manually or via a thin operator script. `task_type: operation` + `implementation_mode: operation` in the frontmatter both signal this.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§Go/no-go criteria, §Follow-on tasks)
- Predecessor: `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md` (§7 "Cohort order", §3 baseline matrix)
- Precursor feature completion: all of TASK-FIX-7B2E, TASK-BDD-JBKF, TASK-FP-LINK, TASK-FP-NDG1, TASK-FP-NDG2 must be done (this task's `depends_on`).
- Sibling cohort data: FEAT-JARVIS-001 autobuild state at `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/`
