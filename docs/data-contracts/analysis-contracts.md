# Analysis Data Contracts

**Category**: Codebase Analysis
**Version**: 1.0.0
**Status**: ✅ COMPLETE

---

## Overview

Analysis contracts represent AI-powered codebase analysis results (brownfield) or inferred analysis (greenfield). These contracts are the foundation for template generation.

---

## CodebaseAnalysis

**Source**: TASK-002 (AI-Powered Codebase Analysis)
**Used By**: TASK-002 → TASK-003, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009
**Schema Version**: 1.0.0

### Structure

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class CodebaseAnalysis:
    """AI-powered codebase analysis results"""

    schema_version: str = "1.0.0"

    # Core identity
    template_name: str

    # Technology stack
    technology: TechnologyInfo

    # Architecture
    architecture: ArchitectureInfo

    # Quality assessment
    quality: QualityInfo

    # Project structure
    layers: List[LayerInfo]
    naming_conventions: Dict[str, str]

    # Example files for template generation
    example_files: List[ExampleFile]

    # Agent recommendations
    suggested_agents: List[str]

    # Metadata
    project_root: Optional[Path] = None
    analyzed_at: datetime = None
    confidence_score: float = 0.0  # 0.0 - 1.0
    source: str = "ai_analysis"  # "ai_analysis" | "greenfield" | "manual"
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | str | Yes | Data contract version |
| `template_name` | str | Yes | Name for generated template |
| `technology` | TechnologyInfo | Yes | Technology stack information |
| `architecture` | ArchitectureInfo | Yes | Architecture patterns and structure |
| `quality` | QualityInfo | Yes | Quality assessment results |
| `layers` | List[LayerInfo] | Yes | Project layers (Domain, Presentation, etc.) |
| `naming_conventions` | Dict[str, str] | Yes | Element type → naming pattern |
| `example_files` | List[ExampleFile] | Yes | Good example files for templates |
| `suggested_agents` | List[str] | Yes | Recommended agent capabilities |
| `project_root` | Optional[Path] | No | Source project path (brownfield only) |
| `analyzed_at` | datetime | No | Analysis timestamp |
| `confidence_score` | float | No | AI confidence (0.0-1.0) |
| `source` | str | No | Analysis source type |

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "template_name": "mycompany-maui-mvvm",
  "technology": {
    "language": "C#",
    "language_version": "12.0",
    "frameworks": [
      {"name": ".NET MAUI", "version": "8.0", "purpose": "ui"},
      {"name": "xUnit", "version": "2.6", "purpose": "testing"}
    ],
    "dependencies": ["CommunityToolkit.Mvvm", "ErrorOr"]
  },
  "architecture": {
    "primary_pattern": "MVVM",
    "secondary_patterns": ["Clean Architecture", "CQRS"],
    "domain_modeling": "functional",
    "layer_count": 4
  },
  "quality": {
    "good_patterns": [
      "Verb-based domain operations",
      "ErrorOr<T> for error handling",
      "MVVM with CommunityToolkit"
    ],
    "anti_patterns": [],
    "complexity_score": 6,
    "maintainability_score": 8
  },
  "layers": [
    {
      "name": "Domain",
      "path": "src/Domain",
      "purpose": "Business logic and domain models",
      "patterns": ["Verb-based operations", "ErrorOr<T>"],
      "file_count": 42
    }
  ],
  "naming_conventions": {
    "domain_operation": "{{Verb}}{{Entity}}.cs",
    "view": "{{Entity}}Page.xaml",
    "viewmodel": "{{Entity}}ViewModel.cs"
  },
  "example_files": [
    {
      "path": "src/Domain/Products/GetProducts.cs",
      "purpose": "Domain operation example",
      "quality_score": 9,
      "patterns": ["Verb-based", "ErrorOr<T>"]
    }
  ],
  "suggested_agents": [
    "maui-appshell-specialist",
    "mvvm-specialist",
    "error-pattern-specialist"
  ],
  "project_root": "/Users/dev/my-maui-app",
  "analyzed_at": "2025-11-01T15:30:00Z",
  "confidence_score": 0.92,
  "source": "ai_analysis"
}
```

### Validation Rules

```python
class CodebaseAnalysisValidator(Validator):
    """Validate CodebaseAnalysis"""

    def validate(self, analysis: CodebaseAnalysis) -> ValidationResult:
        errors = []
        warnings = []

        # Schema version
        if not analysis.schema_version:
            errors.append("schema_version is required")

        # Template name
        if not analysis.template_name or len(analysis.template_name) < 3:
            errors.append("template_name must be at least 3 characters")

        # Technology info
        tech_result = TechnologyInfoValidator().validate(analysis.technology)
        if not tech_result.is_valid:
            errors.extend([f"technology.{e}" for e in tech_result.errors])

        # Architecture info
        arch_result = ArchitectureInfoValidator().validate(analysis.architecture)
        if not arch_result.is_valid:
            errors.extend([f"architecture.{e}" for e in arch_result.errors])

        # Quality info
        quality_result = QualityInfoValidator().validate(analysis.quality)
        if not quality_result.is_valid:
            errors.extend([f"quality.{e}" for e in quality_result.errors])

        # Layers
        if not analysis.layers:
            errors.append("At least one layer is required")
        for i, layer in enumerate(analysis.layers):
            layer_result = LayerInfoValidator().validate(layer)
            if not layer_result.is_valid:
                errors.extend([f"layers[{i}].{e}" for e in layer_result.errors])

        # Confidence score
        if not (0.0 <= analysis.confidence_score <= 1.0):
            errors.append(f"confidence_score must be 0.0-1.0, got {analysis.confidence_score}")

        # Low confidence warning
        if analysis.confidence_score < 0.7:
            warnings.append(f"Low confidence score: {analysis.confidence_score}")

        # Logical consistency
        if analysis.architecture.primary_pattern and not analysis.layers:
            errors.append("Architecture pattern specified but no layers defined")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"contract_type": "CodebaseAnalysis"}
        )
```

---

## TechnologyInfo

**Purpose**: Represent technology stack information
**Part Of**: CodebaseAnalysis

### Structure

```python
@dataclass
class TechnologyInfo:
    """Technology stack information"""

    language: str
    language_version: Optional[str] = None
    frameworks: List[FrameworkInfo] = None
    dependencies: List[str] = None
    build_tools: List[str] = None
    package_manager: Optional[str] = None

@dataclass
class FrameworkInfo:
    """Framework details"""
    name: str
    version: Optional[str] = None
    purpose: str  # "ui" | "testing" | "data" | "core" | "build"
```

### Validation Rules

```python
class TechnologyInfoValidator(Validator):
    def validate(self, tech: TechnologyInfo) -> ValidationResult:
        errors = []

        if not tech.language:
            errors.append("language is required")

        if tech.frameworks:
            for i, fw in enumerate(tech.frameworks):
                if not fw.name:
                    errors.append(f"frameworks[{i}].name is required")
                if fw.purpose not in ["ui", "testing", "data", "core", "build", "other"]:
                    errors.append(f"frameworks[{i}].purpose invalid: {fw.purpose}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

---

## ArchitectureInfo

**Purpose**: Represent architecture patterns and structure
**Part Of**: CodebaseAnalysis

### Structure

```python
@dataclass
class ArchitectureInfo:
    """Architecture patterns and structure"""

    primary_pattern: str  # "MVVM" | "Clean" | "Hexagonal" | "Layered" | etc.
    secondary_patterns: List[str] = None
    domain_modeling: str = "anemic"  # "rich" | "anemic" | "functional" | "data-centric"
    layer_count: int = 1
    separation_style: str = "by-layer"  # "by-layer" | "by-feature" | "hybrid"
```

### Validation Rules

```python
class ArchitectureInfoValidator(Validator):
    VALID_PATTERNS = [
        "MVVM", "MVC", "MVP", "Clean Architecture", "Hexagonal",
        "Layered", "Vertical Slice", "Microservices", "Modular Monolith"
    ]

    VALID_DOMAIN_MODELING = ["rich", "anemic", "functional", "data-centric"]
    VALID_SEPARATION = ["by-layer", "by-feature", "hybrid", "single"]

    def validate(self, arch: ArchitectureInfo) -> ValidationResult:
        errors = []

        if not arch.primary_pattern:
            errors.append("primary_pattern is required")
        elif arch.primary_pattern not in self.VALID_PATTERNS:
            errors.append(f"Unknown primary_pattern: {arch.primary_pattern}")

        if arch.domain_modeling not in self.VALID_DOMAIN_MODELING:
            errors.append(f"Invalid domain_modeling: {arch.domain_modeling}")

        if arch.separation_style not in self.VALID_SEPARATION:
            errors.append(f"Invalid separation_style: {arch.separation_style}")

        if arch.layer_count < 1:
            errors.append("layer_count must be at least 1")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

---

## QualityInfo

**Purpose**: Represent quality assessment results
**Part Of**: CodebaseAnalysis

### Structure

```python
@dataclass
class QualityInfo:
    """Quality assessment results"""

    good_patterns: List[str]
    anti_patterns: List[str]
    complexity_score: int  # 1-10 scale
    maintainability_score: int  # 1-10 scale
    test_coverage: Optional[float] = None  # 0.0-1.0
    code_smells: List[str] = None
    recommendations: List[str] = None
```

### Validation Rules

```python
class QualityInfoValidator(Validator):
    def validate(self, quality: QualityInfo) -> ValidationResult:
        errors = []
        warnings = []

        # Complexity score
        if not (1 <= quality.complexity_score <= 10):
            errors.append(f"complexity_score must be 1-10, got {quality.complexity_score}")

        # Maintainability score
        if not (1 <= quality.maintainability_score <= 10):
            errors.append(f"maintainability_score must be 1-10, got {quality.maintainability_score}")

        # Test coverage
        if quality.test_coverage is not None:
            if not (0.0 <= quality.test_coverage <= 1.0):
                errors.append(f"test_coverage must be 0.0-1.0, got {quality.test_coverage}")
            elif quality.test_coverage < 0.5:
                warnings.append(f"Low test coverage: {quality.test_coverage:.0%}")

        # Anti-patterns
        if quality.anti_patterns:
            warnings.append(f"Found {len(quality.anti_patterns)} anti-patterns")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## LayerInfo

**Purpose**: Represent a project layer
**Part Of**: CodebaseAnalysis

### Structure

```python
@dataclass
class LayerInfo:
    """Project layer information"""

    name: str  # "Domain" | "Application" | "Infrastructure" | "Presentation"
    path: str  # Relative path from project root
    purpose: str  # Human-readable description
    patterns: List[str]  # Patterns used in this layer
    file_count: int
    dependencies: List[str] = None  # Other layers this depends on
    conventions: Dict[str, str] = None  # Layer-specific naming conventions
```

### Example JSON

```json
{
  "name": "Domain",
  "path": "src/Domain",
  "purpose": "Business logic and domain models",
  "patterns": ["Verb-based operations", "ErrorOr<T>", "CQRS"],
  "file_count": 42,
  "dependencies": [],
  "conventions": {
    "operation": "{{Verb}}{{Entity}}.cs",
    "entity": "{{Entity}}.cs"
  }
}
```

### Validation Rules

```python
class LayerInfoValidator(Validator):
    COMMON_LAYER_NAMES = [
        "Domain", "Application", "Infrastructure", "Presentation",
        "Core", "API", "Data", "Services", "UI", "Web"
    ]

    def validate(self, layer: LayerInfo) -> ValidationResult:
        errors = []
        warnings = []

        if not layer.name:
            errors.append("name is required")
        elif layer.name not in self.COMMON_LAYER_NAMES:
            warnings.append(f"Uncommon layer name: {layer.name}")

        if not layer.path:
            errors.append("path is required")

        if not layer.purpose:
            errors.append("purpose is required")

        if layer.file_count < 0:
            errors.append(f"file_count cannot be negative: {layer.file_count}")
        elif layer.file_count == 0:
            warnings.append(f"Layer {layer.name} has no files")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## ExampleFile

**Purpose**: Represent a good example file for template generation
**Part Of**: CodebaseAnalysis

### Structure

```python
@dataclass
class ExampleFile:
    """Good example file for template generation"""

    path: str  # Relative path from project root
    purpose: str  # Why this file is a good example
    quality_score: int  # 1-10 scale
    patterns: List[str]  # Patterns demonstrated
    layer: Optional[str] = None  # Which layer it belongs to
    file_type: str = "code"  # "code" | "config" | "test" | "doc"
    size_lines: Optional[int] = None
    complexity: Optional[int] = None  # 1-10 scale
```

### Example JSON

```json
{
  "path": "src/Domain/Products/GetProducts.cs",
  "purpose": "Demonstrates verb-based domain operation with ErrorOr<T> pattern",
  "quality_score": 9,
  "patterns": ["Verb-based operation", "ErrorOr<T>", "CQRS query"],
  "layer": "Domain",
  "file_type": "code",
  "size_lines": 45,
  "complexity": 3
}
```

### Validation Rules

```python
class ExampleFileValidator(Validator):
    VALID_FILE_TYPES = ["code", "config", "test", "doc"]

    def validate(self, file: ExampleFile) -> ValidationResult:
        errors = []
        warnings = []

        if not file.path:
            errors.append("path is required")

        if not file.purpose:
            errors.append("purpose is required")

        if not (1 <= file.quality_score <= 10):
            errors.append(f"quality_score must be 1-10, got {file.quality_score}")

        if file.quality_score < 7:
            warnings.append(f"Low quality score for example: {file.quality_score}")

        if file.file_type not in self.VALID_FILE_TYPES:
            errors.append(f"Invalid file_type: {file.file_type}")

        if file.complexity and not (1 <= file.complexity <= 10):
            errors.append(f"complexity must be 1-10, got {file.complexity}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## Usage Example

```python
# From TASK-002 AI analysis
from ai_analyzer import AICodebaseAnalyzer

analyzer = AICodebaseAnalyzer(qa_context=brownfield_answers)
analysis: CodebaseAnalysis = analyzer.analyze(brownfield_answers.codebase_path)

# Validate
validator = CodebaseAnalysisValidator()
result = validator.validate(analysis)

if not result.is_valid:
    print(f"Analysis validation failed: {result.errors}")
    return

# Use in downstream tasks
from manifest_generator import ManifestGenerator
from settings_generator import SettingsGenerator

manifest_gen = ManifestGenerator(analysis)
manifest = manifest_gen.generate()

settings_gen = SettingsGenerator(analysis)
settings = settings_gen.generate()
```

---

## Greenfield Conversion

For greenfield templates, `GreenfieldAnswers` must be converted to `CodebaseAnalysis`:

```python
class GreenfieldAnalysisAdapter:
    """Convert GreenfieldAnswers to CodebaseAnalysis"""

    def adapt(self, answers: GreenfieldAnswers) -> CodebaseAnalysis:
        """Infer CodebaseAnalysis from greenfield Q&A"""

        return CodebaseAnalysis(
            schema_version="1.0.0",
            template_name=answers.template_name,

            technology=TechnologyInfo(
                language=answers.primary_language,
                language_version=None,  # Will be inferred later
                frameworks=self._infer_frameworks(answers),
                dependencies=[],
                build_tools=self._infer_build_tools(answers),
                package_manager=self._infer_package_manager(answers)
            ),

            architecture=ArchitectureInfo(
                primary_pattern=answers.architecture_pattern,
                secondary_patterns=[],
                domain_modeling=answers.domain_modeling,
                layer_count=self._count_layers(answers),
                separation_style=answers.layer_organization
            ),

            quality=QualityInfo(
                good_patterns=[],  # Greenfield, no patterns yet
                anti_patterns=[],
                complexity_score=self._estimate_complexity(answers),
                maintainability_score=8,  # Default high for new project
                test_coverage=None,
                code_smells=[],
                recommendations=[]
            ),

            layers=self._infer_layers(answers),
            naming_conventions=self._infer_naming(answers),
            example_files=[],  # Greenfield, no examples
            suggested_agents=self._infer_agent_needs(answers),

            project_root=None,  # Greenfield
            analyzed_at=datetime.now(),
            confidence_score=1.0,  # User-provided, high confidence
            source="greenfield"
        )

    def _infer_frameworks(self, answers: GreenfieldAnswers) -> List[FrameworkInfo]:
        """Infer frameworks from answers"""
        frameworks = [
            FrameworkInfo(
                name=answers.framework,
                version=answers.framework_version,
                purpose="core"
            )
        ]

        # Add testing framework
        if answers.unit_testing_framework != "auto":
            frameworks.append(FrameworkInfo(
                name=answers.unit_testing_framework,
                version=None,
                purpose="testing"
            ))

        return frameworks

    def _infer_layers(self, answers: GreenfieldAnswers) -> List[LayerInfo]:
        """Infer layers from organization choice"""
        if answers.layer_organization == "single":
            return [
                LayerInfo(
                    name="Application",
                    path="src",
                    purpose="Main application code",
                    patterns=[],
                    file_count=0
                )
            ]
        elif answers.layer_organization == "by-layer":
            return [
                LayerInfo(name="Domain", path="src/Domain", purpose="Business logic", patterns=[], file_count=0),
                LayerInfo(name="Application", path="src/Application", purpose="Use cases", patterns=[], file_count=0),
                LayerInfo(name="Infrastructure", path="src/Infrastructure", purpose="External concerns", patterns=[], file_count=0),
                LayerInfo(name="Presentation", path="src/Presentation", purpose="UI/API", patterns=[], file_count=0),
            ]
        # ... other organizations
```

---

## Testing

```python
# tests/test_codebase_analysis.py

def test_codebase_analysis_creation():
    """Test CodebaseAnalysis creation"""
    analysis = CodebaseAnalysis(
        schema_version="1.0.0",
        template_name="test-template",
        technology=create_mock_technology_info(),
        architecture=create_mock_architecture_info(),
        quality=create_mock_quality_info(),
        layers=[create_mock_layer_info()],
        naming_conventions={"view": "{{Entity}}View.cs"},
        example_files=[],
        suggested_agents=["test-agent"],
        confidence_score=0.9
    )

    assert analysis.template_name == "test-template"
    assert analysis.confidence_score == 0.9

def test_codebase_analysis_validation():
    """Test validation"""
    validator = CodebaseAnalysisValidator()

    # Valid
    valid = create_valid_codebase_analysis()
    result = validator.validate(valid)
    assert result.is_valid

    # Invalid (low confidence)
    low_confidence = create_valid_codebase_analysis(confidence_score=0.5)
    result = validator.validate(low_confidence)
    assert result.is_valid  # Still valid
    assert len(result.warnings) > 0  # But has warning

def test_greenfield_conversion():
    """Test greenfield to analysis conversion"""
    answers = create_mock_greenfield_answers()
    adapter = GreenfieldAnalysisAdapter()

    analysis = adapter.adapt(answers)

    assert analysis.source == "greenfield"
    assert analysis.confidence_score == 1.0
    assert analysis.template_name == answers.template_name
    assert len(analysis.layers) > 0
```

---

**Created**: 2025-11-01
**Status**: ✅ COMPLETE
**Next**: [agent-contracts.md](agent-contracts.md)
