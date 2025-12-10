---
id: TASK-HAI-011-B23E
title: Update fastapi-python Template Agents with Discovery Metadata
status: backlog
priority: medium
tags: [haiku-agents, metadata, template-agents, python, fastapi]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Update fastapi-python Template Agents with Discovery Metadata

## Context

Add discovery metadata to 3 agents in the fastapi-python template. These agents are template-specific specialists that complement the global python-api-specialist with narrower focuses (database, testing).

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-010, HAI-012-014)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-G (Conductor workspace - parallel with HAI-009, HAI-010)

## Objectives

1. Add discovery metadata to 3 fastapi-python agents
2. Validate metadata against HAI-001 schema
3. Ensure distinct specializations from global python-api-specialist
4. Preserve all existing content

## Agents to Update

### 1. fastapi-specialist.md

**Location**: `installer/core/templates/fastapi-python/agents/`

**Metadata**:
```yaml
---
name: fastapi-specialist
description: FastAPI framework specialist for API development
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "FastAPI implementation follows established patterns (routers, dependencies, middleware). Haiku provides fast, cost-effective implementation following FastAPI best practices."

# Discovery metadata
stack: [python, fastapi]
phase: implementation
capabilities:
  - FastAPI router organization
  - Dependency injection patterns
  - Middleware implementation
  - Background tasks
  - WebSocket support
keywords: [fastapi, python, api, router, middleware, websocket, background-tasks]

collaborates_with:
  - python-api-specialist
  - fastapi-database-specialist
  - fastapi-testing-specialist
---
```

**Specialization**: FastAPI framework-specific patterns (routers, middleware, background tasks)

### 2. fastapi-database-specialist.md

**Location**: `installer/core/templates/fastapi-python/agents/`

**Metadata**:
```yaml
---
name: fastapi-database-specialist
description: FastAPI database integration specialist (SQLAlchemy, Alembic)
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Database integration follows SQLAlchemy patterns (models, migrations, sessions). Haiku provides fast, cost-effective implementation. Complex query optimization escalated to database-specialist."

# Discovery metadata
stack: [python, fastapi]
phase: implementation
capabilities:
  - SQLAlchemy model design
  - Alembic migrations
  - Database session management
  - Repository pattern implementation
  - FastAPI-specific DB integration
keywords: [fastapi, sqlalchemy, alembic, database, migration, orm, repository]

collaborates_with:
  - fastapi-specialist
  - database-specialist
  - python-api-specialist
---
```

**Specialization**: FastAPI + SQLAlchemy integration (narrower than general DB or API)

### 3. fastapi-testing-specialist.md

**Location**: `installer/core/templates/fastapi-python/agents/`

**Metadata**:
```yaml
---
name: fastapi-testing-specialist
description: FastAPI testing specialist (pytest, TestClient)
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "FastAPI testing follows pytest patterns with TestClient. Haiku provides fast, cost-effective test implementation. Test quality validated by Phase 4.5 enforcement."

# Discovery metadata
stack: [python, fastapi]
phase: testing
capabilities:
  - FastAPI TestClient usage
  - Pytest fixture design for FastAPI
  - API endpoint testing
  - Database mocking for tests
  - Async test patterns
keywords: [fastapi, pytest, testing, testclient, api-testing, fixtures, async-tests]

collaborates_with:
  - fastapi-specialist
  - test-orchestrator
  - test-verifier
---
```

**Specialization**: FastAPI-specific testing patterns (TestClient, async tests)

## Specialization Strategy

### Global vs Template Agents

**Global python-api-specialist**:
- General Python API patterns
- Async/await handling
- Pydantic schemas
- Broad endpoint implementation

**Template-specific specialists**:
- **fastapi-specialist**: FastAPI framework specifics (routers, middleware)
- **fastapi-database-specialist**: SQLAlchemy + FastAPI integration
- **fastapi-testing-specialist**: FastAPI TestClient patterns (phase=testing)

**Discovery behavior**:
- Task keywords "sqlalchemy", "migration", "database" → fastapi-database-specialist
- Task keywords "test", "testclient", "pytest" → fastapi-testing-specialist
- Task keywords "router", "middleware" → fastapi-specialist
- Default Python API task → python-api-specialist (global fallback)

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
with open('installer/core/templates/fastapi-python/agents/fastapi-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['python', 'fastapi']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    print('✅ fastapi-specialist validated')
"
```

**Discovery validation**:
```python
from installer.core.commands.lib.agent_discovery import discover_agents

# Test implementation agents
impl_agents = discover_agents(phase='implementation', stack=['python', 'fastapi'])
names = [a['name'] for a in impl_agents]
assert 'fastapi-specialist' in names
assert 'fastapi-database-specialist' in names

# Test testing agents
test_agents = discover_agents(phase='testing', stack=['python', 'fastapi'])
names = [a['name'] for a in test_agents]
assert 'fastapi-testing-specialist' in names

print('✅ All 3 fastapi-python agents discoverable')
```

## Acceptance Criteria

- [ ] 3 agents updated with discovery metadata
- [ ] Stack: [python, fastapi] for all
- [ ] Phase: implementation (2), testing (1)
- [ ] Capabilities: Minimum 5 per agent
- [ ] Keywords: Minimum 5 per agent, distinct specializations
- [ ] Model: haiku with clear rationale
- [ ] All existing content preserved
- [ ] YAML syntax valid
- [ ] Discovery finds all 3 agents
- [ ] Specializations distinct from global python-api-specialist

## Testing

```bash
# Validate metadata
python3 scripts/validate_template_agents.py fastapi-python

# Test discovery
pytest tests/test_agent_discovery.py::test_fastapi_template_agents -v

# Verify no content changes
git diff --stat installer/core/templates/fastapi-python/agents/
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
git checkout installer/core/templates/fastapi-python/agents/
```

**Recovery Time**: <30 seconds

## Reference Materials

- `installer/core/templates/fastapi-python/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-002-B47C-create-python-api-specialist.md` - Global Python agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema

## Deliverables

1. Updated: 3 fastapi-python template agents
2. Validation: All 3 agents pass schema validation
3. Discovery: All 3 agents found by discovery algorithm
4. Specializations: Distinct keyword sets for targeted matching

## Success Metrics

- Validation: 3/3 agents pass (100%)
- Discovery: 2 found with phase=implementation, 1 with phase=testing
- Keyword targeting: Database tasks → fastapi-database-specialist
- Zero disruption: No content changes

## Risk: LOW | Rollback: Revert files (<30 sec)
