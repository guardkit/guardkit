# Template Data Contracts

**Category**: Template Files
**Version**: 1.0.0
**Status**: ✅ COMPLETE

---

## Overview

Template contracts define the structure of generated template files (manifest.json, settings.json, CLAUDE.md, .template files) and the complete template structure.

---

## TemplateManifest

**Source**: TASK-005 (Manifest Generator)
**Used By**: TASK-005 → TASK-010, TASK-011 → agentic-init
**Schema Version**: 1.0.0
**Full Specification**: See TASK-005-manifest-generator.md

### Structure

```python
from dataclasses import dataclass
from typing import List, Dict, Optional

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
    frameworks: List['FrameworkInfo']
    architecture: str

    # Template structure
    patterns: List[str]  # Architecture patterns used
    layers: List[str]  # Layer names
    placeholders: Dict[str, 'PlaceholderInfo']

    # Usage information
    tags: List[str]
    category: str  # "backend" | "frontend" | "mobile" | "desktop" | "fullstack" | "general"
    complexity: int  # 1-10 scale

    # Compatibility
    compatible_with: List[str]  # Other templates
    requires: List[str]  # Required global agents or tools

    # Metadata
    created_at: str  # ISO 8601
    source_project: Optional[str] = None
    confidence_score: float = 1.0

@dataclass
class FrameworkInfo:
    """Framework details"""
    name: str
    version: Optional[str] = None
    purpose: str  # "core" | "testing" | "ui" | "data" | "build"

@dataclass
class PlaceholderInfo:
    """Template placeholder"""
    name: str  # e.g., "{{ProjectName}}"
    description: str
    default_value: Optional[str] = None
    pattern: Optional[str] = None  # Regex for validation
    required: bool = True
```

### Example (see TASK-005 for full details)

```json
{
  "name": "mycompany-maui-mvvm",
  "display_name": "MyCompany MAUI MVVM",
  "version": "1.0.0",
  "language": "C#",
  "frameworks": [{"name": ".NET MAUI", "version": "8.0", "purpose": "ui"}],
  "architecture": "MVVM",
  "category": "mobile",
  "complexity": 6
}
```

---

## TemplateSettings

**Source**: TASK-006 (Settings Generator)
**Used By**: TASK-006 → TASK-010, TASK-011 → agentic-init
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class TemplateSettings:
    """Generated settings.json structure"""

    schema_version: str = "1.0.0"

    # Naming conventions
    naming_conventions: Dict[str, 'NamingConvention']

    # File organization
    file_organization: 'FileOrganization'

    # Layer mappings
    layer_mappings: Dict[str, 'LayerMapping']

    # Code style preferences
    code_style: Optional['CodeStyle'] = None

    # Generator options
    generation_options: Optional[Dict[str, any]] = None

@dataclass
class NamingConvention:
    """Naming convention for an element type"""
    element_type: str  # "class" | "interface" | "file" | "method" | etc.
    pattern: str  # Pattern with placeholders
    case_style: str  # "PascalCase" | "camelCase" | "snake_case" | "kebab-case"
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    examples: List[str] = None

@dataclass
class FileOrganization:
    """File organization preferences"""
    by_layer: bool = True  # Organize files by layer
    by_feature: bool = False  # Organize files by feature
    test_location: str = "separate"  # "separate" | "adjacent" | "mirror"
    max_files_per_directory: Optional[int] = None

@dataclass
class LayerMapping:
    """Layer configuration"""
    name: str
    directory: str  # Relative path
    namespace_pattern: Optional[str] = None
    file_patterns: List[str] = None  # File name patterns for this layer

@dataclass
class CodeStyle:
    """Code style preferences"""
    indentation: str = "spaces"  # "spaces" | "tabs"
    indent_size: int = 4
    line_length: Optional[int] = None
    trailing_commas: bool = False
```

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "naming_conventions": {
    "domain_operation": {
      "element_type": "class",
      "pattern": "{{Verb}}{{Entity}}",
      "case_style": "PascalCase",
      "suffix": null,
      "examples": ["GetProducts", "CreateOrder"]
    },
    "view": {
      "element_type": "file",
      "pattern": "{{Entity}}Page",
      "case_style": "PascalCase",
      "suffix": ".xaml",
      "examples": ["ProductListPage.xaml"]
    }
  },
  "file_organization": {
    "by_layer": true,
    "by_feature": false,
    "test_location": "separate",
    "max_files_per_directory": 50
  },
  "layer_mappings": {
    "Domain": {
      "name": "Domain",
      "directory": "src/Domain",
      "namespace_pattern": "{{ProjectName}}.Domain.{{SubPath}}",
      "file_patterns": ["*.cs", "!*Test.cs"]
    }
  },
  "code_style": {
    "indentation": "spaces",
    "indent_size": 4,
    "line_length": 120,
    "trailing_commas": false
  }
}
```

### Validation Rules

```python
class TemplateSettingsValidator(Validator):
    VALID_CASE_STYLES = ["PascalCase", "camelCase", "snake_case", "kebab-case", "SCREAMING_SNAKE_CASE"]
    VALID_TEST_LOCATIONS = ["separate", "adjacent", "mirror"]

    def validate(self, settings: TemplateSettings) -> ValidationResult:
        errors = []

        # Naming conventions
        if not settings.naming_conventions:
            errors.append("naming_conventions is required")
        else:
            for key, conv in settings.naming_conventions.items():
                if conv.case_style not in self.VALID_CASE_STYLES:
                    errors.append(f"Invalid case_style in {key}: {conv.case_style}")

        # File organization
        if settings.file_organization:
            if settings.file_organization.test_location not in self.VALID_TEST_LOCATIONS:
                errors.append(f"Invalid test_location: {settings.file_organization.test_location}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

---

## TemplateClaude

**Source**: TASK-007 (CLAUDE.md Generator)
**Used By**: TASK-007 → TASK-010, TASK-011
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class TemplateClaude:
    """Generated CLAUDE.md structure"""

    schema_version: str = "1.0.0"

    # Content sections
    architecture_overview: str  # Markdown describing architecture
    technology_stack: str  # Markdown describing tech stack
    project_structure: str  # Markdown describing folder structure
    naming_conventions: str  # Markdown describing naming rules
    patterns: str  # Markdown describing patterns to follow
    examples: str  # Markdown with code examples
    quality_standards: str  # Markdown with quality guidelines
    agent_usage: str  # Markdown describing which agents to use when

    # Metadata
    generated_at: str  # ISO 8601
    confidence_score: float = 1.0
```

### Example

```python
claude = TemplateClaude(
    architecture_overview="""
# Architecture Overview

This template follows MVVM (Model-View-ViewModel) pattern with Clean Architecture principles.

## Layers
- **Domain**: Business logic and entities
- **Application**: Use cases and application services
- **Infrastructure**: External concerns (database, API)
- **Presentation**: UI (XAML views and ViewModels)
    """,

    technology_stack="""
# Technology Stack

- **Language**: C# 12.0
- **Framework**: .NET MAUI 8.0
- **Architecture**: MVVM + Clean Architecture
- **Error Handling**: ErrorOr<T> pattern
- **Testing**: xUnit + FluentAssertions
    """,

    naming_conventions="""
# Naming Conventions

## Domain Operations
- Pattern: `{{Verb}}{{Entity}}.cs`
- Examples: `GetProducts.cs`, `CreateOrder.cs`

## Views
- Pattern: `{{Entity}}Page.xaml`
- Examples: `ProductListPage.xaml`
    """,

    # ... other sections
)
```

### Conversion to Markdown

```python
def to_markdown(self) -> str:
    """Convert TemplateClaude to full CLAUDE.md content"""
    sections = [
        f"# Claude Code Project Instructions",
        f"",
        f"**Generated**: {self.generated_at}",
        f"**Confidence**: {self.confidence_score:.0%}",
        f"",
        self.architecture_overview,
        "",
        self.technology_stack,
        "",
        self.project_structure,
        "",
        self.naming_conventions,
        "",
        self.patterns,
        "",
        self.examples,
        "",
        self.quality_standards,
        "",
        self.agent_usage
    ]
    return "\n".join(sections)
```

---

## CodeTemplate

**Source**: TASK-008 (Template Generator)
**Used By**: TASK-008 → TASK-010, TASK-011
**Schema Version**: 1.0.0

### Structure

```python
@dataclass
class CodeTemplate:
    """Individual .template file"""

    schema_version: str = "1.0.0"

    # Template identity
    name: str  # File name (e.g., "DomainOperation.cs.template")
    original_path: str  # Original file path that was templated
    template_path: str  # Where to save in template

    # Content
    content: str  # Template content with placeholders
    placeholders: List[str]  # List of placeholder names used

    # Metadata
    file_type: str  # "code" | "config" | "doc" | "test"
    language: Optional[str] = None
    purpose: str = ""  # Human-readable description
    quality_score: int = 0  # 1-10 scale
    patterns: List[str] = None  # Patterns demonstrated

@dataclass
class TemplateCollection:
    """Collection of code templates"""
    templates: List[CodeTemplate]
    total_count: int = 0
    by_type: Dict[str, int] = None  # Count by file_type
```

### Example

```python
template = CodeTemplate(
    name="DomainOperation.cs.template",
    original_path="src/Domain/Products/GetProducts.cs",
    template_path="templates/Domain/DomainOperation.cs.template",

    content="""
using ErrorOr;

namespace {{Namespace}}.Domain.{{Entity}}s;

public sealed class {{Verb}}{{Entity}}
{
    public ErrorOr<List<{{Entity}}>> Execute()
    {
        // Implementation
        return new List<{{Entity}}>();
    }
}
    """,

    placeholders=["Namespace", "Entity", "Verb"],
    file_type="code",
    language="csharp",
    purpose="Demonstrates verb-based domain operation with ErrorOr<T>",
    quality_score=9,
    patterns=["Verb-based operation", "ErrorOr<T>", "CQRS"]
)
```

---

## Template (Complete Structure)

**Purpose**: Represent complete template structure on disk
**Used By**: agentic-init command

### Structure

```python
@dataclass
class Template:
    """Complete template structure"""

    # Template root directory
    root_path: Path

    # Core files
    manifest: TemplateManifest
    settings: TemplateSettings
    claude_md: str  # Full CLAUDE.md content

    # Agents
    agents: List[str]  # Agent definition file names

    # Code templates
    templates: TemplateCollection

    # Additional files
    readme: Optional[str] = None
    gitignore: Optional[str] = None

@dataclass
class TemplateStructure:
    """Expected template directory structure"""

    # Required files
    manifest_json: Path  # manifest.json
    settings_json: Path  # settings.json
    claude_md: Path  # CLAUDE.md

    # Required directories
    agents_dir: Path  # agents/
    templates_dir: Path  # templates/

    # Optional files
    readme: Optional[Path] = None
    gitignore: Optional[Path] = None
```

### Directory Layout

```
template-name/
├── manifest.json          # TemplateManifest
├── settings.json          # TemplateSettings
├── CLAUDE.md              # Generated documentation
├── README.md              # Optional
├── .gitignore             # Optional
├── agents/                # Agent definitions
│   ├── agent1.md
│   ├── agent2.md
│   └── ...
└── templates/             # Code templates
    ├── Domain/
    │   └── DomainOperation.cs.template
    ├── Presentation/
    │   └── Page.xaml.template
    └── ...
```

---

## Usage Example

```python
# Load complete template
from template_loader import TemplateLoader

loader = TemplateLoader()
template: Template = loader.load("installer/local/templates/mycompany-maui")

# Validate structure
validator = TemplateValidator()
result = validator.validate(template)

if not result.is_valid:
    raise TemplateError(result.errors)

# Apply template
from template_applicator import TemplateApplicator

applicator = TemplateApplicator(template)
applicator.apply(
    target_dir=Path("/new/project"),
    placeholders={
        "ProjectName": "MyApp",
        "Namespace": "MyCompany.MyApp"
    }
)
```

---

## Validation

```python
class TemplateValidator(Validator):
    """Validate complete template structure"""

    def validate(self, template: Template) -> ValidationResult:
        errors = []
        warnings = []

        # Validate manifest
        manifest_result = TemplateManifestValidator().validate(template.manifest)
        if not manifest_result.is_valid:
            errors.extend([f"manifest: {e}" for e in manifest_result.errors])

        # Validate settings
        settings_result = TemplateSettingsValidator().validate(template.settings)
        if not settings_result.is_valid:
            errors.extend([f"settings: {e}" for e in settings_result.errors])

        # Check required files exist
        required_files = [
            template.root_path / "manifest.json",
            template.root_path / "settings.json",
            template.root_path / "CLAUDE.md"
        ]

        for file_path in required_files:
            if not file_path.exists():
                errors.append(f"Required file missing: {file_path.name}")

        # Check agents directory
        agents_dir = template.root_path / "agents"
        if not agents_dir.exists():
            warnings.append("No agents directory found")
        elif not list(agents_dir.glob("*.md")):
            warnings.append("Agents directory is empty")

        # Check templates directory
        templates_dir = template.root_path / "templates"
        if not templates_dir.exists():
            warnings.append("No templates directory found")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

---

## Testing

```python
# tests/test_template_contracts.py

def test_template_manifest_creation():
    """Test TemplateManifest creation"""
    manifest = TemplateManifest(
        name="test-template",
        display_name="Test Template",
        description="Test",
        version="1.0.0",
        language="Python",
        frameworks=[],
        architecture="Clean",
        patterns=[],
        layers=[],
        placeholders={},
        tags=["python"],
        category="backend",
        complexity=3,
        compatible_with=[],
        requires=[],
        created_at="2025-11-01T00:00:00Z"
    )

    assert manifest.name == "test-template"
    assert manifest.complexity == 3

def test_template_settings_validation():
    """Test settings validation"""
    validator = TemplateSettingsValidator()

    # Valid settings
    valid = TemplateSettings(
        naming_conventions={
            "class": NamingConvention(
                element_type="class",
                pattern="{{Name}}",
                case_style="PascalCase"
            )
        },
        file_organization=FileOrganization(by_layer=True),
        layer_mappings={}
    )
    result = validator.validate(valid)
    assert result.is_valid

def test_code_template():
    """Test CodeTemplate"""
    template = CodeTemplate(
        name="Example.template",
        original_path="src/Example.cs",
        template_path="templates/Example.template",
        content="class {{Name}} {}",
        placeholders=["Name"],
        file_type="code",
        language="csharp",
        quality_score=8
    )

    assert "{{Name}}" in template.content
    assert len(template.placeholders) == 1

def test_complete_template_validation():
    """Test complete template validation"""
    template = create_mock_template()
    validator = TemplateValidator()

    result = validator.validate(template)
    assert result.is_valid or len(result.warnings) > 0
```

---

**Created**: 2025-11-01
**Status**: ✅ COMPLETE
**Next**: [orchestration-contracts.md](orchestration-contracts.md)
