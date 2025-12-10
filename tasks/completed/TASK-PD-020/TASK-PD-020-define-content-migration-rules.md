---
id: TASK-PD-020
title: Define content migration rules and patterns
status: completed
created: 2025-12-06T10:00:00Z
updated: 2025-12-06T12:35:00Z
completed: 2025-12-06T12:35:00Z
priority: high
tags: [progressive-disclosure, phase-6, content-migration, rules]
complexity: 4
blocked_by: [TASK-PD-019, TASK-REV-PD6]
blocks: [TASK-PD-021, TASK-PD-022, TASK-PD-023]
review_task: TASK-REV-PD-CONTENT
completed_location: tasks/completed/TASK-PD-020/
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-06T12:33:00Z
---

# Task: Define content migration rules and patterns

## Phase

**Phase 6: Content Migration** (Task 1 of 5)

## Description

Define the rules and patterns for migrating content from core agent files to extended files. This establishes the categorization logic that will be applied consistently across all 14 agents.

## Deliverables

### 1. Content Categorization Document

Create `docs/guides/content-migration-rules.md` with:

```markdown
# Content Migration Rules for Progressive Disclosure

## Core File Content (Keep in {agent}.md)

### Required Sections
1. **Frontmatter** - All metadata (name, description, tools, tags, etc.)
2. **Title and Overview** - Agent name and 2-3 sentence description
3. **Quick Start** - 5-10 essential examples showing common usage
4. **Boundaries** - Complete ALWAYS/NEVER/ASK sections
5. **Capabilities Summary** - Bullet list of what agent can do
6. **Phase Integration** - When agent is invoked in workflow
7. **Extended Reference** - Loading instruction for ext file

### Size Targets
- Core file: ≤15KB (warning at 20KB)
- Quick Start: 5-10 examples max
- Boundaries: 5-7 rules each section

## Extended File Content (Move to {agent}-ext.md)

### Sections to Move
1. **Detailed Examples** - Comprehensive code examples (30+)
2. **Best Practices** - Full explanations with rationale
3. **Anti-Patterns** - Code samples showing what NOT to do
4. **Technology-Specific Guidance** - Stack-specific details
5. **Troubleshooting** - Common issues and solutions
6. **Edge Cases** - Handling unusual scenarios
7. **Integration Patterns** - How to work with other agents

### Size Expectations
- Extended file: 10-40KB depending on agent complexity
- No upper limit (comprehensive is good)
```

### 2. Migration Script Enhancement

Update `scripts/split-agent.py` (or create new `scripts/migrate-agent-content.py`) with:

```python
# Content categorization patterns
CORE_SECTIONS = [
    'frontmatter',
    r'^# .*',  # Title
    r'^## Overview',
    r'^## Quick Start',
    r'^## Boundaries',
    r'^### ALWAYS',
    r'^### NEVER',
    r'^### ASK',
    r'^## Capabilities',
    r'^## Phase Integration',
    r'^## Extended Reference',
]

EXTENDED_SECTIONS = [
    r'^## Detailed Examples',
    r'^## Best Practices',
    r'^## Anti-Patterns',
    r'^## Technology',
    r'^## Troubleshooting',
    r'^## Edge Cases',
    r'^## Integration',
    r'^## Advanced',
    r'^## Reference',
]

def categorize_section(heading: str) -> str:
    """Return 'core', 'extended', or 'unknown'"""
    ...
```

### 3. Example Migration

Demonstrate with one agent (e.g., `build-validator`) showing before/after:

**Before** (single file):
```
build-validator.md (16KB)
├── Frontmatter
├── Overview
├── Quick Start (15 examples)
├── Boundaries
├── Detailed Examples (25 examples)
├── Best Practices
├── Anti-Patterns
└── Troubleshooting
```

**After** (split):
```
build-validator.md (6KB)
├── Frontmatter
├── Overview
├── Quick Start (5 examples)
├── Boundaries
├── Capabilities Summary
├── Phase Integration
└── Extended Reference (loading instruction)

build-validator-ext.md (12KB)
├── Header
├── Additional Quick Start (10 examples)
├── Detailed Examples (25 examples)
├── Best Practices
├── Anti-Patterns
└── Troubleshooting
```

## Acceptance Criteria

- [x] Content categorization rules documented (`docs/guides/content-migration-rules.md`)
- [x] Core vs extended section patterns defined (CORE_SECTION_PATTERNS, EXTENDED_SECTION_PATTERNS)
- [x] Migration script created/updated (`scripts/migrate-agent-content.py`)
- [x] Example migration demonstrated (build-validator: 16.1KB → 3.4KB core, 78.6% reduction)
- [ ] Rules reviewed and approved (checkpoint with TASK-REV-PD-CONTENT)

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-019 (infrastructure complete)
- TASK-REV-PD6 (specification review complete)

## Rollback Strategy

### Before Migration (per agent)

```bash
# 1. Create backup before any changes
cp installer/core/agents/{agent}.md installer/core/agents/{agent}.md.bak

# 2. Verify backup is readable
head -20 installer/core/agents/{agent}.md.bak
```

### If Issues Detected

```bash
# 1. Restore from backup
cp installer/core/agents/{agent}.md.bak installer/core/agents/{agent}.md

# 2. Verify restoration
wc -c installer/core/agents/{agent}.md  # Should match original size

# 3. Re-run migration with adjusted rules
```

### Backup Cleanup (after TASK-PD-024 validation)

```bash
# Only after all validations pass:
# 1. Verify all tests pass
./scripts/test-progressive-disclosure.sh

# 2. Verify token reduction target met
# 3. Remove backups
rm installer/core/agents/*.md.bak
```

**Important**: Backups MUST be retained until TASK-PD-024 validates all migrations.

## Section Decision Matrix

For sections not explicitly listed in core/extended categorization:

| Section Pattern | Decision | Rationale |
|-----------------|----------|-----------|
| Unknown section with <5 examples | Keep in core | Minimal impact on token usage |
| Unknown section with ≥5 examples | Move to extended | Significant content |
| Nested subsections | Follow parent | Maintain section coherence |
| `## Configuration` | Keep in core | Essential for agent setup |
| `## Security Considerations` | Keep in core | Critical safety information |
| `## Performance` | Move to extended | Optimization details |
| `## History`/`## Changelog` | Move to extended | Reference only |
| `## See Also`/`## References` | Keep in core | Navigation aids |

### Handling Mixed Content Sections

If a section contains both essential and detailed content:

1. **Split the section**: Keep summary in core, move details to extended
2. **Add cross-reference**: Core section ends with "See extended file for detailed examples"
3. **Example**:
   ```markdown
   ## Best Practices (Core - 3 essential)
   1. Rule one
   2. Rule two
   3. Rule three

   See `{agent}-ext.md` for 15+ additional best practices with code examples.
   ```

## Quick Start Selection Criteria

When reducing Quick Start from many examples to 5-10:

### Selection Priority (highest to lowest)

1. **Most common use case** - What users do 80% of the time
2. **Simplest working example** - Minimal code to demonstrate capability
3. **Boundary demonstration** - Shows ALWAYS/NEVER rules in action
4. **Error handling** - Common error and proper handling
5. **Integration example** - Working with other agents/tools

### Selection Process

```markdown
1. Count existing Quick Start examples
2. If ≤10: Keep all
3. If >10:
   a. Tag each example with priority (1-5 from above)
   b. Keep top 5-7 by priority
   c. Move remaining to extended file under "Additional Examples"
4. Ensure diversity (don't keep 5 similar examples)
```

### Example Selection

For `task-manager` with 25 Quick Start examples:
- Keep: Create task, work on task, complete task, status check, error handling (5)
- Move: Advanced filtering, bulk operations, integration examples, edge cases (20)
