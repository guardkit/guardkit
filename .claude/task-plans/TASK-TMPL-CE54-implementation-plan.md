# Implementation Plan: TASK-TMPL-CE54

## Overview
Fix template directory classification to use AI-provided layer information instead of unreliable string matching.

## Complexity Evaluation
- **Score**: 4/10 (Simple)
- **File Complexity**: 1.5/3 (3 files: 1 new, 1 modified, 1 test)
- **Pattern Familiarity**: 0.5/2 (Strategy pattern - well known)
- **Risk Level**: 1.0/3 (Low risk - new code with fallbacks)
- **Dependencies**: 1.0/2 (No new dependencies)
- **Review Mode**: QUICK_OPTIONAL

## Files to Create/Modify

### 1. Create: `installer/global/lib/template_generator/path_resolver.py`
**Lines**: ~200
**Purpose**: Strategy pattern implementation for template path resolution

**Components**:
- `ClassificationStrategy` protocol (typing.Protocol)
- `LayerClassificationStrategy` - Uses `example_file.layer` (PRIMARY)
- `PatternClassificationStrategy` - Infers from filename patterns (FALLBACK)
- `TemplatePathResolver` - Orchestrator with statistics tracking

**Key Methods**:
- `LayerClassificationStrategy.classify(example_file, analysis) -> Optional[str]`
- `LayerClassificationStrategy._infer_pattern(file_path) -> str`
- `TemplatePathResolver.resolve(example_file, analysis) -> str`
- `TemplatePathResolver.get_classification_summary() -> str`

### 2. Modify: `installer/global/lib/template_generator/template_generator.py`
**Lines Changed**: ~15
**Changes**:
1. Import `TemplatePathResolver` (line ~10)
2. Add `self.path_resolver = TemplatePathResolver()` to `__init__` (line ~70)
3. Replace `_infer_template_path()` implementation (lines 392-421)
4. Add classification summary printing in `generate()` method

### 3. Create: `tests/lib/template_generator/test_path_resolver.py`
**Lines**: ~200
**Purpose**: Comprehensive unit tests for path resolution

**Test Cases**:
- Test layer classification with Repository pattern
- Test layer classification with Service pattern
- Test layer classification with View pattern
- Test pattern-based fallback when layer missing
- Test chain of responsibility resolution
- Test fallback to 'other/' with warning
- Test classification summary generation
- Test high fallback rate warning (>20%)
- Test ambiguous pattern resolution

## Implementation Steps

### Step 1: Create `path_resolver.py` (15 minutes)

**Pattern Mappings**:
```python
PATTERN_MAPPINGS = [
    ('Repository', 'repositories'),
    ('Service', 'services'),
    ('Engine', 'engines'),
    ('View', 'views'),
    ('ViewModel', 'viewmodels'),
    ('Entity', 'entities'),
    ('Model', 'models'),
    ('Error', 'errors'),
    ('Controller', 'controllers'),
    ('Handler', 'handlers'),
]
```

**Classification Logic Flow**:
1. Try `LayerClassificationStrategy`:
   - Check if `example_file.layer` exists
   - Infer pattern from filename (e.g., "Repository" → "repositories")
   - Return `templates/{layer}/{pattern}/{filename}.template`
2. Try `PatternClassificationStrategy`:
   - Infer layer from filename pattern
   - Repository/Service → application layer
   - Entity/Model → domain layer
   - View/ViewModel → presentation layer
   - Engine → infrastructure layer
3. Fallback to `templates/other/`:
   - Add warning to warnings list
   - Track in statistics

### Step 2: Update `template_generator.py` (10 minutes)

**Import Addition**:
```python
from .path_resolver import TemplatePathResolver
```

**Initialization**:
```python
def __init__(self, analysis: CodebaseAnalysis, ai_client: Optional[AIClient] = None):
    # ... existing code ...
    self.path_resolver = TemplatePathResolver()
```

**Method Replacement**:
```python
def _infer_template_path(self, example_file: ExampleFile) -> str:
    """Use resolver for path inference."""
    return self.path_resolver.resolve(example_file, self.analysis)
```

**Summary Printing** (in `generate()` method):
```python
# After template generation
print("\n" + self.path_resolver.get_classification_summary())

# Print warnings if high fallback rate
if self.path_resolver.warnings:
    print(f"\n⚠️  Classification warnings ({len(self.path_resolver.warnings)}):")
    for warning in self.path_resolver.warnings[:5]:
        print(f"  {warning}")
    if len(self.path_resolver.warnings) > 5:
        print(f"  ... and {len(self.path_resolver.warnings) - 5} more")
```

### Step 3: Write Tests (15 minutes)

**Test Structure**:
```python
import pytest
from installer.global.lib.template_generator.path_resolver import (
    LayerClassificationStrategy,
    PatternClassificationStrategy,
    TemplatePathResolver
)
from installer.global.lib.codebase_analyzer.models import ExampleFile, CodebaseAnalysis

@pytest.fixture
def example_file_with_layer():
    return ExampleFile(
        path="src/Repositories/UserRepository.cs",
        purpose="User data access",
        layer="application"
    )

def test_layer_classification_with_repository(example_file_with_layer):
    strategy = LayerClassificationStrategy()
    result = strategy.classify(example_file_with_layer, None)
    assert result == "templates/application/repositories/UserRepository.cs.template"
```

## Testing Strategy

### Unit Tests (10 minutes)
```bash
pytest tests/lib/template_generator/test_path_resolver.py -v --cov=installer/global/lib/template_generator/path_resolver.py
```

**Expected Coverage**: ≥90%

### Integration Test (5 minutes)
Test with actual template generation to verify:
- Classification summary displays
- Files organized by layer/pattern
- Warnings display when fallback rate high

### Manual Verification (5 minutes)
Verify directory structure matches expected:
```
templates/
├── domain/
│   ├── entities/
│   └── errors/
├── application/
│   ├── services/
│   └── repositories/
├── infrastructure/
│   └── engines/
└── presentation/
    └── views/
```

## Quality Gates

### Compilation
- All Python files must parse without syntax errors
- Imports must resolve correctly

### Tests
- All new tests must pass
- Coverage ≥90% for path_resolver.py
- All existing tests must still pass (backward compatibility)

### Code Review
- SOLID score improves from 28/50 to ≥42/50
- Single Responsibility: Each strategy handles one classification method
- Open/Closed: New strategies can be added without modifying resolver
- Dependency Inversion: Resolver depends on Strategy protocol, not concrete implementations

## Acceptance Criteria Mapping

- **AC1-AC2**: Implemented via LayerClassificationStrategy and pattern inference
- **AC3**: Primary strategy uses example_file.layer
- **AC4**: PatternClassificationStrategy provides fallback
- **AC5**: Fallback to 'other/' only when all strategies fail
- **AC6**: Warning printed when fallback rate >20%
- **AC7**: Classification summary printed after generation
- **AC8**: SOLID improvements via Strategy pattern
- **AC9**: Achieved through accurate layer-based classification
- **AC10**: Test coverage target ≥90%

## Risks and Mitigations

### Risk 1: Breaking Existing Templates
**Mitigation**:
- No changes to template reading logic
- Only affects new template generation
- Existing templates work as-is

### Risk 2: Pattern Recognition Failures
**Mitigation**:
- Explicit fallback chain
- Use parent directory name as last resort before 'other/'
- Track and report fallback statistics

### Risk 3: Performance Impact
**Mitigation**:
- Strategy pattern is O(n) where n = number of strategies (small)
- No external API calls
- Minimal performance impact expected

## Estimated Timeline

- **Implementation**: 40 minutes
  - path_resolver.py: 15 minutes
  - template_generator.py: 10 minutes
  - test_path_resolver.py: 15 minutes
- **Testing**: 20 minutes
  - Unit tests: 10 minutes
  - Integration: 5 minutes
  - Manual verification: 5 minutes
- **Total**: 60 minutes

## Success Metrics

### Before Fix
- Classification accuracy: ~0%
- Fallback rate: 100%
- SOLID score: 28/50

### After Fix
- Classification accuracy: ≥80%
- Fallback rate: ≤20%
- SOLID score: ≥42/50
- Test coverage: ≥90%

## Dependencies

- None (self-contained implementation)
- Uses existing ExampleFile.layer attribute
- No new external dependencies required
