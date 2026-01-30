# Feature: Library Knowledge Gap Prevention

## Overview

Prevent stub implementations by automatically gathering library API context before implementation planning. When a task mentions a library by name, the system proactively fetches documentation via Context7 MCP to ensure the AI has concrete implementation knowledge (imports, initialization, method signatures, return types).

## Problem Statement

From TASK-GC-72AF analysis: Tasks that say "use library X" often produce stub implementations because the AI knows *what* to do conceptually but lacks *how* to call the specific library APIs.

**Root cause**: The current Context7 integration is **reactive** (AI decides when to fetch). This fails when the AI doesn't know what it doesn't know.

**Solution**: Make Context7 usage **proactive** by detecting library mentions and automatically fetching documentation.

## Parent Review

- **Review Task**: TASK-REV-668B
- **Review Report**: `.claude/reviews/TASK-REV-668B-knowledge-gap-review.md`

## Subtasks

| Task ID | Title | Mode | Wave | Complexity | Status |
|---------|-------|------|------|------------|--------|
| TASK-LKG-001 | Implement library name detection | task-work | 1 | 4 | ✅ COMPLETED |
| TASK-LKG-002 | Implement Phase 2.1 Library Context Gathering | task-work | 1 | 5 | ✅ COMPLETED |
| TASK-LKG-003 | Update task-work.md specification | direct | 2 | 3 | ✅ COMPLETED |
| TASK-LKG-004 | Add library_context frontmatter field | task-work | 2 | 3 | Backlog |
| TASK-LKG-005 | Add API call preview to Phase 2.8 | task-work | 3 | 4 | ✅ COMPLETED |
| TASK-LKG-006 | Integration tests for library detection | task-work | 3 | 4 | Backlog |

**Progress**: 4/6 tasks complete (67%)

## Wave Execution Strategy

### Wave 1: Core Detection & Fetching (Parallel)
- TASK-LKG-001: Library detection logic
- TASK-LKG-002: Phase 2.1 implementation

### Wave 2: Documentation & Schema (Parallel, depends on Wave 1)
- TASK-LKG-003: Update task-work.md spec
- TASK-LKG-004: library_context frontmatter field

### Wave 3: Verification & Testing (Parallel, depends on Wave 2)
- TASK-LKG-005: API call preview checkpoint
- TASK-LKG-006: Integration tests

## Success Criteria

- [x] Library names automatically detected from task title/description (TASK-LKG-001)
- [x] Context7 documentation fetched for detected libraries (TASK-LKG-002)
- [x] AI receives concrete API knowledge before Phase 2 planning (TASK-LKG-003)
- [ ] Reduction in stub implementations for library-using tasks
- [x] Graceful fallback when Context7 can't resolve library (TASK-LKG-002)

## Technical Approach

### Library Detection (not migration detection)

Detect ANY library mention, not just "migration" tasks:

```python
# Detect: "using graphiti-core", "with Redis", "via PyJWT"
libraries = detect_library_mentions(task_title, task_description)

# For each detected library
for lib in libraries:
    lib_id = mcp__context7__resolve_library_id(lib)
    if lib_id:
        docs = mcp__context7__query_docs(lib_id, "initialization API methods")
        inject_into_planning_context(docs)
```

### Phase 2.1 Workflow

```
Phase 2.0: Load task context
    ↓
Phase 2.1: Library Context Gathering (NEW)
    ├── Detect library names in title/description
    ├── Resolve each via Context7
    ├── Fetch key API docs (imports, init, methods)
    └── Display gathered context to user
    ↓
Phase 2.2: Continue with planning (AI has library knowledge)
```

## Dependencies

- Context7 MCP must be available
- Existing task-work Phase 2 infrastructure

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Context7 can't resolve library | Graceful fallback, warn user |
| False positive library detection | Validate against Context7 registry |
| Over-fetching slows workflow | Token limits, caching resolved IDs |
