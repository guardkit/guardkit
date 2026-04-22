---
id: TASK-FP-LINK
title: Implement R2 linking step in /feature-plan — rewrite features/*.feature with @task:<TASK-ID> tags after task creation
status: backlog
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: high
complexity: 7
tags: [feature-plan, r2, bdd-oracle, pipeline-gap, task-bdd-e8954-followon, linker]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 2
conductor_workspace: r2-pipeline-closure-wave2-linker
depends_on:
  - TASK-BDD-JBKF
---

# Task: Implement R2 linking step in /feature-plan

## Problem Statement

**TASK-REV-4D190 Addendum A** established that R2 is architecturally dormant-by-default. The runner (delivered by TASK-BDD-E8954) waits for `.feature` files containing `@task:<TASK-ID>` tags, but **no command in the current pipeline ever writes those tags**. `/feature-spec` can't (task IDs don't exist at spec time); `/feature-plan` creates tasks but doesn't touch the `.feature` file; `/task-work` consumes tags it expects to already exist. Gap.

Evidence: zero production `.feature` files in the repo contain `@task:` tags. The pattern exists only in test fixtures. TASK-BDD-E8954 explicitly deferred the emission step as a "natural follow-on." On the jarvis run, a thoughtful feature author wrote 15+ well-formed scenarios and still did not add a single task tag — not because they are negligent, but because the workflow never asks.

This task closes the gap by adding a post-task-creation pass to `/feature-plan` that reads the generated `.feature` file, maps scenarios to tasks, and rewrites the file with `@task:<TASK-ID>` tags inserted above matched scenarios.

## Scope

### In-Scope

- New pipeline step in `/feature-plan` (installer/core/commands/feature-plan.md and supporting library code) that runs **after** task creation is complete:
  1. Detect the `features/*.feature` file associated with the feature (convention or explicit path).
  2. Parse the Gherkin structure (scenarios + existing tags + comments + line ranges).
  3. For each task created, identify candidate scenarios. Matching must be LLM-assisted (scenario text + task title/description → best-fit task). Pure heuristic matching is brittle; the LLM has the context.
  4. Present the proposed mapping to the user for confirmation (interactive unless `--no-questions` is set). Allow edit/skip per scenario. Default behaviour when non-interactive: apply the LLM's highest-confidence mapping and log which scenarios were skipped due to low confidence.
  5. Rewrite the `.feature` file in-place, inserting `@task:<TASK-ID>` tags immediately before the matched `Scenario:` or `Scenario Outline:` line, **preserving** all existing tags, comments, blank lines, and Gherkin formatting.
  6. Emit a summary: "linked N scenarios to M tasks; K scenarios left untagged (low confidence)."
- Tests:
  - Unit: Gherkin parse/rewrite preserves formatting (comments, blank lines, existing tags).
  - Unit: mapping honours existing `@task:` tags (do not overwrite if already present).
  - Integration: a feature file + task list goes through linking and the rewritten file passes `pytest-bdd` discovery for the tagged tasks.
  - Integration: `/feature-plan --no-questions` runs end-to-end including linking and produces a tagged `.feature`.
- Documentation: update `installer/core/commands/feature-plan.md` with the new phase; cross-link to `feature-spec.md`'s "Task-scope tag convention" section; update the R2 bits of `autobuild-coach.md` if they imply a manual step.

### Out-of-Scope

- Building a standalone `/feature-link-bdd` command (dropped — Q1=[1]).
- Changing R2 activation semantics in `bdd_runner.py` — the runner contract stays exactly as delivered by TASK-BDD-E8954.
- Supporting hand-written `.feature` files that do not follow the `/feature-spec` output shape (those remain user-tagged; they are rare).
- Graduating R1 from warn-mode to block-mode (that's a separate track).

## Acceptance Criteria

- [ ] `/feature-plan` has a new phase (between task creation and completion) named e.g., "Phase N: BDD scenario linking" and it is documented in `installer/core/commands/feature-plan.md`.
- [ ] Given a feature spec that produces a `.feature` file and tasks, running `/feature-plan` without manual intervention produces a `.feature` file where every scenario that maps to a task carries a `@task:<TASK-ID>` tag.
- [ ] Existing `@task:` tags are never overwritten or duplicated.
- [ ] Existing comments, blank lines, feature-level tags, and category tags (`@key-example`, `@smoke`, etc.) are preserved byte-for-byte except for the inserted tag lines.
- [ ] An LLM scenario→task confidence score is recorded; scenarios below a configurable threshold (default e.g., 0.6) are left untagged and reported.
- [ ] Interactive mode: user can accept/edit/skip each proposed mapping. Non-interactive mode (--no-questions): highest-confidence-above-threshold mappings applied automatically.
- [ ] `pytest-bdd` on the rewritten file discovers scenarios for the tagged tasks (integration test).
- [ ] Running the command twice is idempotent: second run detects existing tags and re-uses them rather than re-mapping.
- [ ] When run against a feature with no `.feature` file, the step is skipped silently (no error).
- [ ] When run against a `.feature` file with all scenarios already tagged, the step reports "0 new tags" and exits.
- [ ] New tests added under `tests/unit/commands/feature_plan/` and `tests/integration/commands/feature_plan/`.
- [ ] The FEAT-JARVIS-001 `.feature` file, run through this step with the J001-001..011 task list, produces a sensible tagging (validated against TASK-BDD-JBKF's ground-truth subset).

## Implementation Notes

- **Cross-component interface note (per `.claude/rules/task-workflow.md`):** this task changes the artefact handed from `/feature-plan` to `/task-work`. The expected interface: after `/feature-plan` completes, `bdd_runner.find_feature_files_with_tag(task_id)` must return at least one match for every task that had a mappable scenario. Verify this contract in the integration test.
- **Gherkin parsing:** use an actual Gherkin parser (e.g., `gherkin-official` or `pytest-bdd`'s parser). Do not roll a regex-based parser — the point of this task is to not be brittle.
- **Rewrite safety:** read file, parse, insert tags, write to temp file, atomic rename. Never corrupt the source.
- **LLM prompt for matching:** supply the scenario text + task title + task description (if present) + task ACs. Ask for the best-fit task ID and a 0.0–1.0 confidence. Log both.
- **Idempotency is non-negotiable.** Users will re-run `/feature-plan` to iterate. Tags should land exactly once.
- **Failure modes to test explicitly:**
  - Zero scenarios (empty feature file): no-op.
  - More scenarios than tasks: extras left untagged, reported.
  - Fewer scenarios than tasks: some tasks get no scenario, reported (R2 will just not fire for them — that's fine).
  - Ambiguous scenarios (equally good fit for two tasks): flag for user resolution in interactive mode; leave untagged in non-interactive.

## Related

- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` (§Addendum A, especially the three-options table)
- Precursor: `tasks/completed/TASK-BDD-E8954/TASK-BDD-E8954.md` (Out-of-Scope note: *"Teaching `/feature-spec` to emit task-scope tags — that's a natural follow-on."* This is that follow-on, relocated to `/feature-plan` where task IDs are actually available.)
- Consumer: `guardkit/orchestrator/quality_gates/bdd_runner.py` (`find_feature_files_with_tag`, `run_bdd_for_task`)
- Interface docs: `installer/core/commands/feature-spec.md` §"Task-scope tag convention"
