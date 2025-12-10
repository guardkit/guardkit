---
id: TASK-CLEANUP-IMPORTLIB
title: Remove importlib workarounds after installer/global rename
status: backlog
task_type: refactor
created: 2025-12-10T17:35:00Z
updated: 2025-12-10T17:35:00Z
priority: low
tags: [technical-debt, refactor, python, cleanup]
complexity: 3
implementation_mode: direct
depends_on: [TASK-RENAME-GLOBAL]
parent_review: TASK-REV-TC01
---

# Remove importlib workarounds after installer/global rename

## Problem Statement

After renaming `installer/global` to `installer/core` (TASK-RENAME-GLOBAL), we can now use standard Python imports instead of the `importlib.import_module()` workarounds that were required due to the reserved keyword conflict.

**Current workaround pattern (can now be removed)**:
```python
# Before (workaround due to reserved keyword)
import importlib
_models_module = importlib.import_module('installer.core.lib.codebase_analyzer.models')
CodebaseAnalysis = _models_module.CodebaseAnalysis

# After (standard import now works!)
from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis
```

## Impact

- **Developer experience**: Standard imports are more intuitive
- **Code quality**: Consistent import patterns across codebase
- **IDE support**: Better autocomplete and go-to-definition
- **Static analysis**: mypy/pylint can now trace dependencies

## Acceptance Criteria

- [ ] All `importlib.import_module('installer.core.*')` calls converted to standard imports
- [ ] Unused `import importlib` statements removed
- [ ] All tests pass after conversion
- [ ] No circular import errors introduced

## Technical Specification

### Files Requiring importlib Removal

Based on TASK-RENAME-GLOBAL analysis, these files contain importlib workarounds:

1. `installer/core/lib/template_creation/manifest_generator.py`
2. `installer/core/lib/template_generator/layer_classifier.py`
3. `installer/core/lib/template_generator/template_generator.py`
4. `installer/core/lib/template_generator/pattern_matcher.py`
5. `installer/core/lib/template_generator/path_resolver.py`
6. `installer/core/lib/template_generator/__init__.py`
7. `installer/core/lib/template_generator/completeness_validator.py`
8. `installer/core/lib/agent_enhancement/orchestrator.py`
9. `installer/core/lib/agent_enhancement/applier.py`
10. `installer/core/lib/agent_enhancement/enhancer.py`
11. `installer/core/lib/settings_generator/generator.py`
12. `installer/core/commands/agent-validate.py`
13. `installer/core/commands/agent-format.py`
14. `installer/core/commands/lib/template_create_orchestrator.py`
15. `installer/core/commands/lib/distribution_helpers.py`
16. `installer/core/commands/lib/phase_execution.py`
17. `installer/core/lib/agent_formatting/parser.py`
18. Multiple test files in `tests/`

### Conversion Process

For each file:

1. **Find importlib patterns**:
   ```python
   # Pattern to find:
   _module = importlib.import_module('installer.core.some.module')
   SomeClass = _module.SomeClass
   ```

2. **Convert to standard import**:
   ```python
   from installer.core.some.module import SomeClass
   ```

3. **Remove unused importlib import** (if no other importlib usage):
   ```python
   # Remove this line:
   import importlib
   ```

4. **Check for circular imports**:
   - Run: `python -c "from installer.core.module import Class; print('OK')"`
   - If circular import detected, keep importlib pattern for that specific case

### Verification

```bash
# 1. Find any remaining importlib workarounds
grep -rn "importlib.import_module.*installer.core" --include="*.py" .

# 2. Verify all imports work
python -c "from installer.core.lib.template_generator import layer_classifier; print('OK')"

# 3. Run full test suite
pytest tests/ -v
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular imports | Medium | High | Keep importlib for affected files |
| Missed conversions | Low | Low | Grep verification |
| Test failures | Low | Medium | Full test suite run |

## Notes

- This task was intentionally deferred from TASK-RENAME-GLOBAL per architectural review
- Some dynamic imports (where module name is computed at runtime) should NOT be converted
- Keep importlib for any cases that cause circular import errors
- Low priority - existing importlib patterns still work correctly

## Estimated Effort

- **Complexity**: 3/10 (mechanical replacement)
- **Duration**: 1-2 hours
- **Files**: ~18 files
