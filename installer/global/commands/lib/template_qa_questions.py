"""
Template Q&A Questions Definitions.

Defines all questions for the interactive Q&A session in /template-create.
Uses Python stdlib only (no external dependencies).

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Question:
    """Represents a single question in the Q&A session."""

    id: str
    section: str
    text: str
    type: str  # 'choice', 'multi_choice', 'text', 'confirm'
    choices: Optional[List[tuple]] = None  # List of (display, value) tuples
    default: Optional[Any] = None
    help_text: Optional[str] = None
    validation: Optional[str] = None
    depends_on: Optional[Dict[str, Any]] = None  # Conditional question logic


# Section 1: Template Identity
SECTION1_QUESTIONS = [
    Question(
        id="template_name",
        section="Template Identity",
        text="What should this template be called?",
        type="text",
        default="my-template",
        help_text="Example: dotnet-maui-mvvm-template",
        validation="non_empty"
    ),
    Question(
        id="template_purpose",
        section="Template Identity",
        text="What is the primary purpose of this template?",
        type="choice",
        choices=[
            ("Start new projects quickly", "quick_start"),
            ("Enforce team standards", "team_standards"),
            ("Prototype/experiment", "prototype"),
            ("Production-ready scaffold", "production"),
        ],
        default="quick_start"
    ),
]

# Section 2: Technology Stack
SECTION2_QUESTIONS = [
    Question(
        id="primary_language",
        section="Technology Stack",
        text="Primary programming language:",
        type="choice",
        choices=[
            ("C# / .NET", "csharp"),
            ("TypeScript / JavaScript", "typescript"),
            ("Python", "python"),
            ("Java / Kotlin", "java"),
            ("Swift", "swift"),
            ("Go", "go"),
            ("Rust", "rust"),
            ("Other (specify)", "other"),
        ],
        default="csharp"
    ),
    Question(
        id="framework_version",
        section="Technology Stack",
        text="Framework version:",
        type="choice",
        choices=[
            ("Latest stable [RECOMMENDED]", "latest"),
            ("Specific version", "specific"),
            ("LTS (long-term support)", "lts"),
        ],
        default="latest"
    ),
]

# Framework questions (context-dependent)
FRAMEWORK_QUESTIONS_DOTNET = [
    (".NET MAUI (mobile/desktop)", "maui"),
    ("ASP.NET Core (web API)", "aspnet-core"),
    ("Blazor (web UI)", "blazor"),
    ("WPF (desktop)", "wpf"),
    ("Console application", "console"),
]

FRAMEWORK_QUESTIONS_TYPESCRIPT = [
    ("React (with Next.js)", "react-nextjs"),
    ("React (with Vite)", "react-vite"),
    ("Angular", "angular"),
    ("Vue.js", "vue"),
    ("NestJS (backend)", "nestjs"),
    ("Express (backend)", "express"),
]

FRAMEWORK_QUESTIONS_PYTHON = [
    ("FastAPI (web API)", "fastapi"),
    ("Django (full-stack)", "django"),
    ("Flask (web API)", "flask"),
    ("Data science (Jupyter/pandas)", "data-science"),
    ("CLI application", "cli"),
]

# Section 3: Architecture Pattern
SECTION3_QUESTIONS = [
    Question(
        id="architecture_pattern",
        section="Architecture Pattern",
        text="Architecture pattern:",
        type="choice",
        choices=[
            ("MVVM (Model-View-ViewModel)", "mvvm"),
            ("Clean Architecture (Entities/Use Cases/Interfaces)", "clean"),
            ("Hexagonal/Ports & Adapters", "hexagonal"),
            ("Layered (Presentation/Business/Data)", "layered"),
            ("Vertical Slice Architecture", "vertical-slice"),
            ("Simple/Minimal (no formal pattern)", "simple"),
            ("Other (specify)", "other"),
        ],
        default="mvvm"
    ),
    Question(
        id="domain_modeling",
        section="Architecture Pattern",
        text="How should domain logic be organized?",
        type="choice",
        choices=[
            ("Rich domain models (entities with behavior)", "rich"),
            ("Anemic models + service layer", "anemic"),
            ("Functional domain operations (verb-based)", "functional"),
            ("Data-centric (minimal domain layer)", "data-centric"),
        ],
        default="rich"
    ),
]

# Section 4: Project Structure
SECTION4_QUESTIONS = [
    Question(
        id="layer_organization",
        section="Project Structure",
        text="Project structure preference:",
        type="choice",
        choices=[
            ("Single project (simple)", "single"),
            ("Multiple projects by layer (Domain, Application, Infrastructure)", "by-layer"),
            ("Multiple projects by feature (vertical slices)", "by-feature"),
            ("Hybrid (layers + features)", "hybrid"),
        ],
        default="single"
    ),
    Question(
        id="standard_folders",
        section="Project Structure",
        text="Include standard folders? (comma-separated numbers)",
        type="multi_choice",
        choices=[
            ("src/ (source code)", "src", True),
            ("tests/ (test code)", "tests", True),
            ("docs/ (documentation)", "docs", False),
            ("scripts/ (build/deploy scripts)", "scripts", False),
            (".github/ (GitHub workflows)", "github", False),
            ("docker/ (container configs)", "docker", False),
        ],
    ),
]

# Section 5: Testing Strategy
SECTION5_QUESTIONS = [
    Question(
        id="unit_testing_framework",
        section="Testing Strategy",
        text="Unit testing framework:",
        type="choice",
        choices=[
            ("Auto-select best for language [RECOMMENDED]", "auto"),
            ("Specify framework", "specify"),
        ],
        default="auto"
    ),
    Question(
        id="testing_scope",
        section="Testing Strategy",
        text="Which types of tests should be included? (comma-separated numbers)",
        type="multi_choice",
        choices=[
            ("Unit tests (logic, pure functions)", "unit", True),
            ("Integration tests (dependencies, database)", "integration", True),
            ("End-to-end tests (full user flows)", "e2e", False),
            ("Performance tests", "performance", False),
            ("Security tests", "security", False),
        ],
    ),
    Question(
        id="test_pattern",
        section="Testing Strategy",
        text="Test pattern preference:",
        type="choice",
        choices=[
            ("Arrange-Act-Assert (AAA)", "aaa"),
            ("Given-When-Then (BDD style)", "bdd"),
            ("No preference", "none"),
        ],
        default="aaa"
    ),
]

# Section 6: Error Handling
SECTION6_QUESTIONS = [
    Question(
        id="error_handling",
        section="Error Handling",
        text="Error handling strategy:",
        type="choice",
        choices=[
            ("Result/Either type (ErrorOr<T>, Result<T, E>)", "result"),
            ("Exceptions (try-catch)", "exceptions"),
            ("Error codes/status objects", "codes"),
            ("Mixed approach", "mixed"),
            ("Minimal (language defaults)", "minimal"),
        ],
        default="result"
    ),
    Question(
        id="validation_approach",
        section="Error Handling",
        text="Input validation strategy:",
        type="choice",
        choices=[
            ("FluentValidation (or equivalent)", "fluent"),
            ("Data annotations/attributes", "annotations"),
            ("Manual validation in code", "manual"),
            ("Minimal validation", "minimal"),
        ],
        default="fluent"
    ),
]

# Section 7: Dependency Management
SECTION7_QUESTIONS = [
    Question(
        id="dependency_injection",
        section="Dependency Management",
        text="Dependency injection approach:",
        type="choice",
        choices=[
            ("Built-in DI container [RECOMMENDED]", "builtin"),
            ("Third-party DI (Autofac, Ninject, etc.)", "third-party"),
            ("Manual DI (constructor injection, no container)", "manual"),
            ("Not needed", "none"),
        ],
        default="builtin"
    ),
    Question(
        id="configuration_approach",
        section="Dependency Management",
        text="Configuration approach:",
        type="choice",
        choices=[
            ("JSON files (appsettings.json, etc.)", "json"),
            ("Environment variables", "env"),
            ("Both (JSON + env vars)", "both"),
            ("Configuration service/library", "service"),
            ("Minimal (hardcoded defaults)", "minimal"),
        ],
        default="both"
    ),
]

# Section 8: UI/Navigation (conditional)
SECTION8_QUESTIONS = [
    Question(
        id="ui_architecture",
        section="UI/Navigation",
        text="UI architecture pattern:",
        type="choice",
        choices=[
            ("MVVM (ViewModel binding)", "mvvm"),
            ("MVC (Model-View-Controller)", "mvc"),
            ("Component-based (React, Vue)", "component"),
            ("Simple code-behind", "codebehind"),
        ],
        default="mvvm",
        depends_on={"framework": ["maui", "blazor", "wpf", "react-nextjs", "react-vite", "angular", "vue"]}
    ),
    Question(
        id="navigation_pattern",
        section="UI/Navigation",
        text="Navigation approach:",
        type="choice",
        choices=[
            ("Framework-recommended [RECOMMENDED]", "recommended"),
            ("Custom navigation", "custom"),
            ("Minimal (single page)", "minimal"),
        ],
        default="recommended",
        depends_on={"framework": ["maui", "blazor", "wpf", "react-nextjs", "react-vite", "angular", "vue"]}
    ),
]

# Section 9: Additional Patterns
SECTION9_QUESTIONS = [
    Question(
        id="needs_data_access",
        section="Additional Patterns",
        text="Does this template need data access?",
        type="confirm",
        default=True
    ),
    Question(
        id="data_access",
        section="Additional Patterns",
        text="Data access pattern (if applicable):",
        type="choice",
        choices=[
            ("Repository pattern", "repository"),
            ("Direct database access (EF Core, etc.)", "direct"),
            ("CQRS (separate read/write)", "cqrs"),
            ("Event sourcing", "eventsourcing"),
            ("Not applicable (no database)", "none"),
        ],
        default="repository",
        depends_on={"needs_data_access": True}
    ),
    Question(
        id="api_pattern",
        section="Additional Patterns",
        text="API pattern preference:",
        type="choice",
        choices=[
            ("REST (resource-based endpoints)", "rest"),
            ("REPR (Request-Endpoint-Response)", "repr"),
            ("Minimal APIs (lightweight)", "minimal"),
            ("GraphQL", "graphql"),
            ("gRPC", "grpc"),
            ("Not applicable", "none"),
        ],
        default="rest",
        depends_on={"framework": ["aspnet-core", "nestjs", "express", "fastapi", "django", "flask"]}
    ),
    Question(
        id="state_management",
        section="Additional Patterns",
        text="State management approach:",
        type="choice",
        choices=[
            ("Framework-recommended [RECOMMENDED]", "recommended"),
            ("Minimal (local state only)", "minimal"),
            ("Specify library", "specify"),
        ],
        default="recommended",
        depends_on={"framework": ["maui", "blazor", "react-nextjs", "react-vite", "angular", "vue"]}
    ),
]

# Section 10: Documentation Input
SECTION10_QUESTIONS = [
    Question(
        id="has_documentation",
        section="Documentation Input",
        text="Do you have documentation to guide template creation?",
        type="confirm",
        default=False,
        help_text="Examples: ADRs, coding standards, API specs, design docs, team guidelines"
    ),
    Question(
        id="documentation_input_method",
        section="Documentation Input",
        text="How would you like to provide documentation?",
        type="choice",
        choices=[
            ("Provide file paths", "paths"),
            ("Paste text directly", "text"),
            ("Provide URLs", "urls"),
            ("None", "none"),
        ],
        default="none",
        depends_on={"has_documentation": True}
    ),
    Question(
        id="documentation_usage",
        section="Documentation Input",
        text="How should we use this documentation?",
        type="choice",
        choices=[
            ("Follow patterns/standards strictly", "strict"),
            ("Use as general guidance", "guidance"),
            ("Extract naming conventions only", "naming"),
            ("Understand architecture reasoning", "reasoning"),
        ],
        default="guidance",
        depends_on={"has_documentation": True}
    ),
]


# All question sections
ALL_SECTIONS = [
    SECTION1_QUESTIONS,
    SECTION2_QUESTIONS,
    SECTION3_QUESTIONS,
    SECTION4_QUESTIONS,
    SECTION5_QUESTIONS,
    SECTION6_QUESTIONS,
    SECTION7_QUESTIONS,
    SECTION8_QUESTIONS,
    SECTION9_QUESTIONS,
    SECTION10_QUESTIONS,
]


def get_framework_choices(language: str) -> List[tuple]:
    """
    Get framework choices based on selected language.

    Args:
        language: Selected programming language

    Returns:
        List of (display, value) tuples for framework selection
    """
    if language == "csharp":
        return FRAMEWORK_QUESTIONS_DOTNET
    elif language == "typescript":
        return FRAMEWORK_QUESTIONS_TYPESCRIPT
    elif language == "python":
        return FRAMEWORK_QUESTIONS_PYTHON
    else:
        return [("Other (specify)", "other")]


def should_ask_question(question: Question, answers: Dict[str, Any]) -> bool:
    """
    Determine if a question should be asked based on previous answers.

    Args:
        question: Question to evaluate
        answers: Dictionary of previous answers

    Returns:
        True if question should be asked, False otherwise
    """
    if question.depends_on is None:
        return True

    for key, expected_values in question.depends_on.items():
        actual_value = answers.get(key)

        # Handle boolean dependencies
        if isinstance(expected_values, bool):
            if actual_value != expected_values:
                return False
        # Handle list dependencies
        elif isinstance(expected_values, list):
            if actual_value not in expected_values:
                return False

    return True


# Module exports
__all__ = [
    "Question",
    "ALL_SECTIONS",
    "get_framework_choices",
    "should_ask_question",
    "SECTION1_QUESTIONS",
    "SECTION2_QUESTIONS",
    "SECTION3_QUESTIONS",
    "SECTION4_QUESTIONS",
    "SECTION5_QUESTIONS",
    "SECTION6_QUESTIONS",
    "SECTION7_QUESTIONS",
    "SECTION8_QUESTIONS",
    "SECTION9_QUESTIONS",
    "SECTION10_QUESTIONS",
]
