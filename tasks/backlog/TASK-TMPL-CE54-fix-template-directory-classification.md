# TASK-TMPL-CE54: Fix Template Directory Structure Classification

**Created**: 2025-11-20
**Priority**: High
**Type**: Bug Fix / Architectural Improvement
**Status**: Backlog
**Complexity**: 4/10 (Simple - straightforward refactoring)
**Estimated Effort**: 30-45 minutes implementation + 20 minutes testing
**Tags**: [template-generation, architecture, file-organization]
**Related**: TASK-C7A9, TASK-PHASE-7.5-SIMPLE

---

## Problem Statement

All `.cs.template` files are being placed in `templates/other/` instead of being organized by their architectural layer (domain, application, infrastructure, presentation). This makes templates difficult to navigate and understand.

**Current Behavior**:
```
templates/
└── other/                              # ❌ ALL files in one directory
    ├── AppErrors.cs.template
    ├── ConfigurationService.cs.template
    ├── ConfigurationRepository.cs.template
    ├── UserRepository.cs.template
    ├── ConfigurationEngine.cs.template
    ├── DomainCameraView.cs.template
    └── (more files...)
```

**Expected Behavior**:
```
templates/
├── domain/
│   ├── entities/
│   │   └── ConfigurationPayload.cs.template
│   └── errors/
│       └── AppErrors.cs.template
├── application/
│   ├── services/
│   │   ├── ConfigurationService.cs.template
│   │   └── ApiClientService.cs.template
│   └── repositories/
│       ├── ConfigurationRepository.cs.template
│       └── UserRepository.cs.template
├── infrastructure/
│   └── engines/
│       └── ConfigurationEngine.cs.template
└── presentation/
    └── views/
        └── DomainCameraView.cs.template
```

---

## Root Cause

**File**: `installer/global/lib/template_generator/template_generator.py` (Lines 392-421)

The `_infer_template_path()` method has a **fundamental flaw**:
1. It searches for layer names in the file path using string matching
2. It **IGNORES** the `example_file.layer` attribute that contains accurate layer information from AI analysis
3. When string matching fails (which it does for most projects), it falls back to `templates/other/`

**Current Code**:
```python
def _infer_template_path(self, example_file: ExampleFile) -> str:
    # Try to match with layers
    for layer in self.analysis.architecture.layers:
        # ❌ PROBLEM: String matching fails for most project structures
        if layer.name.lower() in example_file.path.lower():
            return f"templates/{layer.name}/{original_path.parent.name}/{template_name}"

    # ❌ PROBLEM: Falls back to 'other' too aggressively
    return f"templates/other/{original_path.name}.template"
```

**Why It Fails**: .NET MAUI projects don't have folders named "Domain", "Application", etc. They organize by pattern (Services/, Repositories/, Views/), so the string matching never succeeds.

**The Data We're Ignoring**: The AI analysis already provides `example_file.layer` with accurate layer information, but the code doesn't use it!

---

## Architectural Review Summary

**Architectural Score**: 52/100 ❌ **REJECTED**

**SOLID Compliance**: 28/50 (Failing)
- SRP: 4/10 (method does too much)
- OCP: 3/10 (must modify to add strategies)
- DIP: 6/10 (depends on concrete structures)

**See**: Complete architectural review in the architectural-reviewer agent output above.

---

## Objectives

### Primary Objective
Fix template file classification to properly organize files by architectural layer and sub-pattern (repositories, services, views, etc.).

### Success Criteria
- [ ] **AC1**: Files organized by layer (domain, application, infrastructure, presentation)
- [ ] **AC2**: Sub-organized by pattern (repositories, services, entities, views, etc.)
- [ ] **AC3**: Uses `example_file.layer` attribute from AI analysis as primary classification source
- [ ] **AC4**: Falls back to pattern-based classification when layer info missing
- [ ] **AC5**: Only uses `templates/other/` when truly unclassifiable
- [ ] **AC6**: Warns user when >20% of files go to `other/`
- [ ] **AC7**: Prints classification summary after template generation
- [ ] **AC8**: SOLID score improves from 28/50 to 42/50 (+50%)
- [ ] **AC9**: Fallback rate <20% for typical projects
- [ ] **AC10**: Test coverage ≥90% for new classification code

---

## Solution Design

### Architecture: Strategy Pattern with Chain of Responsibility

**Primary Strategy**: Use AI-provided layer information
**Fallback Strategy**: Pattern-based classification from filename
**Last Resort**: `templates/other/` with warning

**New File**: `installer/global/lib/template_generator/path_resolver.py`

### Implementation Overview

```python
# Strategy 1: Use AI layer data (PRIMARY)
class LayerClassificationStrategy:
    def classify(self, example_file: ExampleFile) -> Optional[str]:
        if example_file.layer:
            pattern = self._infer_pattern(example_file.path)  # Repository, Service, etc.
            return f"templates/{example_file.layer.lower()}/{pattern}/{filename}.template"
        return None

    def _infer_pattern(self, file_path: str) -> str:
        """
        Infer sub-directory from filename patterns.

        Examples:
            UserRepository.cs → repositories
            AuthService.cs → services
            ConfigurationEngine.cs → engines
            DomainCameraView.cs → views
        """
        filename = Path(file_path).stem

        patterns = [
            ('Repository', 'repositories'),
            ('Service', 'services'),
            ('Engine', 'engines'),
            ('View', 'views'),
            ('ViewModel', 'viewmodels'),
            ('Entity', 'entities'),
            ('Model', 'models'),
        ]

        for suffix, pattern_dir in patterns:
            if filename.endswith(suffix):
                return pattern_dir

        # Fallback: use parent directory name
        return Path(file_path).parent.name.lower()

# Strategy 2: Pattern-based fallback
class PatternClassificationStrategy:
    def classify(self, example_file: ExampleFile) -> Optional[str]:
        # Infer layer from filename pattern when layer info missing
        # E.g., *Repository.cs → application layer
        pass

# Orchestrator: Chain of responsibility
class TemplatePathResolver:
    def __init__(self):
        self.strategies = [
            LayerClassificationStrategy(),
            PatternClassificationStrategy(),
        ]
        self.warnings = []
        self.classification_stats = {}

    def resolve(self, example_file: ExampleFile) -> str:
        # Try each strategy
        for strategy in self.strategies:
            if path := strategy.classify(example_file):
                self.classification_stats[strategy.__class__.__name__] += 1
                return path

        # Fallback with warning
        self.warnings.append(f"Could not classify {example_file.path}")
        return f"templates/other/{filename}.template"

    def get_classification_summary(self) -> str:
        """Generate user-friendly summary."""
        total = sum(self.classification_stats.values())
        lines = ["Template Classification Summary:"]
        for strategy, count in self.classification_stats.items():
            percentage = (count / total) * 100
            lines.append(f"  {strategy}: {count} ({percentage:.1f}%)")

        fallback_pct = (self.stats.get('Fallback', 0) / total) * 100
        if fallback_pct > 20:
            lines.append(f"\n  ⚠️  Warning: {fallback_pct:.1f}% of files in 'other'")

        return "\n".join(lines)
```

---

## Files to Modify

### 1. Create New File: `path_resolver.py` (~200 lines)

**Location**: `installer/global/lib/template_generator/path_resolver.py`

**Contents**:
- `ClassificationStrategy` protocol
- `LayerClassificationStrategy` class
- `PatternClassificationStrategy` class
- `TemplatePathResolver` orchestrator

**Estimated Time**: 15 minutes

### 2. Modify: `template_generator.py` (~10 lines changed)

**Location**: `installer/global/lib/template_generator/template_generator.py`

**Changes**:
1. Import `TemplatePathResolver`
2. Add `path_resolver` to `__init__`
3. Replace `_infer_template_path()` implementation (lines 392-421)
4. Update `generate()` to print classification summary

**Estimated Time**: 10 minutes

### 3. Create Tests: `test_path_resolver.py` (~150 lines)

**Location**: `tests/lib/template_generator/test_path_resolver.py`

**Test Cases**:
- `test_layer_classification_with_repository()`
- `test_layer_classification_with_service()`
- `test_layer_classification_with_view()`
- `test_pattern_classification_fallback()`
- `test_resolver_chain_of_responsibility()`
- `test_fallback_with_warning()`
- `test_classification_summary()`
- `test_high_fallback_rate_warning()`

**Estimated Time**: 15 minutes

---

## Implementation Specification

### Step 1: Create `path_resolver.py` (15 min)

**See**: Complete implementation in architectural review Section 6.

**Key Components**:
1. `LayerClassificationStrategy` - uses `example_file.layer` (PRIMARY)
2. `PatternClassificationStrategy` - infers from filename patterns (FALLBACK)
3. `TemplatePathResolver` - orchestrates strategies, tracks stats

### Step 2: Update `template_generator.py` (10 min)

```python
# Add to imports
from .path_resolver import TemplatePathResolver

# Add to __init__
def __init__(self, analysis: CodebaseAnalysis, ai_client: Optional[AIClient] = None):
    # ... existing init code ...
    self.path_resolver = TemplatePathResolver()

# Replace _infer_template_path
def _infer_template_path(self, example_file: ExampleFile) -> str:
    """Use resolver for path inference."""
    return self.path_resolver.resolve(example_file, self.analysis)

# Update generate() to print summary
def generate(self, max_templates: Optional[int] = None) -> TemplateCollection:
    # ... existing generation logic ...

    # Print classification summary
    print(self.path_resolver.get_classification_summary())

    # Print warnings if any
    if self.path_resolver.warnings:
        print(f"\n⚠️  Classification warnings ({len(self.path_resolver.warnings)}):")
        for warning in self.path_resolver.warnings[:5]:
            print(f"  {warning}")
        if len(self.path_resolver.warnings) > 5:
            print(f"  ... and {len(self.path_resolver.warnings) - 5} more")

    return TemplateCollection(...)
```

### Step 3: Write Tests (15 min)

**See**: Complete test specifications in architectural review Section 8.

**Coverage Target**: ≥90% for `path_resolver.py`

---

## Testing Plan

### Unit Tests (10 minutes)

```bash
# Run new tests
pytest tests/lib/template_generator/test_path_resolver.py -v

# Expected output:
# test_layer_classification_with_repository PASSED
# test_layer_classification_with_service PASSED
# test_pattern_classification_fallback PASSED
# test_resolver_chain_of_responsibility PASSED
# test_fallback_with_warning PASSED
# test_classification_summary PASSED
#
# Coverage: 92% for path_resolver.py
```

### Integration Test (5 minutes)

```bash
# Test with real .NET MAUI project
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --name maui-test --validate

# Verify structure
ls -R ~/.agentecflow/templates/maui-test/templates/

# Expected:
# domain/entities/, domain/errors/
# application/services/, application/repositories/
# infrastructure/engines/
# presentation/views/
# (minimal files in other/)
```

### Manual Verification (5 minutes)

```bash
# Check classification summary
cat /tmp/template-create-output.log | grep "Classification Summary" -A10

# Expected output:
# Template Classification Summary:
#   LayerClassificationStrategy: 12 (80.0%)
#   PatternClassificationStrategy: 2 (13.3%)
#   Fallback: 1 (6.7%)
```

---

## Edge Cases

### 1. Missing Layer Information
**Scenario**: AI didn't provide layer for some files
**Expected**: Fall back to pattern-based classification
**Test**: `test_pattern_classification_fallback()`

### 2. Unknown Pattern
**Scenario**: File doesn't match any known pattern (Repository, Service, etc.)
**Expected**: Use parent directory name as pattern
**Test**: `test_unknown_pattern_uses_parent_dir()`

### 3. High Fallback Rate
**Scenario**: >20% of files go to `other/`
**Expected**: Display prominent warning to user
**Test**: `test_high_fallback_rate_warning()`

### 4. Ambiguous Patterns
**Scenario**: File matches multiple patterns (e.g., "UserRepositoryService.cs")
**Expected**: Use first match (Repository takes precedence)
**Test**: `test_ambiguous_pattern_first_match()`

---

## Success Metrics

### Before Fix
- ✅ Classification accuracy: ~0% (all files in `other/`)
- ❌ Fallback rate: 100%
- ❌ User visibility: None (silent failure)
- ❌ SOLID score: 28/50

### After Fix
- ✅ Classification accuracy: >80%
- ✅ Fallback rate: <20%
- ✅ User visibility: Classification summary + warnings
- ✅ SOLID score: 42/50 (+50% improvement)

### Quality Gates
- [ ] Test coverage ≥90% for `path_resolver.py`
- [ ] SOLID score ≥42/50
- [ ] Fallback rate <20% on test .NET MAUI project
- [ ] All existing tests still pass (backward compatibility)

---

## Risk Assessment

### Risk 1: Breaking Existing Templates
**Likelihood**: Medium (40%)
**Impact**: High (users' existing templates break)
**Mitigation**:
- Run tests against existing reference templates
- Add version field to templates
- Document structure changes in release notes

### Risk 2: Over-Classification
**Likelihood**: Low (15%)
**Impact**: Medium (files in wrong directories)
**Mitigation**:
- Comprehensive unit tests for classification logic
- Integration test with real project
- Fallback to `other/` when confidence low

### Risk 3: Pattern Recognition Failures
**Likelihood**: Low (10%)
**Impact**: Low (files in `other/` but with warning)
**Mitigation**:
- Explicit fallback rules
- User warnings when classification fails
- Can add more patterns later (extensible design)

---

## Acceptance Criteria Summary

### Functional Requirements
- [ ] **AC1**: Files organized by layer (domain, application, infrastructure, presentation)
- [ ] **AC2**: Sub-organized by pattern (repositories, services, entities, views)
- [ ] **AC3**: Uses `example_file.layer` as primary source
- [ ] **AC4**: Pattern-based fallback when layer missing
- [ ] **AC5**: `other/` only for unclassifiable files

### Quality Requirements
- [ ] **AC6**: Warning when >20% fallback rate
- [ ] **AC7**: Classification summary printed
- [ ] **AC8**: SOLID score ≥42/50
- [ ] **AC9**: Fallback rate <20%
- [ ] **AC10**: Test coverage ≥90%

### Documentation Requirements
- [ ] **AC11**: Code comments explain classification logic
- [ ] **AC12**: README in `templates/` explains structure
- [ ] **AC13**: CLAUDE.md documents template organization

---

## Timeline

**Total Estimated Time**: 50-65 minutes

### Implementation (30-45 min)
- ✅ Step 1: Create `path_resolver.py` (15 min)
- ✅ Step 2: Update `template_generator.py` (10 min)
- ✅ Step 3: Write tests (15 min)

### Testing (20 min)
- ✅ Unit tests (10 min)
- ✅ Integration test (5 min)
- ✅ Manual verification (5 min)

### Documentation (optional)
- Update README in templates/ (5 min)
- Add comments to classification logic (5 min)

---

## Dependencies

**Blockers**: None (can start immediately)

**Related Tasks**:
- TASK-C7A9: Agent metadata in CLAUDE.md (independent)
- TASK-PHASE-7.5-SIMPLE: Simplified agent enhancement (independent)

**Depends On**: None

---

## Related Documents

- **Architectural Review**: See architectural-reviewer agent output above (complete SOLID analysis)
- **Original Issue**: User report of templates in `other/` directory
- **Code Location**: `installer/global/lib/template_generator/template_generator.py:392-421`

---

## Implementation Notes

### Minimal Changes Philosophy

This task makes ONLY these changes:
1. Create `path_resolver.py` (new file, no impact on existing code)
2. Update `_infer_template_path()` in `template_generator.py` (10 lines)
3. Add classification summary printing (5 lines)

**No other changes** to:
- AI analysis logic (already working correctly)
- Agent generation (unaffected)
- Orchestrator workflow (unaffected)
- Other template generation logic (unaffected)

### Backward Compatibility

**Reading Old Templates**: ✅ Fully supported
- Can read templates organized by `other/`
- Can read templates organized by layer
- Format detection automatic

**Migration**: Optional (existing templates work as-is)

---

## Next Steps

After task creation:
1. **Review**: Review architectural analysis
2. **Implement**: `/task-work TASK-TMPL-CE54`
3. **Test**: Verify on .NET MAUI project
4. **Complete**: `/task-complete TASK-TMPL-CE54`

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-20
**Architectural Review**: COMPLETED (Score: 52/100 → 42/100 after fix)
**Complexity**: 4/10 (Simple refactoring with clear specifications)
**Priority**: HIGH (affects user-facing template quality)
