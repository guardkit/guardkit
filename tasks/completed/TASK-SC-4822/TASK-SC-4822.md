---
id: TASK-SC-4822
title: "E2E verify system commands chain after Graphiti population"
status: completed
created: 2026-02-14T00:00:00Z
updated: 2026-02-14T12:00:00Z
completed: 2026-02-14T12:30:00Z
completed_location: tasks/completed/TASK-SC-4822/
priority: high
tags: [system-overview, impact-analysis, context-switch, e2e, verification]
complexity: 4
feature_id: FEAT-SC-001
depends_on: [TASK-REV-SP-IMPL]
task_type: standard
organized_files: [TASK-SC-4822.md]
---

# Task: E2E Verify System Commands Chain After Graphiti Population

## Description

Verify that the three read commands (`/system-overview`, `/impact-analysis`, `/context-switch`) work end-to-end against real Graphiti data after the `/system-plan` stub is replaced. The code exists and has unit tests — this task confirms the full chain: `/system-plan` writes -> Graphiti stores -> read commands retrieve and format correctly.

## Acceptance Criteria

- [x] AC-001: `/system-overview` returns structured output with >0 components when Graphiti has architecture data
- [x] AC-002: `/system-overview --format json` returns valid JSON with `status: "ok"`
- [x] AC-003: `/impact-analysis "knowledge layer"` returns non-empty component list with risk score
- [x] AC-004: `/impact-analysis` task ID enrichment extracts title from task frontmatter
- [x] AC-005: `/context-switch guardkit` updates `.guardkit/config.yaml` and displays orientation
- [x] AC-006: `condense_for_injection()` output is within token budget (verify with heuristic)
- [x] AC-007: Coach context builder produces non-empty architecture context for complexity >= 7 tasks
- [x] AC-008: Integration test file exists with >= 5 test cases covering the chain
- [x] AC-009: Any bugs found are fixed and documented in task notes

## Files to Verify (read-only review)

- `guardkit/planning/system_overview.py` — Verified, no bugs
- `guardkit/planning/impact_analysis.py` — Fixed 2 bugs (BUG-4, BUG-5)
- `guardkit/planning/context_switch.py` — Verified, no bugs
- `guardkit/planning/coach_context_builder.py` — Fixed 1 bug (BUG-3)
- `guardkit/cli/system_context.py` — Fixed 2 bugs (BUG-1, BUG-2)

## Files Created/Modified

- `tests/integration/test_system_commands_e2e.py` — 24 integration tests, all passing
- `guardkit/cli/system_context.py` — Fixed CLI wiring (BUG-1, BUG-2)
- `guardkit/planning/coach_context_builder.py` — Fixed argument passing (BUG-3)
- `guardkit/planning/impact_analysis.py` — Fixed query enrichment (BUG-4, BUG-5)

## Test Results

- 24 new E2E tests: ALL PASSING
- 36 existing integration tests: ALL PASSING (zero regressions)
- 318 planning unit tests: ALL PASSING (zero regressions)

## Bugs Found and Fixed (AC-009)

### BUG-1: system_overview CLI missing async wiring and sp argument
**File**: `guardkit/cli/system_context.py:387-396`
**Symptom**: `system_overview` Click command called `get_system_overview(verbose=verbose)` directly, but the function is `async def get_system_overview(sp: SystemPlanGraphiti, verbose: bool)` — missing the required `sp` parameter and not using `asyncio.run()`.
**Fix**: Added `_get_graphiti_client()` and `_detect_project_id()` helper functions. Command now creates `SystemPlanGraphiti(client, project_id)` and wraps call in `asyncio.run()`.

### BUG-2: impact_analysis CLI missing async wiring, sp and client arguments
**File**: `guardkit/cli/system_context.py:441-466`
**Symptom**: `impact_analysis` Click command called `run_impact_analysis(task_or_topic=..., depth=...)` but the function signature requires `sp`, `client` as first two positional args, and is async.
**Fix**: Same pattern as BUG-1 — creates `sp` and `client`, wraps in `asyncio.run()`.

### BUG-3: coach_context_builder passes query string as client argument
**File**: `guardkit/planning/coach_context_builder.py:179-184`
**Symptom**: `_get_impact_section` called `run_impact_analysis(sp, query)` — the `query` string was passed as the `client` positional parameter, not `task_or_topic`.
**Fix**: Changed to `run_impact_analysis(sp=sp, client=sp._client, task_or_topic=query, depth="quick")`.

### BUG-4: Tag extraction regex only handles multi-line YAML format
**File**: `guardkit/planning/impact_analysis.py:231-252`
**Symptom**: `_build_query()` tag extraction used `r"tags:\s*\n((?:\s+-.*\n)*)"` which only matches multi-line YAML format (`tags:\n  - tag1\n  - tag2`), but GuardKit task files use inline format (`tags: [tag1, tag2]`).
**Fix**: Added inline tag detection first: `re.search(r"tags:\s*\[([^\]]*)\]", frontmatter)` with fallback to multi-line format.

### BUG-5: Task file search uses exact filename, misses descriptive suffixes
**File**: `guardkit/planning/impact_analysis.py:204-213`
**Symptom**: `_build_query()` used `Path(task_dir) / f"{task_or_topic}.md"` for exact match, but actual task files have descriptive suffixes (e.g., `TASK-SC-4822-e2e-verify-system-commands.md`).
**Fix**: Changed to `task_dir_path.glob(f"{task_or_topic}*.md")` to match descriptive filenames. Also added title quote stripping for quoted YAML values.

## Implementation Notes

- Depends on stub replacement task completing first (Graphiti must have data)
- Key risk: format mismatch between what `system_plan.py` writes and what read modules expect
- `.guardkit/config.yaml` may need a `known_projects` entry for GuardKit
- Expected entities from `guardkit-system-spec.md`: 1 system context, 9 components, 7 cross-cutting concerns, 8 ADRs

## Source Spec

`docs/debugging/system-plan/SPEC-e2e-verify-system-commands.md`
