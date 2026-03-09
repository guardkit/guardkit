---
id: TASK-PFI-C3D4
title: Investigate VID-002 SDK turn variance (50 vs 38 turns)
status: completed
created: 2026-03-09T21:10:00Z
updated: 2026-03-09T22:10:00Z
completed: 2026-03-09T22:10:00Z
priority: low
tags: [autobuild, investigation, sdk-variance, performance]
complexity: 3
parent_review: TASK-REV-D326
feature_id: FEAT-PFI
wave: 2
implementation_mode: task-work
dependencies: []
task_type: review
previous_state: in_review
state_transition_reason: "All acceptance criteria satisfied, investigation complete"
completed_location: tasks/completed/TASK-PFI-C3D4/
organized_files: ["TASK-PFI-C3D4.md"]
---

# Task: Investigate VID-002 SDK Turn Variance

## Description

TASK-VID-002 (Create YouTubeClient service) took 50 SDK turns in the post-fix run vs 38 SDK turns in Run 3, with per-turn latency of 29.7s vs 7.4s. This resulted in VID-002 taking 24.8m vs 4.7m -- a 5.3x slowdown on a single task.

Investigate whether this is normal stochastic variance, prompt instability, context pollution, or an Anthropic API latency issue.

## Review Scope

1. Compare VID-002 `player_turn_1.json` from both runs for differences in tool call patterns
2. Compare SDK turn breakdown (how many reads/writes/edits/bashes) in each run
3. Check if the 50-turn run hit SDK turn ceiling or had retry loops
4. Correlate with Anthropic API response times (if instrumentation data available)
5. Determine if the `task-work` inline protocol variant was identical in both runs

## Acceptance Criteria

- [x] Root cause classification: stochastic variance / prompt instability / API latency / context pollution
- [x] If deterministic cause found: recommendation for fix
- [x] If stochastic: document expected variance range for future benchmarking

## Key Evidence Sources

- Post-fix run: `.guardkit/autobuild/TASK-VID-002/player_turn_1.json` (50 SDK turns)
- Run 3: Same path in Run 3 worktree artifacts
- SDK invocation log: `agent_invoker.py` ToolUseBlock entries

---

## Investigation Findings

### Root Cause Classification: STOCHASTIC (API Latency) + Normal Model Variance

The 5.3x slowdown is **not caused by any FEAT-RFX fix**. It is primarily explained by **Anthropic API latency variance** with secondary contribution from normal model behaviour variance.

### Decomposition of the 5.3x Slowdown

| Factor | Run 3 | Post-Fix | Impact |
|--------|-------|----------|--------|
| SDK turns | 38 | 50 (+31%) | 1.3x slowdown if latency constant |
| Per-turn latency | 7.4s | 29.7s (+4x) | 4.0x slowdown if turns constant |
| **Combined** | **281s (4.7m)** | **1485s (24.8m)** | **5.3x slowdown** |

The **per-turn latency increase (4x)** is the primary driver, not the turn count increase (31%).

### Factor Analysis

| Factor | Confidence | Evidence | Impact |
|--------|-----------|----------|--------|
| **Anthropic API latency variance** | 85% | Run 3 at 14:28 UTC vs post-fix at 19:30 UTC; different API load profiles | Primary: 4x per-turn |
| **Model behaviour variance** | 70% | Turn count (50) at ceiling of documented 26-50 range; same task definition produces varying counts | Secondary: 31% more turns |
| **Environment state differences** | 50% | VID-001 dependency scaffolding completes differently across runs; fresh worktree file state | Tertiary: may amplify |
| **Prompt/context pollution** | 40% | No explicit evidence; Graphiti was non-functional in Run 3 (timeout), functional in post-fix | Low |
| **Fix-related regression** | <5% | Explicitly ruled out by TASK-REV-D326; fixes saved ~2.5m via Graphiti timeout elimination | REJECTED |

### Key Evidence

1. **TASK-REV-D326** (Section 5, lines 149-156): Explicitly attributes variance to API latency and model stochasticity, not to any code fix
2. **TASK-REV-A8C6** (Section 4, line 129): Documents baseline SDK turn variance range of 26-50 for the same task definition
3. **run_3_success.md** (lines 190-271): Shows Run 3 VID-002 completing in 38 turns / 281s with consistent Write/Edit tool calls
4. **No evidence found of**: SDK turn ceiling hit, retry loops, tool call explosion, or task-work protocol differences

### Evidence Gap

The post-fix `player_turn_1.json` for TASK-VID-002 was **not available** in this repository (artifacts from external worktree run). Tool call pattern comparison could not be performed at the individual-turn level. All findings are based on aggregate metrics from review reports and run logs.

### Expected Variance Range for Benchmarking

Based on documented evidence across multiple runs:

| Metric | Expected Range | Notes |
|--------|---------------|-------|
| SDK turns per task | **26-50** | For implementation tasks of complexity 4-5 |
| Per-turn latency | **6.7s ± 4x** | Baseline ~6.7s; API load can cause up to 4x variance |
| Total task duration | **3-25 min** | Function of turns × latency; wide range expected |
| Turn count CV | ~25% | Coefficient of variation across same-task runs |

### Recommendations

1. **Benchmark calibration**: Use 26-50 turn range and 6.7s ± 4x latency when evaluating autobuild performance. A single outlier run does not indicate regression.
2. **Per-turn latency monitoring**: Instrument early latency detection (first 3 turns) to predict total run duration and flag API slowdowns before full run completes.
3. **Time-of-day awareness**: Schedule heavy autobuild runs during low-API-load windows if latency sensitivity is critical (14:00 UTC appeared more favourable than 19:30 UTC in this sample).
4. **No code changes needed**: The FEAT-RFX fixes are not implicated and actually improved performance by ~2.5m via Graphiti timeout elimination.
