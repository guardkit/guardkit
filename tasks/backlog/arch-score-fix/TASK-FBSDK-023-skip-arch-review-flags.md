---
id: TASK-FBSDK-023
title: Add skip_arch_review CLI and frontmatter flags
status: backlog
created: 2025-01-21T16:30:00Z
updated: 2025-01-21T16:30:00Z
priority: medium
tags: [autobuild, cli, override, quality-gates]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 3
conductor_workspace: arch-score-fix-wave3-1
complexity: 3
depends_on: [TASK-FBSDK-021]
---

# Task: Add skip_arch_review CLI and frontmatter flags

## Description

Add explicit override mechanisms for skipping architectural review. This allows users to manually control quality gates when auto-detection or task type profiles don't match their needs.

## Acceptance Criteria

- [ ] CLI flag `--skip-arch-review` added to `guardkit autobuild task`
- [ ] Frontmatter field `skip_arch_review: true` supported
- [ ] CLI flag takes precedence over frontmatter
- [ ] Warning message when skipping architectural review
- [ ] Flag documented in help text and command docs
- [ ] Unit tests verify flag behavior
- [ ] Integration test with override

## Implementation Notes

### CLI Flag

`guardkit/cli/autobuild.py`:

```python
@click.option(
    "--skip-arch-review",
    is_flag=True,
    default=False,
    help="Skip architectural review quality gate (use with caution)"
)
def task(
    task_id: str,
    max_turns: int,
    mode: str,
    skip_arch_review: bool,
    ...
):
    """Execute AutoBuild for a single task."""
    if skip_arch_review:
        click.echo("⚠️  Warning: Architectural review will be skipped")

    orchestrator = AutoBuildOrchestrator(
        ...,
        skip_arch_review=skip_arch_review,
    )
```

### Frontmatter Field

```yaml
---
id: TASK-XXX
title: Legacy migration script
autobuild:
  enabled: true
  skip_arch_review: true  # NEW FIELD
---
```

### Override Cascade

Priority (highest to lowest):
1. CLI flag `--skip-arch-review`
2. Frontmatter `autobuild.skip_arch_review`
3. Task type profile (from TASK-FBSDK-021)
4. Default (architectural review required)

### Files to Modify

1. `guardkit/cli/autobuild.py`
   - Add `--skip-arch-review` option
   - Pass to orchestrator

2. `guardkit/orchestrator/autobuild.py`
   - Accept `skip_arch_review` parameter
   - Pass to CoachValidator

3. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - Accept override in `validate()` method
   - Apply override before profile check

4. Documentation
   - `installer/core/commands/autobuild.md`
   - `.claude/rules/autobuild.md`

### Warning Output

When skip flag is used:
```
⚠️  Warning: Architectural review will be skipped
   This bypasses SOLID/DRY/YAGNI validation.
   Use only for legacy code or special circumstances.
```

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/orchestrator/autobuild.py`
- `installer/core/commands/autobuild.md`

## Notes

This is a safety valve for edge cases where task type profiles don't fit. The warning message ensures users are aware they're bypassing quality gates.
