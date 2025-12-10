---
id: TASK-UX-7F1E
title: Add design URL parameter to task-create command
status: backlog
created: 2025-11-11T10:30:00Z
updated: 2025-11-11T10:30:00Z
priority: high
tags: [ux-integration, task-create]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add design URL parameter to task-create command

## Description

Extend the `/task-create` command to accept an optional `design:URL` parameter that allows users to specify a design URL (Figma, Zeplin, Sketch) when creating tasks.

This is the first task in the Design URL Integration project (see [design-url-integration-proposal.md](../../docs/proposals/design-url-integration-proposal.md) and [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] `/task-create` command accepts `design:URL` parameter
- [ ] Design URL is stored in task frontmatter under `design_url` field
- [ ] Design source is auto-detected (figma/zeplin/sketch) and stored in `design_source` field
- [ ] Design metadata (file_key, node_id, etc.) extracted and stored in `design_metadata` field
- [ ] Command works with or without design URL (backward compatible)
- [ ] Documentation updated with design URL parameter usage

## Implementation Notes

### Files to Modify
- `installer/core/commands/task-create.md` - Update command specification
- Task creation script/logic - Add design URL parameter parsing

### Task Frontmatter Extension
```yaml
---
id: TASK-001
title: Implement login form
status: backlog
design_url: https://figma.com/design/abc?node-id=2-2
design_source: figma  # Auto-detected: figma | zeplin | sketch
design_metadata:
  file_key: abc123
  node_id: "2:2"
  extracted_at: null
---
```

### Design Source Detection
```python
def detect_design_source(url: str) -> str:
    """Auto-detect design tool from URL."""
    if "figma.com" in url:
        return "figma"
    elif "zeplin.io" in url or "app.zeplin.io" in url:
        return "zeplin"
    elif "sketch.com" in url:
        return "sketch"
    else:
        raise ValueError(f"Unsupported design tool: {url}")
```

### Usage Examples
```bash
# With Figma design
/task-create "Login form" design:https://figma.com/design/abc?node-id=2-2 priority:high

# With Zeplin design
/task-create "User profile" design:https://app.zeplin.io/project/abc/screen/def

# Without design (existing behavior)
/task-create "Add validation logic" priority:high
```

## Test Requirements

- [ ] Unit tests for design URL parameter parsing
- [ ] Unit tests for design source detection
- [ ] Unit tests for design metadata extraction
- [ ] Integration test: Create task with Figma URL
- [ ] Integration test: Create task with Zeplin URL
- [ ] Integration test: Create task without design URL (backward compatibility)
- [ ] Edge case tests: Invalid URLs, unsupported design tools

## Dependencies

**None** - This is the first task in the implementation sequence.

## Next Steps

After completing this task:
1. TASK-UX-002: Implement design URL validation
2. TASK-UX-005: Update task-work Phase 1 to load design URL from frontmatter

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md)
- [Design URL Integration Implementation Guide](../../docs/proposals/design-url-integration-implementation-guide.md)

## Implementation Estimate

**Duration**: 2-4 hours

**Complexity**: 3/10 (Simple)
- Single file modification (task-create command)
- Straightforward parameter parsing
- Basic URL pattern detection
- No external dependencies

## Test Execution Log

_Automatically populated by /task-work_
