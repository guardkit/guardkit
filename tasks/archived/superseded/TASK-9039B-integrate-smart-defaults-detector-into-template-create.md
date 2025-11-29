# TASK-9039B: Integrate Smart Defaults Detector into /template-create

**Status**: backlog
**Priority**: high
**Created**: 2025-11-12T10:20:00Z
**Updated**: 2025-11-12T10:20:00Z
**Tags**: #template-create #integration #smart-defaults #non-interactive
**Complexity**: 3/10 (Simple - integration of existing module)
**Depends On**: TASK-9039 (detector module created)

---

## Description

Integrate the smart defaults detector module (created in TASK-9039) into the `/template-create` command to enable non-interactive operation. This completes the refactoring started in TASK-9039.

**Current State**: Smart defaults detector exists but is NOT integrated into `/template-create` orchestrator.

**Goal**: Make `/template-create` work non-interactively using the detector module.

---

## Background

TASK-9039 created a high-quality smart defaults detector module with:
- LanguageDetector (9 languages supported)
- FrameworkDetector (12+ frameworks supported)
- ConfigResolver (priority: config > detection > defaults)
- 36 comprehensive tests (91% coverage)

**What's missing**: The orchestrator still uses interactive Q&A session instead of the new detector.

---

## Acceptance Criteria

### Core Integration
- [ ] Modify `template_create_orchestrator.py` to use `SmartDefaultsDetector`
- [ ] Remove blocking Q&A calls from Phase 1
- [ ] Add `--config` flag support to load config files
- [ ] Maintain backward compatibility with `--skip-qa` (deprecated)
- [ ] Non-interactive by default (no prompts)

### Documentation
- [ ] Update `template-create.md` command specification
- [ ] Document new non-interactive behavior
- [ ] Document `--config` flag usage
- [ ] Add example config file format
- [ ] Mark `--skip-qa` as deprecated

### Testing
- [ ] Create integration tests for non-interactive mode
- [ ] Test with config file loading
- [ ] Test backward compatibility with `--skip-qa`
- [ ] Verify works in CI/CD environment
- [ ] Test across multiple project types (Python, TypeScript, .NET)

---

## Implementation Plan

### Phase 1: Orchestrator Integration (1.5 hours)

**File**: `installer/global/lib/codebase_analyzer/template_create_orchestrator.py`

**Changes**:
1. Import `SmartDefaultsDetector`, `LanguageDetector`, `FrameworkDetector`, `ConfigResolver`
2. Update `_phase1_qa_session()` method:
   ```python
   def _phase1_qa_session(self, config_file: Optional[Path] = None) -> GreenfieldAnswers:
       """Phase 1: Configuration Resolution (non-interactive)."""
       # Priority: config file > smart detection > defaults
       detector = SmartDefaultsDetector(
           codebase_path=self.codebase_path,
           config_handler=TemplateConfigHandler()  # from TASK-9038
       )

       if config_file:
           # Load from config file
           return detector.load_from_config(config_file)
       else:
           # Use smart detection
           return detector.generate_smart_defaults()
   ```
3. Add `config_file` parameter to `OrchestrationConfig` dataclass
4. Add deprecation warning if `skip_qa=True` (now default behavior)

**Estimated**: ~50 LOC changes

### Phase 2: Documentation Update (1 hour)

**File**: `installer/global/commands/template-create.md`

**Changes**:
1. Update command description (non-interactive by default)
2. Add `--config <file>` flag documentation
3. Add smart detection explanation
4. Add example config file format
5. Mark `--skip-qa` as deprecated
6. Add CI/CD usage examples

**Estimated**: ~100 lines of documentation

### Phase 3: Integration Testing (1 hour)

**File**: `tests/integration/test_template_create_integration.py` (NEW)

**Test scenarios**:
1. Run without config (smart defaults)
2. Run with config file (`--config`)
3. Run with `--skip-qa` (deprecated but works)
4. Run in CI/CD environment (non-interactive)
5. Test with Python project
6. Test with TypeScript project
7. Test with .NET project

**Estimated**: ~300 LOC tests

---

## Timeline

- **Phase 1**: 1.5 hours (orchestrator integration)
- **Phase 2**: 1 hour (documentation)
- **Phase 3**: 1 hour (integration tests)
- **Total**: 3-4 hours

---

## Files to Modify

1. `installer/global/lib/codebase_analyzer/template_create_orchestrator.py` (+50 LOC)
2. `installer/global/commands/template-create.md` (+100 lines)
3. `tests/integration/test_template_create_integration.py` (+300 LOC) - NEW

**Total**: ~450 LOC

---

## Dependencies

### Prerequisites (COMPLETED)
- ✅ TASK-9037: Build artifact exclusion
- ✅ TASK-9038: /template-qa command (TemplateConfigHandler)
- ✅ TASK-9039: Smart defaults detector module

### External Dependencies
- None (uses existing modules)

---

## Risk Assessment

**Risk Level**: LOW

**Why Low Risk**:
- Detector module already tested (36 tests, 91% coverage)
- Non-breaking change (backward compatible)
- Integration is straightforward (replace Q&A with detector)
- Config handler already exists (TASK-9038)

**Mitigations**:
- Comprehensive integration tests before deployment
- Backward compatibility maintained via deprecated flags
- Fallback to defaults if detection fails

---

## Success Criteria

### Functional
- `/template-create` runs non-interactively by default
- Smart detection works for Python, TypeScript, .NET projects
- Config file loading works via `--config` flag
- Backward compatible with `--skip-qa` flag
- Works in CI/CD environments (no stdin required)

### Quality
- Integration tests pass (100%)
- Coverage maintained (≥80%)
- Documentation updated and accurate
- No breaking changes to existing workflows

---

## Testing Strategy

### Unit Tests
- Use existing detector tests (TASK-9039)
- Add orchestrator unit tests for config loading

### Integration Tests
- End-to-end workflow tests
- Multiple project types (Python, TypeScript, .NET)
- Config file scenarios
- CI/CD environment simulation

### Manual Tests
- Test on real projects
- Verify non-interactive execution
- Validate detection accuracy
- Confirm backward compatibility

---

## Related Tasks

- **TASK-9037**: Build artifact exclusion (completed)
- **TASK-9038**: /template-qa command (completed)
- **TASK-9039**: Smart defaults detector (completed - partial)
- **TASK-9040**: Investigate regression (in review)

---

## Notes

### Why Separate Task?
1. Detector module is production-ready (excellent quality)
2. Integration is distinct from detector creation
3. Allows phased delivery (detector available now, integration later)
4. Clearer scope and easier tracking

### Complexity Justification
- **3/10 (Simple)**: Integration is straightforward
  - Detector module already exists and tested
  - Clear API for orchestrator to call
  - Minimal code changes required (~50 LOC)
  - Low risk (backward compatible)

### Estimated Effort
- **3-4 hours** total
- **Complexity**: 3/10 (Simple integration)
- **Priority**: High (completes TASK-9039 functionality)
