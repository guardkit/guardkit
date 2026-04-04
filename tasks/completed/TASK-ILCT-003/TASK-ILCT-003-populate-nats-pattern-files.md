---
id: TASK-ILCT-003
title: Populate nats-asyncio-service pattern rule files with real examples
status: completed
completed: 2026-04-03T23:45:00Z
created: 2026-04-03T23:15:00Z
priority: high
tags: [template, nats-asyncio-service, patterns, rules]
parent_review: TASK-REV-81AA
feature_id: FEAT-ILCT
implementation_mode: task-work
wave: 1
complexity: 4
depends_on: []
completed_location: tasks/completed/TASK-ILCT-003/
---

# Task: Populate nats-asyncio-service pattern rule files with real examples

## Description

All 10 pattern rule files under `installer/core/templates/nats-asyncio-service/.claude/rules/patterns/` are boilerplate stubs containing only "No examples found in codebase" and generic SOLID advice. These provide zero guidance to developers.

The agent -ext files in the same template DO contain real examples and detailed guidance. The pattern files should be populated with concrete code examples matching the quality of the langchain-deepagents-orchestrator pattern files (which have full implementations, tables, and "When to Use" sections).

## Files to Update

1. `patterns/handler/service-separation.md`
2. `patterns/module-level-singleton-for-service-instances.md`
3. `patterns/correlation-id-linking-for-request/response-tracing.md`
4. `patterns/lifespan-context-manager-for-startup/shutdown.md`
5. `patterns/pub/sub-messaging.md`
6. `patterns/explicit-unidirectional-dependency-flow-(handler-->-service).md`
7. `patterns/environment-variable-configuration-via-pydantic-settings.md`
8. `patterns/factory-function-pattern-for-test-data.md`
9. `patterns/in-memory-broker-testing-via-testnatsbroker.md`
10. `patterns/marker-gated-integration-tests.md`

## Required Structure per Pattern File

Each file should follow this structure (matching langchain-deepagents-orchestrator patterns):

```markdown
# {Pattern Name}

## Overview
{2-3 sentence description of what this pattern does and why}

## Implementation
{Real code example from the nats-asyncio-service exemplar}

## When to Use
{Bullet list of scenarios where this pattern applies}

## Best Practices
{Specific best practices for this pattern, not generic SOLID advice}
```

## Source Material

Extract examples from:
- Agent -ext files: `installer/core/templates/nats-asyncio-service/agents/*-ext.md`
- The CLAUDE.md template guidance
- FastStream/NATS documentation patterns

## Acceptance Criteria

- [ ] All 10 pattern files have real code examples (no "No examples found")
- [ ] Each pattern has Overview, Implementation, When to Use, Best Practices
- [ ] Examples are specific to NATS/FastStream (not generic Python)
- [ ] No boilerplate "Follow SOLID principles" filler

## References

- Quality reference: `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/two-model-orchestration.md`
- Agent -ext files: `installer/core/templates/nats-asyncio-service/agents/`
- Review report: `.claude/reviews/TASK-REV-81AA-review-report.md` (Finding 3)
