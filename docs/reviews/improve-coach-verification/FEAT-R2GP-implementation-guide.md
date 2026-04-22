Implementation plan — remaining FEAT-R2GP work
Execution order at a glance

Phase 1 (Wave 1 stragglers, parallelizable)
  ├── Track 1: NDG1 + NDG2 together  (twin nudges, ~2h)
  └── Track 2: FIX-3C9D               (R1 structural fix, ~3h)

Phase 2 (Wave 2, serial)
  └── FP-LINK                         (R2 architectural fix, ~1–2 days)

Phase 3 (Wave 3, serial, final)
  └── COH-RUN1                        (cohort run + report, ~half day attended)

Anytime (do before COH-RUN1 for maximum value)
  ├── REV-AC53                        (~1–2h)
  └── REV-RWOP1                       (~2–3h)
Total: ~3 days of focused work + one half-day of cohort-run attention.

Phase 1, Track 1 — TASK-FP-NDG1 + TASK-FP-NDG2 (ship as one)
Mission: When /feature-plan finishes creating tasks, print a nudge if activation artefacts are missing. Twin tasks; implement together in a single change.

Files:

installer/core/commands/feature-plan.md — add the two nudge checks near the end of /feature-plan (post-task-creation, before completion summary)
Test file (new): tests/unit/commands/feature_plan/test_activation_nudges.py covering both nudges
Decisions to make:

NDG1 trigger: features/*.feature exists AND zero @task: tags. (Does NOT trigger if partially tagged — partial activation is fine.)
NDG2 trigger: feature YAML lacks smoke_gates: AND has ≥2 waves. Single-wave features skip (nothing to gate between).
Suppression: both nudges honour --no-questions / --quiet — don't spam CI.
Traps:

Don't use a frontmatter opt-in flag to disable — that re-creates the silent-miss pattern.
Don't auto-generate smoke gate commands for the user. Print the example; let them pick.
The NDG1 nudge will become redundant once FP-LINK ships — leave a TODO noting it should fire only when FP-LINK's auto-tagging was unable to tag any scenarios.
Validation: unit tests cover 3 branches for NDG1 (missing file / tagged file / untagged file) and 4 for NDG2 (waves × smoke-key presence). Manual smoke: run /feature-plan against a fixture with no feature file — no nudge; against prose-ac-spec (no @task:) — NDG1 fires; against a multi-wave fixture without smoke_gates — NDG2 fires.

Effort: 1.5–2 hours. Low risk — pure output text, no file mutation.

Phase 1, Track 2 — TASK-FIX-3C9D (wire AC linter structurally)
Mission: Remove R1 activation non-determinism. Replace descriptive spec prose with an imperative callsite so /feature-plan deterministically invokes the linter in every session.

Files:

~/.agentecflow/bin/generate-feature-yaml (or the installer source that generates it) — add linter invocation at end
installer/core/commands/feature-plan.md — slim Step 10.5 from prose-heavy section to a one-liner pointing at the script; add "Execute:" mention in execution trace
Test: tests/integration/feature_plan/test_ac_linter_wiring.py — end-to-end with prose-AC input
Design decision (already made): Option B over Option A. Move the call into generate-feature-yaml so runtime path and doc path are the same line. Reason: closes "runner without producer" at its root.

Gotcha — data availability: generate-feature-yaml is invoked with --task "id:title:complexity:deps" args which do not carry acceptance_criteria. The linter needs id + acceptance_criteria. Two workable approaches:

(preferred) Extend the --discover code path that already reads task .md files — extract acceptance_criteria from the markdown body during file discovery, pass to lint_plan_warnings at end.
(alternative) Add a new --task-acs multi-arg. More invasive; skip unless option 1 hits a snag.
Traps:

Don't modify UNVERIFIABLE_CONFIDENCE_THRESHOLD (0.6). Pre-tuning is an explicit non-goal per TASK-AC-53445.
Don't add a frontmatter opt-in flag. Same reason — silent opt-in failure mode.
Don't graduate to block-mode v2 in this task. Warn-mode only.
Validation ACs (the critical ones):

End-to-end: running /feature-plan against tests/fixtures/r1-verification/prose-ac-spec.md emits AC-quality review: N unverifiable acceptance criteria detected with N ≥ 3 — deterministically, across multiple fresh sessions. Run twice in separate clean contexts to confirm determinism.
Retro-grep on a post-fix jarvis-like planner history shows the header present (no longer session-dependent).
Existing linter tests still pass.
.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md gains a §"Post-remediation re-verification" section.
Effort: 2.5–3.5 hours.

Phase 2 — TASK-FP-LINK (R2 linker, the big one)
Mission: Close the R2 pipeline gap permanently. Add a post-task-creation phase to /feature-plan that reads the generated .feature file, maps scenarios to tasks (LLM-assisted), and rewrites the file with @task:<TASK-ID> tags inserted.

Files:

New module: guardkit/commands/feature_plan/bdd_linker.py (or similar) — parser, matcher, writer
installer/core/commands/feature-plan.md — add new phase between task creation and completion summary
Tests:
tests/unit/commands/feature_plan/test_bdd_linker.py — Gherkin parse/rewrite, formatting preservation, idempotency, tag insertion position
tests/integration/commands/feature_plan/test_bdd_linking_e2e.py — full feature file through linker; result passes pytest-bdd discovery for tagged tasks
Design decisions (already made):

Parser: use gherkin-official or pytest-bdd's parser. Do not roll a regex. This is the explicit design constraint — the whole point of this task is not to be brittle.
Matcher: LLM-assisted. Each scenario + each task's title/description/ACs → best-fit task ID + 0.0–1.0 confidence. Default threshold 0.6; below threshold = leave untagged and report.
Interactive vs non-interactive: respect --no-questions. Interactive = per-mapping confirmation. Non-interactive = auto-apply above-threshold, report skipped.
Rewrite safety: parse → insert → atomic rename. Temp file + atomic move. Never corrupt source.
Traps:

Idempotency is non-negotiable. Second run must detect existing @task: tags and skip re-mapping them. Users WILL re-run /feature-plan to iterate.
Formatting preservation. Must not touch existing comments, blank lines, feature-level tags, category tags. Only insert the new @task: tag immediately above the matched Scenario: line.
Matching failure modes — test all of these explicitly:
More scenarios than tasks: extras left untagged, reported.
Fewer scenarios than tasks: some tasks get no scenario, reported (R2 will skip them — fine).
Ambiguous scenarios (equal-confidence across 2+ tasks): flag for user in interactive; leave untagged in non-interactive.
Empty feature file: no-op.
Gotcha — scope discipline: this task does NOT modify bdd_runner.py or R2 activation semantics. The runner contract shipped by TASK-BDD-E8954 (plus F584 fix) stays exactly as-is. LINK only produces the artefact the runner already expects.

Validation ACs:

Given a feature spec producing a .feature file + tasks, /feature-plan run without intervention produces a file where every scenario maps to a task with @task:<TASK-ID> tag.
Second run is idempotent (no duplicates, no shifts).
The FEAT-JARVIS-001 .feature, re-run through the linker against the J001-001..011 task list, produces tagging matching TASK-BDD-JBKF's ground-truth subset (have that evidence file open during dev).
No features/*.feature case: step silently skips, no error.
All-tagged case: reports "0 new tags", exits.
pytest-bdd discovers scenarios on the rewritten file for the tagged tasks.
Effort: 1–2 days focused. This is the complexity-7 task — budget accordingly.

Phase 3 — TASK-COH-RUN1 (cohort run)
Mission: Fire forge + study-tutor autobuilds in parallel with R1/R2/R3 verified active. Produce combined review report.

Pre-flight (hard gate — MUST PASS before autobuild starts):


# R1 check (structural fix must have shipped + deterministic activation)
grep -q 'AC-quality review:' /path/to/forge/feature-plan-output.log
grep -q 'AC-quality review:' /path/to/study-tutor/feature-plan-output.log

# R2 check (FP-LINK auto-tagged the feature files)
grep -l '@task:' /path/to/forge/features/*.feature
grep -l '@task:' /path/to/study-tutor/features/*.feature

# R3 check (author added smoke_gates: per NDG2 nudge)
grep -E '^smoke_gates:' /path/to/forge/.guardkit/features/FEAT-*.yaml
grep -E '^smoke_gates:' /path/to/study-tutor/.guardkit/features/FEAT-*.yaml
If any of these fail → block the cohort and file a targeted follow-on task. Don't "waive and proceed."

Execution:

Parallel. Two separate Conductor workspaces (cohort-run-forge, cohort-run-study-tutor), two worktrees. guardkit autobuild feature FEAT-FORGE-XXX + guardkit autobuild feature FEAT-STUDY-TUTOR-XXX in separate terminals.
Do not intervene mid-run. If one fails, let it fail — the data is the point.
Use same Graphiti group IDs as jarvis run so post-run queries span all three cohort members.
Post-run capture (per cohort member):

Task completion counts, first-pass approval rate, wall time
bdd_results block presence in task_work_results.json per task + three-state breakdown
Smoke gate events fired / blocked a wave
AC-linter warnings surfaced during /feature-plan
Post-autobuild patch count at T+24h and T+72h
Report: docs/reviews/TASK-COH-RUN1-forge-study-tutor-cohort-review.md with:

Baseline-matrix rows for forge and study-tutor (continuing TASK-REV-4D012's format with jarvis row inserted from TASK-REV-4D190)
Per-remediation activation evidence
The load-bearing question: did R3 catch a composition failure that per-task Coach missed? (yes / no / not applicable)
Success criteria:

Cohort completed OR failed (either is valid data)
Report written, baseline matrix updated, the PEX-014..020 "review-gate hole" question answered
Traps:

A cohort member failure with R3 correctly blocking is a success for this task. Frame it that way in the report.
Expected negative finding: if R2 flags pending scenarios as failures, that's a regression in F584's fix. Halt, file, re-fix.
Don't compare 0-patch jarvis to 0-patch forge as apples-to-apples — remediation activation differs between runs.
Effort: ~4 hours attended (the autobuilds are autonomous; your time is pre-flight + report). Plus whatever the autobuilds themselves take (~1–2h each).

Standalone — TASK-REV-AC53 + TASK-REV-RWOP1 (do before COH-RUN1 if possible)
These are re-audits, not remediations. Value comes from surfacing unknown-unknowns before COH-RUN1 exposes them at cohort scale.

REV-AC53 — Re-audit TASK-AC-53445 under the runner-without-producer lens. Focus: the specific TASK-AC-53445 delivery — did it produce any other orphan hooks beyond Step 10.5? Read the PR diff and the TASK-AC-53445 task file; look for any "feature-plan.md mentions X but X has no imperative callsite" pattern. Output: report. Effort: 1–2h.

REV-RWOP1 — Broader audit of feature-plan, feature-spec, task-work specs for orphan runners. Focus: any component described in spec prose that lacks a runtime callsite. Use the two confirmed instances (R1 linter, R2 scenario tagger) as the pattern template. Grep systematically. Effort: 2–3h.

Both are review tasks (/task-review). No code changes; just reports + potential new task filings.

Recommended order

Day 1 (parallel, ~1 day):
  Session A: /task-work TASK-FP-NDG1 (ships NDG2 in same PR)
  Session B: /task-work TASK-FIX-3C9D

Day 1 evening (shared session):
  /task-review TASK-REV-AC53  (cheap, may surface new tasks)

Day 2–3 (focused session):
  /task-work TASK-FP-LINK

Day 3 evening:
  /task-review TASK-REV-RWOP1  (broader scan before cohort)

Day 4 (attended):
  /task-work TASK-COH-RUN1
    → pre-flight → kick off 2 parallel autobuilds → write report
If REV-AC53 or REV-RWOP1 surface additional defects, they may need to land before COH-RUN1 — file and triage as they appear.

One meta-note
After the FEAT-R2GP wave completes, you'll have data for TASK-REV-4D012's final carry-over question that's been open since jarvis: does R3 actually close the review-gate hole? If COH-RUN1's report answers "yes" (R3 caught a composition failure on forge or study-tutor that jarvis-shaped per-task Coach would have missed), the remediation cycle is complete. If "no," you'll need a Wave 4 to either strengthen R3 or re-think the gate.