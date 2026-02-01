# Implementation Guide: Graphiti Phase 2 Verification

## Overview

This guide provides the execution strategy for verifying FEAT-0F4A before merge.

## Wave Breakdown

### Wave 1: Tier 1 Verification (Parallel - 2 hours)

Execute these tasks in parallel using Conductor workspaces:

| Task | Description | Workspace | Est. |
|------|-------------|-----------|------|
| TASK-VER-001 | Run Tier 1 unit tests | gp2v-wave1-1 | 30m |
| TASK-VER-002 | Run Tier 1 integration tests | gp2v-wave1-2 | 30m |
| TASK-VER-003 | Fix known test failures | gp2v-wave1-3 | 60m |

**Commands**:
```bash
# Workspace 1
cd .guardkit/worktrees/FEAT-0F4A
pytest tests/unit/knowledge/ -v --cov=guardkit/knowledge

# Workspace 2
cd .guardkit/worktrees/FEAT-0F4A
pytest tests/integration/graphiti/ -v -m "not live"

# Workspace 3
cd .guardkit/worktrees/FEAT-0F4A
# Fix test_status_shows_seeding_state mock issue
```

**Gate**: All Wave 1 tasks must pass before Wave 2.

---

### Wave 2: Tier 2 + CLI Verification (Sequential - 2 hours)

Execute these tasks after Wave 1 completes:

| Task | Description | Dependencies | Est. |
|------|-------------|--------------|------|
| TASK-VER-004 | Run Tier 2 live tests | VER-001,002,003 | 60m |
| TASK-VER-005 | Verify CLI commands | VER-004 | 45m |

**Commands**:
```bash
# Start Neo4j first
docker-compose up -d neo4j

# Then run live tests
cd .guardkit/worktrees/FEAT-0F4A
guardkit graphiti seed --force
pytest tests/integration/graphiti/ -v -m "live"

# Verify CLI
guardkit graphiti status
guardkit graphiti search "feature-plan"
guardkit graphiti show FEAT-GR-003
guardkit graphiti list features
```

**Gate**: Performance must meet <2s target, all live tests pass.

---

### Wave 3: Documentation + Merge (Sequential - 1 hour)

| Task | Description | Dependencies | Est. |
|------|-------------|--------------|------|
| TASK-VER-006 | Document results, prepare merge | VER-004,005 | 30m |

**Commands**:
```bash
# Document results
# Create docs/reviews/graphiti_enhancement/phase_2_verification.md

# If all criteria pass
/feature-complete FEAT-0F4A
```

---

## Quick Start

### Fastest Path (if no issues expected)

```bash
# 1. Run all Tier 1 tests at once
cd .guardkit/worktrees/FEAT-0F4A
pytest tests/unit/knowledge/ tests/integration/graphiti/ tests/cli/test_graphiti*.py \
  -v -m "not live" --tb=short

# 2. Start Neo4j and run Tier 2
docker-compose up -d neo4j
guardkit graphiti seed --force
pytest tests/integration/graphiti/ -v -m "live"
guardkit graphiti verify

# 3. Quick CLI check
guardkit graphiti status
guardkit graphiti search "GuardKit"

# 4. If all pass, merge
/feature-complete FEAT-0F4A
```

**Estimated time**: 20-30 minutes (if no failures)

---

## Troubleshooting

### Neo4j Connection Issues
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Restart if needed
docker-compose restart neo4j
```

### Mock Test Failures
The `test_status_shows_seeding_state` failure is a known mock issue. Fix by using `AsyncMock` instead of `MagicMock` for async methods.

### Performance Issues
If queries take >2s:
1. Check Neo4j indices exist
2. Verify OpenAI API is responsive
3. Check for large result sets

---

## Success Criteria Summary

| Criteria | Threshold | Blocking? |
|----------|-----------|-----------|
| Unit tests | 100% pass | Yes |
| Mock integration | 100% pass | Yes |
| Live integration | 100% pass | Yes |
| Coverage | ≥70% | Yes |
| Query latency | <2s (95th pct) | Yes |
| CLI commands | 4/4 working | No |

---

## After Verification

Once all criteria pass:

1. **Document**: Create `docs/reviews/graphiti_enhancement/phase_2_verification.md`
2. **Merge**: Run `/feature-complete FEAT-0F4A`
3. **Verify**: Check main branch has all changes
4. **Clean up**: Archive worktree (done automatically by feature-complete)
