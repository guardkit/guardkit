---
id: TASK-HAI-003-45BB
title: Create React State Specialist Agent
status: backlog
priority: high
tags: [haiku-agents, react, typescript, implementation, agent-creation]
epic: haiku-agent-implementation
complexity: 4
estimated_hours: 2
dependencies: [TASK-HAI-001]
blocks: [TASK-HAI-005]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Create React State Specialist Agent

## Context

Create a new global implementation agent specialized in React hooks, state management, and component generation. This agent uses Haiku for fast, cost-effective code generation and includes discovery metadata for AI-powered agent matching.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 1 (Foundation + Agent Creation)
**Method**: Direct Claude Code implementation
**Workspace**: WS-B (Conductor workspace)

## Objectives

1. Create `installer/global/agents/react-state-specialist.md`
2. Include complete discovery metadata (stack, phase, capabilities, keywords)
3. Add boundary sections (ALWAYS/NEVER/ASK) following GitHub best practices
4. Configure model: haiku for cost-effective code generation
5. Validate against schema from TASK-HAI-001

## Agent Specification

### Frontmatter (Discovery Metadata)

```yaml
---
name: react-state-specialist
description: React hooks and state management implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "React component implementation follows established patterns (hooks, state management, composition). Haiku provides fast, cost-effective implementation at 90% quality. Architectural quality ensured by upstream architectural-reviewer (Sonnet)."

# Discovery metadata
stack: [react, typescript]
phase: implementation
capabilities:
  - React hooks implementation (useState, useEffect, useCallback)
  - TanStack Query for server state
  - State management patterns (Context, Zustand)
  - Component composition and reusability
  - Performance optimization (useMemo, memo)
keywords: [react, hooks, state, tanstack-query, zustand, typescript, components]

collaborates_with:
  - react-testing-specialist
  - feature-architecture-specialist
  - form-validation-specialist
---
```

### Boundary Sections (ALWAYS/NEVER/ASK)

```markdown
## Boundaries

### ALWAYS
- ✅ Use hooks for state management (modern React patterns)
- ✅ Leverage TanStack Query for server state (data fetching best practice)
- ✅ Use TypeScript for all components (type safety)
- ✅ Implement proper error boundaries (error handling)
- ✅ Follow hooks rules (no conditional calls, deps arrays complete)
- ✅ Use functional components (not class components)
- ✅ Optimize with useMemo/useCallback when needed (performance)

### NEVER
- ❌ Never use class components (deprecated pattern)
- ❌ Never mutate state directly (immutability violation)
- ❌ Never call hooks conditionally (rules of hooks)
- ❌ Never use useEffect for server data (use TanStack Query instead)
- ❌ Never prop drill excessively (use context or state library)
- ❌ Never skip dependency arrays (stale closure bugs)
- ❌ Never use any type in TypeScript (defeats type safety)

### ASK
- ⚠️ Global state needed: Ask if Zustand vs Context appropriate
- ⚠️ Complex form state: Ask if React Hook Form integration needed
- ⚠️ Optimistic updates: Ask if user expects immediate feedback
- ⚠️ Real-time data: Ask if WebSocket vs polling vs SSE
```

## Acceptance Criteria

- [ ] Agent file created at `installer/global/agents/react-state-specialist.md`
- [ ] Discovery metadata validates against HAI-001 schema
- [ ] Stack: [react, typescript]
- [ ] Phase: implementation
- [ ] Capabilities: minimum 5 specific capabilities
- [ ] Keywords: minimum 5 relevant keywords
- [ ] Model: haiku with clear rationale
- [ ] Boundary sections: 7 ALWAYS, 7 NEVER, 4 ASK rules
- [ ] Quick Start with 2+ code examples
- [ ] Collaborates_with lists relevant agents

## Testing

```bash
# Validate metadata
python3 -c "
import frontmatter
with open('installer/global/agents/react-state-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['react', 'typescript']
    assert agent.metadata['phase'] == 'implementation'
    assert 'hooks' in agent.metadata['keywords']
    print('✅ React agent validated')
"
```

## Reference Materials

- `installer/global/templates/react-typescript/agents/react-query-specialist.md`
- `tasks/completed/agent-enhancement-implementation/agents/react/react-state-specialist.md`

## Deliverables

1. Agent file: `installer/global/agents/react-state-specialist.md`
2. Validation passed
3. Metadata complete

## Risk: LOW | Rollback: Delete file (<1 min)

