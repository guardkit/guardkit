---
id: TASK-HAI-010-A89D
title: Update react-typescript Template Agents with Discovery Metadata
status: backlog
priority: medium
tags: [haiku-agents, metadata, template-agents, react, typescript]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Update react-typescript Template Agents with Discovery Metadata

## Context

Add discovery metadata to 3 agents in the react-typescript template. These agents are template-specific specialists that complement the global react-state-specialist. Discovery enables automatic selection based on task keywords (forms, queries, architecture).

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-011-014)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-G (Conductor workspace - parallel with HAI-009)

## Objectives

1. Add discovery metadata to 3 react-typescript agents
2. Validate metadata against HAI-001 schema
3. Ensure distinct specializations from global react-state-specialist
4. Preserve all existing content

## Agents to Update

### 1. feature-architecture-specialist.md

**Location**: `installer/global/templates/react-typescript/agents/`

**Metadata**:
```yaml
---
name: feature-architecture-specialist
description: React feature architecture and component organization specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Feature architecture implementation follows established patterns (feature folders, barrel exports, component composition). Haiku provides fast, cost-effective implementation following Bulletproof React patterns."

# Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - Feature folder structure design
  - Component organization patterns
  - Barrel export management
  - Feature-based code splitting
  - Component composition strategies
keywords: [react, feature-architecture, component-organization, barrel-exports, code-splitting]

collaborates_with:
  - react-state-specialist
  - form-validation-specialist
  - react-query-specialist
---
```

**Specialization**: Feature organization and architecture (broader than state management)

### 2. form-validation-specialist.md

**Location**: `installer/global/templates/react-typescript/agents/`

**Metadata**:
```yaml
---
name: form-validation-specialist
description: React form handling and validation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Form implementation follows React Hook Form patterns with Zod validation. Haiku provides fast, cost-effective implementation of schema-based forms."

# Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - React Hook Form integration
  - Zod schema validation
  - Form state management
  - Error handling patterns
  - Controlled component patterns
keywords: [react, forms, validation, react-hook-form, zod, form-state]

collaborates_with:
  - react-state-specialist
  - feature-architecture-specialist
---
```

**Specialization**: Forms and validation (narrower than general state management)

### 3. react-query-specialist.md

**Location**: `installer/global/templates/react-typescript/agents/`

**Metadata**:
```yaml
---
name: react-query-specialist
description: TanStack Query (React Query) server state specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "TanStack Query implementation follows established patterns (queries, mutations, cache invalidation). Haiku provides fast, cost-effective implementation of data fetching patterns."

# Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - TanStack Query setup and configuration
  - Query and mutation patterns
  - Cache invalidation strategies
  - Optimistic updates
  - Error and loading state handling
keywords: [react, tanstack-query, react-query, data-fetching, server-state, caching]

collaborates_with:
  - react-state-specialist
  - feature-architecture-specialist
---
```

**Specialization**: Server state and data fetching (distinct from client state)

## Specialization Strategy

### Global vs Template Agents

**Global react-state-specialist**:
- Broad React state management
- Hooks (useState, useEffect, useCallback)
- Context API, Zustand
- General component patterns

**Template-specific specialists**:
- **feature-architecture-specialist**: Feature organization (broader than state)
- **form-validation-specialist**: Form-specific patterns (narrower)
- **react-query-specialist**: Server state only (distinct domain)

**Discovery behavior**:
- Task keywords "form", "validation" → form-validation-specialist
- Task keywords "query", "data-fetching" → react-query-specialist
- Task keywords "feature", "architecture" → feature-architecture-specialist
- Default React task → react-state-specialist (global fallback)

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
with open('installer/global/templates/react-typescript/agents/feature-architecture-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['react', 'typescript']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    print('✅ feature-architecture-specialist validated')
"
```

**Discovery validation**:
```python
# Test discovery finds template agents
from installer.global.commands.lib.agent_discovery import discover_agents

agents = discover_agents(phase='implementation', stack=['react'])
names = [a['name'] for a in agents]

assert 'feature-architecture-specialist' in names
assert 'form-validation-specialist' in names
assert 'react-query-specialist' in names
print('✅ All 3 react-typescript agents discoverable')
```

## Acceptance Criteria

- [ ] 3 agents updated with discovery metadata
- [ ] Stack: [react, typescript] for all
- [ ] Phase: implementation for all
- [ ] Capabilities: Minimum 5 per agent
- [ ] Keywords: Minimum 5 per agent, distinct specializations
- [ ] Model: haiku with clear rationale
- [ ] All existing content preserved
- [ ] YAML syntax valid
- [ ] Discovery finds all 3 agents
- [ ] Specializations distinct from global react-state-specialist

## Testing

```bash
# Validate metadata
python3 scripts/validate_template_agents.py react-typescript

# Test discovery
pytest tests/test_agent_discovery.py::test_react_template_agents -v

# Verify no content changes
git diff --stat installer/global/templates/react-typescript/agents/
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
git checkout installer/global/templates/react-typescript/agents/
```

**Recovery Time**: <30 seconds

## Reference Materials

- `installer/global/templates/react-typescript/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-003-45BB-create-react-state-specialist.md` - Global React agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema

## Deliverables

1. Updated: 3 react-typescript template agents
2. Validation: All 3 agents pass schema validation
3. Discovery: All 3 agents found by discovery algorithm
4. Specializations: Distinct keyword sets for targeted matching

## Success Metrics

- Validation: 3/3 agents pass (100%)
- Discovery: All 3 found with stack=[react, typescript]
- Keyword targeting: Form tasks → form-validation-specialist
- Zero disruption: No content changes

## Risk: LOW | Rollback: Revert files (<30 sec)
