---
id: TASK-LKG-004
title: Add library_context frontmatter field to task schema
status: completed
created: 2026-01-30
completed: 2026-01-30
priority: medium
complexity: 3
tags: [task-create, schema, frontmatter]
parent_review: TASK-REV-668B
feature_id: library-knowledge-gap
implementation_mode: task-work
wave: 2
conductor_workspace: library-knowledge-gap-wave2-schema
depends_on:
  - TASK-LKG-001
  - TASK-LKG-002
---

# TASK-LKG-004: Add library_context Frontmatter Field

## Description

Add an optional `library_context` field to task frontmatter that allows users to manually specify library API details. This is useful for internal/proprietary libraries not available in Context7, or when users want to provide specific API documentation.

## Acceptance Criteria

- [x] `library_context` field defined in task schema
- [x] Field is optional (tasks work without it)
- [x] Parsed in Phase 1.5 (Load Task Context)
- [x] Merged with Context7 results in Phase 2.1
- [x] Manual entries take precedence over Context7
- [x] Documentation updated in task-create.md
- [x] Unit tests for parsing

## Implementation Notes

### Schema Definition

```yaml
---
id: TASK-XXX
title: Migrate to graphiti-core library
library_context:
  - name: graphiti-core
    import: "from graphiti_core import Graphiti"
    initialization: |
      graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
      await graphiti.build_indices()
    key_methods:
      - name: search
        signature: "async def search(query: str, group_ids: List[str], num_results: int) -> List[Edge]"
        returns: "List of Edge objects with uuid, fact, name, created_at, score"
      - name: add_episode
        signature: "async def add_episode(name: str, body: str, group_id: str) -> EpisodeResult"
---
```

### Field Specification

```yaml
library_context:                    # Optional: Manual library API documentation
  type: array
  items:
    type: object
    required:
      - name
    properties:
      name:
        type: string
        description: Library/package name
      import:
        type: string
        description: Import statement(s)
      initialization:
        type: string
        description: Initialization code example
      key_methods:
        type: array
        items:
          type: object
          properties:
            name:
              type: string
            signature:
              type: string
            returns:
              type: string
```

### Parsing in Phase 1.5

```python
# In task-work Phase 1.5
def load_task_context(task_file: Path) -> dict:
    frontmatter = parse_frontmatter(task_file)

    task_context = {
        # ... existing fields ...
    }

    # Parse library_context if present
    if "library_context" in frontmatter:
        task_context["manual_library_context"] = parse_library_context(
            frontmatter["library_context"]
        )

    return task_context

def parse_library_context(raw: list) -> Dict[str, LibraryContext]:
    """Parse manual library_context from frontmatter."""
    contexts = {}
    for item in raw:
        ctx = LibraryContext(
            name=item["name"],
            context7_id=None,
            resolved=True,  # Manual = always resolved
            import_statement=item.get("import"),
            initialization=item.get("initialization"),
            key_methods=[m["name"] for m in item.get("key_methods", [])],
            method_docs=format_method_docs(item.get("key_methods", [])),
            source="manual"  # Track source
        )
        contexts[item["name"]] = ctx
    return contexts
```

### Merge with Context7 in Phase 2.1

```python
def gather_library_context(
    libraries: List[str],
    manual_context: Optional[Dict[str, LibraryContext]] = None,
    token_budget: int = 5000
) -> Dict[str, LibraryContext]:
    """
    Gather library context, preferring manual over Context7.

    Priority:
    1. Manual library_context (from frontmatter)
    2. Context7 fetched documentation
    """
    contexts = {}

    for lib_name in libraries:
        # Check manual context first
        if manual_context and lib_name in manual_context:
            contexts[lib_name] = manual_context[lib_name]
            continue

        # Fall back to Context7
        contexts[lib_name] = fetch_from_context7(lib_name, token_budget)

    return contexts
```

### Documentation Update (task-create.md)

Add to Task Structure section:

```markdown
### Extended Fields (Optional)

```yaml
library_context:                    # Manual library API documentation
  - name: graphiti-core
    import: "from graphiti_core import Graphiti"
    initialization: |
      graphiti = Graphiti(uri, user, pass)
      await graphiti.build_indices()
    key_methods:
      - name: search
        signature: "async def search(...) -> List[Edge]"
        returns: "List of Edge objects"
```

**Use when**:
- Library not available in Context7
- Internal/proprietary libraries
- Specific version documentation needed
- Override Context7 with custom docs
```

## Test Cases

```python
def test_parse_library_context_minimal():
    """Test parsing minimal library_context."""
    raw = [{"name": "mylib"}]
    result = parse_library_context(raw)
    assert "mylib" in result
    assert result["mylib"].resolved

def test_parse_library_context_full():
    """Test parsing full library_context."""
    raw = [{
        "name": "graphiti-core",
        "import": "from graphiti_core import Graphiti",
        "initialization": "g = Graphiti(...)",
        "key_methods": [
            {"name": "search", "signature": "...", "returns": "List[Edge]"}
        ]
    }]
    result = parse_library_context(raw)
    assert result["graphiti-core"].import_statement == "from graphiti_core import Graphiti"
    assert "search" in result["graphiti-core"].key_methods

def test_manual_takes_precedence():
    """Test that manual context overrides Context7."""
    manual = {"fastapi": LibraryContext(name="fastapi", resolved=True, source="manual")}
    result = gather_library_context(["fastapi"], manual_context=manual)
    assert result["fastapi"].source == "manual"
```

## Notes

- This provides a manual override when Context7 is insufficient
- Useful for internal libraries, pre-release APIs, or custom documentation
- Does not replace automatic detection - complements it
