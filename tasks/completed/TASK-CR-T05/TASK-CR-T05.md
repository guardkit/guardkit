---
id: TASK-CR-T05
title: Add template validation for paths frontmatter
status: completed
created: 2026-02-06T01:15:00+00:00
updated: 2026-02-06T12:00:00+00:00
priority: high
tags:
- context-optimization
- validation
- templates
- quality-gate
parent_review: TASK-REV-CROPT
feature_id: FEAT-CR01
implementation_mode: direct
wave: 3
complexity: 3
task_type: tooling
depends_on: []
conductor_workspace: context-reduction-wave3-2
---

# Task: Add Template Validation for paths: Frontmatter

## Background

Progressive disclosure relies on `paths:` frontmatter in rules files to enable conditional loading. During the review, some files were found missing this frontmatter, which means they load unconditionally.

**Goal:** Add validation to `/template-validate` to catch missing `paths:` frontmatter and prevent regressions.

## Description

Enhance the `/template-validate` command to:
1. Check all `.claude/rules/*.md` files for `paths:` frontmatter
2. Warn when frontmatter is missing (file loads unconditionally)
3. Suggest appropriate path patterns based on file name/content
4. Add to validation report

## Acceptance Criteria

- [x] `/template-validate` checks for `paths:` in all rules files
- [x] Warning generated for files missing `paths:` frontmatter
- [x] Suggestion provided for appropriate path pattern
- [x] Validation report includes "Path-Gating Coverage" metric
- [x] Existing templates updated to fix any gaps found
- [x] Documentation updated with path-gating requirement

## Implementation Approach

### Step 1: Add Validation Check

In template validation logic, add check:
```python
def validate_rules_path_gating(template_path: Path) -> List[ValidationWarning]:
    """Check that rules files have paths: frontmatter."""
    warnings = []
    rules_dir = template_path / ".claude" / "rules"

    if not rules_dir.exists():
        return warnings

    for rules_file in rules_dir.rglob("*.md"):
        content = rules_file.read_text()
        if not has_paths_frontmatter(content):
            warnings.append(ValidationWarning(
                file=str(rules_file),
                message="Missing paths: frontmatter - file loads unconditionally",
                suggestion=suggest_paths(rules_file.name)
            ))

    return warnings
```

### Step 2: Path Suggestion Logic

Based on common patterns:
```python
def suggest_paths(filename: str) -> str:
    """Suggest paths: frontmatter based on filename."""
    suggestions = {
        "code-style.md": "**/*.py, **/*.ts",
        "testing.md": "tests/**/*.py, **/*.test.ts",
        "database.md": "**/db/**/*.py, **/models.py",
        "api.md": "**/api/**/*.py, **/routes/**/*",
        # Add more patterns
    }
    return suggestions.get(filename, "**/*  # TODO: specify appropriate paths")
```

### Step 3: Update Validation Report

Add section to validation output:
```
Path-Gating Coverage
====================
Files with paths: frontmatter: 12/15 (80%)

Missing paths: frontmatter:
  - .claude/rules/guidance/general.md
    Suggestion: paths: **/*
  - .claude/rules/patterns/utils.md
    Suggestion: paths: **/utils/**/*.py
```

### Step 4: Fix Existing Gaps

Run validation on all templates and fix any gaps found.

### Step 5: Update Documentation

Add to template documentation:
> **Required:** All files in `.claude/rules/` must have `paths:` frontmatter for conditional loading. Files without this frontmatter load in every conversation.

## Token Savings

This task doesn't directly save tokens but **prevents regressions** that would increase token usage.

**Preventive value:**
- Each ungated rules file: ~200-500 tokens loaded unnecessarily
- Potential prevention: ~1,000-2,000 tokens per template

## Files to Modify

- Template validation command/script
- Documentation: `.claude/rules/guidance/agent-development.md` or similar
- Potentially fix existing template rules files

## Testing

1. Create test rules file without `paths:` frontmatter
2. Run `/template-validate`
3. Verify warning is generated
4. Add `paths:` frontmatter
5. Verify warning clears

## Related Tasks

- **Same Wave:** Wave 3 (runs parallel to TASK-CR-T01)
- **Guards:** All subsequent template tasks
