---
id: TASK-TI-013
title: Coach/Evaluator prompt template with weighted criteria and scepticism tuning
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, prompts, coach]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-002, TASK-TI-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Coach/Evaluator Prompt Template

## Description

Create the Coach/Evaluator prompt template for the adversarial template. This encodes the evaluation prompt patterns proven across runs 4-11, including weighted criteria sections, scepticism tuning, the CRITICAL response format pattern, and explicit quality gates.

## What to Build

### 1. Weighted Criteria Section
- Auto-generated from GOAL.md evaluation criteria (TI-012)
- Each criterion with: name, weight, description, score range, examples of good/bad
- Weighted score calculation instruction

### 2. Scepticism Tuning
- Configurable scepticism level: strict (reject borderline), balanced (default), lenient (accept borderline)
- Maps to Coach system prompt language:
  - Strict: "When uncertain, reject. Quality over quantity."
  - Balanced: "Evaluate fairly. Accept if minimum threshold met."
  - Lenient: "Accept if substantially correct. Minor issues are feedback, not rejection."

### 3. CRITICAL Response Format (from TI-002 pattern)
- Coach MUST return structured JSON verdict
- Format: `{"accepted": bool, "scores": {...}, "weighted_score": float, "feedback": str, "revision_hints": [...]}`
- Positioned at end of Coach prompt (recency bias)

### 4. Explicit Quality Gates (TRF-027 lesson)
- Concrete examples of accept vs reject scenarios
- Automatic rejection criteria (e.g., missing think blocks for reasoning-type examples)
- Domain-specific gates injected from GOAL.md `format_requirements`

### 5. Think Block Verification (TRF-027 lesson)
- If domain requires think blocks: "Automatically reject (score 1) any example missing `<think>` blocks"
- Configurable per domain via GOAL.md `format_requirements`

## Acceptance Criteria

- [ ] Weighted criteria auto-generated from GOAL.md
- [ ] Three scepticism levels with distinct prompt language
- [ ] CRITICAL JSON response format at end of prompt
- [ ] Explicit accept/reject examples
- [ ] Think block verification configurable per domain
- [ ] Unit tests for prompt generation at each scepticism level
- [ ] Integration test: Coach prompt + mock evaluation

## Effort Estimate

1-2 days
