---
id: TASK-038A
title: Generic Structure Analyzer
status: backlog
created: 2025-11-01T18:15:00Z
priority: high
complexity: 6
estimated_hours: 6
tags: [architecture-detection, technology-agnostic, structure-analysis]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037A]
blocks: [TASK-038]
---

# TASK-038A: Generic Structure Analyzer

## Objective

Create language-agnostic directory structure analyzer to infer architectural patterns from folder organization, naming conventions, and file relationships - working for ANY technology stack.

**Current Problem:** Architecture detection hardcoded to specific languages
**Solution:** Universal pattern detection based on structural heuristics

## Acceptance Criteria

- [ ] Directory structure analysis (recursively map project tree)
- [ ] Layer detection from folder names (universal patterns)
- [ ] Pattern inference from organization (MVVM, Clean Arch, MVC, etc.)
- [ ] Confidence scoring for detected patterns
- [ ] Multi-pattern support (projects can use multiple patterns)
- [ ] Works for Go, Rust, Java, Ruby, Python, .NET, JavaScript, etc.
- [ ] Graceful handling of non-standard structures
- [ ] Unit tests for 10+ different project structures
- [ ] Documentation of detection heuristics

## Implementation

### 1. Universal Structure Patterns

```python
# src/commands/template_create/structure_analyzer.py

from dataclasses import dataclass
from typing import Dict, List, Set, Optional
from pathlib import Path
from enum import Enum

class ArchitecturePattern(Enum):
    """Universal architecture patterns"""
    CLEAN_ARCHITECTURE = "clean_architecture"
    MVVM = "mvvm"
    MVC = "mvc"
    HEXAGONAL = "hexagonal"
    LAYERED = "layered"
    MICROSERVICE = "microservice"
    REPOSITORY = "repository"
    SERVICE_LAYER = "service_layer"
    FEATURE_SLICED = "feature_sliced"
    DOMAIN_DRIVEN = "domain_driven"
    MONOREPO = "monorepo"

@dataclass
class LayerIndicators:
    """Universal indicators for architectural layers"""
    folder_names: Set[str]
    file_patterns: Set[str]
    typical_neighbors: Set[str]  # Layers that commonly co-exist

# Universal layer patterns (work across all languages)
LAYER_PATTERNS = {
    "domain": LayerIndicators(
        folder_names={
            "domain", "domains", "core", "entities", "models",
            "business", "business_logic", "kernel"
        },
        file_patterns={
            "*entity*", "*model*", "*domain*", "*aggregate*",
            "*value_object*", "*vo*"
        },
        typical_neighbors={"application", "infrastructure", "api"}
    ),
    "application": LayerIndicators(
        folder_names={
            "application", "app", "use_cases", "usecases",
            "services", "features", "commands", "queries"
        },
        file_patterns={
            "*service*", "*usecase*", "*command*", "*query*",
            "*handler*", "*interactor*"
        },
        typical_neighbors={"domain", "infrastructure", "presentation"}
    ),
    "infrastructure": LayerIndicators(
        folder_names={
            "infrastructure", "infra", "data", "persistence",
            "repository", "repositories", "dal", "adapters"
        },
        file_patterns={
            "*repository*", "*repo*", "*dao*", "*adapter*",
            "*gateway*", "*client*"
        },
        typical_neighbors={"domain", "application"}
    ),
    "presentation": LayerIndicators(
        folder_names={
            "presentation", "ui", "views", "pages", "components",
            "controllers", "api", "web", "frontend", "viewmodels"
        },
        file_patterns={
            "*controller*", "*view*", "*component*", "*page*",
            "*viewmodel*", "*vm*", "*presenter*"
        },
        typical_neighbors={"application", "ui"}
    ),
    "api": LayerIndicators(
        folder_names={
            "api", "apis", "endpoints", "routes", "handlers",
            "controllers", "rest", "graphql", "grpc"
        },
        file_patterns={
            "*controller*", "*endpoint*", "*route*", "*handler*",
            "*api*", "*resource*"
        },
        typical_neighbors={"application", "domain"}
    ),
    "tests": LayerIndicators(
        folder_names={
            "test", "tests", "spec", "specs", "__tests__",
            "test_*", "*_test", "integration", "e2e"
        },
        file_patterns={
            "*test*", "*spec*", "*_test*", "test_*"
        },
        typical_neighbors=set()  # Can exist anywhere
    ),
}

@dataclass
class PatternSignature:
    """Signature for detecting architecture patterns"""
    required_layers: Set[str]
    optional_layers: Set[str]
    folder_naming_hints: Set[str]
    confidence_threshold: int  # 0-100

# Pattern signatures (language-agnostic)
PATTERN_SIGNATURES = {
    ArchitecturePattern.CLEAN_ARCHITECTURE: PatternSignature(
        required_layers={"domain", "application"},
        optional_layers={"infrastructure", "presentation", "api"},
        folder_naming_hints={
            "clean", "core", "use_cases", "entities",
            "adapters", "gateways"
        },
        confidence_threshold=60
    ),
    ArchitecturePattern.MVVM: PatternSignature(
        required_layers={"presentation"},
        optional_layers={"domain", "infrastructure"},
        folder_naming_hints={
            "viewmodel", "viewmodels", "views", "models",
            "vm", "mvvm"
        },
        confidence_threshold=50
    ),
    ArchitecturePattern.MVC: PatternSignature(
        required_layers={"presentation"},
        optional_layers={"domain"},
        folder_naming_hints={
            "controller", "controllers", "views", "models",
            "mvc"
        },
        confidence_threshold=50
    ),
    ArchitecturePattern.HEXAGONAL: PatternSignature(
        required_layers={"domain", "infrastructure"},
        optional_layers={"application", "api"},
        folder_naming_hints={
            "port", "ports", "adapter", "adapters", "hexagonal",
            "core", "gateway", "gateways"
        },
        confidence_threshold=60
    ),
    ArchitecturePattern.LAYERED: PatternSignature(
        required_layers={"presentation", "application"},
        optional_layers={"domain", "infrastructure"},
        folder_naming_hints={
            "layer", "layers", "tier", "tiers"
        },
        confidence_threshold=40
    ),
    ArchitecturePattern.REPOSITORY: PatternSignature(
        required_layers={"infrastructure"},
        optional_layers={"domain"},
        folder_naming_hints={
            "repository", "repositories", "repo", "repos"
        },
        confidence_threshold=30
    ),
    ArchitecturePattern.FEATURE_SLICED: PatternSignature(
        required_layers=set(),
        optional_layers={"domain", "application"},
        folder_naming_hints={
            "feature", "features", "module", "modules",
            "bounded_context", "contexts"
        },
        confidence_threshold=40
    ),
}
```

### 2. Generic Structure Analyzer

```python
# src/commands/template_create/structure_analyzer.py (continued)

from collections import Counter

@dataclass
class LayerDetection:
    """Detected architectural layer"""
    layer_name: str
    paths: List[Path]
    confidence: int  # 0-100
    evidence: List[str]

@dataclass
class PatternDetection:
    """Detected architecture pattern"""
    pattern: ArchitecturePattern
    confidence: int  # 0-100
    detected_layers: List[LayerDetection]
    evidence: Dict[str, any]

class GenericStructureAnalyzer:
    """Language-agnostic structure analysis"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.directory_tree = self._build_tree()

    def _build_tree(self) -> Dict[str, List[Path]]:
        """Build directory tree (depth-first)"""
        tree = {}
        for path in self.project_root.rglob("*"):
            if path.is_dir():
                # Skip common exclusions
                if any(skip in path.name for skip in [
                    "node_modules", "venv", ".git", "dist", "build",
                    "__pycache__", ".next", "target", "bin", "obj"
                ]):
                    continue

                relative = path.relative_to(self.project_root)
                tree[str(relative)] = list(path.iterdir())

        return tree

    def detect_layers(self) -> List[LayerDetection]:
        """Detect architectural layers from structure"""
        detected_layers = []

        for layer_name, indicators in LAYER_PATTERNS.items():
            paths = []
            evidence = []

            # Check folder names
            for dir_path in self.directory_tree.keys():
                dir_name = Path(dir_path).name.lower()

                # Direct match
                if dir_name in indicators.folder_names:
                    paths.append(self.project_root / dir_path)
                    evidence.append(f"Folder name '{dir_name}' matches {layer_name} layer")

                # Partial match (e.g., "user_services" matches "services")
                for pattern in indicators.folder_names:
                    if pattern in dir_name:
                        paths.append(self.project_root / dir_path)
                        evidence.append(f"Folder '{dir_name}' contains pattern '{pattern}'")

            if paths:
                # Confidence based on number of matches and evidence strength
                confidence = min(100, len(paths) * 30 + len(evidence) * 10)

                detected_layers.append(LayerDetection(
                    layer_name=layer_name,
                    paths=paths,
                    confidence=confidence,
                    evidence=evidence
                ))

        return detected_layers

    def detect_patterns(
        self,
        detected_layers: List[LayerDetection]
    ) -> List[PatternDetection]:
        """Detect architecture patterns from layers"""
        detected_patterns = []
        layer_names = {layer.layer_name for layer in detected_layers}

        for pattern, signature in PATTERN_SIGNATURES.items():
            # Check if required layers present
            if not signature.required_layers.issubset(layer_names):
                continue

            # Calculate confidence
            confidence = 0
            evidence = {}

            # Required layers present: +40 points
            confidence += 40

            # Optional layers present: +10 points each (max 30)
            optional_present = signature.optional_layers.intersection(layer_names)
            confidence += min(30, len(optional_present) * 10)

            # Naming hints in folder structure: +5 points each (max 30)
            folder_hint_count = 0
            for dir_path in self.directory_tree.keys():
                dir_lower = dir_path.lower()
                for hint in signature.folder_naming_hints:
                    if hint in dir_lower:
                        folder_hint_count += 1

            confidence += min(30, folder_hint_count * 5)

            # Must meet threshold
            if confidence < signature.confidence_threshold:
                continue

            evidence = {
                "required_layers_found": list(signature.required_layers),
                "optional_layers_found": list(optional_present),
                "folder_hints_found": folder_hint_count,
            }

            detected_patterns.append(PatternDetection(
                pattern=pattern,
                confidence=min(100, confidence),
                detected_layers=[
                    layer for layer in detected_layers
                    if layer.layer_name in signature.required_layers.union(signature.optional_layers)
                ],
                evidence=evidence
            ))

        # Sort by confidence
        detected_patterns.sort(key=lambda p: p.confidence, reverse=True)

        return detected_patterns

    def analyze(self) -> Dict[str, any]:
        """
        Complete structure analysis

        Returns:
            {
                'layers': List[LayerDetection],
                'patterns': List[PatternDetection],
                'primary_pattern': Optional[PatternDetection],
                'directory_count': int,
                'max_depth': int
            }
        """
        layers = self.detect_layers()
        patterns = self.detect_patterns(layers)

        # Calculate tree metrics
        max_depth = max(
            (len(Path(p).parts) for p in self.directory_tree.keys()),
            default=0
        )

        return {
            'layers': layers,
            'patterns': patterns,
            'primary_pattern': patterns[0] if patterns else None,
            'directory_count': len(self.directory_tree),
            'max_depth': max_depth,
        }
```

### 3. Integration Helper

```python
# For easy integration with TASK-038

def get_generic_structure_analysis(project_root: Path) -> Dict[str, any]:
    """
    One-line helper for getting structure analysis

    Usage:
        analysis = get_generic_structure_analysis(Path("/project"))
        primary_pattern = analysis['primary_pattern']
        if primary_pattern:
            print(f"Detected: {primary_pattern.pattern.value}")
    """
    analyzer = GenericStructureAnalyzer(project_root)
    return analyzer.analyze()
```

## Testing Strategy

```python
# tests/test_generic_structure_analyzer.py

def test_clean_architecture_detection():
    """Test detection of Clean Architecture (Go project)"""
    # Setup: Create Go project structure
    project = create_test_structure({
        "domain/": ["user.go", "order.go"],
        "application/usecases/": ["create_user.go"],
        "infrastructure/repository/": ["user_repo.go"],
        "api/handlers/": ["user_handler.go"],
    })

    analyzer = GenericStructureAnalyzer(project)
    result = analyzer.analyze()

    # Should detect Clean Architecture
    assert result['primary_pattern'].pattern == ArchitecturePattern.CLEAN_ARCHITECTURE
    assert result['primary_pattern'].confidence >= 60

    # Should detect layers
    layer_names = {layer.layer_name for layer in result['layers']}
    assert "domain" in layer_names
    assert "application" in layer_names
    assert "infrastructure" in layer_names

def test_mvvm_detection():
    """Test MVVM detection (Rust project)"""
    project = create_test_structure({
        "viewmodels/": ["user_vm.rs"],
        "views/": ["user_view.rs"],
        "models/": ["user.rs"],
    })

    analyzer = GenericStructureAnalyzer(project)
    result = analyzer.analyze()

    assert result['primary_pattern'].pattern == ArchitecturePattern.MVVM

def test_repository_pattern_detection():
    """Test Repository pattern (Java project)"""
    project = create_test_structure({
        "repository/": ["UserRepository.java"],
        "model/": ["User.java"],
        "service/": ["UserService.java"],
    })

    analyzer = GenericStructureAnalyzer(project)
    result = analyzer.analyze()

    patterns = {p.pattern for p in result['patterns']}
    assert ArchitecturePattern.REPOSITORY in patterns

def test_unknown_structure():
    """Test graceful handling of unknown structure"""
    project = create_test_structure({
        "weird/": ["stuff.xyz"],
        "random/": ["things.abc"],
    })

    analyzer = GenericStructureAnalyzer(project)
    result = analyzer.analyze()

    # Should not crash
    assert result['patterns'] == [] or result['patterns'][0].confidence < 40
```

## Definition of Done

- [ ] Universal layer detection implemented
- [ ] Pattern inference from structure working
- [ ] Confidence scoring accurate
- [ ] Works for Go, Rust, Java, Python, Ruby, .NET, JavaScript projects
- [ ] Graceful handling of non-standard structures
- [ ] Multi-pattern detection supported
- [ ] Unit tests for 10+ structures passing
- [ ] Documentation of detection heuristics
- [ ] Integration ready for TASK-038

**Estimated Time**: 6 hours | **Complexity**: 6/10 | **Priority**: HIGH

## Impact

Enables architecture pattern detection for ANY technology stack:
- No language-specific AST parsing required
- Works from folder structure alone
- Graceful degradation for unknown structures
- Foundation for universal template generation
