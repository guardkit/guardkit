---
id: TASK-REV-F404
title: Review reseed + guardkit init output (init_project_9)
status: review_complete
created: 2026-03-05T09:00:00Z
updated: 2026-03-05T09:00:00Z
priority: high
task_type: review
review_mode: code-quality
review_depth: standard
complexity: 5
parent_review: TASK-REV-49AB
feature_id: FEAT-SQF
tags: [graphiti, init, seeding, review, falkordb]
---

# Review: Reseed + guardkit init Output (init_project_9)

## Review Scope

Analyse the output of the full reseed + `guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit` run captured in:

**Source file**: `docs/reviews/reduce-static-markdown/reseed_init_project_9.md` (11,292 lines)

## Context

This is the verification run after **FEAT-SQF** (Seed Quality Fixes) — 3 targeted fixes from TASK-REV-49AB findings:

| Task | Fix | Status |
|------|-----|--------|
| TASK-FIX-b06f | Add "templates" to 180s timeout tier in `_create_episode()` | Completed |
| TASK-FIX-bbbd | Return episode counts from `_add_episodes()` for accurate logging | Completed |
| TASK-FIX-ec01 | Fix pattern examples path resolution (CWD → installation dir) | Completed |

### What init_project_8 showed (TASK-REV-49AB findings)

1. **3 template episodes timed out at 120s** → circuit breaker tripped → 5 categories skipped
2. **Misleading "Seeded {category}" logs** even when circuit breaker blocked all episodes
3. **Pattern examples ERROR**: "Pattern files not found: dataclasses, pydantic-models, orchestrators"
4. **Init phase was clean**: `-ext.md` files copying, 3/3 project episodes OK, 392.5s total
5. **Episode 3 (project_architecture) took 249.7s** — borderline but within 300s timeout

## Key Questions for This Review

### Seed Phase Verification
1. Did the template timeout fix work? Are template episodes now completing within 180s?
2. Is the circuit breaker still tripping, or do all 17 categories seed successfully?
3. Are the seed summary logs now accurate (showing actual created/skipped counts)?
4. Did the pattern examples path fix resolve the ERROR? Are pattern files found?
5. What are the episode completion times? Any improvement from clean graph?

### Init Phase Verification
1. Step 1: Are `-ext.md` files still copying correctly?
2. Step 2: Project knowledge seeding — are all 3 episodes completing? What times?
3. Is project_architecture still borderline (~250s) or has it improved?
4. Any new "LLM returned invalid duplicate_facts idx values" warnings?
5. Does the "Next steps: guardkit graphiti seed-system" message still appear?

### Comparison with init_project_8
1. How many seed categories succeed now vs ~12/17 in init_8?
2. Has total seed time changed?
3. Are the FEAT-SQF fixes confirmed effective by log evidence?
4. Any new issues not seen in init_8?

### FEAT-ISF + FEAT-SQF Combined Assessment
1. Are all 9 fix tasks (6 ISF + 3 SQF) validated by this run?
2. Is the init pipeline now production-viable end-to-end?
3. What remains in backlog (FEAT-CR01, FEAT-GE) and is it properly decoupled?

## Acceptance Criteria

- [x] Seed phase analysed: all 17 categories assessed (success/fail/time)
- [x] Template timeout fix verified (TASK-FIX-b06f)
- [x] Episode count logging verified (TASK-FIX-bbbd)
- [x] Pattern path fix verified (TASK-FIX-ec01)
- [x] Init phase analysed: template copy + project seeding
- [x] Comparison with init_project_8 documented
- [x] Combined FEAT-ISF + FEAT-SQF assessment
- [x] Recommendations for remaining work

## Review Results

See: `.claude/reviews/TASK-REV-F404-review-report.md`

### Revision History

- **v1**: Initial review — identified 3 fixes as effective, flagged circuit breaker cascade
- **v2**: CWD investigation — confirmed editable install makes CWD irrelevant for path resolution; revised TASK-FIX-ec01 from "masked by circuit breaker" to "effective"
- **v3**: Deep-dive with C4/sequence diagrams — **corrected root cause**: Run 2 ERROR was pre-fix code (CWD-relative path), NOT circuit breaker. Git history (`a35c2ad27`) proves original code used `Path(".claude/rules/patterns")`. Runs 3-6 succeed because TASK-FIX-ec01 was applied between runs. Added C4 context/container diagrams, 3 sequence diagrams tracing circuit breaker state, and validated root cause summary (Appendices B-D)
