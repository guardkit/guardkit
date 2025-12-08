# TASK-FIX-40B4: Improve Layer Classification for JavaScript Projects

**Task ID**: TASK-FIX-40B4
**Phase**: 2 (Implementation Planning)
**Complexity**: 5/10 (Medium)
**Stack**: Python

## Problem Statement

The `/template-create` command currently misclassifies 80% of JavaScript files as "other" instead of recognizing common architectural layer patterns. This results in poor template generation quality for JavaScript projects.

### Current Failures
```
src/lib/query.js → classified as "other" (should be "infrastructure/data-access")
src/lib/firestore/sessions.js → classified as "other" (should be "data-access/repository")
src/lib/firestore-mock/firebase.js → classified as "other" (should be "testing/mocks")
upload/update-sessions-weather.js → classified as "other" (should be "scripts/utilities")
upload/upload-sessions.js → classified as "other" (should be "scripts/utilities")
```

## Architecture Analysis

### Current Layer Classification System

**Location**: `/installer/global/lib/template_generator/pattern_matcher.py`

**Current Implementation**:
```python
LAYER_PATTERNS = {
    'Domain': ['/Core/', '/Domain/', 'Domain.', '.Core.', 'core/', 'domain/'],
    'UseCases': ['/UseCases/', '/Application/', 'UseCases.', 'Application.', 'usecases/', 'application/'],
    'Web': ['/Web/', '/Api/', '/Endpoints/', 'Web.', 'Api.', 'Endpoints.', 'web/', 'api/', 'endpoints/'],
    'Infrastructure': ['/Infrastructure/', '/Persistence/', 'Infrastructure.', 'Persistence.', 'infrastructure/', 'persistence/']
}
```

**Problems**:
1. **C#/Java-centric**: Designed for capitalized namespaces (`.Core.`, `Domain.`)
2. **No JavaScript support**: Missing common JS directories (`lib/`, `components/`, `stores/`)
3. **Underscore/hyphen blindness**: Can't distinguish `firestore/` vs `firestore-mock/`
4. **No suffix analysis**: Doesn't recognize `__mocks__/` or `*.test.js` patterns
5. **No context awareness**: Treats `lib/query.js` as "other" without analyzing file purpose

### Integration Points

**Response Parser** (`installer/global/lib/codebase_analyzer/response_parser.py`):
- Parses AI-generated layer classification in `example_files` section
- Accepts `layer` field: `"layer": "Domain"`, `"layer": "other"`, etc.
- No fallback for unclassified files

**Prompt Builder** (`installer/global/lib/codebase_analyzer/prompt_builder.py`):
- Provides layer examples (Domain, Application, Infrastructure, Presentation, Testing)
- Uses `CRUDPatternMatcher.identify_layer()` indirectly
- No JavaScript-specific guidance

**Pattern Matcher** (`installer/global/lib/template_generator/pattern_matcher.py`):
- Core layer detection via `identify_layer()` static method
- Returns `Optional[str]` (layer name or None)
- Used by `OperationExtractor.extract_operations_by_layer()`

## Solution Design

### 1. Extend LAYER_PATTERNS for JavaScript

Create a JavaScript-aware pattern set with:
- Directory structure patterns (lib/, components/, stores/, etc.)
- Suffix patterns (\_\_mocks\_\_, .test, .mock)
- Technology-aware patterns (firestore/, api/, etc.)

### 2. Implement LayerClassificationStrategy

Create a new abstraction layer to support multiple classification strategies:
- **JavaScript Strategy**: Handles JS/TS directory patterns
- **C# Strategy**: Current behavior (minimal changes)
- **Python Strategy**: FastAPI, Django patterns
- **Fallback Strategy**: Pattern matching → confidence score

### 3. Add Confidence Scoring

Each classification returns:
```python
ClassificationResult = {
    "layer": str,           # "data-access", "infrastructure", "scripts", etc.
    "confidence": float,    # 0.0 to 1.0
    "reason": str,         # Why this layer was assigned
    "patterns_matched": List[str]  # Which patterns matched
}
```

### 4. Enhanced Architecture Support

Map JavaScript patterns to standard architectural layers:

| JS Directory | Standard Layer | Confidence | Patterns |
|---|---|---|---|
| `lib/` | `infrastructure/` or `utilities/` | HIGH | Contains utility functions |
| `src/lib/firestore/` | `data-access/` | HIGH | Database operations |
| `src/lib/firestore-mock/` | `testing/` | HIGH | Contains "mock" suffix |
| `__mocks__/` | `testing/` | CRITICAL | Jest mock convention |
| `upload/` | `scripts/` | HIGH | Contains "upload" verb |
| `scripts/` | `scripts/` | CRITICAL | Standard convention |
| `bin/` | `scripts/` | CRITICAL | Executable script directory |
| `components/` | `presentation/` | HIGH | UI components |
| `routes/` | `routes/` | CRITICAL | Routing logic |
| `pages/` | `routes/` | CRITICAL | Page routes |
| `stores/` | `state/` | HIGH | State management |
| `state/` | `state/` | HIGH | State management |
| `hooks/` | `infrastructure/` | HIGH | Reusable logic |
| `utils/` | `utilities/` | HIGH | Helper functions |
| `contexts/` | `state/` | HIGH | React contexts |

## Implementation Plan

### Phase 1: Core Implementation (4 hours)

**Step 1.1**: Create `LayerClassificationStrategy` abstraction
- **File**: `/installer/global/lib/template_generator/layer_classifier.py` (NEW)
- **Responsibility**: Abstract interface for language-specific classification
- **Pattern**: Strategy pattern with factory

```python
class LayerClassificationStrategy(ABC):
    """Abstract base for language-specific layer classification."""

    @abstractmethod
    def classify(self, template: CodeTemplate) -> ClassificationResult:
        """Classify a file into an architectural layer."""
        pass

    @abstractmethod
    def supports_language(self, language: str) -> bool:
        """Check if strategy handles this language."""
        pass

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """JavaScript/TypeScript layer classification."""

    # Ordered patterns (first match wins)
    PATTERNS = {
        'testing': [
            r'(__mocks__|\.mock|\.test|\.spec)',
            r'/(mock|mocks|test|tests|__tests__)/',
        ],
        'scripts': [
            r'/(scripts|bin|upload|tasks)/',
            r'(script|upload|task|cli)\.js$',
        ],
        'data-access': [
            r'/(firestore|api|data|database|repository|repositories)/',
            r'(query|mutation|model|schema)\.js$',
        ],
        'presentation': [
            r'/(components|screens|pages|views)/',
            r'Component\.js$',
        ],
        'state': [
            r'/(store|stores|state|context|contexts)/',
        ],
        'routes': [
            r'/(routes|pages|routes)/',
        ],
        'utilities': [
            r'/(utils|helpers|lib|services)/',
        ],
    }

class PythonLayerClassifier(LayerClassificationStrategy):
    """Python layer classification (FastAPI, Django, etc.)."""
    pass

class CSharpLayerClassifier(LayerClassificationStrategy):
    """C# layer classification (existing pattern_matcher behavior)."""
    pass
```

**Step 1.2**: Implement JavaScript classifier
- Regex-based pattern matching with priority ordering
- File suffix analysis (e.g., `.test.js`, `.mock.ts`)
- Directory depth consideration

**Step 1.3**: Create factory function
- `get_classifier(language: str) -> LayerClassificationStrategy`
- Defaults to `GenericLayerClassifier` for unknown languages

### Phase 2: Integration (3 hours)

**Step 2.1**: Update `CRUDPatternMatcher`
- Replace `identify_layer()` implementation
- Inject classifier via constructor
- Maintain backward compatibility

```python
class CRUDPatternMatcher:
    def __init__(self, classifier: LayerClassificationStrategy = None):
        self.classifier = classifier or get_classifier("generic")

    @staticmethod
    def identify_layer(template: CodeTemplate) -> Optional[str]:
        """Legacy interface - delegates to classifier."""
        classifier = get_classifier(template.language or "generic")
        result = classifier.classify(template)
        return result.layer if result else None
```

**Step 2.2**: Update response_parser.py
- Accept `confidence` in layer classification
- Log classifications with confidence scores
- Handle None returns gracefully

**Step 2.3**: Update prompt_builder.py
- Add JavaScript layer examples to guidance
- Include firestore/, components/, stores/ patterns
- Emphasize suffix patterns (__mocks__, .test)

### Phase 3: Testing (2 hours)

**Step 3.1**: Create test file
- **File**: `/tests/lib/template_generator/test_layer_classifier.py` (NEW)
- Test each JavaScript pattern
- Test confidence scoring
- Test priority ordering (first match wins)

```python
class TestJavaScriptLayerClassifier:
    """Test JavaScript layer classification."""

    def test_firestore_data_access(self):
        """Test firestore/ directory classification."""
        template = CodeTemplate(
            name="sessions.js",
            original_path="src/lib/firestore/sessions.js",
            language="JavaScript"
        )
        classifier = JavaScriptLayerClassifier()
        result = classifier.classify(template)

        assert result.layer == "data-access"
        assert result.confidence > 0.85
        assert "firestore" in result.patterns_matched

    def test_mock_testing_layer(self):
        """Test __mocks__ directory classification."""
        template = CodeTemplate(
            name="firebase.js",
            original_path="src/lib/firestore-mock/firebase.js",
            language="JavaScript"
        )
        result = classifier.classify(template)
        assert result.layer == "testing"
        assert result.confidence >= 0.95

    def test_upload_scripts(self):
        """Test scripts/ directory classification."""
        template = CodeTemplate(
            name="upload-sessions.js",
            original_path="upload/upload-sessions.js",
            language="JavaScript"
        )
        result = classifier.classify(template)
        assert result.layer == "scripts"

    def test_lib_fallback_to_utilities(self):
        """Test lib/ falls back to utilities when no other patterns match."""
        template = CodeTemplate(
            name="query.js",
            original_path="src/lib/query.js",
            language="JavaScript"
        )
        result = classifier.classify(template)
        # Should be utilities or infrastructure, not "other"
        assert result.layer in ["utilities", "infrastructure"]
```

**Step 3.2**: Test pattern priority
- Verify `testing` checked before `utilities`
- Verify `firestore/` matches before generic `lib/`

**Step 3.3**: Test C# backward compatibility
- Verify existing C# patterns still work
- Verify no regression in other tests

### Phase 4: Documentation (1 hour)

**Step 4.1**: Add docstrings
- `LayerClassificationStrategy` interface documentation
- `JavaScriptLayerClassifier` implementation notes
- Pattern ordering rationale

**Step 4.2**: Update CLAUDE.md
- Add JavaScript layer classification to capabilities
- Document confidence scoring
- Link to pattern matcher for advanced usage

## Files to Create/Modify

### Create (NEW)
1. `/installer/global/lib/template_generator/layer_classifier.py` - Strategy implementation
2. `/tests/lib/template_generator/test_layer_classifier.py` - Comprehensive tests

### Modify (EXISTING)
1. `/installer/global/lib/template_generator/pattern_matcher.py` - Integrate classifier, maintain backward compatibility
2. `/installer/global/lib/codebase_analyzer/response_parser.py` - Handle confidence scores
3. `/installer/global/lib/codebase_analyzer/prompt_builder.py` - Add JavaScript guidance
4. `/CLAUDE.md` - Document JavaScript classification capability

## Success Criteria

### Quantitative
- [ ] JavaScript file misclassification reduced from 80% to <30%
- [ ] Test coverage: 100% of new classification code
- [ ] All C# patterns still work (zero regression)

### Qualitative
- [ ] No breaking changes to public API
- [ ] Backward compatible with existing code
- [ ] Confidence scores guide future enhancements

### Test Coverage
- [ ] All JavaScript patterns tested individually
- [ ] Priority ordering validated
- [ ] Edge cases: nested directories, compound names
- [ ] Backward compatibility: C# patterns unchanged

## Risk Assessment

**LOW RISK**:
- Using strategy pattern isolates JavaScript logic
- Backward compatible interface
- Comprehensive tests prevent regression

**DEPENDENCIES**:
- `CodeTemplate` model must have `language` field
- Must not break existing CRUD pattern matching

## Architecture Decisions

### Decision 1: Strategy Pattern
**Why**: Different languages need different rules. Strategy pattern allows:
- Clean separation of concerns
- Easy to add Python, Go, Rust classifiers later
- Testable in isolation

### Decision 2: Regex-based Patterns
**Why**:
- Fast, no AI/ML required
- Deterministic and testable
- Can achieve 95%+ accuracy for structured directories
- Fallback to AI for edge cases

### Decision 3: Confidence Scoring
**Why**:
- Guides humans when classification uncertain
- Enables future AI refinement
- Transparent classification logic

### Decision 4: First-Match-Wins Priority
**Why**:
- `testing` patterns checked first (most specific)
- `scripts` patterns checked next
- `lib/` patterns checked last (most generic)
- Prevents false positives (e.g., `firestore-mock/` → testing, not data-access)

## Component Structure

```
layer_classifier.py
├── ClassificationResult (dataclass)
├── LayerClassificationStrategy (ABC)
├── JavaScriptLayerClassifier (implements Strategy)
├── PythonLayerClassifier (implements Strategy)
├── CSharpLayerClassifier (implements Strategy)
├── GenericLayerClassifier (implements Strategy)
└── get_classifier(language: str) -> LayerClassificationStrategy (factory)

pattern_matcher.py (modified)
├── CRUDPatternMatcher
│   ├── __init__(classifier: LayerClassificationStrategy = None)
│   ├── identify_layer(template) [delegates to classifier]
│   └── [other methods unchanged]
└── [legacy LAYER_PATTERNS kept for backward compatibility]
```

## Testing Strategy

### Unit Tests
- **File**: `test_layer_classifier.py`
- **Coverage**: Each pattern, priority ordering, edge cases
- **Examples**:
  - `test_firestore_data_access()` - High confidence for firestore/
  - `test_mock_testing_layer()` - Highest confidence for mocks/
  - `test_lib_fallback_utilities()` - Fallback behavior
  - `test_priority_ordering()` - Verify testing > scripts > data-access
  - `test_c_sharp_backward_compatibility()` - Zero regression

### Integration Tests
- Verify with actual template_generator workflow
- Test with example JavaScript projects
- Ensure response_parser handles confidence scores

### Manual Testing
- Run `/template-create` on guardkit codebase
- Run `/template-create` on JavaScript project (if available)
- Verify layer assignments match expected values

## Confidence Levels

| Layer | Confidence | Pattern |
|---|---|---|
| Testing | 0.95+ | `__mocks__`, `.test.js`, `firestore-mock` |
| Scripts | 0.9+ | `/scripts/`, `/bin/`, `/upload/` |
| Data-Access | 0.85+ | `/firestore/`, `/api/`, `/data/`, `query.js` |
| Presentation | 0.85+ | `/components/`, `/screens/`, `/views/` |
| State | 0.9+ | `/store/`, `/stores/`, `/state/` |
| Routes | 0.95+ | `/routes/`, `/pages/` |
| Utilities | 0.75+ | `/utils/`, `/helpers/`, `/lib/` (fallback) |

## Related Patterns

**Dependency Injection**: Classifier injected into CRUDPatternMatcher
**Factory Pattern**: `get_classifier()` creates appropriate instance
**Strategy Pattern**: Language-specific implementations
**Composition**: CRUDPatternMatcher composes classifier

## Rollback Plan

If issues arise:
1. Revert `pattern_matcher.py` changes (keep classifier implementation)
2. Use legacy `identify_layer()` implementation
3. No data loss - only classification logic changes

## Future Enhancements

1. **AI Refinement**: Use claude-provided layer + confidence to train better patterns
2. **Python Support**: Add FastAPI/Django layer patterns
3. **Learning System**: Log actual layers used, improve confidence scores
4. **Per-Project Tuning**: Let users define custom layer patterns per project
5. **Visualization**: Show classification scores in template preview

## Estimated Timeline

| Phase | Tasks | Duration | Dependencies |
|---|---|---|---|
| 1 | Core implementation + strategy | 4 hours | None |
| 2 | Integration + updates | 3 hours | Phase 1 |
| 3 | Comprehensive testing | 2 hours | Phase 1, 2 |
| 4 | Documentation | 1 hour | Phases 1-3 |
| **Total** | | **10 hours** | |

**Includes**:
- Code implementation and testing
- Documentation and examples
- Backward compatibility validation

**Excludes**:
- Python/C# pattern extensions (future enhancement)
- ML-based learning system (future enhancement)
