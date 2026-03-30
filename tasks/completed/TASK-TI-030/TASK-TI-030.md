---
id: TASK-TI-030
title: Create GETTING_STARTED.md developer onboarding guide
status: completed
created: 2026-03-30T12:00:00Z
updated: 2026-03-30T17:00:00Z
completed: 2026-03-30T17:00:00Z
completed_location: tasks/completed/TASK-TI-030/
priority: medium
tags: [template, documentation, onboarding, developer-experience]
task_type: implementation
complexity: 4
parent_review: TASK-REV-4F71
feature_id: FEAT-TI
implementation_mode: direct
wave: 5
depends_on: []
---

# Task: Create GETTING_STARTED.md Developer Onboarding Guide

## Description

The conversation starter spec included `first_run.sh`, `FIRST_RUN_CHECKLIST.md`, and `SDK_PITFALLS.md` for developer onboarding. Neither template includes these. New users must discover SDK constraints (ainvoke contract, create_agent vs create_deep_agent, tool separation) by reading pattern rules, which are comprehensive but not structured as a getting-started guide.

## Finding Reference

TASK-REV-4F71, Finding F3 (MEDIUM severity).

## What to Do

1. Create `docs/GETTING_STARTED.md` in the base template that condenses the pattern rules into a step-by-step first-run guide:
   - Prerequisites (Python >=3.11, DeepAgents SDK, vLLM or compatible provider)
   - Quick start (5-minute path to first working adversarial pipeline)
   - Key SDK constraints (ainvoke contract, create_agent vs create_deep_agent)
   - Tool separation rules (Player tools, Coach: zero tools, Orchestrator owns writes)
   - Common pitfalls (from model-compatibility.md and pattern rules)
   - "What to do next" with links to pattern rules for deeper understanding
2. Reference existing docs: model-compatibility.md, pattern rules, CLAUDE.md
3. Keep it concise — this is a quickstart, not a tutorial

## Acceptance Criteria

- [x] `docs/GETTING_STARTED.md` exists in base template
- [x] Covers prerequisites, quick start, key constraints, common pitfalls
- [x] References existing pattern rules and documentation
- [x] A developer new to the template can reach a working pipeline by following this guide
- [x] Extension CLAUDE.md references the base's GETTING_STARTED.md
