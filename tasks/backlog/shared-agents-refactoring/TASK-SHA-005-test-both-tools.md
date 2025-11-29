---
id: TASK-SHA-005
title: Test both tools work with shared-agents
status: backlog
created: 2025-11-28T21:00:00Z
updated: 2025-11-28T21:00:00Z
priority: critical
tags: [shared-agents, testing, lean]
complexity: 2
estimated_effort: 1h
depends_on: [TASK-SHA-003, TASK-SHA-004]
blocks: [TASK-SHA-006]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Test Both Tools

## Context

Simple smoke testing to verify both TaskWright and RequireKit work correctly with shared-agents. Keep it practical - if the main commands work, we're good.

## Acceptance Criteria

- [ ] TaskWright standalone works
- [ ] RequireKit standalone works
- [ ] Both tools together work (no conflicts)
- [ ] Shared agents are discovered correctly
- [ ] No obvious regressions

## Implementation

### Test Scenario 1: TaskWright Standalone

```bash
# Fresh test directory
mkdir test-taskwright-solo
cd test-taskwright-solo

# Install TaskWright
../taskwright/installer/scripts/install.sh

# Verify shared agents installed
test -d .claude/agents/universal && echo "✅ Universal agents present"
ls .claude/agents/universal/*.md

# Test core functionality
/task-create "Test task for shared agents"
/task-status
# Should show new task

# Try using an agent (if applicable)
/task-work TASK-001
# Should work without errors
```

**Pass criteria**: Commands execute without errors

### Test Scenario 2: RequireKit Standalone

```bash
# Fresh test directory
mkdir test-requirekit-solo
cd test-requirekit-solo

# Install RequireKit
../require-kit/installer/scripts/install.sh

# Verify shared agents installed
test -d .claude/agents/universal && echo "✅ Universal agents present"
ls .claude/agents/universal/*.md

# Test RequireKit commands
# (Execute main RequireKit workflow)
```

**Pass criteria**: Commands execute without errors

### Test Scenario 3: Both Tools Together

```bash
# Fresh test directory
mkdir test-both-tools
cd test-both-tools

# Install TaskWright first
../taskwright/installer/scripts/install.sh
count1=$(ls .claude/agents/universal/*.md | wc -l)

# Install RequireKit second
../require-kit/installer/scripts/install.sh
count2=$(ls .claude/agents/universal/*.md | wc -l)

# Verify no duplication
if [ $count1 -eq $count2 ]; then
    echo "✅ No duplication - shared agents count unchanged"
else
    echo "❌ Agent count changed: $count1 -> $count2"
fi

# Test both tools
/task-status  # TaskWright
# (RequireKit command)  # RequireKit

# Both should work
```

**Pass criteria**: Agent count stays same, both tools work

### Test Scenario 4: Agent Discovery

```bash
# Verify agents are discovered
cd .claude/agents

# Check structure
tree .
# Should show:
# .
# ├── universal/          (shared agents)
# │   ├── code-reviewer.md
# │   └── test-orchestrator.md
# └── (other local agents if any)

# Verify agent metadata (if applicable)
grep -H "name:" universal/*.md
# Should show agent names
```

**Pass criteria**: Agents have valid frontmatter and are in correct location

## Test Requirements

### Manual Testing Checklist

- [ ] Test 1: TaskWright alone ✅/❌
- [ ] Test 2: RequireKit alone ✅/❌
- [ ] Test 3: Both together ✅/❌
- [ ] Test 4: Agent discovery ✅/❌

### If Any Test Fails

1. Check `.claude/agents/universal/` exists
2. Check agents downloaded correctly
3. Check installer logs for errors
4. Verify v1.0.0 release is accessible
5. Try manual download: `curl -sL https://github.com/taskwright-dev/shared-agents/releases/download/v1.0.0/shared-agents.tar.gz`

## Estimated Effort

**1 hour**
- Test setup: 20 minutes
- Execute scenarios: 30 minutes
- Verify results: 10 minutes

## Success Criteria

- [ ] All 4 test scenarios pass
- [ ] No errors in any tool
- [ ] No agent duplication
- [ ] Shared agents discoverable
- [ ] **Ready to ship** 🚀

## Notes

**Keep it simple**: We're doing smoke testing, not comprehensive QA. If basic workflows work, we're good. We can catch edge cases in production if needed.

**What we're NOT testing** (intentionally):
- ❌ Version conflicts (handling multiple versions)
- ❌ Offline installation (edge case)
- ❌ Network failures (can handle if occurs)
- ❌ Concurrent installations (unlikely scenario)
- ❌ Every possible agent command (basic ones suffice)

**If bugs found**: Fix them quickly and re-test. Ship when smoke tests pass.
