# FEAT-27F2: Player/Coach Test Divergence Fix

## Problem

During FEAT-BA28 (PostgreSQL Database Integration), the AutoBuild Player/Coach adversarial workflow entered an 18-turn infinite loop on TASK-DB-003. The Player consistently reported tests passing while the Coach's independent `pytest` verification failed every turn. The task timed out after 45 minutes and 58 seconds, wasting significant API cost.

**Root cause**: 5 interacting bugs forming a failure cascade:
1. **F1 (Critical)**: Environment parity gap — Coach `subprocess.run()` runs in bare Python env while Player uses SDK Bash tool with full user shell environment
2. **F2**: Duplicate test paths from mixed absolute/relative paths defeating `set()` dedup
3. **F3**: Feedback truncation discarding tracebacks — Player never sees actual error
4. **F4**: Stall detection defeated by variable test class names in feedback MD5 hash
5. **F5**: Quality gate short-circuit on Turn 2 producing different feedback category

## Solution

Three implementation waves, each providing incremental value:

| Wave | Task | Description | Impact |
|------|------|-------------|--------|
| 1 | TASK-PCTD-5208 | Quick wins: feedback, stall detection, path dedup | Catches stall at Turn 5 (saves 13 turns) |
| 2 | TASK-PCTD-9BEB | Classify infrastructure vs code failures | Actionable remediation for DB/env failures |
| 3 | TASK-PCTD-3182 | SDK Bash tool for Coach (Option C) | 100% environment parity — root cause fix |

## Review

- **Review Report**: `.claude/reviews/TASK-REV-D7B2-review-report.md` (1600+ lines)
- **Architecture Score**: 35/100 (pre-fix)
- **Findings**: 5 definitive, with exact code locations and log evidence
- **Recommendations**: 5 regression-safe, with implementation code and test plans
- **R5 (Option C)**: Validated against SDK v0.1.18 with 9 GAP-FIX annotations

## Execution

```bash
# Wave 1: Quick wins (no dependencies)
/task-work TASK-PCTD-5208

# Wave 2: Infrastructure classification (after Wave 1)
/task-work TASK-PCTD-9BEB

# Wave 3: SDK environment parity (after Wave 1)
/task-work TASK-PCTD-3182
```
