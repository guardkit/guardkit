# Implementation Guide: FEAT-ASPF — AutoBuild Synthetic Pipeline Fix

**Parent Review**: TASK-REV-953F
**Review Report**: `.claude/reviews/TASK-REV-953F-review-report.md`

## Execution Strategy

### Wave 1: Critical Fixes (No Dependencies — Parallel)

4 tasks, all independent. Wave 1 can be executed in parallel using Conductor.

| Task | Method | Workspace | Est. Effort |
|------|--------|-----------|-------------|
| TASK-FIX-ASPF-001 | direct (git commit) | aspf-wave1-1 | 5 min |
| TASK-FIX-ASPF-002 | `/task-work` | aspf-wave1-2 | 30 min |
| TASK-FIX-ASPF-003 | direct (1-line fix) | aspf-wave1-3 | 5 min |
| TASK-FIX-ASPF-007 | direct (remove line) | aspf-wave1-4 | 5 min |

**ASPF-001 should be done first** (commits existing changes that ASPF-002/003 build upon).

**Recommended order**: ASPF-001 → then ASPF-002, ASPF-003, ASPF-007 in parallel.

### Wave 2: Secondary Fixes (Depend on Wave 1 Committed)

2 tasks, independent of each other.

| Task | Method | Workspace | Est. Effort |
|------|--------|-----------|-------------|
| TASK-FIX-ASPF-004 | `/task-work` | aspf-wave2-1 | 2-4 hrs |
| TASK-FIX-ASPF-005 | direct (constant + script changes) | aspf-wave2-2 | 10 min |

**ASPF-005 is the highest-impact fix** — increasing SDK turns from 50→100 and vLLM context from 128K→256K lets the Player complete the report-writing step, making the DMCP fixes work end-to-end on vLLM.

### Wave 3: Enhancement (Only if Synthetic Path Still Needed)

| Task | Method | Workspace | Est. Effort |
|------|--------|-----------|-------------|
| TASK-FIX-ASPF-006 | `/task-work` | aspf-wave3-1 | 4-6 hrs |

**Note**: If ASPF-005 resolves the turn exhaustion issue, ASPF-006 becomes lower priority since the synthetic fallback path will be used less frequently.

## Key Files

| File | Modified By | Purpose |
|------|------------|---------|
| `guardkit/orchestrator/autobuild.py` | ASPF-002 | State recovery disk write |
| `guardkit/orchestrator/agent_invoker.py` | ASPF-001, ASPF-007 | DMCP fixes, double-write |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | ASPF-001, ASPF-003 | DMCP fixes, log fix |
| `guardkit/orchestrator/feature_orchestrator.py` | ASPF-004 | Cancellation |
| `scripts/vllm-serve.sh` | ASPF-005 | vLLM context 128K→256K |
| `guardkit/orchestrator/synthetic_report.py` | ASPF-006 | Requirements inference |

## File Conflict Analysis

- **Wave 1**: ASPF-001 touches agent_invoker.py and coach_validator.py. ASPF-003 touches coach_validator.py (different line). ASPF-007 touches agent_invoker.py (different section). **No conflicts if ASPF-001 commits first.**
- **Wave 2**: ASPF-004 touches feature_orchestrator.py and agent_invoker.py. ASPF-005 touches agent_invoker.py (constant only) and vllm-serve.sh. **No conflicts with each other.**
- **Wave 3**: ASPF-006 touches synthetic_report.py and coach_validator.py. **No conflicts with wave 2.**

## Verification

After Wave 1:
```bash
python3 -m pytest tests/unit/ -v --tb=short
# Expected: 6676+ passed, 6 failed (pre-existing)
```

After all waves, run a vLLM autobuild to verify end-to-end:
```bash
guardkit autobuild feature FEAT-3CC2 --verbose --fresh
```

## Next Steps

1. Review this guide
2. Start with TASK-FIX-ASPF-001 (commit DMCP fixes)
3. Proceed to Wave 1 remaining tasks
4. Use Conductor for parallel Wave 1 execution
