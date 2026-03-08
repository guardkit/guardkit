# vLLM Run 3 Fixes (FEAT-VR3)

**Parent Review**: TASK-REV-1509 — Analyse vLLM Run 2 Performance and Graphiti Integration Failure

## Problem Statement

vLLM Run 2 revealed two blocking issues for Run 3:
1. **Graphiti never initializes** in autobuild — a call-order bug in `_preflight_check()` silently disables context for every run
2. **SDK turn ceiling and timeout too low** — Qwen3 needs more turns and time than Claude

## Subtasks

| Task | Description | Priority | Complexity | Mode | Wave |
|------|-------------|----------|------------|------|------|
| TASK-FIX-GPLI | Fix `_preflight_check()` lazy-init ordering | Critical | 2 | task-work | 1 |
| TASK-VPT-002 | Tune sdk_max_turns=100, timeout_multiplier=4.0 | High | 1 | direct | 1 |

## Execution Strategy

**Wave 1** (parallel — no file conflicts):
- TASK-FIX-GPLI: Modifies `feature_orchestrator.py` only
- TASK-VPT-002: Modifies `agent_invoker.py` only

Both can run in parallel via Conductor or sequential — no dependencies between them.

## Pre-Run 3 Checklist

After implementing both tasks:

```
□ Code fixes applied and tested
□ pip install -e . (reinstall guardkit in vllm-profiling env)
□ FalkorDB running on whitestocks: redis-cli -h whitestocks -p 6379 ping
□ Verify: cd vllm-profiling && guardkit graphiti search "test"
□ Verify log: "FalkorDB pre-flight TCP check passed" (not "factory not available")
□ Run: guardkit autobuild feature FEAT-XXXX --max-turns 30 --verbose
```
