---
id: TASK-FIX-LAYER-CLASS
title: Add C#/MAUI Layer Classification Patterns
status: backlog
task_type: implementation
created: 2025-12-10T16:30:00Z
updated: 2025-12-10T16:30:00Z
priority: medium
tags: [template-create, layer-classification, enhancement]
complexity: 4
implementation_mode: direct
conductor_workspace: template-fix-wave2-layer
wave: 2
parent_review: TASK-REV-TC01
---

# Add C#/MAUI Layer Classification Patterns

## Problem Statement

Template files for .NET MAUI projects are miscategorized into "other" category instead of appropriate architectural layers. Files like `MauiProgram.cs`, `*Tests.cs`, and `*Mapper.cs` should have specific classifications.

**Current "other" contents for MyDrive**:
- `MauiProgram.cs` → should be "bootstrap" or "infrastructure"
- `ConfigurationEngineTests.cs` → should be "testing"
- `PlanningTypesMapper.cs` → should be "mapping" or "infrastructure"

## Root Cause

The `layer_classifier.py` only has `JavaScriptLayerClassifier` - no C#-specific classifier exists. The `GenericLayerClassifier` fallback doesn't understand C# naming conventions.

## Acceptance Criteria

- [ ] `MauiProgram.cs` classified as "bootstrap" (not "other")
- [ ] `*Tests.cs` files classified as "testing" (not "other")
- [ ] `*Mapper.cs` files classified as "mapping" (not "other")
- [ ] `*Repository.cs` files classified as "data-access"
- [ ] `*ViewModel.cs` files classified as "presentation"
- [ ] C# projects have ≤5% "other" classification rate
- [ ] Unit tests for C# classification patterns

## Technical Specification

### File: layer_classifier.py

**Location**: `installer/global/lib/template_generator/layer_classifier.py`

#### Change 1: Add CSharpLayerClassifier class (after JavaScriptLayerClassifier, ~line 200)

```python
class CSharpLayerClassifier(LayerClassificationStrategy):
    """
    C#/.NET-specific layer classifier using naming conventions and folder patterns.

    Classifies C# files based on:
    - *Tests.cs, *Test.cs → Testing layer
    - *Mapper.cs, *Mapping.cs → Mapping layer
    - *Repository.cs → Data access layer
    - *Service.cs → Services layer
    - *Engine.cs → Business logic layer
    - *ViewModel.cs → Presentation layer
    - *Controller.cs → API layer
    - Program.cs, MauiProgram.cs → Bootstrap layer
    - App.xaml.cs, AppShell.xaml.cs → Bootstrap layer
    """

    # Pattern: (regex_pattern, layer, confidence)
    # Ordered by specificity (most specific first)
    LAYER_PATTERNS: List[tuple] = [
        # Testing (highest specificity)
        (r'Tests?\.cs$', 'testing', 0.95),
        (r'/Tests?/', 'testing', 0.90),

        # Bootstrap/Entry points
        (r'Program\.cs$', 'bootstrap', 0.95),
        (r'MauiProgram\.cs$', 'bootstrap', 0.95),
        (r'App\.xaml\.cs$', 'bootstrap', 0.90),
        (r'AppShell\.xaml\.cs$', 'bootstrap', 0.90),
        (r'Startup\.cs$', 'bootstrap', 0.95),

        # Mapping layer
        (r'Mapper\.cs$', 'mapping', 0.90),
        (r'Mapping\.cs$', 'mapping', 0.90),
        (r'/Mappers?/', 'mapping', 0.85),

        # Data access
        (r'Repository\.cs$', 'data-access', 0.90),
        (r'/Repositories/', 'data-access', 0.85),

        # Services
        (r'Service\.cs$', 'services', 0.85),
        (r'/Services/', 'services', 0.80),

        # Engines (business logic)
        (r'Engine\.cs$', 'business-logic', 0.90),
        (r'/Engines/', 'business-logic', 0.85),

        # Presentation
        (r'ViewModel\.cs$', 'presentation', 0.90),
        (r'/ViewModels/', 'presentation', 0.85),
        (r'View\.cs$', 'presentation', 0.85),
        (r'/Views/', 'presentation', 0.80),
        (r'\.xaml\.cs$', 'presentation', 0.80),

        # API
        (r'Controller\.cs$', 'api', 0.90),
        (r'/Controllers/', 'api', 0.85),

        # Domain/Entities
        (r'/Domain/', 'domain', 0.85),
        (r'/Entities/', 'domain', 0.85),
        (r'/Models/', 'domain', 0.80),

        # Infrastructure
        (r'/Infrastructure/', 'infrastructure', 0.85),
        (r'/Database/', 'infrastructure', 0.80),
    ]

    def supports_language(self, language: str) -> bool:
        """Check if this classifier supports the given language."""
        return language.lower() in ['c#', 'csharp', '.net', 'dotnet']

    def classify(
        self,
        example_file: ExampleFile,
        analysis: CodebaseAnalysis
    ) -> Optional[ClassificationResult]:
        """
        Classify a C# file into an architectural layer.

        Args:
            example_file: File to classify
            analysis: Codebase analysis context

        Returns:
            ClassificationResult if matched, None to fall through to next classifier
        """
        file_path = str(example_file.path)

        for pattern, layer, confidence in self.LAYER_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return ClassificationResult(
                    layer=layer,
                    confidence=confidence,
                    strategy_used='CSharpLayerClassifier',
                    pattern_matched=pattern
                )

        return None  # Fall through to generic classifier
```

#### Change 2: Register classifier in ChainedLayerClassifier (modify `__init__`, ~line 240)

```python
def __init__(self, strategies: Optional[List[LayerClassificationStrategy]] = None):
    """
    Initialize with default or custom strategies.

    Args:
        strategies: Optional list of classification strategies.
                   If None, uses default chain: JavaScript → C# → Generic
    """
    if strategies is None:
        strategies = [
            JavaScriptLayerClassifier(),
            CSharpLayerClassifier(),  # Add C# classifier
            GenericLayerClassifier(),
        ]
    self.strategies = strategies
```

## Test Cases

| File | Expected Layer | Confidence |
|------|----------------|------------|
| `MauiProgram.cs` | bootstrap | 0.95 |
| `ConfigurationEngineTests.cs` | testing | 0.95 |
| `PlanningTypesMapper.cs` | mapping | 0.90 |
| `PlanningRepository.cs` | data-access | 0.90 |
| `HomeViewModel.cs` | presentation | 0.90 |
| `UserService.cs` | services | 0.85 |
| `PlanningEngine.cs` | business-logic | 0.90 |
| `ApiController.cs` | api | 0.90 |

## Execution

This task uses **direct implementation** (not `/task-work`):

```bash
# 1. Open the file
# 2. Add CSharpLayerClassifier class after JavaScriptLayerClassifier
# 3. Register in ChainedLayerClassifier.__init__
# 4. Run tests
pytest tests/lib/template_generator/test_layer_classifier.py -v
```

## Verification

```bash
# After implementation, test on MyDrive
cd ~/Projects/MyDrive
/template-create --name mydrive-test

# Verify templates/ directory structure:
# - templates/bootstrap/MauiProgram.cs.template
# - templates/testing/ConfigurationEngineTests.cs.template
# - templates/mapping/PlanningTypesMapper.cs.template
# - templates/other/ should have very few files (≤5% of total)
```

## Notes

- Follows existing pattern from `JavaScriptLayerClassifier`
- Patterns ordered by specificity (most specific first)
- File name patterns take precedence over folder patterns
- Falls through to `GenericLayerClassifier` if no match
