---
id: TASK-049
title: Implement external ID mapper for PM tools
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: high
tags: [infrastructure, hash-ids, pm-tools, integration]
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement external ID mapper for PM tools

## Description

Create a bidirectional mapping system between internal hash-based task IDs and external sequential IDs used by PM tools (JIRA, Azure DevOps, Linear, GitHub). This enables Taskwright to use collision-free hash IDs internally while PM tools see their preferred sequential formats.

## Acceptance Criteria

- [ ] Map internal hash ID to external sequential IDs per PM tool
- [ ] Support JIRA format: `{project_key}-{number}` (e.g., PROJ-456)
- [ ] Support Azure DevOps format: `{number}` (e.g., 1234)
- [ ] Support Linear format: `{team}-{number}` (e.g., TEAM-789)
- [ ] Support GitHub format: `#{number}` (e.g., #234)
- [ ] Bidirectional lookup: internal ↔ external
- [ ] Thread-safe counter increment per tool
- [ ] Auto-generate external ID on first export to tool
- [ ] Store mapping persistently (handled by TASK-050)

## Test Requirements

- [ ] Unit tests for mapping internal → external (all 4 tools)
- [ ] Unit tests for reverse lookup external → internal
- [ ] Unit tests for counter increment (sequential)
- [ ] Concurrency tests (10 simultaneous mappings)
- [ ] Integration tests with actual PM tool formats
- [ ] Test coverage ≥85%

## Implementation Notes

### File Location
Create new file: `installer/global/lib/external_id_mapper.py`

### Key Functions
```python
def map_to_external(
    internal_id: str,
    tool: str,
    project_key: str = "PROJ"
) -> str:
    """Map internal hash ID to external sequential ID."""

def get_internal_id(external_id: str, tool: str) -> Optional[str]:
    """Reverse lookup: external ID → internal ID."""

def increment_counter(tool: str) -> int:
    """Get next sequential number for PM tool."""

def get_all_mappings(internal_id: str) -> Dict[str, str]:
    """Get all external IDs for an internal ID."""
```

### Mapping Data Structure
```python
{
  "TASK-E01-b2c4": {
    "jira": "PROJ-456",
    "azure_devops": "1234",
    "linear": "TEAM-789",
    "github": "234",
    "created": "2025-01-08T10:00:00Z",
    "epic": "EPIC-001"  # Optional context
  },
  "TASK-DOC-f1a3": {
    "jira": "PROJ-457",
    "azure_devops": "1235",
    "created": "2025-01-08T10:05:00Z"
  }
}
```

### Counter Management
```python
# Per-tool counters stored separately
{
  "jira": {
    "PROJ": 457,  # Next: PROJ-457
    "TEST": 12    # Next: TEST-12
  },
  "azure_devops": 1235,  # Next: 1235
  "linear": {
    "TEAM": 789,
    "DESIGN": 45
  },
  "github": 234
}
```

### Tool Format Specifications

**JIRA**:
- Format: `{PROJECT_KEY}-{number}`
- Example: `PROJ-456`
- Counter: Per-project sequential

**Azure DevOps**:
- Format: `{number}`
- Example: `1234`
- Counter: Global sequential integer

**Linear**:
- Format: `{TEAM_KEY}-{number}`
- Example: `TEAM-789`
- Counter: Per-team sequential

**GitHub**:
- Format: `#{number}`
- Example: `#234`
- Counter: Per-repository sequential

### Thread Safety
Use locks for counter increment:
```python
import threading

_counter_lock = threading.Lock()

def increment_counter(tool: str, key: str = None) -> int:
    with _counter_lock:
        # Read, increment, write atomically
        pass
```

## Dependencies

- TASK-046: Hash ID generator (for format understanding)

## Related Tasks

- TASK-050: JSON persistence for mappings
- TASK-051: Update task frontmatter schema
- TASK-048: /task-create integration

## Test Execution Log

[Automatically populated by /task-work]
