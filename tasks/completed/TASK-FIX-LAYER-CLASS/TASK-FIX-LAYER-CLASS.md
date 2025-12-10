---
id: TASK-FIX-LAYER-CLASS
title: Add AI-Powered Layer Classification with Generic Fallback
status: completed
task_type: implementation
created: 2025-12-10T16:30:00Z
updated: 2025-12-10T19:30:00Z
completed: 2025-12-10T19:30:00Z
priority: medium
tags: [template-create, layer-classification, enhancement, ai-native]
complexity: 5
implementation_mode: direct
conductor_workspace: template-fix-wave2-layer
wave: 2
parent_review: TASK-REV-TC01
---

# Add AI-Powered Layer Classification with Generic Fallback

## Problem Statement

Template files for complex codebases are miscategorized into "other" category instead of appropriate architectural layers. The current approach has per-language classifiers (`JavaScriptLayerClassifier`) which creates maintenance burden and doesn't scale.

**Current "other" contents for MyDrive**:
- `MauiProgram.cs` → should be "bootstrap" or "infrastructure"
- `ConfigurationEngineTests.cs` → should be "testing"
- `PlanningTypesMapper.cs` → should be "mapping" or "infrastructure"

## Root Cause

The `layer_classifier.py` uses hardcoded per-language classifiers. This approach:
- Requires new classifier for each language/framework
- Creates maintenance burden
- Doesn't leverage AI capabilities
- Contradicts GuardKit's technology-agnostic philosophy

## Solution: AI-Native with Generic Heuristics

Follow the same pattern used in `agent_generator.py`:
1. **AI-first**: Use AI to understand file purpose (works for ANY language)
2. **Heuristic fallback**: Use generic folder/path patterns that work across all languages

This mirrors the successful `_heuristic_identify_agents()` pattern you already implemented.

## Acceptance Criteria

- [x] AI-powered layer classification attempts first
- [x] Generic heuristic fallback when AI fails or returns no result
- [x] Heuristics use folder patterns that work across ALL languages
- [x] No hardcoded language-specific patterns (remove `JavaScriptLayerClassifier` approach)
- [x] "Other" classification rate ≤10% for well-structured codebases
- [x] Unit tests for generic heuristic patterns

## Technical Specification

### File: layer_classifier.py

**Location**: `installer/core/lib/template_generator/layer_classifier.py`

#### Change 1: Add AI classification method

```python
def _ai_classify_layer(self, file_path: str, file_content: Optional[str], analysis: Any) -> Optional[str]:
    """
    Use AI to classify file into architectural layer.

    Works for ANY language by analyzing:
    - File path and name
    - File content (if available)
    - Codebase context from analysis

    Args:
        file_path: Path to the file
        file_content: Optional file content for deeper analysis
        analysis: Codebase analysis context

    Returns:
        Layer name or None if AI cannot determine
    """
    # AI prompt that works for any language
    prompt = f"""Analyze this file and determine its architectural layer.

File: {file_path}
Project type: {getattr(analysis, 'project_type', 'unknown')}
Primary language: {getattr(analysis, 'language', 'unknown')}

Return ONLY one of these layer names (lowercase):
- testing (test files, specs, fixtures)
- presentation (UI, views, components, view models)
- api (controllers, routes, endpoints, handlers)
- services (business logic services, use cases)
- domain (entities, models, value objects)
- data-access (repositories, data stores, DAOs)
- infrastructure (config, bootstrap, utilities, helpers)
- mapping (mappers, transformers, converters)
- other (if truly doesn't fit)

Respond with just the layer name, nothing else."""

    try:
        # Use existing AI integration pattern
        response = self._call_ai(prompt)
        layer = response.strip().lower()

        valid_layers = {'testing', 'presentation', 'api', 'services', 'domain',
                       'data-access', 'infrastructure', 'mapping', 'other'}

        if layer in valid_layers:
            return layer
        return None
    except Exception:
        return None
```

#### Change 2: Add generic heuristic fallback (language-agnostic)

```python
def _heuristic_classify_layer(self, file_path: str) -> str:
    """
    Classify file using generic folder/path patterns.

    These patterns work across ALL languages:
    - /tests/, /test/, /spec/ → testing
    - /views/, /ui/, /components/ → presentation
    - /controllers/, /api/, /routes/ → api
    - etc.

    Args:
        file_path: Path to the file

    Returns:
        Layer name (defaults to 'other' if no match)
    """
    path_lower = file_path.lower()

    # Generic folder patterns that work across languages
    # Ordered by specificity (most specific first)

    # Testing - universal patterns
    if any(p in path_lower for p in ['/test/', '/tests/', '/spec/', '/specs/',
                                       '/__tests__/', '/testing/', '.test.', '.spec.',
                                       '_test.', '_tests.', 'test_', 'tests_']):
        return 'testing'

    # Bootstrap/Entry - universal patterns
    if any(p in path_lower for p in ['/bootstrap/', '/startup/', '/config/',
                                       'program.', 'main.', 'app.', 'index.',
                                       '/entry/', 'bootstrap.', 'startup.']):
        # Exclude test bootstraps
        if 'test' not in path_lower:
            return 'infrastructure'

    # Mapping - universal patterns
    if any(p in path_lower for p in ['/mapper/', '/mappers/', '/mapping/',
                                       '/transform/', '/converter/', '/adapters/',
                                       'mapper.', 'mapping.', 'transformer.']):
        return 'mapping'

    # Presentation - universal patterns
    if any(p in path_lower for p in ['/view/', '/views/', '/ui/', '/components/',
                                       '/pages/', '/screens/', '/widgets/',
                                       '/viewmodel/', '/viewmodels/', '/presenter/',
                                       'view.', 'component.', 'page.', 'screen.']):
        return 'presentation'

    # API - universal patterns
    if any(p in path_lower for p in ['/controller/', '/controllers/', '/api/',
                                       '/routes/', '/handlers/', '/endpoints/',
                                       '/rest/', '/graphql/', 'controller.',
                                       'handler.', 'endpoint.']):
        return 'api'

    # Services - universal patterns
    if any(p in path_lower for p in ['/service/', '/services/', '/usecase/',
                                       '/usecases/', '/application/', '/business/',
                                       'service.', 'usecase.']):
        return 'services'

    # Domain - universal patterns
    if any(p in path_lower for p in ['/domain/', '/entities/', '/entity/',
                                       '/model/', '/models/', '/core/',
                                       '/valueobject/', 'entity.', 'model.']):
        return 'domain'

    # Data access - universal patterns
    if any(p in path_lower for p in ['/repository/', '/repositories/', '/data/',
                                       '/database/', '/persistence/', '/storage/',
                                       '/dao/', '/store/', 'repository.',
                                       'store.', 'dao.']):
        return 'data-access'

    # Infrastructure - universal patterns
    if any(p in path_lower for p in ['/infrastructure/', '/infra/', '/util/',
                                       '/utils/', '/helper/', '/helpers/',
                                       '/common/', '/shared/', '/lib/',
                                       'util.', 'utils.', 'helper.', 'helpers.']):
        return 'infrastructure'

    return 'other'
```

#### Change 3: Update main classify method to use AI-first approach

```python
def classify(self, example_file: ExampleFile, analysis: CodebaseAnalysis) -> ClassificationResult:
    """
    Classify a file into an architectural layer.

    Uses AI-first approach with generic heuristic fallback:
    1. Try AI classification (works for any language)
    2. Fall back to generic folder patterns

    Args:
        example_file: File to classify
        analysis: Codebase analysis context

    Returns:
        ClassificationResult with layer and confidence
    """
    file_path = str(example_file.path)

    # 1. Try AI classification first
    try:
        ai_layer = self._ai_classify_layer(file_path, example_file.content, analysis)
        if ai_layer and ai_layer != 'other':
            return ClassificationResult(
                layer=ai_layer,
                confidence=0.90,
                strategy_used='AI',
                pattern_matched='ai_analysis'
            )
    except Exception as e:
        print(f"  ⚠️ AI classification failed: {e}")

    # 2. Fall back to generic heuristics
    heuristic_layer = self._heuristic_classify_layer(file_path)

    confidence = 0.85 if heuristic_layer != 'other' else 0.50

    return ClassificationResult(
        layer=heuristic_layer,
        confidence=confidence,
        strategy_used='GenericHeuristic',
        pattern_matched=f'folder_pattern:{heuristic_layer}'
    )
```

#### Change 4: Remove or deprecate per-language classifiers

```python
# DEPRECATED: Remove JavaScriptLayerClassifier and similar per-language classifiers
# The AI-first approach with generic heuristics handles all languages

# If backward compatibility needed, keep as empty pass-through:
class JavaScriptLayerClassifier(LayerClassificationStrategy):
    """DEPRECATED: Use GenericLayerClassifier with AI instead."""

    def classify(self, example_file, analysis) -> Optional[ClassificationResult]:
        # Pass through to generic classifier
        return None
```

## Test Cases

| File | Expected Layer | Pattern Type |
|------|----------------|--------------|
| `src/tests/UserTest.py` | testing | folder |
| `app/controllers/UserController.java` | api | folder |
| `lib/services/AuthService.ts` | services | folder |
| `domain/entities/User.cs` | domain | folder |
| `data/repositories/UserRepo.go` | data-access | folder |
| `MauiProgram.cs` | infrastructure | AI or program. |
| `ConfigurationEngineTests.cs` | testing | Tests. suffix |
| `PlanningTypesMapper.cs` | mapping | Mapper. suffix |
| `src/components/Button.vue` | presentation | folder |
| `pkg/handlers/health.go` | api | folder |

## Execution

This task uses **direct implementation** (not `/task-work`):

```bash
# 1. Open layer_classifier.py
# 2. Add _ai_classify_layer method
# 3. Add _heuristic_classify_layer method
# 4. Update main classify method
# 5. Deprecate per-language classifiers
# 6. Run tests
pytest tests/lib/template_generator/test_layer_classifier.py -v
```

## Verification

```bash
# After implementation, test on MyDrive
cd ~/Projects/MyDrive
/template-create --name mydrive-test --dry-run

# Verify classification results:
# - MauiProgram.cs → infrastructure (not other)
# - ConfigurationEngineTests.cs → testing (not other)
# - PlanningTypesMapper.cs → mapping (not other)
# - "other" rate should be ≤10%
```

## Benefits

1. **Technology agnostic**: Works for C#, Python, Go, Rust, any language
2. **No maintenance burden**: No new classifiers needed per language
3. **AI-native**: Leverages AI for intelligent classification
4. **Consistent pattern**: Matches `agent_generator.py` approach
5. **Graceful fallback**: Generic heuristics always work

## Notes

- Follows same AI-first + heuristic pattern as `_heuristic_identify_agents()`
- Generic folder patterns are industry-standard conventions
- AI can understand language-specific nuances without hardcoding
- Deprecates rather than removes old classifiers for backward compatibility
