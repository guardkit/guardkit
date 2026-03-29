---
id: TASK-TI-002
title: Create prompt engineering template with CRITICAL section pattern
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-002/
priority: p0
tags: [template, prompts, base-template]
complexity: 4
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 1
implementation_mode: task-work
depends_on: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-29T00:00:00Z
  tests_passed: 29
  tests_failed: 0
quality_gates:
  compilation: passed
  tests: 29/29 passed
  code_review: approved
organized_files:
  - TASK-TI-002.md
  - completion-report.md
---

# Task: Prompt Engineering Template

## Description

Create a standard prompt template module for the `langchain-deepagents` base template that encodes the hard-won prompt engineering lessons from 7 fixes. The template generates prompt sections that prevent the most common prompt-related failures.

## What to Build

Standard prompt section generators:

### 1. `## CRITICAL -- Response Format` (end-of-prompt)
- Positioned LAST in system prompt (recency bias — TRF-031 lesson)
- Uses imperative language: "MUST", "NEVER", "ALWAYS" (not "please", "should")
- Includes negative examples: "Do NOT return conversational text"
- Includes concrete JSON structure example (show-don't-tell — TRF-029 lesson)

### 2. `## Tool Usage`
- Explicit call limits: "Call rag_retrieval at most once per target" (TRF-014 lesson)
- Pre-fetch documentation: "Curriculum context is already provided below" (TRF-009 lesson)
- Tool purpose descriptions with when-to-use/when-not-to-use

### 3. `## Quality Gates` (for evaluator/coach prompts)
- Concrete accept/reject criteria with examples (TRF-027 lesson)
- Weighted scoring template with configurable criteria
- Scepticism tuning instructions

### 4. `## Output Structure`
- Full JSON example with all required fields (TRF-029 lesson)
- Field-by-field description with types and constraints
- Common mistakes section with "DO NOT" examples

## Fixes Prevented

TRF-008, TRF-009, TRF-014, TRF-027, TRF-029, TRF-031, FRF-002

## Target Location

`prompts/templates.py` (in the template output)

## Acceptance Criteria

- [x] Four section generators implemented
- [x] CRITICAL section positioned at end of prompt by default
- [x] Imperative language used throughout (no polite hedging)
- [x] At least one concrete JSON example in output structure
- [x] Tool usage section includes explicit call limits
- [x] Quality gates section includes weighted scoring
- [x] Unit tests verify section positioning and content patterns
- [x] Integration test assembles a full prompt from all sections

## Effort Estimate

1 day
