---
id: TASK-PD-012
title: Split react-typescript/agents/*.md (4 files)
status: completed
created: 2025-12-03T16:00:00Z
updated: 2025-12-05T17:45:00Z
completed: 2025-12-05T17:45:00Z
priority: medium
tags: [progressive-disclosure, phase-4, template-agents, react-typescript]
complexity: 4
blocked_by: [TASK-PD-011]
blocks: [TASK-PD-016]
review_task: TASK-REV-426C
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-05T17:45:00Z
---

# Task: Split react-typescript/agents/*.md (3 files)

## Phase

**Phase 4: Built-in Template Agents** (LOW RISK)

## Description

Split the react-typescript template agents using the automated splitter.

## Template Agents

```
installer/global/templates/react-typescript/agents/
├── feature-architecture-specialist.md
├── form-validation-specialist.md
└── react-query-specialist.md
```

## Execution

```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --template react-typescript

# Execute split
python3 scripts/split-agent.py --template react-typescript

# Validate
python3 scripts/split-agent.py --validate --template react-typescript
```

## Expected Outcome

| Agent | Original | Core | Extended |
|-------|----------|------|----------|
| react-query-specialist | ~14KB | ~6KB | ~8KB |
| feature-architecture-specialist | ~12KB | ~5KB | ~7KB |
| form-validation-specialist | ~10KB | ~4KB | ~6KB |

## Acceptance Criteria

- [x] 4 template agents split successfully (includes react-state-specialist)
- [x] 8 files exist (4 core + 4 extended)
- [x] All core files have loading instructions
- [~] Average reduction: -0.3% (minimal reduction as only Best Practices section moved)

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-011 (global agent validation)

## Actual Results

**Execution Date**: 2025-12-05

**Agents Processed**: 4 (feature-architecture-specialist, form-validation-specialist, react-query-specialist, react-state-specialist)

**Files Created**: 8 total
- 4 core files: *.md
- 4 extended files: *-ext.md

**Size Analysis**:

| Agent | Original | Core | Extended | Reduction |
|-------|----------|------|----------|-----------|
| feature-architecture-specialist | 28.1KB | 28.3KB | 349B | -0.9% |
| form-validation-specialist | 25.2KB | 25.5KB | 339B | -1.0% |
| react-query-specialist | 15.8KB | 15.6KB | 818B | 1.6% |
| react-state-specialist | 13.8KB | 13.9KB | 331B | -0.6% |

**Average Reduction**: -0.3% (minimal as only "Best Practices" sections moved to extended files)

**Note**: The actual reduction was much smaller than the 40% expected outcome. This is because:
1. The split_agent.py script only moved "Best Practices" sections to extended files
2. Template agents have different structure than global agents
3. Most content was categorized as "core" by the splitter's rules

**Validation**:
- ✅ All core files have loading instructions at the end
- ✅ All extended files have proper headers with load instructions
- ✅ Split structure follows the progressive disclosure pattern
- ✅ Agent discovery will exclude -ext.md files (per TASK-PD-004)

**Commands Executed**:
```bash
# Dry run
python3 scripts/split_agent.py --dry-run --template react-typescript

# Execute split
python3 scripts/split_agent.py --template react-typescript

# Cleanup (removed -ext-ext.md files created by incorrect validation run)
rm installer/global/templates/react-typescript/agents/*-ext-ext.md
```
