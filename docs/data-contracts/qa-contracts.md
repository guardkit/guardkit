# Q&A Session Data Contracts

**Category**: Q&A Sessions
**Version**: 1.0.0
**Status**: ✅ COMPLETE

---

## Overview

Q&A session contracts capture user responses from interactive sessions for brownfield (`/template-create`) and greenfield (`/template-init`) template creation workflows.

---

## BrownfieldAnswers

**Source**: TASK-001 (Interactive Q&A Session for /template-create)
**Used By**: TASK-001 → TASK-002
**Schema Version**: 1.0.0

### Structure

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime

@dataclass
class BrownfieldAnswers:
    """Answers from /template-create Q&A session"""

    schema_version: str = "1.0.0"

    # Core template identity
    purpose: str  # "new_projects" | "share_structure" | "document_patterns" | "variations"
    codebase_path: Path
    template_name: str

    # Analysis scope
    scope: List[str]  # ["structure", "patterns", "config", "build", "docs", "tests"]
    quality_focus: str  # "all" | "good" | "specific"
    naming_consistency: str  # "high" | "medium" | "low"

    # Optional architecture hint
    known_pattern: Optional[str] = None  # e.g., "MVVM", "Clean Architecture"

    # Exclusions
    exclusions: List[str] = None  # File/folder patterns to exclude

    # Documentation input (Priority 1 - added 2025-11-02)
    documentation_paths: Optional[List[Path]] = None  # File paths to documentation
    documentation_text: Optional[str] = None  # Pasted documentation text
    documentation_urls: Optional[List[str]] = None  # URLs to documentation
    documentation_usage: Optional[str] = None  # "strict" | "guidance" | "naming" | "reasoning"

    # Session metadata
    session_id: str = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | str | Yes | Data contract version (semver) |
| `purpose` | str | Yes | Primary template purpose (enum) |
| `codebase_path` | Path | Yes | Path to existing codebase to analyze |
| `template_name` | str | Yes | Name for generated template |
| `scope` | List[str] | Yes | What to include in template extraction |
| `quality_focus` | str | Yes | How AI should evaluate code quality |
| `naming_consistency` | str | Yes | Consistency level of naming conventions |
| `known_pattern` | Optional[str] | No | Architecture pattern hint (if known) |
| `exclusions` | List[str] | No | Additional folders/files to exclude |
| `documentation_paths` | Optional[List[Path]] | No | File paths to documentation (ADRs, standards, etc.) |
| `documentation_text` | Optional[str] | No | Documentation pasted as text |
| `documentation_urls` | Optional[List[str]] | No | URLs to documentation resources |
| `documentation_usage` | Optional[str] | No | How to use documentation: "strict", "guidance", "naming", "reasoning" |
| `session_id` | str | No | Unique session identifier |
| `created_at` | datetime | No | Session start timestamp |
| `completed_at` | Optional[datetime] | No | Session completion timestamp |

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "purpose": "new_projects",
  "codebase_path": "/Users/dev/my-maui-app",
  "template_name": "mycompany-maui-mvvm",
  "scope": ["structure", "patterns", "config", "tests"],
  "quality_focus": "good",
  "naming_consistency": "high",
  "known_pattern": "MVVM",
  "exclusions": ["bin", "obj", ".vs"],
  "documentation_paths": ["/docs/architecture/ADR-001-mvvm-pattern.md", "/docs/standards/coding-standards.md"],
  "documentation_text": null,
  "documentation_urls": null,
  "documentation_usage": "guidance",
  "session_id": "qa-20251101-143022",
  "created_at": "2025-11-01T14:30:22Z",
  "completed_at": "2025-11-01T14:35:45Z"
}
```

### Validation Rules

```python
class BrownfieldAnswersValidator(Validator):
    """Validate BrownfieldAnswers"""

    VALID_PURPOSES = ["new_projects", "share_structure", "document_patterns", "variations"]
    VALID_SCOPES = ["structure", "patterns", "config", "build", "docs", "tests"]
    VALID_QUALITY_FOCUS = ["all", "good", "specific"]
    VALID_NAMING = ["high", "medium", "low"]

    def validate(self, answers: BrownfieldAnswers) -> ValidationResult:
        errors = []

        # Schema version
        if not answers.schema_version:
            errors.append("schema_version is required")

        # Purpose
        if answers.purpose not in self.VALID_PURPOSES:
            errors.append(f"Invalid purpose: {answers.purpose}")

        # Codebase path
        if not answers.codebase_path or not Path(answers.codebase_path).exists():
            errors.append(f"Codebase path does not exist: {answers.codebase_path}")

        # Template name
        if not answers.template_name or len(answers.template_name) < 3:
            errors.append("Template name must be at least 3 characters")

        # Scope
        if not answers.scope:
            errors.append("At least one scope item is required")
        for item in answers.scope:
            if item not in self.VALID_SCOPES:
                errors.append(f"Invalid scope item: {item}")

        # Quality focus
        if answers.quality_focus not in self.VALID_QUALITY_FOCUS:
            errors.append(f"Invalid quality_focus: {answers.quality_focus}")

        # Naming consistency
        if answers.naming_consistency not in self.VALID_NAMING:
            errors.append(f"Invalid naming_consistency: {answers.naming_consistency}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[],
            metadata={"contract_type": "BrownfieldAnswers"}
        )
```

### Usage Example

```python
# From TASK-001 Q&A session
from qa_session import TemplateCreateQASession

qa = TemplateCreateQASession()
answers: BrownfieldAnswers = qa.run()

# Validate
validator = BrownfieldAnswersValidator()
result = validator.validate(answers)

if not result.is_valid:
    print(f"Validation failed: {result.errors}")
    return

# Pass to TASK-002
from ai_analyzer import AICodebaseAnalyzer

analyzer = AICodebaseAnalyzer(qa_context=answers)
analysis: CodebaseAnalysis = analyzer.analyze(answers.codebase_path)
```

---

## GreenfieldAnswers

**Source**: TASK-001B (Interactive Q&A Session for /template-init)
**Used By**: TASK-001B → TASK-011
**Schema Version**: 1.0.0

### Structure

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class GreenfieldAnswers:
    """Answers from /template-init Q&A session (greenfield)"""

    schema_version: str = "1.0.0"

    # Section 1: Template Identity
    template_name: str
    template_purpose: str  # "quick_start" | "team_standards" | "prototype" | "production"

    # Section 2: Technology Stack
    primary_language: str  # "csharp" | "typescript" | "python" | "java" | etc.
    framework: str  # Language-specific (e.g., "maui", "react-nextjs", "fastapi")
    framework_version: str  # "latest" | "lts" | specific version

    # Section 3: Architecture
    architecture_pattern: str  # "mvvm" | "clean" | "hexagonal" | "layered" | etc.
    domain_modeling: str  # "rich" | "anemic" | "functional" | "data-centric"

    # Section 4: Project Structure
    layer_organization: str  # "single" | "by-layer" | "by-feature" | "hybrid"
    standard_folders: List[str]  # ["src", "tests", "docs", "scripts", etc.]

    # Section 5: Testing
    unit_testing_framework: str  # "auto" | specific framework name
    testing_scope: List[str]  # ["unit", "integration", "e2e", "performance", etc.]
    test_pattern: str  # "aaa" | "bdd" | "none"

    # Section 6: Error Handling
    error_handling: str  # "result" | "exceptions" | "codes" | "mixed" | "minimal"
    validation_approach: str  # "fluent" | "annotations" | "manual" | "minimal"

    # Section 7: Dependency Management
    dependency_injection: str  # "builtin" | "third-party" | "manual" | "none"
    configuration_approach: str  # "json" | "env" | "both" | "service" | "minimal"

    # Section 8: UI/Navigation (optional, if UI framework)
    ui_architecture: Optional[str] = None  # "mvvm" | "mvc" | "component" | "codebehind"
    navigation_pattern: Optional[str] = None  # "recommended" | "custom" | "minimal"

    # Section 9: Additional Patterns (optional)
    data_access: Optional[str] = None  # "repository" | "direct" | "cqrs" | "eventsourcing"
    api_pattern: Optional[str] = None  # "rest" | "repr" | "minimal" | "graphql" | "grpc"
    state_management: Optional[str] = None  # "recommended" | "minimal" | specific library

    # Section 10: Documentation Input (Priority 1 - added 2025-11-02)
    documentation_paths: Optional[List[Path]] = None  # File paths to documentation
    documentation_text: Optional[str] = None  # Pasted documentation text
    documentation_urls: Optional[List[str]] = None  # URLs to documentation
    documentation_usage: Optional[str] = None  # "strict" | "guidance" | "naming" | "reasoning"
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | str | Yes | Data contract version |
| `template_name` | str | Yes | Template identifier |
| `template_purpose` | str | Yes | Template purpose |
| `primary_language` | str | Yes | Programming language |
| `framework` | str | Yes | Framework/platform |
| `framework_version` | str | Yes | Framework version strategy |
| `architecture_pattern` | str | Yes | Architecture pattern |
| `domain_modeling` | str | Yes | Domain modeling approach |
| `layer_organization` | str | Yes | Project structure organization |
| `standard_folders` | List[str] | Yes | Standard folders to include |
| `unit_testing_framework` | str | Yes | Testing framework choice |
| `testing_scope` | List[str] | Yes | Types of tests |
| `test_pattern` | str | Yes | Test writing pattern |
| `error_handling` | str | Yes | Error handling strategy |
| `validation_approach` | str | Yes | Input validation approach |
| `dependency_injection` | str | Yes | DI approach |
| `configuration_approach` | str | Yes | Configuration approach |
| `ui_architecture` | Optional[str] | No | UI architecture (if UI framework) |
| `navigation_pattern` | Optional[str] | No | Navigation approach (if UI) |
| `data_access` | Optional[str] | No | Data access pattern (if applicable) |
| `api_pattern` | Optional[str] | No | API pattern (if backend) |
| `state_management` | Optional[str] | No | State management (if UI) |
| `documentation_paths` | Optional[List[Path]] | No | File paths to documentation (ADRs, standards, etc.) |
| `documentation_text` | Optional[str] | No | Documentation pasted as text |
| `documentation_urls` | Optional[List[str]] | No | URLs to documentation resources |
| `documentation_usage` | Optional[str] | No | How to use documentation: "strict", "guidance", "naming", "reasoning" |

### Example JSON

```json
{
  "schema_version": "1.0.0",
  "template_name": "mycompany-maui-mvvm",
  "template_purpose": "production",
  "primary_language": "csharp",
  "framework": "maui",
  "framework_version": "latest",
  "architecture_pattern": "mvvm",
  "domain_modeling": "functional",
  "layer_organization": "by-layer",
  "standard_folders": ["src", "tests", "docs"],
  "unit_testing_framework": "auto",
  "testing_scope": ["unit", "integration"],
  "test_pattern": "aaa",
  "error_handling": "result",
  "validation_approach": "fluent",
  "dependency_injection": "builtin",
  "configuration_approach": "both",
  "ui_architecture": "mvvm",
  "navigation_pattern": "recommended",
  "data_access": "repository",
  "api_pattern": null,
  "state_management": "recommended",
  "documentation_paths": ["/docs/company-standards/mobile-dev-guide.md"],
  "documentation_text": null,
  "documentation_urls": ["https://company.com/architecture/maui-guidelines"],
  "documentation_usage": "guidance"
}
```

### Validation Rules

```python
class GreenfieldAnswersValidator(Validator):
    """Validate GreenfieldAnswers"""

    VALID_PURPOSES = ["quick_start", "team_standards", "prototype", "production"]
    VALID_LANGUAGES = ["csharp", "typescript", "python", "java", "swift", "go", "rust", "other"]
    VALID_ARCHITECTURES = ["mvvm", "clean", "hexagonal", "layered", "vertical-slice", "simple", "other"]
    # ... other enum lists

    def validate(self, answers: GreenfieldAnswers) -> ValidationResult:
        errors = []

        # Required fields
        if not answers.template_name:
            errors.append("template_name is required")

        if answers.template_purpose not in self.VALID_PURPOSES:
            errors.append(f"Invalid template_purpose: {answers.template_purpose}")

        if answers.primary_language not in self.VALID_LANGUAGES:
            errors.append(f"Invalid primary_language: {answers.primary_language}")

        # Conditional validation
        if answers.framework in ["maui", "blazor", "wpf", "react-nextjs", "angular", "vue"]:
            if not answers.ui_architecture:
                errors.append("ui_architecture is required for UI frameworks")

        if answers.framework in ["aspnet-core", "nestjs", "express", "fastapi", "django"]:
            if not answers.api_pattern:
                errors.append("api_pattern is required for backend frameworks")

        # Logical consistency
        if "tests" in answers.standard_folders and not answers.testing_scope:
            errors.append("testing_scope required when tests folder included")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[],
            metadata={"contract_type": "GreenfieldAnswers"}
        )
```

### Usage Example

```python
# From TASK-001B Q&A session
from qa_session import TemplateInitQASession

qa = TemplateInitQASession()
answers: GreenfieldAnswers = qa.run()

# Validate
validator = GreenfieldAnswersValidator()
result = validator.validate(answers)

if not result.is_valid:
    print(f"Validation failed: {result.errors}")
    return

# Pass to TASK-011 orchestrator
from template_init.command import TemplateInitCommand

command = TemplateInitCommand()
result = command.execute_with_answers(answers)
```

---

## Shared Q&A Infrastructure

Both `BrownfieldAnswers` and `GreenfieldAnswers` are created using shared Q&A infrastructure.

### BaseQASession (Abstract)

```python
from abc import ABC, abstractmethod

class BaseQASession(ABC):
    """Template Method pattern for Q&A sessions"""

    def run(self) -> QuestionAnswers:
        """Orchestrate shared + specific questions"""

        print("\n" + "="*60)
        print(f"  {self.session_title()}")
        print("="*60 + "\n")

        # Shared questions (common to both)
        shared_answers = self.run_shared_questions()

        # Specific questions (brownfield vs greenfield)
        specific_answers = self.run_specific_questions()

        # Combine
        all_answers = self.combine_answers(shared_answers, specific_answers)

        # Show summary
        self._show_summary(all_answers)

        # Confirm
        if not self._confirm_answers():
            return None

        return all_answers

    @abstractmethod
    def session_title(self) -> str:
        """Return session title"""
        pass

    @abstractmethod
    def run_specific_questions(self) -> dict:
        """Subclass implements specific questions"""
        pass

    def run_shared_questions(self) -> dict:
        """Questions common to both brownfield and greenfield"""
        return {
            "template_name": SharedQuestions.ask_template_name(),
            "template_description": SharedQuestions.ask_description(),
            # ... shared questions
        }

    @abstractmethod
    def combine_answers(self, shared: dict, specific: dict) -> QuestionAnswers:
        """Combine shared + specific into contract"""
        pass
```

### SharedQuestions (Utility)

```python
class SharedQuestions:
    """Reusable questions for both Q&A sessions"""

    @staticmethod
    def ask_template_name(default: str = "") -> str:
        return inquirer.text(
            message="Template name",
            default=default or "my-template"
        )

    @staticmethod
    def ask_description() -> str:
        return inquirer.text(
            message="Template description (optional)",
            default=""
        )

    # ... other shared questions
```

---

## Conversion Between Contracts

Greenfield answers need to be converted to `CodebaseAnalysis` format for generator compatibility:

```python
class GreenfieldAnalysisAdapter:
    """Convert GreenfieldAnswers to CodebaseAnalysis"""

    def adapt(self, answers: GreenfieldAnswers) -> CodebaseAnalysis:
        """Infer CodebaseAnalysis from greenfield Q&A"""

        return CodebaseAnalysis(
            schema_version="1.0.0",
            template_name=answers.template_name,
            language=answers.primary_language,
            frameworks=[answers.framework],
            architecture_pattern=answers.architecture_pattern,

            # Infer layers from organization choice
            layers=self._infer_layers(answers),

            # Infer naming conventions from language/framework
            naming_conventions=self._infer_naming(answers),

            # No actual patterns (greenfield), use defaults
            good_patterns=[],
            anti_patterns=[],

            # No example files (greenfield)
            example_files=[],

            # Infer agent needs from answers
            suggested_agents=self._infer_agent_needs(answers),

            # Metadata
            project_root=None,  # Greenfield, no existing code
            analyzed_at=datetime.now(),
            confidence_score=1.0,  # User-provided, high confidence
            source="greenfield"  # Mark as inferred
        )
```

---

## Testing

### BrownfieldAnswers Tests

```python
def test_brownfield_answers_creation():
    """Test BrownfieldAnswers creation"""
    answers = BrownfieldAnswers(
        purpose="new_projects",
        codebase_path=Path("/test/project"),
        template_name="test-template",
        scope=["structure", "patterns"],
        quality_focus="good",
        naming_consistency="high",
        exclusions=["node_modules"]
    )
    assert answers.schema_version == "1.0.0"
    assert answers.purpose == "new_projects"

def test_brownfield_answers_validation():
    """Test validation"""
    validator = BrownfieldAnswersValidator()

    # Valid
    valid = create_valid_brownfield_answers()
    result = validator.validate(valid)
    assert result.is_valid

    # Invalid (missing path)
    invalid = BrownfieldAnswers(
        purpose="new_projects",
        codebase_path=Path("/nonexistent"),
        template_name="test",
        scope=["structure"],
        quality_focus="good",
        naming_consistency="high"
    )
    result = validator.validate(invalid)
    assert not result.is_valid
    assert "does not exist" in result.errors[0]
```

### GreenfieldAnswers Tests

```python
def test_greenfield_answers_creation():
    """Test GreenfieldAnswers creation"""
    answers = GreenfieldAnswers(
        template_name="test-template",
        template_purpose="production",
        primary_language="csharp",
        framework="maui",
        framework_version="latest",
        architecture_pattern="mvvm",
        domain_modeling="functional",
        layer_organization="by-layer",
        standard_folders=["src", "tests"],
        unit_testing_framework="auto",
        testing_scope=["unit"],
        test_pattern="aaa",
        error_handling="result",
        validation_approach="fluent",
        dependency_injection="builtin",
        configuration_approach="both"
    )
    assert answers.schema_version == "1.0.0"
    assert answers.framework == "maui"

def test_greenfield_answers_conditional_validation():
    """Test conditional validation for UI frameworks"""
    validator = GreenfieldAnswersValidator()

    # UI framework without ui_architecture (should fail)
    answers = create_greenfield_answers(
        framework="maui",
        ui_architecture=None  # Missing
    )
    result = validator.validate(answers)
    assert not result.is_valid
    assert "ui_architecture is required" in result.errors[0]
```

---

**Created**: 2025-11-01
**Status**: ✅ COMPLETE
**Next**: [analysis-contracts.md](analysis-contracts.md)
