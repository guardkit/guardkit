---
id: TASK-VPR-005
title: Create AC quality template for local LLM runs
status: completed
priority: low
complexity: 3
tags: [autobuild, acceptance-criteria, quality, templates, local-llm]
parent_review: TASK-REV-C960
feature_id: FEAT-VPR
wave: 2
implementation_mode: direct
dependencies: []
completed: 2026-02-27T12:00:00Z
completed_location: tasks/completed/TASK-VPR-005/
---

# Task: Create Acceptance Criteria Quality Template for Local LLM Runs

## Description

Create a template and guidance for writing acceptance criteria that are optimised for local LLM backends (which have lower first-pass comprehension than Anthropic models).

## Context

TASK-REV-C960 Finding 4 and Recommendation R4: Qwen3's 50% first-pass rate was partly due to acceptance criteria that were insufficiently specific. TASK-DB-008 passed independent tests but failed 7/9 AC on Turn 1, indicating the model produced functionally correct but specification-incomplete code.

## Acceptance Criteria

- [x] Template document created at `docs/guides/acceptance-criteria-best-practices.md`
- [x] Covers: explicit vs implicit AC (always prefer explicit for local LLMs)
- [x] Covers: including expected interface signatures in AC text
- [x] Covers: specifying exact file paths and function names where possible
- [x] Covers: breaking large AC into smaller, testable items
- [x] Provides before/after examples showing vague AC vs specific AC
- [x] References TASK-DB-008 Turn 1 failure as case study
