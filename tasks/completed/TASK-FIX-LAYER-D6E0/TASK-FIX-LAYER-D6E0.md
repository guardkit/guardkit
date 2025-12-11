---
id: TASK-FIX-LAYER-D6E0
title: Complete Layer Detection
status: completed
task_type: implementation
created: 2025-12-11T10:45:00Z
updated: 2025-12-11T14:30:00Z
completed: 2025-12-11T14:30:00Z
completed_location: tasks/completed/TASK-FIX-LAYER-D6E0/
priority: medium
tags: [template-create, layer-detection, settings-json, codebase-analyzer]
complexity: 4
parent_review: TASK-REV-D4A7
test_results:
  status: passed
  coverage: 90
  last_run: 2025-12-11T14:25:00Z
  tests_passed: 116
  tests_failed: 0
---

# Task: Complete Layer Detection

## Problem Statement

Layer detection is incomplete for .NET MAUI projects, resulting in missing layer mappings in `settings.json`. Specifically:
- ViewModels layer detected as generic "Presentation" instead of separate layer
- Engines (business logic) layer not detected at all
- Handlers and Processors layers missing

## Root Cause

**Current VALID_LAYERS** (`layer_classifier.py:128-131`):
```python
VALID_LAYERS = [
    'testing', 'presentation', 'api', 'services', 'domain',
    'data-access', 'infrastructure', 'mapping', 'other'
]
```

**Missing Layers:**
- `viewmodels` - MVVM ViewModels layer
- `engines` - Business logic orchestration
- `handlers` - Event/command handlers
- `processors` - Data processors

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `installer/core/lib/template_generator/layer_classifier.py` | 128-131 | Expand VALID_LAYERS |
| `installer/core/lib/template_generator/layer_classifier.py` | 274-417 | Add detection patterns |
| `installer/core/lib/codebase_analyzer/agent_invoker.py` | 195-211 | Update EXTENDED_LAYER_PATTERNS |
| `installer/core/lib/codebase_analyzer/agent_invoker.py` | 568-596 | Update _infer_layer_from_path |

## Implementation Specification

### Step 1: Expand VALID_LAYERS (layer_classifier.py:128-131)

**Before:**
```python
VALID_LAYERS = [
    'testing', 'presentation', 'api', 'services', 'domain',
    'data-access', 'infrastructure', 'mapping', 'other'
]
```

**After:**
```python
VALID_LAYERS = [
    # Core architectural layers
    'domain',           # Domain entities and business rules
    'application',      # Application services and use cases
    'infrastructure',   # External concerns (DB, API clients, etc.)
    'presentation',     # UI layer (views, pages)

    # Specialized layers
    'viewmodels',       # MVVM ViewModels
    'engines',          # Business logic orchestration
    'services',         # Service layer
    'api',              # API controllers/endpoints
    'data-access',      # Repositories and data access

    # Supporting layers
    'handlers',         # Event/command handlers
    'processors',       # Data processors
    'mapping',          # Object mappers
    'testing',          # Test projects

    # Fallback
    'other'
]
```

### Step 2: Add Detection Patterns (layer_classifier.py:274-417)

**Add after existing patterns (around line 400):**

```python
# ViewModels layer (MVVM pattern)
viewmodel_patterns = [
    '/viewmodel/', '/viewmodels/', '/vm/',
    '/view-models/', '/view_models/'
]
if any(p in path_lower for p in viewmodel_patterns):
    return 'viewmodels', 'folder_pattern:viewmodel'

viewmodel_suffixes = ['viewmodel.', 'vm.']
if any(s in filename_lower for s in viewmodel_suffixes):
    return 'viewmodels', 'suffix_pattern:viewmodel'

# Engines layer (business logic orchestration)
engine_patterns = [
    '/engine/', '/engines/',
    '/businesslogic/', '/business-logic/',
    '/orchestration/'
]
if any(p in path_lower for p in engine_patterns):
    return 'engines', 'folder_pattern:engine'

engine_suffixes = ['engine.']
if any(s in filename_lower for s in engine_suffixes):
    return 'engines', 'suffix_pattern:engine'

# Handlers layer (CQRS, events)
handler_patterns = [
    '/handler/', '/handlers/',
    '/commandhandlers/', '/command-handlers/',
    '/eventhandlers/', '/event-handlers/',
    '/queryhandlers/', '/query-handlers/'
]
if any(p in path_lower for p in handler_patterns):
    return 'handlers', 'folder_pattern:handler'

handler_suffixes = ['handler.', 'commandhandler.', 'queryhandler.', 'eventhandler.']
if any(s in filename_lower for s in handler_suffixes):
    return 'handlers', 'suffix_pattern:handler'

# Processors layer
processor_patterns = [
    '/processor/', '/processors/',
    '/pipeline/', '/pipelines/'
]
if any(p in path_lower for p in processor_patterns):
    return 'processors', 'folder_pattern:processor'

processor_suffixes = ['processor.', 'pipeline.']
if any(s in filename_lower for s in processor_suffixes):
    return 'processors', 'suffix_pattern:processor'
```

### Step 3: Update EXTENDED_LAYER_PATTERNS (agent_invoker.py:195-211)

**Add these entries:**

```python
EXTENDED_LAYER_PATTERNS = {
    # ... existing patterns ...

    # MVVM ViewModels
    "viewmodels/": ("ViewModels", "MVVM ViewModels", ["Domain", "Services"]),
    "ViewModels/": ("ViewModels", "MVVM ViewModels", ["Domain", "Services"]),

    # Business Logic Engines
    "engines/": ("Engines", "Business logic orchestration", ["Domain", "Services", "Data-Access"]),
    "Engines/": ("Engines", "Business logic orchestration", ["Domain", "Services", "Data-Access"]),

    # Handlers (CQRS)
    "handlers/": ("Handlers", "Command/Query handlers", ["Domain", "Services"]),
    "Handlers/": ("Handlers", "Command/Query handlers", ["Domain", "Services"]),

    # Processors
    "processors/": ("Processors", "Data processors", ["Domain", "Services"]),
    "Processors/": ("Processors", "Data processors", ["Domain", "Services"]),
}
```

### Step 4: Update _infer_layer_from_path (agent_invoker.py:568-596)

**Add to the layer inference logic:**

```python
def _infer_layer_from_path(self, path: str) -> str:
    """Infer architectural layer from file path."""
    path_lower = path.lower()

    # ViewModels layer
    if any(x in path_lower for x in ["viewmodel", "viewmodels", "/vm/"]):
        return "ViewModels"

    # Engines layer
    if any(x in path_lower for x in ["engine", "engines", "businesslogic"]):
        return "Engines"

    # Handlers layer
    if any(x in path_lower for x in ["handler", "handlers", "commandhandler", "queryhandler"]):
        return "Handlers"

    # Processors layer
    if any(x in path_lower for x in ["processor", "processors", "pipeline"]):
        return "Processors"

    # ... existing logic for other layers ...

    # Domain layer
    if any(x in path_lower for x in ["domain", "entities", "models"]):
        return "Domain"

    # Application layer
    if any(x in path_lower for x in ["application", "usecases", "services"]):
        return "Application"

    # Infrastructure layer
    if any(x in path_lower for x in ["infrastructure", "data", "repository", "repositories"]):
        return "Infrastructure"

    # Presentation layer
    if any(x in path_lower for x in ["web", "api", "controllers", "routes", "endpoints"]):
        return "Presentation"

    # Testing layer
    if any(x in path_lower for x in ["test", "tests", "spec", "specs"]):
        return "Testing"

    # Shared/Common
    if any(x in path_lower for x in ["shared", "common", "core"]):
        return "Shared"

    return "Other"
```

### Step 5: Add Tests

```python
# tests/lib/template_generator/test_layer_classifier.py

import pytest
from pathlib import Path
from installer.core.lib.template_generator.layer_classifier import AILayerClassifier


class TestLayerClassifier:
    """Tests for layer classification."""

    @pytest.fixture
    def classifier(self):
        return AILayerClassifier()

    def test_classify_viewmodels_folder(self, classifier):
        """Test ViewModels folder detection."""
        result = classifier._heuristic_classify_layer("/src/ViewModels/MainViewModel.cs")
        assert result[0] == 'viewmodels'

    def test_classify_viewmodel_file(self, classifier):
        """Test ViewModel file suffix detection."""
        result = classifier._heuristic_classify_layer("/src/MainViewModel.cs")
        assert result[0] == 'viewmodels'

    def test_classify_engines_folder(self, classifier):
        """Test Engines folder detection."""
        result = classifier._heuristic_classify_layer("/src/Engines/LoadingEngine.cs")
        assert result[0] == 'engines'

    def test_classify_engine_file(self, classifier):
        """Test Engine file suffix detection."""
        result = classifier._heuristic_classify_layer("/src/LoadingEngine.cs")
        assert result[0] == 'engines'

    def test_classify_handlers_folder(self, classifier):
        """Test Handlers folder detection."""
        result = classifier._heuristic_classify_layer("/src/Handlers/CreateOrderHandler.cs")
        assert result[0] == 'handlers'

    def test_classify_processors_folder(self, classifier):
        """Test Processors folder detection."""
        result = classifier._heuristic_classify_layer("/src/Processors/ImageProcessor.cs")
        assert result[0] == 'processors'

    def test_classify_maui_project_structure(self, classifier):
        """Integration test for typical .NET MAUI structure."""
        test_paths = {
            "/MyApp/ViewModels/HomeViewModel.cs": "viewmodels",
            "/MyApp/Engines/ScanEngine.cs": "engines",
            "/MyApp/Services/ApiService.cs": "services",
            "/MyApp/Repositories/UserRepository.cs": "data-access",
            "/MyApp/Domain/Entities/User.cs": "domain",
            "/MyApp/Views/HomePage.xaml": "presentation",
            "/MyApp.Tests/UserTests.cs": "testing",
        }

        for path, expected_layer in test_paths.items():
            result = classifier._heuristic_classify_layer(path)
            assert result[0] == expected_layer, f"Path {path} should be {expected_layer}, got {result[0]}"
```

## Acceptance Criteria

- [x] ViewModels layer detected for `/ViewModels/` folders and `*ViewModel.cs` files
- [x] Engines layer detected for `/Engines/` folders and `*Engine.cs` files
- [x] Handlers layer detected for `/Handlers/` folders and `*Handler.cs` files
- [x] Processors layer detected for `/Processors/` folders
- [x] Layer mappings appear correctly in settings.json
- [x] Works for .NET MAUI project structure
- [x] All existing tests continue to pass (116/116 passing)
- [x] New tests added and passing (11 new test methods, 197 lines)

## Test Requirements

```bash
# Run layer classifier tests
pytest tests/lib/template_generator/test_layer_classifier.py -v

# Integration test with mydrive template
python3 -c "
from pathlib import Path
from installer.core.lib.template_generator.layer_classifier import AILayerClassifier

classifier = AILayerClassifier()

# Test MAUI paths
test_paths = [
    'ViewModels/MainViewModel.cs',
    'Engines/LoadingEngine.cs',
    'Services/ConfigurationService.cs',
    'Repositories/UserRepository.cs',
]

for path in test_paths:
    result = classifier._heuristic_classify_layer(f'/MyApp/{path}')
    print(f'{path}: {result[0]}')
"
```

## Regression Prevention

**Potential Regressions:**
1. Existing layer detection might change (e.g., ViewModels previously classified as Presentation)
2. Performance impact from additional pattern checks

**Mitigation:**
- Add specific patterns before generic ones (ViewModels before Presentation)
- Use early returns to avoid unnecessary checks
- Maintain backward compatibility - don't change existing classifications unless wrong

## Notes

- **Medium priority** - improves settings.json accuracy
- Consider adding layer dependency validation (ViewModels shouldn't depend on Infrastructure)
- Future: Support for custom layer definitions in template config
