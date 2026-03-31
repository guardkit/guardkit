# Implementation Guide: vLLM GB10 Production Readiness

## Parent Review
TASK-REV-C960 — Analyse vLLM Qwen3 DB Feature AutoBuild Successful Run on GB10

## Wave Breakdown

### Wave 1: Code Changes (3 tasks, parallel)

These tasks modify GuardKit's Python codebase and require standard quality gates.

| Task | Description | Complexity | Method |
|------|-------------|------------|--------|
| TASK-VPR-001 | Add `--max-parallel` CLI option | 4 | task-work |
| TASK-VPR-002 | Add ISO timestamps to logs | 3 | task-work |
| TASK-VPR-003 | Add SDK turn ceiling monitoring | 4 | task-work |

**Key files likely affected:**
- `guardkit/cli/autobuild.py` — CLI flag parsing
- `guardkit/orchestrator/feature_orchestrator.py` — Wave dispatch, parallelism
- `guardkit/orchestrator/agent_invoker.py` — SDK turn tracking
- `guardkit/orchestrator/progress.py` — Log output, timestamps
- `guardkit/cli/display.py` — Summary display, turn reporting

### Wave 2: Documentation (2 tasks, parallel)

These tasks create documentation files. No code changes required.

| Task | Description | Complexity | Method |
|------|-------------|------------|--------|
| TASK-VPR-004 | vLLM/local backend usage guide | 2 | direct |
| TASK-VPR-005 | AC quality template for local LLMs | 3 | direct |

**Dependency**: TASK-VPR-004 depends on TASK-VPR-001 (references --max-parallel flag).

## Execution Strategy

```
Wave 1 (parallel):  VPR-001 + VPR-002 + VPR-003
                         ↓
Wave 2 (parallel):  VPR-004 + VPR-005
```

## Next Steps

1. Start with Wave 1 tasks (can run in parallel via Conductor)
2. After Wave 1 completes, run Wave 2 tasks
3. Verify all tests pass after Wave 1
4. Run a validation feature build on GB10 with the new flags
