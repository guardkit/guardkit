---
id: TASK-SHA-001
title: Verify which agents are truly duplicated between repos
status: backlog
created: 2025-11-28T21:00:00Z
updated: 2025-11-28T21:00:00Z
priority: critical
tags: [shared-agents, verification, lean]
complexity: 2
estimated_effort: 1h
depends_on: []
blocks: [TASK-SHA-002]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Verify Agent Duplication

## Context

Before migrating agents to a shared repository, we need to verify which agents actually exist in BOTH GuardKit and RequireKit. The proposal assumes certain agents are duplicated, but we need to confirm this.

**Why critical**: Migrating wrong agents would break one or both tools.

## Acceptance Criteria

- [ ] Comparison script created and executed
- [ ] List of truly duplicated agents documented
- [ ] Similarity check performed (files should be >80% similar)
- [ ] Verified list approved for migration

## Implementation

### Simple Verification Script

```bash
#!/bin/bash
# verify-duplication.sh

GUARDKIT_AGENTS="installer/global/agents"
REQUIREKIT_AGENTS="../require-kit/.claude/agents"

echo "========================================"
echo "Agent Duplication Verification"
echo "========================================"
echo ""

# Check both directories exist
if [ ! -d "$REQUIREKIT_AGENTS" ]; then
    echo "ERROR: RequireKit not found at ../require-kit/"
    echo "Please clone RequireKit first"
    exit 1
fi

# Find common agents
echo "Agents present in BOTH repositories:"
echo ""

COMMON=$(comm -12 \
    <(ls $GUARDKIT_AGENTS/*.md 2>/dev/null | xargs basename -a | sort) \
    <(ls $REQUIREKIT_AGENTS/*.md 2>/dev/null | xargs basename -a | sort))

if [ -z "$COMMON" ]; then
    echo "No common agents found!"
    exit 1
fi

# Check each common agent
for agent in $COMMON; do
    tw_file="$GUARDKIT_AGENTS/$agent"
    rk_file="$REQUIREKIT_AGENTS/$agent"

    # Quick similarity check (line count difference)
    tw_lines=$(wc -l < "$tw_file")
    rk_lines=$(wc -l < "$rk_file")
    diff_lines=$(echo "$tw_lines - $rk_lines" | bc | tr -d -)
    similarity=$(echo "100 - ($diff_lines * 100 / $tw_lines)" | bc)

    if [ $similarity -gt 80 ]; then
        echo "✅ $agent (${similarity}% similar - MIGRATE)"
    else
        echo "⚠️  $agent (${similarity}% similar - REVIEW MANUALLY)"
    fi
done

echo ""
echo "========================================"
echo "Save the ✅ marked agents for migration"
echo "========================================"
```

### Execute

```bash
chmod +x scripts/verify-duplication.sh
./scripts/verify-duplication.sh > docs/verified-agents.txt
cat docs/verified-agents.txt
```

### Document Results

Create `docs/verified-agents-for-migration.md`:

```markdown
# Verified Agents for Migration

**Verification Date**: 2025-11-28
**Method**: File comparison between GuardKit and RequireKit

## Agents to Migrate

Based on verification script:

1. **agent-name.md** - XX% similarity ✅
2. **agent-name.md** - XX% similarity ✅

## Agents to Review Manually

(If any showed <80% similarity)

## Agents NOT to Migrate

**GuardKit only**: ...
**RequireKit only**: ...
```

## Test Requirements

- [ ] Script runs without errors
- [ ] All common agents identified
- [ ] Similarity percentages make sense
- [ ] List reviewed by human (sanity check)

## Estimated Effort

**1 hour**
- Script creation: 20 minutes
- Execution: 10 minutes
- Documentation: 30 minutes

## Success Criteria

- [ ] Clear list of agents to migrate
- [ ] High confidence (>80% similarity)
- [ ] No obvious mistakes (manual spot check)
- [ ] List approved to proceed

## Notes

**Keep it simple**: We don't need elaborate diff analysis. If agents have similar line counts and exist in both repos, they're likely duplicates. Manual spot-check a few files to confirm.

**If agents differ significantly**: Either they've diverged (don't migrate) or they're tool-specific (don't migrate).
