# Text Matching Semantic Fix

**Feature ID**: FEAT-TM-FIX
**Parent Review**: [TASK-REV-0828](../../backlog/TASK-REV-0828-analyse-logging-feature-3-text-matching-failure.md)
**Status**: Ready for implementation

## Problem

The Coach validator's text-based criteria matching fails for local vLLM models because:
1. **Bug #1**: `_extract_keywords()` uses whitespace splitting that preserves backticks/quotes as keyword parts
2. **Bug #2**: `_hybrid_fallback()` evidence check blocks file-existence promise upgrades

This causes 0/7 criteria matches on the vLLM path while the same feature succeeds 7/7 on Anthropic API.

## Solution

Four targeted fixes to `coach_validator.py`, all in the text-matching fallback path (zero impact on Anthropic promise-based path):

| # | Fix | Priority | Impact |
|---|-----|----------|--------|
| 1 | Align keyword extraction with regex splitting | P0 | Turns 2-3: 0/7 → 5/7 |
| 2 | Widen hybrid fallback evidence check | P0 | Turn 4: 0/7 → 6/7 |
| 3 | Add markdown formatting stripping | P1 | Defense-in-depth |
| 4 | Add AC-XXX prefix stripping | P2 | Defense-in-depth |

## Subtasks

- [TASK-FIX-TM01](TASK-FIX-TM01-align-extract-keywords-regex.md) — Align `_extract_keywords()` regex (P0, Wave 1)
- [TASK-FIX-TM02](TASK-FIX-TM02-widen-hybrid-fallback-evidence.md) — Widen `_hybrid_fallback()` evidence (P0, Wave 1)
- [TASK-FIX-TM03](TASK-FIX-TM03-add-markdown-stripping-normalization.md) — Markdown formatting stripping (P1, Wave 2)
- [TASK-FIX-TM04](TASK-FIX-TM04-add-ac-prefix-stripping.md) — AC-XXX prefix stripping (P2, Wave 2)

## Execution Strategy

**Wave 1** (parallel): TASK-FIX-TM01 + TASK-FIX-TM02 — different methods, no conflicts
**Wave 2** (parallel, after Wave 1): TASK-FIX-TM03 + TASK-FIX-TM04 — defense-in-depth

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for full details.
