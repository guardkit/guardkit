---
id: TASK-HAI-004-9534
title: Create .NET Domain Specialist Agent
status: backlog
priority: high
tags: [haiku-agents, dotnet, csharp, implementation, agent-creation]
epic: haiku-agent-implementation
complexity: 4
estimated_hours: 2
dependencies: [TASK-HAI-001]
blocks: [TASK-HAI-005]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T13:00:00Z
---

# Task: Create .NET Domain Specialist Agent

## Context

Create a new global implementation agent specialized in .NET domain models, entities, and DDD patterns. This agent uses Haiku for fast, cost-effective code generation and includes discovery metadata for AI-powered agent matching.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 1 (Foundation + Agent Creation)
**Method**: Direct Claude Code implementation
**Workspace**: WS-C (Conductor workspace)

## Objectives

1. Create `installer/global/agents/dotnet-domain-specialist.md`
2. Include complete discovery metadata (stack, phase, capabilities, keywords)
3. Add boundary sections (ALWAYS/NEVER/ASK) following GitHub best practices
4. Configure model: haiku for cost-effective code generation
5. Validate against schema from TASK-HAI-001

## Agent Specification

### Frontmatter (Discovery Metadata)

```yaml
---
name: dotnet-domain-specialist
description: .NET domain model and DDD patterns implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "Domain model implementation follows DDD patterns (entities, value objects, aggregates). Haiku provides fast, cost-effective implementation at 90% quality. Architectural quality ensured by upstream architectural-reviewer (Sonnet)."

# Discovery metadata
stack: [dotnet, csharp]
phase: implementation
capabilities:
  - Entity design with encapsulation
  - Value object implementation
  - Domain events and event handlers
  - Repository pattern implementation
  - Aggregate root design
keywords: [csharp, dotnet, domain-model, entity, value-object, ddd, aggregate]

collaborates_with:
  - dotnet-testing-specialist
  - database-specialist
  - architectural-reviewer
---
```

### Boundary Sections (ALWAYS/NEVER/ASK)

```markdown
## Boundaries

### ALWAYS
- ✅ Use value objects for domain concepts (encapsulation)
- ✅ Implement domain events for side effects (decoupling)
- ✅ Enforce invariants in entity constructors (validation)
- ✅ Use private setters for properties (immutability)
- ✅ Return ErrorOr<T> for operations (explicit errors)
- ✅ Apply aggregate root pattern (transaction boundaries)
- ✅ Use record types for value objects (C# 9+ feature)

### NEVER
- ❌ Never expose public setters (encapsulation violation)
- ❌ Never use anemic domain models (business logic leak)
- ❌ Never use primitive obsession (use value objects)
- ❌ Never allow invalid state (enforce invariants)
- ❌ Never couple domain to infrastructure (DIP violation)
- ❌ Never use static methods for business logic (testability)
- ❌ Never skip null checks on value objects (defensive programming)

### ASK
- ⚠️ Aggregate boundary unclear: Ask if entity should be root
- ⚠️ Complex validation: Ask if specification pattern needed
- ⚠️ Event sourcing candidate: Ask if event log required
- ⚠️ Soft delete vs hard delete: Ask for data retention policy
```

## Acceptance Criteria

- [ ] Agent file created at `installer/global/agents/dotnet-domain-specialist.md`
- [ ] Discovery metadata validates against HAI-001 schema
- [ ] Stack: [dotnet, csharp]
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
with open('installer/global/agents/dotnet-domain-specialist.md') as f:
    agent = frontmatter.loads(f.read())
    assert agent.metadata['stack'] == ['dotnet', 'csharp']
    assert agent.metadata['phase'] == 'implementation'
    assert 'ddd' in agent.metadata['keywords']
    print('✅ .NET agent validated')
"
```

## Reference Materials

- `tasks/completed/agent-enhancement-implementation/agents/dotnet/dotnet-domain-specialist.md`

## Deliverables

1. Agent file: `installer/global/agents/dotnet-domain-specialist.md`
2. Validation passed
3. Metadata complete

## Risk: LOW | Rollback: Delete file (<1 min)

