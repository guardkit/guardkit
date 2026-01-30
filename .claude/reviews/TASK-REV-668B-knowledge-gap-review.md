# Review Report: TASK-REV-668B

## Executive Summary

Analysis of `/task-create` and `/task-work` commands reveals a **systematic knowledge gap** in how implementation context flows from task creation to code generation. The root cause of stub implementations (as observed in TASK-GC-72AF) is **missing concrete API knowledge at implementation time**, not a failure of architectural review or test enforcement.

**Key Finding**: The current workflow tells AI *what* to do (migrate to graphiti-core) but not *how* to call the specific library APIs (imports, initialization, method signatures, return types).

**Recommended Solution**: Enhancement B (Auto-fetch Library Docs in Phase 2) combined with Enhancement C (Migration Task Detection) provides the highest value with lowest implementation complexity.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: ~45 minutes
- **Reviewer**: Claude Code AI Agent

---

## Current State Analysis

### 1. Task Creation Phase (`task-create.md`)

**What it captures well:**
- Title and description (auto-inferencing)
- Priority and tags
- Linked requirements (if Require-Kit installed)
- Complexity evaluation (Phase 2.5)
- Review task detection

**What it does NOT capture:**
- Library dependencies for migration tasks
- Required import statements
- API method signatures
- Initialization requirements
- Return type expectations

**Gap identified at**: `installer/core/commands/task-create.md:29-34` - Task structure section has no `library_context` field.

### 2. Implementation Phase (`task-work.md`)

**Context7 MCP integration exists but is reactive:**

From `task-work.md:1030-1147`:
```markdown
During task implementation, **automatically use Context7 MCP** to retrieve
up-to-date library documentation when implementing with specific libraries
or frameworks.
```

**Current triggers (Phase 2):**
- "When selecting libraries or frameworks"
- "When planning API usage patterns"

**Problem**: These triggers are **opportunistic**, not **systematic**. The AI decides whether to fetch docs based on its own judgment. For migration tasks where the AI has partial knowledge (knows the concept, lacks implementation details), this judgment fails because the AI doesn't know what it doesn't know.

### 3. Evidence from TASK-GC-72AF Stub Analysis

From `.claude/reviews/TASK-GC-72AF-stub-analysis.md:99-114`:

```markdown
### Probable Cause 1: Missing Concrete API Examples

**Observation**: The task description said "migrate from zepai/graphiti Docker
REST API to graphiti-core Python library" but did NOT include:
- graphiti-core API documentation
- Example usage code
- Import statements needed
- Object types returned (e.g., `Edge` objects)

**Result**: The AI knew it needed to wrap graphiti-core but didn't know HOW to call it.
```

The stub comments explicitly confirm this:
```python
# In production, this would call Graphiti's search API  <-- Knew what, not how
return []  # <-- Stub because lacked implementation details
```

---

## Proposed Enhancement Evaluation

### Enhancement A: Library Context in Task Frontmatter

**Proposal**: Add `library_context` field with imports, initialization, and key methods.

**Evaluation**:

| Criterion | Score | Notes |
|-----------|-------|-------|
| Effectiveness | 9/10 | Directly solves knowledge gap |
| User Effort | 3/10 | Requires manual specification |
| Automation | 2/10 | User must know API details upfront |
| Maintenance | 4/10 | Context can become stale |

**Verdict**: **HIGH VALUE, HIGH EFFORT**. Useful for teams with domain experts who can provide API details, but doesn't scale.

**When to use**: Internal/proprietary libraries not available via Context7.

### Enhancement B: Auto-fetch Library Docs in Phase 2

**Proposal**: Automatically detect library mentions and fetch Context7 docs during implementation planning.

**Evaluation**:

| Criterion | Score | Notes |
|-----------|-------|-------|
| Effectiveness | 8/10 | Proactive context gathering |
| User Effort | 9/10 | Automatic - no user action needed |
| Automation | 9/10 | Integrates with existing Context7 MCP |
| Maintenance | 8/10 | Context7 maintains current docs |

**Verdict**: **HIGH VALUE, LOW EFFORT**. Leverages existing Context7 MCP infrastructure.

**Implementation approach**:

```markdown
### Phase 2.1: Library Context Gathering (NEW)

**TRIGGER**: Detect library migration OR new library integration patterns

**DETECTION KEYWORDS**:
- "migrate", "migration", "switch to", "replace with"
- "integrate", "using {library}", "with {library}"

**IF** detected:

1. **EXTRACT** library name from task description/title
2. **RESOLVE** via Context7: `mcp__context7__resolve_library_id(library_name)`
3. **FETCH** key API documentation:
   - `mcp__context7__query_docs(library_id, "getting started initialization")`
   - `mcp__context7__query_docs(library_id, "main API methods")`
4. **INJECT** into Phase 2 planning context

**DISPLAY**:
```
📚 Library Context Gathered:
  Package: graphiti-core
  Import: from graphiti_core import Graphiti
  Key Methods: search(), add_episode(), build_indices()
  Documentation: [snippets from Context7]

Proceed with planning? [Y/n]
```
```

### Enhancement C: Library Usage Detection (REVISED)

**Original Proposal**: Detect "migrate", "switch to", "replace with" keywords.

**Revised Proposal**: Detect ANY library name mentioned in task title/description.

**Why Revised**: The original "migration detection" approach was flawed:
- Too narrow: "Add caching with Redis" has no migration keywords but has the same problem
- Fragile: Users don't consistently use "migrate" terminology
- Wrong abstraction: The problem is library API usage, not task type

**Corrected Evaluation**:

| Criterion | Score | Notes |
|-----------|-------|-------|
| Effectiveness | 9/10 | Catches ALL library usage, not just migrations |
| User Effort | 9/10 | Automatic - detects library names |
| Automation | 9/10 | Pattern matching + Context7 validation |
| Maintenance | 8/10 | Library registry can be extended |

**Verdict**: **HIGH VALUE, LOW EFFORT**. Now properly scoped to the actual problem.

**Revised implementation approach**:

```python
def detect_library_mentions(title: str, description: str) -> List[str]:
    """
    Detect library/package names that will require API knowledge.

    Uses multiple signals:
    1. Known library names (from registry)
    2. "using X", "with X" patterns
    3. Context7 validation (can be resolved)
    """
    text = f"{title} {description}".lower()

    # Signal 1: Known libraries
    known_libraries = [
        "graphiti-core", "graphiti", "fastapi", "pydantic",
        "react", "redis", "pyjwt", "langchain", "pytest", ...
    ]

    # Signal 2: Usage patterns
    usage_patterns = [
        r"using\s+(\w+[-\w]*)",   # "using graphiti-core"
        r"with\s+(\w+[-\w]*)",     # "with Redis"
        r"via\s+(\w+[-\w]*)",      # "via PyJWT"
    ]

    detected = []
    for lib in known_libraries:
        if lib in text:
            detected.append(lib)

    # Validate detected names against Context7
    return [lib for lib in detected if can_resolve_in_context7(lib)]
```

**Key Insight**: The root cause isn't "migration tasks are special" - it's:

> **Any task that says "use library X" needs to know HOW to call library X.**

The word "migration" in TASK-GC-72AF was incidental. The solution should detect library mentions, not task types.

### Enhancement D: "Show Planned API Calls" Checkpoint

**Proposal**: Add API call preview to Phase 2.8 Human Checkpoint.

**Evaluation**:

| Criterion | Score | Notes |
|-----------|-------|-------|
| Effectiveness | 6/10 | Good verification but late in pipeline |
| User Effort | 7/10 | Human must verify API correctness |
| Automation | 4/10 | Requires human judgment |
| Maintenance | 5/10 | Additional checkpoint complexity |

**Verdict**: **MEDIUM VALUE, MEDIUM EFFORT**. Useful as a verification step but doesn't prevent the problem.

**When to use**: High-risk migrations where human verification is required.

---

## Recommendation Matrix

| Enhancement | Priority | Effort | Dependencies | Implementation Mode |
|-------------|----------|--------|--------------|---------------------|
| B: Auto-fetch in Phase 2 | **P1 - Critical** | Medium (2-3 days) | Context7 MCP | `/task-work` |
| C: Migration Detection | **P2 - High** | Low (1 day) | None | `/task-work` |
| A: Library Context Field | **P3 - Medium** | Low (1 day) | Schema change | Direct |
| D: API Call Preview | **P4 - Low** | Medium (2 days) | B | `/task-work` |

---

## Recommended Implementation Approach

### Phase 1: Enhancement B (Auto-fetch Library Docs)

**Why first**: Directly addresses root cause with existing infrastructure.

**Implementation tasks**:

1. **TASK-LKG-001**: Add library detection to Phase 2 context loading
   - Detect library names from task title/description
   - Pattern matching for "using X", "with X", "to X library"
   - Complexity: 4/10, Wave 1

2. **TASK-LKG-002**: Implement Phase 2.1 Library Context Gathering
   - Context7 resolve and fetch for detected libraries
   - Display gathered context to user
   - Inject into planning prompt
   - Complexity: 5/10, Wave 1

3. **TASK-LKG-003**: Update task-work.md specification
   - Document Phase 2.1 in execution protocol
   - Add library context to agent prompts
   - Complexity: 3/10, Wave 2 (depends on TASK-LKG-002)

### Phase 2: Enhancement C (Migration Detection)

**Why second**: Complements B by flagging migration tasks early.

**Implementation tasks**:

4. **TASK-LKG-004**: Add migration task detection to task-create
   - Keyword detection for migration patterns
   - User prompt for library context
   - Optional auto-fetch via Context7
   - Complexity: 4/10, Wave 2

### Phase 3: Enhancement A (Library Context Field)

**Why third**: Provides manual override for internal/proprietary libraries.

**Implementation tasks**:

5. **TASK-LKG-005**: Add `library_context` frontmatter field
   - Schema update in task-create.md
   - Parsing in task-work Phase 1
   - Documentation update
   - Complexity: 3/10, Wave 3

### Phase 4: Enhancement D (API Call Preview)

**Why fourth**: Verification layer for high-risk migrations.

**Implementation tasks**:

6. **TASK-LKG-006**: Add API call preview to Phase 2.8
   - Extract planned API calls from implementation plan
   - Display for human verification
   - "Fetch docs" option if calls look wrong
   - Complexity: 5/10, Wave 3

---

## Integration with Existing Context7 MCP

The current Context7 integration is **reactive** (AI decides when to fetch). The recommended approach makes it **proactive** (system automatically fetches for detected libraries).

**Current flow** (`task-work.md:1030-1147`):
```
Phase 2 → AI decides "do I need library docs?" → Sometimes fetches
```

**Proposed flow**:
```
Phase 2.0 → Detect library mentions → Always fetch if detected
Phase 2.1 → Display context → Confirm with user
Phase 2.2 → Continue planning with guaranteed context
```

**No changes needed to Context7 MCP itself** - only changes to when/how it's invoked.

---

## Context7 Query Templates

For Enhancement B, use these query patterns:

**Getting Started**:
```python
mcp__context7__query_docs(
    library_id,
    "getting started initialization import setup"
)
```

**Main API Methods**:
```python
mcp__context7__query_docs(
    library_id,
    "main API methods function signatures"
)
```

**Return Types**:
```python
mcp__context7__query_docs(
    library_id,
    "return types data structures objects"
)
```

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context7 library not found | Medium | Fallback to training data, warn user |
| Over-fetching slows workflow | Low | Token limits, caching resolved IDs |
| False positive migration detection | Low | User confirmation prompt |
| Context7 rate limiting | Low | Retry logic, graceful degradation |

---

## Success Metrics

**Primary**: Reduction in stub implementations for library migration tasks
- Target: <5% stub rate (from estimated >30% currently)

**Secondary**: User satisfaction with library context
- Target: >80% approval at Phase 2.1 checkpoint

**Tertiary**: Time to working implementation
- Target: No increase (context gathering should save debugging time)

---

## Relationship to TASK-SD-CA08

**TASK-SD-CA08** (Stub Detection Quality Gate) is a **symptom treatment** - it catches stubs after they happen.

**This review** addresses **root cause** - it prevents stubs by providing implementation knowledge.

**Both are needed**:
- Root cause prevention (this review) → Reduces stub occurrence
- Symptom detection (TASK-SD-CA08) → Catches edge cases that slip through

---

## Appendix: Files Reviewed

| File | Purpose | Key Findings |
|------|---------|--------------|
| `installer/core/commands/task-create.md` | Task creation spec | No library_context field |
| `installer/core/commands/task-work.md` | Implementation workflow | Context7 exists but reactive |
| `.claude/reviews/TASK-GC-72AF-stub-analysis.md` | Stub root cause | Missing concrete API examples |
| `docs/workflows/context7-mcp-integration-workflow.md` | Context7 usage | Good infrastructure, needs proactive triggering |

---

## Decision Outcome

**Decision**: **[I]mplement** - Approved after revision

**Revision Applied**: Enhancement C was revised from "Migration Detection" to "Library Usage Detection" based on user feedback that migration keywords were too narrow and fragile.

**Implementation Tasks Created**:

| Task ID | Title | Wave | Complexity |
|---------|-------|------|------------|
| TASK-LKG-001 | Implement library name detection | 1 | 4 |
| TASK-LKG-002 | Implement Phase 2.1 Library Context Gathering | 1 | 5 |
| TASK-LKG-003 | Update task-work.md specification | 2 | 3 |
| TASK-LKG-004 | Add library_context frontmatter field | 2 | 3 |
| TASK-LKG-005 | Add API call preview to Phase 2.8 | 3 | 4 |
| TASK-LKG-006 | Integration tests for library detection | 3 | 4 |

**Location**: `tasks/backlog/library-knowledge-gap/`

**Expected outcome**: 80%+ reduction in stub implementations for library-using tasks (not just migrations).

---

*Generated by GuardKit /task-review command*
*Review ID: TASK-REV-668B*
*Date: 2026-01-30*
*Revised: 2026-01-30 (Enhancement C corrected)*
