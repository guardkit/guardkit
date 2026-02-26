---
id: TASK-REV-0828
title: Analyse logging_feature_3 autobuild failure — text matching semantic mismatch
status: review_complete
task_type: review
created: 2026-02-25T10:00:00Z
updated: 2026-02-25T10:00:00Z
priority: critical
tags: [autobuild, text-matching, criteria-verification, direct-mode, review, regression-analysis]
complexity: 6
parent_review: TASK-REV-CECA
related_reviews: [TASK-REV-953F]
decision_required: true
---

# Task: Analyse logging_feature_3 autobuild failure — text matching semantic mismatch

## Description

This is the **third consecutive failed autobuild** of FEAT-3CC2 (Structured JSON Logging) on `api_test` with vLLM local backend. The run is captured in `docs/reviews/gb10_local_autobuild/logging_feature_3.md`.

### Series Timeline

| Run | Log File | Fixes Applied Before | Outcome | Root Cause |
|-----|----------|---------------------|---------|------------|
| **1** | `logging_feature_1.md` | None | UNRECOVERABLE_STALL (3 turns) | Data pipeline bugs: requirements dropped, wrong field names |
| **2** | `logging_feature_2.md` | DMCP-001 to 004 (4 fixes) | TIMEOUT (3 turns) | Synthetic pipeline gaps: no report written, state recovery not persisted |
| **3** | `logging_feature_3.md` | ASPF-001 to 007 (7 fixes) | CANCELLED (5 turns, timeout on Turn 5) | **NEW: Text matching semantic mismatch** |

### What Changed Between Run 2 and Run 3

Seven ASPF fixes were implemented following the TASK-REV-953F review:
- **ASPF-001**: Committed DMCP-001 through 004
- **ASPF-002**: State recovery now writes `task_work_results.json` to disk
- **ASPF-003**: Fixed misleading "not found" log message
- **ASPF-004**: SDK subprocess cancellation on feature timeout (SIGTERM)
- **ASPF-005**: Increased SDK turn limit and vLLM context for fresh builds
- **ASPF-006**: Enhanced synthetic report with requirements inference
- **ASPF-007**: Eliminated double-write of `player_turn_N.json`

### Run 3 Key Observations — What IMPROVED

1. **Data pipeline is flowing**: `requirements_met` is now populated (was `[]` in Runs 1-2)
2. **Synthetic path works**: Turn 4 shows `_synthetic: True`, `matching_strategy: promises+hybrid (synthetic)`, 7 file-existence promises generated, 6 `requirements_addressed` inferred (ASPF-006)
3. **Cancellation works**: Turn 5 received SIGTERM correctly (`TASK-FIX-ASPF-004: Sent SIGTERM to child process pid=73372`) — no more zombie Player processes
4. **Progress**: Turn 3 verified 1/7 criteria (vs 0/7 in all previous turns across Runs 1-2)
5. **No stall detection**: Reached Turn 5 (max_turns) instead of stalling at Turn 3

### Run 3 Key Observations — What STILL FAILS

The Coach **still rejects 7/7 criteria on Turns 1-2 and 6/7 on Turn 3** despite `requirements_met` being populated. The root cause has shifted from "data not flowing" to **"text matching algorithm cannot match paraphrased criteria"**.

#### Turn 1 Diagnostic (line 97):
```
requirements_met: ['Add logging settings to core config module', 'Implement logging configuration
  module', 'Write comprehensive tests for logging functionality', 'Support console and file logging
  outputs', 'Support rotating file handlers', 'Add environment variable configuration']
```
The Player produced **generic summaries** of what it did, not text that matches the acceptance criteria.

#### Turn 2 Diagnostic (line 157):
```
requirements_met: ['AC-001: Settings class has log_level field with default INFO', 'AC-002: Settings
  class has log_format field with default json', 'AC-003: log_level is configurable via LOG_LEVEL
  environment variable', 'AC-004: log_format is configurable via LOG_FORMAT environment variable',
  'AC-005: .env.example updated with new variables']
```
The Player produced **closer paraphrases** (with AC-ID prefixes) but WITHOUT backtick formatting and quotation marks. The acceptance criteria have backticks and quotes:
- AC: `` `Settings` class has `log_level` field with default "INFO" ``
- Player: `AC-001: Settings class has log_level field with default INFO`

The text matching fails because:
1. Backtick delimiters (`` ` ``) in AC text vs plain text in Player response
2. Quotation marks (`"INFO"`) in AC text vs plain (`INFO`) in Player response
3. `AC-XXX:` prefix in Player response not present in AC text
4. Turn 1: Player uses completely different wording (summaries vs criteria)

#### Turn 4 (Synthetic) Diagnostic (line 279):
All 7 file-existence promises are `incomplete` with `No file-existence evidence for this criterion`. The synthetic path generates promises but cannot verify content-based criteria like "Settings class has log_level field".

### Comparison: MacBook/Anthropic API Runs (SUCCESS)

The **same feature** (Structured JSON Logging) has been successfully built on MacBook using the Anthropic API:

| Environment | Feature ID | Backend | TASK-LOG-001 | Overall | Duration |
|-------------|-----------|---------|--------------|---------|----------|
| **MacBook** | FEAT-CC79 | Anthropic API | SUCCESS (2 turns) | 5/5 tasks | 24m 6s |
| **GB10** | FEAT-3CC2 | vLLM local | FAILED (5 turns) | 0/5 tasks | >40m |

#### Why MacBook/Anthropic Succeeds

Evidence from `docs/reviews/autobuild-fixes/db_finally_succeds.md` (same codebase, same Coach validator) shows:

1. **Player writes structured reports**: `Recovered 6 requirements_addressed from agent-written player report`
2. **Coach verifies on Turn 1**: `Criteria Progress (Turn 1): 6/6 verified (100%)` — approved immediately
3. **Consistent across features**: FEAT-BA28 (DB Integration) shows same pattern — 5/5 tasks approved on Turn 1, all with 6/6 or 7/7 criteria

The Anthropic API Player produces `requirements_addressed` entries that **closely match** the acceptance criteria text, enabling `_match_by_text` to succeed. The vLLM Player either:
- **Turn 1**: Writes generic summaries ("Add logging settings to core config module") — no resemblance to AC text
- **Turn 2**: Writes closer paraphrases ("AC-001: Settings class has log_level field with default INFO") — close but formatting differs (backticks, quotes stripped, AC-prefix added)

This confirms the issue is **not a Coach bug** but a **model behaviour gap** between Anthropic API and vLLM, amplified by a text matching algorithm that has no tolerance for formatting differences or paraphrasing.

#### Key Question: Should the Coach Be Model-Agnostic?

The Coach's `_match_by_text` algorithm implicitly assumes the Player will echo acceptance criteria verbatim or near-verbatim. This assumption holds for Anthropic's Claude but breaks for local vLLM models. The fix should make the Coach **robust to varying Player output quality**.

## Review Questions

1. **Is the `_match_by_text` algorithm too strict?** How does it compare strings? Does it use exact match, substring, fuzzy matching, or semantic similarity? What threshold is used?

2. **Why did Turn 3 match 1/7 but Turns 1-2 matched 0/7?** What was different about the Player's response on Turn 3? Which criterion was verified?

3. **Should the matching algorithm strip markdown formatting?** Backticks, quotes, and other markdown characters in acceptance criteria create a systematic mismatch with Player responses that don't include formatting.

4. **Should the matching algorithm normalize AC-prefix patterns?** The Player on Turn 2 used `AC-XXX: <criterion text>` format — stripping the prefix would enable matching.

5. **Is the Coach-side codebase verification fallback (P6 from TASK-REV-CECA) now the right approach?** Content-based criteria like "Settings class has log_level field" could be verified by grepping the actual source files rather than relying on text matching Player claims.

6. **Are the ASPF fixes introducing any regressions?** Run current tests.

7. **Why do file-existence promises show "No file-existence evidence" on Turn 4?** The Player created files on Turns 1-3. Are the promises checking the right paths?

8. **What specific differences in Player output exist between Anthropic API and vLLM?** Compare the `requirements_addressed` format from MacBook runs (`db_finally_succeds.md`) against GB10 Run 3 to identify exactly what text normalization would bridge the gap.

## Context: Full Causal Chain Across 3 Runs

```
Run 1: Player writes requirements_addressed, but data dropped in transit
  → Fixed by DMCP-001 to 004

Run 2: Player doesn't write report at all, synthetic fallback has gaps
  → Fixed by ASPF-001 to 007

Run 3: Data flows correctly, but text matching can't match paraphrased text
  → THIS IS THE REMAINING GAP
```

The fixes have been progressively correct — each run surfaces a deeper issue in the criteria verification pipeline:
1. Data pipeline integrity (fixed)
2. Synthetic fallback reliability (fixed)
3. **Semantic matching quality** (current issue)

## Acceptance Criteria

1. Root cause the text matching failure with evidence from `_match_by_text` algorithm
2. Determine why Turn 3 achieved 1/7 vs 0/7 on other turns
3. Assess whether ASPF fixes introduced regressions (run tests)
4. Evaluate the file-existence promise verification failure on Turn 4
5. Recommend specific fixes with effort/risk assessment
6. Consider whether this is fundamentally a text matching problem or whether a different verification approach (e.g., codebase inspection) is needed
7. Compare Anthropic API vs vLLM Player output formats to determine what normalization would make the Coach model-agnostic

## Artifacts to Inspect

### Run Logs
- `docs/reviews/gb10_local_autobuild/logging_feature_1.md` — Run 1
- `docs/reviews/gb10_local_autobuild/logging_feature_2.md` — Run 2
- `docs/reviews/gb10_local_autobuild/logging_feature_3.md` — Run 3

### Previous Reviews
- `.claude/reviews/TASK-REV-CECA-review-report.md` — Run 1 root cause analysis
- `.claude/reviews/TASK-REV-953F-review-report.md` — Run 2 regression analysis
- `tasks/backlog/TASK-REV-953F-analyse-logging-feature-2-autobuild-regression.md` — Run 2 task

### Fix Tasks
- `tasks/completed/TASK-FIX-DMCP-001/` through `TASK-FIX-DMCP-004/` — Run 1 fixes
- `tasks/completed/TASK-FIX-ASPF-001/` through `TASK-FIX-ASPF-007/` — Run 2 fixes

### Successful MacBook/Anthropic Runs (Comparison Baseline)
- `docs/reviews/autobuild-fixes/fast_api_summaries.md` — FEAT-CC79 (Structured JSON Logging) SUCCESS: 5/5 tasks, 9 turns, 24m
- `docs/reviews/autobuild-fixes/db_finally_succeds.md` — FEAT-BA28 (DB Integration) showing Coach criteria verification patterns with Anthropic Player

### Code to Inspect
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_match_by_text()`, `_validate_requirements()`, synthetic fast-path
- `guardkit/orchestrator/agent_invoker.py` — Report handling, synthetic report creation
- `guardkit/orchestrator/synthetic_report.py` — Promise generation, requirements inference
- `guardkit/orchestrator/autobuild.py` — State recovery, criteria progress tracking

## Suggested Review Approach

1. **Read `_match_by_text`**: Understand the exact algorithm — tokenization, normalization, comparison method, threshold
2. **Test with actual data**: Manually run the matching with Run 3 Turn 2 data (Player's `AC-001: Settings class...` against AC `` `Settings` class has `log_level`... ``)
3. **Check Turn 3 delta**: Compare Turn 3's `player_turn_3.json` against Turns 1-2 to find what matched 1/7
4. **Inspect promise verification**: Trace Turn 4's file-existence promise evaluation to understand why all are `incomplete`
5. **Run test suite**: Verify no ASPF regressions
6. **Compare Anthropic vs vLLM output**: Extract `requirements_addressed` from MacBook runs to understand what format the text matching expects, and what normalization would make vLLM output compatible
7. **Recommend approach**: Text normalization vs codebase verification vs fuzzy matching vs hybrid — considering model-agnosticism as a design goal
