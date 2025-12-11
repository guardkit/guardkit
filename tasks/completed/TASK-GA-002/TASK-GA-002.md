---
id: TASK-GA-002
title: Add size validation for guidance files
status: completed
task_type: implementation
created: 2025-12-11T20:00:00Z
updated: 2025-12-11T22:30:00Z
completed: 2025-12-11T22:30:00Z
priority: medium
tags: [validation, rules-structure, guidance, template-validation]
complexity: 3
parent: TASK-REV-ARCH
related_to: [TASK-GA-001]
implementation_mode: task-work
conductor_workspace: guidance-architecture-wave1-2
wave: 1
completed_location: tasks/completed/TASK-GA-002/
organized_files:
  - TASK-GA-002.md
  - completion-report.md
---

# Task: Add Size Validation for Guidance Files

## Background

To prevent accidental full duplication in guidance files, add validation that flags guidance files exceeding 5KB. This acts as a safety net to ensure the progressive disclosure pattern is maintained.

## Acceptance Criteria

- [ ] Validation runs during Phase 7 of `/template-create`
- [ ] Guidance files >5KB trigger a warning (not error)
- [ ] Warning message includes file name, size, and suggestion
- [ ] Validation is non-blocking (template creation continues)
- [ ] Unit tests verify validation behavior

## Implementation Details

### File to Modify

`installer/core/lib/template_generator/rules_structure_generator.py` or a separate validation module.

### Proposed Implementation

```python
MAX_GUIDANCE_SIZE = 5 * 1024  # 5KB

def validate_guidance_sizes(self, rules_dir: Path) -> List[ValidationIssue]:
    """
    Validate guidance files stay under size threshold.

    This ensures progressive disclosure benefits are maintained
    by keeping guidance files slim (path-triggered hints only).

    Args:
        rules_dir: Path to .claude/rules/ directory

    Returns:
        List of validation issues (warnings for oversized files)
    """
    issues = []

    guidance_dir = rules_dir / "guidance"
    if not guidance_dir.exists():
        return issues

    for file in guidance_dir.glob("*.md"):
        size = file.stat().st_size
        if size > MAX_GUIDANCE_SIZE:
            issues.append(ValidationIssue(
                level="warning",
                file=str(file),
                message=f"Guidance file {file.name} exceeds 5KB ({size:,} bytes)",
                suggestion=(
                    "Guidance files should be slim summaries (<3KB). "
                    "Move detailed content to agents/{name}.md or agents/{name}-ext.md"
                )
            ))

    return issues
```

### Integration Point

Add call during Phase 7 validation in `/template-create` workflow:

```python
# Phase 7: Validation
validation_issues = []
validation_issues.extend(self._validate_manifest())
validation_issues.extend(self._validate_guidance_sizes())  # NEW
validation_issues.extend(self._validate_agent_files())
```

### Output Format

```
⚠️  Warning: Guidance file docker.md exceeds 5KB (4,196 bytes)
   Suggestion: Guidance files should be slim summaries (<3KB).
               Move detailed content to agents/{name}.md or agents/{name}-ext.md
```

## Testing

### Unit Tests

```python
def test_validate_guidance_sizes_pass():
    """Small guidance files should pass validation."""
    # Create temp dir with small guidance file
    guidance_file = tmp_path / ".claude/rules/guidance/test.md"
    guidance_file.write_text("Small content")

    issues = validate_guidance_sizes(tmp_path / ".claude/rules")
    assert len(issues) == 0

def test_validate_guidance_sizes_warning():
    """Large guidance files should trigger warning."""
    guidance_file = tmp_path / ".claude/rules/guidance/large.md"
    guidance_file.write_text("x" * 6000)  # 6KB

    issues = validate_guidance_sizes(tmp_path / ".claude/rules")
    assert len(issues) == 1
    assert issues[0].level == "warning"
    assert "exceeds 5KB" in issues[0].message

def test_validate_guidance_no_dir():
    """Missing guidance directory should not error."""
    issues = validate_guidance_sizes(tmp_path / ".claude/rules")
    assert len(issues) == 0
```

## Notes

- Validation is warning-only, not blocking
- 5KB threshold allows some buffer above the 3KB target
- This catches accidental full-copy scenarios from generator bugs
