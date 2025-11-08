---
id: TASK-068
title: Refactor template creation location to support output location flag (Solution C)
status: backlog
created: 2025-01-08T10:00:00Z
updated: 2025-01-08T10:00:00Z
priority: medium
tags: [template-creation, installation, workflow, refactoring, ux-improvement]
complexity: 0
related_tasks: [TASK-021]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-068: Refactor Template Creation Location to Support Output Location Flag

## Description

Implement **Solution C: Hybrid with Flag** from TASK-021 investigation. This refactors the `/template-create` command to default to the global location (`~/.agentecflow/templates/`) for immediate use while supporting an optional `--output-location` flag to write templates to the repository location for team/public distribution.

**Background**: Currently, `/template-create` always writes templates to the repository location (`installer/global/templates/`), requiring users to run `install.sh` before templates become available. This creates friction for solo developers creating personal templates while working well for team/public distribution.

**Related Investigation**: [TASK-021](tasks/backlog/TASK-021-evaluate-template-creation-location-strategy.md)

## Acceptance Criteria

### Core Functionality
- [ ] **AC1**: Default behavior writes templates to `~/.agentecflow/templates/` (global location)
- [ ] **AC2**: `--output-location=repo` flag writes templates to `installer/global/templates/` (repository location)
- [ ] **AC3**: Short form `-o repo` works as alias for `--output-location=repo`
- [ ] **AC4**: `--output-location=global` explicitly specifies global location (same as default)
- [ ] **AC5**: Templates created in global location are immediately usable without running `install.sh`

### User Feedback
- [ ] **AC6**: Command outputs clear message indicating where template was created
- [ ] **AC7**: Output distinguishes between "personal use" (global) and "distribution" (repo) templates
- [ ] **AC8**: Help text documents both output locations and when to use each

### Validation & Error Handling
- [ ] **AC9**: Invalid `--output-location` values display helpful error message
- [ ] **AC10**: Directory creation handles permissions issues gracefully
- [ ] **AC11**: Existing template detection works for both locations
- [ ] **AC12**: Overwrite confirmation required if template already exists in target location

### Documentation
- [ ] **AC13**: CLAUDE.md updated to reflect new default behavior
- [ ] **AC14**: `/template-create` command documentation updated with flag details
- [ ] **AC15**: Usage examples provided for both personal and team distribution workflows

### Testing
- [ ] **AC16**: Test personal workflow: Create template → immediate use without `install.sh`
- [ ] **AC17**: Test team workflow: Create template with `-o repo` → verify in repo → `install.sh` → use
- [ ] **AC18**: Test iteration workflow: Create → test → recreate with `--overwrite` → test again
- [ ] **AC19**: Test both short (`-o`) and long (`--output-location`) flag forms

## Implementation Plan

### Phase 1: Command Flag Support
1. Add `--output-location` parameter to `/template-create` command
2. Add `-o` short form alias
3. Validate parameter values (global/repo)
4. Default to `global` if flag not provided

### Phase 2: Directory Logic
1. Refactor target directory selection:
   ```bash
   if [[ "$OUTPUT_LOCATION" == "repo" ]]; then
       TEMPLATE_DIR="installer/global/templates/$TEMPLATE_NAME"
       LOCATION_TYPE="distribution"
   else
       TEMPLATE_DIR="$HOME/.agentecflow/templates/$TEMPLATE_NAME"
       LOCATION_TYPE="personal"
   fi
   ```
2. Ensure directory creation with proper permissions
3. Handle directory existence and overwrite scenarios

### Phase 3: User Feedback
1. Update output messages:
   ```
   ✅ Template created successfully

   📁 Location: ~/.agentecflow/templates/my-template/
   🎯 Type: Personal use (immediately available)

   📝 Next Steps:
      taskwright init my-template
   ```
   vs.
   ```
   ✅ Template created successfully

   📁 Location: installer/global/templates/my-template/
   📦 Type: Distribution (requires installation)

   📝 Next Steps:
      git add installer/global/templates/my-template/
      git commit -m "Add my-template"
      ./installer/scripts/install.sh
   ```

### Phase 4: Documentation Updates
1. Update `installer/global/commands/template-create.md`:
   - Add flag documentation
   - Add usage examples for both modes
   - Clarify when to use each mode
2. Update `CLAUDE.md`:
   - Reflect new default behavior
   - Update workflow examples
   - Clarify installation flow
3. Update `docs/guides/` (if applicable)

### Phase 5: Testing
1. Test default behavior (global location)
2. Test repo flag (`-o repo`)
3. Test immediate usage after global creation
4. Test `install.sh` still works for repo templates
5. Test overwrite scenarios for both locations

## Test Requirements

### Unit Tests
- [ ] Flag parsing tests (long and short forms)
- [ ] Directory selection logic tests
- [ ] Path validation tests

### Integration Tests
- [ ] End-to-end personal workflow test
- [ ] End-to-end team distribution workflow test
- [ ] Template creation + immediate usage test
- [ ] Template creation + install.sh + usage test

### Scenario Tests
```bash
# Scenario 1: Solo Developer (Personal Template)
/template-create  # Default to global
taskwright init my-template  # Should work immediately
# ✅ Expected: Template available without install.sh

# Scenario 2: Team Lead (Distribution Template)
/template-create -o repo  # Write to repo
git add installer/global/templates/my-team-template/
git commit -m "Add team template"
./installer/scripts/install.sh
taskwright init my-team-template
# ✅ Expected: Template in version control, team can install

# Scenario 3: Template Iteration
/template-create  # Version 1 in global
taskwright init test-template  # Test immediately
/template-create --overwrite  # Version 2 in global
taskwright init test-template  # Test immediately
# ✅ Expected: Fast iteration without install.sh
```

## Implementation Notes

### Benefits of Solution C
1. **Better UX for Solo Developers**: Templates immediately available (80% use case)
2. **Maintains Team Distribution**: Explicit flag for version-controlled templates
3. **Clear Intent**: Flag makes distribution intent explicit
4. **Flexibility**: Supports both personal and team workflows

### Migration Considerations
- Existing templates in `installer/global/templates/` remain valid
- `install.sh` continues to work for repo-based templates
- No breaking changes to existing workflows
- New default is opt-in (existing scripts with explicit paths unchanged)

### Files to Modify
```
installer/global/commands/
└── template-create.md ← Add --output-location flag

CLAUDE.md ← Update default behavior documentation

docs/guides/
└── (if template creation guide exists)
```

### Success Metrics
- Solo developers can create and use templates in 1 step (vs. 2 steps currently)
- Team distribution workflow remains clear and explicit
- Zero confusion about where templates are created (clear output messages)

## Related Documentation

- **Investigation Task**: [TASK-021](tasks/backlog/TASK-021-evaluate-template-creation-location-strategy.md) - Complete analysis and solution comparison
- **Solution Details**: Solution C (lines 293-316 in TASK-021)
- **Command Spec**: `installer/global/commands/template-create.md`
- **Installation Script**: `installer/scripts/install.sh`

## Questions to Resolve

1. Should we add a config option to set default output location per user?
2. Should we detect if running in taskwright repo and auto-select repo location?
3. Should we add `--force` flag to skip overwrite confirmation?

---

**Estimated Complexity**: Medium (4-6 hours)
**Priority**: Medium
**Type**: Enhancement / Refactoring
**Impact**: High (improves UX for majority use case)
