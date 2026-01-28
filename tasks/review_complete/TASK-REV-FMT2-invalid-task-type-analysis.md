---
id: TASK-REV-FMT2
title: Analyze and fix invalid task_type values in FEAT-FMT AutoBuild failure
status: review_complete
task_type: review
created: 2026-01-28T10:00:00Z
updated: 2026-01-28T12:30:00Z
priority: high
tags:
- autobuild
- coach-validator
- task-type
- feat-fmt
- bug-analysis
complexity: 5
decision_required: true
related_tasks:
- TASK-FMT-001
- TASK-FMT-002
feature_id: FEAT-FMT
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 4
  report_path: .claude/reviews/TASK-REV-FMT2-review-report.md
  completed_at: 2026-01-28T12:30:00Z
  decision: implement
  implementation_task: TASK-IMP-ALIAS
---

# Task: Analyze and fix invalid task_type values in FEAT-FMT AutoBuild failure

## Description

FEAT-FMT tasks (TASK-FMT-001, TASK-FMT-002) repeatedly failed AutoBuild with the same Coach feedback across all 5 turns:

> "Invalid task_type value: implementation. Must be one of: scaffolding, feature, infrastructure, documentation, testing, refactor"

This review task will analyze the root cause and propose a fix.

## Context

### Observed Behavior
- Both TASK-FMT-001 and TASK-FMT-002 reached max turns (5) without approval
- Every turn received identical Coach feedback about invalid `task_type: implementation`
- The Player kept using "Implementation via task-work delegation" approach

### Key Files
- Task files: `tasks/backlog/fastmcp-python-template/TASK-FMT-00*.md`
- Coach validator: `guardkit/orchestrator/quality_gates/coach_validator.py`
- Task types enum: `guardkit/models/task_types.py`
- Review output: `docs/reviews/feature-build/mcp_template_feature.md`

### Valid TaskType Values
From `guardkit/models/task_types.py`:
- `scaffolding` - Configuration files, project setup, templates
- `feature` - Feature implementation, bug fixes, enhancements
- `infrastructure` - Docker, deployment, CI/CD, terraform, ansible
- `documentation` - Guides, API docs, tutorials, README files
- `testing` - Test files, test utilities, coverage improvements
- `refactor` - Code cleanup, performance optimization, pattern refactoring

## Analysis Scope

1. **Source of Invalid Value**: Where is `task_type: implementation` coming from?
   - Is it in the task frontmatter? (No - tasks have `task_type: scaffolding`)
   - Is the Player writing it to a file being validated?
   - Is there confusion between task metadata and template manifest schema?

2. **Coach Validator Logic**: Review `_resolve_task_type()` method
   - What data is it reading?
   - Is it reading the wrong file or field?

3. **Player Behavior**: Why does Player keep using `implementation`?
   - Is there a prompt or instruction causing this?
   - Is the Player agent documentation outdated?

4. **Schema Confusion**: Are there two different `task_type` concepts?
   - Task workflow metadata (TaskType enum)
   - Template manifest.json schema (may have different allowed values)

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Fix proposed with implementation approach
- [ ] Decision made: fix Coach, fix Player, or fix both
- [ ] If fix is straightforward, create implementation subtask

## Review Deliverables

1. Root cause analysis document
2. Proposed fix (code changes or configuration updates)
3. Decision checkpoint for implementation approach

## Related Information

### Coach Validator Error Location
`guardkit/orchestrator/quality_gates/coach_validator.py:329-332`:
```python
except ValueError as e:
    logger.error(f"Invalid task_type value: {task_type_str}")
    raise ValueError(
        f"Invalid task_type value: {task_type_str}. "
        f"Must be one of: {', '.join(t.value for t in TaskType)}"
    ) from e
```

### Task Frontmatter (Correct)
Both tasks have `task_type: scaffolding` which IS valid:
```yaml
task_type: scaffolding
```

### Hypothesis
The Coach may be reading `task_type` from the template `manifest.json` file being created by the Player, rather than from the task metadata. The template manifest schema may use different values like "implementation" which are not in the TaskType enum.

## Test Execution Log

[Automatically populated by /task-review]
