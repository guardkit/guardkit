---
id: TASK-TI-026
title: Document two-template architecture and evaluation model distinction
status: backlog
created: 2026-03-30T00:30:00Z
updated: 2026-03-30T00:30:00Z
priority: p1
tags: [template, documentation, architecture, weighted-evaluation]
complexity: 3
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 4
implementation_mode: direct
depends_on: [TASK-TI-025]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Document Two-Template Architecture and Evaluation Model Distinction

## Description

Document the relationship between the base `langchain-deepagents` template and the `langchain-deepagents-weighted-evaluation` extension. The key insight — and what must be clearly communicated — is that the distinction is NOT simple vs production-grade, but the **evaluation model**:

- **Base**: Binary accept/reject evaluation against fixed pass/fail criteria. Works for verifiable domains (code generation, data synthesis, schema conformance).
- **Weighted-evaluation**: Configurable weighted multi-criteria evaluation via GOAL.md quality contracts. Makes subjective quality gradable — the Anthropic insight applied to creative content (video planning, design, content creation).

## What to Document

### 1. Base Template CLAUDE.md Update

Update `installer/core/templates/langchain-deepagents/.claude/CLAUDE.md` to:
- Clarify this is the base template for adversarial cooperation with binary evaluation
- Reference the weighted-evaluation extension for subjective/creative domains
- List what's included vs what needs the extension

### 2. Weighted-Evaluation Template CLAUDE.md

Create `installer/core/templates/langchain-deepagents-weighted-evaluation/.claude/CLAUDE.md`:
- Explain what it extends and why
- Document the GOAL.md quality contract pattern
- Explain when to use this vs the base (verifiable vs subjective domains)
- Reference the Anthropic and Block research that validates the approach

### 3. Template Selection Guide

Add a selection guide (in docs or installer output) that helps users choose:

```
Which template do I need?

Is your evaluation criteria objectively verifiable?
  (schema conformance, code compilation, test pass/fail)
  → Use langchain-deepagents (base)

Does quality require subjective judgement with weighted criteria?
  (creative content, design, planning, pedagogy)
  → Use langchain-deepagents-weighted-evaluation
```

### 4. Cross-Domain Examples

Document the three proven use cases:

| Domain | Template | Evaluation Model | Evidence |
|--------|----------|-----------------|----------|
| Training data generation | Base | Schema conformance, metadata accuracy | agentic-dataset-factory: 11 runs, 85% acceptance |
| Code synthesis | Base | Test pass/fail, compilation | GuardKit AutoBuild: 100% task completion |
| Video content planning | Weighted-evaluation | Hook strength, originality, structure (weighted) | Anthropic research validation |

## Acceptance Criteria

- [ ] Base template CLAUDE.md updated with clear scope description
- [ ] Weighted-evaluation template CLAUDE.md created
- [ ] Template selection guide written
- [ ] Three cross-domain examples documented
- [ ] Both templates reference each other for discoverability

## Effort Estimate

2 hours
