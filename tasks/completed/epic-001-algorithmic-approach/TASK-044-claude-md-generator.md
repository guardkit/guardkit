---
id: TASK-044
title: Implement CLAUDE.md generator
status: backlog
created: 2025-11-01T16:09:00Z
priority: medium
complexity: 5
estimated_hours: 6
tags: [template-create, documentation-generation]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037, TASK-038]
blocks: [TASK-047]
---

# TASK-044: Implement CLAUDE.md Generator

## Objective

Generate architectural guidance document (CLAUDE.md) from detected patterns:
- Technology stack overview
- Architecture patterns and principles
- Code conventions
- Quality standards
- Usage examples

## Acceptance Criteria

- [ ] Generates comprehensive CLAUDE.md
- [ ] Includes technology stack description
- [ ] Documents architectural patterns
- [ ] Includes naming conventions
- [ ] Provides code examples
- [ ] Documents quality gates
- [ ] Markdown is well-formatted
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class ClaudeMdGenerator:
    def generate(self, stack_result, arch_result, patterns):
        # Generate markdown sections
        return """
# Project Template - {stack}

## Architecture
{architecture_description}

## Patterns
{patterns_list}

## Conventions
{conventions}
        """
```

**Estimated Time**: 6 hours | **Complexity**: 5/10 | **Priority**: MEDIUM
