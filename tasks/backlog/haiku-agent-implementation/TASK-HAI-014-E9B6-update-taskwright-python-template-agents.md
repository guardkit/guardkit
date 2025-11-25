---
id: TASK-HAI-014-E9B6
title: Update taskwright-python Template Agents with Discovery Metadata
status: backlog
priority: medium
tags: [haiku-agents, metadata, template-agents, python, cli]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Update taskwright-python Template Agents with Discovery Metadata

## Context

Add discovery metadata to 3 agents in the taskwright-python template. These agents specialize in Python CLI patterns, orchestrator architecture, and testing strategies unique to Taskwright's own codebase (16K LOC dogfooding).

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-010-013)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-H (Conductor workspace - parallel with other template updates)

## Objectives

1. Add discovery metadata to 3 taskwright-python agents
2. Validate metadata against HAI-001 schema
3. Ensure distinct specializations for CLI/orchestrator patterns
4. Preserve all existing content

## Agents to Update

### 1. python-cli-specialist.md

**Location**: `installer/global/templates/taskwright-python/agents/`

**Metadata**:
```yaml
---
name: python-cli-specialist
description: Python CLI development specialist (Click, Typer, argparse)
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "CLI implementation follows established patterns (Click/Typer commands, argparse). Haiku provides fast, cost-effective implementation of command-line interfaces."

# Discovery metadata
stack: [python, cli]
phase: implementation
capabilities:
  - Click/Typer command structure
  - Argument parsing and validation
  - Command group organization
  - Interactive prompts
  - Output formatting (rich, colorama)
keywords: [python, cli, click, typer, argparse, command-line, terminal]

collaborates_with:
  - python-architecture-specialist
  - python-testing-specialist
  - python-api-specialist
---
```

**Specialization**: Python CLI frameworks and command-line interfaces

### 2. python-architecture-specialist.md

**Location**: `installer/global/templates/taskwright-python/agents/`

**Metadata**:
```yaml
---
name: python-architecture-specialist
description: Python orchestrator pattern and complex workflow specialist
tools: [Read, Write, Edit, Bash, Grep]
model: sonnet
model_rationale: "Orchestrator architecture requires complex workflow coordination, state management, and multi-phase orchestration. Sonnet's reasoning ensures correct phase transitions and error handling patterns."

# Discovery metadata
stack: [python, cli]
phase: implementation
capabilities:
  - Orchestrator pattern implementation
  - Complex workflow coordination
  - State management strategies
  - Phase-based execution patterns
  - Error recovery and rollback logic
keywords: [python, orchestrator, workflow, state-management, phases, architecture, coordination]

collaborates_with:
  - python-cli-specialist
  - python-testing-specialist
  - architectural-reviewer
---
```

**Specialization**: Orchestrator patterns (like Taskwright's own phase-based workflow)

### 3. python-testing-specialist.md

**Location**: `installer/global/templates/taskwright-python/agents/`

**Metadata**:
```yaml
---
name: python-testing-specialist
description: Python testing specialist (pytest, coverage, mocking)
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Python testing follows pytest patterns (fixtures, parametrize, mocking). Haiku provides fast, cost-effective test implementation. Test quality validated by Phase 4.5 enforcement."

# Discovery metadata
stack: [python, cli]
phase: testing
capabilities:
  - Pytest test design
  - Fixture design and management
  - Parametrized testing
  - Mock/patch strategies
  - Coverage optimization
keywords: [python, pytest, testing, fixtures, mocking, coverage, unit-tests]

collaborates_with:
  - python-cli-specialist
  - python-architecture-specialist
  - test-orchestrator
---
```

**Specialization**: Python testing with pytest (CLI and orchestrator testing)

## Specialization Strategy

### Global vs Template Agents

**Global python-api-specialist**:
- FastAPI endpoint implementation
- Async/await patterns
- Pydantic schemas

**Template-specific specialists**:
- **python-cli-specialist**: Click/Typer command-line interfaces (not API)
- **python-architecture-specialist**: Orchestrator patterns (Sonnet for complexity)
- **python-testing-specialist**: pytest patterns for CLI/orchestrator testing

**Discovery behavior**:
- Task keywords "click", "typer", "cli", "command" → python-cli-specialist
- Task keywords "orchestrator", "workflow", "phases" → python-architecture-specialist
- Task keywords "pytest", "test", "fixture", "mock" → python-testing-specialist
- Default Python task → python-api-specialist (global fallback)

**Note**: python-architecture-specialist uses **Sonnet** (not Haiku) because orchestrator patterns require complex reasoning about state management and workflow coordination.

## Implementation Procedure

**For each agent**:

1. Read existing file
2. Add discovery metadata to frontmatter
3. Preserve all existing content
4. Validate YAML syntax
5. Test discovery matching

## Validation

**Per-agent validation**:
```python
python3 -c "
import frontmatter
with open('installer/global/templates/taskwright-python/agents/python-cli-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['python', 'cli']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    print('✅ python-cli-specialist validated')
"

# Validate architecture specialist uses Sonnet
python3 -c "
import frontmatter
with open('installer/global/templates/taskwright-python/agents/python-architecture-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['model'] == 'sonnet'
    print('✅ python-architecture-specialist uses Sonnet')
"
```

**Discovery validation**:
```python
from installer.global.commands.lib.agent_discovery import discover_agents

# Test Python CLI agents
impl_agents = discover_agents(phase='implementation', stack=['python', 'cli'])
names = [a['name'] for a in impl_agents]
assert 'python-cli-specialist' in names
assert 'python-architecture-specialist' in names

# Test testing agents
test_agents = discover_agents(phase='testing', stack=['python'])
names = [a['name'] for a in test_agents]
assert 'python-testing-specialist' in names

print('✅ All 3 taskwright-python agents discoverable')
```

## Acceptance Criteria

- [ ] 3 agents updated with discovery metadata
- [ ] Stack: [python, cli] for all
- [ ] Phase: implementation (2), testing (1)
- [ ] Capabilities: Minimum 5 per agent
- [ ] Keywords: Minimum 5 per agent, distinct CLI/orchestrator specializations
- [ ] Model: haiku (2), sonnet (1 - architecture specialist)
- [ ] All existing content preserved
- [ ] YAML syntax valid
- [ ] Discovery finds all 3 agents
- [ ] Specializations distinct from global python-api-specialist

## Testing

```bash
# Validate metadata
python3 scripts/validate_template_agents.py taskwright-python

# Test discovery
pytest tests/test_agent_discovery.py::test_taskwright_python_template_agents -v

# Verify no content changes
git diff --stat installer/global/templates/taskwright-python/agents/
```

## Risk Assessment

**LOW Risk**:
- Simple metadata addition (3 files)
- Template agents, not global (lower impact)
- Validation script catches errors

**Mitigations**:
- Batch validation after all updates
- Git diff review
- Discovery test ensures matching works

## Rollback Strategy

```bash
# Revert template agent changes
git checkout installer/global/templates/taskwright-python/agents/
```

**Recovery Time**: <30 seconds

## Reference Materials

- `installer/global/templates/taskwright-python/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-002-B47C-create-python-api-specialist.md` - Global Python agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema
- Taskwright's own 16K LOC codebase - Real-world orchestrator patterns

## Deliverables

1. Updated: 3 taskwright-python template agents
2. Validation: All 3 agents pass schema validation
3. Discovery: All 3 agents found by discovery algorithm
4. Specializations: Distinct keyword sets for CLI/orchestrator patterns
5. Model selection: 2 Haiku + 1 Sonnet (architecture specialist)

## Success Metrics

- Validation: 3/3 agents pass (100%)
- Discovery: 2 found with phase=implementation, 1 with phase=testing
- Model selection: Architecture specialist correctly uses Sonnet
- Keyword targeting: CLI tasks → python-cli-specialist
- Zero disruption: No content changes

## Risk: LOW | Rollback: Revert files (<30 sec)
