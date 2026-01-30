# Implementation Guide: Library Knowledge Gap Prevention

## Wave Breakdown

### Wave 1: Core Detection & Fetching

**Tasks**: TASK-LKG-001, TASK-LKG-002 (parallel)

**Conductor Workspaces**:
- `library-knowledge-gap-wave1-detection`
- `library-knowledge-gap-wave1-phase21`

**Goal**: Implement the core library detection and Context7 fetching logic.

**Dependencies**: None (first wave)

**Deliverables**:
- `installer/core/commands/lib/library_detector.py` - Detection module
- `installer/core/commands/lib/library_context_gatherer.py` - Context7 integration

---

### Wave 2: Documentation & Schema

**Tasks**: TASK-LKG-003, TASK-LKG-004 (parallel)

**Conductor Workspaces**:
- `library-knowledge-gap-wave2-spec`
- `library-knowledge-gap-wave2-schema`

**Goal**: Document Phase 2.1 in specifications and add optional frontmatter field.

**Dependencies**: Wave 1 complete

**Deliverables**:
- Updated `installer/core/commands/task-work.md`
- Updated `installer/core/commands/task-create.md`
- Schema changes for `library_context` field

---

### Wave 3: Verification & Testing

**Tasks**: TASK-LKG-005, TASK-LKG-006 (parallel)

**Conductor Workspaces**:
- `library-knowledge-gap-wave3-preview`
- `library-knowledge-gap-wave3-tests`

**Goal**: Add verification checkpoint and comprehensive tests.

**Dependencies**: Wave 2 complete

**Deliverables**:
- API call preview in Phase 2.8
- Integration tests for detection + fetching

---

## File Structure

```
installer/core/commands/
├── lib/
│   ├── library_detector.py      # NEW: Library name detection
│   ├── library_context.py       # NEW: Context7 gathering
│   └── ...
├── task-work.md                 # UPDATED: Phase 2.1 spec
└── task-create.md               # UPDATED: library_context field

tests/
└── test_library_detection.py    # NEW: Integration tests
```

## Integration Points

### task-work.md Changes

Add Phase 2.1 between Phase 2.0 (Load Context) and Phase 2.2 (Planning):

```markdown
### Phase 2.1: Library Context Gathering (NEW)

**TRIGGER**: Always execute (detection is fast, no-op if no libraries)

**STEP 1: Detect Libraries**
```python
from installer.core.commands.lib.library_detector import detect_library_mentions

libraries = detect_library_mentions(
    task_context.get("title", ""),
    task_context.get("description", "")
)
```

**STEP 2: Resolve and Fetch** (if libraries detected)
```python
from installer.core.commands.lib.library_context import gather_library_context

if libraries:
    library_context = gather_library_context(libraries)
    task_context["library_context"] = library_context

    **DISPLAY**:
    📚 Library Context Gathered:
      {for lib in library_context:}
      • {lib.name}: {lib.summary}
        Import: {lib.import_statement}
        Key methods: {lib.key_methods}
      {endfor}
```

**STEP 3: Inject into Planning**
- Add library_context to Phase 2 agent prompt
- AI receives concrete API knowledge before planning
```

### Agent Prompt Enhancement

Phase 2 agent prompt should include:

```
{if task_context.library_context:}
LIBRARY CONTEXT (from Phase 2.1):
The following libraries were detected in this task. Use this documentation
to write WORKING code, not stubs:

{for lib in task_context.library_context:}
### {lib.name}
Import: {lib.import_statement}
Initialization: {lib.initialization}
Key Methods:
{lib.method_docs}
{endfor}

IMPORTANT: Use the actual API calls shown above. Do NOT write placeholder
comments like "# In production, this would call..."
{endif}
```

## Testing Strategy

### Unit Tests (TASK-LKG-001)

```python
def test_detect_known_library():
    assert detect_library_mentions("Implement search with graphiti-core", "") == ["graphiti-core"]

def test_detect_using_pattern():
    assert detect_library_mentions("Add caching using Redis", "") == ["redis"]

def test_detect_with_pattern():
    assert detect_library_mentions("Build auth with PyJWT", "") == ["pyjwt"]

def test_no_false_positives():
    # Common words that aren't libraries
    assert detect_library_mentions("Fix the bug", "") == []
    assert detect_library_mentions("Add tests", "") == []
```

### Integration Tests (TASK-LKG-006)

```python
@pytest.mark.integration
def test_library_context_gathering():
    """Test end-to-end library detection and Context7 fetching."""
    task = {
        "title": "Implement search with graphiti-core",
        "description": "Create search functionality using the graphiti-core library"
    }

    # Detection
    libraries = detect_library_mentions(task["title"], task["description"])
    assert "graphiti-core" in libraries

    # Context7 resolution
    context = gather_library_context(libraries)
    assert context["graphiti-core"].import_statement is not None
    assert "search" in context["graphiti-core"].method_docs.lower()
```

## Rollback Plan

If issues arise:

1. **Phase 2.1 can be disabled** via flag: `--no-library-context`
2. **Graceful fallback**: If Context7 fails, continue with warning
3. **No breaking changes**: Existing workflows unaffected

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Stub reduction | >80% | Compare stub rate before/after |
| Detection accuracy | >90% | False positive/negative rate |
| Performance impact | <3s | Phase 2.1 execution time |
| User satisfaction | >80% | Approval rate at context display |
