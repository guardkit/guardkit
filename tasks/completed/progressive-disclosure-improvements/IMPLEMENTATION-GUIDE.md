# Implementation Guide: Progressive Disclosure Improvements

## Overview

This guide provides the execution strategy for implementing technology-agnostic improvements to `/template-create` identified in TASK-REV-PD01.

**Scope**: Core command improvements only. Template-specific agent content will be regenerated when commands are re-run.

## Wave Breakdown

### Wave 1: Guidance File Paths

**Task**: TASK-PDI-001
**Estimated Time**: 30 minutes
**Mode**: Direct implementation
**Target**: Update template-create to generate guidance files with `paths:` frontmatter

```bash
# Update the guidance file generation logic in template-create
# to include path patterns based on agent specialty
```

### Wave 2: Pattern File Enrichment

**Task**: TASK-PDI-003
**Estimated Time**: 2-4 hours
**Mode**: task-work (requires planning)
**Target**: Update template-create to extract pattern examples from source codebase

```bash
/task-work TASK-PDI-003
```

## Execution Commands

### Wave 1
```bash
# Direct implementation - update template-create guidance generation
```

### Wave 2
```bash
/task-work TASK-PDI-003
```

## Verification

After implementation:

1. Run `/template-create` on a test project (e.g., mydrive codebase)
2. Verify guidance files have `paths:` frontmatter
3. Verify pattern files have extracted examples
4. Run `guardkit init` and check output structure

## Success Criteria

- [ ] Guidance files generated with appropriate `paths:` frontmatter
- [ ] Pattern files populated with codebase examples (not "No examples found")
- [ ] No regressions in template-create or guardkit init
- [ ] Re-running on mydrive produces improved output
