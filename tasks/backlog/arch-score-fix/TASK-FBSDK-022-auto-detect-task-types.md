---
id: TASK-FBSDK-022
title: Update feature-plan to auto-detect task types
status: backlog
created: 2025-01-21T16:30:00Z
updated: 2025-01-21T16:30:00Z
priority: medium
tags: [feature-plan, task-types, auto-detection]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 2
conductor_workspace: arch-score-fix-wave2-3
complexity: 4
depends_on: [TASK-FBSDK-020]
---

# Task: Update feature-plan to auto-detect task types

## Description

Enhance the `/feature-plan` command's subtask generation to automatically classify tasks by type based on their title, description, and content. This ensures newly created tasks have appropriate quality gate profiles without manual annotation.

## Acceptance Criteria

- [ ] Auto-detection logic classifies tasks into 4 types
- [ ] Classification based on title keywords and task content
- [ ] Generated task files include `task_type` in frontmatter
- [ ] Detection accuracy ≥90% for common patterns
- [ ] Manual override available if auto-detection is wrong
- [ ] Unit tests verify classification rules
- [ ] Integration test with sample feature plan

## Implementation Notes

### Detection Rules

```python
def detect_task_type(title: str, description: str = "") -> TaskType:
    """Auto-detect task type from title and description."""
    title_lower = title.lower()
    desc_lower = description.lower()

    # Scaffolding indicators
    scaffolding_keywords = [
        "setup", "structure", "pyproject", "package.json",
        "directory", "scaffold", "initialize", "init",
        "config", "configuration", ".env", "dotfile"
    ]
    if any(kw in title_lower for kw in scaffolding_keywords):
        return TaskType.SCAFFOLDING

    # Documentation indicators
    doc_keywords = [
        "readme", "documentation", "docs", "comment",
        "docstring", "changelog", "contributing"
    ]
    if any(kw in title_lower for kw in doc_keywords):
        return TaskType.DOCUMENTATION

    # Infrastructure indicators
    infra_keywords = [
        "ci", "cd", "pipeline", "deploy", "docker",
        "kubernetes", "terraform", "ansible", "github actions",
        "workflow", "build system"
    ]
    if any(kw in title_lower for kw in infra_keywords):
        return TaskType.INFRASTRUCTURE

    # Default to feature
    return TaskType.FEATURE
```

### File to Modify

`installer/core/lib/implement_orchestrator.py`

In the subtask generation phase, after extracting subtask titles:

```python
for subtask in subtasks:
    task_type = detect_task_type(subtask["title"], subtask.get("description", ""))
    subtask["task_type"] = task_type.value
```

### Generated Frontmatter

```yaml
---
id: TASK-FN-001
title: Setup project structure and pyproject.toml
task_type: scaffolding  # AUTO-DETECTED
# ...
---
```

### Override Mechanism

If auto-detection is wrong, user can manually edit the task file:

```yaml
task_type: feature  # Manually overridden from scaffolding
```

Or specify in feature-plan:
```
/feature-plan "Create auth system" --task-type-overrides="TASK-FN-001:feature"
```

## Edge Cases

1. **Ambiguous titles**: "Create user model" could be scaffolding or feature
   - Default to `feature` for ambiguous cases (safer, more validation)

2. **Hybrid tasks**: "Setup and implement auth" has both scaffolding and feature
   - Use `feature` type (higher validation requirements)

3. **Test tasks**: "Add integration tests for auth"
   - Classify as `feature` (tests should pass tests requirement)

## Related Files

- `guardkit/models/task_types.py` (created in TASK-FBSDK-020)
- `installer/core/commands/feature-plan.md` (command specification)
- `installer/core/lib/implement_orchestrator.py` (subtask generation)

## Notes

This task can run in parallel with TASK-FBSDK-021 once TASK-FBSDK-020 is complete.
