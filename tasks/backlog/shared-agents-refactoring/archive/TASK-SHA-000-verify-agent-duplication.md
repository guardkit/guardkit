---
id: TASK-SHA-000
title: Verify agent duplication between TaskWright and RequireKit
status: backlog
created: 2025-11-28T20:30:00Z
updated: 2025-11-28T20:30:00Z
priority: critical
tags: [shared-agents, verification, phase-0, prerequisite]
complexity: 3
estimated_effort: 2h
phase: "Phase 0: Prerequisites"
depends_on: []
blocks: [TASK-SHA-P1-002]
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Verify Agent Duplication

## Context

**Critical Finding from Architectural Review**: The proposal assumes certain agents are duplicated between TaskWright and RequireKit, but this assumption has not been verified. Migrating the wrong agents would break existing workflows.

**Risk**: High severity - Could migrate wrong agents, breaking both tools
**Mitigation**: Create verification script to identify truly duplicated agents

## Description

Create and execute a verification script that compares agents between TaskWright and RequireKit repositories to identify which agents are truly duplicated (≥80% similarity).

## Acceptance Criteria

- [ ] Script created: `scripts/verify-agent-duplication.sh`
- [ ] Script compares TaskWright and RequireKit agents
- [ ] Output includes:
  - [ ] Agent name
  - [ ] Similarity percentage
  - [ ] Duplication status (TRUE DUPLICATE / DIVERGED / UNIQUE)
  - [ ] File paths for both versions
- [ ] Verified duplication list documented
- [ ] Results peer-reviewed by 2+ people
- [ ] Proposal updated with accurate agent list (if needed)

## Implementation Approach

### 1. Create Verification Script

```bash
#!/bin/bash
# scripts/verify-agent-duplication.sh

set -e

GUARDKIT_AGENTS="installer/global/agents"
REQUIREKIT_AGENTS="../require-kit/.claude/agents"

echo "======================================================================="
echo "Agent Duplication Verification"
echo "======================================================================="
echo ""
echo "Comparing:"
echo "  TaskWright: $GUARDKIT_AGENTS"
echo "  RequireKit: $REQUIREKIT_AGENTS"
echo ""

# Check RequireKit path exists
if [ ! -d "$REQUIREKIT_AGENTS" ]; then
    echo "ERROR: RequireKit agents directory not found: $REQUIREKIT_AGENTS"
    echo "Please clone RequireKit repository to ../require-kit/"
    exit 1
fi

# Create output file
OUTPUT_FILE="docs/agent-duplication-verification.txt"
mkdir -p docs

echo "=== TRUE DUPLICATES (≥80% similarity) ===" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

duplicates=0
diverged=0
unique=0

for agent in $GUARDKIT_AGENTS/*.md; do
    basename=$(basename "$agent")
    requirekit_agent="$REQUIREKIT_AGENTS/$basename"

    if [ -f "$requirekit_agent" ]; then
        # Calculate similarity (line-based diff)
        total_lines=$(wc -l < "$agent")
        diff_lines=$(diff "$agent" "$requirekit_agent" | grep -c '^[<>]' || echo 0)
        similarity=$(( 100 - (diff_lines * 100 / total_lines) ))

        if [ $similarity -ge 80 ]; then
            echo "✅ $basename - ${similarity}% similar (TRUE DUPLICATE)" | tee -a "$OUTPUT_FILE"
            echo "   TaskWright: $agent" | tee -a "$OUTPUT_FILE"
            echo "   RequireKit: $requirekit_agent" | tee -a "$OUTPUT_FILE"
            echo "" | tee -a "$OUTPUT_FILE"
            duplicates=$((duplicates + 1))
        else
            echo "⚠️  $basename - ${similarity}% similar (DIVERGED - NOT DUPLICATE)"
            echo "   These agents have diverged significantly."
            echo "   Manual review required before migration."
            echo ""
            diverged=$((diverged + 1))
        fi
    else
        echo "ℹ️  $basename - UNIQUE (TaskWright only)"
        unique=$((unique + 1))
    fi
done

echo "" >> "$OUTPUT_FILE"
echo "=== SUMMARY ===" >> "$OUTPUT_FILE"
echo "True duplicates: $duplicates" >> "$OUTPUT_FILE"
echo "Diverged agents: $diverged" >> "$OUTPUT_FILE"
echo "Unique to TaskWright: $unique" >> "$OUTPUT_FILE"

echo ""
echo "======================================================================="
echo "Summary:"
echo "  True duplicates: $duplicates (will be migrated)"
echo "  Diverged agents: $diverged (manual review needed)"
echo "  Unique to TaskWright: $unique (won't be migrated)"
echo ""
echo "Results saved to: $OUTPUT_FILE"
echo "======================================================================="
```

### 2. Execute Verification

```bash
chmod +x scripts/verify-agent-duplication.sh
./scripts/verify-agent-duplication.sh
```

### 3. Document Verified List

Create `docs/verified-universal-agents.md`:

```markdown
# Verified Universal Agents

**Verification Date**: 2025-11-28
**Verification Method**: Automated similarity analysis (≥80% threshold)
**Script**: scripts/verify-agent-duplication.sh

## True Duplicates (To Be Migrated)

Based on verification script output:

1. **agent-name.md** - XX% similarity
   - TaskWright: installer/global/agents/agent-name.md
   - RequireKit: .claude/agents/agent-name.md
   - Status: ✅ Verified duplicate

[Add all verified duplicates]

## Diverged Agents (Not Migrating)

[Add diverged agents that need manual review]

## Unique Agents

**TaskWright Only**:
- [List agents unique to TaskWright]

**RequireKit Only**:
- [List agents unique to RequireKit]
```

### 4. Peer Review

- Share results with TaskWright maintainer
- Share results with RequireKit maintainer
- Document any discrepancies or concerns
- Get sign-off from both teams

## Test Requirements

### Verification Tests

- [ ] Script runs without errors
- [ ] Script handles missing RequireKit directory gracefully
- [ ] Similarity calculation accurate (spot-check 3+ agents manually)
- [ ] Output file created successfully
- [ ] Summary counts correct

### Edge Cases

- [ ] Agent exists in TaskWright but not RequireKit (unique)
- [ ] Agents with similar names but different content (diverged)
- [ ] Empty agent files (handle gracefully)
- [ ] Binary files (skip with warning)

## Dependencies

**Prerequisite Tasks**: None (this is Phase 0)

**Blocks**:
- TASK-SHA-P1-002 (Migrate Universal Agents)
- All subsequent migration tasks

**External Dependencies**:
- RequireKit repository cloned to `../require-kit/`
- `diff` command available (standard on Unix systems)

## Success Criteria

- [ ] Verification script executes successfully
- [ ] Output file created: `docs/agent-duplication-verification.txt`
- [ ] Verified list documented: `docs/verified-universal-agents.md`
- [ ] Peer review completed (2+ approvals)
- [ ] Zero false positives (agents incorrectly marked as duplicates)
- [ ] Zero false negatives (true duplicates missed)

## Estimated Effort

**Total**: 2 hours
- Script creation: 1 hour
- Execution and analysis: 30 minutes
- Documentation: 30 minutes

## Notes

### Why This Matters (from Architectural Review)

The proposal assumes these 4 agents are universal:
1. `requirements-analyst.md`
2. `bdd-generator.md`
3. `test-orchestrator.md`
4. `code-reviewer.md`

However:
- `test-orchestrator.md` exists in TaskWright `installer/global/agents/` ✅
- `code-reviewer.md` exists in TaskWright `installer/global/agents/` ✅
- `requirements-analyst.md` may be RequireKit-only ⚠️
- `bdd-generator.md` may be RequireKit-only ⚠️

**This verification will confirm the actual duplication.**

### Manual Review Criteria

If similarity is 70-79%, manual review required to determine:
- Are differences intentional (tool-specific)?
- Can agents be unified?
- Should they remain separate?

## Related Documents

- Architectural Review: `.claude/reviews/TASK-ARCH-DC05-shared-agents-architectural-review.md`
- Implementation Plan: `tasks/backlog/shared-agents-refactoring/IMPLEMENTATION-PLAN.md`
- Risk Mitigation Plan: `.claude/reviews/TASK-ARCH-DC05-risk-mitigation-plan.md`
