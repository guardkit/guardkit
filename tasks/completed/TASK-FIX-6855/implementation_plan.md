# Implementation Plan: TASK-FIX-6855

## Executive Summary

This task addresses 4 HIGH/MEDIUM priority issues from the TASK-REV-6E5D review:

1. **Issue 1** (HIGH): Pydantic validation failure - AI returns categorized framework dict, but schema expects list
2. **Issue 4** (HIGH): 30% of templates classified as "other/" due to narrow layer detection
3. **Issue 5** (MEDIUM): Utility files falsely detected as entities causing CRUD warnings
4. **Issue 6** (HIGH): Malformed template names with double extensions

**Estimated Duration**: 6-9 hours
**Complexity Score**: 5/10 (Medium)
**Files Modified**: 4 Python modules
**Test Files Created**: 4 new test files
**Estimated LOC**: ~155 lines implementation + ~830 lines tests

---

## Files to Modify

| File | Issue | Changes |
|------|-------|---------|
| `installer/core/lib/codebase_analyzer/models.py` | Issue 1 | Add FrameworkInfo model, Union type for frameworks |
| `installer/core/lib/codebase_analyzer/agent_invoker.py` | Issue 4 | Extend _detect_layers() with 13 directory patterns |
| `installer/core/lib/template_generator/pattern_matcher.py` | Issue 5 | Add CRUD prefix guard clause to identify_entity() |
| `installer/core/lib/template_generator/completeness_validator.py` | Issue 6 | Fix _estimate_file_path() to handle .template suffix |

## Test Files to Create

| File | Issue | Purpose |
|------|-------|---------|
| `tests/unit/lib/codebase_analyzer/test_models_frameworks.py` | Issue 1 | Framework schema tests |
| `tests/unit/lib/codebase_analyzer/test_agent_invoker_layers.py` | Issue 4 | Layer detection tests |
| `tests/unit/lib/template_generator/test_pattern_matcher_entity.py` | Issue 5 | Entity detection tests |
| `tests/unit/lib/template_generator/test_completeness_validator_naming.py` | Issue 6 | Template naming tests |

---

## Issue 1: Framework Schema Fix

### File: `installer/core/lib/codebase_analyzer/models.py`

**Problem**: `TechnologyInfo.frameworks` only accepts `List[str]` but AI returns categorized dict like:
```python
{"frontend": ["React"], "backend": ["FastAPI"], "build_tools": ["Vite"]}
```

**Solution**:
1. Add `FrameworkInfo` model for rich metadata
2. Change `frameworks` to `Union[List[str], Dict[str, List[Union[str, FrameworkInfo]]]]`
3. Add `framework_list` property for backward compatibility

**Risk**: LOW - Union type allows both formats

---

## Issue 4: Extended Layer Detection

### File: `installer/core/lib/codebase_analyzer/agent_invoker.py`

**Problem**: Only Clean Architecture layers detected (domain/, application/, infrastructure/), causing 30% of files to end up in "other/"

**Solution**: Extend `_detect_layers()` with 13 additional directory patterns:
- `routes/`, `controllers/`, `views/`, `endpoints/` → Presentation
- `lib/`, `upload/`, `scripts/`, `middleware/` → Infrastructure
- `utils/`, `helpers/` → Shared
- `src/`, `components/`, `stores/`, `services/` → Application

**Risk**: LOW - Additive change, preserves existing behavior

---

## Issue 5: Entity Detection Fix

### File: `installer/core/lib/template_generator/pattern_matcher.py`

**Problem**: Utility files like `query.js`, `firebase.js` detected as entities, causing false CRUD completeness warnings

**Solution**: Add guard clause to `identify_entity()`:
```python
operation = CRUDPatternMatcher.identify_crud_operation(template)
if operation is None:
    return None  # Not a CRUD file - don't treat as entity
```

**Risk**: LOW - Simple guard clause eliminates false positives

---

## Issue 6: Template Naming Fix

### File: `installer/core/lib/template_generator/completeness_validator.py`

**Problem**: Double extensions like `.svelte.svelte.template` and malformed names like `query.j.js.template`

**Cause**: `Path.suffixes` treats `.template` as part of compound extension incorrectly

**Solution**: Manually separate `.template` as meta-suffix:
```python
if ref_name.endswith('.template'):
    actual_filename = ref_name[:-9]  # len('.template') == 9
    template_suffix = '.template'
else:
    actual_filename = ref_name
    template_suffix = ''

actual_path = Path(actual_filename)
actual_ext = actual_path.suffix  # .svelte, .js, etc.
```

**Risk**: MEDIUM - Complex logic but well-tested

---

## Implementation Sequence

1. **Phase 1** (1.5h): Issue 1 - Framework schema (foundation)
2. **Phase 2** (2-3h): Issue 4 - Layer detection (additive)
3. **Phase 3** (1.5h): Issue 5 - Entity detection (guard clause)
4. **Phase 4** (2h): Issue 6 - Template naming (complex)
5. **Phase 5** (1h): Integration testing

---

## Acceptance Criteria

### Issue 1: Framework Schema
- [ ] `TechnologyInfo.frameworks` accepts both `List[str]` and categorized dict
- [ ] AI's categorized framework response is preserved
- [ ] Backward compatible with simple list format

### Issue 4: Layer Detection
- [ ] Heuristic layer detection covers extended patterns
- [ ] Directories map to appropriate layers
- [ ] "other/" directory usage reduced to <15%

### Issue 5: Entity Detection
- [ ] Only files with CRUD operation prefix are treated as entities
- [ ] Utility files (query.js, firebase.js) are NOT detected as entities
- [ ] No false positive CRUD completeness warnings

### Issue 6: Template Naming
- [ ] `.template` suffix correctly separated from actual file extension
- [ ] No double extensions (`.svelte.svelte.template`)
- [ ] No malformed names (`query.j.js.template`)

---

## Architecture Decisions

### AD-1: Union Type for Frameworks
Use `Union[List[str], Dict[str, List[Union[str, FrameworkInfo]]]]` to preserve rich AI responses while maintaining backward compatibility.

### AD-2: Extended Pattern Mapping
Add 13 common directory patterns beyond Clean Architecture to cover MVC, Rails, Django, Express codebases.

### AD-3: CRUD Prefix Guard Clause
Check `identify_crud_operation()` first in `identify_entity()`, return `None` if no CRUD prefix.

### AD-4: Template Suffix Separation
Manually separate `.template` as meta-suffix before processing to preserve actual file extension.
