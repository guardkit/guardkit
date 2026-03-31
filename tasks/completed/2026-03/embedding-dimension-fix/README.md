# FEAT-EMB: Embedding Dimension Mismatch Fix

## Problem

Graphiti reports `Vector dimension mismatch, expected 768 but got 1024` when running AutoBuild from youtube-transcript-mcp against a shared FalkorDB instance seeded from the guardkit project.

**Root Cause:** Split-brain config — FalkorDB connection comes from residual `.env` vars (correct), but embedding provider defaults to OpenAI (wrong) because the per-project `graphiti.yaml` is sparse.

## Solution

1. **Complete per-project configs** — ensure all projects sharing FalkorDB have full `graphiti.yaml`
2. **Clean `.env` files** — remove infrastructure config, keep only secrets
3. **Improve `guardkit init`** — auto-offer config copying from parent project
4. **Fix env stripping bug** — coach_validator SDK invocation loses env vars
5. **Add safeguards** — dimension pre-flight check + sparse config warning

## Subtasks

| Task | Title | Wave | Priority | Complexity |
|------|-------|------|----------|-----------|
| TASK-EMB-001 | Complete youtube-transcript-mcp graphiti.yaml | 1 | Critical | 1 |
| TASK-EMB-002 | Remove infra config from guardkit .env | 1 | Critical | 1 |
| TASK-EMB-003 | Auto-offer --copy-graphiti during init | 2 | High | 4 |
| TASK-EMB-004 | Fix coach_validator env stripping | 2 | High | 2 |
| TASK-EMB-005 | Embedding dimension pre-flight check | 3 | Medium | 5 |
| TASK-EMB-006 | Sparse config + FalkorDB warning | 3 | Medium | 3 |

## Review

- **Review Task**: TASK-REV-D2B5
- **Review Report**: [.claude/reviews/TASK-REV-D2B5-review-report.md](../../../.claude/reviews/TASK-REV-D2B5-review-report.md)
