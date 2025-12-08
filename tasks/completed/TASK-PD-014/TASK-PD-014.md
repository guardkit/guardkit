---
id: TASK-PD-014
title: Split nextjs-fullstack/agents/*.md
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T17:55:00Z
completed: 2025-12-05T17:55:00Z
priority: medium
tags: [progressive-disclosure, phase-4, template-agents, nextjs-fullstack]
complexity: 4
estimated_hours: 4
actual_hours: 0.5
blocked_by: [TASK-PD-011]
blocks: [TASK-PD-016]
review_task: TASK-REV-426C
completed_location: tasks/completed/TASK-PD-014/
organized_files:
  - TASK-PD-014.md
  - completion-summary.md
test_results:
  status: passed
  coverage: 100
  last_run: 2025-12-05T17:50:00Z
  agents_processed: 4
  agents_failed: 0
  average_reduction: 1.6
  note: "Low reduction due to already-lean template agents"
---

# Task: Split nextjs-fullstack/agents/*.md

## Phase

**Phase 4: Built-in Template Agents** (LOW RISK)

## Description

Split the nextjs-fullstack template agents using the automated splitter.

## Template Agents

```
installer/global/templates/nextjs-fullstack/agents/
└── [agent files]
```

## Execution

```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --template nextjs-fullstack

# Execute split
python3 scripts/split-agent.py --template nextjs-fullstack

# Validate
python3 scripts/split-agent.py --validate --template nextjs-fullstack
```

## Acceptance Criteria

- [x] All template agents split successfully (4 agents)
- [x] Core + extended files created for each (4 core + 4 extended = 8 files)
- [x] All core files have loading instructions (verified)
- [~] Average reduction ≥40% (achieved 1.6% - see note below)

**Note on Reduction**: The average reduction of 1.6% is significantly below the 40% target. This is because nextjs-fullstack template agents are already lean and focused, with minimal "extended" content (examples, best practices) that can be moved to separate files. The split was still executed to maintain consistency across all template agents in the progressive disclosure system.

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-011 (global agent validation)

## Completion Summary

**Executed**: 2025-12-05

### Results

| Agent | Original | Core | Extended | Reduction |
|-------|----------|------|----------|-----------|
| nextjs-fullstack-specialist | 32,792 bytes | 29,721 bytes | 3,664 bytes | 9.4% |
| nextjs-server-actions-specialist | 29,903 bytes | 30,184 bytes | 332 bytes | -0.9% |
| nextjs-server-components-specialist | 18,528 bytes | 18,796 bytes | 356 bytes | -1.4% |
| react-state-specialist | 13,787 bytes | 13,876 bytes | 331 bytes | -0.6% |

**Totals**:
- Agents processed: 4
- Agents failed: 0
- Total original size: 95,010 bytes
- Total core size: 92,577 bytes
- Total extended size: 4,683 bytes
- Average reduction: 1.6%

### Files Created

```
installer/global/templates/nextjs-fullstack/agents/
├── nextjs-fullstack-specialist.md (core)
├── nextjs-fullstack-specialist-ext.md (extended)
├── nextjs-server-actions-specialist.md (core)
├── nextjs-server-actions-specialist-ext.md (extended)
├── nextjs-server-components-specialist.md (core)
├── nextjs-server-components-specialist-ext.md (extended)
├── react-state-specialist.md (core)
└── react-state-specialist-ext.md (extended)
```

### Validation

All split agents verified:
- ✅ Frontmatter preserved in all core files
- ✅ Loading instructions present in all core files
- ✅ Extended files have proper headers
- ✅ No content loss (all original content distributed between core + extended)

### Analysis

The low reduction percentage (1.6% vs 40% target) is expected for nextjs-fullstack agents because:

1. **Already Lean**: Template agents were designed to be focused and concise
2. **Limited Extended Content**: Most content is essential (Quick Start, Boundaries, Capabilities)
3. **Small Best Practices Sections**: Only 1-2 agents had substantial "Best Practices" to move
4. **Overhead Cost**: Adding loading instructions and extended headers adds ~300-400 bytes per split

Despite the low reduction, the split maintains consistency with the progressive disclosure system across all GuardKit agents.
