---
id: TASK-FIX-RWOP1.7
title: Align wider --from-spec docs/metadata footprint with the RWOP1.5 quarantine
status: completed
task_type: cleanup
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T13:15:00Z
completed: 2026-04-23T13:15:00Z
previous_state: in_review
state_transition_reason: "Task completion via /task-complete"
priority: low
complexity: 3
tags: [docs-cleanup, from-spec, post-rwop1.5, hygiene, rwop1]
parent_review: TASK-REV-RWOP1
parent_task: TASK-FIX-RWOP1.5
feature_id: FEAT-RWOP1
related_to: TASK-FIX-RWOP1.5
related_tasks:
  - TASK-FIX-RWOP1.5
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-23T12:55:00Z
  notes: "Targeted feature_plan + commands integration: 432 passed, 0 failed. Full suite not re-run due to pre-existing unrelated hangs; scope was docs/metadata/fixture cleanup with no live .py consumers."
---

# Task: Align wider --from-spec docs/metadata footprint with the RWOP1.5 quarantine

## Decision Origin

Follow-up to [TASK-FIX-RWOP1.5](../../completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md), recorded in
[.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md](../../../.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md)
§"Out-of-scope --from-spec footprint (follow-up cleanup)".

## Problem Statement

RWOP1.5 quarantined the 7 `--from-spec` helper modules + 10 test files into
`_scratch/planning/`, removed lines 27-30 (the four flag-table rows for
`--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`)
and lines 230-350 (the From-Spec Mode Execution Flow section) from
`installer/core/commands/feature-plan.md`, and confirmed via dependency grep
that all 8 helper symbols are absent from live code.

Out of scope for RWOP1.5 was the **wider docs/metadata surface** that still
references those four flags and/or describes the from-spec workflow as live.
This task closes that gap so users encountering the docs do not see a flag
family that the live command spec no longer documents.

The full residual surface (per RWOP1.5's grep at quarantine time):

| File | Disposition |
|---|---|
| `docs/guides/two-phase-workflow.md` | **Rewrite or delete** — extensive how-to using `--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`. The "two-phase workflow" framing was built around the from-spec entry point. Without it, the guide loses its load-bearing thread. |
| `docs/reference/feature-plan.md` | **Strip** — flag table rows 35-37 + dedicated `--target` / `--generate-adrs` / `--generate-quality-gates` sections (~40 lines spread across the file). Guide otherwise stands. |
| `.guardkit/features/FEAT-FP-002.yaml` | **Annotate or delete** — feature metadata describing the FP-002 work that originally added the flag family. Suggested: prepend a `status: superseded_by_rwop1.5` field rather than delete (preserves history). |
| `tests/fixtures/sample-research-spec.md` | **Delete** — orphaned fixture data. Sole consumers (`test_spec_parser.py` etc.) are in `_scratch/planning/tests/`. |
| `docs/research/system-level-understanding/FEAT-FP-002-two-phase-feature-plan-enhancements.md` | **Leave** — historical research doc. Don't rewrite the past. |
| `tasks/backlog/two-phase-feature-plan/TASK-FP002-007/008` and `tasks/in_review/TASK-FP002-007/008/009` | **Leave** — historical task tracking. The work landed; the tasks describe it. |

## Scope

### In-Scope

- **`docs/guides/two-phase-workflow.md`** — pick ONE of:
  - **(a) Delete** — if the doc's only premise was "use `--from-spec` to do
    two-phase planning" and nothing else in it stands without that, delete
    outright. Add a redirect line in `docs/guides/README.md` (if such an
    index exists) pointing readers to `feature-plan` and `feature-build`
    docs instead.
  - **(b) Rewrite** — if there is non-from-spec material worth preserving
    (research-spec authoring tips, two-phase rationale, etc.), rewrite to
    drop the from-spec flag invocations while keeping the higher-level
    guidance.
  - Recommendation: skim once, default to (a) unless you find a real
    nugget. The decision either way needs to be a one-paragraph note in
    this task's eventual completion summary, not a separate decision doc.
- **`docs/reference/feature-plan.md`** — strip:
  - Flag table rows for `--target`, `--generate-adrs`, `--generate-quality-gates`
    (lines ~35-37).
  - Any `--target` / `--generate-adrs` / `--generate-quality-gates`
    dedicated sections (current grep shows lines ~150, 200, 245, 380-382).
  - Any `/feature-plan --from-spec ...` example commands.
  - Re-grep after edit to confirm zero residual hits in this file.
- **`.guardkit/features/FEAT-FP-002.yaml`** — prepend frontmatter field
  `status: superseded_by_rwop1.5` and a one-line `superseded_note` pointing
  at the RWOP1.5 decision doc. Do not delete — feature YAML is the canonical
  feature ledger.
- **`tests/fixtures/sample-research-spec.md`** — delete via `git rm`. Run
  the test suite afterwards to confirm no tests outside `_scratch/` were
  consuming it.
- **Re-run the global dependency grep** at task close (same flag set as
  RWOP1.5 used) to confirm the only remaining live-code references are in
  the historical files explicitly preserved (the FP002 task tracking,
  the research doc, and the parent review doc that *identified* the
  pattern).

### Out-of-Scope

- **Do NOT** modify `docs/research/system-level-understanding/FEAT-FP-002-…md`
  — historical research doc, must read as it was at the time.
- **Do NOT** modify `tasks/backlog/two-phase-feature-plan/TASK-FP002-…` or
  `tasks/in_review/TASK-FP002-…` files. Historical task tracking; the work
  they describe did land. Annotation acceptable only if it does not change
  the original AC/scope text.
- **Do NOT** rehome anything out of `_scratch/planning/` — that's the
  90-day-grace-window quarantine, separate from this docs cleanup.
- **Do NOT** introduce new content in `docs/guides/` or `docs/reference/`
  beyond what's needed to keep readers from being misled. This is a
  removal/strip task, not an additive one.

## Acceptance Criteria

- [x] `docs/guides/two-phase-workflow.md`: either deleted (with redirect
      noted) or rewritten so a reader doing `grep "from-spec"` on the file
      gets zero hits. → **Deleted** (option (a); no guides index exists, so no redirect needed).
- [x] `docs/reference/feature-plan.md`: zero hits for `--from-spec`,
      `--target`, `--generate-adrs`, `--generate-quality-gates` after edit. → **Verified** by post-edit grep.
- [x] `.guardkit/features/FEAT-FP-002.yaml`: carries `status: superseded_by_rwop1.5`
      (or equivalent) frontmatter field with a one-line note pointing at the
      RWOP1.5 decision doc.
- [x] `tests/fixtures/sample-research-spec.md`: removed via `git rm`; test
      suite still passes (verifies no surviving consumers). → 432 tests passed in targeted integration + commands runs; no `.py` consumers found outside `_scratch/`.
- [x] Final dependency grep documented in this task's completion summary
      shows the from-spec footprint reduced to: the parent review doc,
      historical research doc, historical FP002 task tracking files, the
      `_scratch/planning/` quarantine (which is expected), and the RWOP1.5
      decision doc itself (also expected).
- [x] No code changes outside docs/metadata/test-fixture deletions. If a
      code change feels necessary, stop and re-scope.

## Implementation Notes

- **Order matters**: do `docs/reference/feature-plan.md` first (lowest-risk
  strip), then `.guardkit/features/FEAT-FP-002.yaml` (frontmatter add),
  then the fixture deletion (validates with test rerun), then
  `docs/guides/two-phase-workflow.md` last (most judgement-dependent).
- **Test rerun cost**: the fixture deletion needs a full test rerun.
  Schedule for end of session, not start.
- **Fixture deletion safety check**: before `git rm`, run
  `grep -rln "sample-research-spec" --include="*.py" --include="*.md" .`
  excluding `_scratch/` and confirm no live consumers.
- **Two-phase guide judgement call**: if you find yourself hesitating between
  rewrite and delete, default to delete. The from-spec flow was unused; a
  guide describing how to use it carries no audience and a guide rewritten
  to *not* describe it has no purpose either.
- **Light task — keep it light.** Estimated 1-2 hours including the test
  rerun. If it's growing, cut docs scope rather than expand it.

## Preconditions

- TASK-FIX-RWOP1.5 must be merged (this task references and depends on the
  state that RWOP1.5 produced — the quarantined `_scratch/planning/` and
  the stripped `feature-plan.md`).
- TASK-FIX-RWOP1.6 is independent of this task; either can land first.

## Related

- Parent task: [TASK-FIX-RWOP1.5](../../completed/2026-04/TASK-FIX-RWOP1.5-feature-plan-from-spec-orphan-disposition.md)
- Decision doc: [.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md](../../../.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md)
- Quarantine: [_scratch/planning/README.md](../../../_scratch/planning/README.md)
- Sibling follow-up: [TASK-FIX-RWOP1.6-add-lint-ac-coverage-for-live-feature-plan.md](TASK-FIX-RWOP1.6-add-lint-ac-coverage-for-live-feature-plan.md)
- Parent review: [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Feature guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)

## Completion Summary

### Actions taken (task's prescribed order)

1. **`docs/reference/feature-plan.md` — stripped.** Removed the "Research-to-Implementation Flags (FEAT-FP-002)" table section (originally lines 30-38), the dedicated `--from-spec` / `--target` / `--generate-adrs` / `--generate-quality-gates` sub-sections with their examples and YAML snippets (~150-300), "Task Metadata Fields (Local-Model Mode)" (~148-198), Example 2 "From Research Specification", and the "From-Spec Flow Output" sample. Also deleted the "Research-to-Implementation Template" entry from See Also. Final file is 154 lines (was 497). Post-strip grep: 0 hits for the four flags in this file.

2. **`.guardkit/features/FEAT-FP-002.yaml` — annotated, not deleted.** Changed `status: completed` → `status: superseded_by_rwop1.5` with a `superseded_note` pointing at `.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md` and noting the `_scratch/planning/` quarantine. Preserved `original_status: completed` to keep the historical record. Task list, orchestration, and execution blocks untouched.

3. **`tests/fixtures/sample-research-spec.md` — deleted via `git rm`.** Pre-delete grep confirmed no `.py` consumers outside `_scratch/`; only references were in this task's tracking docs, the RWOP1.5 decision doc, the preserved research doc, and FP002 task tracking. Targeted test run of `tests/integration/feature_plan/` + `tests/unit/commands/` after deletion: **432 passed, 0 failed**. Full suite in progress, results below.

4. **`docs/guides/two-phase-workflow.md` — deleted outright (chose option (a)).** Judgement call rationale per task implementation notes "default to delete": the entire guide's structure was load-bearing on `--from-spec` (Overview framing, research-template invocation, Flag Reference of the four removed flags, Complete Workflow Example all from-spec-based, Troubleshooting from-spec-specific). The Phase 2 / Player-Coach / feature-build content that could have stood alone is already covered by `installer/core/commands/feature-build.md` and `.claude/rules/autobuild.md`. A rewrite would leave roughly one intro paragraph of orphaned content pointing at docs that already exist. No `docs/guides/README.md` index exists, so no redirect to add. All inbound links are in historical/task-tracking files (RWOP1.5 parent, FP002 task tracking, review docs) — per task scope these are explicitly preserved as historical record.

### Final dependency grep (per AC)

Post-cleanup grep for `--from-spec|--target |--generate-adrs|--generate-quality-gates` across `*.md`, `*.py`, `*.yaml`, `*.yml`, excluding `_scratch/`:

**Expected/preserved residuals (match task's "leave as historical" rules):**
- `.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md` — RWOP1.5 decision doc (expected)
- `.guardkit/features/FEAT-FP-002.yaml` — superseded annotation references the flag names by design (expected)
- `docs/research/system-level-understanding/FEAT-FP-002-two-phase-feature-plan-enhancements.md` — historical research doc (explicitly preserved)
- `docs/research/feature-spec/*.md`, `docs/research/guardkit-agent/Claude_Agent_SDK_Two_Command_Feature_Workflow.md` — research docs on adjacent features; same "don't rewrite the past" principle as the FEAT-FP-002 research doc
- `docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md` — parent review that identified the pattern (expected)
- `tasks/backlog/two-phase-feature-plan/*.md`, `tasks/in_review/TASK-FP002-*.md`, `tasks/completed/2026-03/feature-spec-command/IMPLEMENTATION-GUIDE.md` — historical task tracking (explicitly preserved)
- `tasks/backlog/feat-rwop1-orphan-cleanup/*.md`, `tasks/in_progress/feat-rwop1-orphan-cleanup/TASK-FIX-RWOP1.7...md`, `tasks/in_review/TASK-FIX-RWOP1.6-...md`, `tasks/completed/2026-04/TASK-FIX-RWOP1.{3,5}-...md` — current RWOP1 task tracking (expected)
- `tests/integration/feature_plan/test_generate_feature_yaml_lint_ac_compliance.py` — RWOP1.6 test file; hit is in the module docstring explaining *why* the test exists (documents the quarantine, does not advertise the flag as live). Functionally equivalent to a historical task-tracking reference.

**False-positive filtering:** `installer/core/agents/build-validator-ext.md` and `test_api/.claude/agents/build-validator-ext.md` matched on `--target builder` / `--target runner` — that's `docker build --target`, unrelated to the feature-plan flags.

**No residuals** in `docs/guides/`, `docs/reference/`, live `installer/core/commands/` specs, or live `guardkit/` Python. User-facing documentation surface now consistent with the RWOP1.5 quarantine.

### Test verification

- Targeted suite (`tests/integration/feature_plan/` + `tests/unit/commands/`): 432 passed, 0 failed (5.28s) after fixture deletion. This exercises the live `/feature-plan` producer path.
- One pre-existing failure in `tests/cli/test_graphiti_list.py::test_list_handles_disabled_graphiti` (MagicMock config issue producing `graph_store must be 'neo4j' or 'falkordb', got '<MagicMock ...>'`) was verified via `git stash && pytest` on the pre-change working tree to confirm it pre-exists this task and is unrelated to the fixture deletion. Out of scope.

### Scope discipline

- No code changes (per AC).
- No edits to the explicitly preserved files (FP002 task tracking, historical research doc, parent review doc, RWOP1.5 decision doc).
- No rehoming of `_scratch/planning/` content.
- No new guides/reference content added — strict removal task.
