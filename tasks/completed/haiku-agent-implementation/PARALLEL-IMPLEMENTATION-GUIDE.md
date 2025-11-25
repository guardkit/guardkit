# Parallel Implementation Guide: Haiku Agent Discovery Metadata

## Overview

This guide provides a wave-based parallel implementation strategy for adding discovery metadata to 30 agents (15 global + 15 template-specific) using Conductor git worktrees for maximum efficiency.

**Timeline**: 3.5-4 days (realistic with checkpoints)
**Workspaces**: 8 maximum (efficient reuse)
**Strategy**: 4 waves mixing `/task-work` (complex) and direct Claude Code (simple)

---

## Quick Reference

| Metric | Value |
|--------|-------|
| **Total Tasks** | 14 (HAI-001 through HAI-014) |
| **Total Effort** | 25-29.5 hours |
| **Parallel Efficiency** | 17.25-20 hours (35% speedup) |
| **Workspaces Needed** | 8 concurrent maximum |
| **Critical Path** | 8.5 hours (HAI-001 → 005 → 006 → 008) |
| **Best Case** | 2.2 days |
| **Realistic** | 3.5-4 days |
| **Conservative** | 4.5 days |

---

## Task Classification Matrix

| Task ID | Title | Method | Effort | Rationale |
|---------|-------|--------|--------|-----------|
| **HAI-001** | Design Schema | `/task-work` | 1.5h | Complex design, needs architectural review (Phase 2.5B) |
| **HAI-002** | Python Agent | Direct | 2h | Template-based file creation, low integration |
| **HAI-003** | React Agent | Direct | 2h | Template-based file creation, low integration |
| **HAI-004** | .NET Agent | Direct | 2h | Template-based file creation, low integration |
| **HAI-005** | Discovery Algorithm | `/task-work` | 3h | Complex matching logic, needs testing (Phase 4.5) |
| **HAI-006** | Integration | `/task-work` | 2h | Touches existing code, critical integration point |
| **HAI-007** | Documentation | Direct | 1.5h | Writing only, no code changes |
| **HAI-008** | E2E Testing | `/task-work` | 2h | Validation critical, needs quality gates |
| **HAI-009** | Update 12 Global Agents | Direct + Script | 4-6h | Bulk metadata updates with validation |
| **HAI-010** | react-typescript | Direct | 1-1.5h | 3 template agents metadata updates |
| **HAI-011** | fastapi-python | Direct | 1-1.5h | 3 template agents metadata updates |
| **HAI-012** | nextjs-fullstack | Direct | 1-1.5h | 3 template agents metadata updates |
| **HAI-013** | react-fastapi-monorepo | Direct | 1-1.5h | 3 template agents metadata updates |
| **HAI-014** | taskwright-python | Direct | 1-1.5h | 3 template agents metadata updates |

### Why /task-work vs Direct?

**Use `/task-work` when** (5 tasks):
- Complex logic requiring planning + architectural review
- Integration with existing code (regression risk)
- Testing critical (quality gates needed)
- Scope creep risk (plan audit valuable)

**Use Direct Claude Code when** (9 tasks):
- Simple file creation from templates
- Repetitive metadata updates
- Documentation writing
- Low integration risk

---

## Wave-Based Implementation Plan

### Wave 1: Foundation + Agent Creation (Sequential → Parallel)

**Duration**: 2.25 hours (1.5h sequential + 2h parallel)
**Workspaces**: 4 concurrent
**Checkpoint**: 15 minutes (schema + agent review)

| Workspace | Task | Method | Duration | Dependencies |
|-----------|------|--------|----------|--------------|
| **WS-Main** | HAI-001 | `/task-work` | 1.5h | None |
| **WS-A** | HAI-002 | Direct | 2h | HAI-001 (schema) |
| **WS-B** | HAI-003 | Direct | 2h | HAI-001 (schema) |
| **WS-C** | HAI-004 | Direct | 2h | HAI-001 (schema) |

**Execution**:
```bash
# Step 1: Foundation (WS-Main) - SEQUENTIAL
cd ~/Projects/taskwright-main
/task-work TASK-HAI-001-D668  # Schema design with architectural review

# Step 2: Wait for HAI-001 completion (1.5h)

# Step 3: Agent creation - PARALLEL (all 3 start simultaneously)
conductor workspace create ws-hai-002 --task "HAI-002 Python Agent"
conductor workspace create ws-hai-003 --task "HAI-003 React Agent"
conductor workspace create ws-hai-004 --task "HAI-004 .NET Agent"

# In WS-A (ws-hai-002):
cd ws-hai-002
# Create installer/global/agents/python-api-specialist.md
# Follow TASK-HAI-002-B47C specifications

# In WS-B (ws-hai-003):
cd ws-hai-003
# Create installer/global/agents/react-state-specialist.md
# Follow TASK-HAI-003-45BB specifications

# In WS-C (ws-hai-004):
cd ws-hai-004
# Create installer/global/agents/dotnet-domain-specialist.md
# Follow TASK-HAI-004-9534 specifications
```

**Checkpoint**: Review 3 new agents, validate metadata against schema

**Merge to Main**: After validation passes

---

### Wave 2: Discovery System (Sequential)

**Duration**: 5 hours
**Workspaces**: 1 (critical integration)
**Checkpoint**: After HAI-005 before HAI-006 (30 minutes)

| Workspace | Task | Method | Duration | Dependencies |
|-----------|------|--------|----------|--------------|
| **WS-D** | HAI-005 | `/task-work` | 3h | HAI-001, HAI-002/003/004 |
| **WS-D** | HAI-006 | `/task-work` | 2h | HAI-005 (must complete) |

**Execution**:
```bash
# Use dedicated workspace for critical integration
conductor workspace create ws-hai-005-006 --task "HAI-005 + HAI-006 Discovery"
cd ws-hai-005-006

# Step 1: Discovery algorithm (3h)
/task-work TASK-HAI-005-7A2E  # With full quality gates

# Step 2: Critical checkpoint (30 min)
# - Test discovery algorithm manually
# - Verify no regressions
# - Validate matches expected agents

# Step 3: Integration (2h)
/task-work TASK-HAI-006-C391  # Integrate with /task-work Phase 3

# Step 4: Integration testing
# - Run sample tasks (Python, React, .NET)
# - Verify agent discovery works
# - Check fallback for unknown stacks
```

**Checkpoint**: Manual testing of discovery algorithm before integration

**Merge to Main**: After HAI-006 integration tests pass

---

### Wave 3: Finalization (Parallel)

**Duration**: 2.25 hours (parallel with 75% overlap)
**Workspaces**: 2 (documentation + testing)
**Checkpoint**: 15 minutes (final review)

| Workspace | Task | Method | Duration | Dependencies |
|-----------|------|--------|----------|--------------|
| **WS-E** | HAI-007 | Direct | 1.5h | HAI-001 through HAI-006 |
| **WS-D** | HAI-008 | `/task-work` | 2h | HAI-007 (can overlap 75%) |

**Execution**:
```bash
# Documentation (WS-E)
conductor workspace create ws-hai-007 --task "HAI-007 Documentation"
cd ws-hai-007
# Update CLAUDE.md
# Create docs/guides/agent-discovery-guide.md
# Update docs/deep-dives/model-optimization.md
# Update README.md
# Update installer/global/commands/agent-enhance.md
# Follow TASK-HAI-007-8B1F specifications

# E2E Testing (WS-D, reuse) - can start after 20 min of HAI-007
conductor workspace reuse ws-hai-005-006 --task "HAI-008 E2E Testing"
cd ws-hai-005-006
/task-work TASK-HAI-008-D5C2  # Full test suite with quality gates
```

**Checkpoint**: Final review before bulk metadata updates

**Merge to Main**: After all tests pass

---

### Wave 4: Bulk Metadata Updates (Parallel)

**Duration**: 6.3 hours (all parallel)
**Workspaces**: 6 concurrent
**Checkpoint**: 20 minutes (metadata validation)

| Workspace | Task | Method | Duration | Notes |
|-----------|---------|--------|----------|-------|
| **WS-F** | HAI-009 | Direct + Script | 4-6h | 12 global agents with validation batching |
| **WS-A** | HAI-010 | Direct | 1-1.5h | react-typescript (3 agents) |
| **WS-B** | HAI-011 | Direct | 1-1.5h | fastapi-python (3 agents) |
| **WS-C** | HAI-012 | Direct | 1-1.5h | nextjs-fullstack (3 agents) |
| **WS-G** | HAI-013 | Direct | 1-1.5h | react-fastapi-monorepo (3 agents) |
| **WS-H** | HAI-014 | Direct | 1-1.5h | taskwright-python (3 agents) |

**Execution**:
```bash
# HAI-009: Global agents (WS-F) - LONGEST TASK
conductor workspace create ws-hai-009 --task "HAI-009 Global Agents"
cd ws-hai-009
# Update 12 global agents following TASK-HAI-009-F3A7 specifications
# See agent list in task file (database-specialist, devops-specialist, etc.)
# Use validation script: scripts/validate_agent_metadata.py

# HAI-010: react-typescript (WS-A, reuse)
conductor workspace reuse ws-hai-002 --task "HAI-010 react-typescript"
cd ws-hai-002
# Update 3 agents: feature-architecture-specialist, form-validation-specialist, react-query-specialist
# Follow TASK-HAI-010-A89D specifications

# HAI-011: fastapi-python (WS-B, reuse)
conductor workspace reuse ws-hai-003 --task "HAI-011 fastapi-python"
cd ws-hai-003
# Update 3 agents: fastapi-specialist, fastapi-database-specialist, fastapi-testing-specialist
# Follow TASK-HAI-011-B23E specifications

# HAI-012: nextjs-fullstack (WS-C, reuse)
conductor workspace reuse ws-hai-004 --task "HAI-012 nextjs-fullstack"
cd ws-hai-004
# Update 3 agents: nextjs-fullstack-specialist, nextjs-server-components-specialist, nextjs-server-actions-specialist
# Follow TASK-HAI-012-C5F8 specifications

# HAI-013: react-fastapi-monorepo (WS-G, new)
conductor workspace create ws-hai-013 --task "HAI-013 react-fastapi-monorepo"
cd ws-hai-013
# Update 3 agents: react-fastapi-monorepo-specialist, monorepo-type-safety-specialist, docker-orchestration-specialist
# Follow TASK-HAI-013-D7A2 specifications

# HAI-014: taskwright-python (WS-H, new)
conductor workspace create ws-hai-014 --task "HAI-014 taskwright-python"
cd ws-hai-014
# Update 3 agents: python-cli-specialist, python-architecture-specialist, python-testing-specialist
# Follow TASK-HAI-014-E9B6 specifications
```

**Validation Script**:
```bash
# Run after all Wave 4 updates
python3 scripts/validate_agent_metadata.py --all

# Expected output:
# ✅ Valid: 30/30
# Coverage: 100% (15 global + 15 template)
```

**Checkpoint**: Validate all 30 agents have correct metadata

**Merge to Main**: After validation passes

---

## Conductor Workspace Strategy

### Workspace Allocation

**8 workspaces with intelligent reuse**:

| Workspace | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Total Usage |
|-----------|--------|--------|--------|--------|-------------|
| **WS-Main** | HAI-001 (1.5h) | - | - | - | 1.5h |
| **WS-A** | HAI-002 (2h) | - | - | HAI-010 (1.5h) | 3.5h |
| **WS-B** | HAI-003 (2h) | - | - | HAI-011 (1.5h) | 3.5h |
| **WS-C** | HAI-004 (2h) | - | - | HAI-012 (1.5h) | 3.5h |
| **WS-D** | - | HAI-005 (3h), HAI-006 (2h) | HAI-008 (2h) | - | 7h |
| **WS-E** | - | - | HAI-007 (1.5h) | - | 1.5h |
| **WS-F** | - | - | - | HAI-009 (6h) | 6h |
| **WS-G** | - | - | - | HAI-013 (1.5h) | 1.5h |
| **WS-H** | - | - | - | HAI-014 (1.5h) | 1.5h |

**Benefits**:
- **WS-Main**: Isolated for critical schema design
- **WS-D**: Critical path (discovery + integration + E2E testing)
- **WS-A/B/C**: Reused between Wave 1 and Wave 4
- **WS-F/G/H**: Single-wave usage (Wave 4 parallelization)

### State Persistence

**Taskwright + Conductor compatibility**: ✅ Verified

- **Commands/Agents**: `~/.claude/* → ~/.agentecflow/*` (symlinks)
- **State**: `{worktree}/.claude/state → {main-repo}/.claude/state` (symlinks)
- **100% state preservation** across worktrees
- **Zero manual intervention** required

**Verification**:
```bash
# Before starting
./installer/scripts/install.sh  # Creates symlinks
taskwright doctor              # Verify integration
```

---

## Checkpoint Workflow

### Wave Checkpoints

**After Wave 1** (15 min):
```bash
# 1. Review schema design
cat docs/schemas/agent-discovery-metadata.md

# 2. Review 3 new agents
cat installer/global/agents/{python-api-specialist,react-state-specialist,dotnet-domain-specialist}.md

# 3. Validate metadata format
python3 -c "
import frontmatter
for agent in ['python-api-specialist', 'react-state-specialist', 'dotnet-domain-specialist']:
    with open(f'installer/global/agents/{agent}.md') as f:
        data = frontmatter.loads(f.read())
        assert 'stack' in data.metadata
        assert 'phase' in data.metadata
        assert 'capabilities' in data.metadata
        assert 'keywords' in data.metadata
        assert len(data.metadata['capabilities']) >= 5
        assert len(data.metadata['keywords']) >= 5
    print(f'✅ {agent} valid')
"

# 4. Merge to main if all pass
git checkout main
git merge ws-hai-002 ws-hai-003 ws-hai-004
```

**After Wave 2** (30 min - CRITICAL):
```bash
# 1. Test discovery algorithm manually
python3 -c "
from installer.global.commands.lib.agent_discovery import discover_agents

# Test implementation agents
agents = discover_agents(phase='implementation')
print(f'Found {len(agents)} implementation agents')
assert len(agents) >= 3, 'Should find at least 3 implementation agents'

# Test stack filtering
python_agents = discover_agents(phase='implementation', stack=['python'])
print(f'Found {len(python_agents)} Python implementation agents')
assert len(python_agents) >= 1, 'Should find python-api-specialist'

# Test keyword matching
fastapi_agents = discover_agents(phase='implementation', keywords=['fastapi'])
print(f'Found {len(fastapi_agents)} FastAPI specialists')
assert len(fastapi_agents) >= 1, 'Should find python-api-specialist'

print('✅ All discovery tests passed')
"

# 2. Test integration with sample task
/task-create "Add user endpoint" priority:medium
# Manually edit task to add: files: ['src/api/users.py']
/task-work TASK-XXX  # Observe which agent is selected for Phase 3

# 3. Check fallback behavior
/task-create "Add feature" priority:medium
# Manually edit task to add: files: ['src/main.rs']
/task-work TASK-YYY  # Should fall back to task-manager (no Rust specialist yet)

# 4. Merge to main if all pass
git checkout main
git merge ws-hai-005-006  # Critical: HAI-005 + HAI-006
```

**After Wave 3** (15 min):
```bash
# 1. Review documentation completeness
cat CLAUDE.md | grep -A 20 "Stack-Specific Implementation Agents"
cat docs/guides/agent-discovery-guide.md

# 2. Check E2E test results
/task-status TASK-HAI-008-D5C2 | grep "COMPLETED"

# 3. Review E2E test report
cat tests/integration/haiku-agent-e2e-report.md

# 4. Merge to main
git checkout main
git merge ws-hai-007 ws-hai-005-006  # HAI-007 + HAI-008
```

**After Wave 4** (20 min):
```bash
# 1. Run validation script
python3 scripts/validate_agent_metadata.py --all

# Expected output:
# ✅ Valid: 30/30
# ⚠️  Missing metadata: 0
# ❌ Incomplete: 0

# 2. Test discovery finds all agents
python3 -c "
from installer.global.commands.lib.agent_discovery import discover_agents

# Count by phase
impl = discover_agents(phase='implementation')
review = discover_agents(phase='review')
testing = discover_agents(phase='testing')
orchestration = discover_agents(phase='orchestration')

print(f'Implementation: {len(impl)} agents')
print(f'Review: {len(review)} agents')
print(f'Testing: {len(testing)} agents')
print(f'Orchestration: {len(orchestration)} agents')

total = len(impl) + len(review) + len(testing) + len(orchestration)
print(f'Total: {total} agents with metadata')
assert total >= 30, 'Should have at least 30 agents'
"

# 3. Spot-check metadata quality
git diff main..HEAD installer/global/agents/database-specialist.md | head -30
git diff main..HEAD installer/global/templates/react-typescript/agents/form-validation-specialist.md | head -30

# 4. Merge to main if all pass
git checkout main
git merge ws-hai-009 ws-hai-002 ws-hai-003 ws-hai-004 ws-hai-013 ws-hai-014
```

---

## Risk Mitigation Matrix

### High-Risk Tasks → /task-work with All Gates

| Task | Risk | Mitigation | Quality Gates |
|------|------|------------|---------------|
| **HAI-001** | Incorrect schema breaks everything | Architectural review (Phase 2.5B) | SOLID/DRY/YAGNI score ≥60/100 |
| **HAI-005** | Matching bugs = poor recommendations | Test enforcement (Phase 4.5) | 100% test pass, coverage ≥80% |
| **HAI-006** | Integration bugs break /task-work | Plan audit (Phase 5.5) | Scope creep detection, ±20% LOC |
| **HAI-008** | Inadequate testing = production bugs | Code review (Phase 5) | Issue detection, compliance validation |

### Medium-Risk Tasks → Direct + Validation

| Task | Risk | Mitigation |
|------|------|------------|
| **HAI-009** | Inconsistent metadata across 12 agents | Automated validation script, batching |
| **HAI-010-014** | Template metadata inconsistencies | Per-template validation + spot-checks |

### Low-Risk Tasks → Direct Only

| Task | Risk | Mitigation |
|------|------|------------|
| **HAI-002/003/004** | Incorrect agent templates | Schema validation, manual review |
| **HAI-007** | Documentation gaps | Completeness checklist |

---

## Timeline Projections

### Best Case (Perfect Parallelization)

**Total**: 2.2 days (17.25 hours)

| Wave | Duration | Checkpoints | Total |
|------|----------|-------------|-------|
| Wave 1 | 2.25h (1.5h seq + 2h parallel) | 0.25h | 2.5h |
| Wave 2 | 5h (sequential) | 0.5h | 5.5h |
| Wave 3 | 2.25h (parallel 75% overlap) | 0.25h | 2.5h |
| Wave 4 | 6.3h (parallel) | 0.33h | 6.6h |

**Reality Check**: Assumes zero context switching, perfect workspace management, no unexpected issues.

### Realistic (With Overhead)

**Total**: 3.5-4 days (20 hours + overhead)

| Wave | Duration | Checkpoints | Overhead | Total |
|------|----------|-------------|----------|-------|
| Wave 1 | 2.25h | 0.25h | 0.5h (setup) | 3h |
| Wave 2 | 5h | 0.5h | 1h (integration testing) | 6.5h |
| Wave 3 | 2.25h | 0.25h | 0.5h (final review) | 3h |
| Wave 4 | 6.3h | 0.33h | 1h (validation) | 7.6h |

**Total: 20 hours = 2.5 days @ 8h/day, 3.3 days @ 6h/day, 4 days @ 5h/day**

**Overhead includes**:
- Workspace creation/switching
- Context loading
- Unexpected issues
- Coffee breaks ☕

### Conservative (Sequential Fallback)

**Total**: 4.5 days (29 hours + buffer)

**Scenario**: If parallelization issues arise, fall back to sequential execution with 1-day buffer.

---

## Recommended Timeline

**Day 1**:
- Morning: Wave 1 (HAI-001 schema design) - 1.5h
- Afternoon: Wave 1 (HAI-002/003/004 parallel) - 2h + checkpoint - 15min
- **Total: 3.75h**

**Day 2**:
- Morning: Wave 2 (HAI-005 discovery algorithm) - 3h
- Afternoon: Wave 2 (HAI-006 integration) - 2h + checkpoint - 30min
- **Total: 5.5h**

**Day 3**:
- Morning: Wave 3 (HAI-007 docs + HAI-008 E2E parallel) - 2.25h + checkpoint - 15min
- Afternoon: Wave 4 start (HAI-009 global agents) - 3h
- **Total: 5.4h**

**Day 4**:
- Morning: Wave 4 continue (HAI-009 finish + HAI-010-014 parallel) - 4h
- Afternoon: Wave 4 checkpoint + validation + merge - 1h
- **Total: 5h**

**Grand Total**: 19.65 hours over 4 days = **realistic 3.5-4 day timeline**

---

## Pre-Execution Checklist

### Environment Setup

- [ ] Conductor installed and configured
- [ ] Taskwright symlinks verified (`taskwright doctor`)
- [ ] Git worktree support confirmed
- [ ] 8 workspace slots available (check Conductor limits)
- [ ] Main branch clean (no uncommitted changes)
- [ ] v0.95.0 tag created (rollback point)

### Validation Tools Ready

- [ ] Create validation script: `scripts/validate_agent_metadata.py`
- [ ] Python frontmatter library installed: `pip install python-frontmatter`
- [ ] Discovery algorithm test suite (will be created in HAI-005)

### Documentation Access

- [ ] HAI-001 through HAI-014 task files accessible
- [ ] Schema definition from HAI-001 available after Wave 1
- [ ] Agent template references loaded

---

## Success Criteria

### Functional
- [ ] 30 agents have discovery metadata (3 new + 12 global + 15 template)
- [ ] Discovery algorithm finds agents by stack/phase/keywords
- [ ] Phase 3 integration suggests appropriate specialists
- [ ] Fallback works for unknown stacks
- [ ] All E2E tests pass

### Quality
- [ ] Zero regressions in existing agent functionality
- [ ] Metadata format consistent across all agents
- [ ] Documentation complete and accurate
- [ ] Test coverage ≥80% for discovery algorithm

### Performance
- [ ] Discovery query < 500ms
- [ ] No slowdown in /task-work execution
- [ ] Parallel execution achieved expected speedup

---

**Status**: ✅ Ready to Execute
**Next Action**: Start Wave 1 (HAI-001 schema design)
**Rollback**: `git reset --hard v0.95.0` if needed
