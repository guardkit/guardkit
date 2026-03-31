---
id: TASK-REV-5E93
title: Review vLLM performance and context retrieval for Dell ProMax GB10
status: backlog
created: 2026-03-07T00:00:00Z
updated: 2026-03-07T00:00:00Z
priority: high
tags: [vllm, performance, context-retrieval, dell-promax-gb10, autobuild, review]
task_type: review
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review vLLM Performance and Context Retrieval for Dell ProMax GB10

## Description

Analyse the performance aspects and context retrieval behaviour from the vLLM autobuild run documented in `docs/reviews/vllm-profiling/vllm_run_1.md`. The run crashed with the same CancelledError that also occurred on the Anthropic API run (documented in `docs/reviews/vllm-profiling/anthropic_run_1.md`). Root cause analysis is documented in `docs/reviews/vllm-profiling/c4-sequence-diagrams.md`.

The CancelledError fix has been implemented (see `cancelled-error-fix` task folder). Before re-running the autobuild for FEAT-1637 with these fixes on the Dell ProMax GB10 with vLLM, this review should identify any additional performance optimisations needed.

## Context

### Infrastructure Environment

The development environment spans three machines connected via **Tailscale** mesh VPN:

| Machine | Tailscale Hostname | Role | Services |
|---------|-------------------|------|----------|
| **Dell ProMax GB10** | `promaxgb10-41b1` | GPU compute | vLLM (LLM serving for autobuild + Graphiti LLM/embedding services), Linux 6.17.0-1008-nvidia |
| **Synology NAS** | `whitestocks` | Database | FalkorDB (graph database for Graphiti - NOT Neo4j), Linux 4.4.180+ |
| **MacBook Pro** | `richards-macbook-pro` | Development | GuardKit development, Graphiti seeding, `guardkit init`, macOS 15.6.1 |

All three machines are on Tailscale v1.94.2 (GB10 + MacBook) / v1.58.2-1 (Synology). GB10 and Synology NAS show as **Connected**; MacBook Pro was last seen 11:36 AM GMT.

**Important**: Graphiti uses **FalkorDB** on the Synology NAS, not Neo4j. Any references to Neo4j in code/config are outdated and incorrect. The embedding and LLM services that Graphiti requires are served by vLLM on the same Dell GB10.

**Recent validation**: Graphiti seeding and GuardKit project init have been successfully tested from the MacBook Pro over the past few days, with vLLM on the GB10 serving the Graphiti LLM/embedding needs correctly. This confirms the infrastructure works end-to-end.

### What Happened
- **Feature**: FEAT-1637 (FastAPI Base Project, 7 tasks, 5 waves)
- **Platform**: Dell ProMax GB10 running vLLM locally
- **Crash**: `AttributeError: 'CancelledError' object has no attribute 'success'` at feature_orchestrator.py:1564
- **Root Cause**: CancelledError (BaseException, not Exception on Python 3.9+) escaped through 5 unguarded `except Exception` handlers
- **Same crash occurred** on Anthropic API run (anthropic_run_1.md), confirming it's a GuardKit bug, not vLLM-specific

### Key Observations from vLLM Run
1. **Timeout multiplier**: 4.0x applied for local backend (sdk_timeout base=1200s, effective max up to 14400s)
2. **SDK max turns reduced**: to 50 for local backend
3. **Context loading disabled**: "Graphiti not available - context loading disabled for this run"
4. **Task execution times**: Single tasks taking 1140s+ (19 min) on Turn 1 (TASK-FBP-001)
5. **Parallel wave execution**: Wave 2 ran TASK-FBP-002 + TASK-FBP-004 in parallel (max_parallel=2)
6. **Crash occurred during Wave 4**: After successful completion of waves 1-3 and TASK-FBP-006 in wave 4, TASK-FBP-007 triggered the CancelledError

### Existing Fix Tasks
- `tasks/backlog/cancelled-error-fix/` - CancelledError handling fix
- `tasks/backlog/vllm-gb10-production-readiness/` - vLLM production readiness tasks
- `tasks/backlog/autobuild-stall-detection/` - Stall detection improvements
- `tasks/backlog/autobuild-context-opt/` - Context optimisation
- `tasks/backlog/context-reduction/` - Context reduction tasks

## Review Objectives

### 1. Performance Analysis
- [ ] Compare vLLM vs Anthropic API task execution times for equivalent tasks
- [ ] Analyse token generation speed and latency patterns from vLLM logs
- [ ] Evaluate whether 4.0x timeout multiplier is appropriate or needs tuning
- [ ] Assess impact of max_parallel=2 on GPU memory/compute utilisation
- [ ] Review whether SDK max turns=50 is sufficient for local backend
- [ ] Identify any vLLM-specific performance bottlenecks (prefill vs decode, KV cache, etc.)
- [ ] **Assess vLLM dual-role contention**: vLLM on GB10 serves both autobuild LLM requests AND Graphiti's LLM/embedding needs - evaluate whether concurrent usage causes contention, queue delays, or GPU memory pressure when Graphiti context is enabled alongside autobuild tasks

### 2. Graphiti Context Retrieval - Deep Investigation (CRITICAL)

Graphiti context retrieval is **expected to be fully working** but is completely failing in this run. This is a critical issue that must be root-caused before the next run.

#### Evidence of Failure
- FeatureOrchestrator initialises with `enable_context=True` (line 7) - correctly configured
- Immediately fails: `"Graphiti factory not available or disabled, disabling context loading"` (line 35)
- **All 7 AutoBuildOrchestrators** show `enable_context=False, context_loader=None, factory=None` - context completely bypassed
- **Paradox**: Graphiti thread clients ARE being created later (`"Graphiti factory: thread client created (pending init)"` at lines 159, 369, 476, 682, 860, 1291) - so the Graphiti library IS available
- This suggests a **factory initialisation ordering bug**: the factory availability check runs before the factory is created, or the factory creation at the FeatureOrchestrator level fails silently while task-level creation succeeds
- **Key context**: Graphiti seeding and `guardkit init` have been validated working from the MacBook Pro over the past few days, with vLLM on GB10 serving Graphiti's LLM/embedding needs. This proves the infrastructure (FalkorDB on Synology NAS, vLLM on GB10, Tailscale networking) is functional - the failure is in the autobuild orchestrator's factory wiring, not the infrastructure

#### Investigation Items
- [ ] **Root cause the factory availability check failure**: Why does FeatureOrchestrator say "not available" when Graphiti IS importable (proven by later thread client creation)?
- [ ] **Check FalkorDB/Graphiti service connectivity**: Is FalkorDB reachable on the Synology NAS via Tailscale? Are the Graphiti LLM/embedding endpoints on vLLM (GB10) accessible? Are environment variables (FALKORDB_URL, GRAPHITI_URL, embedding endpoint, etc.) correctly configured?
- [ ] **Check for stale Neo4j references**: Any remaining NEO4J_URI or Neo4j config in the codebase is outdated - identify and flag for removal
- [ ] **Trace the factory creation path**: Does the FeatureOrchestrator try to create a GraphitiFactory before the availability check? What exception is silently swallowed?
- [ ] **Review graphiti-context-wiring task**: Check if the wiring fix in `tasks/backlog/graphiti-context-wiring/` addresses this specific issue
- [ ] **Review graphiti-lifecycle-fix task**: Check if `tasks/backlog/graphiti-lifecycle-fix/` (enable-context-guard, shutdown-suppression) is relevant
- [ ] **Check if context was available on Anthropic run**: Compare anthropic_run_1.md to see if Graphiti also failed there (given infra is proven working from MacBook Pro, this is likely a code-level bug in the autobuild orchestrator path)
- [ ] **Verify the enable_context flag propagation**: FeatureOrchestrator has `enable_context=True` but all AutoBuildOrchestrators get `enable_context=False` - trace the code path that disables it
- [ ] **Assess impact on code quality**: Without Graphiti context, the LLM has no project knowledge, patterns, or previous decisions - quantify quality impact

#### Context Loading Analysis
- [ ] Evaluate inline protocol size (~19KB) relative to vLLM context window limits
- [ ] Determine if CLAUDE.md/rules loading is consuming excessive context for local models
- [ ] Assess whether context loading (when fixed) will cause performance degradation on vLLM
- [ ] Review if context should be selectively loaded (e.g., only for complex tasks) to manage token budget

### 3. Dell ProMax GB10 Optimisation Recommendations
- [ ] Recommend vLLM serving parameters (tensor parallelism, max_model_len, gpu_memory_utilization)
- [ ] Evaluate whether model quantisation (AWQ/GPTQ) would help with the available GPU
- [ ] Assess optimal max_parallel setting for the hardware
- [ ] Consider batching strategy for parallel wave execution
- [ ] Review if environment bootstrapping (pip installs) should be pre-cached

### 4. Pre-Run Checklist for Next Attempt
- [ ] Confirm CancelledError fix is deployed
- [ ] **Verify Graphiti context is working**: Run a quick test to confirm factory initialisation succeeds and context loading is enabled
- [ ] **Verify FalkorDB is reachable** on the Synology NAS via Tailscale, and Graphiti LLM/embedding endpoints on vLLM (GB10) are accessible
- [ ] **Confirm enable_context=True propagates** to AutoBuildOrchestrator (not silently disabled)
- [ ] Verify timeout settings are appropriate
- [ ] Check vLLM model is warmed up before starting
- [ ] Ensure sufficient GPU memory headroom for parallel tasks
- [ ] Consider running with --verbose for detailed profiling

## Acceptance Criteria

- [ ] **Graphiti root cause identified**: Why "factory not available" when Graphiti IS importable
- [ ] **Graphiti fix verified or new task created**: Either confirm existing fix tasks cover this, or create new task
- [ ] Performance comparison table: vLLM vs Anthropic API per-task
- [ ] Specific vLLM parameter recommendations for Dell ProMax GB10
- [ ] Context retrieval strategy recommendation (when Graphiti is fixed)
- [ ] Updated timeout/parallel settings recommendation
- [ ] Pre-run checklist with specific commands/settings (including Graphiti verification)

## Reference Files
- `docs/reviews/vllm-profiling/vllm_run_1.md` - vLLM run log (276KB)
- `docs/reviews/vllm-profiling/anthropic_run_1.md` - Anthropic API run log
- `docs/reviews/vllm-profiling/c4-sequence-diagrams.md` - Root cause analysis
- `guardkit/orchestrator/feature_orchestrator.py` - Factory availability check logic
- `guardkit/knowledge/graphiti_client.py` - Graphiti factory/client implementation
- `tasks/backlog/graphiti-context-wiring/` - Existing context wiring fix
- `tasks/backlog/graphiti-lifecycle-fix/` - Existing lifecycle fix
- `.claude/rules/graphiti-knowledge.md` - Graphiti configuration reference

## Implementation Notes
[Space for review findings]

## Test Execution Log
[Automatically populated by /task-work]
