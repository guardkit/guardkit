---
id: TASK-FDB2
title: Add --name flag to /template-create command
status: in_progress
created: 2025-11-12T21:25:24.930438+00:00
updated: 2025-11-12T21:33:45.000000+00:00
priority: high
tags: ["template-create", "cli", "enhancement"]
complexity: 3
estimated_time: "1-2 hours"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-TASK-FDB2: Add --name flag to /template-create command

## Problem Statement

Currently, `/template-create` auto-generates template names via AI analysis during Phase 1. There's no way to override this AI-generated name with a custom name, which is inconvenient when users want specific naming conventions.

Additionally, there are references to `/template-qa` command in the documentation that should be removed to avoid confusion.

## Requirements

1. **Add `--name` flag to `/template-create` command**
   - Allows users to specify a custom template name
   - Overrides AI-generated name if provided
   - Optional parameter (AI generation remains default behavior)

2. **Remove `/template-qa` references**
   - Clean up documentation references to `/template-qa` command
   - Ensure no broken workflow suggestions

## Acceptance Criteria

### Functional Requirements

1. **Flag Implementation** ✅
   - Add `--name` parameter to command-line parsing
   - Override AI-generated `template_name` if flag is provided
   - Maintain backward compatibility (no flag = AI generation)

2. **Validation** ✅
   - Template name must match pattern: `^[a-z0-9-]+$` (lowercase, numbers, hyphens only)
   - Name must be 3-50 characters
   - Clear error message if invalid name provided

3. **Usage Examples** ✅
   ```bash
   # With custom name
   /template-create --name my-custom-template --validate
   
   # Without name (AI generates)
   /template-create --validate
   
   # With name and other flags
   /template-create --name my-api-template --output-location repo
   ```

4. **Documentation Updates** ✅
   - Update `installer/global/commands/template-create.md` with `--name` flag
   - Remove all references to `/template-qa` command
   - Add usage examples with `--name` flag

### Technical Requirements

5. **Minimal Changes** ✅
   - Changes should be isolated to:
     - Command-line argument parsing
     - Template name override logic in orchestrator
     - Documentation updates
   - DO NOT modify Phase 1 AI analysis logic
   - DO NOT modify manifest generation logic beyond name override
   - DO NOT add complex validation beyond pattern matching

6. **No Breaking Changes** ✅
   - Existing behavior preserved when flag not used
   - AI-generated names still work as before
   - All existing tests pass without modification

7. **Error Handling** ✅
   - Invalid name format → Clear error message + example
   - Duplicate name → Warning message (allow overwrite)
   - Empty name → Use AI generation (don't error)

### Quality Gates

8. **Testing** ✅
   - Unit test: Flag parsing
   - Unit test: Name validation (valid/invalid patterns)
   - Unit test: Name override in orchestrator
   - Integration test: End-to-end with custom name

9. **Code Review** ✅
   - Changes isolated to 2-3 files maximum
   - No complex refactoring introduced
   - Clear comments explaining override logic

10. **Documentation** ✅
    - Updated command documentation with examples
    - Removed all `/template-qa` references
    - Clear explanation of when to use custom names vs AI generation

## Implementation Approach

### Step 1: Add Command-Line Flag (15 minutes)

**File**: `installer/global/commands/template-create.md`

Add to flags section:
```markdown
--name NAME              Custom template name (overrides AI-generated name)
                         Pattern: lowercase, numbers, hyphens only
                         Length: 3-50 characters
                         Example: my-api-template, react-admin, dotnet-api
                         Default: AI-generated from codebase analysis
```

### Step 2: Implement Name Validation (20 minutes)

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

Add validation function:
```python
def _validate_template_name(self, name: str) -> tuple[bool, str]:
    """Validate custom template name.
    
    Returns:
        (is_valid, error_message)
    """
    import re
    
    if not name:
        return True, ""  # Empty is valid (use AI generation)
    
    if len(name) < 3 or len(name) > 50:
        return False, "Template name must be 3-50 characters"
    
    if not re.match(r'^[a-z0-9-]+$', name):
        return False, "Template name must contain only lowercase letters, numbers, and hyphens"
    
    return True, ""
```

### Step 3: Override AI-Generated Name (25 minutes)

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

Add to `OrchestrationConfig`:
```python
@dataclass
class OrchestrationConfig:
    # ... existing fields ...
    custom_name: Optional[str] = None  # User-provided template name
```

Modify Phase 2 manifest generation:
```python
def _execute_phase_2_manifest_generation(self):
    # ... existing code ...
    
    # Override AI-generated name if custom name provided
    if self.config.custom_name:
        is_valid, error_msg = self._validate_template_name(self.config.custom_name)
        if not is_valid:
            raise ValueError(f"Invalid template name: {error_msg}")
        
        self.manifest.name = self.config.custom_name
        self._print_info(f"Using custom template name: {self.config.custom_name}")
    else:
        self._print_info(f"Using AI-generated name: {self.manifest.name}")
```

### Step 4: Remove /template-qa References (10 minutes)

**Files to update**:
- `installer/global/commands/template-create.md` (line 18)
- Any other documentation mentioning `/template-qa`

Search and replace:
```bash
grep -r "template-qa" installer/global/commands/
grep -r "template_qa" installer/global/commands/
```

Remove or rephrase references to the command.

### Step 5: Testing (30 minutes)

**Unit Tests**:
```python
def test_validate_template_name_valid():
    orchestrator = TemplateCreateOrchestrator(...)
    assert orchestrator._validate_template_name("my-template")[0] is True
    assert orchestrator._validate_template_name("api-123")[0] is True

def test_validate_template_name_invalid():
    orchestrator = TemplateCreateOrchestrator(...)
    assert orchestrator._validate_template_name("MyTemplate")[0] is False
    assert orchestrator._validate_template_name("my_template")[0] is False
    assert orchestrator._validate_template_name("ab")[0] is False

def test_custom_name_override():
    config = OrchestrationConfig(
        codebase_path=Path("."),
        custom_name="my-custom-name"
    )
    orchestrator = TemplateCreateOrchestrator(config)
    orchestrator.run()
    
    assert orchestrator.manifest.name == "my-custom-name"
```

**Integration Test**:
```bash
# Test with custom name
/template-create --name test-template --dry-run

# Expected: Template name is "test-template" (not AI-generated)
```

## File Changes Summary

**Files to Modify** (3 files):
1. `installer/global/commands/template-create.md` - Add flag documentation, remove `/template-qa` references
2. `installer/global/commands/lib/template_create_orchestrator.py` - Add name validation and override logic
3. `tests/unit/test_template_create_orchestrator.py` - Add unit tests for validation and override

**Lines of Code Estimate**: ~80 LOC
- Validation function: ~20 LOC
- Override logic: ~15 LOC
- Documentation: ~25 LOC
- Tests: ~20 LOC

## Success Metrics

### Before Implementation
- ❌ No way to specify custom template name
- ❌ References to `/template-qa` command cause confusion
- ❌ Users must accept AI-generated names

### After Implementation
- ✅ Users can override template name with `--name` flag
- ✅ No broken references to `/template-qa`
- ✅ Clear validation and error messages for invalid names
- ✅ Backward compatible (AI generation still works)
- ✅ Minimal code changes (3 files, ~80 LOC)

## Architecture Compliance

- ✅ **Minimal Changes**: Isolated to command parsing and name override
- ✅ **No Breaking Changes**: Existing behavior preserved
- ✅ **Single Responsibility**: Name validation separate from AI generation
- ✅ **Clear Separation**: Override logic doesn't touch Phase 1 analysis
- ✅ **Fail Fast**: Validate name before orchestration starts

## Related Tasks

- **TASK-0CE5**: Fix empty example_files in AI Analysis (completed) - Related to template generation
- **TASK-51B2**: AI-native codebase analysis (completed) - Generates template names

## Notes

### Design Decisions

1. **Why `--name` instead of `--template-name`?**
   - Shorter and more intuitive
   - Consistent with other CLI tools (Docker, NPM)

2. **Why lowercase-only pattern?**
   - Consistent with NPM package naming
   - Avoids case-sensitivity issues on different filesystems
   - Standard convention for template/package names

3. **Why not validate against existing templates?**
   - Allow overwriting templates (user intent)
   - Duplicate detection adds complexity
   - Users can manually check with `taskwright init --list`

### Testing Strategy

Focus on:
- ✅ Valid name patterns (lowercase, numbers, hyphens)
- ✅ Invalid name patterns (uppercase, underscores, special chars)
- ✅ Edge cases (empty, too short, too long)
- ✅ Override integration (AI-generated vs custom)

### Risk Mitigation

**Low Risk** because:
- Changes are isolated to 3 files
- Backward compatible (flag is optional)
- Simple validation logic (regex pattern)
- No changes to core AI analysis or template generation

**If issues occur**:
- Rollback is easy (remove flag, revert 3 files)
- Existing functionality unaffected
- Tests catch validation bugs early

## Implementation Time Estimate

- Validation function: 20 minutes
- Override logic: 25 minutes
- Documentation updates: 15 minutes
- Testing: 30 minutes
- Code review: 10 minutes

**Total**: 1.5 hours
