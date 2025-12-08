# TASK-FIX-40B4: Quick Reference Guide

## Problem in One Sentence
JavaScript files are 80% misclassified as "other" because the pattern matcher only understands C# namespaces, not JavaScript directories.

## Solution in One Sentence
Add a `LayerClassificationStrategy` abstraction with language-specific implementations, starting with `JavaScriptLayerClassifier`.

---

## Files to Create

### 1. `/installer/global/lib/template_generator/layer_classifier.py`

**What it does**: Defines layer classification strategy for different languages

**Key components**:
```python
@dataclass
class ClassificationResult:
    layer: str           # "testing", "data-access", etc.
    confidence: float    # 0.75 to 0.95
    reason: str         # Why this classification
    patterns_matched: List[str]

class LayerClassificationStrategy(ABC):
    def classify(template: CodeTemplate) -> Optional[ClassificationResult]
    def supports_language(language: str) -> bool

class JavaScriptLayerClassifier(LayerClassificationStrategy):
    # 7 layers with regex patterns
    # Priority: testing > scripts > routes > data-access > ...

class PythonLayerClassifier(LayerClassificationStrategy): pass
class CSharpLayerClassifier(LayerClassificationStrategy): pass
class GenericLayerClassifier(LayerClassificationStrategy): pass

def get_classifier(language: Optional[str]) -> LayerClassificationStrategy:
    # Factory function for classifier selection
```

**JavaScript patterns (priority order)**:
```
testing:      __mocks__/, .test.js, .spec.js, -mock/ (confidence: 0.95)
scripts:      /scripts/, /bin/, /upload/, /tasks/ (confidence: 0.90)
routes:       /routes/, /pages/ (confidence: 0.95)
state:        /store/, /state/, /context/ (confidence: 0.90)
data-access:  /firestore/, /api/, /data/ (confidence: 0.85)
presentation: /components/, /screens/ (confidence: 0.85)
utilities:    /utils/, /lib/ (confidence: 0.75, fallback)
```

---

### 2. `/tests/lib/template_generator/test_layer_classifier.py`

**What it does**: Comprehensive unit tests for classification logic

**Test cases**:
```python
def test_firestore_data_access()        # src/lib/firestore/ → data-access
def test_firestore_mock_testing()       # src/lib/firestore-mock/ → testing (mock suffix)
def test_jest_mocks_testing()           # src/__mocks__/ → testing
def test_test_suffix_testing()          # src/lib/query.test.js → testing
def test_upload_scripts()               # upload/ → scripts
def test_scripts_directory()            # scripts/ → scripts
def test_components_presentation()      # components/ → presentation
def test_stores_state()                 # stores/ → state
def test_lib_fallback_utilities()       # lib/ → utilities
def test_priority_ordering()            # testing checked before utilities
def test_confidence_scoring()           # verify confidence levels
def test_csharp_backward_compatibility() # C# patterns still work
def test_javascript_language_variants()  # js, ts, jsx, tsx all work
def test_error_handling()               # None/invalid inputs handled
```

---

## Files to Modify

### 1. `/installer/global/lib/template_generator/pattern_matcher.py`

**Changes**:
```python
class CRUDPatternMatcher:
    def __init__(self, classifier: LayerClassificationStrategy = None):
        self.classifier = classifier or get_classifier("generic")

    @staticmethod
    def identify_layer(template: CodeTemplate) -> Optional[str]:
        """Legacy interface - now delegates to classifier."""
        classifier = get_classifier(template.language or "generic")
        result = classifier.classify(template)
        return result.layer if result else None
```

**Keep existing**:
- `CRUD_PATTERNS` (unchanged)
- `identify_crud_operation()` (unchanged)
- `identify_entity()` (unchanged)
- Legacy `LAYER_PATTERNS` (for backward compatibility reference only)

---

### 2. `/installer/global/lib/codebase_analyzer/response_parser.py`

**Changes**:
```python
def _parse_example_files(self, files_data: list) -> list:
    """Parse example files, including optional confidence scores."""
    for file_data in files_data:
        ExampleFile(
            path=file_data.get("path"),
            layer=file_data.get("layer"),
            confidence=file_data.get("confidence", 1.0),  # NEW
        )
```

---

### 3. `/installer/global/lib/codebase_analyzer/prompt_builder.py`

**Changes**:
```python
# Add to example_files in prompt:
{
    "path": "src/lib/firestore/sessions.js",
    "layer": "data-access",
    "purpose": "Firebase/Firestore database operations"
},
{
    "path": "src/lib/firestore-mock/firebase.js",
    "layer": "testing",
    "purpose": "Mock implementations for testing"
},
{
    "path": "src/components/Button.js",
    "layer": "presentation",
    "purpose": "Reusable UI component"
},
{
    "path": "src/stores/SessionStore.js",
    "layer": "state",
    "purpose": "Application state management"
},
{
    "path": "upload/upload-sessions.js",
    "layer": "scripts",
    "purpose": "Executable script for data import"
},
```

---

### 4. `/CLAUDE.md`

**Add section**:
```markdown
## JavaScript Layer Classification

The system now recognizes common JavaScript project patterns:

- **data-access**: `/firestore/`, `/api/`, `/data/` directories
- **testing**: `__mocks__/`, `.test.js`, `.spec.js`, `-mock/` suffix
- **scripts**: `/scripts/`, `/bin/`, `/upload/`, `/tasks/`
- **presentation**: `/components/`, `/screens/`, `/views/`
- **state**: `/store/`, `/stores/`, `/state/`, `/contexts/`
- **routes**: `/routes/`, `/pages/`
- **utilities**: `/utils/`, `/helpers/`, `/lib/`, `/services/`

See [Layer Classification Guide](docs/guides/layer-classification.md) for details.
```

---

## Implementation Checklist

### Phase 1: Core Implementation (4 hours)
- [ ] Create `layer_classifier.py`
  - [ ] `ClassificationResult` dataclass
  - [ ] `LayerClassificationStrategy` ABC
  - [ ] `JavaScriptLayerClassifier` implementation
  - [ ] `PythonLayerClassifier` (skeleton)
  - [ ] `CSharpLayerClassifier` (wraps legacy patterns)
  - [ ] `GenericLayerClassifier`
  - [ ] `get_classifier()` factory function
  - [ ] Add comprehensive docstrings
  - [ ] Add type hints throughout

### Phase 2: Integration (3 hours)
- [ ] Update `pattern_matcher.py`
  - [ ] Add classifier dependency injection
  - [ ] Update `identify_layer()` to delegate
  - [ ] Keep legacy patterns for reference

- [ ] Update `response_parser.py`
  - [ ] Handle confidence scores in example files

- [ ] Update `prompt_builder.py`
  - [ ] Add JavaScript examples to AI prompt

- [ ] Update `CLAUDE.md`
  - [ ] Document JavaScript classification

### Phase 3: Testing (2 hours)
- [ ] Create `test_layer_classifier.py`
  - [ ] Unit tests for each JavaScript layer
  - [ ] Pattern matching tests
  - [ ] Priority ordering tests
  - [ ] Confidence scoring tests
  - [ ] Backward compatibility tests
  - [ ] Language variant tests
  - [ ] Error handling tests

- [ ] Run existing tests
  - [ ] Verify all C# tests pass (zero regression)
  - [ ] Verify all CRUD tests pass

### Phase 4: Documentation (1 hour)
- [ ] Add docstrings to all public APIs
- [ ] Update CLAUDE.md
- [ ] Create layer classification guide (optional)

---

## Key Design Decisions

| Decision | Why | Impact |
|----------|-----|--------|
| Strategy Pattern | Different languages need different rules | Clean separation, easy to extend |
| Regex-based patterns | Fast, deterministic, no AI overhead | 95%+ accuracy achievable |
| Confidence scoring | Guide humans when uncertain | Transparent classification |
| First-match-wins priority | Prevent false positives | testing checked before utilities |
| Factory function | Encapsulate classifier selection | Flexible, easy to test |

---

## Expected Test Results

```
✓ test_firestore_data_access
✓ test_firestore_mock_testing
✓ test_jest_mocks_testing
✓ test_test_suffix_testing
✓ test_upload_scripts
✓ test_scripts_directory
✓ test_components_presentation
✓ test_stores_state
✓ test_lib_fallback_utilities
✓ test_priority_ordering
✓ test_confidence_scoring
✓ test_csharp_backward_compatibility
✓ test_javascript_language_variants
✓ test_error_handling

Total: 14 tests, 100% pass rate
Coverage: 100% of new code
Regressions: 0 (all C# tests still pass)
```

---

## Before/After Example

```javascript
// BEFORE (80% misclassified as "other")
src/lib/query.js                  → "other" ❌
src/lib/firestore/sessions.js     → "other" ❌
src/lib/firestore-mock/firebase.js → "other" ❌
upload/upload-sessions.js         → "other" ❌

// AFTER (all correctly classified)
src/lib/query.js                  → "utilities" (0.75) ✓
src/lib/firestore/sessions.js     → "data-access" (0.88) ✓
src/lib/firestore-mock/firebase.js → "testing" (0.95) ✓
upload/upload-sessions.js         → "scripts" (0.92) ✓
```

---

## Pattern Matching Algorithm

```
Input: src/lib/firestore-mock/firebase.js

Step 1: Normalize path
  search_text = "src/lib/firestore-mock/firebase.js"

Step 2: Check patterns in priority order
  ├─ testing patterns
  │  └─ matches: "firestore-mock" contains "-mock" ✓
  │     → Return ClassificationResult(
  │         layer="testing",
  │         confidence=0.95,
  │         reason="Matched pattern '.*-mock.*'",
  │         patterns_matched=["-mock"]
  │       )
  │
  └─ (Stop - first match found)

Output: ClassificationResult(layer="testing", confidence=0.95)
```

---

## Confidence Levels Reference

| Layer | Confidence | Rationale |
|-------|-----------|-----------|
| testing | 0.95 | Distinctive patterns (__mocks__, .test.js) |
| routes | 0.95 | Critical architectural pattern |
| scripts | 0.90 | Standard convention |
| state | 0.90 | Common directory pattern |
| data-access | 0.85 | Fairly distinctive (firestore, api) |
| presentation | 0.85 | Clear pattern (components) |
| utilities | 0.75 | Generic fallback (lib/ is ambiguous) |

---

## Integration with Existing Code

**CRUDPatternMatcher** (existing class):
```python
# Before
result = CRUDPatternMatcher.identify_layer(template)

# After (no change to calling code!)
result = CRUDPatternMatcher.identify_layer(template)
# Internally uses classifier now, but interface unchanged
```

**OperationExtractor** (existing class):
```python
# Automatically benefits from better classification
operations_by_layer = extractor.extract_operations_by_layer(templates)
# Now correctly identifies JavaScript files in right layers
```

---

## Testing Approach

**Unit Tests** (test_layer_classifier.py):
- Isolated tests of classification logic
- No dependencies on template_generator
- Mock CodeTemplate objects
- Fast execution (<1 second)

**Integration Tests** (in existing test_template_generator.py):
- Verify with OperationExtractor
- Verify with template_generator workflow
- Ensure backward compatibility

**Manual Testing**:
- Run `/template-create` on real JavaScript projects
- Verify layer assignments match expectations
- Check confidence scores in output

---

## Common Patterns to Watch For

| Pattern | Classification | Confidence |
|---------|---|---|
| `__mocks__/` | testing | 0.95 |
| `.test.js` | testing | 0.95 |
| `.spec.ts` | testing | 0.95 |
| `-mock/` | testing | 0.95 |
| `/firestore/` | data-access | 0.88 |
| `/components/` | presentation | 0.85 |
| `/lib/` | utilities | 0.75 |
| `/scripts/` | scripts | 0.90 |
| `/upload/` | scripts | 0.90 |

---

## Error Handling

```python
# Invalid template
result = classifier.classify(None)
# Raises ClassificationError

# Unknown language
result = get_classifier("Cobol")
# Returns GenericLayerClassifier

# No patterns match
result = classifier.classify(template_with_unusual_path)
# Returns None (not classified)
```

---

## Future Enhancements

1. **Python Classifier**: Django/FastAPI patterns (skeleton exists)
2. **Go Classifier**: Add cmd/, pkg/, internal/ patterns
3. **Rust Classifier**: Add src/bin/, src/lib/ patterns
4. **ML-based Learning**: Log actual layers, train better patterns
5. **Per-project Customization**: Let users define custom patterns

---

## Quick Debugging Checklist

If classification fails:

- [ ] Check file extension (must be JS/TS/JSX/TSX)
- [ ] Check `original_path` has `/` separators (not `\`)
- [ ] Check pattern regex is correct (use `re.compile()` to test)
- [ ] Check pattern priority (testing before utilities?)
- [ ] Check confidence in valid range (0.0-1.0)
- [ ] Check C# patterns unchanged (backward compatibility)

---

## Documentation Links

- **Implementation Plan**: `TASK-FIX-40B4-implementation-plan.md`
- **Design Summary**: `TASK-FIX-40B4-design-summary.md`
- **Python Patterns**: `TASK-FIX-40B4-python-patterns-reference.md`
- **Executive Summary**: `TASK-FIX-40B4-EXECUTIVE-SUMMARY.txt`

---

## Success Criteria

- [ ] JavaScript misclassification reduced from 80% to <30%
- [ ] All 14+ test cases pass
- [ ] 100% test coverage of new code
- [ ] All C# tests still pass (zero regression)
- [ ] No breaking API changes
- [ ] Clear, documented code

Ready to implement!
