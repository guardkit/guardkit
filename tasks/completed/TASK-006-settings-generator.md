---
id: TASK-006
title: Settings Generator from AI Analysis
status: completed
created: 2025-11-01T20:40:00Z
updated: 2025-11-06T13:00:00Z
completed: 2025-11-06T13:00:00Z
priority: medium
complexity: 3
estimated_hours: 3
actual_hours: 2
tags: [template-generation, settings, ai-assisted]
epic: EPIC-001
feature: template-generation
dependencies: [TASK-002]
blocks: [TASK-010, TASK-011]
---

# TASK-006: Settings Generator from AI Analysis

## Objective

Generate `settings.json` from AI-provided naming conventions, layer structure, and code style preferences.

**Purpose**: Create the settings file that defines naming conventions, file organization, and code style for the template.

## Context

**Input**: `CodebaseAnalysis` from TASK-002
**Output**: `TemplateSettings` (settings.json)
**Data Contract**: See [template-contracts.md](../../docs/data-contracts/template-contracts.md#templatesettings)

## Acceptance Criteria

- [ ] Generate complete settings.json from CodebaseAnalysis
- [ ] Extract naming conventions from analysis
- [ ] Define file organization preferences
- [ ] Map layer configurations
- [ ] Infer code style preferences
- [ ] Validation of generated settings
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration with TASK-010

## Implementation

```python
# src/commands/template_create/settings_generator.py

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import json

class SettingsGenerator:
    """Generate settings.json from AI analysis"""

    def __init__(self, analysis: CodebaseAnalysis):
        self.analysis = analysis

    def generate(self) -> TemplateSettings:
        """
        Generate complete settings from analysis

        Returns:
            TemplateSettings with all fields populated
        """
        return TemplateSettings(
            schema_version="1.0.0",
            naming_conventions=self._extract_naming_conventions(),
            file_organization=self._infer_file_organization(),
            layer_mappings=self._create_layer_mappings(),
            code_style=self._infer_code_style(),
            generation_options=self._create_generation_options()
        )

    def _extract_naming_conventions(self) -> Dict[str, NamingConvention]:
        """Extract naming conventions from analysis"""
        conventions = {}

        for element_type, pattern in self.analysis.naming_conventions.items():
            conventions[element_type] = NamingConvention(
                element_type=element_type,
                pattern=pattern,
                case_style=self._infer_case_style(pattern),
                prefix=self._extract_prefix(pattern),
                suffix=self._extract_suffix(pattern),
                examples=self._find_examples(element_type)
            )

        return conventions

    def _infer_case_style(self, pattern: str) -> str:
        """Infer case style from pattern"""
        # Check for common patterns
        if "{{" in pattern and "}}" in pattern:
            # Extract sample from pattern
            sample = pattern.split("{{")[0] if pattern.split("{{")[0] else "Sample"
        else:
            sample = pattern

        # Detect case style
        if sample and sample[0].isupper():
            if "_" in sample:
                return "SCREAMING_SNAKE_CASE"
            return "PascalCase"
        elif "_" in sample:
            return "snake_case"
        elif "-" in sample:
            return "kebab-case"
        else:
            return "camelCase"

    def _extract_prefix(self, pattern: str) -> Optional[str]:
        """Extract prefix from pattern if present"""
        # Check if pattern starts with literal text before placeholder
        if "{{" in pattern:
            prefix = pattern.split("{{")[0]
            return prefix if prefix else None
        return None

    def _extract_suffix(self, pattern: str) -> Optional[str]:
        """Extract suffix from pattern if present"""
        # Check if pattern ends with literal text after placeholder
        if "}}" in pattern:
            suffix = pattern.split("}}")[-1]
            return suffix if suffix else None
        return None

    def _find_examples(self, element_type: str) -> List[str]:
        """Find examples from analysis example files"""
        examples = []

        for example_file in self.analysis.example_files:
            # Extract file name as example
            file_name = Path(example_file.path).stem
            examples.append(file_name)

            if len(examples) >= 3:  # Max 3 examples
                break

        return examples

    def _infer_file_organization(self) -> FileOrganization:
        """Infer file organization preferences"""
        # Determine organization style from layer structure
        by_layer = len(self.analysis.layers) > 1
        by_feature = self.analysis.architecture.separation_style == "by-feature"

        return FileOrganization(
            by_layer=by_layer,
            by_feature=by_feature,
            test_location=self._infer_test_location(),
            max_files_per_directory=50  # Reasonable default
        )

    def _infer_test_location(self) -> str:
        """Infer where tests are located"""
        # Check if tests are in separate directory
        test_layer = next(
            (layer for layer in self.analysis.layers if "test" in layer.name.lower()),
            None
        )

        if test_layer:
            # Tests in separate directory structure
            return "separate"

        # Check example files for test file locations
        for example_file in self.analysis.example_files:
            if example_file.file_type == "test":
                if "/tests/" in example_file.path:
                    return "separate"
                elif "Test" in Path(example_file.path).name:
                    return "adjacent"

        # Default to separate
        return "separate"

    def _create_layer_mappings(self) -> Dict[str, LayerMapping]:
        """Create layer mappings from analysis"""
        mappings = {}

        for layer in self.analysis.layers:
            mappings[layer.name] = LayerMapping(
                name=layer.name,
                directory=layer.path,
                namespace_pattern=self._infer_namespace_pattern(layer),
                file_patterns=self._infer_file_patterns(layer)
            )

        return mappings

    def _infer_namespace_pattern(self, layer: LayerInfo) -> Optional[str]:
        """Infer namespace pattern for layer"""
        # Language-specific logic
        lang = self.analysis.technology.language.lower()

        if lang in ["csharp", "c#", "java", "kotlin"]:
            # Namespace-based languages
            return f"{{{{ProjectName}}}}.{layer.name}.{{{{SubPath}}}}"

        elif lang in ["typescript", "javascript"]:
            # Module-based
            return None  # TypeScript uses file paths

        elif lang == "python":
            # Package-based
            return f"{{{{project_name}}}}.{layer.name.lower()}"

        return None

    def _infer_file_patterns(self, layer: LayerInfo) -> List[str]:
        """Infer file patterns for layer"""
        lang = self.analysis.technology.language.lower()

        # Language-specific patterns
        if lang in ["csharp", "c#"]:
            return ["*.cs", "!*Test.cs"]
        elif lang in ["typescript", "javascript"]:
            return ["*.ts", "*.tsx", "!*.test.ts", "!*.spec.ts"]
        elif lang == "python":
            return ["*.py", "!*_test.py", "!test_*.py"]
        elif lang in ["java", "kotlin"]:
            return ["*.java", "*.kt", "!*Test.java", "!*Test.kt"]
        else:
            return ["*"]

    def _infer_code_style(self) -> CodeStyle:
        """Infer code style from language"""
        lang = self.analysis.technology.language.lower()

        # Language-specific defaults
        if lang in ["python"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=88,  # Black default
                trailing_commas=True
            )
        elif lang in ["typescript", "javascript"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=2,
                line_length=100,
                trailing_commas=True
            )
        elif lang in ["csharp", "c#"]:
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=120,
                trailing_commas=False
            )
        else:
            return CodeStyle(
                indentation="spaces",
                indent_size=4,
                line_length=None,
                trailing_commas=False
            )

    def _create_generation_options(self) -> Dict[str, any]:
        """Create generation options"""
        return {
            "preserve_comments": True,
            "preserve_whitespace": True,
            "auto_format": True
        }

    def to_json(self, settings: TemplateSettings) -> str:
        """Convert settings to JSON string"""
        return json.dumps(asdict(settings), indent=2, default=str)

    def save(self, settings: TemplateSettings, output_path: Path):
        """Save settings to file"""
        output_path.write_text(self.to_json(settings))
```

## Testing Strategy

```python
# tests/test_settings_generator.py

def test_settings_generation():
    """Test settings generation from analysis"""
    analysis = create_mock_codebase_analysis()
    generator = SettingsGenerator(analysis)

    settings = generator.generate()

    assert settings.schema_version == "1.0.0"
    assert len(settings.naming_conventions) > 0
    assert settings.file_organization is not None
    assert len(settings.layer_mappings) > 0

def test_naming_convention_extraction():
    """Test naming convention extraction"""
    analysis = create_mock_codebase_analysis(
        naming_conventions={
            "domain_operation": "{{Verb}}{{Entity}}.cs",
            "view": "{{Entity}}Page.xaml"
        }
    )
    generator = SettingsGenerator(analysis)

    conventions = generator._extract_naming_conventions()

    assert "domain_operation" in conventions
    assert conventions["domain_operation"].pattern == "{{Verb}}{{Entity}}.cs"
    assert conventions["domain_operation"].suffix == ".cs"

def test_case_style_inference():
    """Test case style inference"""
    generator = SettingsGenerator(create_mock_codebase_analysis())

    assert generator._infer_case_style("SampleClass") == "PascalCase"
    assert generator._infer_case_style("sampleFunction") == "camelCase"
    assert generator._infer_case_style("sample_var") == "snake_case"
    assert generator._infer_case_style("sample-file") == "kebab-case"

def test_layer_mappings():
    """Test layer mapping creation"""
    analysis = create_mock_codebase_analysis(
        layers=[
            LayerInfo(name="Domain", path="src/Domain", purpose="Business logic", patterns=[], file_count=10)
        ]
    )
    generator = SettingsGenerator(analysis)

    mappings = generator._create_layer_mappings()

    assert "Domain" in mappings
    assert mappings["Domain"].directory == "src/Domain"
    assert mappings["Domain"].namespace_pattern is not None
```

## Integration with TASK-010

```python
# From TASK-010 orchestrator
from settings_generator import SettingsGenerator

settings_gen = SettingsGenerator(analysis)
settings = settings_gen.generate()

# Validate
validator = TemplateSettingsValidator()
result = validator.validate(settings)

if not result.is_valid:
    raise GenerationError(f"Invalid settings: {result.errors}")

# Save
settings_gen.save(settings, template_dir / "settings.json")
```

## Definition of Done

- [ ] Complete SettingsGenerator class implemented
- [ ] Naming conventions extracted from analysis
- [ ] File organization preferences inferred
- [ ] Layer mappings created
- [ ] Code style preferences inferred
- [ ] JSON serialization working
- [ ] Validation integration working
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with TASK-010 passing

**Estimated Time**: 3 hours | **Complexity**: 3/10 | **Priority**: MEDIUM

**Rationale**: Straightforward data transformation with language-specific inference logic.

---

**Created**: 2025-11-01
**Updated**: 2025-11-02 (expanded specification)
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Dependencies**: TASK-002 (CodebaseAnalysis)
**Blocks**: TASK-010 (Template Create), TASK-011 (Template Init)
