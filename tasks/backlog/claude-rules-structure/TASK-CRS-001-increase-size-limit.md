---
id: TASK-CRS-001
title: Increase Default CLAUDE.md Size Limit to 25KB
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: high
tags: [quick-fix, size-limit, template-create]
complexity: 2
parent_feature: claude-rules-structure
wave: 1
implementation_mode: direct
conductor_workspace: claude-rules-wave1-1
estimated_hours: 1-2
dependencies: []
---

# Task: Increase Default CLAUDE.md Size Limit to 25KB

## Description

Increase the default CLAUDE.md size limit from 10KB to 25KB to unblock complex templates like `.NET MAUI` and `fastapi-python` (currently 29.2KB).

## Problem

- Default 10KB limit is too restrictive
- `fastapi-python` template is 29.2KB
- Complex codebases generate larger CLAUDE.md files
- Users must manually override with `--claude-md-size-limit` flag

## Files to Modify

| File | Line | Change |
|------|------|--------|
| `installer/core/lib/template_generator/models.py` | ~409 | Change `10 * 1024` to `25 * 1024` |
| `installer/core/commands/lib/template_create_orchestrator.py` | ~125 | Change `10 * 1024` to `25 * 1024` |

## Implementation

### Step 1: Update models.py

```python
def validate_size_constraints(self, max_core_size: int = 25 * 1024) -> tuple[bool, Optional[str]]:
    """
    Validate that core content doesn't exceed size limit.

    Args:
        max_core_size: Maximum allowed size in bytes (default 25KB, configurable via --claude-md-size-limit)

    Note:
        Increased from 10KB to 25KB based on real-world template analysis.
        Complex templates (.NET MAUI, React + FastAPI) typically need 15-25KB.
    """
```

### Step 2: Update template_create_orchestrator.py

```python
@dataclass
class OrchestrationConfig:
    # ... other config options ...
    claude_md_size_limit: int = 25 * 1024  # Default 25KB (increased from 10KB)
```

## Acceptance Criteria

- [ ] Default size limit is 25KB in both files
- [ ] Existing templates still generate without errors
- [ ] CLI flag `--claude-md-size-limit` still works for custom values
- [ ] Unit tests pass

## Testing

```bash
# Verify default limit
python3 -c "from installer.core.commands.lib.template_create_orchestrator import OrchestrationConfig; print(OrchestrationConfig().claude_md_size_limit)"
# Expected: 25600 (25 * 1024)

# Test with existing template
pytest tests/lib/template_generator/test_orchestrator_split_claude_md.py -v -k size
```

## Notes

- This is a quick fix (Wave 1)
- Low risk - only increases limit, doesn't change behavior
- Backward compatible - users with smaller templates unaffected
- Unblocks TASK-FIX-SIZE-F8G2 Phase 1
