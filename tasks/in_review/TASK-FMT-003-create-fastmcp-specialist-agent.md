---
complexity: 5
conductor_workspace: fastmcp-wave2-1
created: 2026-01-24 14:30:00+00:00
dependencies:
- TASK-FMT-002
feature_id: FEAT-FMT
id: TASK-FMT-003
implementation_mode: task-work
parallel_group: wave2
parent_review: TASK-REV-A7F3
priority: high
status: in_review
tags:
- template
- mcp
- fastmcp
- agent
task_type: documentation
title: Create fastmcp-specialist agent
updated: 2026-01-28T07:30:00+00:00
wave: 2
implementation:
  completed_at: 2026-01-28T07:30:00+00:00
  mode: tdd
  workflow: implement-only
  files_created:
    - installer/core/templates/fastmcp-python/agents/fastmcp-specialist.md
    - installer/core/templates/fastmcp-python/agents/fastmcp-specialist-ext.md
  validation:
    total_criteria: 57
    passed: 57
    failed: 0
  review:
    score: 92
    status: approved
    blockers: 0
    suggestions: 3
---

# Task: Create fastmcp-specialist agent

## Description

Create the core `fastmcp-specialist` agent for the `fastmcp-python` template. This agent provides guidance for MCP server development and embeds the 10 critical production patterns as boundaries.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-specialist.md` as structural reference.

## Files Created

1. `installer/core/templates/fastmcp-python/agents/fastmcp-specialist.md` (core) - 92 lines
2. `installer/core/templates/fastmcp-python/agents/fastmcp-specialist-ext.md` (extended) - 641 lines

## Acceptance Criteria

### Core Agent File (fastmcp-specialist.md)

- [x] Valid frontmatter with:
  - name: fastmcp-specialist
  - stack: [python, mcp, fastmcp]
  - phase: implementation
  - capabilities: 5-7 MCP-specific capabilities
  - keywords: [mcp, fastmcp, python, claude-code, tools, resources]
  - collaborates_with: [fastmcp-testing-specialist]
- [x] Role section describing MCP server specialist
- [x] Boundaries section with ALWAYS/NEVER/ASK:

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

- [x] Capabilities section covering:
  1. Tool Registration and Discovery
  2. Streaming Tool Architecture
  3. Resource Definition
  4. Protocol Configuration
  5. Error Handling Patterns
  6. Async Pattern Implementation

- [x] References section with MCP links
- [x] Related Agents section

### Extended Agent File (fastmcp-specialist-ext.md)

- [x] Code examples for:
  - Basic tool registration
  - Streaming two-layer pattern
  - Parameter type conversion
  - Error handling
- [x] Best practices section (5-8 practices)
- [x] Anti-patterns section (3-5 common mistakes)
- [x] Troubleshooting section

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

- ✅ Circuit Breaker Pattern Example included

### Source

These additions address gaps identified in TASK-REV-A7F9 gap analysis:
- GAP-3: Idempotent operations with request IDs ✅
- GAP-5: Structured content pattern ✅
- GAP-7: Circuit breaker pattern details ✅

## Test Execution Log

### Validation Results (2026-01-28)

**Core Agent File (fastmcp-specialist.md)**: 30/30 PASS
- All frontmatter fields present and correct
- All ALWAYS rules (10 items) implemented
- All NEVER rules (5 items) implemented
- All ASK rules (4 items) implemented
- 8 capabilities documented
- References and Related Agents complete

**Extended Agent File (fastmcp-specialist-ext.md)**: 14/14 PASS
- 10 code examples (basic tool, streaming, params, error handling, idempotent, pagination, structured content, circuit breaker, resources, config)
- 10 best practices documented
- 5 anti-patterns documented with code
- 6 troubleshooting scenarios

**Critical Patterns Coverage**: 13/13 PASS
- All 10 baseline patterns + 3 gap analysis patterns embedded

### Code Review Results

**Score**: 92/100
**Status**: APPROVED
**Issues**: 0 blockers, 3 minor suggestions

**Strengths**:
- Excellent boundaries section with all critical patterns
- Comprehensive extended documentation (10 code examples)
- Complete pattern coverage
- Production-ready code examples
- Professional documentation quality
- Perfect consistency with template conventions

**Suggestions** (non-blocking):
1. Consider adding cursor encoding strategies comment
2. Could add validation example in parameter conversion
3. Could add Claude Desktop log file locations in troubleshooting
