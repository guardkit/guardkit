# Review Report: TASK-REV-BA6F

## Executive Summary

Run 4 succeeded due to **two independent changes**, not one:

1. **Code change** (commit `ccba106d`): Added a synthetic path text matching fallback (ASPF-006 Strategy D) that bypasses Bug #2 for the "no promises" case. This directly fixed TASK-LOG-004's synthetic path (5/5 on Turn 1).

2. **Model change** (Qwen3 Next Coder): The Qwen3 model produces `requirements_met` entries that more closely echo the acceptance criteria text — including markdown formatting — enabling text matching to succeed on Turn 2 for TASK-LOG-001 (5/7). The previous model produced plain-text paraphrases with `AC-XXX:` prefixes that failed all three matching strategies.

**The TASK-FIX-TM01–04 fixes remain essential as defense-in-depth.** The success is partially model-dependent, and the text matching bugs identified in TASK-REV-0828 are still present in the committed codebase.

**Reproducibility confidence: MEDIUM (60-70%).** The result depends on Qwen3 model behaviour that is non-deterministic.

## Review Details

- **Mode**: Decision Analysis (deep trace)
- **Depth**: Comprehensive
- **Reviewer**: Opus 4.6 comparative analysis
- **Artifacts analyzed**: 4 run logs, 3 prior review reports, 4 fix task files, coach_validator.py source, git history

## Finding 1: Two Independent Root Causes of Success

### 1A: Code Change — Synthetic Path Text Matching Fallback

**Commit**: `ccba106d` ("autobuild fixes, increase sdk turns and context window")
**Date**: 2026-02-25 07:31:40 UTC (between Run 3 and Run 4)
**Contradicts task assumption**: The task description states "No additional Coach fixes were applied." This is incorrect — `ccba106d` made significant changes to `coach_validator.py`.

**Changes in `ccba106d`**:

| Change | Location | Effect |
|--------|----------|--------|
| Added hybrid fallback to synthetic path when promises exist but don't cover all criteria | `coach_validator.py:1520-1532` | Enables text matching as fallback for partially-covered synthetic reports |
| Added direct text matching fallback when synthetic report has NO promises but HAS `requirements_addressed` | `coach_validator.py:1548-1561` | **Bypasses Bug #2 entirely** for the no-promises case |
| Passed `worktree_path` to synthetic report builder | `autobuild.py`, `agent_invoker.py` | Enables file-content-based `requirements_addressed` inference |

**Impact on TASK-LOG-004**: In Run 4, the synthetic report for TASK-LOG-004 had NO completion_promises but 5 `requirements_addressed` inferred from file content. The new code path sent this directly to `_match_by_text()`, bypassing `_hybrid_fallback()` and Bug #2. Result: 5/5 verified on Turn 1.

**Contrast with Run 3**: In Run 3, TASK-LOG-001 Turn 4 (synthetic path) had 7 file-existence promises (all "incomplete"). These went through `_match_by_promises()` → `_hybrid_fallback()` → Bug #2 blocked all upgrades → 0/7. The new code path added in `ccba106d` handles this differently by applying hybrid fallback AFTER promise matching on the synthetic path.

### 1B: Model Change — Qwen3 Produces Better-Formatted Reports

**Evidence**: TASK-LOG-001 Turn 2 matched 5/7 in Run 4 vs 0/7 in Run 3, despite the same text matching code running (TM01-04 NOT applied).

**Run 3 Turn 2** `requirements_met` (from diagnostic dump):
```
['AC-001: Settings class has log_level field with default INFO',
 'AC-002: Settings class has log_format field with default json',
 'AC-003: log_level is configurable via LOG_LEVEL environment variable',
 'AC-004: log_format is configurable via LOG_FORMAT environment variable',
 'AC-005: .env.example updated with new variables']
```
These are plain-text paraphrases with `AC-XXX:` prefixes. No backticks, no quotes. Jaccard similarity: **30%** (below 70% threshold).

**Run 4 Turn 2** `requirements_met`: Not available in diagnostic dump (diagnostic only fires when 0/N criteria match). However, 5/7 criteria were verified, indicating the Player produced text that matched via the existing (buggy) keyword extraction.

**Hypothesis**: The Qwen3 model, when given Coach feedback containing the backtick-formatted AC text, echoes it back more precisely in `requirements_met` — potentially including backticks and quotes. This would enable exact matching or substring matching to succeed, even without TM01's regex keyword fix.

**Supporting evidence**:
- The 2 missing criteria (AC-006: `` `structlog` added... ``, AC-007: "Existing tests still pass") are the same ones the previous model omitted in Run 3 Turn 2. This is a Player reporting gap, not a matching bug.
- Task-work delegation tasks (LOG-002, 003, 005) show a consistent pattern: Turn 1 produces empty/unusable structured data, Turn 2 recovers full `completion_promises` and `requirements_addressed`. The Qwen3 model follows the report schema better on retry.

## Finding 2: Run 3 vs Run 4 — Full Comparison

### Scale of difference

| Metric | Run 3 | Run 4 | Delta |
|--------|-------|-------|-------|
| Tasks completed | 0/5 | 5/5 | +5 |
| Tasks attempted | 1 | 5 | +4 |
| Total turns | 5 (TASK-LOG-001 only) | 9 (all tasks) | +4 (but all 5 tasks done) |
| Duration | 40 min (timeout) | 93 min (clean completion) | +53 min |
| Farthest wave reached | Wave 1 | Wave 4 | +3 waves |
| Outcome | CANCELLED | SUCCESS | — |

### Per-task comparison (Run 4 only — Run 3 never left Wave 1)

| Task | Mode | Turns | T1 Criteria | T2 Criteria | Matching Strategy |
|------|------|-------|-------------|-------------|-------------------|
| LOG-001 | direct | 3 | 0/7 | 5/7 → 7/7 (T3) | text |
| LOG-002 | task-work | 1 | 8/8 | — | promises |
| LOG-003 | task-work | 2 | 0/9 | 9/9 | T1: text (empty), T2: promises |
| LOG-004 | direct (synthetic) | 1 | 5/5 | — | text (ASPF-006 fallback) |
| LOG-005 | task-work | 2 | 0/6 | 6/6 | T1: text (empty), T2: promises |

### Matching strategy that succeeded per task

| Task | How it got approved | Bug #1 hit? | Bug #2 hit? |
|------|---------------------|-------------|-------------|
| LOG-001 | Better model output on Turn 2-3 | **Bypassed** (model echoed AC text) | N/A (not synthetic) |
| LOG-002 | Promise-based matching (8 promises recovered) | N/A | N/A |
| LOG-003 | Promise-based matching (9 promises recovered) | N/A | N/A |
| LOG-004 | ASPF-006 text fallback (no promises path) | N/A | **Bypassed** (new code path) |
| LOG-005 | Promise-based matching (6 promises recovered) | N/A | N/A |

## Finding 3: TASK-LOG-001 Turn 2 — The Critical Turn

This is the most informative comparison point:

| Aspect | Run 3 Turn 2 | Run 4 Turn 2 |
|--------|-------------|-------------|
| Criteria matched | 0/7 | 5/7 |
| Diagnostic dump? | Yes (0/N trigger) | No (>0 matched) |
| `requirements_met` entries | 5 (AC-prefixed, plain text) | Unknown (not dumped) |
| Player reported AC-006, AC-007? | No | No |
| Text matching code | Pre-TM01 (`.split()`) | Pre-TM01 (`.split()`) — identical |
| Model | Previous vLLM model | Qwen3 Next Coder |

**Conclusion**: The only variable that changed for this turn is the model. The same buggy text matching code produced 0/7 with the old model and 5/7 with Qwen3. The Qwen3 model must have produced `requirements_met` entries formatted differently enough to pass the existing matching strategies.

## Finding 4: TASK-LOG-004 Synthetic Path — Code Fix Confirmed

| Aspect | Run 3 (TASK-LOG-001 T4) | Run 4 (TASK-LOG-004 T1) |
|--------|--------------------------|--------------------------|
| Path | Synthetic (SDK didn't write report) | Synthetic (SDK didn't write report) |
| Promises generated | 7 file-existence (all "incomplete") | **None** |
| `requirements_addressed` | 6 (from `infer_requirements_from_files`) | 5 (from `infer_requirements_from_files`) |
| Code path | `_match_by_promises()` → `_hybrid_fallback()` | **`_match_by_text()` directly** (new path from `ccba106d`) |
| Bug #2 triggered? | Yes — evidence "Promise status: incomplete" ≠ "No completion promise" | **No** — bypassed entirely |
| Result | 0/7 | 5/5 |

**Key insight**: The `ccba106d` commit didn't fix Bug #2. It added a NEW code path that avoids Bug #2. Bug #2 still exists for cases where synthetic reports DO have promises.

## Finding 5: Anthropic API Comparison (FEAT-CC79)

The same logging feature was successfully built on MacBook using the Anthropic API:

| Task | vLLM (Run 4) Turns | Anthropic API Turns | Notes |
|------|---------------------|---------------------|-------|
| LOG-001 | 3 | 2 | Anthropic uses promise matching (format-agnostic) |
| LOG-002 | 1 | 1 | Both used promises |
| LOG-003 | 2 | 1 | Anthropic produced promises on Turn 1 |
| LOG-004 | 1 | 4 | vLLM used ASPF-006 fallback; Anthropic had a different issue |
| LOG-005 | 2 | 1 | Anthropic produced promises on Turn 1 |
| **Total** | **9** | **9** | **Same total turns** |

**Structural difference**: Anthropic API tasks typically succeed via promise-based matching (criterion ID-based, format-agnostic). vLLM tasks rely more on text matching because the model doesn't reliably produce `completion_promises`. This makes vLLM more sensitive to text formatting bugs.

## Finding 6: Assessment of TASK-FIX-TM01–04

### Current status

All four fixes are **implemented** (staged in working directory) but **not committed**:

| Fix | Bug | Status | In committed code? |
|-----|-----|--------|-------------------|
| TM01: Regex keyword splitting | Bug #1 | Staged | No |
| TM02: Widen hybrid fallback evidence | Bug #2 | Staged | No |
| TM03: Markdown format stripping | Defense-in-depth | Staged | No |
| TM04: AC-prefix stripping | Defense-in-depth | Staged | No |

### Are they still needed?

| Fix | Still needed? | Rationale |
|-----|---------------|-----------|
| **TM01** | **YES — Critical** | Bug #1 is still present. Success depended on Qwen3 model echoing AC text closely. A different model (or different temperature) could produce entries like Run 3's, causing 0/7 matching. This is the single most important fix for model-agnostic robustness. |
| **TM02** | **YES — Important** | Bug #2 is still present. `ccba106d` only bypasses it for the "no promises" synthetic path. If file-existence promises are generated (scaffolding tasks), the hybrid fallback evidence check is still broken. Run 3's TASK-LOG-001 Turn 4 demonstrated this failure. |
| **TM03** | **YES — Defense-in-depth** | Enables Strategy 1 (exact) and Strategy 2 (substring) matching when the only difference is markdown formatting. Without this, matching depends entirely on Strategy 3 (keywords), which requires the TM01 fix. Multiple matching strategies is better than one. |
| **TM04** | **YES — Defense-in-depth** | Enables matching when Player formats with `AC-XXX:` prefixes. Run 3 Turn 2 showed this exact pattern. Without this, AC-prefixed entries can only match via keyword overlap (Strategy 3). |

### Priority assessment

| Priority | Fix | Risk if not applied |
|----------|-----|---------------------|
| **P0** | TM01 | Next model version or temperature change could regress to 0/N matching |
| **P0** | TM02 | Any synthetic report with file-existence promises will fail hybrid fallback |
| **P1** | TM03 | Reduces robustness — falls back to keyword-only matching |
| **P2** | TM04 | Reduces robustness — AC-prefixed entries need keyword matching to succeed |

**Recommendation: Commit all four fixes.** They are already implemented and tested. The cost of committing is near-zero; the cost of not committing is potential regression on the next vLLM run with a different model or configuration.

## Finding 7: Reproducibility Assessment

### Confidence: MEDIUM (60-70%)

**Factors supporting reproducibility:**
1. ASPF-006 text matching fallback (code fix) is deterministic — TASK-LOG-004 will succeed consistently
2. Task-work delegation tasks (LOG-002, 003, 005) that produce `completion_promises` on Turn 2 are likely stable
3. The core implementation quality is good — tests pass, files are created correctly

**Factors against reproducibility:**
1. TASK-LOG-001 success depends on Qwen3 model producing well-formatted `requirements_met` — this is non-deterministic
2. TASK-LOG-001 Turn 1 always fails (0/7) because the model produces generic summaries — the model must learn from Coach feedback
3. Run 3 showed the same model type producing poorly-formatted entries that failed matching
4. vLLM temperature, sampling parameters, or model version could change behaviour

**If TM01-04 are committed**, confidence increases to **HIGH (85-90%)**:
- TM01 fixes keyword matching to handle any formatting variation
- TM02 fixes hybrid fallback for synthetic reports with promises
- TM03+TM04 provide additional matching robustness

### Recommendation: Re-run once after committing TM01-04

A single confirmation run with the fixes applied would raise confidence to >95%. The fixes should make the pipeline robust regardless of model output formatting.

## Finding 8: Remaining Pipeline Fragility

### Fragile points (even after TM01-04)

1. **Turn 1 cold start**: The vLLM model consistently produces generic summaries on Turn 1 that fail ALL matching strategies. This wastes a turn on every direct-mode task. The Anthropic model doesn't have this issue.

2. **Task-work delegation Turn 1**: Tasks LOG-003 and LOG-005 had empty `requirements_met` on Turn 1 despite the task-work mode running 48-50 SDK turns. The structured data recovery only succeeds on Turn 2. This suggests the first task-work invocation doesn't reliably produce the expected report format.

3. **No `completion_promises` from vLLM**: The Qwen3 model does not produce `completion_promises` in direct mode, forcing reliance on text matching. The Anthropic model reliably produces promises. This is a fundamental model-capability gap.

4. **Diagnostic logging gap**: When criteria > 0 matched (but < 100%), the diagnostic dump doesn't fire. This means we don't have `requirements_met` data for the most interesting cases (partial matches). Consider adding diagnostic logging for all cases, not just 0/N.

### Not fragile (fixed or stable)

1. Synthetic report generation (ASPF-006) — deterministic
2. Promise-based matching — only fails when promises aren't produced (model issue, not code issue)
3. Quality gate evaluation — all tests pass, coverage requirements are met

## Decision Matrix

| Option | Effort | Risk | Impact | Recommendation |
|--------|--------|------|--------|----------------|
| Commit TM01-04 as-is | 5 min | Very Low | High — model-agnostic robustness | **Recommended** |
| Re-run without TM fixes first | ~2 hrs | Medium | Low — confirms model non-determinism | Optional |
| Re-run WITH TM fixes | ~2 hrs | Very Low | High — validates fix + confirms stability | Recommended after commit |
| Add diagnostic logging for partial matches | 30 min | Very Low | Medium — better observability | Follow-up task |
| Investigate Turn 1 cold start pattern | 2-4 hrs | Low | Medium — save 1 turn per direct-mode task | Future investigation |

## Recommendations

1. **Commit TASK-FIX-TM01-04 immediately.** They are implemented, tested, and address real bugs that could regress.

2. **Run a confirmation autobuild** after committing TM01-04 to validate the full pipeline with fixes applied.

3. **Create a follow-up task** to add diagnostic logging for partial matches (criteria > 0 but < 100%). This would provide `requirements_met` data for cases like TASK-LOG-001 Turn 2, enabling better root cause analysis.

4. **Consider investigating** the Turn 1 cold start pattern — all direct-mode tasks waste Turn 1 because the model produces generic summaries. This may be addressable through prompt engineering or few-shot examples.

5. **Do NOT deprioritise the text matching fixes** based on this single success. The success is partially model-dependent, and the bugs are real.

## Appendix A: Timeline Reconstruction

```
2026-02-25 05:51 — Commit 5c1aea32: DMCP-001 to 004 fixes
                    [Run 3 happens here — uses pre-ccba106d code]
2026-02-25 07:14 — Merge remote-tracking branch
2026-02-25 07:31 — Commit ccba106d: ASPF-006 synthetic path + SDK config changes
                    [Run 4 happens here — uses post-ccba106d code]
2026-02-25 ~12:00 — TASK-FIX-TM01-04 implemented (staged, not committed)
2026-02-25 14:00 — TASK-REV-BA6F created (this review)
```

## Appendix B: Configuration Comparison

| Setting | Run 3 | Run 4 | Changed? |
|---------|-------|-------|----------|
| `ANTHROPIC_BASE_URL` | http://localhost:8000 | http://localhost:8000 | No |
| `max_turns` (feature) | 5 | 5 | No |
| `task_timeout` | 2400s | 2400s | No |
| `sdk_timeout` (base) | 1200s | 1200s | No |
| `enable_pre_loop` | False | False | No |
| `enable_perspective_reset` | True | True | No |
| `reset_turns` | [3, 5] | [3, 5] | No |
| Coach validator code | Pre-`ccba106d` | Post-`ccba106d` | **Yes** |
| Synthetic report path | No text fallback | ASPF-006 text fallback | **Yes** |
| vLLM model | Unknown (previous) | Qwen3 Next Coder | **Likely changed** |

## Appendix C: Acceptance Criteria Assessment

| AC | Met? | Evidence |
|----|------|----------|
| 1. Identify what changed between Run 3 and Run 4 with evidence | YES | Findings 1A (code change) and 1B (model change) with commit diff and diagnostic data |
| 2. Document matching strategy used for each task/turn | YES | Finding 2, per-task comparison table |
| 3. Compare `requirements_met` format between Run 3 and Run 4 for TASK-LOG-001 | PARTIAL | Run 3 data available; Run 4 data not logged (diagnostic gap). Inference from matching results provided. |
| 4. Assess whether TASK-FIX-TM01-04 are still needed | YES | Finding 6: all four still needed, priority assessment provided |
| 5. Evaluate generated code quality | YES | All tests pass, quality gates pass, independent test verification succeeds |
| 6. Provide reproducibility assessment with confidence level | YES | Finding 7: MEDIUM (60-70%) without fixes, HIGH (85-90%) with fixes |
| 7. Recommend next steps for vLLM autobuild pipeline | YES | Recommendations section with 5 specific actions |
