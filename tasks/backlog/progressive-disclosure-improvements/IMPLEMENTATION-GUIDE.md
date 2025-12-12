# Implementation Guide: Progressive Disclosure Improvements

## Overview

This guide provides the execution strategy for implementing improvements identified in TASK-REV-PD01.

## Wave Breakdown

### Wave 1: Quick Wins (Parallel)

**Tasks**: TASK-PDI-001, TASK-PDI-002
**Estimated Time**: 30 minutes each
**Mode**: Direct implementation (no /task-work needed)
**Parallel Execution**: Yes - independent changes

#### TASK-PDI-001: Add paths to guidance files
```bash
# Direct edit - update 9 guidance files in mydrive template
# Then update template-create to include paths in generated guidance files
```

#### TASK-PDI-002: Enhance xunit ASK section
```bash
# Direct edit - add 1-2 ASK items to xunit-nsubstitute-testing-specialist.md
```

### Wave 2: Pattern Enhancement

**Task**: TASK-PDI-003
**Estimated Time**: 2-4 hours
**Mode**: task-work (requires planning)
**Dependencies**: None (can run independently)

```bash
/task-work TASK-PDI-003
```

## Execution Commands

### Wave 1 (Parallel)
```bash
# Can be done in parallel with Conductor
# Workspace 1:
# Edit guidance files directly

# Workspace 2:
# Edit xunit specialist directly
```

### Wave 2
```bash
/task-work TASK-PDI-003
```

## Verification

After implementation:

1. Run `/template-create` on a test project
2. Verify guidance files have `paths:` frontmatter
3. Verify pattern files have examples
4. Run `guardkit init` and check output

## Success Criteria

- [ ] All 9 guidance files have paths
- [ ] xunit specialist has 4-5 ASK items
- [ ] 12 pattern files have real examples
- [ ] No regressions in template-create or guardkit init
