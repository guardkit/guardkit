# Implementation Guide: Embedding Dimension Fix (FEAT-EMB)

## Parent Review

- **Review Task**: TASK-REV-D2B5
- **Review Report**: `.claude/reviews/TASK-REV-D2B5-review-report.md`

## Problem Statement

Graphiti embedding dimension mismatch (expected 768, got 1024) caused by:
1. Sparse per-project `graphiti.yaml` defaulting to OpenAI embeddings
2. Infrastructure config in `.env` causing cross-session pollution
3. No safeguards against mixed embedding providers on shared FalkorDB

## Execution Strategy

**3 waves, maximize parallel within each wave.**
**Testing depth: Standard (quality gates).**

---

### Wave 1: Immediate Fixes (Config-Only)

**Parallel execution — 2 independent tasks, no file conflicts.**

| Task | Title | Mode | Complexity | Workspace |
|------|-------|------|-----------|-----------|
| TASK-EMB-001 | Complete youtube-transcript-mcp graphiti.yaml | direct | 1 | embedding-fix-wave1-1 |
| TASK-EMB-002 | Remove infrastructure config from guardkit .env | direct | 1 | embedding-fix-wave1-2 |

**Dependencies:** None
**Expected Duration:** 5 minutes total
**Verification:** Run config verification scripts from both projects

These two tasks fix the immediate dimension mismatch by:
- EMB-001: Giving youtube-transcript-mcp a complete config with vLLM embedding provider
- EMB-002: Removing the `.env` infra vars that cause cross-session pollution

---

### Wave 2: Code Fixes (Preventive)

**Parallel execution — 2 independent tasks, different files.**

| Task | Title | Mode | Complexity | Workspace |
|------|-------|------|-----------|-----------|
| TASK-EMB-003 | Auto-offer --copy-graphiti during guardkit init | task-work | 4 | embedding-fix-wave2-1 |
| TASK-EMB-004 | Fix coach_validator env stripping | task-work | 2 | embedding-fix-wave2-2 |

**Dependencies:** None (independent of Wave 1)
**Expected Duration:** 2-3 hours total
**Files Modified:**
- EMB-003: `guardkit/cli/init.py`
- EMB-004: `guardkit/orchestrator/quality_gates/coach_validator.py`

---

### Wave 3: Defensive Improvements

**Parallel execution — 2 independent tasks, different files.**

| Task | Title | Mode | Complexity | Workspace |
|------|-------|------|-----------|-----------|
| TASK-EMB-005 | Add embedding dimension pre-flight check | task-work | 5 | embedding-fix-wave3-1 |
| TASK-EMB-006 | Log warning for sparse config + FalkorDB | task-work | 3 | embedding-fix-wave3-2 |

**Dependencies:** EMB-005 depends on EMB-001 (needs correct config to test against)
**Expected Duration:** 3-4 hours total
**Files Modified:**
- EMB-005: `guardkit/knowledge/graphiti_client.py`
- EMB-006: `guardkit/knowledge/config.py`

---

## Quick Start

```bash
# Wave 1 (parallel, direct execution)
# Workspace 1:
# Edit ~/Projects/appmilla_github/youtube-transcript-mcp/.guardkit/graphiti.yaml
# Workspace 2:
# Edit ~/Projects/appmilla_github/guardkit/.env

# Wave 2 (parallel, task-work)
/task-work TASK-EMB-003
/task-work TASK-EMB-004

# Wave 3 (parallel, task-work)
/task-work TASK-EMB-005
/task-work TASK-EMB-006
```

## Verification Checklist

After all waves complete:

- [ ] Run `guardkit graphiti search "test query"` from guardkit project — should succeed
- [ ] Run `guardkit graphiti search "test query"` from youtube-transcript-mcp — should succeed (no dimension mismatch)
- [ ] Start fresh terminal, run from youtube-transcript-mcp only — should work (no residual env vars needed)
- [ ] Run `guardkit init` in a new project under the same parent dir — should prompt to copy graphiti.yaml
- [ ] Run tests: `pytest tests/ -v`
