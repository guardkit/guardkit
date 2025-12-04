---
id: TASK-FW-004
title: Add implementation mode auto-tagging (complexity/risk analysis)
status: backlog
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T11:00:00Z
priority: high
tags: [feature-workflow, auto-detection, complexity]
complexity: 5
implementation_mode: task-work
parallel_group: 2
conductor_workspace: feature-workflow-2
parent_review: TASK-REV-FW01
---

# Implementation Mode Auto-Tagging

## Description

Automatically assign implementation mode (`task-work`, `direct`, `manual`) to each subtask based on complexity and risk analysis.

## Acceptance Criteria

- [ ] Analyze subtask complexity based on multiple factors
- [ ] Detect high-risk keywords (security, auth, database, etc.)
- [ ] Assign `task-work` for complex/risky tasks
- [ ] Assign `direct` for simple/low-risk tasks
- [ ] Assign `manual` for script execution tasks
- [ ] Add `implementation_mode` to subtask frontmatter

## Implementation Details

### Mode Assignment Logic

```python
def assign_implementation_mode(subtask: dict) -> str:
    """
    Assign implementation mode based on complexity and risk.

    Returns: "task-work" | "direct" | "manual"
    """
    # Check for manual indicators
    manual_keywords = ["run script", "execute", "bulk operation", "migration"]
    if any(kw in subtask["title"].lower() for kw in manual_keywords):
        return "manual"

    # Check for high-risk indicators
    risk_keywords = [
        "security", "auth", "authentication", "authorization",
        "database", "schema", "migration", "api", "endpoint",
        "refactor", "breaking change", "core", "foundation"
    ]
    is_high_risk = any(kw in subtask["title"].lower() for kw in risk_keywords)
    is_high_risk = is_high_risk or any(kw in subtask.get("description", "").lower() for kw in risk_keywords)

    # Check complexity score
    complexity = subtask.get("complexity", 5)

    # Decision matrix
    if complexity >= 6 or is_high_risk:
        return "task-work"
    elif complexity <= 3:
        return "direct"
    else:
        # Medium complexity - check file count
        file_count = len(subtask.get("files", []))
        if file_count > 3:
            return "task-work"
        else:
            return "direct"
```

### Mode Definitions

| Mode | When to Use | Quality Gates |
|------|-------------|---------------|
| `task-work` | Complex logic, needs review | Full phases 2-5.5 |
| `direct` | Simple changes, configuration | None (direct Claude Code) |
| `manual` | Script execution, bulk ops | Human runs command |

### Complexity Factors

1. **Keyword complexity**: Risk keywords increase score
2. **File count**: More files = higher complexity
3. **Code changes**: New files vs modifications
4. **Dependencies**: External library changes

## Files to Create/Modify

- `installer/global/lib/complexity_analyzer.py` (NEW or extend existing)

## Test Cases

| Subtask Title | Expected Mode |
|---------------|---------------|
| "Add CSS variables" | direct |
| "Refactor authentication service" | task-work |
| "Run database migration script" | manual |
| "Update documentation" | direct |
| "Implement OAuth 2.0 flow" | task-work |
| "Fix typo in README" | direct |

## Dependencies

- TASK-FW-003 (provides subtask definitions)

## Notes

Can run in parallel with FW-005, FW-006 since it operates on subtask data.
