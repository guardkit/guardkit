---
id: TASK-PD-018
title: Update command docs (template-create.md, agent-enhance.md)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-5, documentation, commands]
complexity: 3
blocked_by: [TASK-PD-017]
blocks: [TASK-PD-019]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update command docs (template-create.md, agent-enhance.md)

## Phase

**Phase 5: Validation & Documentation**

## Description

Update command documentation to reflect progressive disclosure output structure.

## Files to Update

### 1. template-create.md

Add section on split output:

```markdown
## Output Structure

### Default (Progressive Disclosure)

```
output-dir/
├── CLAUDE.md              # Core (~8KB)
├── docs/
│   ├── patterns/
│   │   └── README.md      # Pattern documentation
│   └── reference/
│       └── README.md      # Reference documentation
├── agents/
│   ├── specialist.md      # Core agent (~6KB)
│   └── specialist-ext.md  # Extended content
└── ...
```

### Single-File Mode (Not Recommended)

```bash
/template-create --no-split
```

Produces single CLAUDE.md and single agent files.

## Size Targets

| File | Target | Validation |
|------|--------|------------|
| CLAUDE.md (core) | ≤10KB | Enforced |
| Agent (core) | ≤15KB | Warning at 20KB |
| Reduction | ≥50% | Validated |
```

### 2. agent-enhance.md

Add section on split output:

```markdown
## Output Structure

### Default (Progressive Disclosure)

When enhancing an agent, two files are produced:

```
agents/
├── my-agent.md        # Core content (~6KB)
└── my-agent-ext.md    # Extended content (~10KB)
```

**Core file contains**:
- Frontmatter (discovery metadata)
- Quick Start (5-10 examples)
- Boundaries (ALWAYS/NEVER/ASK)
- Capabilities summary
- Loading instructions

**Extended file contains**:
- Detailed code examples (30+)
- Best practices with explanations
- Anti-patterns with code
- Technology-specific guidance

### Single-File Mode

```bash
/agent-enhance my-agent.md --no-split
```

Produces single enhanced file (not recommended).

## Loading Extended Content

The core file includes loading instructions:

```markdown
## Extended Reference

Before generating code, load the extended reference:

```bash
cat agents/my-agent-ext.md
```
```
```

## Acceptance Criteria

- [ ] template-create.md updated with split output structure
- [ ] agent-enhance.md updated with split output structure
- [ ] Size targets documented
- [ ] --no-split flag documented
- [ ] Loading instructions explained

## Files to Modify

1. `installer/global/commands/template-create.md`
2. `installer/global/commands/agent-enhance.md`

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-017 (CLAUDE.md updated)
