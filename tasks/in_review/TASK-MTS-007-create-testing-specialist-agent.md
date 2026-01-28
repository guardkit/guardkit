---
complexity: 4
conductor_workspace: mcp-ts-wave3-1
created: 2026-01-24 16:45:00+00:00
dependencies:
- TASK-MTS-003
feature_id: FEAT-MTS
id: TASK-MTS-007
implementation_mode: task-work
parallel_group: wave3
parent_review: TASK-REV-4371
priority: medium
status: in_review
tags:
- template
- mcp
- typescript
- agent
- testing
task_type: feature
title: Create mcp-testing-specialist agent
updated: 2026-01-28 19:15:00+00:00
wave: 3
---

# Task: Create mcp-testing-specialist agent

## Description

Create a specialized agent for MCP server testing, covering unit tests (Vitest), protocol tests (JSON-RPC), and integration testing patterns.

## Reference

Use `installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md` as structural reference.
Use `.claude/reviews/TASK-REV-4371-review-report.md` Section 7 for testing strategy.

## Acceptance Criteria

- [x] Core file created at `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist.md`
- [x] Extended file created at `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist-ext.md`
- [x] Valid frontmatter with:
  - name: mcp-testing-specialist
  - description: MCP server testing specialist
  - tools: [Read, Write, Edit, Bash, Grep]
  - model: haiku
  - stack: [typescript, vitest, mcp]
  - phase: testing
  - priority: 7
- [x] Testing pyramid documented:
  - Unit tests (Vitest)
  - Protocol tests (JSON-RPC manual)
  - Integration tests (MCP Inspector)
- [x] ALWAYS boundaries:
  - Test tool implementations independently
  - Test with JSON-RPC protocol commands
  - Mock external dependencies
  - Verify stderr logging doesn't break tests
- [x] NEVER boundaries:
  - Assume unit tests verify protocol compliance
  - Skip protocol testing
  - Use console.log in test files (affects STDIO)

## Agent Structure

```markdown
---
name: mcp-testing-specialist
description: MCP server testing specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku

stack: [typescript, vitest, mcp]
phase: testing
capabilities:
  - Unit testing with Vitest
  - Protocol testing with JSON-RPC
  - Integration testing patterns
  - Coverage analysis
keywords: [mcp, testing, vitest, protocol, json-rpc]

collaborates_with:
  - mcp-typescript-specialist
priority: 7
---

## Role
You are an MCP testing specialist focusing on comprehensive test coverage for MCP servers.

## Test Pyramid

### Level 1: Unit Tests (Vitest)
- Test tool implementation functions independently
- Test schema validation
- Mock external dependencies

### Level 2: Protocol Tests (JSON-RPC)
- Test initialize handshake
- Test tools/list endpoint
- Test tools/call with various inputs
- Test error responses

### Level 3: Integration Tests
- Test with MCP Inspector
- Test Claude Desktop connection
- Test end-to-end workflows

## Boundaries

### ALWAYS
[Testing patterns]

### NEVER
[Anti-patterns]

## Extended Reference
See agents/mcp-testing-specialist-ext.md
```

## Test Execution Log

### Implementation Phase (TDD Mode)
- **Date**: 2026-01-28
- **Mode**: TDD (Red → Green → Refactor)
- **Workflow**: --implement-only (using approved design)

### Files Created
1. `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist.md` (331 lines, 10,032 bytes)
2. `installer/core/templates/mcp-typescript/agents/mcp-testing-specialist-ext.md` (913 lines, 24,445 bytes)

### Phase 4: Validation Results
- **Status**: ✅ PASS
- **Frontmatter**: All required fields present and correct
- **Test Pyramid**: All 3 levels documented (Unit, Protocol, Integration)
- **ALWAYS Boundaries**: 8 boundaries with rationales
- **NEVER Boundaries**: 8 boundaries with MCP-specific concerns
- **ASK Boundaries**: 5 boundaries for edge cases
- **Code Examples**: 10 in core, 30+ in extended (all syntactically correct)

### Phase 5: Code Review Results
- **Overall Score**: 92/100
- **Verdict**: ✅ APPROVED with minor revisions

**Strengths**:
- Complete coverage of all three testing levels
- Practical examples with real code
- MCP-specific guidance on STDIO transport, stderr logging
- Comprehensive troubleshooting section
- Clear boundaries preventing common mistakes

**Minor Issues Identified**:
- Inconsistent comment style (missing emoji markers)
- Missing malformed JSON-RPC test case
- Vague async test boundary rationale

**Recommendation**: Approve for merge; minor issues can be addressed in follow-up refinement task.

### State Transition
- **From**: DESIGN_APPROVED
- **To**: IN_REVIEW
- **Reason**: All quality gates passed, implementation verified
