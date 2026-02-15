# Warnings & Risks: FEAT-BAE2 (AutoBuild Context Payload Optimization)

**Source**: [FEAT-AUTOBUILD-CONTEXT-OPT-spec.md](../../docs/features/FEAT-AUTOBUILD-CONTEXT-OPT-spec.md)

## Risk Assessment

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Prompt quality degradation** — missing context from full spec causes Player to produce lower-quality output | Medium | High | Extract protocol carefully; test on real tasks before committing; compare output quality side-by-side |
| 2 | **TaskWorkStreamParser incompatibility** — new prompt format produces output that regex parser can't parse | Low | High | Parser uses regex on output text; prompt instructs same output format; test parsing against actual output |
| 3 | **Coach validation breaks** — Coach can't validate Player output from new prompts | Low | High | Coach reads `player_turn_N.json` and `task_work_results.json` — JSON schema unchanged; verify end-to-end |
| 4 | **Interactive /task-work regression** — changes accidentally affect the interactive CLI path | Very Low | Critical | Zero changes to interactive path; only autobuild invocation path changes; regression tests in TASK-ACO-005 |
| 5 | **Direct mode auto-detection false positives** — tasks incorrectly routed to direct mode miss needed review | Low | Medium | Conservative criteria (complexity <=3 AND no risk keywords); log all auto-detections for observability |

## Key Constraint

The interactive `/task-work` command path must remain **completely untouched**. All changes are isolated to the AutoBuild invocation path in `agent_invoker.py` and `task_work_interface.py`.

## Deferred Risks (Out of Scope)

These items from review TASK-REV-A781 are intentionally deferred:

| Item | Description | Why Deferred |
|------|-------------|-------------|
| R2 | Merge pre-loop and Player Turn 1 into single SDK session | Higher architectural risk; needs separate design |
| R5 | SDK-level prompt caching or session reuse | Depends on Claude Agent SDK capabilities not yet available |
