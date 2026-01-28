---
complexity: 6
conductor_workspace: fastmcp-wave2-3
created: 2026-01-24 14:30:00+00:00
dependencies:
- TASK-FMT-002
feature_id: FEAT-FMT
id: TASK-FMT-005
implementation_mode: task-work
parallel_group: wave2
parent_review: TASK-REV-A7F3
priority: high
status: in_review
tags:
- template
- mcp
- fastmcp
- scaffolding
task_type: scaffolding
title: Create code templates for fastmcp-python
updated: 2026-01-28T14:30:00+00:00
wave: 2
code_review:
  score: 92
  status: approved_with_recommendations
  recommendations:
    - Add resource lifecycle management example
    - Implement concrete dependency check pattern
    - Add cursor implementation example
---

# Task: Create code templates for fastmcp-python

## Description

Create code scaffolding templates for the `fastmcp-python` template. These templates enable developers to quickly generate MCP server boilerplate with all critical patterns embedded.

## Reference

Use `installer/core/templates/fastapi-python/templates/` as structural reference.

## Files Created

```
installer/core/templates/fastmcp-python/templates/
├── server/
│   ├── __main__.py.template ✅
│   └── server.py.template ✅
├── tools/
│   ├── tool.py.template ✅
│   ├── streaming_tool.py.template ✅
│   ├── health_check_tool.py.template ✅ (GAP-2)
│   └── paginated_tool.py.template ✅ (GAP-4)
├── resources/
│   └── resource.py.template ✅
├── config/
│   ├── pyproject.toml.template ✅
│   └── Dockerfile.template ✅
└── testing/
    ├── conftest.py.template ✅
    └── test_tool.py.template ✅
```

## Acceptance Criteria

### server/__main__.py.template (CRITICAL)

- [x] Tool registration at module level
- [x] Logging to stderr configuration
- [x] FastMCP initialization
- [x] Placeholders: {{ServerName}}, {{ServerDescription}}

### tools/tool.py.template

- [x] Parameter type conversion pattern
- [x] Async function structure
- [x] Error handling
- [x] Placeholders: {{ToolName}}, {{ToolDescription}}, {{Parameters}}

### tools/streaming_tool.py.template (Two-Layer Pattern)

- [x] Implementation layer (AsyncGenerator)
- [x] FastMCP wrapper layer
- [x] CancelledError handling
- [x] Cleanup in finally block

### config/Dockerfile.template

- [x] Python 3.10-slim base
- [x] Non-root user (mcp)
- [x] PYTHONUNBUFFERED=1
- [x] Proper CMD for stdio transport

### testing/test_tool.py.template

- [x] pytest-asyncio markers
- [x] String parameter conversion tests
- [x] Basic functionality tests

## Gap Analysis Additions (TASK-REV-A7F9)

### tools/health_check_tool.py.template (GAP-2: Critical)

- [x] Includes uptime tracking
- [x] Includes memory monitoring
- [x] Includes dependency health checks
- [x] Uses timezone-aware datetime

### tools/paginated_tool.py.template (GAP-4: Major)

- [x] Cursor-based pagination pattern
- [x] Limit parameter with bounds (1-100)
- [x] next_cursor in response
- [x] has_more indicator

## Critical Patterns Embedded

1. **__main__.py**: Tool registration at module level ✅
2. **Logging**: stderr only (NOT stdout) ✅
3. **Parameters**: String conversion with `int()`, `float()`, `bool()` ✅
4. **Streaming**: Two-layer architecture (implementation + wrapper) ✅
5. **Docker**: Non-root user, PYTHONUNBUFFERED=1 ✅

## Test Execution Log

**Date**: 2026-01-28T14:30:00+00:00
**Mode**: TDD (Red-Green-Refactor)

### Phase 3-TDD: RED Phase
- Created test file: `tests/unit/test_fastmcp_templates.py`
- Total tests: 69
- Initial status: 17 FAILED, 1 PASSED, 50 ERRORS (templates didn't exist)

### Phase 3-TDD: GREEN Phase
- Created all 11 template files
- All critical patterns implemented

### Phase 4: Testing
```
tests/unit/test_fastmcp_templates.py .................. [100%]
69 passed in 2.45s
```

### Phase 5: Code Review
- **Quality Score**: 92/100
- **Status**: APPROVED WITH MINOR RECOMMENDATIONS
- **Critical Issues**: 0
- **Recommendations**:
  1. Add resource lifecycle management example
  2. Implement concrete dependency check pattern
  3. Add cursor implementation example

### Quality Gates
| Gate | Threshold | Result |
|------|-----------|--------|
| Tests Passing | 100% | ✅ 69/69 (100%) |
| Code Review | ≥60/100 | ✅ 92/100 |
| Critical Patterns | All 8 | ✅ Implemented |
| MCP Protocol | No violations | ✅ stderr logging, stdio transport |
