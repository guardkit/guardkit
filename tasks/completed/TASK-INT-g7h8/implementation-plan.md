# Implementation Plan: TASK-INT-g7h8

## Task: Update task-work command to use intensity system

**Complexity**: 3/10 (Simple integration)
**Estimated Duration**: 2.5 hours
**Documentation Level**: minimal (2 files max)

---

## Files to Modify

### 1. `/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/task-work.md`

**Changes Required**:

1. **Add Phase 0: Intensity Resolution** (before Phase 1)
   - Read task frontmatter: `parent_review`, `feature_id`, `complexity`
   - Call auto-detection logic (from TASK-INT-e5f6)
   - Override with `--intensity` flag if provided
   - Display intensity banner with reason

2. **Update Micro-Task Mode section** (~line 402)
   - Change description: "`--micro` is now an alias for `--intensity=minimal`"
   - Reference intensity system
   - Remove standalone micro-task criteria (now in intensity system)
   - Keep backward compatibility notes

3. **Add Intensity-Based Phase Configuration**
   - Insert new section after "Intensity Levels" (~line 350)
   - Document phase selection logic per intensity level
   - Map each phase to intensity requirements

4. **Update Phase Execution Logic** (throughout phases)
   - Add conditional checks: "IF intensity >= LIGHT: execute, ELSE: skip"
   - Update phase headers with intensity requirements
   - Maintain backward compatibility

**Line Count Estimate**: +150 lines (mostly documentation)

---

## Implementation Structure

### Phase 0: Intensity Resolution

```markdown
## Phase 0: Resolve Intensity (NEW - TASK-INT-g7h8)

**When**: Before Phase 1 (task context loading)
**Duration**: <5 seconds

### Read Provenance Fields

```yaml
parent_review: {task.parent_review or "none"}
feature_id: {task.feature_id or "none"}
complexity: {task.complexity}
```

### Resolve Intensity

1. **IF** `--intensity` flag provided:
   - Use flag value
   - Display: "Intensity: {level} (user-specified)"

2. **ELSE** auto-detect:
   - Call `determine_intensity(task)` (TASK-INT-e5f6 logic)
   - Display: "Intensity: {level} (auto-detected)"
   - Show reason: "Task has parent_review: {id}" or "Fresh task, complexity {score}"

### Display Banner

```
═══════════════════════════════════════════════════════
INTENSITY: {LEVEL}
═══════════════════════════════════════════════════════
Detection: {auto-detected | user-specified}
Reason: {reason_text}
Phases: {active_phase_list}
Quality gates: {gate_requirements}
Duration estimate: {estimated_minutes} minutes
═══════════════════════════════════════════════════════

Use --intensity=<level> to override.
```

### Store Resolved Intensity

Store in execution context for phase checks.
```

---

### Intensity-Based Phase Selection

```markdown
## Intensity-Based Phase Selection (NEW - TASK-INT-g7h8)

Each phase checks resolved intensity before executing.

### Minimal Intensity

**Phases Executed**:
- Phase 1: Load Task Context
- Phase 3: Implementation (simplified)
- Phase 4: Quick Testing (compilation + tests, no coverage)
- Phase 4.5: Fix Loop (1 attempt)
- Phase 5: Quick Review (lint only)

**Phases Skipped**:
- Phase 2, 2.5A, 2.5B, 2.7, 2.8, 5.5

### Light Intensity

**Phases Executed**:
- Phase 1: Load Task Context
- Phase 2: Implementation Planning (brief, 200 tokens max)
- Phase 2.8: Human Checkpoint (10s timeout, auto-proceed)
- Phase 3: Implementation
- Phase 4: Testing (70% coverage required)
- Phase 4.5: Fix Loop (2 attempts)
- Phase 5: Code Review (quick SOLID check)
- Phase 5.5: Plan Audit (50% thresholds)

**Phases Skipped**:
- Phase 2.5A, 2.5B (unless pattern need detected)
- Phase 2.7

### Standard Intensity (Default)

**Phases Executed**: All phases

**Conditional**:
- Phase 2.5A: Only if pattern need detected
- Phase 2.7: Always executed
- Phase 2.8: Checkpoint if complexity ≥7

### Strict Intensity

**Phases Executed**: All phases with enhanced validation

**Enhanced**:
- Phase 2.5B: Mandatory architectural review
- Phase 2.8: Blocking checkpoint (no timeout)
- Phase 4: 85% coverage required
- Phase 5: Full SOLID/DRY/YAGNI review
- Phase 5.5: Strict plan audit (±10% variance)
```

---

### Update Micro-Task Mode Section

**Current** (~line 402):
```markdown
## Micro-Task Mode (NEW - TASK-020)

The task-work command now supports a `--micro` flag for streamlined execution...

**Criteria for micro-tasks** (ALL must be true) - TASK-TWP-c3d4 updated thresholds:
- Complexity: ≤3/10 (was 1/10 - simple tasks now qualify)
- Files: ≤3 file modifications (was single file)
...
```

**Replace With**:
```markdown
## Micro-Task Mode (Legacy Alias)

The `--micro` flag is now an alias for `--intensity=minimal` (introduced in TASK-INT-g7h8).

**Usage**:
```bash
/task-work TASK-047 --micro
# Equivalent to:
/task-work TASK-047 --intensity=minimal
```

**Behavior**:
- Sets intensity to MINIMAL
- Executes minimal phase set (see "Intensity-Based Phase Selection")
- Same quality gates as minimal intensity
- Backward compatible with existing workflows

**Note**: All micro-task criteria are now handled by the intensity auto-detection system. Tasks with complexity ≤3 and no high-risk keywords auto-detect to minimal intensity.

**See**: "Intensity System" and "Phase 0: Resolve Intensity" for complete details.
```

---

## Validation Points

### 1. Provenance Detection
- Task with `parent_review: TASK-REV-a3f8` → auto-detects minimal/light
- Task with `feature_id: FEAT-a3f8` → auto-detects light/standard
- Fresh task → complexity-based detection

### 2. Flag Override
- `--intensity=strict` overrides auto-detection
- Display shows "user-specified" instead of "auto-detected"

### 3. Backward Compatibility
- `--micro` still works (alias for `--intensity=minimal`)
- Existing tasks without provenance fields → fallback to complexity detection
- No breaking changes to command syntax

### 4. Phase Execution
- Minimal intensity skips Phase 2, 2.5A, 2.5B, 2.7, 2.8, 5.5
- Standard intensity executes all phases
- Strict intensity adds blocking checkpoints

---

## Technical Notes

### Integration with TASK-INT-e5f6

This task integrates the auto-detection logic from TASK-INT-e5f6:

```python
# TASK-INT-e5f6 provides:
def determine_intensity(task: Task) -> Intensity:
    """Auto-detect intensity from provenance + complexity."""
    # Implementation in TASK-INT-e5f6
    pass

# TASK-INT-g7h8 uses:
def resolve_intensity(task: Task, flag_value: Optional[str]) -> Intensity:
    if flag_value:
        return Intensity[flag_value.upper()]
    else:
        return determine_intensity(task)  # From TASK-INT-e5f6
```

### Phase Conditional Logic

Each phase section needs conditional check:

```markdown
## Phase 2: Implementation Planning

**IF** intensity >= LIGHT:
  Execute planning phase...
**ELSE**:
  Skip (minimal intensity)
```

### Micro Mode Compatibility

```python
# Command parsing
if "--micro" in flags:
    flags.remove("--micro")
    flags.append("--intensity=minimal")
```

---

## Testing Strategy

### Manual Testing Scenarios

1. **Reviewed Task (Minimal)**
   ```bash
   # Create task with parent_review
   /task-create "Fix typo" parent_review:TASK-REV-001 complexity:2
   /task-work TASK-XXX
   # Expected: Auto-detects minimal, skips Phase 2
   ```

2. **Feature Task (Light)**
   ```bash
   # Create task with feature_id
   /task-create "Add button" feature_id:FEAT-001 complexity:4
   /task-work TASK-XXX
   # Expected: Auto-detects light, brief Phase 2
   ```

3. **Fresh Complex Task (Standard)**
   ```bash
   # Create fresh task
   /task-create "Refactor auth" complexity:7
   /task-work TASK-XXX
   # Expected: Auto-detects standard, full phases
   ```

4. **Override Flag**
   ```bash
   /task-work TASK-XXX --intensity=strict
   # Expected: Uses strict regardless of auto-detection
   ```

5. **Micro Alias**
   ```bash
   /task-work TASK-XXX --micro
   # Expected: Same as --intensity=minimal
   ```

### Edge Cases

- Task without frontmatter → fallback to complexity
- Task with both `parent_review` and `feature_id` → `parent_review` takes precedence
- Invalid `--intensity` value → error message
- High-risk keywords → force strict (even if flagged minimal)

---

## Rollback Plan

If issues arise:

1. **Phase 0 issues**: Remove Phase 0, default to standard intensity
2. **Auto-detection issues**: Disable auto-detection, require `--intensity` flag
3. **Backward compatibility**: Keep `--micro` as standalone mode (revert to TASK-020 behavior)

All changes are additive and non-breaking.

---

## Dependencies

**Requires**:
- TASK-INT-a1b2: Frontmatter fields (`parent_review`, `feature_id`) documented
- TASK-INT-c3d4: `--intensity` flag parsing implemented
- TASK-INT-e5f6: Auto-detection logic (`determine_intensity()`) implemented

**Blocks**:
- TASK-INT-i9j0: Integration tests (needs this implementation)

---

## Success Criteria

- [ ] Phase 0 resolves intensity before Phase 1
- [ ] Auto-detection reads provenance fields from frontmatter
- [ ] `--intensity` flag overrides auto-detection
- [ ] Intensity banner displays detection reason
- [ ] Phase execution respects intensity level
- [ ] `--micro` works as alias for `--intensity=minimal`
- [ ] Backward compatible with tasks without provenance fields
- [ ] Duration: <2.5 hours (simple integration)
- [ ] Files modified: 1 (task-work.md)

---

## Implementation Checklist

- [ ] Add Phase 0: Intensity Resolution section
- [ ] Add Intensity-Based Phase Selection section
- [ ] Update Micro-Task Mode section (convert to alias)
- [ ] Add conditional checks to Phase 2, 2.5A, 2.5B, 2.7, 2.8, 5.5
- [ ] Update command syntax documentation
- [ ] Add examples for each intensity level
- [ ] Add validation scenarios
- [ ] Update backward compatibility notes
- [ ] Test with provenance tasks
- [ ] Test with fresh tasks
- [ ] Test flag overrides
- [ ] Verify micro alias works

---

**Estimated Lines of Code**: +150 lines (documentation)
**Estimated Duration**: 2.5 hours
**Risk Level**: Low (additive changes only)
