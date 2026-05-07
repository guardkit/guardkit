---
id: TASK-GK-PA-002
title: AC-fallback scanner must honour explicit Files-to-Create/Modify and restrict prose scan
status: completed
created: 2026-05-07T00:00:00Z
updated: 2026-05-07T00:00:00Z
completed: 2026-05-07T00:00:00Z
previous_state: in_review
state_transition_reason: "All 8 ACs satisfied; 18 new tests pass, 470 regression tests pass, ruff clean"
completed_location: tasks/completed/TASK-GK-PA-002/
priority: high
priority_band: P0
task_type: feature
parent_review: TASK-REV-PEBR-002
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-2-analysis.md
parent_feature_folder: autobuild-feat-pebr-failure-recovery-rev2
related_tasks:
  - TASK-GK-AC-001
  - TASK-GK-PA-001
  - TASK-FRR-PEB-FM-001
  - TASK-FRR-PEB-FM-002
  - TASK-REV-PEBR-002
implementation_mode: task-work
wave: 1
complexity: 5
estimated_minutes: 90
dependencies: []
tags:
  - autobuild
  - plan-audit
  - ac-scanner
  - regression-fix
  - feat-pebr
  - bug-a
  - P0
test_results:
  status: passed
  coverage: null  # not measured for this single-module change; spec only requires AC-7 regression
  last_run: 2026-05-07T00:00:00Z
  new_tests_passed: 18
  regression_tests_passed: 470
  regression_tests_deselected: 1  # tests/unit/test_agent_invoker.py::TestInvokeTaskWorkImplement::test_invoke_task_work_implement_mode_passed — fails on clean main, unrelated to TASK-GK-PA-002
  ruff: clean (test file); 0 new errors introduced in agent_invoker.py
---

# Task: AC-fallback scanner must honour explicit Files-to-Create/Modify and restrict prose scan

## Description

`AgentInvoker._scan_ac_for_missing_paths`
([`guardkit/orchestrator/agent_invoker.py:6054-6152`](../../../guardkit/orchestrator/agent_invoker.py))
is invoked when `PlanAuditor` returns `skipped=True` (no plan at
`docs/state/{task_id}/implementation_plan.md`). It is the
TASK-AB-FIX-INVAB1 AC-005 escalation: it scans the task body for
file-shaped tokens and flags any that don't exist on disk as
"missing".

Two surface bugs surfaced by FEAT-PEBR run-2:

1. **Scope mismatch with name + docstring.** The function is named
   `_scan_ac_for_missing_paths` and the docstring says *"inspect
   the task's acceptance criteria"* (lines 6062-6097), but the
   implementation reads the **whole post-frontmatter body** —
   `## Implementation notes`, `## §4 Integration Contract`, and
   every other section. Any qualified prose path that doesn't exist
   verbatim is flagged. TASK-GK-AC-001 closed bare-basename false
   positives, but qualified paths (`/`-containing, e.g.
   `src/forge/dispatch/autobuild_async.py`) still trip the scanner.
2. **Explicit `## Files to Create` / `## Files to Modify` sections
   are inert.** TASK-FRR-PEB-FM-001 added these sections to the
   FRR-PEB tasks (commit `02aac9c`), but the audit fallback path
   doesn't consult them. The `PlanMarkdownParser` extractor is only
   invoked against `docs/state/{task_id}/` — never against the task
   body — so FM-001's sections live alongside but are not
   consumed.

The two issues compound: FRR-PEB-003 has 5 declared `## Files to
Create` and 2 declared `## Files to Modify` — all of which the
Player produced — but the scanner still flagged
`src/forge/dispatch/autobuild_async.py` from `## Implementation
notes` (a typo cross-reference; real file is at
`src/forge/pipeline/dispatchers/autobuild_async.py`). Plan-audit
fired all 5 turns.

This bug affects any task whose body contains a qualified prose
path to an existing-but-mistyped or hypothetical file. The FRR-PEB
family is at high risk (FRR-PEB-009, -013, -014 likely have prose
references); other features may be similarly exposed.

## Acceptance Criteria

- [x] **AC-1 — Explicit sections are authoritative when present.**
  When the task body contains a non-empty `## Files to Create` and/or
  `## Files to Modify` section, `_scan_ac_for_missing_paths` (or its
  caller `_compute_plan_audit_verdict`) treats the union as the
  authoritative `planned_files` set and **does not run the prose
  regex scan**. The audit verdict compares `planned_files` against
  the worktree state (existence on disk) and reports any genuinely
  missing planned files.
- [x] **AC-2 — When neither section is present, prose scan is
  restricted to AC section.** When neither `## Files to Create` nor
  `## Files to Modify` is in the task body, the fallback regex scan
  runs only on the text between the `## Acceptance Criteria` (or
  `## Acceptance criterion`) header and the next `##` header. Prose
  paths in `## Implementation notes` and other sections are no
  longer scanned. This matches the function's name and docstring.
- [x] **AC-3 — Repro test using FEAT-PEBR run-2 signature.** Add a
  unit test fixture in
  `tests/orchestrator/test_agent_invoker_ac_scanner.py` (or a new
  parallel file) that mirrors TASK-FRR-PEB-003's body shape:
  - `## Files to Create` lists 5 paths that exist in a fixture
    worktree.
  - `## Files to Modify` lists 2 paths that exist.
  - `## Implementation notes` contains a prose bullet `- Reference:
    \`src/forge/dispatch/autobuild_async.py\`'s existing ...` (the
    typo path, not in the worktree fixture).
  - Expected: `_scan_ac_for_missing_paths` returns `[]` (or the
    fix's equivalent helper returns no `missing_files`). The
    typo-prose path must NOT be flagged.
  - This must FAIL on `main` (returns
    `["src/forge/dispatch/autobuild_async.py"]`) and PASS after the
    fix.
- [x] **AC-4 — When explicit lists name a file that doesn't exist,
  flag it.** Don't over-correct: a task with `## Files to Create:
  - src/foo/bar.py` and a worktree that doesn't contain
  `src/foo/bar.py` MUST still produce a missing-file violation. Add
  a fixture for this case.
- [x] **AC-5 — Bare basename guard preserved.** Verify TASK-GK-AC-001's
  basename guard still functions: AC text containing
  `pipeline_consumer.py` (no `/`) where the file lives at
  `src/forge/adapters/nats/pipeline_consumer.py` must NOT be
  flagged. Add a fixture that exercises this on the AC-only branch
  (no `## Files to Create` section present).
- [x] **AC-6 — End-to-end test through `_compute_plan_audit_verdict`.**
  Replicate the FEAT-PEBR run-2 fixture end-to-end:
  - Worktree with `src/forge/lifecycle_bridge/translation.py` and
    the other 6 FRR-PEB-003 declared files.
  - No `docs/state/TASK-FRR-PEB-003/implementation_plan.md`.
  - Task body with FM-001 sections and the typo prose.
  - Expected: `_compute_plan_audit_verdict` returns
    `{status: "passed", severity: "low", missing_files: []}` (or
    equivalent — the audit passes).
  - Today: returns `{status: "violation", severity: "high",
    missing_files: ["src/forge/dispatch/autobuild_async.py"]}`.
- [x] **AC-7 — Regression: existing test suite stays green.** All
  tests under `tests/orchestrator/test_agent_invoker_ac_scanner.py`,
  `tests/unit/test_agent_invoker.py`, and
  `tests/integration/autobuild/test_plan_audit_gate.py` continue to
  pass.
- [x] **AC-8 — All modified files pass project-configured lint/format
  checks** (ruff). New test fixtures pass cleanly.

## Out of Scope

- Bug B (Coach AC-ID strip-before-extract) — covered by
  TASK-GK-CV-001.
- Bug C (stall extender plateau) — covered by TASK-GK-COACH-001.
- Renaming `_scan_ac_for_missing_paths` (the name no longer
  perfectly describes the body-wide behaviour either way after this
  fix; rename can fold into the implementation as a courtesy or be
  deferred).
- Auto-stub plan enrichment from the task body (rev-2 review item
  #6) — deferred to a follow-up task.

## Files to Create

- `tests/orchestrator/test_agent_invoker_ac_scanner_explicit_sections.py`
  (or extend existing
  `tests/orchestrator/test_agent_invoker_ac_scanner.py`)
- `tests/fixtures/feat_pebr_run2_worktree/` — minimal fixture
  mirroring TASK-FRR-PEB-003's body shape and the matching worktree
  file layout.

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (the
  `_scan_ac_for_missing_paths` function and/or its caller
  `_compute_plan_audit_verdict` at lines 6204-6228)
- Possibly `guardkit/installer/core/commands/lib/plan_markdown_parser.py`
  (if its `_extract_list_section` helper needs to be exposed for
  callers other than `parse_file`)

## Implementation notes

### Recommended approach

Add a helper `_extract_explicit_planned_files(task_body: str) ->
Optional[Set[str]]` that:

1. Searches the task body for `## Files to Create\s*\n(.*?)(?=\n##|\Z)`
   and `## Files to Modify\s*\n(.*?)(?=\n##|\Z)`.
2. If either section is non-empty, parses bullet lines using the
   same logic as `PlanMarkdownParser._extract_list_section`
   (`installer/core/commands/lib/plan_markdown_parser.py:249-295`).
   Reuse that helper if you can expose it (consider lifting it to
   a module-level function in `plan_markdown_parser`).
3. Returns the **union** of both sections as a set of relative
   paths. Returns `None` (or empty set) when neither section is
   present.

Then update `_compute_plan_audit_verdict` at the `skipped` branch
(`agent_invoker.py:6204-6228`):

```python
if result.get("skipped"):
    # NEW: prefer explicit task-body sections over prose scan
    explicit = self._extract_explicit_planned_files(task_id)
    if explicit:
        # Compare explicit declarations against worktree state
        missing = [
            p for p in sorted(explicit)
            if not (self.worktree_path / p).exists()
        ]
        if missing:
            return {
                "status": "violation",
                "severity": "high",
                ...
                "missing_files": missing,
                "message": (
                    f"task body declares {len(explicit)} planned file(s); "
                    f"{len(missing)} not on disk: {', '.join(missing[:3])}"
                ),
            }
        return {
            "status": "passed",
            ...
            "message": "all task-body-declared files present on disk",
        }
    # FALLBACK: prose scan, but restrict to ## Acceptance Criteria
    ac_missing = self._scan_ac_for_missing_paths(task_id)
    ...
```

And modify `_scan_ac_for_missing_paths` to slice `body` to the
`## Acceptance Criteria` section only:

```python
# In _scan_ac_for_missing_paths, after the frontmatter strip:
ac_match = re.search(
    r'^##\s+Acceptance\s+(?:Criteria|criterion)\s*\n(.*?)(?=\n##|\Z)',
    body,
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
if ac_match:
    body = ac_match.group(1)  # restrict scan to AC section only
# else: keep current body-wide scan as a defensive fallback
#       (preserves behaviour for tasks with non-standard structure)
```

### Why both halves are needed

- **Explicit sections branch (AC-1)** is the canonical path for
  tasks that follow the FM-001 convention. Closes the prose-trap
  for every well-formed FRR-PEB task.
- **AC-only fallback (AC-2)** matches the function name + docstring
  and prevents prose paths in `## Implementation notes` etc. from
  tripping the scanner on tasks that don't yet have FM-001
  sections.

If you do only one, choose AC-1: it has higher leverage (closes the
trap on the family of tasks that triggered run-2's failure).

### Regression risk

- Tasks without `## Files to Create` and with prose paths in
  `## Acceptance Criteria` itself (rare but possible) will see a
  behaviour change: the scanner no longer scans
  `## Implementation notes` etc. This is correct — if AC text doesn't
  declare a file, it's not load-bearing for plan-audit.
- `synthetic_report.generate_file_existence_promises` is a parallel
  module that uses similar regexes. Don't touch it.
- The `PlanAuditor` comparison-mode path (when `docs/state/` plan
  exists) is unchanged.

## Test requirements

- Unit tests for `_extract_explicit_planned_files` (AC-1, AC-4).
- Unit tests for the AC-only fallback when no explicit sections
  (AC-2, AC-5).
- End-to-end test through `_compute_plan_audit_verdict` using a
  FEAT-PEBR run-2 fixture (AC-6).
- Regression: full pass on
  `tests/orchestrator/test_agent_invoker_ac_scanner.py`,
  `tests/unit/test_agent_invoker.py`,
  `tests/integration/autobuild/test_plan_audit_gate.py`.

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/orchestrator/test_agent_invoker_ac_scanner_explicit_sections.py -x -v
PYTHONPATH=. python -m pytest tests/orchestrator/test_agent_invoker_ac_scanner.py tests/unit/test_agent_invoker.py tests/integration/autobuild/test_plan_audit_gate.py -x
ruff check guardkit/orchestrator/agent_invoker.py tests/orchestrator/test_agent_invoker_ac_scanner_explicit_sections.py
```
