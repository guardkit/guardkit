---
id: TASK-005
title: AI-Guided Manifest Generator
status: completed
created: 2025-11-01T20:35:00Z
updated: 2025-11-06T01:00:00Z
completed: 2025-11-06T01:00:00Z
priority: high
complexity: 3
estimated_hours: 4
actual_hours: 3.5
tags: [template-generation, manifest, ai-assisted]
epic: EPIC-001
feature: template-generation
dependencies: [TASK-002]
blocks: [TASK-010, TASK-011]
---

# TASK-005: AI-Guided Manifest Generator

## Objective

Generate `manifest.json` from AI-powered codebase analysis containing template metadata, language, frameworks, architecture patterns, and intelligent placeholders.

**Purpose**: Create the manifest file that describes the template's capabilities, structure, and usage for the `agentic-init` command.

## Context

The manifest.json file is the primary metadata file for templates. It's used by:
- `agentic-init` (taskwright) to discover and apply templates
- Template browsers to display template information
- Validation systems to ensure template compatibility

**Input**: `CodebaseAnalysis` from TASK-002
**Output**: `TemplateManifest` (manifest.json)

## Acceptance Criteria

- [ ] Generate complete manifest.json from CodebaseAnalysis
- [ ] Include all required fields (name, version, language, frameworks)
- [ ] AI-extracted architecture patterns and conventions
- [ ] Intelligent placeholder detection and documentation
- [ ] Template metadata (description, author, tags)
- [ ] Compatibility information (language versions, framework versions)
- [ ] Validation of generated manifest structure
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with TASK-010

## Data Contract

### Input: CodebaseAnalysis

```python
@dataclass
class CodebaseAnalysis:
    schema_version: str
    template_name: str
    language: str
    frameworks: List[str]
    architecture_pattern: str
    layers: List[LayerInfo]
    naming_conventions: Dict[str, str]
    good_patterns: List[str]
    anti_patterns: List[str]
    example_files: List[ExampleFile]
    suggested_agents: List[str]
    project_root: Path
    analyzed_at: datetime
    confidence_score: float
```

### Output: TemplateManifest

```python
@dataclass
class TemplateManifest:
    """Generated manifest.json structure"""
    schema_version: str = "1.0.0"

    # Core identity
    name: str
    display_name: str
    description: str
    version: str  # Template version (semver)
    author: Optional[str] = None

    # Technology stack
    language: str
    language_version: Optional[str] = None
    frameworks: List[FrameworkInfo]
    architecture: str

    # Template structure
    patterns: List[str]  # Architecture patterns used
    layers: List[str]  # Layer names (Domain, Presentation, etc.)
    placeholders: Dict[str, PlaceholderInfo]

    # Usage information
    tags: List[str]
    category: str  # "backend", "frontend", "mobile", "fullstack", etc.
    complexity: int  # 1-10 scale

    # Compatibility
    compatible_with: List[str]  # Other templates this works with
    requires: List[str]  # Required global agents or tools

    # Metadata
    created_at: str  # ISO 8601
    source_project: Optional[str] = None
    confidence_score: float  # From AI analysis

@dataclass
class FrameworkInfo:
    name: str
    version: Optional[str] = None
    purpose: str  # "testing", "ui", "data", etc.

@dataclass
class PlaceholderInfo:
    name: str  # e.g., "{{ProjectName}}"
    description: str
    default_value: Optional[str] = None
    pattern: Optional[str] = None  # Regex for validation
    required: bool = True
```

## Implementation

```python
# src/commands/template_create/manifest_generator.py

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

class ManifestGenerator:
    """Generate manifest.json from AI analysis"""

    def __init__(self, analysis: CodebaseAnalysis):
        self.analysis = analysis

    def generate(self) -> TemplateManifest:
        """
        Generate complete manifest from analysis

        Returns:
            TemplateManifest with all fields populated
        """
        return TemplateManifest(
            schema_version="1.0.0",

            # Core identity
            name=self._generate_name(),
            display_name=self._generate_display_name(),
            description=self._generate_description(),
            version="1.0.0",  # Initial version
            author=self._infer_author(),

            # Technology stack
            language=self.analysis.language,
            language_version=self._infer_language_version(),
            frameworks=self._extract_frameworks(),
            architecture=self.analysis.architecture_pattern,

            # Template structure
            patterns=self._extract_patterns(),
            layers=self._extract_layer_names(),
            placeholders=self._extract_placeholders(),

            # Usage information
            tags=self._generate_tags(),
            category=self._infer_category(),
            complexity=self._calculate_complexity(),

            # Compatibility
            compatible_with=self._infer_compatible_templates(),
            requires=self._extract_requirements(),

            # Metadata
            created_at=datetime.now().isoformat(),
            source_project=str(self.analysis.project_root) if self.analysis.project_root else None,
            confidence_score=self.analysis.confidence_score
        )

    def _generate_name(self) -> str:
        """Generate template name from analysis"""
        # Use analysis template_name if provided
        if self.analysis.template_name:
            return self.analysis.template_name

        # Otherwise infer from language + architecture
        name_parts = [
            self.analysis.language.lower(),
            self.analysis.architecture_pattern.lower().replace(" ", "-")
        ]
        return "-".join(name_parts) + "-template"

    def _generate_display_name(self) -> str:
        """Generate human-friendly display name"""
        return self.analysis.template_name.replace("-", " ").title()

    def _generate_description(self) -> str:
        """Generate template description"""
        # Use AI to generate description if not provided
        # For now, use template
        return f"{self.analysis.language} template using {self.analysis.architecture_pattern} architecture"

    def _infer_author(self) -> Optional[str]:
        """Infer author from git config or environment"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                cwd=self.analysis.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _infer_language_version(self) -> Optional[str]:
        """Infer language version from project files"""
        # Language-specific logic
        if self.analysis.language.lower() == "python":
            return self._infer_python_version()
        elif self.analysis.language.lower() in ["csharp", "c#"]:
            return self._infer_dotnet_version()
        elif self.analysis.language.lower() in ["typescript", "javascript"]:
            return self._infer_node_version()
        return None

    def _infer_python_version(self) -> Optional[str]:
        """Infer Python version from project"""
        # Check pyproject.toml, setup.py, .python-version, etc.
        if not self.analysis.project_root:
            return None

        # Check .python-version
        python_version_file = self.analysis.project_root / ".python-version"
        if python_version_file.exists():
            return python_version_file.read_text().strip()

        # Check pyproject.toml
        pyproject = self.analysis.project_root / "pyproject.toml"
        if pyproject.exists():
            import tomli
            data = tomli.loads(pyproject.read_text())
            python_req = data.get("project", {}).get("requires-python")
            if python_req:
                return python_req

        return None

    def _infer_dotnet_version(self) -> Optional[str]:
        """Infer .NET version from csproj files"""
        # Find .csproj files and extract TargetFramework
        if not self.analysis.project_root:
            return None

        for csproj in self.analysis.project_root.rglob("*.csproj"):
            import xml.etree.ElementTree as ET
            tree = ET.parse(csproj)
            target = tree.find(".//TargetFramework")
            if target is not None:
                return target.text
        return None

    def _infer_node_version(self) -> Optional[str]:
        """Infer Node.js version from package.json"""
        if not self.analysis.project_root:
            return None

        package_json = self.analysis.project_root / "package.json"
        if package_json.exists():
            data = json.loads(package_json.read_text())
            engines = data.get("engines", {})
            return engines.get("node")
        return None

    def _extract_frameworks(self) -> List[FrameworkInfo]:
        """Extract framework information with versions"""
        frameworks = []
        for fw_name in self.analysis.frameworks:
            # Try to infer version and purpose
            frameworks.append(FrameworkInfo(
                name=fw_name,
                version=self._infer_framework_version(fw_name),
                purpose=self._infer_framework_purpose(fw_name)
            ))
        return frameworks

    def _infer_framework_version(self, framework: str) -> Optional[str]:
        """Infer framework version from project files"""
        # Framework-specific logic
        # ... implementation
        return None

    def _infer_framework_purpose(self, framework: str) -> str:
        """Infer framework purpose (testing, ui, data, etc.)"""
        # Map common frameworks to purposes
        testing_frameworks = ["pytest", "jest", "vitest", "xunit", "nunit"]
        ui_frameworks = ["react", "vue", "angular", "maui", "wpf"]
        data_frameworks = ["sqlalchemy", "ef-core", "prisma"]

        fw_lower = framework.lower()
        if any(test in fw_lower for test in testing_frameworks):
            return "testing"
        elif any(ui in fw_lower for ui in ui_frameworks):
            return "ui"
        elif any(data in fw_lower for data in data_frameworks):
            return "data"
        else:
            return "core"

    def _extract_patterns(self) -> List[str]:
        """Extract all architecture patterns"""
        patterns = [self.analysis.architecture_pattern]

        # Add layer-specific patterns
        for layer in self.analysis.layers:
            if hasattr(layer, 'patterns'):
                patterns.extend(layer.patterns)

        # Add good patterns from analysis
        patterns.extend(self.analysis.good_patterns)

        # Deduplicate
        return list(set(patterns))

    def _extract_layer_names(self) -> List[str]:
        """Extract layer names"""
        return [layer.name for layer in self.analysis.layers]

    def _extract_placeholders(self) -> Dict[str, PlaceholderInfo]:
        """
        Extract intelligent placeholders from analysis

        AI identifies common patterns like:
        - Project/solution names
        - Namespace roots
        - Database names
        - API endpoints
        """
        placeholders = {}

        # Standard placeholders (always present)
        placeholders["ProjectName"] = PlaceholderInfo(
            name="{{ProjectName}}",
            description="Name of the project/solution",
            default_value=None,
            pattern="^[A-Za-z][A-Za-z0-9_]*$",
            required=True
        )

        placeholders["Namespace"] = PlaceholderInfo(
            name="{{Namespace}}",
            description="Root namespace for the project",
            default_value=None,
            pattern="^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z][A-Za-z0-9_]*)*$",
            required=True
        )

        # Infer additional placeholders from naming conventions
        for element_type, pattern in self.analysis.naming_conventions.items():
            if "{{" in pattern:
                # Extract placeholder name
                placeholder_name = pattern.split("{{")[1].split("}}")[0]
                if placeholder_name not in placeholders:
                    placeholders[placeholder_name] = PlaceholderInfo(
                        name=f"{{{{{placeholder_name}}}}}",
                        description=f"Value for {element_type}",
                        default_value=None,
                        pattern=None,
                        required=False
                    )

        return placeholders

    def _generate_tags(self) -> List[str]:
        """Generate relevant tags for discoverability"""
        tags = []

        # Language tag
        tags.append(self.analysis.language.lower())

        # Framework tags
        tags.extend([fw.lower() for fw in self.analysis.frameworks])

        # Architecture tag
        tags.append(self.analysis.architecture_pattern.lower().replace(" ", "-"))

        # Layer tags
        tags.extend([layer.name.lower() for layer in self.analysis.layers])

        # Deduplicate
        return list(set(tags))

    def _infer_category(self) -> str:
        """Infer template category"""
        frameworks_lower = [fw.lower() for fw in self.analysis.frameworks]

        # Backend
        if any(fw in frameworks_lower for fw in ["fastapi", "django", "flask", "aspnet", "express"]):
            return "backend"

        # Frontend
        elif any(fw in frameworks_lower for fw in ["react", "vue", "angular", "blazor"]):
            return "frontend"

        # Mobile
        elif any(fw in frameworks_lower for fw in ["maui", "react-native", "flutter"]):
            return "mobile"

        # Desktop
        elif any(fw in frameworks_lower for fw in ["wpf", "winforms", "electron"]):
            return "desktop"

        # Fullstack
        elif any(fw in frameworks_lower for fw in ["nextjs", "nuxt"]):
            return "fullstack"

        else:
            return "general"

    def _calculate_complexity(self) -> int:
        """Calculate template complexity (1-10)"""
        complexity = 1

        # More layers = more complex
        complexity += min(len(self.analysis.layers), 3)

        # More frameworks = more complex
        complexity += min(len(self.analysis.frameworks), 3)

        # More patterns = more complex
        complexity += min(len(self.analysis.good_patterns), 3)

        return min(complexity, 10)

    def _infer_compatible_templates(self) -> List[str]:
        """Infer compatible templates"""
        # This would check global template registry
        # For now, return empty
        return []

    def _extract_requirements(self) -> List[str]:
        """Extract required global agents or tools"""
        requirements = []

        # Based on suggested agents
        for agent in self.analysis.suggested_agents:
            requirements.append(f"agent:{agent}")

        return requirements

    def to_json(self, manifest: TemplateManifest) -> str:
        """Convert manifest to JSON string"""
        return json.dumps(asdict(manifest), indent=2, default=str)

    def save(self, manifest: TemplateManifest, output_path: Path):
        """Save manifest to file"""
        output_path.write_text(self.to_json(manifest))
```

## Testing Strategy

```python
# tests/test_manifest_generator.py

def test_manifest_generation():
    """Test manifest generation from analysis"""
    analysis = create_mock_codebase_analysis()
    generator = ManifestGenerator(analysis)

    manifest = generator.generate()

    assert manifest.schema_version == "1.0.0"
    assert manifest.name == analysis.template_name
    assert manifest.language == analysis.language
    assert len(manifest.frameworks) > 0
    assert len(manifest.placeholders) >= 2  # At least ProjectName and Namespace

def test_placeholder_extraction():
    """Test intelligent placeholder extraction"""
    analysis = create_mock_codebase_analysis()
    generator = ManifestGenerator(analysis)

    placeholders = generator._extract_placeholders()

    # Standard placeholders
    assert "ProjectName" in placeholders
    assert "Namespace" in placeholders
    assert placeholders["ProjectName"].required == True

def test_framework_info_extraction():
    """Test framework information extraction"""
    analysis = create_mock_codebase_analysis(
        frameworks=["FastAPI", "pytest", "SQLAlchemy"]
    )
    generator = ManifestGenerator(analysis)

    frameworks = generator._extract_frameworks()

    # Check purposes
    assert any(fw.purpose == "core" and fw.name == "FastAPI" for fw in frameworks)
    assert any(fw.purpose == "testing" and fw.name == "pytest" for fw in frameworks)
    assert any(fw.purpose == "data" and fw.name == "SQLAlchemy" for fw in frameworks)

def test_complexity_calculation():
    """Test complexity scoring"""
    # Simple project (1 layer, 1 framework)
    simple_analysis = create_mock_codebase_analysis(
        layers=[LayerInfo(name="Application")],
        frameworks=["Flask"]
    )
    simple_generator = ManifestGenerator(simple_analysis)
    assert simple_generator._calculate_complexity() <= 3

    # Complex project (5 layers, 5 frameworks)
    complex_analysis = create_mock_codebase_analysis(
        layers=[LayerInfo(name=f"Layer{i}") for i in range(5)],
        frameworks=[f"Framework{i}" for i in range(5)]
    )
    complex_generator = ManifestGenerator(complex_analysis)
    assert complex_generator._calculate_complexity() >= 7
```

## Integration with TASK-010

```python
# From TASK-010 orchestrator
from manifest_generator import ManifestGenerator

manifest_gen = ManifestGenerator(analysis)
manifest = manifest_gen.generate()

# Validate
validator = TemplateManifestValidator()
result = validator.validate(manifest)

if not result.is_valid:
    raise GenerationError(f"Invalid manifest: {result.errors}")

# Save
manifest_gen.save(manifest, template_dir / "manifest.json")
```

## Definition of Done

- [ ] Complete ManifestGenerator class implemented
- [ ] All fields populated from CodebaseAnalysis
- [ ] Intelligent placeholder detection working
- [ ] Language/framework version inference working
- [ ] Framework purpose classification accurate
- [ ] Complexity calculation reasonable
- [ ] JSON serialization working
- [ ] Validation integration working
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with TASK-010 passing

**Estimated Time**: 4 hours | **Complexity**: 3/10 | **Priority**: HIGH

**Rationale**: Relatively straightforward data transformation with some intelligent inference logic. Most complexity is in framework-specific version detection.

---

**Created**: 2025-11-01
**Updated**: 2025-11-01 (expanded specification)
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Dependencies**: TASK-002 (CodebaseAnalysis)
**Blocks**: TASK-010 (Template Create), TASK-011 (Template Init)
