---
id: TASK-TI-025
title: Register langchain-deepagents-weighted-evaluation template in installer
status: completed
created: 2026-03-30T00:30:00Z
updated: 2026-03-30T12:15:00Z
completed: 2026-03-30T12:15:00Z
completed_location: tasks/completed/TASK-TI-025/
priority: p1
tags: [template, installer, weighted-evaluation, registration]
complexity: 4
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-009, TASK-TI-027]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Register langchain-deepagents-weighted-evaluation Template in Installer

## Description

Create the template directory structure, manifest.json, and settings.json for the new `langchain-deepagents-weighted-evaluation` template and register it in the GuardKit installer so it appears in `guardkit init` as a selectable template.

## Template Architecture

Two templates with an inheritance relationship:

| Template | Purpose | Evaluation Model |
|----------|---------|-----------------|
| `langchain-deepagents` (base, exists) | Production-grade adversarial cooperation with binary accept/reject | Fixed criteria — Coach evaluates pass/fail |
| `langchain-deepagents-weighted-evaluation` (new) | Extends base with configurable weighted evaluation | GOAL.md quality contract — weighted gradable criteria for subjective domains |

The weighted-evaluation template **extends** the base template. It inherits all base infrastructure (JsonExtractor, factory guards, observability, tool separation, gated writes) and adds the evaluation model components.

## What to Create

### 1. Template Directory

```
installer/core/templates/langchain-deepagents-weighted-evaluation/
├── .claude/
│   ├── CLAUDE.md                    # Template docs referencing base + extensions
│   ├── settings.json
│   └── rules/
│       └── patterns/
│           ├── weighted-evaluation.md    # GOAL.md quality contract pattern
│           ├── configurable-intensity.md # full/light/solo modes
│           └── sprint-contract.md        # Pre-generation scope negotiation
├── manifest.json                    # Template metadata with extends field
├── agents/                          # Template-specific agents (if needed)
└── templates/
    └── other/
        ├── scaffold/
        │   └── goal_schema.py.template         # GOAL.md parser + evaluation schema
        ├── prompts/
        │   └── weighted_coach_prompts.py.template  # Weighted criteria prompt builder
        ├── config/
        │   └── adversarial_config.py.template  # Intensity settings
        ├── hooks/
        │   ├── hitl.py.template                # HITL checkpoint hooks
        │   └── sprint_contract.py.template     # Sprint negotiation
        └── other/
            └── GOAL.md.template                # Quality contract scaffold
```

### 2. manifest.json

```json
{
  "schema_version": "1.0.0",
  "name": "langchain-deepagents-weighted-evaluation",
  "display_name": "Python Adversarial Cooperation — Weighted Evaluation",
  "description": "Extends langchain-deepagents with configurable weighted evaluation via GOAL.md quality contracts. Makes subjective quality gradable for creative content, design, and planning domains.",
  "version": "1.0.0",
  "language": "Python",
  "extends": "langchain-deepagents",
  "architecture": "Adversarial Cooperation with Weighted Evaluation",
  "patterns": ["Weighted Evaluation", "Quality Contract", "Configurable Intensity", "Sprint Contract"],
  "category": "adversarial",
  "complexity": 7,
  "tags": ["adversarial-cooperation", "weighted-evaluation", "quality-contract", "goal-md", "creative-content"]
}
```

### 3. Installer Registration

- Add template to `guardkit init` template list
- Ensure `extends: langchain-deepagents` is handled (base template installed first, then extension overlays)
- Add to installer template discovery

## Acceptance Criteria

- [ ] Template directory structure created
- [ ] manifest.json with `extends` field pointing to `langchain-deepagents`
- [ ] Template appears in `guardkit init` template selection
- [ ] Installing this template also installs the base `langchain-deepagents` components
- [ ] GOAL.md.template scaffold included
- [ ] settings.json configured

## Effort Estimate

2-3 hours
