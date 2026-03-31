---
id: TASK-REV-4219
title: Analyse Graphiti unavailable during /system-arch session
status: review_complete
task_type: review
review_mode: decision
review_depth: standard
created: 2026-03-17T00:00:00Z
updated: 2026-03-17T12:00:00Z
priority: medium
tags: [graphiti, installer, system-arch, environment, review]
complexity: 4
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-4219-review-report.md
  completed_at: 2026-03-17T12:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse Graphiti unavailable during /system-arch session

## Description

Review and analyse the incident documented in `docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md`.

During a `/system-arch` session on the agentic-dataset-factory project, Graphiti was reported as unavailable despite all infrastructure (FalkorDB, vLLM LLM server, vLLM embedding server) being healthy. The root cause is that `graphiti-core` is not installed in the system Python used by the `graphiti-check` script. A secondary issue is that the symlink target lacks execute permission.

The review should evaluate the four proposed fix options and recommend the best path forward for the GuardKit installer.

## Review Scope

- Analyse root cause: `graphiti_check.py` shebang resolves to system Python which lacks `graphiti-core`
- Evaluate secondary issue: symlink execute permission on `graphiti_check.py`
- Assess the four fix options (A: fix shebang, B: wrapper script, C: system pip install, D: Claude Code config)
- Consider impact on existing installations and upgrade path
- Recommend implementation approach with acceptance criteria

## Source Document

`docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md`

## Acceptance Criteria

- [ ] Root cause confirmed and documented
- [ ] All fix options evaluated with trade-offs
- [ ] Recommended fix selected with justification
- [ ] Impact on existing installations assessed
- [ ] Retroactive seeding approach confirmed
- [ ] Implementation task(s) identified for the chosen fix

## Implementation Notes

Review completed 2026-03-17. Recommended fix: Option B (wrapper script) combined with command spec updates.

### Implementation Tasks Created

Feature folder: `tasks/backlog/graphiti-check-env-fix/`

| Task | Title | Wave | Priority |
|------|-------|------|----------|
| TASK-FIX-GC01 | Wrapper script + chmod | 1 | P0/P1 |
| TASK-FIX-GC02 | Update command specs | 1 | P1 |
| TASK-FIX-GC03 | Harden installer graphiti-core install | 2 | P2 |

### Post-fix Action
Retroactively seed agentic-dataset-factory: `guardkit graphiti seed --force`

See full report: `.claude/reviews/TASK-REV-4219-review-report.md`

## Test Execution Log

[Automatically populated by /task-work]
