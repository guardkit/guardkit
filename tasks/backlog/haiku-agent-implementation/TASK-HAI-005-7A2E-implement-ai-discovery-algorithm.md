---
id: TASK-HAI-005-7A2E
title: Implement AI Discovery Algorithm
status: backlog
priority: high
tags: [haiku-agents, discovery, algorithm, ai-matching, implementation]
epic: haiku-agent-implementation
complexity: 6
estimated_hours: 3
dependencies: [TASK-HAI-001, TASK-HAI-002, TASK-HAI-003, TASK-HAI-004]
blocks: [TASK-HAI-006]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Implement AI Discovery Algorithm

## Context

Create AI-powered agent discovery system that matches task context to appropriate specialist agents using metadata (stack, phase, capabilities, keywords). This replaces hardcoded mappings with intelligent discovery, maintaining Taskwright's AI-first philosophy.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 2 (Discovery System)
**Method**: `/task-work` (complex logic, needs quality gates)
**Workspace**: WS-D (Conductor workspace)

## Objectives

1. Create `installer/global/commands/lib/agent_discovery.py`
2. Implement metadata-based agent scanning and matching
3. Add graceful degradation (handle agents without metadata)
4. Support multi-stack matching and phase filtering
5. Include comprehensive unit tests (>90% coverage)

## Algorithm Specification

### Core Function Signature

```python
def discover_agents(
    phase: str,
    stack: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    min_capability_match: int = 1
) -> List[Dict[str, Any]]:
    """
    Discover agents matching criteria using metadata.

    Args:
        phase: Required phase (implementation/review/testing/orchestration)
        stack: Optional stack filter (python, react, dotnet, etc.)
        keywords: Optional keyword matching for capabilities
        min_capability_match: Minimum number of keyword matches required

    Returns:
        List of matching agents with metadata, sorted by relevance
    """
```

### Matching Logic

**Phase 1: Scan All Agents**
```python
# Scan both locations
agents = []
agents.extend(glob.glob("~/.agentecflow/agents/*.md"))
agents.extend(glob.glob("installer/global/agents/*.md"))
agents.extend(glob.glob("installer/global/templates/*/agents/*.md"))
```

**Phase 2: Extract Metadata**
```python
import frontmatter

for agent_path in agents:
    with open(agent_path) as f:
        agent = frontmatter.loads(f.read())
        if 'phase' not in agent.metadata:
            continue  # Graceful degradation: skip agents without metadata

        # Extract discovery fields
        metadata = {
            'name': agent.metadata.get('name'),
            'stack': agent.metadata.get('stack', []),
            'phase': agent.metadata.get('phase'),
            'capabilities': agent.metadata.get('capabilities', []),
            'keywords': agent.metadata.get('keywords', []),
            'path': agent_path
        }
```

**Phase 3: Apply Filters**
```python
# Filter by phase (required)
if metadata['phase'] != phase:
    continue

# Filter by stack (optional)
if stack and not any(s in metadata['stack'] for s in stack):
    continue

# Score by keyword relevance (optional)
if keywords:
    matches = sum(1 for k in keywords if k in metadata['keywords'])
    if matches < min_capability_match:
        continue
    metadata['relevance_score'] = matches
```

**Phase 4: Sort and Return**
```python
# Sort by relevance score (highest first)
results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
return results
```

### Graceful Degradation Strategy

**Agents WITHOUT metadata**:
- Skip during discovery (no error thrown)
- System continues to work with partial agent pool
- Log warning for tracking migration progress

**No agents found**:
- Return empty list (no exception)
- Caller decides fallback strategy (e.g., use task-manager)
- User-friendly message: "No specialist found, using general agent"

**Partial matches**:
- Phase match required (strict filter)
- Stack match optional (broader search if no exact match)
- Keyword scoring allows ranked results

## Acceptance Criteria

- [ ] Module created at `installer/global/commands/lib/agent_discovery.py`
- [ ] `discover_agents()` function implements 4-phase algorithm
- [ ] Graceful degradation: skips agents without `phase` field
- [ ] Multi-location scanning: global + template agents
- [ ] Stack filtering: handles single and multi-stack agents
- [ ] Keyword scoring: relevance-based ranking
- [ ] Edge cases handled: empty results, no metadata, invalid paths
- [ ] Unit tests: >90% coverage, 15+ test cases
- [ ] Integration test: discovers HAI-002, HAI-003, HAI-004 agents

## Testing Strategy

### Unit Tests (15+ test cases)

**Test File**: `tests/test_agent_discovery.py`

```python
import pytest
from installer.global.commands.lib.agent_discovery import discover_agents

def test_discover_by_phase_only():
    """Should find all implementation agents"""
    results = discover_agents(phase='implementation')
    assert len(results) >= 3  # At minimum: Python, React, .NET
    assert all(r['phase'] == 'implementation' for r in results)

def test_discover_by_stack():
    """Should filter by stack"""
    results = discover_agents(phase='implementation', stack=['python'])
    assert len(results) >= 1
    assert all('python' in r['stack'] for r in results)

def test_discover_multi_stack():
    """Should handle multi-stack agents"""
    results = discover_agents(phase='implementation', stack=['react', 'typescript'])
    react_agent = next(r for r in results if 'react' in r['stack'])
    assert 'typescript' in react_agent['stack']

def test_keyword_scoring():
    """Should rank by keyword relevance"""
    results = discover_agents(
        phase='implementation',
        stack=['python'],
        keywords=['fastapi', 'async', 'endpoints']
    )
    assert results[0]['relevance_score'] >= 2  # Python agent has 3+ matches

def test_graceful_degradation_no_metadata():
    """Should skip agents without phase field"""
    # Create temp agent without metadata
    # Verify it's skipped without error
    results = discover_agents(phase='implementation')
    # Should succeed even if some agents lack metadata

def test_no_agents_found():
    """Should return empty list if no matches"""
    results = discover_agents(phase='nonexistent-phase')
    assert results == []

def test_handles_invalid_paths():
    """Should skip agents with read errors"""
    # Simulate permission error or missing file
    # Verify graceful handling

def test_cross_stack_agent():
    """Should find cross-stack agents"""
    results = discover_agents(phase='implementation', stack=['cross-stack'])
    # database-specialist, devops-specialist, security-specialist

def test_template_agent_discovery():
    """Should find template-specific agents"""
    results = discover_agents(phase='implementation', stack=['react'])
    template_agents = [r for r in results if 'templates/' in r['path']]
    assert len(template_agents) >= 3  # react-query, form-validation, feature-arch

def test_min_capability_threshold():
    """Should respect min_capability_match parameter"""
    results = discover_agents(
        phase='implementation',
        keywords=['fastapi', 'async'],
        min_capability_match=2
    )
    assert all(r['relevance_score'] >= 2 for r in results)

# Additional tests:
# - test_duplicate_agents_handled()
# - test_case_insensitive_matching()
# - test_empty_stack_list()
# - test_phase_enum_validation()
# - test_scanning_performance()
```

### Integration Test

**Test File**: `tests/integration/test_discovery_integration.py`

```python
def test_discover_haiku_agents():
    """Verify HAI-002, HAI-003, HAI-004 are discoverable"""
    results = discover_agents(phase='implementation')

    agent_names = [r['name'] for r in results]
    assert 'python-api-specialist' in agent_names
    assert 'react-state-specialist' in agent_names
    assert 'dotnet-domain-specialist' in agent_names

    # Verify metadata completeness
    python_agent = next(r for r in results if r['name'] == 'python-api-specialist')
    assert 'python' in python_agent['stack']
    assert len(python_agent['keywords']) >= 5
    assert len(python_agent['capabilities']) >= 5
```

### Performance Test

```python
def test_discovery_performance():
    """Should scan 30+ agents in <500ms"""
    import time
    start = time.time()
    results = discover_agents(phase='implementation')
    duration = time.time() - start

    assert duration < 0.5  # 500ms max
    assert len(results) >= 10  # Should find multiple agents
```

## Implementation Notes

### Dependencies

```python
# requirements.txt
frontmatter>=1.0.0  # YAML frontmatter parsing
pytest>=7.0.0       # Testing
pytest-cov>=4.0.0   # Coverage reporting
```

### Error Handling

```python
def discover_agents(phase, stack=None, keywords=None, min_capability_match=1):
    results = []

    try:
        agent_paths = _scan_agent_locations()
    except Exception as e:
        logger.error(f"Failed to scan agent locations: {e}")
        return []  # Graceful degradation

    for path in agent_paths:
        try:
            metadata = _extract_metadata(path)
            if _matches_criteria(metadata, phase, stack, keywords, min_capability_match):
                results.append(metadata)
        except Exception as e:
            logger.warning(f"Skipping agent {path}: {e}")
            continue  # Skip problematic agents, don't fail entire discovery

    return _sort_by_relevance(results)
```

### Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Log discovery activity for debugging
logger.info(f"Discovery: phase={phase}, stack={stack}, found {len(results)} agents")
logger.debug(f"Matched agents: {[r['name'] for r in results]}")
logger.warning(f"Skipped {skipped_count} agents without metadata")
```

## Risk Assessment

**MEDIUM Risk**:
- Complex matching logic (keyword scoring, multi-stack)
- Edge cases (no metadata, empty results, invalid files)
- Performance with 30+ agents to scan

**Mitigations**:
- Use `/task-work` (Phases 2.5, 4.5, 5.5 quality gates)
- Comprehensive unit tests (>90% coverage)
- Graceful degradation ensures no breakage
- Performance test enforces <500ms constraint

## Rollback Strategy

**If discovery fails**:
```bash
# Revert the module
rm installer/global/commands/lib/agent_discovery.py

# Phase 3 integration (HAI-006) not yet merged
# System continues using task-manager as before
```

**Recovery Time**: <2 minutes

## Reference Materials

- `installer/global/commands/lib/phase_execution.py` - Phase 3 orchestration
- `installer/global/agents/*.md` - Global agent examples
- `installer/global/templates/*/agents/*.md` - Template agent examples
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema specification

## Deliverables

1. Module: `installer/global/commands/lib/agent_discovery.py`
2. Tests: `tests/test_agent_discovery.py` (>90% coverage)
3. Integration test: `tests/integration/test_discovery_integration.py`
4. Performance validated: <500ms for 30+ agents
5. Documentation: Inline docstrings + usage examples

## Success Metrics

- Unit test coverage: >90%
- Integration test: Discovers all 3 new Haiku agents
- Performance: <500ms discovery time
- Graceful degradation: Zero errors with mixed agent pool
- Code review: SOLID compliance >70/100

## Risk: MEDIUM | Rollback: Delete module (<2 min)
