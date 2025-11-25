---
id: TASK-HAI-013-D7A2
title: Update react-fastapi-monorepo Template Agents with Discovery Metadata
status: completed
priority: medium
tags: [haiku-agents, metadata, template-agents, monorepo, react, fastapi]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
actual_hours: 0.5
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T16:52:00Z
completed_at: 2025-11-25T16:52:00Z
completion_metrics:
  agents_updated: 3
  validation_passed: true
  discovery_working: true
  content_preserved: true
  yaml_valid: true
  acceptance_criteria_met: 8/8
---

# Task: Update react-fastapi-monorepo Template Agents with Discovery Metadata

## Context

Add discovery metadata to 3 agents in the react-fastapi-monorepo template. These agents specialize in monorepo-specific concerns (type safety across frontend/backend, Docker orchestration) which are distinct from single-stack patterns.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-010-012, HAI-014)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-H (Conductor workspace - parallel with other template updates)

## Objectives

1. Add discovery metadata to 3 react-fastapi-monorepo agents
2. Validate metadata against HAI-001 schema
3. Ensure distinct specializations for monorepo patterns
4. Preserve all existing content

## Agents to Update

### 1. react-fastapi-monorepo-specialist.md

**Location**: `installer/global/templates/react-fastapi-monorepo/agents/`

**Metadata**:
```yaml
---
name: react-fastapi-monorepo-specialist
description: React + FastAPI monorepo structure and coordination specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Monorepo coordination follows established patterns (workspace management, shared configs, build orchestration). Haiku provides fast, cost-effective implementation of monorepo conventions."

# Discovery metadata
stack: [react, typescript, python, fastapi]
phase: implementation
capabilities:
  - Monorepo workspace structure (frontend/backend)
  - Shared configuration management
  - Cross-workspace dependencies
  - Build orchestration
  - Development environment setup
keywords: [monorepo, workspace, react, fastapi, full-stack, build-orchestration, shared-config]

collaborates_with:
  - monorepo-type-safety-specialist
  - docker-orchestration-specialist
  - react-state-specialist
  - python-api-specialist
---
```

**Specialization**: Monorepo structure and cross-workspace coordination

### 2. monorepo-type-safety-specialist.md

**Location**: `installer/global/templates/react-fastapi-monorepo/agents/`

**Metadata**:
```yaml
---
name: monorepo-type-safety-specialist
description: Cross-stack type safety specialist (Pydantic → TypeScript)
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Type generation follows schema-first patterns (Pydantic models → TypeScript types via openapi-typescript). Haiku provides fast, cost-effective type sync implementation."

# Discovery metadata
stack: [react, typescript, python, fastapi]
phase: implementation
capabilities:
  - OpenAPI schema generation from Pydantic
  - TypeScript type generation from OpenAPI
  - Type sync automation
  - Frontend/backend contract validation
  - Shared type definitions
keywords: [type-safety, pydantic, typescript, openapi, schema, type-generation, contract]

collaborates_with:
  - react-fastapi-monorepo-specialist
  - python-api-specialist
  - react-state-specialist
---
```

**Specialization**: Cross-stack type safety (Pydantic ↔ TypeScript)

### 3. docker-orchestration-specialist.md

**Location**: `installer/global/templates/react-fastapi-monorepo/agents/`

**Metadata**:
```yaml
---
name: docker-orchestration-specialist
description: Docker Compose orchestration for monorepo services specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Docker orchestration follows Compose patterns (multi-service setup, networking, volumes). Haiku provides fast, cost-effective Docker configuration. Security reviews handled by security-specialist."

# Discovery metadata
stack: [docker, cross-stack]
phase: implementation
capabilities:
  - Docker Compose multi-service setup
  - Service networking and communication
  - Volume management
  - Environment configuration
  - Development vs production configs
keywords: [docker, docker-compose, orchestration, containers, multi-service, networking]

collaborates_with:
  - react-fastapi-monorepo-specialist
  - devops-specialist
---
```

**Specialization**: Docker Compose for monorepo (frontend + backend + database)

## Specialization Strategy

### Global vs Template Agents

**Global agents**:
- **react-state-specialist**: React patterns only
- **python-api-specialist**: Python API patterns only
- **devops-specialist**: General infrastructure

**Template-specific specialists**:
- **react-fastapi-monorepo-specialist**: Monorepo structure (broader, coordinates both stacks)
- **monorepo-type-safety-specialist**: Type sync between React/FastAPI (unique to monorepo)
- **docker-orchestration-specialist**: Multi-service Docker setup (monorepo-specific)

**Discovery behavior**:
- Task keywords "type-safety", "schema", "pydantic", "openapi" → monorepo-type-safety-specialist
- Task keywords "docker", "compose", "orchestration" → docker-orchestration-specialist
- Task keywords "monorepo", "workspace", "build" → react-fastapi-monorepo-specialist
- Default monorepo task → react-fastapi-monorepo-specialist (coordination)

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
with open('installer/global/templates/react-fastapi-monorepo/agents/react-fastapi-monorepo-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert 'react' in agent.metadata['stack']
    assert 'python' in agent.metadata['stack'] or 'fastapi' in agent.metadata['stack']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    print('✅ react-fastapi-monorepo-specialist validated')
"
```

**Discovery validation**:
```python
from installer.global.commands.lib.agent_discovery import discover_agents

# Test multi-stack discovery
agents = discover_agents(phase='implementation', stack=['react', 'python'])
names = [a['name'] for a in agents]

assert 'react-fastapi-monorepo-specialist' in names
assert 'monorepo-type-safety-specialist' in names

# Test Docker stack
docker_agents = discover_agents(phase='implementation', stack=['docker'])
docker_names = [a['name'] for a in docker_agents]
assert 'docker-orchestration-specialist' in docker_names

print('✅ All 3 react-fastapi-monorepo agents discoverable')
```

## Acceptance Criteria

- [ ] 3 agents updated with discovery metadata
- [ ] Stack: Multi-stack for monorepo/type-safety, docker+cross-stack for orchestration
- [ ] Phase: implementation for all
- [ ] Capabilities: Minimum 5 per agent
- [ ] Keywords: Minimum 5 per agent, distinct monorepo specializations
- [ ] Model: haiku with clear rationale
- [ ] All existing content preserved
- [ ] YAML syntax valid
- [ ] Discovery finds all 3 agents with appropriate stack filters
- [ ] Specializations distinct (structure vs type-safety vs Docker)

## Testing

```bash
# Validate metadata
python3 scripts/validate_template_agents.py react-fastapi-monorepo

# Test discovery
pytest tests/test_agent_discovery.py::test_monorepo_template_agents -v

# Verify no content changes
git diff --stat installer/global/templates/react-fastapi-monorepo/agents/
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
git checkout installer/global/templates/react-fastapi-monorepo/agents/
```

**Recovery Time**: <30 seconds

## Reference Materials

- `installer/global/templates/react-fastapi-monorepo/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-002-B47C-create-python-api-specialist.md` - Global Python agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-003-45BB-create-react-state-specialist.md` - Global React agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema

## Deliverables

1. Updated: 3 react-fastapi-monorepo template agents
2. Validation: All 3 agents pass schema validation
3. Discovery: All 3 agents found by discovery algorithm
4. Specializations: Distinct keyword sets for monorepo patterns

## Success Metrics

- Validation: 3/3 agents pass (100%)
- Discovery: Multi-stack agents found with both react+python filters
- Keyword targeting: Type safety tasks → monorepo-type-safety-specialist
- Zero disruption: No content changes

## Risk: LOW | Rollback: Revert files (<30 sec)
