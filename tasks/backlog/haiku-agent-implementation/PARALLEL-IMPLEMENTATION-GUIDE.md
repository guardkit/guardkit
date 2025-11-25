# Parallel Implementation Guide: Haiku Agent Discovery Metadata

## Overview

This guide provides a wave-based parallel implementation strategy for adding discovery metadata to 30 agents (15 global + 15 template-specific) using Conductor git worktrees for maximum efficiency.

**Timeline**: 3.5-4 days (realistic with checkpoints)
**Workspaces**: 6 maximum (efficient reuse)
**Strategy**: 4 waves mixing `/task-work` (complex) and direct Claude Code (simple)

---

## Quick Reference

| Metric | Value |
|--------|-------|
| **Total Tasks** | 14 (HAI-001 through HAI-014) |
| **Total Effort** | 25-29.5 hours |
| **Parallel Efficiency** | 17.25-20 hours (35% speedup) |
| **Workspaces Needed** | 6 concurrent maximum |
| **Critical Path** | 8.5 hours (HAI-001 → 005 → 006 → 008) |
| **Best Case** | 2.2 days |
| **Realistic** | 3.5 days |
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
| **HAI-010** | react-typescript | Direct | 1-1.5h | Repetitive metadata updates (3 agents) |
| **HAI-011** | fastapi-python | Direct | 1-1.5h | Repetitive metadata updates (3 agents) |
| **HAI-012** | nextjs-fullstack | Direct | 1-1.5h | Repetitive metadata updates (3 agents) |
| **HAI-013** | react-fastapi-monorepo | Direct | 1-1.5h | Repetitive metadata updates (3 agents) |
| **HAI-014** | taskwright-python | Direct | 1-1.5h | Repetitive metadata updates (3 agents) |

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

### Wave 1: Foundation + Agent Creation (Parallel)

**Duration**: 2.25 hours
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
# Step 1: Foundation (WS-Main)
cd ~/Projects/taskwright-main
/task-work TASK-HAI-001-D668  # Schema design with architectural review

# Step 2: Wait for HAI-001 completion + 15 min checkpoint

# Step 3: Agent creation (parallel)
conductor workspace create ws-hai-002 --task "HAI-002 Python Agent"
conductor workspace create ws-hai-003 --task "HAI-003 React Agent"
conductor workspace create ws-hai-004 --task "HAI-004 .NET Agent"

# In each workspace (parallel execution):
# WS-A: Create python-api-specialist.md with metadata from HAI-001 schema
# WS-B: Create react-state-specialist.md with metadata from HAI-001 schema
# WS-C: Create dotnet-domain-specialist.md with metadata from HAI-001 schema
```

**Checkpoint**: Review 3 new agents, validate metadata against schema

**Merge to Main**: After validation passes

---

### Wave 2: Agent Updates (Parallel)

**Duration**: 6.3 hours
**Workspaces**: 6 concurrent
**Checkpoint**: 20 minutes (metadata validation)

| Workspace | Task(s) | Method | Duration | Notes |
|-----------|---------|--------|----------|-------|
| **WS-A** | HAI-009 (Batch 1: 4 agents) | Direct | 1.5-2h | architectural-reviewer, code-reviewer, pattern-advisor, complexity-evaluator |
| **WS-B** | HAI-009 (Batch 2: 4 agents) | Direct | 1.5-2h | test-orchestrator, test-verifier, build-validator, debugging-specialist |
| **WS-C** | HAI-009 (Batch 3: 4 agents) | Direct | 1.5-2h | database-specialist, devops-specialist, security-specialist, git-workflow-manager |
| **WS-D** | HAI-010, HAI-011 | Direct | 2-3h | react-typescript (3), fastapi-python (3) |
| **WS-E** | HAI-012, HAI-013 | Direct | 2-3h | nextjs-fullstack (3), react-fastapi-monorepo (3) |
| **WS-F** | HAI-014 | Direct | 1-1.5h | taskwright-python (3), agent-content-enhancer, figma, zeplin |

**Execution**:
```bash
# Reuse existing workspaces + create new
conductor workspace reuse ws-hai-002 --task "HAI-009 Batch 1"
conductor workspace reuse ws-hai-003 --task "HAI-009 Batch 2"
conductor workspace reuse ws-hai-004 --task "HAI-009 Batch 3"
conductor workspace create ws-hai-010-011 --task "HAI-010 + HAI-011"
conductor workspace create ws-hai-012-013 --task "HAI-012 + HAI-013"
conductor workspace create ws-hai-014 --task "HAI-014"

# In each workspace (parallel execution):
# Add discovery metadata (stack, phase, capabilities, keywords) to assigned agents
# Follow schema from HAI-001
# Validate metadata format
```

**Validation Script**:
```bash
# Run after all Wave 2 updates
python3 installer/global/commands/lib/validate_agent_metadata.py --all
```

**Checkpoint**: Validate all 27 agents have correct metadata

**Merge to Main**: After validation passes

---

### Wave 3: Discovery System (Sequential)

**Duration**: 5 hours
**Workspaces**: 1 (critical integration)
**Checkpoint**: After HAI-005 before HAI-006 (30 minutes)

| Workspace | Task | Method | Duration | Dependencies |
|-----------|------|--------|----------|--------------|
| **WS-A** | HAI-005 | `/task-work` | 3h | HAI-001, HAI-002/003/004, HAI-009-014 |
| **WS-A** | HAI-006 | `/task-work` | 2h | HAI-005 (must complete) |

**Execution**:
```bash
# Reuse WS-A (isolated for sensitive integration)
conductor workspace reuse ws-hai-002 --task "HAI-005 Discovery"

# Step 1: Discovery algorithm (3h)
/task-work TASK-HAI-005-4F78  # With full quality gates

# Step 2: Critical checkpoint (30 min)
# - Test discovery algorithm manually
# - Verify no regressions
# - Validate matches expected agents

# Step 3: Integration (2h)
/task-work TASK-HAI-006-6632  # Integrate with /task-work Phase 3

# Step 4: Integration testing
# - Run sample tasks (Python, React, .NET)
# - Verify agent discovery works
# - Check fallback for unknown stacks
```

**Checkpoint**: Manual testing of discovery algorithm before integration

**Merge to Main**: After HAI-006 integration tests pass

---

### Wave 4: Finalization (Mostly Sequential)

**Duration**: 3.75 hours
**Workspaces**: 2 (documentation + testing)
**Checkpoint**: 15 minutes (final review)

| Workspace | Task | Method | Duration | Dependencies |
|-----------|------|--------|----------|--------------|
| **WS-A** | HAI-007 | Direct | 1.5h | All previous waves |
| **WS-B** | HAI-008 | `/task-work` | 2h | HAI-007 (can overlap 75%) |

**Execution**:
```bash
# Parallel start, sequential finish
conductor workspace reuse ws-hai-002 --task "HAI-007 Docs"
conductor workspace reuse ws-hai-003 --task "HAI-008 E2E Testing"

# Step 1: Documentation (WS-A, 1.5h)
# - Update CLAUDE.md
# - Create docs/guides/agent-discovery.md
# - Update model-optimization.md

# Step 2: E2E Testing (WS-B, 2h) - can start after 20 min of HAI-007
/task-work TASK-HAI-008-1537  # Full test suite with quality gates

# Step 3: Final checkpoint (15 min)
# - Review documentation completeness
# - Verify all E2E tests pass
# - Check integration one more time
```

**Checkpoint**: Final review before blog post

**Merge to Main**: After all tests pass

---

## Conductor Workspace Strategy

### Workspace Allocation

**6 workspaces with intelligent reuse**:

| Workspace | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Total Usage |
|-----------|--------|--------|--------|--------|-------------|
| **WS-Main** | HAI-001 (1.5h) | - | - | - | 1.5h |
| **WS-A** | HAI-002 (2h) | HAI-009-B1 (2h) | HAI-005 (3h), HAI-006 (2h) | HAI-007 (1.5h) | 10.5h |
| **WS-B** | HAI-003 (2h) | HAI-009-B2 (2h) | - | HAI-008 (2h) | 6h |
| **WS-C** | HAI-004 (2h) | HAI-009-B3 (2h) | - | - | 4h |
| **WS-D** | - | HAI-010/011 (3h) | - | - | 3h |
| **WS-E** | - | HAI-012/013 (3h) | - | - | 3h |
| **WS-F** | - | HAI-014 (1.5h) | - | - | 1.5h |

**Benefits**:
- **WS-Main**: Isolated for critical schema design
- **WS-A**: Heavy reuse (4 sequential tasks, 10.5h total)
- **WS-B/C**: Moderate reuse (3 tasks each)
- **WS-D/E/F**: Single-wave usage (Wave 2 parallelization)

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
import yaml
for agent in ['python-api-specialist', 'react-state-specialist', 'dotnet-domain-specialist']:
    with open(f'installer/global/agents/{agent}.md') as f:
        content = f.read()
        # Check for required fields
        assert 'stack:' in content
        assert 'phase:' in content
        assert 'capabilities:' in content
        assert 'keywords:' in content
    print(f'✅ {agent} valid')
"

# 4. Merge to main if all pass
git merge ws-hai-002 ws-hai-003 ws-hai-004
```

**After Wave 2** (20 min):
```bash
# 1. Run validation script
python3 installer/global/commands/lib/validate_agent_metadata.py --all

# 2. Check for missing metadata
python3 -c "
import glob
agents = glob.glob('installer/global/agents/*.md')
for agent in agents:
    with open(agent) as f:
        content = f.read()
        if 'phase:' not in content:
            print(f'⚠️  Missing metadata: {agent}')
"

# 3. Spot-check 3 random agents
cat installer/global/agents/database-specialist.md | head -20
cat installer/global/templates/react-typescript/agents/form-validation-specialist.md | head -20
cat installer/global/templates/fastapi-python/agents/fastapi-specialist.md | head -20

# 4. Merge to main if all pass
git merge <all-wave-2-workspaces>
```

**After Wave 3** (30 min - CRITICAL):
```bash
# 1. Test discovery algorithm manually
python3 -c "
from installer.global.commands.lib.agent_discovery import discover_agents

# Test implementation agents
agents = discover_agents(phase='implementation')
print(f'Found {len(agents)} implementation agents')
assert len(agents) >= 10, 'Should find at least 10 implementation agents'

# Test stack filtering
python_agents = discover_agents(phase='implementation', stack='python')
print(f'Found {len(python_agents)} Python implementation agents')
assert len(python_agents) >= 3, 'Should find Python specialists'

# Test keyword matching
form_agents = discover_agents(phase='implementation', keywords=['form', 'validation'])
print(f'Found {len(form_agents)} form specialists')
assert len(form_agents) >= 1, 'Should find form-validation-specialist'

print('✅ All discovery tests passed')
"

# 2. Test integration with sample task
/task-create "Add user endpoint" stack:python
/task-work TASK-XXX  # Observe which agent is selected for Phase 3

# 3. Check fallback behavior
/task-create "Add feature" stack:rust
/task-work TASK-YYY  # Should fall back gracefully (no Rust specialist yet)

# 4. Merge to main if all pass
git merge ws-hai-002  # Critical: HAI-005 + HAI-006
```

**After Wave 4** (15 min):
```bash
# 1. Review documentation completeness
cat CLAUDE.md | grep -A 20 "Stack-Specific Implementation Agents"
cat docs/guides/agent-discovery.md

# 2. Check E2E test results
cat .claude/state/TASK-HAI-008-1537/test-results.json

# 3. Final integration test
/task-create "Complete workflow test" stack:python
/task-work TASK-ZZZ  # Full workflow with discovery

# 4. Merge to main
git merge ws-hai-002 ws-hai-003  # HAI-007 + HAI-008
```

### Merge-to-Main Schedule

| Point | Branches | Validation |
|-------|----------|------------|
| **After Wave 1** | ws-hai-002/003/004 | Schema + 3 agents validated |
| **After Wave 2** | 6 workspace branches | 27 agents metadata validated |
| **After HAI-005** | ws-hai-002 (discovery only) | Discovery algorithm tested manually |
| **After HAI-006** | ws-hai-002 (integration) | Integration tested with sample tasks |
| **After Wave 4** | ws-hai-002/003 (docs + tests) | E2E tests pass, docs complete |

**Total Merges**: 5 (incremental integration reduces risk)

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
| **HAI-009** | Inconsistent metadata across 12 agents | Automated validation script |
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
| Wave 1 | 2.25h (parallel) | 0.25h | 2.5h |
| Wave 2 | 6.3h (parallel) | 0.33h | 6.6h |
| Wave 3 | 5h (sequential) | 0.5h | 5.5h |
| Wave 4 | 2.25h (overlap) | 0.25h | 2.5h |

**Reality Check**: Assumes zero context switching, perfect workspace management, no unexpected issues.

### Realistic (With Overhead)

**Total**: 3.5 days (20 hours + overhead)

| Wave | Duration | Checkpoints | Overhead | Total |
|------|----------|-------------|----------|-------|
| Wave 1 | 2.25h | 0.25h | 0.5h (setup) | 3h |
| Wave 2 | 6.3h | 0.33h | 1h (validation) | 7.6h |
| Wave 3 | 5h | 0.5h | 1h (integration testing) | 6.5h |
| Wave 4 | 2.25h | 0.25h | 0.5h (final review) | 3h |

**Overhead includes**:
- Workspace creation/switching
- Context loading
- Unexpected issues
- Coffee breaks ☕

### Conservative (Sequential Fallback)

**Total**: 4.5 days (29 hours + buffer)

**Scenario**: If parallelization issues arise, fall back to sequential execution with 1-day buffer.

---

## Pre-Execution Checklist

### Environment Setup

- [ ] Conductor installed and configured
- [ ] Taskwright symlinks verified (`taskwright doctor`)
- [ ] Git worktree support confirmed
- [ ] 6 workspace slots available (check Conductor limits)
- [ ] Main branch clean (no uncommitted changes)

### Validation Tools Ready

- [ ] Schema validation script: `installer/global/commands/lib/validate_agent_metadata.py`
- [ ] Agent metadata checker (Python script)
- [ ] Discovery algorithm test suite (from HAI-005)

### Documentation Access

- [ ] HAI-001 through HAI-014 task files accessible
- [ ] Schema definition from HAI-001 available
- [ ] Agent template references loaded

---

## Execution Commands (Quick Reference)

### Wave 1 Execution

```bash
# Foundation
cd ~/Projects/taskwright-main
/task-work TASK-HAI-001-D668

# After HAI-001 completes + checkpoint
conductor workspace create ws-hai-002 && cd ws-hai-002
# Create python-api-specialist.md with metadata

conductor workspace create ws-hai-003 && cd ws-hai-003
# Create react-state-specialist.md with metadata

conductor workspace create ws-hai-004 && cd ws-hai-004
# Create dotnet-domain-specialist.md with metadata

# Checkpoint + merge
# <validation steps from checkpoint workflow>
git checkout main && git merge ws-hai-002 ws-hai-003 ws-hai-004
```

### Wave 2 Execution

```bash
# 6 parallel workspaces
conductor workspace reuse ws-hai-002 && cd ws-hai-002
# Update architectural-reviewer, code-reviewer, pattern-advisor, complexity-evaluator

conductor workspace reuse ws-hai-003 && cd ws-hai-003
# Update test-orchestrator, test-verifier, build-validator, debugging-specialist

conductor workspace reuse ws-hai-004 && cd ws-hai-004
# Update database-specialist, devops-specialist, security-specialist, git-workflow-manager

conductor workspace create ws-hai-010-011 && cd ws-hai-010-011
# Update react-typescript (3) + fastapi-python (3)

conductor workspace create ws-hai-012-013 && cd ws-hai-012-013
# Update nextjs-fullstack (3) + react-fastapi-monorepo (3)

conductor workspace create ws-hai-014 && cd ws-hai-014
# Update taskwright-python (3) + agent-content-enhancer + figma + zeplin

# Validation + merge
python3 installer/global/commands/lib/validate_agent_metadata.py --all
git checkout main && git merge <all 6 workspaces>
```

### Wave 3 Execution

```bash
# Critical sequential path
conductor workspace reuse ws-hai-002 && cd ws-hai-002

# Discovery algorithm
/task-work TASK-HAI-005-4F78

# Critical checkpoint (30 min manual testing)
# <manual discovery tests from checkpoint workflow>

# Integration
/task-work TASK-HAI-006-6632

# Merge
git checkout main && git merge ws-hai-002
```

### Wave 4 Execution

```bash
# Documentation (WS-A)
conductor workspace reuse ws-hai-002 && cd ws-hai-002
# Update CLAUDE.md, create docs/guides/agent-discovery.md

# E2E Testing (WS-B, parallel after 20 min)
conductor workspace reuse ws-hai-003 && cd ws-hai-003
/task-work TASK-HAI-008-1537

# Final checkpoint + merge
# <final validation from checkpoint workflow>
git checkout main && git merge ws-hai-002 ws-hai-003
```

---

## Post-Execution Verification

### Completeness Check

```bash
# 1. Count agents with metadata
python3 -c "
import glob
agents = glob.glob('installer/global/agents/*.md') + glob.glob('installer/global/templates/*/agents/*.md')
with_metadata = 0
for agent in agents:
    with open(agent) as f:
        if 'phase:' in f.read():
            with_metadata += 1
print(f'✅ {with_metadata}/{len(agents)} agents have discovery metadata')
assert with_metadata >= 30, 'Should have at least 30 agents with metadata'
"

# 2. Test discovery for each stack
python3 -c "
from installer.global.commands.lib.agent_discovery import discover_agents
stacks = ['python', 'react', 'dotnet', 'typescript']
for stack in stacks:
    agents = discover_agents(phase='implementation', stack=stack)
    print(f'{stack}: {len(agents)} agents')
    assert len(agents) >= 2, f'Should find agents for {stack}'
"

# 3. Verify documentation
test -f docs/guides/agent-discovery.md && echo "✅ Discovery guide exists"
grep -q "Stack-Specific Implementation Agents" CLAUDE.md && echo "✅ CLAUDE.md updated"

# 4. Run full E2E test suite
/task-status TASK-HAI-008-1537 | grep "COMPLETED" && echo "✅ E2E tests passed"
```

### Performance Validation

```bash
# Test discovery performance
python3 -c "
import time
from installer.global.commands.lib.agent_discovery import discover_agents

start = time.time()
agents = discover_agents(phase='implementation')
duration = time.time() - start

print(f'Discovery time: {duration*1000:.1f}ms')
print(f'Agents found: {len(agents)}')
assert duration < 0.1, 'Discovery should be < 100ms'
"
```

---

## Troubleshooting

### Common Issues

**Issue**: Workspace state conflicts
```bash
# Solution: Verify symlinks
ls -la .claude/state  # Should point to main repo
./installer/scripts/install.sh  # Recreate symlinks
```

**Issue**: Discovery returns empty list
```bash
# Solution: Check metadata format
python3 installer/global/commands/lib/validate_agent_metadata.py --debug
```

**Issue**: Integration tests fail in HAI-006
```bash
# Solution: Roll back and debug
git checkout main
/task-work TASK-HAI-006-6632 --debug
```

**Issue**: Merge conflicts between workspaces
```bash
# Solution: Sequential merge
git merge ws-hai-002  # Merge one at a time
# Resolve conflicts
git merge ws-hai-003
# Continue...
```

---

## Success Criteria

### Functional
- [ ] 30 agents have discovery metadata (15 global + 15 template)
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
- [ ] Discovery query < 100ms
- [ ] No slowdown in /task-work execution
- [ ] Parallel execution achieved expected speedup

---

## Recommended Approach

**Best Strategy**: Follow waves sequentially with checkpoints

1. **Wave 1** (Day 1 morning): Foundation + 3 new agents
2. **Wave 2** (Day 1 afternoon + Day 2): Update 27 existing agents
3. **Wave 3** (Day 3): Discovery system (critical, sequential)
4. **Wave 4** (Day 4 morning): Finalization
5. **Blog Post** (Day 4 afternoon / Day 5): Write with complete implementation

**Why This Works**:
- Built-in quality gates via `/task-work` where it matters
- Parallelization where safe (agent metadata updates)
- Sequential execution for critical integration points
- Checkpoints prevent compound errors
- Realistic timeline with buffer

**Total**: 3.5-4 days → Blog post ready with complete story

---

**Status**: ✅ Ready to Execute
**Next Action**: Start Wave 1 (HAI-001 schema design)
