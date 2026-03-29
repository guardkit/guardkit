---
id: TASK-TI-001
title: Package JsonExtractor class from generation_loop.py
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p0
tags: [template, extraction, json, base-template]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 1
implementation_mode: task-work
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Package JsonExtractor Class

## Description

Extract the proven JSON extraction code from `entrypoint/generation_loop.py` into a reusable `JsonExtractor` class for the `langchain-deepagents` base template. This single component prevents 9 of the 31 fixes identified in TASK-REV-TRF12.

## What to Build

A `JsonExtractor` class implementing a 5-strategy cascade:

1. **Direct parse**: `json.loads(content)` — handles clean JSON
2. **Code-fence strip**: Remove ` ```json ... ``` ` wrappers, retry parse
3. **String-aware brace matching**: Find outermost `{...}` tracking quoted context (TRF-025 lesson)
4. **JSON string repair**: Escape literal newlines/tabs in string values before parse (TRF-030 lesson)
5. **reasoning_content fallback**: Check `additional_kwargs["reasoning_content"]` for vLLM providers (TRF-013/TRF-026 lesson)

Also include:
- `normalise_think_closing_tags()` — fix `<think>...<think>` and `<think>...EOF` patterns (TRF-019/TRF-021)
- Canonical pipeline order enforced: normalize -> extract -> validate

## Source Code

Extract from these existing, proven functions in `entrypoint/generation_loop.py`:
- `_extract_example_json()`
- `_extract_player_content()`
- `_extract_coach_content()`
- `_repair_json_strings()`

And from `synthesis/validator.py`:
- `normalise_think_closing_tags()`

## Fixes Prevented

TRF-008, TRF-013, TRF-015, TRF-019, TRF-020, TRF-021, TRF-025, TRF-026, TRF-030

## Target Location

`lib/json_extractor.py` (in the template output)

## Acceptance Criteria

- [ ] `JsonExtractor` class with 5-strategy cascade
- [ ] `normalise_think_closing_tags()` included
- [ ] Brace matcher is string-aware (handles `{` inside quoted values)
- [ ] JSON repair handles literal newlines and tabs
- [ ] reasoning_content fallback for both Player and Coach extraction
- [ ] Unit tests covering all 5 strategies with edge cases from TRF fixes
- [ ] Regression tests derived from actual failing inputs in runs 7-10
- [ ] Pipeline order enforced: normalize before extract

## Effort Estimate

2-3 days
