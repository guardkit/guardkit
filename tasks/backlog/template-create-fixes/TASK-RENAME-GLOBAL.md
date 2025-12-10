---
id: TASK-RENAME-GLOBAL
title: Rename installer/global to installer/core
status: backlog
task_type: refactor
created: 2025-12-10T16:30:00Z
updated: 2025-12-10T16:30:00Z
priority: medium
tags: [technical-debt, refactor, python]
complexity: 5
implementation_mode: direct
wave: 3
parent_review: TASK-REV-TC01
---

# Rename installer/global to installer/core

## Problem Statement

The directory `installer/global/` contains the Python reserved keyword `global`, causing syntax errors when using standard import statements. Currently 20+ files use `importlib.import_module()` as a workaround.

**Example of current workaround**:
```python
# Instead of:
from installer.global.lib.codebase_analyzer.models import CodebaseAnalysis  # SyntaxError!

# We use:
_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')
CodebaseAnalysis = _models_module.CodebaseAnalysis
```

## Impact

- **Developer experience**: Confusing workaround pattern
- **Code quality**: Non-standard import syntax
- **Future risk**: Python 3.14+ may have stricter keyword handling
- **Maintenance**: Each new file needs to remember the workaround

## Acceptance Criteria

- [ ] Directory renamed from `installer/global/` to `installer/core/`
- [ ] All 44 Python references updated
- [ ] All markdown documentation updated
- [ ] All JSON configuration updated
- [ ] importlib workarounds removed (optional but recommended)
- [ ] All tests pass after rename
- [ ] install.sh script updated
- [ ] Backward compatibility: Old symlinks updated

## Technical Specification

### Step 1: Rename Directory

```bash
git mv installer/global installer/core
```

### Step 2: Update Python References

```bash
# Update import paths (44 occurrences in 20 files)
find . -name "*.py" -not -path "./.git/*" -exec sed -i '' 's/installer\.global/installer.core/g' {} \;
find . -name "*.py" -not -path "./.git/*" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
```

### Step 3: Update Markdown Documentation

```bash
find . -name "*.md" -not -path "./.git/*" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
```

### Step 4: Update JSON Files

```bash
find . -name "*.json" -not -path "./.git/*" -not -path "./node_modules/*" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
```

### Step 5: Update Shell Scripts

```bash
find . -name "*.sh" -not -path "./.git/*" -exec sed -i '' 's/installer\/global/installer\/core/g' {} \;
```

### Step 6: Update importlib Usage (Optional but Recommended)

After rename, convert `importlib` calls to standard imports:

```python
# Before:
import importlib
_models_module = importlib.import_module('installer.core.lib.codebase_analyzer.models')
CodebaseAnalysis = _models_module.CodebaseAnalysis

# After:
from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis
```

### Files Requiring importlib Removal

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

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed references | Medium | High | Full grep verification before commit |
| Broken symlinks | Low | Medium | Update install.sh symlink paths |
| Test failures | Medium | Medium | Run full test suite |
| CI/CD issues | Low | High | Verify GitHub Actions workflows |

## Rollback Plan

```bash
# If issues found after commit:
git revert HEAD

# If issues found before commit:
git mv installer/core installer/global
git checkout -- .
```

## Execution

**IMPORTANT**: Execute during test freeze period (no parallel development)

```bash
# 1. Verify clean state
git status  # Should be clean
pytest      # All tests pass

# 2. Create backup branch
git checkout -b backup/pre-rename-global
git checkout -  # Return to original branch

# 3. Execute rename steps 1-5 above

# 4. Verify no stray references
grep -r "installer/global" --include="*.py" --include="*.md" --include="*.json" --include="*.sh" .
# Should return no results

# 5. Run full test suite
pytest

# 6. (Optional) Remove importlib workarounds - step 6

# 7. Commit
git add -A
git commit -m "refactor: rename installer/global to installer/core

Eliminates Python reserved keyword issue and enables standard import syntax.

Changes:
- Renamed installer/global/ → installer/core/
- Updated 44 Python references across 20 files
- Updated markdown documentation
- Updated JSON configuration
- Updated shell scripts

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

## Verification

```bash
# 1. All imports work
python -c "from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis; print('OK')"

# 2. All tests pass
pytest

# 3. Template creation works
cd /tmp && mkdir test-project && cd test-project
echo '{}' > package.json
/template-create --dry-run

# 4. No stray references
grep -r "installer/global" --include="*.py" .
# Should return empty
```

## Notes

- **Schedule carefully**: This affects many files and should not conflict with other work
- **Do NOT use Conductor**: Too many files affected for worktree approach
- **Execute on main branch**: After all other waves complete
- **Consider importlib removal**: While optional, removing workarounds improves code quality
- **Update install.sh**: The installation script creates symlinks that need path updates
