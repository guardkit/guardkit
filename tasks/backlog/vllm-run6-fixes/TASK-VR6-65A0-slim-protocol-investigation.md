---
id: TASK-VR6-65A0
title: Investigate slim protocol turn inflation on vLLM backend
status: backlog
task_type: review
review_mode: decision
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: medium
complexity: 4
wave: 2
implementation_mode: direct
parent_review: TASK-REV-35DC
feature_id: FEAT-81DD
tags: [autobuild, protocol, vllm, profiling, investigation]
dependencies: [TASK-VR6-3B1F]
---

# Task: Investigate slim protocol turn inflation on vLLM backend

## Description

The slim protocol (TASK-VOPT-001, 5.5KB) causes 50-174% more SDK turns compared to the full protocol (19KB) on the vLLM backend. This investigation should determine whether a "medium" protocol variant or other mitigation is warranted.

## Context

### Protocol Comparison

| Protocol | Size | FBP-001 turns | FBP-006 turns | Source |
|----------|------|---------------|---------------|--------|
| Full (19KB) | 19,270 bytes | 37 | 43 | Run 4 |
| Slim (5.5KB) | 5,587 bytes | 46-58 | 110-118 | Runs 5-6 |

### What Slim Removes

- Detailed Docker setup (58 lines → single-line)
- Stack patterns with error handling (47 lines → one sentence)
- Fix loop pseudocode (34 lines → one paragraph)
- Anti-stub rules with REJECTED/ACCEPTED examples (88 lines → one sentence)
- SOLID/DRY/YAGNI explanations (48 lines → one checklist)
- Report schema documentation (80 lines → minimal example)

### What Slim Preserves

- File count constraints table
- Quality gate thresholds
- Core phase structure (3-5.5)
- Completion promises requirement

### Confounding Factor (Commit 821dfda5)

The session resume feature (TASK-RFX-B20B) may partially mitigate turn inflation by preserving context between turns. This should be measured in the next profiling run before concluding slim protocol is the sole cause.

## Review Scope

1. **Measure**: Per-turn latency savings from slim vs full (prompt tokens saved × $/token)
2. **Measure**: Total duration cost from additional turns (extra turns × avg turn time)
3. **Analyse**: Which removed sections correlate most with turn inflation?
4. **Consider**: A "medium" protocol (~10KB) retaining anti-stub rules and stack patterns
5. **Consider**: Keeping slim but raising SDK max turns from 100 → 150 for local backends
6. **Recommend**: Best configuration for Run 7

## Files to Examine

- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (full, 573 lines)
- `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md` (slim, 131 lines)
- `guardkit/orchestrator/agent_invoker.py:4028-4035` (selection logic)
- `guardkit/orchestrator/agent_invoker.py:825-835` (SDK max turns reduction)

## Acceptance Criteria

- [ ] Quantified per-turn latency delta between slim and full protocols
- [ ] Quantified total duration delta attributable to turn inflation
- [ ] Identified which removed protocol sections correlate with turn inflation
- [ ] Recommendation: keep slim / create medium / revert to full / raise max turns
- [ ] Risk assessment of recommended change
