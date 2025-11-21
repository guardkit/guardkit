# TASK-REMOVE-DETECTOR: Remove Hard-Coded Detection

**Task ID**: TASK-REMOVE-DETECTOR
**Title**: Remove 1,045 LOC of Hard-Coded Pattern Detection
**Status**: BACKLOG
**Priority**: MEDIUM
**Complexity**: 2/10 (Simple)
**Estimated Hours**: 1-2
**Phase**: 6 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

The codebase contains 1,045 LOC of hard-coded pattern matching that violates the AI-first principle:

```python
# smart_defaults_detector.py (531 LOC)
class LanguageDetector:
    def detect_language(self, project_path: Path) -> Optional[str]:
        if (project_path / "setup.py").exists():
            return "Python"
        # ... 7 more languages with file-based detection

class FrameworkDetector:
    PYTHON_FRAMEWORKS = {
        r"fastapi[>=<]": "FastAPI",
        r"flask[>=<]": "Flask",
        # ... Pattern matching for 12+ frameworks
```

### Impact

- Maintenance burden (update code for every new framework)
- Brittle with monorepos, custom configs
- Contradicts AI-native vision from TASK-042/058/059
- Redundant with AI-powered Phases 1 and 4

---

## Solution Design

### Approach

Delete the hard-coded detection code now that AI-powered phases handle all detection.

### Files to Delete

| File | LOC | Description |
|------|-----|-------------|
| `installer/global/commands/lib/smart_defaults_detector.py` | 531 | Hard-coded detectors |
| `tests/unit/test_smart_defaults_detector.py` | 514 | Tests for deleted code |
| **Total** | **1,045** | |

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/global/commands/lib/template_create_orchestrator.py` | MODIFY | Remove imports and references |

---

## Implementation Details

### 1. Remove Imports

```python
# In template_create_orchestrator.py

# DELETE these imports:
# from .smart_defaults_detector import SmartDefaultsDetector, LanguageDetector, FrameworkDetector

# DELETE any usage:
# self.detector = SmartDefaultsDetector()
# result = self.detector.detect_defaults(...)
```

### 2. Remove Any Fallback References

```python
# DELETE any code like:
# if not ai_result:
#     return self.detector.detect_language(...)
```

### 3. Verify Imports

After deletion, ensure no other files import the detector:

```bash
grep -r "smart_defaults_detector" installer/
grep -r "SmartDefaultsDetector" installer/
grep -r "LanguageDetector" installer/
grep -r "FrameworkDetector" installer/
```

---

## Acceptance Criteria

### Functional

- [ ] Files deleted: smart_defaults_detector.py, test_smart_defaults_detector.py
- [ ] No remaining imports or references
- [ ] All tests pass
- [ ] Template creation still works

### Quality

- [ ] 1,045 LOC removed
- [ ] No regressions
- [ ] AI-first architecture restored

---

## Test Specifications

### Pre-Deletion Verification

Before deleting, verify AI phases work:

```bash
# Test on all 4 reference projects
for project in maui react fastapi nextjs; do
    /template-create --validate --name $project
    # Should succeed with AI-powered detection
done
```

### Post-Deletion Verification

```bash
# 1. Verify files deleted
test ! -f installer/global/commands/lib/smart_defaults_detector.py
test ! -f tests/unit/test_smart_defaults_detector.py

# 2. Verify no dangling imports
grep -r "smart_defaults_detector" . && echo "FAIL: Remaining imports"

# 3. Run all tests
pytest tests/ -v

# 4. Test template creation
/template-create --validate --name test-post-deletion
```

### Regression Tests

Test that templates still create correctly:

```python
# tests/regression/test_template_creation.py

class TestTemplateCreationRegression:
    """Regression tests after removing hard-coded detection."""

    @pytest.mark.parametrize("project,expected_lang,expected_framework", [
        ("~/Projects/DeCUK.Mobile.MyDrive", "C#", ".NET MAUI"),
        ("~/Projects/bulletproof-react", "TypeScript", "React"),
        ("~/Projects/fastapi-best-practices", "Python", "FastAPI"),
        ("~/Projects/nextjs-boilerplate", "TypeScript", "Next.js"),
    ])
    def test_project_detection(self, project, expected_lang, expected_framework):
        """Test that AI correctly detects language and framework."""
        result = run_template_create(project)

        assert result.language == expected_lang
        assert result.framework == expected_framework
        assert result.confidence >= 0.85
```

---

## Dependencies

### Depends On
- TASK-PHASE-1-CHECKPOINT (Phase 3) - AI analysis must work
- TASK-PHASE-5-CHECKPOINT (Phase 4) - AI agent creation must work

### Blocks
- TASK-RENAME-LEGACY-BUILD-NEW (Phase 7) - clean code for new command

---

## Rollback Plan

If AI phases prove insufficient:

1. **Immediate**: Revert deletion using git
2. **Short-term**: Keep detector as optional fallback
3. **Long-term**: Improve AI prompts until detection is reliable

```bash
# Emergency rollback
git checkout HEAD~1 -- installer/global/commands/lib/smart_defaults_detector.py
git checkout HEAD~1 -- tests/unit/test_smart_defaults_detector.py
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| LOC removed | 1,045 | File deletion |
| Tests passing | 100% | pytest |
| Regressions | 0 | Regression tests |
| Template creation | Works | Manual verification |

---

## Notes

- This is a simple deletion task but has dependencies
- Must ensure AI phases work before deleting
- Keep rollback plan ready for first few weeks

---

**Created**: 2025-11-18
**Phase**: 6 of 8 (Template-Create Redesign)
**Related**: AI-First principle restoration
