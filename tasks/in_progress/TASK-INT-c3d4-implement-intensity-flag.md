---
id: TASK-INT-c3d4
title: Implement --intensity flag with 4 levels
status: in_progress
created: 2026-01-17T14:30:00Z
updated: 2026-01-17T18:45:23Z
priority: high
previous_state: backlog
state_transition_reason: Automatic transition for task-work execution
tags:
  - intensity-system
  - cli
  - task-work
complexity: 3
parent_review: TASK-REV-FB16
feature: provenance-intensity
wave: 1
implementation_mode: task-work
estimated_minutes: 150
conductor_workspace: provenance-int-wave1-2
dependencies: []
---

# Implement --intensity Flag with 4 Levels

## Description

Add a new `--intensity` flag to `/task-work` with four levels:

- `minimal` (alias: `--micro`) - Fastest, skip most phases
- `light` - Skip architectural review, brief planning
- `standard` - Full phases except MCP if not needed (current default)
- `strict` - All phases, blocking checkpoints

This replaces the binary `--micro` flag with a spectrum while maintaining backwards compatibility.

## Acceptance Criteria

- [ ] `--intensity=minimal|light|standard|strict` flag added to task-work
- [ ] `--micro` works as alias for `--intensity=minimal`
- [ ] Default behavior unchanged (standard intensity)
- [ ] Each intensity level has defined phase configuration
- [ ] Flag documentation added to task-work.md
- [ ] Help text shows all intensity options

## Technical Approach

### 1. Update task-work.md Available Flags

```markdown
| Flag | Description |
|------|-------------|
| `--intensity=LEVEL` | Control ceremony level (minimal, light, standard, strict) |
| `--micro` | Alias for --intensity=minimal |
```

### 2. Define Phase Configurations

```markdown
## Intensity Levels

### minimal (--micro alias)
- Phase 1: Load context ✓
- Phase 2: Planning ✗
- Phase 2.5A: Pattern MCP ✗
- Phase 2.5B: Arch review ✗
- Phase 2.7: Complexity ✗
- Phase 2.8: Checkpoint ✗
- Phase 3: Implementation ✓ (simplified)
- Phase 4: Testing ✓ (no coverage)
- Phase 4.5: Fix loop ✓ (1 attempt)
- Phase 5: Code review ✓ (lint only)
- Phase 5.5: Plan audit ✗

### light
- Phase 1: Load context ✓
- Phase 2: Planning ✓ (brief)
- Phase 2.5A: Pattern MCP ✗
- Phase 2.5B: Arch review ✗
- Phase 2.7: Complexity ✗
- Phase 2.8: Checkpoint ✓ (10s timeout)
- Phase 3: Implementation ✓
- Phase 4: Testing ✓
- Phase 4.5: Fix loop ✓ (2 attempts)
- Phase 5: Code review ✓ (quick)
- Phase 5.5: Plan audit ✓ (50% variance threshold)

### standard (default)
- All phases ✓
- Phase 2.5A: Only if pattern need detected
- Phase 2.8: 30s timeout
- Phase 4.5: 3 attempts
- Phase 5.5: 20% variance threshold

### strict
- All phases ✓
- Phase 2.5A: Always
- Phase 2.8: Blocking (no timeout)
- Phase 4.5: 5 attempts
- Phase 5: Full review + security scan
- Phase 5.5: 0% variance (any deviation flagged)
```

### 3. Flag Parsing Logic

```python
def parse_intensity(args) -> Intensity:
    if args.micro:
        return Intensity.MINIMAL
    if args.intensity:
        return Intensity[args.intensity.upper()]
    return Intensity.STANDARD  # Default
```

## Files to Modify

- `installer/core/commands/task-work.md` - Add flag docs and intensity level specs
- `.claude/rules/task-workflow.md` - Reference intensity levels

## Test Requirements

- [ ] --intensity=minimal skips Phase 2
- [ ] --intensity=light includes brief Phase 2, skips arch review
- [ ] --intensity=standard is current behavior
- [ ] --intensity=strict has blocking checkpoint
- [ ] --micro works as --intensity=minimal alias
- [ ] Invalid intensity value shows error message

## Notes

This task focuses on the flag and phase configuration documentation. The auto-detection logic is in TASK-INT-e5f6. Keep the flag implementation simple - it's a selector for predefined phase configurations.
