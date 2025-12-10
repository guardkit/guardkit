---
id: TASK-HAI-004-9534
title: Create .NET Domain Specialist Agent
status: completed
priority: high
tags: [haiku-agents, dotnet, csharp, implementation, agent-creation]
epic: haiku-agent-implementation
complexity: 4
estimated_hours: 2
actual_hours: 0.25
dependencies: [TASK-HAI-001]
blocks: [TASK-HAI-005]
created: 2025-11-25T13:00:00Z
updated: 2025-11-25T16:35:00Z
completed: 2025-11-25T16:35:00Z
completion_metrics:
  total_duration: "20 minutes"
  estimated_vs_actual: "800% efficiency"
  files_created: 1
  validation_checks_passed: 13
  boundary_rules: 18
---

# Task: Create .NET Domain Specialist Agent

## Context

Create a new global implementation agent specialized in .NET domain models, entities, and DDD patterns. This agent uses Haiku for fast, cost-effective code generation and includes discovery metadata for AI-powered agent matching.

**Parent Epic**: haiku-agent-implementation
**Wave**: Wave 1 (Foundation + Agent Creation)
**Method**: Direct Claude Code implementation
**Workspace**: WS-C (Conductor workspace)

## Objectives

1. Create `installer/core/agents/dotnet-domain-specialist.md`
2. Include complete discovery metadata (stack, phase, capabilities, keywords)
3. Add boundary sections (ALWAYS/NEVER/ASK) following GitHub best practices
4. Configure model: haiku for cost-effective code generation
5. Validate against schema from TASK-HAI-001

## Acceptance Criteria

- [x] Agent file created at `installer/core/agents/dotnet-domain-specialist.md`
- [x] Discovery metadata validates against HAI-001 schema
- [x] Stack: [dotnet, csharp]
- [x] Phase: implementation
- [x] Capabilities: minimum 5 specific capabilities (7 provided)
- [x] Keywords: minimum 5 relevant keywords (11 provided)
- [x] Model: haiku with clear rationale
- [x] Boundary sections: 7 ALWAYS, 7 NEVER, 4 ASK rules
- [x] Quick Start with 2+ code examples
- [x] Collaborates_with lists relevant agents (4 agents)

## Deliverables

1. Agent file: `installer/core/agents/dotnet-domain-specialist.md`
2. Validation passed
3. Metadata complete

---

# Task Completion Report - TASK-HAI-004-9534

## Summary

**Task**: Create .NET Domain Specialist Agent
**Completed**: 2025-11-25T16:35:00Z
**Duration**: ~20 minutes
**Estimated**: 2 hours
**Final Status**: COMPLETED

## Deliverables

- Files created: 1
  - `installer/core/agents/dotnet-domain-specialist.md`
- Agent content:
  - Discovery metadata (stack, phase, capabilities, keywords)
  - Model: haiku with rationale
  - Boundary sections (7 ALWAYS, 7 NEVER, 4 ASK)
  - Quick Start with 2 code examples
  - Full DDD implementation patterns
  - Best practices documentation

## Quality Metrics

| Check | Result |
|-------|--------|
| Agent file exists | PASS |
| Stack: [dotnet, csharp] | PASS |
| Phase: implementation | PASS |
| Capabilities: 7 >= 5 | PASS |
| Keywords: 11 >= 5 | PASS |
| Model: haiku | PASS |
| Model rationale present | PASS |
| Collaborates with: 4 agents | PASS |
| Contains keyword: ddd | PASS |
| ALWAYS rules: 7 (5-7) | PASS |
| NEVER rules: 7 (5-7) | PASS |
| ASK rules: 4 (3-5) | PASS |
| Quick Start examples: 2+ | PASS |

**All 13 validation checks passed**

## Agent Content Summary

### Discovery Metadata
- **Stack**: [dotnet, csharp]
- **Phase**: implementation
- **Capabilities**: Entity design, Value objects, Domain events, Repository pattern, Aggregate roots, CQRS, Specification pattern
- **Keywords**: csharp, dotnet, domain-model, entity, value-object, ddd, aggregate, domain-event, repository, cqrs, specification-pattern

### Boundary Rules (18 total)
- **ALWAYS (7)**: Value objects, domain events, invariants, private setters, ErrorOr<T>, aggregate roots, record types
- **NEVER (7)**: Public setters, anemic models, primitives, invalid state, infrastructure coupling, static methods, null checks
- **ASK (4)**: Aggregate boundaries, complex validation, event sourcing, soft delete

### Collaboration Graph
- dotnet-testing-specialist
- database-specialist
- architectural-reviewer
- dotnet-api-specialist

## Lessons Learned

**What went well:**
- Reference material from completed agent enhancement provided excellent template
- HAI-001 schema clearly defined validation requirements
- Boundary section format well documented in CLAUDE.md

**Challenges faced:**
- Initial boundary sections lacked emoji prefixes (fixed immediately)

**Improvements for next time:**
- Include emoji prefixes in boundary rules from the start

## Impact

- **Unblocks**: TASK-HAI-005 (next in haiku-agent-implementation epic)
- **Enables**: AI-powered agent discovery for .NET domain modeling tasks
- **Cost savings**: Haiku model provides 90% quality at fraction of cost

## Risk Assessment

**Risk Level**: LOW
**Rollback Strategy**: Delete file (<1 min)
**Technical Debt**: None incurred
