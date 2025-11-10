---
id: TASK-038
title: Implement architecture pattern analyzer for /template-create
status: backlog
created: 2025-11-01T15:35:00Z
priority: high
complexity: 6
estimated_hours: 7
tags: [template-create, pattern-extraction, architecture-analysis]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037]
blocks: [TASK-042, TASK-050]
---

# TASK-038: Implement Architecture Pattern Analyzer

## Objective

Create an analyzer that detects architectural patterns from codebase structure:
- MVVM (Model-View-ViewModel)
- Clean Architecture (Domain, Application, Infrastructure)
- Repository Pattern
- Service Pattern
- Domain Pattern (verb-based operations)
- CQRS (Command Query Responsibility Segregation)

## Context

This is Phase 1.2 of `/template-create`. After detecting the technology stack (TASK-037), we need to understand the architectural patterns to generate accurate templates.

## Scope

### In Scope
- Directory structure analysis
- Class naming pattern detection
- Layer identification (Domain, Data, Presentation)
- Pattern scoring and confidence
- Support for React, Python, .NET MAUI

### Out of Scope
- Code pattern extraction (TASK-039)
- Naming convention inference (TASK-040)
- Template generation (later tasks)

## Requirements

### Functional Requirements

**REQ-1**: Detect MVVM pattern
```
When analyzing a .NET MAUI or React project, the system shall:
- Identify ViewModel classes by suffix or folder structure
- Identify View classes (Pages, Components)
- Identify Model/Entity classes
- Calculate MVVM confidence score (0-100)
```

**REQ-2**: Detect Clean Architecture layers
```
When analyzing project structure, the system shall:
- Identify Domain layer (business logic)
- Identify Application layer (use cases, services)
- Identify Infrastructure layer (external dependencies)
- Identify Presentation layer (UI)
- Verify dependency direction (inward)
```

**REQ-3**: Detect Repository Pattern
```
When analyzing data access code, the system shall:
- Find interfaces with "Repository" suffix
- Find implementations matching interfaces
- Identify repository methods (GetAll, GetById, Create, Update, Delete)
- Calculate Repository pattern confidence
```

**REQ-4**: Detect Service Pattern
```
When analyzing external integrations, the system shall:
- Find interfaces with "Service" suffix
- Identify external API integrations
- Detect HTTP clients, SDK usage
```

**REQ-5**: Detect Domain Pattern
```
When analyzing domain logic, the system shall:
- Identify verb-based class names (GetProducts, CreateOrder)
- Detect ErrorOr<T> or Result<T> return types
- Identify domain operation patterns
```

## Acceptance Criteria

### AC1: MVVM Detection
- [ ] Detects MVVM in .NET MAUI projects (>85% accuracy)
- [ ] Identifies ViewModels by suffix or folder
- [ ] Identifies Views (Pages/ContentViews)
- [ ] Identifies Models/Entities
- [ ] Returns confidence score

### AC2: Clean Architecture Detection
- [ ] Identifies Domain layer correctly
- [ ] Identifies Application layer (if exists)
- [ ] Identifies Infrastructure layer
- [ ] Identifies Presentation layer
- [ ] Validates dependency direction

### AC3: Repository Pattern Detection
- [ ] Finds IRepository interfaces
- [ ] Matches implementations to interfaces
- [ ] Identifies CRUD methods
- [ ] Calculates pattern confidence (>80% = present)

### AC4: Service Pattern Detection
- [ ] Finds IService interfaces
- [ ] Identifies HTTP/API integrations
- [ ] Detects external SDK usage

### AC5: Domain Pattern Detection
- [ ] Identifies verb-based operations
- [ ] Detects ErrorOr<T> or Result<T>
- [ ] Recognizes domain operation structure

### AC6: Data Structure
- [ ] Returns structured JSON with all patterns
- [ ] Includes confidence scores per pattern
- [ ] Provides evidence (file paths, class names)

## Implementation Plan

### Step 1: Create Analyzer Module

```python
# installer/global/commands/lib/architecture_analyzer.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

class ArchitecturePattern(Enum):
    MVVM = "mvvm"
    CLEAN_ARCHITECTURE = "clean_architecture"
    REPOSITORY = "repository_pattern"
    SERVICE = "service_pattern"
    DOMAIN = "domain_pattern"
    CQRS = "cqrs"

@dataclass
class PatternDetection:
    pattern: ArchitecturePattern
    confidence: int  # 0-100
    evidence: List[str]  # File paths, class names
    description: str

@dataclass
class ArchitectureAnalysisResult:
    patterns: List[PatternDetection]
    layers: Dict[str, List[str]]  # {"Domain": ["src/Domain/..."], ...}
    conventions: Dict[str, str]  # {"ViewModel": "suffix", ...}
    confidence_overall: int

class ArchitectureAnalyzer:
    def __init__(self, project_path: str, stack_result):
        self.project_path = project_path
        self.stack_result = stack_result

    def analyze(self) -> ArchitectureAnalysisResult:
        """Main analysis method"""
        pass

    def _detect_mvvm(self) -> Optional[PatternDetection]:
        """Detect MVVM pattern"""
        pass

    def _detect_clean_architecture(self) -> Optional[PatternDetection]:
        """Detect Clean Architecture layers"""
        pass

    def _detect_repository_pattern(self) -> Optional[PatternDetection]:
        """Detect Repository pattern"""
        pass

    def _detect_service_pattern(self) -> Optional[PatternDetection]:
        """Detect Service pattern"""
        pass

    def _detect_domain_pattern(self) -> Optional[PatternDetection]:
        """Detect verb-based domain operations"""
        pass
```

### Step 2: Implement MVVM Detection

```python
def _detect_mvvm(self) -> Optional[PatternDetection]:
    """Detect MVVM pattern from file structure and naming"""

    viewmodels = []
    views = []
    models = []

    # Search for ViewModels
    for root, dirs, files in os.walk(self.project_path):
        if 'node_modules' in root or '.git' in root:
            continue

        for file in files:
            file_lower = file.lower()

            # ViewModel detection
            if 'viewmodel' in file_lower:
                viewmodels.append(os.path.join(root, file))

            # View detection (.xaml, .tsx, .jsx for pages/views)
            if file.endswith(('.xaml', 'Page.tsx', 'View.tsx')):
                views.append(os.path.join(root, file))

            # Model detection
            if any(keyword in file_lower for keyword in ['model.', 'entity.', 'dto.']):
                models.append(os.path.join(root, file))

    # Calculate confidence
    has_viewmodels = len(viewmodels) > 0
    has_views = len(views) > 0
    has_models = len(models) > 0

    if not (has_viewmodels and has_views):
        return None  # Not MVVM

    confidence = 0
    evidence = []

    if has_viewmodels:
        confidence += 40
        evidence.append(f"Found {len(viewmodels)} ViewModels")

    if has_views:
        confidence += 30
        evidence.append(f"Found {len(views)} Views/Pages")

    if has_models:
        confidence += 30
        evidence.append(f"Found {len(models)} Models/Entities")

    return PatternDetection(
        pattern=ArchitecturePattern.MVVM,
        confidence=confidence,
        evidence=evidence,
        description="MVVM (Model-View-ViewModel) pattern detected"
    )
```

### Step 3: Implement Repository Pattern Detection

```python
def _detect_repository_pattern(self) -> Optional[PatternDetection]:
    """Detect Repository pattern from interfaces and implementations"""

    repository_interfaces = []
    repository_implementations = []

    for root, dirs, files in os.walk(self.project_path):
        if any(skip in root for skip in ['node_modules', '.git', 'venv']):
            continue

        for file in files:
            file_path = os.path.join(root, file)

            # C# repository detection
            if file.endswith('.cs'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Look for IRepository interfaces
                    if 'interface I' in content and 'Repository' in content:
                        repository_interfaces.append(file_path)

                    # Look for Repository implementations
                    if 'class ' in content and 'Repository' in content and ': I' in content:
                        repository_implementations.append(file_path)

            # TypeScript repository detection
            elif file.endswith('.ts'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    if 'Repository' in content and ('interface' in content or 'class' in content):
                        if 'interface' in content:
                            repository_interfaces.append(file_path)
                        else:
                            repository_implementations.append(file_path)

            # Python repository detection
            elif file.endswith('.py'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    if 'Repository' in content and ('class ' in content or 'Protocol' in content):
                        if 'Protocol' in content or 'ABC' in content:
                            repository_interfaces.append(file_path)
                        else:
                            repository_implementations.append(file_path)

    if not repository_interfaces and not repository_implementations:
        return None

    confidence = 0
    evidence = []

    if repository_interfaces:
        confidence += 50
        evidence.append(f"Found {len(repository_interfaces)} repository interfaces")

    if repository_implementations:
        confidence += 50
        evidence.append(f"Found {len(repository_implementations)} repository implementations")

    return PatternDetection(
        pattern=ArchitecturePattern.REPOSITORY,
        confidence=min(confidence, 100),
        evidence=evidence,
        description="Repository pattern for data access abstraction"
    )
```

### Step 4: Implement Clean Architecture Detection

```python
def _detect_clean_architecture(self) -> Optional[PatternDetection]:
    """Detect Clean Architecture layers from directory structure"""

    layers = {
        'Domain': [],
        'Application': [],
        'Infrastructure': [],
        'Presentation': []
    }

    for root, dirs, files in os.walk(self.project_path):
        if any(skip in root for skip in ['node_modules', '.git', 'venv', 'bin', 'obj']):
            continue

        root_lower = root.lower()

        # Detect Domain layer
        if 'domain' in root_lower and 'test' not in root_lower:
            layers['Domain'].append(root)

        # Detect Application layer
        if any(keyword in root_lower for keyword in ['application', 'usecases', 'services']):
            layers['Application'].append(root)

        # Detect Infrastructure layer
        if any(keyword in root_lower for keyword in ['infrastructure', 'data', 'persistence']):
            layers['Infrastructure'].append(root)

        # Detect Presentation layer
        if any(keyword in root_lower for keyword in ['presentation', 'ui', 'views', 'pages', 'components']):
            layers['Presentation'].append(root)

    # Calculate confidence
    layers_found = sum(1 for paths in layers.values() if paths)

    if layers_found < 3:
        return None  # Not Clean Architecture

    confidence = (layers_found / 4) * 100
    evidence = [f"{layer}: {len(paths)} directories" for layer, paths in layers.items() if paths]

    return PatternDetection(
        pattern=ArchitecturePattern.CLEAN_ARCHITECTURE,
        confidence=int(confidence),
        evidence=evidence,
        description="Clean Architecture with clear layer separation"
    )
```

### Step 5: Implement Domain Pattern Detection

```python
def _detect_domain_pattern(self) -> Optional[PatternDetection]:
    """Detect verb-based domain operations pattern"""

    domain_operations = []
    erroror_usage = []

    for root, dirs, files in os.walk(self.project_path):
        if any(skip in root for skip in ['node_modules', '.git', 'test']):
            continue

        for file in files:
            if not file.endswith(('.cs', '.ts', '.py')):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Detect verb-based class names
                    import re
                    verb_pattern = r'class (Get|Create|Update|Delete|Add|Remove|Fetch|Load|Save)\w+'
                    matches = re.findall(verb_pattern, content)

                    if matches:
                        domain_operations.append(file_path)

                    # Detect ErrorOr<T> or Result<T>
                    if 'ErrorOr<' in content or 'Result<' in content:
                        erroror_usage.append(file_path)

            except Exception:
                continue

    if not domain_operations:
        return None

    confidence = 0
    evidence = []

    if domain_operations:
        confidence += 60
        evidence.append(f"Found {len(domain_operations)} verb-based domain operations")

    if erroror_usage:
        confidence += 40
        evidence.append(f"Found ErrorOr/Result pattern in {len(erroror_usage)} files")

    return PatternDetection(
        pattern=ArchitecturePattern.DOMAIN,
        confidence=min(confidence, 100),
        evidence=evidence,
        description="Domain pattern with verb-based operations"
    )
```

## Testing Strategy

### Unit Tests

```python
def test_detect_mvvm_dotnet():
    """Should detect MVVM in .NET MAUI project"""
    analyzer = ArchitectureAnalyzer("tests/fixtures/maui-mvvm-project", mock_stack)
    result = analyzer.analyze()

    mvvm = next((p for p in result.patterns if p.pattern == ArchitecturePattern.MVVM), None)

    assert mvvm is not None
    assert mvvm.confidence >= 70

def test_detect_repository_pattern():
    """Should detect Repository pattern"""
    analyzer = ArchitectureAnalyzer("tests/fixtures/clean-arch-project", mock_stack)
    result = analyzer.analyze()

    repo = next((p for p in result.patterns if p.pattern == ArchitecturePattern.REPOSITORY), None)

    assert repo is not None
    assert repo.confidence >= 80

def test_detect_clean_architecture():
    """Should detect Clean Architecture layers"""
    analyzer = ArchitectureAnalyzer("tests/fixtures/clean-arch-project", mock_stack)
    result = analyzer.analyze()

    clean_arch = next((p for p in result.patterns if p.pattern == ArchitecturePattern.CLEAN_ARCHITECTURE), None)

    assert clean_arch is not None
    assert 'Domain' in result.layers
    assert 'Infrastructure' in result.layers
```

## Files to Create

1. `installer/global/commands/lib/architecture_analyzer.py` - Main analyzer (~500 lines)
2. `installer/global/commands/lib/architecture_analyzer/pattern_detectors.py` - Pattern detection (~350 lines)
3. `installer/global/commands/lib/architecture_analyzer/layer_detector.py` - Layer identification (~200 lines)
4. `tests/unit/test_architecture_analyzer.py` - Unit tests (~400 lines)
5. `tests/fixtures/` - Test project fixtures (MVVM, Clean Architecture)

## Definition of Done

- [ ] ArchitectureAnalyzer class implemented
- [ ] MVVM pattern detection working
- [ ] Clean Architecture layer detection working
- [ ] Repository pattern detection working
- [ ] Service pattern detection working
- [ ] Domain pattern detection working
- [ ] Returns structured JSON with confidence scores
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration with TASK-037 (uses StackDetectionResult)
- [ ] Documentation and examples

## Success Metrics

- Pattern detection accuracy: >85%
- False positive rate: <15%
- Execution time: <10 seconds for typical project
- Confidence scores correlate with human assessment

## Related Tasks

- **Depends On**: TASK-037 (Technology Stack Detection)
- **Blocks**: TASK-042 (Manifest Generator)
- **Blocks**: TASK-050 (Agent Matching Algorithm)
- **Epic**: EPIC-001 (Template Creation Automation)

---

**Estimated Time**: 7 hours
**Complexity**: 6/10 (Medium-High)
**Priority**: HIGH (Core pattern extraction)
