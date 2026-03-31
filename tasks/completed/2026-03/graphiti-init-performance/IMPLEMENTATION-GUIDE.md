# Implementation Guide: Graphiti Init Performance (FEAT-GIP)

**Source Review**: TASK-REV-8A31 (Review reseed guardkit_3 + init project_12)
**Parent Feature**: FEAT-SPR (closing) + new FEAT-GIP

---

## Wave 1: Immediate (Parallel)

Three tasks can run in parallel — no file conflicts between them.

| Task | Title | Mode | Complexity | Est. |
|------|-------|------|-----------|------|
| TASK-FIX-cc7e | Increase project_purpose timeout to 600s | task-work | 2 | <1h |
| TASK-INV-7c71 | Investigate Episode 3 structural slowdown | direct | 6 | 2-4h |
| TASK-OPS-64fe | Close FEAT-SPR as delivered | direct | 1 | <30m |

### Execution Notes

**TASK-FIX-cc7e** (timeout increase):
- File: `guardkit/knowledge/graphiti_client.py` — find the timeout tier logic
- Change project_purpose from 300s to 600s
- Quick, low-risk change

**TASK-INV-7c71** (investigation):
- Research/analysis task, not implementation
- Use `/task-review TASK-INV-7c71 --mode=decision` when ready
- Key deliverable: root cause ranking and recommendation

**TASK-OPS-64fe** (FEAT-SPR closure):
- Housekeeping — verify completed tasks, create summary
- No code changes

## Wave 2: After Wave 1

| Task | Title | Mode | Complexity | Est. |
|------|-------|------|-----------|------|
| TASK-FIX-303e | Raise agent timeout from 150s to 240s | task-work | 2 | <1h |

### Execution Notes

**TASK-FIX-303e** depends on TASK-FIX-cc7e (same file, timeout tier logic). Run after cc7e merges to avoid conflicts.

---

## Verification

After Wave 1+2 implementation:
1. Run `guardkit graphiti seed --force` and verify timeout changes in logs
2. Run `guardkit init fastapi-python -n vllm-profiling` and verify Episode 1 doesn't timeout
3. Compare agent success rate to guardkit_3 baseline (9/18)

## Context Files

- Review report: [TASK-REV-8A31-review-report.md](../../../docs/reviews/TASK-REV-8A31-review-report.md)
- Parent review: [TASK-REV-FFD3-review-report.md](../../../docs/reviews/TASK-REV-FFD3-review-report.md)
- Init log: [init_project_12.md](../../../docs/reviews/reduce-static-markdown/init_project_12.md)
- Reseed log: [reseed_guardkit_3.md](../../../docs/reviews/reduce-static-markdown/reseed_guardkit_3.md)
