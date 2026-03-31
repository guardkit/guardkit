---
id: TASK-REV-8A94
title: Analyse vLLM Qwen3 DB feature autobuild failure on GB10
status: review_complete
review_mode: decision
review_depth: standard
review_results:
  score: 85
  findings_count: 5
  recommendations_count: 7
  decision: implement
  report_path: .claude/reviews/TASK-REV-8A94-review-report.md
  completed_at: 2026-02-26T13:00:00Z
  implementation_tasks:
    - TASK-FIX-VL01
    - TASK-FIX-VL02
    - TASK-FIX-VL03
    - TASK-FIX-VL04
    - TASK-FIX-VL05
    - TASK-FIX-VL06
    - TASK-FIX-VL07
  implementation_guide: tasks/backlog/vllm-autobuild-fixes/IMPLEMENTATION-GUIDE.md
task_type: review
created: 2026-02-26T12:00:00Z
updated: 2026-02-26T12:00:00Z
priority: high
tags: [autobuild, vllm, qwen3, local-llm, debugging, gb10]
complexity: 6
decision_required: true
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse vLLM Qwen3 DB feature autobuild failure on GB10

## Description

Analyse the failing database feature (FEAT-947C - PostgreSQL Database Integration) autobuild output when running via vLLM with Qwen3 Next Coder on the Dell GB10 local hardware. The same feature was previously troublesome with Anthropic models but was eventually resolved successfully.

**Goal**: Identify root causes of failure, compare with the successful Anthropic run, and recommend fixes or configuration changes to enable vLLM/Qwen3 compatibility with GuardKit AutoBuild.

## Context

### Environment
- **Hardware**: Dell GB10 (local)
- **LLM Backend**: vLLM serving Qwen3 Next Coder
- **Endpoint**: `ANTHROPIC_BASE_URL=http://localhost:8000`
- **Feature**: FEAT-947C - PostgreSQL Database Integration (8 tasks, 4 waves)
- **Config**: `--max-turns 5`, `stop_on_failure=True`

### Failing Output
- Primary: `docs/reviews/gb10_local_autobuild/db_feature_1.md`

### Reference (Successful Anthropic Run)
- Success output: `docs/reviews/autobuild-fixes/db_finally_succeds.md`
- Previous fix history: `docs/reviews/autobuild-fixes/` (multiple iterations)

## Observed Failure Pattern

### What Succeeded (2/8 tasks)
- **TASK-DB-001** (Wave 1): Create database infrastructure - APPROVED (1 turn)
- **TASK-DB-003** (Wave 2): Create user model and schemas - APPROVED (1 turn)

### What Failed (2 tasks, Wave 2 stopped remaining 4 waves)
- **TASK-DB-002** (Wave 2): Set up Alembic migrations - TIMEOUT/CANCELLED
- **TASK-DB-004** (Wave 2): Set up database test infrastructure - TIMEOUT/CANCELLED

### Root Cause Indicators

1. **Coach Validation Text Matching Failure (Critical)**
   - TASK-DB-002: `Criteria verification 0/9` - ALL acceptance criteria rejected
   - TASK-DB-004: `Criteria verification 0/7` - ALL acceptance criteria rejected
   - `matching_strategy: text` used (strict text matching)
   - `requirements_met: []` - Player (Qwen3) returned empty requirements_met
   - Player DID complete the work (files created/modified) but Coach couldn't verify
   - Compare: TASK-DB-001 and TASK-DB-003 got `10/10` and `7/7` verified

2. **Empty requirements_met from Qwen3**
   - The Qwen3 model is not populating `requirements_met` in `task_work_results.json`
   - Coach validator relies on text matching between AC text and requirements_met entries
   - When requirements_met is empty, 0 criteria can be verified regardless of actual work done

3. **Timeout Cascade**
   - Turn 1: Coach gives feedback (rejection due to 0 criteria matched)
   - Turn 2: Player re-implements but feature is already timing out
   - TASK-DB-002 ran for 1200+ seconds on turn 2 before cancellation
   - TASK-DB-004 ran for 450+ seconds on turn 2 before cancellation

4. **Configuration Differences vs Successful Anthropic Run**
   - vLLM run: `--max-turns 5`, feature FEAT-947C (8 tasks, 4 waves)
   - Anthropic run: `--max-turns 10`, feature FEAT-BA28 (5 tasks, 4 waves), `--fresh`
   - Anthropic had SDK max_turns=50 vs vLLM had SDK max_turns=100
   - Anthropic environment bootstrapped dependencies; vLLM had "no dependency install available"

5. **Slower Token Generation**
   - vLLM/Qwen3 significantly slower: TASK-DB-001 took ~1650s (27.5 min) vs Anthropic ~400s (6.7 min)
   - 4x slower generation pushes parallel wave tasks toward timeout boundaries

## Key Questions for Review

1. **Why does text matching succeed for DB-001/DB-003 but fail for DB-002/DB-004?**
   - Is Qwen3 inconsistent in how it formats `requirements_met`?
   - Are the AC criteria for DB-002/DB-004 more complex or specific?

2. **Should semantic matching be enabled as default for vLLM/local models?**
   - The text matching strategy requires exact/near-exact text reproduction
   - Local models may paraphrase criteria differently than Anthropic models

3. **Are the timeout values appropriate for local vLLM inference speed?**
   - 40-minute task timeout with 4x slower generation
   - Should `sdk_timeout` and `task_timeout` be configurable per-backend?

4. **What fixes from the Anthropic debugging journey apply here?**
   - The `autobuild-fixes/` directory shows extensive prior debugging
   - Which fixes are model-agnostic vs Anthropic-specific?

5. **Is the feature definition (8 tasks) too granular for local models?**
   - Anthropic success used 5 tasks; this run uses 8 tasks
   - More tasks = more parallel pressure on local hardware

## Acceptance Criteria

- [ ] Root cause of Coach text matching failure for TASK-DB-002 and TASK-DB-004 identified
- [ ] Comparison of Qwen3 vs Anthropic `task_work_results.json` output format documented
- [ ] Recommendations for vLLM/local model autobuild configuration provided
- [ ] Assessment of whether text-matching or semantic-matching strategy should be used
- [ ] Timeout/performance recommendations for local inference documented
- [ ] Actionable fix list prioritised (quick wins vs architectural changes)

## Review Approach

1. **Deep-dive the Coach validator rejection logs** for TASK-DB-002 and TASK-DB-004
2. **Compare player report JSON** structure between successful (DB-001) and failed (DB-002) tasks
3. **Cross-reference with Anthropic success** patterns in `db_finally_succeds.md`
4. **Evaluate matching strategy** options (text vs semantic vs hybrid)
5. **Model the timeout budget** for local inference at observed token rates

## Implementation Notes

This review should produce:
- A findings report with prioritised recommendations
- Specific configuration changes for vLLM/Qwen3 autobuild runs
- Potential code changes to coach_validator or agent_invoker for local model support

## References

| Resource | Location |
|----------|----------|
| Failing Output | `docs/reviews/gb10_local_autobuild/db_feature_1.md` |
| Successful Anthropic Run | `docs/reviews/autobuild-fixes/db_finally_succeds.md` |
| Autobuild Fix History | `docs/reviews/autobuild-fixes/` |
| Coach Validator | `guardkit/orchestrator/quality_gates/coach_validator.py` |
| Agent Invoker | `guardkit/orchestrator/agent_invoker.py` |
| Text Matching Logic | `guardkit/orchestrator/quality_gates/` |

## Test Execution Log

[Automatically populated by /task-review]
