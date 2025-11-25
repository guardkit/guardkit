---
id: TASK-HAI-012-C5F8
title: Update nextjs-fullstack Template Agents with Discovery Metadata
status: backlog
priority: medium
tags: [haiku-agents, metadata, template-agents, nextjs, fullstack]
epic: haiku-agent-implementation
complexity: 2
estimated_hours: 1-1.5
dependencies: [TASK-HAI-001]
blocks: []
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Update nextjs-fullstack Template Agents with Discovery Metadata

## Context

Add discovery metadata to 3 agents in the nextjs-fullstack template. These agents specialize in Next.js App Router patterns (server components, server actions) which are distinct from general React patterns.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 4 (Template Updates - parallel with HAI-009, HAI-010, HAI-011, HAI-013-014)
**Method**: Direct Claude Code implementation (simple metadata addition)
**Workspace**: WS-H (Conductor workspace - parallel with other template updates)

## Objectives

1. Add discovery metadata to 3 nextjs-fullstack agents
2. Validate metadata against HAI-001 schema
3. Ensure distinct specializations for Next.js App Router patterns
4. Preserve all existing content

## Agents to Update

### 1. nextjs-fullstack-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-fullstack-specialist
description: Next.js App Router full-stack specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Next.js full-stack implementation follows App Router patterns (layouts, routing, middleware). Haiku provides fast, cost-effective implementation of Next.js conventions."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Next.js App Router structure
  - File-based routing patterns
  - Layout and template components
  - Middleware implementation
  - API route handlers (Route Handlers)
keywords: [nextjs, app-router, routing, layouts, middleware, fullstack, route-handlers]

collaborates_with:
  - nextjs-server-components-specialist
  - nextjs-server-actions-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js App Router architecture and routing patterns

### 2. nextjs-server-components-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-server-components-specialist
description: Next.js Server Components and data fetching specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Server Component implementation follows Next.js patterns (async components, fetch API, caching). Haiku provides fast, cost-effective implementation of RSC patterns."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Server Component patterns
  - Data fetching in Server Components
  - Streaming and Suspense
  - Cache configuration (fetch, unstable_cache)
  - Client vs Server Component boundaries
keywords: [nextjs, server-components, rsc, data-fetching, streaming, suspense, caching]

collaborates_with:
  - nextjs-fullstack-specialist
  - nextjs-server-actions-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js Server Components (RSC) and data fetching patterns

### 3. nextjs-server-actions-specialist.md

**Location**: `installer/global/templates/nextjs-fullstack/agents/`

**Metadata**:
```yaml
---
name: nextjs-server-actions-specialist
description: Next.js Server Actions and mutations specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Server Actions implementation follows Next.js patterns ('use server', form actions, revalidation). Haiku provides fast, cost-effective implementation of mutation patterns."

# Discovery metadata
stack: [nextjs, react, typescript]
phase: implementation
capabilities:
  - Server Actions implementation ('use server')
  - Form handling with Server Actions
  - Optimistic updates with useOptimistic
  - Revalidation (revalidatePath, revalidateTag)
  - Error handling in Server Actions
keywords: [nextjs, server-actions, mutations, forms, revalidation, use-server, optimistic-updates]

collaborates_with:
  - nextjs-fullstack-specialist
  - nextjs-server-components-specialist
  - react-state-specialist
---
```

**Specialization**: Next.js Server Actions for mutations and form handling

## Specialization Strategy

### Global vs Template Agents

**Global react-state-specialist**:
- General React state management
- Client-side patterns
- Hooks and Context API

**Template-specific specialists**:
- **nextjs-fullstack-specialist**: App Router architecture (routing, layouts, middleware)
- **nextjs-server-components-specialist**: RSC patterns (server-side data fetching, streaming)
- **nextjs-server-actions-specialist**: Mutation patterns (forms, revalidation)

**Discovery behavior**:
- Task keywords "server-component", "rsc", "streaming" → nextjs-server-components-specialist
- Task keywords "server-action", "mutation", "revalidation" → nextjs-server-actions-specialist
- Task keywords "routing", "layout", "middleware" → nextjs-fullstack-specialist
- Default Next.js task → nextjs-fullstack-specialist (most general)

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
with open('installer/global/templates/nextjs-fullstack/agents/nextjs-fullstack-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['nextjs', 'react', 'typescript']
    assert agent.metadata['phase'] == 'implementation'
    assert len(agent.metadata['capabilities']) >= 5
    assert len(agent.metadata['keywords']) >= 5
    print('✅ nextjs-fullstack-specialist validated')
"
```

**Discovery validation**:
```python
from installer.global.commands.lib.agent_discovery import discover_agents

# Test Next.js agents
agents = discover_agents(phase='implementation', stack=['nextjs'])
names = [a['name'] for a in agents]

assert 'nextjs-fullstack-specialist' in names
assert 'nextjs-server-components-specialist' in names
assert 'nextjs-server-actions-specialist' in names

# Test React stack also finds Next.js agents (since Next.js is React-based)
react_agents = discover_agents(phase='implementation', stack=['react'])
react_names = [a['name'] for a in react_agents]
assert any('nextjs' in name for name in react_names)

print('✅ All 3 nextjs-fullstack agents discoverable')
```

## Acceptance Criteria

- [ ] 3 agents updated with discovery metadata
- [ ] Stack: [nextjs, react, typescript] for all
- [ ] Phase: implementation for all
- [ ] Capabilities: Minimum 5 per agent
- [ ] Keywords: Minimum 5 per agent, distinct Next.js specializations
- [ ] Model: haiku with clear rationale
- [ ] All existing content preserved
- [ ] YAML syntax valid
- [ ] Discovery finds all 3 agents with stack=nextjs
- [ ] Discovery finds all 3 agents with stack=react (inheritance)
- [ ] Specializations distinct (routing vs RSC vs Server Actions)

## Testing

```bash
# Validate metadata
python3 scripts/validate_template_agents.py nextjs-fullstack

# Test discovery
pytest tests/test_agent_discovery.py::test_nextjs_template_agents -v

# Verify no content changes
git diff --stat installer/global/templates/nextjs-fullstack/agents/
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
git checkout installer/global/templates/nextjs-fullstack/agents/
```

**Recovery Time**: <30 seconds

## Reference Materials

- `installer/global/templates/nextjs-fullstack/agents/*.md` - Existing agents
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-003-45BB-create-react-state-specialist.md` - Global React agent
- `tasks/backlog/haiku-agent-implementation/TASK-HAI-001-D668-design-discovery-metadata-schema.md` - Schema

## Deliverables

1. Updated: 3 nextjs-fullstack template agents
2. Validation: All 3 agents pass schema validation
3. Discovery: All 3 agents found by discovery algorithm
4. Specializations: Distinct keyword sets for Next.js patterns

## Success Metrics

- Validation: 3/3 agents pass (100%)
- Discovery: All 3 found with stack=[nextjs, react, typescript]
- Keyword targeting: Server Component tasks → nextjs-server-components-specialist
- Zero disruption: No content changes

## Risk: LOW | Rollback: Revert files (<30 sec)
