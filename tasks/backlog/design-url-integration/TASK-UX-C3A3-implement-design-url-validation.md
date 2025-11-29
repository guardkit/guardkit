---
id: TASK-UX-C3A3
title: Implement design URL validation
status: backlog
created: 2025-11-11T10:35:00Z
updated: 2025-11-11T10:35:00Z
priority: high
tags: [ux-integration, validation]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement design URL validation

## Description

Add comprehensive validation for design URLs during task creation to fail fast when URLs are invalid, inaccessible, or when required MCP servers are not available.

This is the second task in the Design URL Integration project (see [design-url-integration-proposal.md](../../docs/proposals/design-url-integration-proposal.md) and [design-url-integration-implementation-guide.md](../../docs/proposals/design-url-integration-implementation-guide.md)).

## Acceptance Criteria

- [ ] URL format validation - check URL matches known design tool patterns
- [ ] MCP availability check - verify required MCP server is installed
- [ ] Accessibility check - attempt to fetch design metadata (lightweight call)
- [ ] Authentication check - validate access token has required permissions
- [ ] Clear error messages with actionable suggestions
- [ ] Graceful handling when design URL is not provided (backward compatible)
- [ ] Unit tests for all validation scenarios

## Implementation Notes

### Files to Modify
- `installer/global/commands/task-create.md` - Add validation logic
- Task creation script/logic - Implement validation functions

### Validation Steps

```python
def validate_design_url(url: str) -> ValidationResult:
    # 1. Detect design source
    design_source = detect_design_source(url)  # "figma" | "zeplin"

    # 2. Check MCP server availability
    if design_source == "figma" and not mcp_available("figma-dev-mode"):
        return ValidationResult(
            valid=False,
            error="Figma MCP server not installed",
            help="Run: npm install -g @figma/mcp-server"
        )

    if design_source == "zeplin" and not mcp_available("zeplin"):
        return ValidationResult(
            valid=False,
            error="Zeplin MCP server not installed",
            help="Install Zeplin MCP server"
        )

    # 3. Lightweight accessibility check
    try:
        metadata = fetch_design_metadata(url, design_source)
        return ValidationResult(valid=True, metadata=metadata)
    except AuthError:
        return ValidationResult(
            valid=False,
            error="Design URL not accessible - authentication failed",
            help="Check FIGMA_ACCESS_TOKEN in .env"
        )
    except NotFoundError:
        return ValidationResult(
            valid=False,
            error="Design URL not found",
            help="Verify URL is correct and design exists"
        )
```

### Error Message Examples

**Invalid URL format:**
```
❌ Design URL validation failed

Error: Invalid URL format
URL: https://invalid-url.com/test

Expected format:
- Figma: https://figma.com/design/{file-key}?node-id={node-id}
- Zeplin: https://app.zeplin.io/project/{project-id}/screen/{screen-id}

Task creation aborted.
```

**MCP server not available:**
```
❌ Design URL validation failed

Error: Figma MCP server not installed
URL: https://figma.com/design/abc?node-id=2-2

To use Figma design URLs, install the MCP server:
  npm install -g @figma/figma-dev-mode

After installation, configure your access token in .env:
  FIGMA_ACCESS_TOKEN=your-token-here

Task creation aborted.
```

**Design not accessible:**
```
❌ Design URL validation failed

Error: Design not found
URL: https://figma.com/design/abc?node-id=2-2

Possible causes:
- URL is incorrect or malformed
- Design was deleted or moved
- Access token doesn't have permission to this file

Suggestions:
1. Verify URL in Figma
2. Check FIGMA_ACCESS_TOKEN has 'file:read' scope
3. Ensure design is shared with you

Task creation aborted.
```

### Validation Functions to Implement

```python
def mcp_available(mcp_name: str) -> bool:
    """Check if MCP server is installed and accessible."""
    # Check MCP server configuration
    # Return True if available, False otherwise
    pass

def fetch_design_metadata(url: str, design_source: str) -> dict:
    """Lightweight check to verify design URL is accessible."""
    # Use appropriate MCP to fetch minimal metadata
    # Raises AuthError or NotFoundError if issues
    pass
```

## Test Requirements

- [ ] Unit test: Valid Figma URL with available MCP
- [ ] Unit test: Valid Zeplin URL with available MCP
- [ ] Unit test: Invalid URL format
- [ ] Unit test: MCP server not installed
- [ ] Unit test: Authentication failure
- [ ] Unit test: Design not found
- [ ] Unit test: No design URL provided (should skip validation)
- [ ] Integration test: Full task creation with valid design URL
- [ ] Integration test: Task creation with invalid design URL (should abort)

## Dependencies

**Depends on**: TASK-UX-7F1E (Add design URL parameter to task-create)

This task extends the design URL parameter added in UX-7F1E with validation logic.

## Next Steps

After completing this task:
1. TASK-UX-003: Create react-ux-specialist agent (can be developed in parallel)
2. TASK-UX-004: Create maui-ux-specialist agent (can be developed in parallel)
3. TASK-UX-005: Update task-work Phase 1 to load design URL from frontmatter

## References

- [Design URL Integration Proposal](../../docs/proposals/design-url-integration-proposal.md) - See "Design Decisions" section #5
- [Design URL Integration Implementation Guide](../../docs/proposals/design-url-integration-implementation-guide.md) - Phase 1, TASK-UX-002

## Implementation Estimate

**Duration**: 2-4 hours

**Complexity**: 4/10 (Simple-Medium)
- MCP availability checking
- Error handling and messaging
- Lightweight metadata fetching
- Multiple validation scenarios

## Test Execution Log

_Automatically populated by /task-work_
