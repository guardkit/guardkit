---
review_id: TASK-REV-4D190
title: "Review: first jarvis autobuild run (FEAT-JARVIS-001) post Coach updates"
mode: architectural
depth: comprehensive
date: 2026-04-22
revision: 2  # r2 deep-dive addendum added 2026-04-22
parent_review: TASK-REV-4D012
related_tasks:
  - TASK-AC-53445  # R1
  - TASK-BDD-E8954 # R2
  - TASK-SMK-F703A # R3
decision: proceed-with-conditions
---

# Review: first jarvis autobuild run (FEAT-JARVIS-001) post Coach updates

## Executive Summary — decision-ready

**Decision: PROCEED with forge + study-tutor runs in parallel, under two conditions.**

FEAT-JARVIS-001 completed cleanly: **11/11 tasks**, **10/11 first-pass approvals (91%)**, **57m 36s** wall-clock, **0 post-autobuild patches** in the 14+ hours since completion. By the raw numbers the run is a regression-free execution.

But the honest reading of this run is the one the task brief asked for explicitly: **a clean run on an 11-task scaffolding feature does not prove R1/R2/R3 work; it proves they don't break anything.** All three remediations were **inactive** on this run:

| | Activated on FEAT-JARVIS-001? | Reason |
|---|---|---|
| **R1** — Assertable-AC linter | **No (non-deterministic)** — TASK-FIX-7B2E retro-grep of FEAT-JARVIS-001 planner history shows 0 matches for the `AC-quality review:` header. A separate fresh-session dynamic test against a prose-AC fixture *did* fire the linter. Activation is session-dependent under the Claude-as-runtime model. | Runner-without-producer: spec describes linter post-step in prose but Step 10.5 has no imperative callsite and is absent from the execution trace. Claude interprets the spec non-deterministically across sessions. Addressed by TASK-FIX-3C9D (structural fix). Cross-link: `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md` §"Retro grep of FEAT-JARVIS-001". |
| **R2** — BDD oracle | **No** — 0 tasks had `bdd_results` in `task_work_results.json` | Feature file exists but lacks `@task:<ID>` scenario tags (R2 trigger) |
| **R3** — Feature-level smoke gates | **No** — `FEAT-JARVIS-001.yaml` has no `smoke_gates:` key | Plan author did not opt in |

This is **exactly the design TASK-REV-4D012 specified**: "zero change for tasks without a matching `features/*.feature` file ... zero change for features without `smoke_gates` key ... all three are opt-in-by-artefact-or-config ... nothing already passing will start failing." On that criterion alone jarvis is a perfect pass — the remediations are additive and did not regress a working cohort.

However, jarvis also did not exercise the **composition surface** that motivated R3 (the PEX-014..020 pattern: "13/13 green + e2e broken"). An 11-task supervisor/session-lifecycle skeleton has low inter-task schema-shape risk; forge and study-tutor do not. The original sequencing rationale — "jarvis first to shake out regressions" — is satisfied. The remaining question is no longer "will the remediations regress?" (answered: no) but "will they activate when they should?" (answered: not yet tested).

**Conditions for proceeding:**
1. **Activate R3 on forge + study-tutor feature plans** — require `smoke_gates:` in their `.yaml` with at minimum a feature-level sanity check after each wave. Do not run them R3-blind.
2. **Activate R2 on forge + study-tutor features** — require `@task:<TASK-ID>` tags on at least one scenario per task in their `features/*.feature` files. **See Addendum §A below — R2 is structurally dormant-by-default until `/feature-plan` (or a new linker command) rewrites `.feature` files with task tags. Interim activation is a manual edit step.** This is the first real activation of the oracle; without it, R2 remains vaporware validated only by unit tests.

R1 (AC linter) needs no explicit activation since it's warn-mode and the plan author cannot opt out; an independent verification step (below) is recommended to confirm it actually runs during `/feature-plan`.

> **Note (revision 2):** After this report's first draft flagged R2 non-activation, a targeted investigation confirmed the root cause is a **workflow pipeline gap, not per-feature author negligence**. See §**Addendum A — R2 activation is architecturally dormant-by-default** below. The recommendation above is updated accordingly: activating R2 for forge + study-tutor requires manual tagging *today*, and a new task to build a `/feature-plan` tagging pass (or a `/feature-link-bdd` command) should block R2's graduation from "runner exists" to "runner runs in production."

## Run outcome

**Source of truth:** `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/reviews/phase-1/autobuild-FEAT-JARVIS-001.md` (2,081 lines) and `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/`.

| Metric | Value |
|---|---|
| Tasks completed | 11/11 |
| Tasks blocked | 0 |
| Waves | 6 (sizes: 3, 2, 2, 1, 1, 2) |
| First-pass (1-turn) approvals | 10/11 (91%) |
| Multi-turn tasks | 1 (TASK-J001-002: 2 player / 2 coach turns) |
| Wall-clock | 57m 36s (2026-04-21T22:31:06 → 23:28:43 UTC) |
| Post-autobuild patches filed | 0 (verified by mtime scan of `tasks/` — 14h+ elapsed) |
| SDK-turn ceiling hits | 0/5 (max 48 / 100) |
| Coach rejections | 1 (resolved on turn 2 of TASK-J001-002) |
| Upstream noise | Graphiti `RecursionError` in `edge_fulltext_search` — known upstream graphiti-core/FalkorDB issue, non-blocking, workaround applied |

## Per-remediation assessment

### R1 — Assertable-AC linter in `/feature-plan` (TASK-AC-53445, warn-mode v1)

> **Note (revision 3, 2026-04-22):** TASK-FIX-7B2E completed static + dynamic verification. Revised verdict below. Short version: **R1 activation is non-deterministic across Claude sessions** (spec-interpretation-dependent). Retro-grep of FEAT-JARVIS-001 planner history shows 0 matches for `AC-quality review:` — R1 did not fire on the real cohort run. A separate dynamic test in a different Claude session (against `tests/fixtures/r1-verification/prose-ac-spec.md`) *did* fire it. This is precisely the "runner without producer" pattern manifesting as session-dependent behaviour. Cross-link: `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md` §"Retro grep of FEAT-JARVIS-001". Structural fix tracked in TASK-FIX-3C9D (priority: high; now blocks TASK-COH-RUN1). The original analysis below (revision 1 wording: "inconclusive") is preserved for lineage — the two explanations (a) and (b) are *both* partially right: the linter is not wired in the deterministic sense (a), AND the ACs were already largely assertable (b), so the absence of output on jarvis cannot distinguish them. TASK-FIX-7B2E's prose-AC fixture eliminates (b) as an explanation, and the retro-grep against that fixture's header pattern in jarvis history closes the question.

**Activation evidence (revision 1 — superseded):** No `assertable`, `ac-linter`, or warning-flagged markers found in `FEAT-JARVIS-001.yaml` or any task file. There are two possible explanations and no way to distinguish them from the run artefacts alone:

- **(a) Linter not wired into `/feature-plan`:** the TASK-AC-53445 implementation was not in place, or was disabled, when the feature plan was generated.
- **(b) Linter ran silently because ACs were already assertable:** warn-mode on high-quality phrasing produces no output.

**Evidence for (b) over (a):** the sampled ACs are uniformly high-quality assertables. Examples verbatim from three task files:

- TASK-J001-005: *"`infrastructure.logging.configure("INFO")` produces JSON-formatted events on a pipe, console-formatted on a TTY."* — testable via format assertion.
- TASK-J001-006: *"`build_supervisor(test_config)` returns a `CompiledStateGraph` without issuing any network request (verified by mock of the chat model's transport layer)."* — testable via mock assertion.
- TASK-J001-007: *"Concurrent invoke on the same session ... raises `JarvisError` with a clear message (ASSUM-003)."* — testable via `pytest.raises`.

These are the phrasings R1 is designed to *accept without warning*. None of the sampled ACs would trigger the linter's "prose AC" heuristic (per parent review: "schema shape, stub semantic drift, path validation" class of bugs).

**Comparison to TASK-REV-4D012 prediction.** The parent review's acceptance criterion for R1 was: *"on a re-run of the specialist-agent FEAT-POR-EXT planning call, at least 3 of the 6 post-patch bugs have a corresponding warning-flagged AC in the revised plan output."* jarvis does not test this criterion — it's the wrong feature. The specialist-agent re-run remains the real R1 acceptance gate.

**Recommendation:** **Verify R1 wiring explicitly before running forge/study-tutor.** File a 30-minute investigation task (see "Follow-on tasks" below). Cost is trivial; consequence of flying blind through forge+study-tutor is non-trivial.

**Misfire check:** None. No false positives, no workflow disruption. The linter either did nothing or did nothing because there was nothing to flag.

### R2 — BDD oracle wiring (TASK-BDD-E8954, task-work reads task-scoped features/*.feature)

**Activation evidence: did not fire, by design.**

- `features/` directory exists at the jarvis root: **yes**, contains one file — `project-scaffolding-supervisor-sessions.feature` (well-formed Gherkin, 15+ scenarios across "Key Examples / Boundary Conditions / Negative Cases" groups).
- `bdd_results` in any `task_work_results.json`: **zero matches** across all 11 task directories.
- "pending" scenario mentions in Coach rejections or run log: **none**.

**The gap:** R2's activation trigger is the presence of a feature file with **`@task:<TASK-ID>` tags on scenarios** (per the Graphiti note on `bdd_runner.run_bdd_for_task`). The jarvis feature file has scenarios but no task-ID tags. Per the parent review's R2 acceptance criterion #3: *"A feature-level `.feature` (no task-scope tags) is **not** run by R2 — that's R3's surface."* So R2 behaved **exactly as specified**: a task without matching scoped scenarios got treated as today's task, with no BDD invocation.

**The non-gap that's nonetheless uncomfortable.** The three-state pass/fail/**pending** model was designed specifically to prevent "unscaffolded features from falsely appearing as build breaks" (per Graphiti: *"BDD oracle must not collapse pending into failed. The approval rule is `scenarios_failed == 0`."*). The jarvis run did not exercise this model. If any of R2's three states has a bug, this run would not have surfaced it.

**Comparison to TASK-REV-4D012 prediction.** Parent review AC #1: *"A demo feature with a task-scoped `.feature` file containing one failing scenario causes Coach to reject with a specific `bdd_results` feedback entry."* jarvis does not test this. There has been no real-code BDD run under this cohort yet.

**Recommendation:** **Backfill R2 activation** before forge/study-tutor runs. Two cheap options:
- **(Preferred) Add `@task:J001-*` tags** to two of the existing jarvis scenarios post-hoc and run `pytest-bdd` locally against the merged code. If `bdd_results` appears in a fresh `task_work_results.json` with the correct three-state breakdown, R2 is operationally validated. If it doesn't appear, R2 has a wiring bug caught before forge/study-tutor.
- (Alternate) Require task-tagged scenarios in forge/study-tutor feature files from their `/feature-spec` output. Makes forge/study-tutor the first activation — riskier but acceptable given the warn-mode regression envelope.

**But the recommendation above is a workaround. See §Addendum A — R2 activation is architecturally dormant-by-default.** The jarvis miss is not a plan-author mistake; it's a workflow pipeline gap. `/feature-spec` does not emit `@task:<ID>` tags (it can't — task IDs don't exist yet), and `/feature-plan` does not insert them after tasks are created. There is **no command in the current pipeline** that writes the activation artefact R2 needs. TASK-BDD-E8954 delivered the runner and explicitly deferred the linking step as a follow-on. That follow-on is now the single biggest blocker to R2 being a real quality gate rather than a latent capability.

**Misfire check:** None. The oracle correctly did not fire on an untagged feature file. This *is* the acceptance-criterion-2 behaviour. The issue is not misfire; it is **structural non-activation**.

### R3 — Feature-level smoke gates (TASK-SMK-F703A, between autobuild waves)

**Activation evidence: did not fire, by design.**

- `FEAT-JARVIS-001.yaml` contains **no `smoke_gates:` key**. Full file reviewed.
- Grep across `events.jsonl` for `smoke_gate|smoke-gate|SMOKE`: **zero matches**.

Per the parent review: *"zero change for features without `smoke_gates` key."* Behaviour matched the spec exactly.

**The uncomfortable observation.** TASK-REV-4D190's own brief called FEAT-JARVIS-001 "the first cohort autobuild run to execute after the R1–R3 remediations ... landed." If the plan author — who was aware this was a proving run — did not opt into smoke gates, that's a soft signal that the R3 opt-in ergonomics may be too quiet. The gate is invisible by default, and there is no nudge from `/feature-plan` to add one. For forge + study-tutor this needs to be corrected.

**Does jarvis surface the class of composition bug R3 is meant to catch?** Probably not. The PEX-014..020 pattern was:
1. Inter-task schema drift (129 Pydantic errors)
2. Path-validation / directory-structure failures (`[Errno 20] Not a directory`)
3. Stub semantic drift

FEAT-JARVIS-001 is "Project Scaffolding, Supervisor Skeleton & Session Lifecycle." The scaffolding surface has low inter-task schema risk (each task is mostly independent: logging, config, supervisor factory, session manager). The 11-task / 6-wave shape is modest. The composition surface on forge and study-tutor — both larger, both closer in character to specialist-agent than to jarvis — is where R3 will actually get exercised.

**Comparison to TASK-REV-4D012 prediction.** Parent review AC: *"A demo feature with a failing smoke command causes `/feature-build` to stop after wave 1 ... a demo without `smoke_gates` runs unchanged."* The second half is verified by this run. The first half remains untested on any real cohort.

**Recommendation:** **Require `smoke_gates:` in forge and study-tutor feature plans.** Minimal bar: after each wave, run a feature-level sanity check (e.g., for a Python feature, `python -c "import <module>"`; for services, a `--phase <name>` smoke). The plan author should not be able to opt out silently.

**Misfire check:** None. Zero smoke-gate events means zero misfires.

## Comparison matrix — jarvis added to TASK-REV-4D012 baseline

Extending the baseline from §3 of TASK-REV-4D012:

| Repo | Tasks via autobuild | 1st-pass approval | Integration tests exist? | Integration run by Coach? | BDD `.feature` present | BDD consumed anywhere | Post-build patches needed | Notes |
|---|---:|---:|---|---|---|---|---:|---|
| nats-core | 30 | 30/30 (100%) | Yes | No | No | — | 0 | ACs assertable |
| nats-infrastructure | 20 | 20/20 (100%) | Excluded | No | No | — | 0 | Small surface |
| youtube-transcript-mcp | 37 | 30/37 (81%) | Yes | No | No | — | 0 | Task-sizing issue on SKEL-004 |
| agentic-dataset-factory | 48 | 44/48 (92%) | Yes (stubs) | Partial | Yes | No | 0 | Stub conftest enables unit path |
| specialist-agent | 75 + 102 | 71/75 (95%) | Yes | No | Yes | **No** (passed to /feature-plan only) | **6+ (PEX-014..020)** | Highest Coach rate, worst e2e surface |
| **jarvis (FEAT-JARVIS-001)** | **11** | **10/11 (91%)** | **Yes** | **No** | **Yes (untagged, not run)** | **No** | **0 (at T+14h)** | **First cohort run post-R1/R2/R3. None of R1/R2/R3 activated.** |

**Where does jarvis land?** On first-pass rate alone (91%), jarvis sits between specialist-agent (95%) and ADF (92%). On post-build patch count (0), it sits with the clean cohorts. But jarvis is by far the **smallest** cohort member (11 vs 20–75 tasks) and the simplest composition surface, so these metrics say less than they appear to.

The review-gate hole Graphiti episode ("Review-gate hole: AutoBuild 13/13 green + e2e broken") is **not falsifiable on this run**: with zero smoke gates configured, we cannot know whether R3 would have caught a composition failure, because there's no composition failure in scaffolding to catch. The hypothesis remains alive and untested.

## Post-autobuild patch triage

**Count at T+14 hours:** 0.

Directory scan (`tasks/backlog`, `tasks/in_progress`, `tasks/completed`, `tasks/blocked`, `tasks/in_review`, `tasks/design_approved`) for anything created after 2026-04-21T23:28:43 UTC: **no hits**. No PATCH-*, FIX-*, or HOTFIX-* tasks. The only review-adjacent item is `in_review/TASK-REV-J001-plan-project-scaffolding-supervisor-sessions.md`, dated pre-run (21:13 UTC).

**Comparison to specialist-agent baseline:** specialist-agent required 6 patches (PEX-014..020) within 36h of its autobuild. jarvis is at 0 patches at T+14h with no obvious smoke failures reported anywhere downstream. This is a strong early signal — but the specialist-agent patches were triggered by downstream composition smoke which was **the thing that was absent on jarvis**. Comparing patch counts between a run with smoke gates and one without is not apples-to-apples. The clean 0 on jarvis should be read as "nothing leaked into tasks that we can measure," not "nothing was broken."

**Pre-Coach-approval-blind check:** zero of the post-run tasks (all 0 of them) appear to be that class. The specific failure pattern (*"previously this same error only fired post-Coach-acceptance after burning tokens"*) cannot recur on a run that had no post-Coach-acceptance smoke step — the detection surface simply wasn't active.

## Surprises

**Positive:**
- **Single-turn dominance (10/11).** Even higher than specialist-agent's 95%. Supervisor/session-lifecycle code is apparently very amenable to single-turn implementation under the current Coach.
- **Zero SDK-turn ceiling hits.** Max 48/100 on TASK-J001-008. Coach–Player exchanges are tight.
- **Upstream Graphiti noise was non-blocking.** `RecursionError in edge_fulltext_search` fired 20+ times without causing any task failure. The workaround is solid.

**Neutral / uncomfortable:**
- **The feature file was written but not tagged.** `project-scaffolding-supervisor-sessions.feature` is well-formed Gherkin with >15 scenarios. The author wrote it. They just didn't tag scenarios with `@task:J001-*`. This looks like an awareness gap: once a feature file exists, adding two words (`@task:J001-005`) per scenario is trivial, and the cost of doing it is much lower than the information gained from activating R2.
- **`/feature-plan` did not nudge toward `smoke_gates:`.** For a feature explicitly labelled as the first post-remediation cohort run, the silent opt-out is uncomfortable. This is an ergonomics bug, not a correctness bug, but it matters for future cohorts.

**Negative:**
- **The run validated zero percent of R1/R2/R3's behavioural surface.** Expected (that's what "opt-in by artefact" means), but worth naming as the single most important finding.

## Answers to the task's acceptance-criteria questions

- *"Did the jarvis run clear cleanly enough to proceed with forge + study-tutor in parallel?"* **Yes, clear-enough to proceed — but the criterion for clearance (regression-free on existing surface) is the *easy* criterion. The hard criterion (R1/R2/R3 positively demonstrate value on a real run) is not yet met.** Proceeding with forge + study-tutor is correct; proceeding with them R3-blind is not.
- *"Did any of R1/R2/R3 misfire?"* **No — none of them fired at all.** Zero false warnings, zero blocked good work, zero misleading output. The regression envelope is validated.

## Go/no-go criteria used

**Go:** (a) No Coach regressions observed; (b) No post-autobuild patches filed; (c) R1/R2/R3 design spec ("opt-in by artefact-or-config; nothing already passing will start failing") verified.

**No-go would have been:** a single post-run patch attributable to a pattern R3 was meant to catch, a Coach rejection caused by a false-positive warning from R1, or a `bdd_results` entry showing incorrect pass/fail/pending categorisation. None observed.

**Caveat:** these are "no-regression" criteria. They do not test "R1/R2/R3 work when activated." Go/no-go on forge + study-tutor activation is a separate question, addressed by the recommendations above.

## Recommendation

**Proceed with forge + study-tutor in parallel, under these conditions:**

1. **Activate R3:** forge and study-tutor feature plans must contain a non-empty `smoke_gates:` block with at least one per-wave sanity check.
2. **Activate R2:** feature files for forge and study-tutor must include `@task:<TASK-ID>` tags on at least one scenario per task.
3. **Verify R1 wiring** before starting forge + study-tutor (see follow-on below).
4. **Backfill R2 on jarvis** (cheap) to get one real-code activation data-point before running larger cohorts.

## Addendum A — R2 activation is architecturally dormant-by-default

### The question

> "R2 did not fire because the feature file lacks `@task:<ID>` scenario tags. Is this because `/feature-spec` and/or `/feature-plan` need updating to enable this?"

### The answer, in one line

**Yes — and the gap is larger than a single-command fix.** The current workflow has no command that ever inserts `@task:<TASK-ID>` tags into a `.feature` file. R2 is a runner that waits for an artefact shape the rest of the pipeline does not produce.

### The chicken-and-egg pipeline gap

```
/feature-spec     ──►  writes features/*.feature   (task IDs do not exist yet; cannot tag)
       ↓
/feature-plan     ──►  creates tasks with IDs      (does not touch the .feature file)
       ↓
       ◄── GAP: no command writes @task:<TASK-ID> tags back into the .feature ──►
       ↓
/task-work        ──►  calls bdd_runner.run_bdd_for_task(task_id)
       ↓
bdd_runner.find_feature_files_with_tag()  ──►  greps for the literal string "@task:TASK-XXX"
       ↓
       ──►  zero matches  ──►  returns None  ──►  no bdd_results in task_work_results.json
```

Every step behaves correctly in isolation. The gap is **between** `/feature-plan` and `/task-work`: the artefact handed over has no task linkage, so the runner silently returns `None`.

### Evidence this is by design, not a defect

1. **`/feature-spec` output spec (installer/core/commands/feature-spec.md, Phase 6, lines 366–384)** shows scenarios tagged only with category tags (`@key-example`, `@smoke`, `@boundary`, `@negative`, `@edge-case`). `@task:` tags are not in the emission template.
2. **`/feature-spec.md`, "Task-scope tag convention" section (lines 469–500)** — added by TASK-BDD-E8954 — describes the `@task:<TASK-ID>` convention as **user-added guidance**, not an auto-emission instruction. Phrasing: *"When a scenario **should** run as a task-level BDD oracle, tag it with `@task:<TASK-ID>`."*
3. **TASK-BDD-E8954 Out-of-Scope section** explicitly defers tagging: *"Teaching `/feature-spec` to emit task-scope tags — that's a natural follow-on if Gherkin adoption grows."* R2's runner was delivered; R2's *input pipeline* was not.
4. **`bdd_runner.py` module docstring:** *"Activation is by artefact presence (a `features/*.feature` file containing the task's `@task:<TASK-ID>` tag), never by frontmatter flag."* Artefact-presence-driven activation is the entire activation contract.
5. **`bdd_runner.find_feature_files_with_tag`** is a literal text scan for `@task:<TASK-ID>`. No fallbacks (no filename-matching, no scenario-name-matching, no heuristic).
6. **Grep for `@task:` across production code:** zero hits. All matches are in test fixtures demonstrating the expected shape. The pattern has **never existed on a real feature file** in this repository.
7. **Jarvis feature file** was generated by `/feature-spec` exactly as the spec prescribes — well-formed Gherkin, category tags only. It is correct output. The absence of `@task:` tags is not a `/feature-spec` bug; it is a deliberate scope boundary.

### Why auto-emission can't live in `/feature-spec`

`/feature-spec` runs **before** any tasks exist. Task IDs are assigned downstream by `/feature-plan`. At spec-generation time there is nothing to tag *with*. Attempting auto-emission in `/feature-spec` would require either:
- placeholder tags (`@task:TBD-1`) rewritten later by a linker — which means the linker still has to be built, and
- a forward reference that breaks the separation between spec and plan.

Either way, `/feature-spec` is the wrong place.

### The three viable fixes

| | Where | What | Cost | Pros | Cons |
|---|---|---|---|---|---|
| **Option 1** | `/feature-plan` | Add a post-task-creation pass that reads the `.feature` file, matches scenarios to tasks (by name heuristic or LLM), rewrites the file with `@task:<TASK-ID>` tags inserted. | 1–2 days | Zero new command; activation becomes default when both artefacts present; matches the intuitive mental model ("planning links scenarios to tasks"). | Matching is brittle unless LLM-assisted. Rewriting a user-edited file requires care (preserve comments, formatting). |
| **Option 2** | New `/feature-link-bdd` command | A standalone interactive command: show scenarios, show tasks, let the user (or an LLM) map them, write tags. | 3–4 days | Clean separation of concerns; works even when `.feature` is hand-written outside `/feature-spec`; explicit and auditable. | Adds a manual step to the canonical workflow. Users will forget to run it (same class of miss we saw on jarvis). |
| **Option 3** | Docs + nudge only | `/feature-plan` output prints: *"To activate R2 BDD oracle: edit features/*.feature and add `@task:<TASK-ID>` to scenarios you want Coach-gated."* No code. | 30 minutes | Lowest effort; transparent about the limitation. | Same failure mode as jarvis (well-intentioned author doesn't tag); R2 remains effectively dormant for most cohorts. |

**Recommendation: Option 1 (preferred) with Option 3 as immediate interim.** Reasoning: R2 was built to be the Coach's BDD verification oracle, but an oracle no one activates is indistinguishable from an oracle that does not exist. Until `/feature-plan` closes the linking step, R2's value is one-off per cohort (someone remembering to edit the file). That's not a quality gate — that's a discipline check.

The TASK-BDD-E8954 "natural follow-on" deferral was reasonable *if* users would manually tag, but FEAT-JARVIS-001 is our first data point and the answer was: **they don't**. The scenario author wrote 15+ well-formed scenarios and still did not add a single task tag. This is not negligence; it's friction against a non-obvious workflow step. The pipeline should do it.

### What this means for the go/no-go

The top-level decision ("proceed with forge + study-tutor under conditions") does **not** change. What changes is the **cost** and **certainty** of condition #2:

- **Previously stated:** "Activate R2 on forge + study-tutor — require `@task:<TASK-ID>` tags on at least one scenario per task."
- **Actually required today:** someone (the feature author or reviewer) must manually edit the `.feature` file after `/feature-plan` creates tasks, before `/task-work` runs. This is error-prone, easy to skip, and not auditable from artefacts alone.
- **Should be required before further cohorts beyond forge + study-tutor:** one of Options 1 or 2 above shipped, so R2 activates by the artefacts alone — no discipline required.

Forge + study-tutor can proceed with the manual tagging workaround, **but the manual tagging must be verified** (grep the `.feature` files for `@task:` before autobuild, verify `bdd_results` appears in `task_work_results.json` after). And before any *subsequent* cohort, the linking step must move into the pipeline.

## Follow-on tasks (drafts) — revised after Addendum A

```bash
# 1. Verify R1 linter is actually wired into /feature-plan
/task-create "Verify R1 (assertable-AC linter) fires in /feature-plan by running it on a known-prose-AC fixture" \
  prefix:FIX tags:[autobuild,r1,verification,task-ac-53445] related_to:TASK-REV-4D190 priority:high

# 2. Backfill R2 activation on jarvis to get one real-code data point
/task-create "Backfill R2 by tagging 2 jarvis scenarios with @task:J001-* and running pytest-bdd to confirm bdd_results emission" \
  prefix:BDD tags:[autobuild,r2,backfill,jarvis,task-bdd-e8954] related_to:TASK-REV-4D190 priority:high

# 3. Close the R2 pipeline gap: /feature-plan should insert @task:<TASK-ID> tags into features/*.feature
#    (The architectural fix. TASK-BDD-E8954's deferred "natural follow-on".)
/task-create "Implement R2 linking step in /feature-plan: after tasks are created, rewrite features/*.feature to insert @task:<TASK-ID> tags on scenarios mapped to each task (LLM-assisted matching, preserve comments)" \
  prefix:FP tags:[feature-plan,r2,pipeline-gap,bdd-oracle,task-bdd-e8954-followon] related_to:TASK-REV-4D190 priority:high

# 3b. Short-term ergonomics: /feature-plan prints a nudge when a .feature exists but has no @task: tags
/task-create "Add /feature-plan warning: when features/*.feature exists without any @task:<TASK-ID> tag, print an activation-gap notice with a copy-paste workaround command" \
  prefix:FP tags:[feature-plan,r2,ergonomics,nudge,interim] related_to:TASK-REV-4D190 priority:medium

# 4. Require R3 opt-in ergonomics for future feature plans
/task-create "Update /feature-plan to warn when smoke_gates: is missing from an autobuild feature plan (R3 opt-in ergonomics)" \
  prefix:FP tags:[feature-plan,r3,ergonomics,task-smk-f703a] related_to:TASK-REV-4D190 priority:medium

# 5. Fire forge + study-tutor cohort runs with R1/R2/R3 activation required AND VERIFIED
/task-create "Run forge and study-tutor autobuild cohort in parallel with R1/R2/R3 activation required; pre-flight check must grep for @task: tags in features/*.feature and verify smoke_gates: in the .yaml before autobuild starts" \
  prefix:COH tags:[autobuild,cohort,forge,study-tutor,r1,r2,r3,preflight] related_to:TASK-REV-4D190 priority:high

# 6. (Optional, future) Post-hoc linker command for hand-written features
/task-create "Build /feature-link-bdd command: interactive scenario-to-task linker for .feature files generated outside /feature-spec or hand-edited" \
  prefix:CMD tags:[commands,feature-link-bdd,r2,follow-on] related_to:TASK-REV-4D190 priority:low
```

## Related

- **Parent review:** `docs/reviews/TASK-REV-4D012-autobuild-coach-integration-review.md`
- **R1 task:** `tasks/backlog/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
- **R2 task:** `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md`
- **R3 task:** `tasks/completed/TASK-SMK-F703A/TASK-SMK-F703A.md`
- **Jarvis run log:** `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/reviews/phase-1/autobuild-FEAT-JARVIS-001.md`
- **Jarvis autobuild state:** `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-JARVIS-001/`

**Does this review's predictions confirm TASK-REV-4D012's?** Yes for the regression-envelope prediction ("nothing already passing will start failing" — confirmed). **Not yet testable** for the activation predictions (R1 catching ≥3 of the 6 PEX bug classes on a re-run; R2 `bdd_results` emission; R3 stopping after wave-1 on failing smoke). Those predictions remain open until forge and study-tutor run with the remediations activated.

**Graphiti episode status:** *"Review-gate hole: AutoBuild 13/13 green + e2e broken"* — **pattern not reproducible on jarvis**, but **not because the hole is closed**. The hole remains open because R3 was not configured on this run. The test of whether the hole is closed requires a cohort member with `smoke_gates:` configured and a composition surface large enough to fail. forge and study-tutor are that test.

## Context Used

Knowledge-graph context retrieved in Phase 1.5 (via `mcp__graphiti__*`, groups `guardkit__task_outcomes` and `guardkit__project_decisions`) and influencing this review:

- **Node "AutoBuild Coach integration gaps"** — established that TASK-REV-4D012 recommended R1–R3 and set jarvis-first cohort sequencing. Used to frame the go/no-go structure.
- **Node "AutoBuild Coach first-pass approval rate"** — stated explicitly that first-pass approval is a poor proxy for feature quality, and must be paired with post-build patch count as a composition-health signal. Drove the decision to treat the 91% + 0 patches numbers as necessary but not sufficient.
- **Node "BDD oracle must not collapse pending into failed"** — defined the three-state pass/fail/pending contract of R2 (`guardkit.orchestrator.quality_gates.bdd_runner.BDDResult`). Used to frame the R2 activation gap (no BDD ran → three-state model untested).
- **Node "autobuild.bdd_oracle: true"** — confirmed R2's activation trigger is the presence of a `features/*.feature` file **tagged with `@task:<TASK-ID>`**, not a YAML flag. This is why a present-but-untagged feature file correctly did not fire R2.
- **Node "Feature-level smoke gates"** / fact "AutoBuild smoke gates fire between waves, not tasks" — confirmed R3's placement. Used to rule out "did R3 fire per-task?" as a question.
- **Fact "specialist-agent's Player-Coach approval rate was 95%"** — baseline for comparison matrix.
- **Fact "FEAT-POR-EXT was approved by the Coach but then failed smoke testing, leading to numerous patch tasks"** — the canonical PEX-014..020 pattern, used to frame the "review-gate hole" and recommend R3 activation on forge/study-tutor.
