---
id: TASK-FMT-003
title: Create fastmcp-specialist agent
status: backlog
task_type: documentation
created: 2026-01-24T14:30:00Z
updated: 2026-01-24T14:30:00Z
priority: high
tags: [template, mcp, fastmcp, agent]
complexity: 5
parent_review: TASK-REV-A7F3
feature_id: FEAT-FMT
wave: 2
parallel_group: wave2
implementation_mode: task-work
conductor_workspace: fastmcp-wave2-1
dependencies: [TASK-FMT-002]
---

# Task: Create fastmcp-specialist agent

## Description

Create the core `fastmcp-specialist` agent for the `fastmcp-python` template. This agent provides guidance for MCP server development and embeds the 10 critical production patterns as boundaries.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-specialist.md` as structural reference.

## Files to Create

1. `installer/core/templates/fastmcp-python/agents/fastmcp-specialist.md` (core)
2. `installer/core/templates/fastmcp-python/agents/fastmcp-specialist-ext.md` (extended)

## Acceptance Criteria

### Core Agent File (fastmcp-specialist.md)

- [ ] Valid frontmatter with:
  - name: fastmcp-specialist
  - stack: [python, mcp, fastmcp]
  - phase: implementation
  - capabilities: 5-7 MCP-specific capabilities
  - keywords: [mcp, fastmcp, python, claude-code, tools, resources]
  - collaborates_with: [fastmcp-testing-specialist]
- [ ] Role section describing MCP server specialist
- [ ] Boundaries section with ALWAYS/NEVER/ASK:

**ALWAYS (embed critical patterns)**:
- ✅ Register tools in `__main__.py` at module level
- ✅ Log to stderr only (stdout reserved for MCP protocol)
- ✅ Convert string parameters explicitly (`int(count)`)
- ✅ Use FastMCP, never custom Server classes
- ✅ Use `datetime.now(UTC)` not deprecated `utcnow()`
- ✅ Handle `asyncio.CancelledError` in streaming

**NEVER**:
- ❌ Never print to stdout (breaks MCP protocol)
- ❌ Never use relative paths in .mcp.json
- ❌ Never register tools outside __main__.py
- ❌ Never return AsyncGenerator directly from FastMCP tools

**ASK**:
- ⚠️ Streaming vs non-streaming tool design
- ⚠️ Docker vs local development configuration

- [ ] Capabilities section covering:
  1. Tool Registration and Discovery
  2. Streaming Tool Architecture
  3. Resource Definition
  4. Protocol Configuration
  5. Error Handling Patterns
  6. Async Pattern Implementation

- [ ] References section with MCP links
- [ ] Related Agents section

### Extended Agent File (fastmcp-specialist-ext.md)

- [ ] Code examples for:
  - Basic tool registration
  - Streaming two-layer pattern
  - Parameter type conversion
  - Error handling
- [ ] Best practices section (5-8 practices)
- [ ] Anti-patterns section (3-5 common mistakes)
- [ ] Troubleshooting section

## Critical Patterns to Embed

All 10 patterns from TASK-REV-MCP must be present in boundaries or capabilities:

1. ✅ Use FastMCP, Not Custom Server Classes → ALWAYS
2. ✅ Tool Registration in `__main__.py` → ALWAYS
3. ✅ Logging to stderr → ALWAYS
4. ✅ Streaming Tools Two-Layer Architecture → Capability
5. ✅ Error Handling for Streaming → ALWAYS
6. ✅ MCP Parameter Type Conversion → ALWAYS
7. ✅ Configuration with Absolute Paths → NEVER (relative)
8. ✅ Timestamp Best Practices → ALWAYS
9. ✅ Protocol Testing Commands → References
10. ✅ Docker Deployment Patterns → Extended file

## Gap Analysis Additions (TASK-REV-A7F9)

The following items were identified in gap analysis and MUST be included:

### Additional ALWAYS Boundaries

- ✅ Accept and log client-generated request IDs for idempotency
- ✅ Use cursor-based pagination for list operations returning >20 items
- ✅ Return structured content with both `content` (text) and `structuredContent` (JSON) fields

### Additional Capabilities

- **Idempotent Operation Patterns**: Design tools that return deterministic results for same inputs
- **Pagination Design**: Cursor-based pagination with `next_cursor` response pattern
- **Structured Content Responses**: Dual-format responses for LLM parsing and human readability

### Extended File Addition

Add to `fastmcp-specialist-ext.md`:

**Circuit Breaker Pattern Example**:
```python
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CircuitBreaker:
    failures: int = 0
    last_failure: datetime = None
    state: str = "closed"  # closed, open, half-open

    def record_failure(self):
        self.failures += 1
        self.last_failure = datetime.now()
        if self.failures >= 3:  # Open after 3 consecutive failures
            self.state = "open"

    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            # Reset attempt after 60 seconds
            if datetime.now() - self.last_failure > timedelta(seconds=60):
                self.state = "half-open"
                return True
            return False
        return True  # half-open allows one attempt
```

### Source

These additions address gaps identified in TASK-REV-A7F9 gap analysis:
- GAP-3: Idempotent operations with request IDs
- GAP-5: Structured content pattern
- GAP-7: Circuit breaker pattern details

## Test Execution Log

[Automatically populated by /task-work]
