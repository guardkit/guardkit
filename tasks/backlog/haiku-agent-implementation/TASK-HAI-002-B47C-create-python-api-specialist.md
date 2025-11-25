---
id: TASK-HAI-002-B47C
title: Create Python API Specialist Agent
status: backlog
priority: high
tags: [haiku-agents, python, implementation, agent-creation]
epic: haiku-agent-implementation
complexity: 4
estimated_hours: 2
dependencies: [TASK-HAI-001]
blocks: [TASK-HAI-005]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Create Python API Specialist Agent

## Context

Create a new global implementation agent specialized in FastAPI endpoint and Pydantic model generation. This agent uses Haiku for fast, cost-effective code generation and includes discovery metadata for AI-powered agent matching.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 1 (Foundation + Agent Creation)
**Method**: Direct Claude Code implementation
**Workspace**: WS-A (Conductor workspace)

## Objectives

1. Create `installer/global/agents/python-api-specialist.md`
2. Include complete discovery metadata (stack, phase, capabilities, keywords)
3. Add boundary sections (ALWAYS/NEVER/ASK) following GitHub best practices
4. Configure model: haiku for cost-effective code generation
5. Validate against schema from TASK-HAI-001

## Agent Specification

### Frontmatter (Discovery Metadata)

```yaml
---
name: python-api-specialist
description: FastAPI endpoint and Pydantic model implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "FastAPI code generation follows established patterns (async handlers, dependency injection, Pydantic validation). Haiku provides fast, cost-effective implementation at 90% quality. Architectural quality ensured by upstream architectural-reviewer (Sonnet)."

# Discovery metadata
stack: [python]
phase: implementation
capabilities:
  - FastAPI endpoint implementation
  - Async request handling patterns
  - Dependency injection via Depends()
  - Pydantic schema integration
  - Error handling with ErrorOr pattern
keywords: [fastapi, async, endpoints, router, dependency-injection, pydantic, python-api]

collaborates_with:
  - python-testing-specialist
  - database-specialist
  - security-specialist
---
```

### Boundary Sections (ALWAYS/NEVER/ASK)

```markdown
## Boundaries

### ALWAYS
- ✅ Use async def for all endpoint handlers (async/await best practice)
- ✅ Inject dependencies via Depends() (testability and dependency inversion)
- ✅ Validate input with Pydantic schemas (type safety and security)
- ✅ Return ErrorOr or Result types (explicit error handling)
- ✅ Document endpoints with docstrings (OpenAPI generation)
- ✅ Use HTTPException for HTTP errors (FastAPI standard)
- ✅ Apply proper status codes (REST conventions)

### NEVER
- ❌ Never use sync def for I/O operations (blocks event loop)
- ❌ Never instantiate dependencies directly (breaks testability)
- ❌ Never skip input validation (security vulnerability)
- ❌ Never use bare except (hides errors)
- ❌ Never hardcode configuration (use settings/environment)
- ❌ Never return raw exceptions to client (information leakage)
- ❌ Never ignore type hints (reduces maintainability)

### ASK
- ⚠️ Complex dependency chains: Ask if circular dependencies detected
- ⚠️ Performance-critical endpoints: Ask if caching strategy needed
- ⚠️ Long-running operations: Ask if background tasks appropriate
- ⚠️ File uploads: Ask if streaming vs buffered upload
```

### Quick Start Examples

```markdown
## Quick Start

### Create Basic Endpoint
\`\`\`python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    name: str

@router.post("/users", status_code=201)
async def create_user(
    user: UserCreate,
    db: Database = Depends(get_db)
) -> dict:
    """Create a new user."""
    # Implementation here
    return {"id": 1, "email": user.email}
\`\`\`

### With Dependency Injection
\`\`\`python
from typing import Annotated
from fastapi import Depends

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Decode and validate token
    return user

@router.get("/profile")
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    return {"user": current_user}
\`\`\`
```

## Acceptance Criteria

- [ ] Agent file created at `installer/global/agents/python-api-specialist.md`
- [ ] Discovery metadata present and validates against HAI-001 schema
- [ ] Stack: [python]
- [ ] Phase: implementation
- [ ] Capabilities: minimum 5 specific capabilities listed
- [ ] Keywords: minimum 5 relevant keywords for matching
- [ ] Model: haiku with clear rationale
- [ ] Boundary sections: 7 ALWAYS, 7 NEVER, 4 ASK rules
- [ ] Quick Start section with 2+ code examples
- [ ] Collaborates_with lists relevant agents
- [ ] File follows markdown formatting standards

## Implementation Steps

1. **Create agent file** from template
2. **Add frontmatter** with discovery metadata
3. **Write boundary sections** (ALWAYS/NEVER/ASK)
4. **Add Quick Start examples** (FastAPI patterns)
5. **Add Capabilities section** (detailed agent features)
6. **Validate metadata** against schema

## Testing

### Metadata Validation

```bash
# Validate YAML frontmatter parses correctly
python3 -c "
import frontmatter
with open('installer/global/agents/python-api-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    
    # Check required fields
    assert 'stack' in agent.metadata
    assert 'phase' in agent.metadata
    assert 'capabilities' in agent.metadata
    assert 'keywords' in agent.metadata
    
    # Validate values
    assert agent.metadata['stack'] == ['python']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    assert agent.metadata['model'] == 'haiku'
    
    print('✅ Metadata validation passed')
"
```

### Boundary Section Validation

```bash
# Check boundary sections present
grep -q "### ALWAYS" installer/global/agents/python-api-specialist.md && echo "✅ ALWAYS present"
grep -q "### NEVER" installer/global/agents/python-api-specialist.md && echo "✅ NEVER present"
grep -q "### ASK" installer/global/agents/python-api-specialist.md && echo "✅ ASK present"

# Count rules
python3 -c "
with open('installer/global/agents/python-api-specialist.md') as f:
    content = f.read()
    always_count = content.count('✅')
    never_count = content.count('❌')
    ask_count = content.count('⚠️')
    
    assert 5 <= always_count <= 10, f'ALWAYS rules: {always_count} (expected 5-10)'
    assert 5 <= never_count <= 10, f'NEVER rules: {never_count} (expected 5-10)'
    assert 3 <= ask_count <= 7, f'ASK rules: {ask_count} (expected 3-7)'
    
    print(f'✅ Boundary rules: {always_count} ALWAYS, {never_count} NEVER, {ask_count} ASK')
"
```

## Reference Materials

**Template agents to reference**:
- `installer/global/templates/fastapi-python/agents/fastapi-specialist.md`
- `tasks/completed/agent-enhancement-implementation/agents/python/python-api-specialist.md`

**Schema**:
- TASK-HAI-001: Discovery metadata schema
- `docs/schemas/agent-discovery-metadata.md`

## Deliverables

1. **Agent file**: `installer/global/agents/python-api-specialist.md`
2. **Validation report**: Metadata and boundary sections validated
3. **Quick test**: Frontmatter parses without errors

## Rollback Strategy

**If issues arise**:
```bash
# Delete agent file
rm installer/global/agents/python-api-specialist.md

# No impact on system (new file, no dependencies)
```

**Recovery time**: < 1 minute

## Risk Assessment

**Risk Level**: LOW

**Potential Risks**:
1. Metadata doesn't match schema → Validation catches before merge
2. Missing boundary sections → Checklist ensures completeness
3. Incorrect model configuration → Peer review validates

**Mitigation**: Follow acceptance criteria checklist, validate before commit

## Related Tasks

**Dependencies**:
- TASK-HAI-001: Schema must be complete (provides metadata format)

**Blocks**:
- TASK-HAI-005: Discovery algorithm needs agents to discover

**Related**:
- TASK-HAI-003: React agent (parallel creation)
- TASK-HAI-004: .NET agent (parallel creation)
- TASK-HAI-009: Update existing agents (similar metadata work)

## Definition of Done

- [ ] Agent file created and committed
- [ ] All acceptance criteria met
- [ ] Metadata validated against schema
- [ ] Boundary sections complete (ALWAYS/NEVER/ASK)
- [ ] Quick Start examples functional
- [ ] Peer reviewed
- [ ] Merged to main (after Wave 1 checkpoint)

## Notes

This agent represents the first stack-specific Haiku implementation agent, completing the Phase 3 optimization strategy from TASK-EE41. It enables 4-5x faster Python API code generation at 3x lower cost while maintaining 90% quality through upstream architectural review.

**Implementation Method**: Direct Claude Code (not /task-work) - simple file creation from template, low integration risk.
