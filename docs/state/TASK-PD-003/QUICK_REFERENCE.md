# TASK-PD-003 Quick Reference

## What This Task Does

Updates `enhancer.py` to support progressive disclosure by calling the new `apply_with_split()` method from TASK-PD-001, enabling creation of split agent files (core + extended).

```
Before (Single-File):
  agent.md (all content merged in one file)

After (Split-File - Progressive Disclosure):
  agent.md (core content with loading instruction)
  agent-ext.md (extended content: examples, best practices)
```

## Core Implementation

### 1. EnhancementResult Dataclass Changes
```python
@dataclass
class EnhancementResult:
    # Existing fields...
    success: bool
    agent_name: str
    sections: List[str]
    templates: List[str]
    examples: List[str]
    diff: str
    error: Optional[str]
    strategy_used: Optional[str]
    
    # NEW FIELDS:
    core_file: Optional[Path] = None          # Path to core file
    extended_file: Optional[Path] = None      # Path to extended file
    split_output: bool = False                # Whether split mode used
    
    # NEW PROPERTY:
    @property
    def files(self) -> List[Path]:
        """Return list of all created files"""
        return [f for f in [self.core_file, self.extended_file] if f]
```

### 2. enhance() Method Changes
```python
def enhance(
    self,
    agent_file: Path,
    template_dir: Path,
    split_output: bool = True      # NEW PARAMETER (default True)
) -> EnhancementResult:
    """
    - Load agent metadata
    - Discover templates
    - Generate enhancement
    - Validate enhancement
    
    NEW: Branch on split_output:
    ├─ split_output=True:  Call applier.apply_with_split()
    │                      Returns (core_path, ext_path)
    └─ split_output=False: Call applier.apply()
                           Returns single path (legacy)
    
    - Generate diff
    - Return EnhancementResult with all paths
    """
```

### 3. File Changes Summary
```
enhancer.py (4 changes):
  1. EnhancementResult dataclass: Add 3 fields + 1 property
  2. enhance() signature: Add split_output parameter
  3. enhance() docstring: Document new behavior
  4. enhance() body: Implement branching logic

agent-enhance.md (3 sections updated):
  1. Output Format: Examples for both modes
  2. Usage Examples: Split vs single-file
  3. Mode Selection: Document --split-output and --single-file
```

## Testing Strategy

### Unit Tests (New File: `test_enhancer_split_output.py`)
```
✓ test_enhancement_result_split_output
✓ test_enhancement_result_single_file_mode
✓ test_enhancement_result_with_error
✓ test_files_property_split
✓ test_files_property_single
✓ test_files_property_empty

Target: ≥90% line coverage, ≥85% branch coverage
```

### Integration Tests (New File: `test_enhancer_split_integration.py`)
```
✓ test_full_enhancement_with_split_output
✓ test_full_enhancement_with_single_file_mode
✓ test_dry_run_with_split_output
✓ test_loading_instruction_in_split_output
✓ test_extended_file_content

Target: ≥80% line coverage, ≥75% branch coverage
```

## Step-by-Step Implementation

```
Phase A: Preparation (10 min)
  └─ Step 1: Verify dependencies (TASK-PD-001, TASK-PD-002)

Phase B: Code Implementation (55 min)
  ├─ Step 2: Update EnhancementResult dataclass (15 min)
  ├─ Step 3: Update enhance() signature & docstring (10 min)
  └─ Step 4: Refactor enhance() implementation (30 min)

Phase C: Documentation (20 min)
  └─ Step 5: Update command documentation (20 min)

Phase D: Testing (1 hr 45 min)
  ├─ Step 6: Create unit tests (45 min)
  └─ Step 7: Create integration tests (1 hr)

Phase E: Validation (30 min)
  └─ Step 8: Run full test suite (30 min)

TOTAL: ~3.5 hours
```

## Key Decision Points

### Default Behavior: split_output=True
- Progressive disclosure is the new default
- Backward compatibility available via `split_output=False`
- Rationale: Better user experience, split files easier to navigate

### Backward Compatibility Strategy
- Make all new fields optional with defaults
- Keep existing methods unchanged
- Single-file mode available for legacy workflows
- No breaking changes to existing APIs

### Dependencies
- TASK-PD-001 must provide `apply_with_split()` method
- TASK-PD-002 must provide `generate_loading_instruction()` function
- Verify both exist before starting (via grep)

## Acceptance Criteria

```
✓ enhance() supports split_output parameter
✓ Default behavior is split_output=True
✓ EnhancementResult dataclass implemented with new fields
✓ Backward compatible mode available (split_output=False)
✓ Command output shows both files when split
✓ Unit tests for both modes (target: 6 tests)
✓ Integration test for full enhancement (target: 5 tests)
```

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| API change breaks existing code | Make fields optional, test backward compat |
| Dependencies missing | Verify before start, clear error messages |
| Performance overhead | Split = 2 writes, fallback available |
| File layout changes | Document migration, provide single-file mode |

## Files to Create

```
tests/unit/test_enhancer_split_output.py          (NEW)
tests/integration/test_enhancer_split_integration.py (NEW)
```

## Files to Modify

```
installer/global/lib/agent_enhancement/enhancer.py        (4 changes)
installer/global/commands/agent-enhance.md                (3 changes)
```

## Success Criteria

- All 7 acceptance criteria met
- Line coverage ≥80%, branch coverage ≥75%
- All tests passing
- Backward compatible
- Documentation updated
- Code reviewed and approved

## Next Steps After Completion

1. TASK-PD-004: Command integration
   - CLI flag parsing (--split-output, --single-file)
   - Command output handler updates

2. TASK-PD-005: Claude.md generator updates
   - Handle split files in documentation generation

3. TASK-PD-006+: Deploy progressive disclosure
   - Apply to all agent files across templates

## Documentation Reference

- Main Plan: `implementation_plan.md` (comprehensive, 10 sections)
- Summary: `SUMMARY.md` (executive overview)
- This File: `QUICK_REFERENCE.md` (quick lookup)

---

**Current Date**: 2025-12-05
**Status**: READY FOR IMPLEMENTATION
**Dependencies**: TASK-PD-001, TASK-PD-002 (must be complete)
