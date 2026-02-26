# Implementation Guide: Text Matching Semantic Fix

**Feature**: FEAT-TM-FIX — Fix Coach validator text matching for model-agnostic criteria verification
**Parent Review**: TASK-REV-0828
**Target File**: `guardkit/orchestrator/quality_gates/coach_validator.py`

## Problem Statement

The Coach's criteria verification pipeline has two bugs that prevent text-based matching from working when the Player (especially local vLLM models) produces paraphrased or reformatted acceptance criteria text. The Anthropic API path is unaffected because it uses ID-based promise matching.

## Wave Breakdown

### Wave 1: Critical Bug Fixes (P0) — Parallel

These two fixes are independent and can be implemented in parallel.

| Task | Title | Complexity | Mode | Files |
|------|-------|-----------|------|-------|
| TASK-FIX-TM01 | Align `_extract_keywords()` regex | 2 | task-work | coach_validator.py |
| TASK-FIX-TM02 | Widen `_hybrid_fallback()` evidence | 3 | task-work | coach_validator.py |

**Parallel execution**: Both tasks modify different methods in the same file. No merge conflicts expected as changes are in separate line ranges (L1868 vs L2060-2063).

**Conductor workspaces**:
- `text-matching-fix-wave1-1` → TASK-FIX-TM01
- `text-matching-fix-wave1-2` → TASK-FIX-TM02

### Wave 2: Defense-in-Depth (P1-P2) — Parallel

These enhance matching robustness but are not strictly required if Wave 1 succeeds.

| Task | Title | Complexity | Mode | Files |
|------|-------|-----------|------|-------|
| TASK-FIX-TM03 | Markdown formatting stripping | 2 | task-work | coach_validator.py |
| TASK-FIX-TM04 | AC-XXX prefix stripping | 1 | direct | coach_validator.py |

**Dependencies**: Wave 2 depends on Wave 1 completion (same file modifications).

**Conductor workspaces**:
- `text-matching-fix-wave2-1` → TASK-FIX-TM03
- `text-matching-fix-wave2-2` → TASK-FIX-TM04

## Architectural Invariants

ALL fixes must preserve these 6 invariants documented in the review:

| ID | Invariant | Verification |
|----|-----------|-------------|
| INV-1 | `_match_by_promises()` ID-based path untouched | No changes to L1713-1801 |
| INV-2 | Hybrid fallback architecture (TASK-REV-E719) preserved | Fix 2 strengthens, doesn't weaken |
| INV-3 | Synthetic report pipeline (ASPF fixes) preserved | No changes to synthetic_report.py |
| INV-4 | `_strip_criterion_prefix()` existing patterns preserved | Fix 4 extends, doesn't replace |
| INV-5 | Artifact store read/write paths preserved | No changes to agent_invoker.py |
| INV-6 | `_extract_criterion_keywords()` regex approach is reference | Fix 1 aligns with this |

## Testing Strategy

After implementing ALL fixes, run the full test suite:

```bash
# Coach validator tests
python3 -m pytest tests/unit/test_coach_validator*.py -v

# Synthetic report tests
python3 -m pytest tests/unit/test_synthetic_report*.py -v

# Autobuild integration tests
python3 -m pytest tests/unit/test_autobuild*.py -v

# Full targeted suite
python3 -m pytest tests/unit/test_coach_validator*.py tests/unit/test_synthetic_report*.py tests/unit/test_autobuild*.py -v --tb=short
```

## Verification: Re-run logging_feature_3

After all fixes are applied, re-run the autobuild for FEAT-3CC2 on GB10 with vLLM to verify:
- Turn 2: ≥5/7 criteria matched (was 0/7)
- Turn 3: ≥2/7 criteria matched (was 1/7)
- Turn 4 (synthetic): ≥6/7 criteria matched (was 0/7)

## Risk Assessment

**Anthropic API regression risk**: ZERO — all fixes target the text-matching fallback path that is only used when `completion_promises` are absent. Anthropic models produce promises, so they always take the ID-based matching path (INV-1).

## Reference

- Review report: `.claude/reviews/TASK-REV-0828-review-report.md`
- Run 3 log: `docs/reviews/gb10_local_autobuild/logging_feature_3.md`
- Previous reviews: TASK-REV-CECA (Run 1), TASK-REV-953F (Run 2)
