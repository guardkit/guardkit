---
id: TASK-TI-009
title: Create langchain-deepagents-weighted-evaluation template scaffold
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, scaffold]
complexity: 6
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-001, TASK-TI-002, TASK-TI-003, TASK-TI-004, TASK-TI-005, TASK-TI-006]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Adversarial Template Scaffold

## Description

Create the `langchain-deepagents-weighted-evaluation` template that extends the base `langchain-deepagents` template. This is the foundation for all adversarial cooperation agents, encoding the patterns proven across 11 runs.

## What to Build

### Template Structure
```
langchain-deepagents-weighted-evaluation/
  SKILL.md                               # DeepAgents skill definition
  extends: langchain-deepagents           # Inherits base template
  scaffold/
    orchestrator.py.j2                   # Three-role wiring (TI-010)
    pipeline.py.j2                       # Canonical pipeline (TI-011)
    goal_schema.py.j2                    # Domain config (TI-012)
  prompts/
    coach_template.py                    # Coach/Evaluator prompts (TI-013)
    adversarial_base.py                  # Shared adversarial patterns
  hooks/
    hitl.py                              # HITL checkpoints (TI-015)
    sprint_contract.py                   # Sprint negotiation (TI-016)
  config/
    adversarial_config.py                # Intensity settings (TI-014)
  tests/
    test_scaffold.py                     # Template generation tests
```

### Template Variables
- `project_name`: Project identifier
- `domain_name`: Domain for GOAL.md generation
- `adversarial_intensity`: full | light | solo
- `roles`: List of role definitions (default: orchestrator + player + coach)
- `evaluation_criteria`: List of weighted criteria for Coach

### Relationship to Anthropic Terminology
| This Template | Anthropic Term | Role |
|--------------|---------------|------|
| Orchestrator | Planner | Coordinates pipeline, owns writes, manages retries |
| Player | Generator | Produces content using domain tools |
| Coach | Evaluator | Evaluates content against criteria, returns structured verdict |

## Acceptance Criteria

- [ ] Template scaffold created with correct directory structure
- [ ] SKILL.md with template metadata and variable definitions
- [ ] Extends base template (inherits JsonExtractor, guards, validator)
- [ ] Template variables documented with defaults
- [ ] Smoke test: template generates a minimal adversarial agent project

## Effort Estimate

1 day
