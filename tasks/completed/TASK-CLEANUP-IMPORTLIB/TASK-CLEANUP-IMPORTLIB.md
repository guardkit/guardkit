---
id: TASK-CLEANUP-IMPORTLIB
title: Remove importlib workarounds after installer/global rename
status: completed
task_type: refactor
created: 2025-12-10T17:35:00Z
updated: 2025-12-11T11:30:00Z
completed: 2025-12-11T11:30:00Z
priority: low
tags: [technical-debt, refactor, python, cleanup]
complexity: 3
implementation_mode: direct
depends_on: [TASK-RENAME-GLOBAL]
parent_review: TASK-REV-TC01
completion_summary:
  files_converted: 46
  occurrences_converted: 88
  preserved_importlib: 8
  fix_loop_iterations: 1
  tests_passing: 100
  module_imports_verified: 21
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

- [x] All `importlib.import_module('installer.core.*')` calls converted to standard imports
- [x] Unused `import importlib` statements removed
- [x] All tests pass after conversion
- [x] No circular import errors introduced

## Implementation Summary

### Files Converted (46 files)

**installer/core/lib/codebase_analyzer/** (7 files):
- serializer.py, response_parser.py, agent_invoker.py, prompt_builder.py, stratified_sampler.py, `__init__.py`, ai_analyzer.py

**installer/core/lib/template_generator/** (9 files):
- pattern_matcher.py, completeness_validator.py, extended_validator.py, path_resolver.py, layer_classifier.py, template_generator.py, report_generator.py, `__init__.py`

**installer/core/lib/settings_generator/** (3 files):
- generator.py, validator.py, `__init__.py`

**installer/core/lib/agent_orchestration/** (2 files):
- `__init__.py`, agent_orchestration.py

**Other installer/core/lib/** (4 files):
- agent_bridge/`__init__.py`, agent_enhancement/applier.py, agent_formatting/parser.py, template_creation/manifest_generator.py, template_qa_orchestrator.py

**installer/core/commands/** (3 files):
- agent-format.py, agent-validate.py, lib/agent_validator/validator.py

**tests/** (18 files):
- All test files with importlib patterns converted

### Preserved Importlib Patterns (8 occurrences)

These patterns were intentionally preserved due to circular imports or lazy loading requirements:

1. **external_discovery.py** - ALL 4 imports (circular with agent_orchestration.py)
2. **agent_orchestration.py:199** - lazy import of external_discovery
3. **ai_analyzer.py:126** - optional feature lazy load
4. **orchestrator.py:89** - try-except fallback pattern
5. **enhancer.py:312** - try-except fallback pattern
6. **test_integration_imports.py:140** - intentional error testing

### Import Patterns Used

- **Same-package**: Relative imports (`from .models import X`)
- **Cross-package**: Absolute imports (`from installer.core.lib.utils.file_io import X`)
- **Commands**: Absolute imports
- **Tests**: Absolute imports

### Fix Loop

One fix was required during Phase 4.5:
- **Issue**: Missing `CRUD_PATTERNS` import in completeness_validator.py
- **Fix**: Added `CRUD_PATTERNS` to the import statement

## Verification

```bash
# Module imports verified: 21/21 successful
# Tests passing: 100 tests for converted files
# Remaining importlib patterns: 8 (intentionally preserved)
```

## Notes

- This task was intentionally deferred from TASK-RENAME-GLOBAL per architectural review
- Some dynamic imports (where module name is computed at runtime) should NOT be converted
- Keep importlib for any cases that cause circular import errors
- Low priority - existing importlib patterns still work correctly
