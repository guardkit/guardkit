# Implementation Plan: TASK-9038

## Task: Create /template-qa Command for Optional Customization

**Status**: Phase 2.7 - Complexity Evaluation
**Created**: 2025-11-12T09:30:00Z
**Estimated Duration**: 5-6 hours
**Estimated LOC**: ~970 lines

---

## Executive Summary

Create a new **optional** command `/template-qa` that runs an interactive Q&A session to customize template generation. This separates the Q&A functionality from `/template-create`, making it optional for advanced users while keeping the default workflow simple.

**Key Principle**: 90% of users will just run `/template-create` with smart defaults. Only 10% who need customization will use `/template-qa` first.

---

## Files to Create (3 files)

### 1. Command Specification
- **Path**: `installer/global/commands/template-qa.md`
- **LOC**: ~150 lines
- **Purpose**: Command specification and documentation
- **Dependencies**: None

### 2. Q&A Orchestrator
- **Path**: `installer/global/lib/template_qa_orchestrator.py`
- **LOC**: ~400 lines
- **Purpose**: Core Q&A logic, config persistence, validation
- **Dependencies**:
  - Extracted logic from `template_create_orchestrator.py`
  - Standard library: `json`, `pathlib`, `typing`

### 3. Config Handler
- **Path**: `installer/global/lib/template_config_handler.py`
- **LOC**: ~200 lines
- **Purpose**: Config file I/O, validation, schema management
- **Dependencies**:
  - Standard library: `json`, `pathlib`, `typing`
  - JSON schema validation

---

## Files to Modify (2 files)

### 1. Template Create Orchestrator
- **Path**: `installer/global/lib/template_create_orchestrator.py`
- **Current LOC**: ~800 lines (estimated)
- **Changes**:
  - Extract Q&A logic (~200 lines removed)
  - Add config file loading support (~20 lines added)
  - Net change: ~-180 lines
- **Purpose**: Simplify by delegating Q&A to new command

### 2. Command Index/Registry
- **Path**: TBD (command registry or index file)
- **Changes**: Add `/template-qa` to available commands
- **LOC**: ~20 lines

---

## Implementation Phases

### Phase 1: Config Handler (2 hours)
**Files**: `template_config_handler.py`

1. **Config Schema Definition** (30 min)
   - JSON schema for `.template-create-config.json`
   - Field validation rules
   - Default values

2. **Config I/O Operations** (45 min)
   - Load config from file
   - Save config to file
   - Merge with defaults

3. **Validation Logic** (45 min)
   - Schema validation
   - Field-level validation
   - Error reporting

**Deliverable**: Reusable config handler module

---

### Phase 2: Q&A Orchestrator (2 hours)

**Files**: `template_qa_orchestrator.py`

1. **Extract Q&A Logic** (60 min)
   - Identify Q&A code in `template_create_orchestrator.py`
   - Extract to new module
   - Maintain existing behavior

2. **Add Config Persistence** (30 min)
   - Save answers to config file
   - Resume from existing config
   - Preserve unchanged answers

3. **Improve Prompts** (30 min)
   - Clear, helpful prompts
   - Examples and defaults
   - Validation feedback

**Deliverable**: Standalone Q&A orchestrator

---

### Phase 3: Command Specification (1 hour)

**Files**: `installer/global/commands/template-qa.md`

1. **Command Documentation** (30 min)
   - Usage examples
   - Flag documentation (`--resume`)
   - Config file format

2. **Integration Examples** (30 min)
   - Workflow examples
   - 90/10 use case explanation
   - When to use vs skip

**Deliverable**: Complete command spec

---

### Phase 4: Template Create Integration (1 hour)

**Files**: `installer/global/lib/template_create_orchestrator.py`

1. **Remove Q&A Logic** (30 min)
   - Delete extracted Q&A code
   - Add config file loading
   - Maintain backward compatibility

2. **Update Command Flow** (30 min)
   - Check for config file first
   - Fall back to smart defaults
   - Update documentation

**Deliverable**: Simplified `/template-create`

---

### Phase 5: Testing (1 hour)

**Test Coverage**:
1. **Config Handler Tests** (20 min)
   - Load/save operations
   - Validation logic
   - Error handling

2. **Q&A Orchestrator Tests** (20 min)
   - Interactive flow
   - Resume functionality
   - Config persistence

3. **Integration Tests** (20 min)
   - `/template-qa` → config file → `/template-create`
   - Default workflow (no config)
   - Error scenarios

**Deliverable**: Comprehensive test suite

---

## Architecture Patterns

### 1. Command Pattern
- Separate command (`/template-qa`) from orchestration
- Clear separation of concerns

### 2. Config Persistence Pattern
- JSON config file
- Human-readable and editable
- Schema validation

### 3. Builder Pattern
- Q&A builds config incrementally
- Resume capability (load → edit → save)
- Validation at each step

---

## Risk Assessment

### Low Risk Factors ✅
- **No external dependencies**: Using standard library only
- **Extracted logic**: Code already exists, just reorganizing
- **Backward compatible**: Doesn't break existing `/template-create`
- **Clear interfaces**: Config file format is well-defined

### Medium Risk Factors ⚠️
- **Integration testing**: Need to verify both commands work together
- **User experience**: Prompts must be clear and helpful
- **Resume logic**: Must handle partial config files correctly

### Mitigation Strategies
1. **Integration Testing**: Test both commands in isolation and together
2. **User Testing**: Review prompts with target users
3. **Validation**: Comprehensive schema validation before saving

---

## Dependencies

### Internal Dependencies
- `template_create_orchestrator.py` (source of extracted logic)
- Command registry/index system

### External Dependencies
- None (using Python standard library)

### Optional Enhancements
- JSON schema validation library (e.g., `jsonschema`)
- Rich terminal formatting (e.g., `rich` library)

---

## Success Criteria

### Functional Requirements ✅
- [ ] `/template-qa` command runs interactive Q&A
- [ ] Saves answers to `.template-create-config.json`
- [ ] `--resume` flag loads and edits existing config
- [ ] `/template-create --config` uses saved config
- [ ] `/template-create` works without config (smart defaults)

### Quality Requirements ✅
- [ ] 100% test coverage for config handler
- [ ] Integration tests pass
- [ ] Clear, helpful prompts (user feedback)
- [ ] Documentation complete and accurate

### Non-Functional Requirements ✅
- [ ] No breaking changes to `/template-create`
- [ ] Config file is human-readable JSON
- [ ] Validation errors are clear and actionable

---

## LOC Breakdown

| Component | New LOC | Modified LOC | Net Change |
|-----------|---------|--------------|------------|
| Command spec | +150 | 0 | +150 |
| Q&A orchestrator | +400 | 0 | +400 |
| Config handler | +200 | 0 | +200 |
| Template create | 0 | -180 | -180 |
| Command index | +20 | 0 | +20 |
| **Total** | **+770** | **-180** | **+590** |

**Note**: Original estimate of ~970 LOC included ~200 lines of tests not counted here.

---

## Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Config Handler | 2 hours | Pending |
| Phase 2: Q&A Orchestrator | 2 hours | Pending |
| Phase 3: Command Spec | 1 hour | Pending |
| Phase 4: Integration | 1 hour | Pending |
| Phase 5: Testing | 1 hour | Pending |
| **Total** | **5-6 hours** | **Pending** |

---

## Related Tasks

- **TASK-9037**: Fix build artifact exclusion (independent)
- **TASK-9039**: Remove Q&A from /template-create (depends on this task)

---

## Architectural Review Summary

**Overall Score**: 78/100 (Approved with recommendations)

- **SOLID**: 40/50
  - SRP: 10/10 ✅
  - OCP: 8/10 ✅
  - LSP: 9/10 ✅
  - ISP: 8/10 ✅
  - DIP: 5/10 ⚠️ (Recommendation: Inject dependencies)

- **DRY**: 20/25
  - Some duplication possible between Q&A and template-create

- **YAGNI**: 18/25
  - Question: Could this be a flag instead of standalone command?
  - Decision: Standalone command is clearer for 90/10 use case split

---

## Notes

- **90/10 Use Case Split**: This design optimizes for the common case (no customization) while providing power users with full control
- **Backward Compatibility**: Existing `/template-create` workflow unchanged
- **Future Enhancement**: Could add config templates or presets for common customizations
