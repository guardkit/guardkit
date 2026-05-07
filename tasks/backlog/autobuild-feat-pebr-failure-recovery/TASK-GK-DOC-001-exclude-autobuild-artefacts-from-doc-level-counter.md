---
id: TASK-GK-DOC-001
title: Exclude autobuild artefacts from documentation-level file-count constraint
status: backlog
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 00:00:00+00:00
priority: low
priority_band: P2
task_type: refactor
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: direct
wave: 2
complexity: 2
estimated_minutes: 45
dependencies:
  - TASK-GK-AC-001
tags:
  - autobuild
  - documentation-level
  - false-positive-warning
  - P2
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Exclude autobuild artefacts from documentation-level file-count constraint

## Description

`AgentInvoker._validate_file_count_constraint`
([guardkit/orchestrator/agent_invoker.py:6598-6649](../../../guardkit/orchestrator/agent_invoker.py#L6598-L6649))
counts every entry in `files_created` against the per-doc-level limit
(2 for `minimal`/`standard`, no limit for `comprehensive`). The
`files_created` list is built at
[agent_invoker.py:6358](../../../guardkit/orchestrator/agent_invoker.py#L6358)
from the Player's report, which includes orchestrator bookkeeping
files like `.guardkit/autobuild/{task_id}/player_turn_1.json`,
`.guardkit/bdd/*.xml`, `.claude/task-plans/*.md`, and empty
`__init__.py` package markers.

In the FEAT-PEBR turn-1 run this produced the false warning:
*"Documentation level constraint violated: created 4 files, max
allowed 2 for minimal level. Files: ['player_turn_1.json',
'src/forge/pipeline/build_ack_handle.py',
'tests/forge/adapters/nats/__init__.py',
'tests/forge/adapters/nats/test_pipeline_consumer.py']"*

The actual new-code count is 2 (one impl, one test) — within budget.
The warning is purely cosmetic but pollutes the live log and risks
desensitising operators to real scope-creep signals.

## Acceptance Criteria

- [ ] AC-1: `_validate_file_count_constraint` (or its caller at
  `agent_invoker.py:6358`) excludes paths matching any of:
  - `.guardkit/autobuild/**`
  - `.guardkit/bdd/**`
  - `.claude/task-plans/**`
  - `**/__init__.py`
  before counting.
- [ ] AC-2: With the FEAT-PEBR turn-1 fixture (4 files in
  `files_created` per the run log), the counter sees 2 files and
  does NOT emit the warning.
- [ ] AC-3: The exclusion list is centralised in a module-level
  constant (e.g. `_DOC_LEVEL_EXCLUDED_PATTERNS`) so future tweaks
  don't require touching the validation function.
- [ ] AC-4: Real new-code creations (under `src/`, `lib/`, `tests/`,
  `installer/`, etc.) continue to count as before.
- [ ] AC-5: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test: `files_created` containing only autobuild artefacts →
  no warning.
- Unit test: `files_created` containing 3 real source files →
  warning fires for `minimal` level (current behaviour).
- Unit test: `files_created` mixed (artefacts + real) → counter
  sees only the real count.

## Implementation notes

### Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — `_validate_file_count_constraint`
  (lines 6598-6649) and the caller around line 6358 / 6422
- `tests/orchestrator/test_agent_invoker.py` — three new test cases

### Recommended approach

Add a filter helper:

```python
_DOC_LEVEL_EXCLUDED_PATTERNS = (
    ".guardkit/autobuild/",
    ".guardkit/bdd/",
    ".claude/task-plans/",
)

def _is_doc_level_excluded(path: str) -> bool:
    return (
        any(path.startswith(p) or f"/{p}" in path
            for p in _DOC_LEVEL_EXCLUDED_PATTERNS)
        or path.endswith("/__init__.py")
        or path == "__init__.py"
    )
```

Then in `_validate_file_count_constraint`:

```python
files_for_count = [f for f in files_created if not _is_doc_level_excluded(f)]
actual_count = len(files_for_count)
```

Implementation mode is `direct` (no full task-work loop) because the
change is mechanical and the test surface is small.

### Dependency on TASK-GK-AC-001

Listed as a dependency because both touch `agent_invoker.py`. Land
GK-AC first (P0), then this. The merge surface is small but disjoint
(scanner is around line 6028; counter is around line 6598).

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/orchestrator/test_agent_invoker.py -x -v -k file_count
ruff check guardkit/orchestrator/agent_invoker.py
```

## Out of scope

- Changing the per-level file limits themselves (still 2 / 2 / None).
- Adding a `documentation_level: comprehensive` declaration to forge
  task frontmatter (that's TASK-FRR-PEB-FM-001's territory).
