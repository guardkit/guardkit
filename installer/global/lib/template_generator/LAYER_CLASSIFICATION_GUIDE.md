# Layer Classification Guide

TASK-FIX-40B4: Improved layer classification for template organization with JavaScript-specific and generic patterns.

## Overview

The layer classification system uses a **Strategy pattern** to classify code files into architectural layers. This enables better organization of generated templates and improves template discoverability.

### Key Features

- **Language-specific classifiers**: JavaScript/TypeScript folder conventions
- **Generic fallback**: Cross-language patterns for all other languages
- **Confidence scoring**: Quality metrics for classification reliability
- **Chain of responsibility**: Multiple strategies with graceful fallback

## Architecture

```
LayerClassificationOrchestrator (main coordinator)
├── JavaScriptLayerClassifier (JS/TS specific, 0.85-0.95 confidence)
├── GenericLayerClassifier (fallback, 0.60-0.70 confidence)
└── TemplatePathResolver (integration point)
    ├── AIProvidedLayerStrategy (AI-provided layer info, highest priority)
    ├── LayerClassificationOrchestratorStrategy (uses orchestrator)
    ├── PatternClassificationStrategy (legacy fallback)
    └── templates/other/ (final fallback)
```

## Usage

### Basic Classification

```python
from lib.template_generator import LayerClassificationOrchestrator, ClassificationResult
from lib.codebase_analyzer.models import ExampleFile, CodebaseAnalysis

# Create orchestrator
orchestrator = LayerClassificationOrchestrator()

# Classify a file
example_file = ExampleFile(
    path="src/components/Button.jsx",
    purpose="Button component",
    layer=None,
    patterns_used=[],
    key_concepts=[]
)

result = orchestrator.classify(example_file, analysis)

if result:
    print(f"Layer: {result.layer}")              # 'presentation'
    print(f"Confidence: {result.confidence:.2%}") # 85%
    print(f"Strategy: {result.strategy_used}")    # 'JavaScriptLayerClassifier'
    print(f"Pattern: {result.pattern_matched}")   # '/components/'
```

### Custom Strategies

```python
from lib.template_generator.layer_classifier import (
    LayerClassificationStrategy,
    LayerClassificationOrchestrator
)

class CustomLayerClassifier(LayerClassificationStrategy):
    """Your custom classifier implementation."""

    def classify(self, example_file, analysis):
        # Your logic here
        if some_custom_condition(example_file):
            return ClassificationResult(
                layer='custom_layer',
                confidence=0.95,
                strategy_used=self.__class__.__name__
            )
        return None

    def supports_language(self, language):
        return language.lower() == 'yourlangage'

# Use custom classifier with orchestrator
orchestrator = LayerClassificationOrchestrator(
    strategies=[
        CustomLayerClassifier(),
        JavaScriptLayerClassifier(),
        GenericLayerClassifier(),
    ]
)
```

### Integration with TemplatePathResolver

```python
from lib.template_generator.path_resolver import TemplatePathResolver

# Create resolver with default strategies
resolver = TemplatePathResolver()

# Use in template generation pipeline
template_path = resolver.resolve(example_file, analysis)
# Returns: 'templates/presentation/components/Button.jsx.template'
```

## JavaScript Layer Patterns

### Testing Layer (0.95 confidence)
- `/__mocks__/` - Mock data
- `/__tests__/` - Test files
- `/*.test.js(x|jsx|ts|tsx)` - Jest test files
- `/*.spec.js(x|jsx|ts|tsx)` - Jasmine/Mocha spec files
- `/-mock/` - Custom mock folder pattern

**Examples**:
- `src/__tests__/Button.spec.js` → testing
- `src/utils/__mocks__/helpers.js` → testing

### Scripts/Tooling Layer (0.90 confidence)
- `/scripts/` - Build and utility scripts
- `/bin/` - Executable scripts
- `/upload/` - File upload handlers

**Examples**:
- `src/scripts/build.js` → scripts
- `bin/cli.js` → scripts

### Routes/Pages Layer (0.95 confidence)
- `/routes/` - Route definitions
- `/pages/` - Page components

**Examples**:
- `src/routes/home.js` → routes
- `src/pages/Dashboard.jsx` → routes

### State Management Layer (0.90 confidence)
- `/store/` - Redux/Vuex stores
- `/state/` - State management
- `/context/` - React Context

**Examples**:
- `src/store/authStore.js` → state
- `src/context/UserContext.jsx` → state

### Data Access Layer (0.85 confidence)
- `/firestore/` - Firebase Firestore
- `/api/` - API clients
- `/query.js` - GraphQL/API queries

**Examples**:
- `src/api/users.js` → data-access
- `src/firestore/config.js` → data-access

### Presentation Layer (0.85 confidence)
- `/components/` - Reusable components
- `/screens/` - Full-screen components

**Examples**:
- `src/components/Button.jsx` → presentation
- `src/screens/Home.jsx` → presentation

### Utilities Layer (0.75 confidence)
- `/lib/` - Library code
- `/utils/` - Utility functions

**Examples**:
- `src/utils/helpers.js` → utilities
- `src/lib/validators.js` → utilities

## Generic (Cross-Language) Patterns

Used when language-specific patterns don't match (confidence: 0.60-0.70).

### Domain Layer
- `/Domain/`, `/Core/`, `/domain/`, `/core/`

### Application Layer
- `/Application/`, `/UseCases/`, `/application/`, `/usecases/`

### Presentation Layer
- `/Web/`, `/Api/`, `/Endpoints/`, `/Controllers/`

### Infrastructure Layer
- `/Infrastructure/`, `/Persistence/`

## Confidence Scores

Classification confidence indicates reliability:

| Score | Level | Recommendation |
|-------|-------|-----------------|
| 0.90+ | High | Safe for production, specific pattern |
| 0.80-0.89 | Medium | Reliable but verify manually |
| 0.70-0.79 | Medium-Low | Consider review, common ambiguity |
| < 0.70 | Low | Use as fallback only |

## Classification Flow

When classifying a file, the orchestrator:

1. **Detects language** from file extension
2. **Checks language support** for each strategy
3. **Tries strategies in order**:
   - JavaScript-specific (if JS/TS file)
   - Generic classifier (always)
4. **Returns first match** with confidence score
5. **Returns None** if no patterns match

## Examples

### JavaScript/TypeScript Project

```
src/
├── components/          → presentation (confidence: 0.85)
├── hooks/               → utilities (confidence: 0.75)
├── pages/               → routes (confidence: 0.95)
├── store/               → state (confidence: 0.90)
├── services/api.js      → data-access (confidence: 0.85)
├── __tests__/           → testing (confidence: 0.95)
└── utils/               → utilities (confidence: 0.75)
```

### C# Project (uses generic patterns)

```
src/
├── Domain/              → domain (confidence: 0.70)
├── Application/         → application (confidence: 0.65)
├── Web/                 → presentation (confidence: 0.70)
└── Infrastructure/      → infrastructure (confidence: 0.65)
```

## Extending the System

### Adding a Language Classifier

```python
from lib.template_generator.layer_classifier import LayerClassificationStrategy

class PythonLayerClassifier(LayerClassificationStrategy):
    """Python-specific layer classifier."""

    LAYER_PATTERNS = [
        (r'/models\.py$', 'domain', 0.90),
        (r'/services/', 'application', 0.85),
        (r'/views/', 'presentation', 0.85),
        (r'/migrations/', 'infrastructure', 0.80),
        (r'/tests/', 'testing', 0.95),
    ]

    def classify(self, example_file, analysis):
        for pattern, layer, confidence in self.LAYER_PATTERNS:
            if re.search(pattern, example_file.path):
                return ClassificationResult(
                    layer=layer,
                    confidence=confidence,
                    strategy_used=self.__class__.__name__,
                    pattern_matched=pattern
                )
        return None

    def supports_language(self, language):
        return language.lower() == 'python'

# Register with orchestrator
orchestrator = LayerClassificationOrchestrator(
    strategies=[
        PythonLayerClassifier(),
        JavaScriptLayerClassifier(),
        GenericLayerClassifier(),
    ]
)
```

## Troubleshooting

### Files Always Going to `templates/other/`

1. Check file language detection: `_detect_language(path)` should return correct language
2. Verify patterns: Is your folder structure matching expected patterns?
3. Add debug: Print `result.pattern_matched` to see which pattern matched
4. Check confidence: If < 0.70, may be deprioritized

### Confidence Too Low

- Language-specific patterns: 0.85-0.95
- Generic patterns: 0.60-0.70
- Custom classifiers: Set appropriately for your domain

If confidence is too low, add more specific patterns to your classifier.

### Custom Classifier Not Being Used

1. Verify it's in strategies list
2. Check `supports_language()` returns True for your language
3. Verify `classify()` returns ClassificationResult (not None)
4. Check strategy order (first match wins)

## References

- `layer_classifier.py` - Classifier implementations
- `path_resolver.py` - Integration with template path resolution
- Tests: `tests/lib/template_generator/` - Comprehensive test suite
