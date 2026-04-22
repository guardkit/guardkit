---
id: TASK-FP-LNKB-19AC
title: Wire bdd-linker subagent and BDD scenario linking phase into /feature-plan
status: completed
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
completed: 2026-04-22T00:00:00Z
completed_location: tasks/completed/TASK-FP-LNKB-19AC/
previous_state: in_review
state_transition_reason: "Implementation complete; all acceptance criteria met; 72/72 tests passing; 84% line / 87% branch coverage on new module."
outcome: "Step 11 orchestrator + bdd-linker subagent + docs + integration tests delivered. R2 auto-activation pipeline closed from /feature-spec through /feature-plan to /task-work Phase 4."
evidence: docs/reviews/TASK-FP-LNKB-19AC-jarvis-linking-evidence.md
organized_files:
  - TASK-FP-LNKB-19AC.md
priority: high
complexity: 6
tags: [feature-plan, r2, bdd-oracle, pipeline-gap, linker, follow-on]
parent_review: TASK-REV-4D190
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 2
conductor_workspace: r2-pipeline-closure-wave2-linker-integration
depends_on:
  - TASK-FP-LINK
---

# Task: Wire bdd-linker subagent and BDD scenario linking phase into /feature-plan

## Problem Statement

TASK-FP-LINK delivered the mechanical half of the R2 linking step — a `bdd_linker` Python library that parses `features/*.feature` files, emits a structured matching request, and atomically rewrites the file with `@task:<TASK-ID>` tags when a mapping is confirmed. It is fully unit-tested and has a stable JSON contract (`MatchingRequest` → `TaskMatch[]`).

What's still missing is the orchestration half:

1. A `bdd-linker` subagent that takes a `MatchingRequest` and returns `TaskMatch[]` with confidence scores.
2. A new phase in `/feature-plan` that runs after task creation, invokes the subagent, presents the proposed mapping interactively (or applies highest-confidence-above-threshold when `--no-questions` is set), and calls `bdd_linker.apply_mapping` with the confirmed result.
3. End-to-end tests proving the rewritten file is discoverable via `bdd_runner.find_feature_files_with_tag` and that `pytest-bdd` picks up the scenarios for the tagged tasks.
4. Documentation updates in `feature-plan.md`, `feature-spec.md`, and (if it implies a manual step) `autobuild-coach.md`.

## Scope

### In-Scope

- New subagent `installer/core/agents/bdd-linker.md` that:
  - Accepts a JSON `MatchingRequest` payload (schema defined in `installer/core/commands/lib/bdd_linker.py`).
  - Returns a JSON array of `TaskMatch` values (`scenario_index`, `task_id`, `confidence`).
  - Reasons about scenario/task fit using the scenario steps + task title/description/ACs.
  - Has clear instructions on the confidence rubric (0.9+ = obvious fit, 0.7–0.9 = good fit, 0.5–0.7 = plausible, <0.5 = weak).
- New phase in `/feature-plan` (after Step 10 in the auto-detection pipeline, before the final summary). Named e.g. **"Step 11: Link BDD scenarios to tasks"**. Responsibilities:
  - Detect the `features/*.feature` file for the feature (convention: `features/{feature_slug}.feature` or `features/{feature_slug}/{feature_slug}.feature`).
  - Skip silently if no feature file exists.
  - Call `parse_feature_file`. Skip silently if no scenarios.
  - Call `build_matching_request` (omits already-tagged scenarios).
  - Invoke the `bdd-linker` subagent with the JSON payload.
  - Parse the response into `TaskMatch[]`.
  - **Interactive mode**: display proposed mappings in a table; user can `[A]ccept all`, `[E]dit scenario N`, `[S]kip scenario N`, `[D]one`. Edit lets the user swap the proposed task_id or set confidence to 0 (skip).
  - **`--no-questions` mode**: apply auto-threshold; log skipped low-confidence scenarios.
  - Call `apply_mapping` with the confirmed matches.
  - Print the `LinkingResult.summary` (e.g. "linked 3 scenario(s) to task(s); 0 already tagged; 1 below threshold (0.60); 1 untagged (of 5 total)").
- Integration tests in `tests/integration/feature_plan/test_bdd_linking.py`:
  - Mock the subagent response; feed a feature file + task list through the full phase; assert the rewritten file has the expected tags and that `bdd_runner.find_feature_files_with_tag(features_dir, f"@task:{task_id}")` returns the rewritten file for each linked task.
  - Test `--no-questions` path end-to-end (non-interactive defaults applied).
  - Test idempotency end-to-end: run the phase, then re-run with the same inputs; file unchanged, summary reports 0 new tags.
  - Test "no feature file" and "all already tagged" silent no-ops.
- Validation against FEAT-JARVIS-001's feature file + J001-001..011 tasks, using TASK-BDD-JBKF's evidence report as the ground-truth oracle subset. Record in a short evidence note under `docs/reviews/`.
- Documentation:
  - `installer/core/commands/feature-plan.md` — add "Step 11: Link BDD scenarios to tasks" section with the agent-invocation prose, the `--no-questions` behaviour, and the feature-file discovery convention.
  - `installer/core/commands/feature-spec.md` §"Task-scope tag convention" — add a forward-reference to `/feature-plan`'s linking phase.
  - `installer/core/agents/autobuild-coach.md` — if it currently implies manual tagging, update to reference the linker.

### Out-of-Scope

- The mechanical library — already shipped in TASK-FP-LINK.
- Standalone `/feature-link-bdd` command.
- Changes to `bdd_runner.py` or R2 activation semantics.
- Hand-written `.feature` files that don't follow `/feature-spec` output shape.

## Acceptance Criteria

- [ ] `installer/core/agents/bdd-linker.md` exists with metadata (stack=cross-stack, phase=orchestration, keywords=[bdd, gherkin, scenario, task, matching]) and clear prompt instructions.
- [ ] `installer/core/commands/feature-plan.md` documents Step 11 (BDD scenario linking), including the agent invocation, interactive flow, `--no-questions` behaviour, and file discovery convention.
- [ ] Running `/feature-plan` end-to-end (with a mocked subagent response in tests, real agent in practice) tags scenarios in the generated `.feature` file with `@task:<TASK-ID>` tags without manual intervention.
- [ ] Interactive mode allows per-scenario accept/edit/skip.
- [ ] `--no-questions` applies auto-threshold matches and reports untagged scenarios in the summary.
- [ ] Running `/feature-plan` twice against the same inputs is idempotent — second run reports 0 new tags and does not duplicate existing ones.
- [ ] No `.feature` file → step is silently skipped.
- [ ] Integration test: rewritten file is discovered by `bdd_runner.find_feature_files_with_tag(features_dir, task_tag(task_id))` for every linked task.
- [ ] FEAT-JARVIS-001 feature file + J001 task list produces a sensible tagging (documented in a short evidence note; ground truth from TASK-BDD-JBKF).
- [ ] `feature-spec.md` and (if applicable) `autobuild-coach.md` cross-reference the new phase.

## Implementation Notes

- The library contract is stable: `installer/core/commands/lib/bdd_linker.py` exposes `parse_feature_file`, `existing_task_tags`, `build_matching_request`, `apply_mapping`, and the `TaskInfo`/`TaskMatch`/`MatchingRequest`/`LinkingResult` dataclasses. Do not re-implement parsing or rewriting.
- The subagent's JSON output needs to parse cleanly into `TaskMatch` values. Surface parse errors with a clear retry path rather than silently dropping matches.
- The feature-file discovery convention should match what `/feature-spec` actually writes (verify before coding). The jarvis precedent uses `features/{slug}/{slug}.feature`; the simpler `features/{slug}.feature` also exists.
- For the interactive table, use `rich` (already a core dependency) for consistency with other commands.
- Confidence threshold default: 0.6 (inherited from `bdd_linker.DEFAULT_CONFIDENCE_THRESHOLD`). Make it configurable via a `--bdd-link-threshold=0.X` flag for power users, but do not require a command-line flag for the default behaviour.

## Related

- **Upstream**: TASK-FP-LINK (delivered the `bdd_linker` library).
- **Parent review**: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` §Addendum A.
- **Consumer contract**: `guardkit/orchestrator/quality_gates/bdd_runner.py` — `find_feature_files_with_tag`, `run_bdd_for_task`, `task_tag`.
- **Interface docs**: `installer/core/commands/feature-spec.md` §"Task-scope tag convention".
- **Nudge fallback**: `installer/core/commands/lib/bdd_oracle_nudge.py` (TASK-FP-NDG1) — when this task lands, decide whether the nudge stays as a fallback for hand-written feature files or is removed.
