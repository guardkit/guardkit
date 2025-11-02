---
id: TASK-001B
title: Interactive Q&A Session for /template-init (Greenfield)
status: backlog
created: 2025-11-01T23:45:00Z
priority: high
complexity: 5
estimated_hours: 8
tags: [qa-session, interactive, greenfield, user-experience]
epic: EPIC-001
feature: ai-analysis
dependencies: []
blocks: [TASK-011]
---

# TASK-001B: Interactive Q&A Session for /template-init (Greenfield)

## Objective

Create an interactive Q&A session for `/template-init` that guides users through greenfield template creation from scratch (no existing codebase).

**Purpose**: Gather technology stack and architecture decisions before AI generates intelligent defaults.

**Key Difference from TASK-001**:
- Brownfield (TASK-001): Analyzes existing codebase
- Greenfield (TASK-001B): Guides technology selection and architecture decisions

## Context

From **AGENT-STRATEGY-high-level-design.md** (Flow 3: Greenfield Template Creation):

```bash
$ /template-init

[Q&A Session - 10 sections, ~42 questions...]

Technology Stack: .NET MAUI
Architecture: MVVM
Navigation: AppShell
Error Handling: ErrorOr<T>
Testing: xUnit

🤖 Generating agents for this configuration...
```

**User Need**: Create a template when no codebase exists, by selecting technologies and patterns.

## Acceptance Criteria

- [ ] Interactive Q&A flow with 10 sections (~42 questions total, including documentation input)
- [ ] Technology stack selection (language, framework, version)
- [ ] Architecture pattern selection (MVVM, Clean, Hexagonal, etc.)
- [ ] Project structure preferences (layers, folders)
- [ ] Testing strategy selection (unit, integration, e2e tools)
- [ ] Error handling approach selection
- [ ] Session persistence (save/resume capability)
- [ ] Input validation and helpful prompts
- [ ] Summary of answers before proceeding to AI generation
- [ ] Option to skip Q&A and use defaults
- [ ] Clear, user-friendly CLI interface with guidance
- [ ] Unit tests for Q&A flow

## Questions to Ask

### Section 1: Template Identity

#### 1.1 Template Name
```
What should this template be called?

[Default: {language}-{framework}-template]
Example: dotnet-maui-mvvm-template

Purpose: Generates template identifier
```

#### 1.2 Template Purpose
```
What is the primary purpose of this template?

[a] Start new projects quickly
[b] Enforce team standards
[c] Prototype/experiment
[d] Production-ready scaffold

Purpose: Guides AI's choices for completeness vs flexibility
```

### Section 2: Technology Stack

#### 2.1 Primary Language
```
Primary programming language:

[a] C# / .NET
[b] TypeScript / JavaScript
[c] Python
[d] Java / Kotlin
[e] Swift
[f] Go
[g] Rust
[h] Other (specify)

Purpose: Determines base template structure
```

#### 2.2 Framework (context-dependent)

**If .NET selected**:
```
.NET framework/platform:

[a] .NET MAUI (mobile/desktop)
[b] ASP.NET Core (web API)
[c] Blazor (web UI)
[d] WPF (desktop)
[e] Console application

Purpose: Determines project type and structure
```

**If TypeScript selected**:
```
TypeScript framework:

[a] React (with Next.js)
[b] React (with Vite)
[c] Angular
[d] Vue.js
[e] NestJS (backend)
[f] Express (backend)

Purpose: Determines project type and tooling
```

**If Python selected**:
```
Python framework:

[a] FastAPI (web API)
[b] Django (full-stack)
[c] Flask (web API)
[d] Data science (Jupyter/pandas)
[e] CLI application

Purpose: Determines project type and dependencies
```

#### 2.3 Framework Version
```
Framework version:

[a] Latest stable [RECOMMENDED]
[b] Specific version: __________
[c] LTS (long-term support)

Purpose: Ensures compatibility
```

### Section 3: Architecture Pattern

#### 3.1 Primary Architecture
```
Architecture pattern:

[a] MVVM (Model-View-ViewModel)
[b] Clean Architecture (Entities/Use Cases/Interfaces)
[c] Hexagonal/Ports & Adapters
[d] Layered (Presentation/Business/Data)
[e] Vertical Slice Architecture
[f] Simple/Minimal (no formal pattern)
[g] Other (specify)

Purpose: Determines project structure and agent needs
```

#### 3.2 Domain Modeling Approach
```
How should domain logic be organized?

[a] Rich domain models (entities with behavior)
[b] Anemic models + service layer
[c] Functional domain operations (verb-based)
[d] Data-centric (minimal domain layer)

Purpose: Guides code generation patterns
```

### Section 4: Project Structure

#### 4.1 Layer Organization
```
Project structure preference:

[a] Single project (simple)
[b] Multiple projects by layer (Domain, Application, Infrastructure)
[c] Multiple projects by feature (vertical slices)
[d] Hybrid (layers + features)

Purpose: Determines folder/project structure
```

#### 4.2 Standard Folders
```
Include standard folders? (select all that apply)

[✓] src/ (source code)
[✓] tests/ (test code)
[ ] docs/ (documentation)
[ ] scripts/ (build/deploy scripts)
[ ] .github/ (GitHub workflows)
[ ] docker/ (container configs)

Purpose: Defines template structure
```

### Section 5: Testing Strategy

#### 5.1 Unit Testing Framework
```
Unit testing framework:

[a] Auto-select best for language [RECOMMENDED]
[b] Specify: __________

Examples:
- .NET: xUnit, NUnit, MSTest
- TypeScript: Vitest, Jest
- Python: pytest, unittest

Purpose: Determines test project setup
```

#### 5.2 Testing Scope
```
Which types of tests should be included?

[✓] Unit tests (logic, pure functions)
[✓] Integration tests (dependencies, database)
[ ] End-to-end tests (full user flows)
[ ] Performance tests
[ ] Security tests

Purpose: Determines test structure and tools
```

#### 5.3 Test Patterns
```
Test pattern preference:

[a] Arrange-Act-Assert (AAA)
[b] Given-When-Then (BDD style)
[c] No preference

Purpose: Guides test generation style
```

### Section 6: Error Handling

#### 6.1 Error Handling Approach
```
Error handling strategy:

[a] Result/Either type (ErrorOr<T>, Result<T, E>)
[b] Exceptions (try-catch)
[c] Error codes/status objects
[d] Mixed approach
[e] Minimal (language defaults)

Purpose: Determines error handling patterns
```

#### 6.2 Validation Approach
```
Input validation strategy:

[a] FluentValidation (or equivalent)
[b] Data annotations/attributes
[c] Manual validation in code
[d] Minimal validation

Purpose: Determines validation infrastructure
```

### Section 7: Dependency Management

#### 7.1 Dependency Injection
```
Dependency injection approach:

[a] Built-in DI container (Microsoft.Extensions.DependencyInjection, etc.)
[b] Third-party DI (Autofac, Ninject, etc.)
[c] Manual DI (constructor injection, no container)
[d] Not needed

Purpose: Determines DI setup
```

#### 7.2 Configuration Management
```
Configuration approach:

[a] JSON files (appsettings.json, etc.)
[b] Environment variables
[c] Both (JSON + env vars)
[d] Configuration service/library
[e] Minimal (hardcoded defaults)

Purpose: Determines configuration infrastructure
```

### Section 8: UI/Navigation (if applicable)

**Only asked if UI framework selected**

#### 8.1 UI Architecture
```
UI architecture pattern:

[a] MVVM (ViewModel binding)
[b] MVC (Model-View-Controller)
[c] Component-based (React, Vue)
[d] Simple code-behind

Purpose: Determines UI structure
```

#### 8.2 Navigation Pattern
```
Navigation approach:

[MAUI] Shell (AppShell) or NavigationPage
[React] React Router
[Angular] Angular Router
[Blazor] Blazor Router

[a] Framework-recommended [RECOMMENDED]
[b] Custom navigation
[c] Minimal (single page)

Purpose: Determines navigation setup
```

### Section 9: Additional Patterns

#### 9.1 Data Access
```
Data access pattern (if applicable):

[a] Repository pattern
[b] Direct database access (EF Core, etc.)
[c] CQRS (separate read/write)
[d] Event sourcing
[e] Not applicable (no database)

Purpose: Determines data layer structure
```

#### 9.2 API Pattern (if backend)
```
API pattern preference:

[a] REST (resource-based endpoints)
[b] REPR (Request-Endpoint-Response)
[c] Minimal APIs (lightweight)
[d] GraphQL
[e] gRPC
[f] Not applicable

Purpose: Determines API structure
```

#### 9.3 State Management (if UI)
```
State management approach:

[React] Redux, Zustand, Context
[Vue] Vuex, Pinia
[MAUI] MVVM binding, MAUI Community Toolkit
[Angular] NgRx, Services

[a] Framework-recommended [RECOMMENDED]
[b] Minimal (local state only)
[c] Specify: __________

Purpose: Determines state management infrastructure
```

### Section 10: Documentation Input

#### 10.1 Documentation Input
```
Do you have documentation to guide template creation?

Examples:
- Architecture Decision Records (ADRs)
- Coding standards documents
- API specifications
- Requirements documents
- Design documents
- Company/team engineering guidelines

Options:
[a] Provide file paths
[b] Paste text directly
[c] Provide URLs
[d] None

Purpose: Gives AI context about WHY patterns exist, not just WHAT patterns exist
         Especially valuable for greenfield to understand organizational standards
```

#### 10.2 Documentation Usage (if provided)
```
How should we use this documentation?

[a] Follow patterns/standards strictly
[b] Use as general guidance
[c] Extract naming conventions only
[d] Understand architecture reasoning

Purpose: Determines how documentation influences template generation
```

## Implementation

```python
# src/commands/template_init/qa_session.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import inquirer

@dataclass
class GreenfieldAnswers:
    """Answers from greenfield Q&A session"""

    # Section 1: Template Identity
    template_name: str
    template_purpose: str

    # Section 2: Technology Stack
    primary_language: str
    framework: str
    framework_version: str

    # Section 3: Architecture
    architecture_pattern: str
    domain_modeling: str

    # Section 4: Project Structure
    layer_organization: str
    standard_folders: List[str]

    # Section 5: Testing
    unit_testing_framework: str
    testing_scope: List[str]
    test_pattern: str

    # Section 6: Error Handling
    error_handling: str
    validation_approach: str

    # Section 7: Dependency Management
    dependency_injection: str
    configuration_approach: str

    # Section 8: UI/Navigation (optional)
    ui_architecture: Optional[str] = None
    navigation_pattern: Optional[str] = None

    # Section 9: Additional Patterns
    data_access: Optional[str] = None
    api_pattern: Optional[str] = None
    state_management: Optional[str] = None

    # Section 10: Documentation Input (Priority 1)
    documentation_paths: Optional[List[Path]] = None
    documentation_text: Optional[str] = None
    documentation_urls: Optional[List[str]] = None
    documentation_usage: Optional[str] = None

class TemplateInitQASession:
    """Interactive Q&A session for /template-init (greenfield)"""

    def __init__(self):
        self.answers: Optional[GreenfieldAnswers] = None

    def run(self) -> GreenfieldAnswers:
        """
        Run interactive Q&A session for greenfield template creation

        Returns:
            GreenfieldAnswers with user responses
        """
        print("\n" + "="*60)
        print("  /template-init - Greenfield Template Creation")
        print("="*60 + "\n")

        print("This Q&A will guide you through creating a new project template.")
        print("Press Ctrl+C at any time to save and exit.\n")

        # Section 1: Template Identity
        answers = self._section1_identity()

        # Section 2: Technology Stack
        self._section2_technology(answers)

        # Section 3: Architecture
        self._section3_architecture(answers)

        # Section 4: Project Structure
        self._section4_structure(answers)

        # Section 5: Testing
        self._section5_testing(answers)

        # Section 6: Error Handling
        self._section6_error_handling(answers)

        # Section 7: Dependency Management
        self._section7_dependencies(answers)

        # Section 8: UI/Navigation (conditional)
        if self._is_ui_framework(answers.framework):
            self._section8_ui_navigation(answers)

        # Section 9: Additional Patterns
        self._section9_additional_patterns(answers)

        # Build final answers
        self.answers = answers

        # Show summary
        self._show_summary()

        # Confirm
        proceed = inquirer.confirm(
            message="Proceed with template generation using these settings?",
            default=True
        )

        if not proceed:
            print("\nQ&A session cancelled. Run /template-init again to restart.\n")
            return None

        return self.answers

    def _section1_identity(self) -> dict:
        """Section 1: Template Identity"""
        print("\n" + "-"*60)
        print("  Section 1: Template Identity")
        print("-"*60 + "\n")

        template_name = inquirer.text(
            message="Template name",
            default="my-template"
        )

        template_purpose = inquirer.list_input(
            message="Template purpose",
            choices=[
                ("Start new projects quickly", "quick_start"),
                ("Enforce team standards", "team_standards"),
                ("Prototype/experiment", "prototype"),
                ("Production-ready scaffold", "production"),
            ]
        )

        return {
            "template_name": template_name,
            "template_purpose": template_purpose
        }

    def _section2_technology(self, answers: dict):
        """Section 2: Technology Stack"""
        print("\n" + "-"*60)
        print("  Section 2: Technology Stack")
        print("-"*60 + "\n")

        primary_language = inquirer.list_input(
            message="Primary programming language",
            choices=[
                ("C# / .NET", "csharp"),
                ("TypeScript / JavaScript", "typescript"),
                ("Python", "python"),
                ("Java / Kotlin", "java"),
                ("Swift", "swift"),
                ("Go", "go"),
                ("Rust", "rust"),
                ("Other", "other"),
            ]
        )
        answers["primary_language"] = primary_language

        # Framework (context-dependent)
        framework = self._ask_framework(primary_language)
        answers["framework"] = framework

        framework_version = inquirer.list_input(
            message="Framework version",
            choices=[
                ("Latest stable [RECOMMENDED]", "latest"),
                ("Specific version", "specific"),
                ("LTS (long-term support)", "lts"),
            ]
        )

        if framework_version == "specific":
            specific_version = inquirer.text(message="Specify version")
            answers["framework_version"] = specific_version
        else:
            answers["framework_version"] = framework_version

    def _ask_framework(self, language: str) -> str:
        """Ask framework based on language selection"""

        if language == "csharp":
            return inquirer.list_input(
                message=".NET framework/platform",
                choices=[
                    (".NET MAUI (mobile/desktop)", "maui"),
                    ("ASP.NET Core (web API)", "aspnet-core"),
                    ("Blazor (web UI)", "blazor"),
                    ("WPF (desktop)", "wpf"),
                    ("Console application", "console"),
                ]
            )

        elif language == "typescript":
            return inquirer.list_input(
                message="TypeScript framework",
                choices=[
                    ("React (with Next.js)", "react-nextjs"),
                    ("React (with Vite)", "react-vite"),
                    ("Angular", "angular"),
                    ("Vue.js", "vue"),
                    ("NestJS (backend)", "nestjs"),
                    ("Express (backend)", "express"),
                ]
            )

        elif language == "python":
            return inquirer.list_input(
                message="Python framework",
                choices=[
                    ("FastAPI (web API)", "fastapi"),
                    ("Django (full-stack)", "django"),
                    ("Flask (web API)", "flask"),
                    ("Data science (Jupyter/pandas)", "data-science"),
                    ("CLI application", "cli"),
                ]
            )

        else:
            return inquirer.text(message=f"Specify framework for {language}")

    def _section3_architecture(self, answers: dict):
        """Section 3: Architecture"""
        print("\n" + "-"*60)
        print("  Section 3: Architecture Pattern")
        print("-"*60 + "\n")

        architecture_pattern = inquirer.list_input(
            message="Architecture pattern",
            choices=[
                ("MVVM (Model-View-ViewModel)", "mvvm"),
                ("Clean Architecture", "clean"),
                ("Hexagonal/Ports & Adapters", "hexagonal"),
                ("Layered (Presentation/Business/Data)", "layered"),
                ("Vertical Slice Architecture", "vertical-slice"),
                ("Simple/Minimal (no formal pattern)", "simple"),
                ("Other", "other"),
            ]
        )
        answers["architecture_pattern"] = architecture_pattern

        domain_modeling = inquirer.list_input(
            message="Domain logic organization",
            choices=[
                ("Rich domain models (entities with behavior)", "rich"),
                ("Anemic models + service layer", "anemic"),
                ("Functional domain operations (verb-based)", "functional"),
                ("Data-centric (minimal domain layer)", "data-centric"),
            ]
        )
        answers["domain_modeling"] = domain_modeling

    def _section4_structure(self, answers: dict):
        """Section 4: Project Structure"""
        print("\n" + "-"*60)
        print("  Section 4: Project Structure")
        print("-"*60 + "\n")

        layer_organization = inquirer.list_input(
            message="Project structure preference",
            choices=[
                ("Single project (simple)", "single"),
                ("Multiple projects by layer", "by-layer"),
                ("Multiple projects by feature", "by-feature"),
                ("Hybrid (layers + features)", "hybrid"),
            ]
        )
        answers["layer_organization"] = layer_organization

        standard_folders = inquirer.checkbox(
            message="Include standard folders",
            choices=[
                ("src/ (source code)", "src", True),
                ("tests/ (test code)", "tests", True),
                ("docs/ (documentation)", "docs", False),
                ("scripts/ (build/deploy)", "scripts", False),
                (".github/ (GitHub workflows)", "github", False),
                ("docker/ (containers)", "docker", False),
            ]
        )
        answers["standard_folders"] = standard_folders

    def _section5_testing(self, answers: dict):
        """Section 5: Testing Strategy"""
        print("\n" + "-"*60)
        print("  Section 5: Testing Strategy")
        print("-"*60 + "\n")

        unit_testing_framework = inquirer.list_input(
            message="Unit testing framework",
            choices=[
                ("Auto-select best for language [RECOMMENDED]", "auto"),
                ("Specify framework", "specify"),
            ]
        )

        if unit_testing_framework == "specify":
            specific_framework = inquirer.text(message="Testing framework name")
            answers["unit_testing_framework"] = specific_framework
        else:
            answers["unit_testing_framework"] = "auto"

        testing_scope = inquirer.checkbox(
            message="Types of tests to include",
            choices=[
                ("Unit tests", "unit", True),
                ("Integration tests", "integration", True),
                ("End-to-end tests", "e2e", False),
                ("Performance tests", "performance", False),
                ("Security tests", "security", False),
            ]
        )
        answers["testing_scope"] = testing_scope

        test_pattern = inquirer.list_input(
            message="Test pattern preference",
            choices=[
                ("Arrange-Act-Assert (AAA)", "aaa"),
                ("Given-When-Then (BDD)", "bdd"),
                ("No preference", "none"),
            ]
        )
        answers["test_pattern"] = test_pattern

    def _section6_error_handling(self, answers: dict):
        """Section 6: Error Handling"""
        print("\n" + "-"*60)
        print("  Section 6: Error Handling")
        print("-"*60 + "\n")

        error_handling = inquirer.list_input(
            message="Error handling strategy",
            choices=[
                ("Result/Either type (ErrorOr<T>, Result<T, E>)", "result"),
                ("Exceptions (try-catch)", "exceptions"),
                ("Error codes/status objects", "codes"),
                ("Mixed approach", "mixed"),
                ("Minimal (language defaults)", "minimal"),
            ]
        )
        answers["error_handling"] = error_handling

        validation_approach = inquirer.list_input(
            message="Input validation strategy",
            choices=[
                ("FluentValidation (or equivalent)", "fluent"),
                ("Data annotations/attributes", "annotations"),
                ("Manual validation in code", "manual"),
                ("Minimal validation", "minimal"),
            ]
        )
        answers["validation_approach"] = validation_approach

    def _section7_dependencies(self, answers: dict):
        """Section 7: Dependency Management"""
        print("\n" + "-"*60)
        print("  Section 7: Dependency Management")
        print("-"*60 + "\n")

        dependency_injection = inquirer.list_input(
            message="Dependency injection approach",
            choices=[
                ("Built-in DI container [RECOMMENDED]", "builtin"),
                ("Third-party DI (Autofac, etc.)", "third-party"),
                ("Manual DI (constructor injection)", "manual"),
                ("Not needed", "none"),
            ]
        )
        answers["dependency_injection"] = dependency_injection

        configuration_approach = inquirer.list_input(
            message="Configuration approach",
            choices=[
                ("JSON files (appsettings.json)", "json"),
                ("Environment variables", "env"),
                ("Both (JSON + env vars)", "both"),
                ("Configuration service", "service"),
                ("Minimal (hardcoded)", "minimal"),
            ]
        )
        answers["configuration_approach"] = configuration_approach

    def _section8_ui_navigation(self, answers: dict):
        """Section 8: UI/Navigation (optional)"""
        print("\n" + "-"*60)
        print("  Section 8: UI/Navigation")
        print("-"*60 + "\n")

        ui_architecture = inquirer.list_input(
            message="UI architecture pattern",
            choices=[
                ("MVVM (ViewModel binding)", "mvvm"),
                ("MVC (Model-View-Controller)", "mvc"),
                ("Component-based (React, Vue)", "component"),
                ("Simple code-behind", "codebehind"),
            ]
        )
        answers["ui_architecture"] = ui_architecture

        navigation_pattern = inquirer.list_input(
            message="Navigation approach",
            choices=[
                ("Framework-recommended [RECOMMENDED]", "recommended"),
                ("Custom navigation", "custom"),
                ("Minimal (single page)", "minimal"),
            ]
        )
        answers["navigation_pattern"] = navigation_pattern

    def _section9_additional_patterns(self, answers: dict):
        """Section 9: Additional Patterns"""
        print("\n" + "-"*60)
        print("  Section 9: Additional Patterns")
        print("-"*60 + "\n")

        needs_data_access = inquirer.confirm(
            message="Does this template need data access?",
            default=True
        )

        if needs_data_access:
            data_access = inquirer.list_input(
                message="Data access pattern",
                choices=[
                    ("Repository pattern", "repository"),
                    ("Direct database access", "direct"),
                    ("CQRS (separate read/write)", "cqrs"),
                    ("Event sourcing", "eventsourcing"),
                ]
            )
            answers["data_access"] = data_access
        else:
            answers["data_access"] = None

        # API pattern (if backend)
        if self._is_backend_framework(answers.get("framework")):
            api_pattern = inquirer.list_input(
                message="API pattern preference",
                choices=[
                    ("REST (resource-based)", "rest"),
                    ("REPR (Request-Endpoint-Response)", "repr"),
                    ("Minimal APIs", "minimal"),
                    ("GraphQL", "graphql"),
                    ("gRPC", "grpc"),
                ]
            )
            answers["api_pattern"] = api_pattern
        else:
            answers["api_pattern"] = None

        # State management (if UI)
        if self._is_ui_framework(answers.get("framework")):
            state_management = inquirer.list_input(
                message="State management approach",
                choices=[
                    ("Framework-recommended [RECOMMENDED]", "recommended"),
                    ("Minimal (local state only)", "minimal"),
                    ("Specify library", "specify"),
                ]
            )

            if state_management == "specify":
                specific_state = inquirer.text(message="State management library")
                answers["state_management"] = specific_state
            else:
                answers["state_management"] = state_management
        else:
            answers["state_management"] = None

    def _is_ui_framework(self, framework: str) -> bool:
        """Check if framework is UI-focused"""
        ui_frameworks = [
            "maui", "blazor", "wpf",
            "react-nextjs", "react-vite", "angular", "vue"
        ]
        return framework in ui_frameworks

    def _is_backend_framework(self, framework: str) -> bool:
        """Check if framework is backend-focused"""
        backend_frameworks = [
            "aspnet-core", "nestjs", "express",
            "fastapi", "django", "flask"
        ]
        return framework in backend_frameworks

    def _show_summary(self):
        """Display summary of answers"""
        print("\n" + "="*60)
        print("  Q&A Summary")
        print("="*60 + "\n")

        print(f"Template Name: {self.answers.template_name}")
        print(f"Purpose: {self.answers.template_purpose}")
        print(f"\nTechnology Stack:")
        print(f"  Language: {self.answers.primary_language}")
        print(f"  Framework: {self.answers.framework}")
        print(f"  Version: {self.answers.framework_version}")
        print(f"\nArchitecture:")
        print(f"  Pattern: {self.answers.architecture_pattern}")
        print(f"  Domain: {self.answers.domain_modeling}")
        print(f"\nProject Structure:")
        print(f"  Organization: {self.answers.layer_organization}")
        print(f"  Folders: {', '.join(self.answers.standard_folders)}")
        print(f"\nTesting:")
        print(f"  Framework: {self.answers.unit_testing_framework}")
        print(f"  Scope: {', '.join(self.answers.testing_scope)}")
        print(f"  Pattern: {self.answers.test_pattern}")
        print(f"\nError Handling:")
        print(f"  Strategy: {self.answers.error_handling}")
        print(f"  Validation: {self.answers.validation_approach}")
        print(f"\nDependency Management:")
        print(f"  DI: {self.answers.dependency_injection}")
        print(f"  Config: {self.answers.configuration_approach}")

        if self.answers.ui_architecture:
            print(f"\nUI/Navigation:")
            print(f"  Architecture: {self.answers.ui_architecture}")
            print(f"  Navigation: {self.answers.navigation_pattern}")

        if self.answers.data_access or self.answers.api_pattern or self.answers.state_management:
            print(f"\nAdditional Patterns:")
            if self.answers.data_access:
                print(f"  Data Access: {self.answers.data_access}")
            if self.answers.api_pattern:
                print(f"  API: {self.answers.api_pattern}")
            if self.answers.state_management:
                print(f"  State: {self.answers.state_management}")

        print()

    def save_session(self, session_file: Path = None):
        """Save Q&A session for resuming later"""
        if session_file is None:
            session_file = Path(".template-init-session.json")

        import json
        from dataclasses import asdict

        data = asdict(self.answers)
        session_file.write_text(json.dumps(data, indent=2))
        print(f"✓ Session saved to {session_file}")

    @staticmethod
    def load_session(session_file: Path = None) -> Optional[GreenfieldAnswers]:
        """Load saved Q&A session"""
        if session_file is None:
            session_file = Path(".template-init-session.json")

        if not session_file.exists():
            return None

        import json
        data = json.loads(session_file.read_text())

        return GreenfieldAnswers(**data)
```

## Testing Strategy

```python
# tests/test_template_init_qa.py

def test_greenfield_qa_session_flow():
    """Test complete greenfield Q&A flow"""
    # Mock user inputs for all 9 sections
    answers = mock_greenfield_qa_session(
        template_name="test-template",
        primary_language="csharp",
        framework="maui",
        architecture_pattern="mvvm",
        # ... all other fields
    )

    assert answers.template_name == "test-template"
    assert answers.primary_language == "csharp"
    assert answers.framework == "maui"
    assert answers.architecture_pattern == "mvvm"

def test_conditional_sections():
    """Test conditional UI/backend sections"""
    # Test UI framework triggers UI section
    session = TemplateInitQASession()
    assert session._is_ui_framework("maui") == True
    assert session._is_ui_framework("aspnet-core") == False

    # Test backend framework triggers API section
    assert session._is_backend_framework("aspnet-core") == True
    assert session._is_backend_framework("maui") == False

def test_session_persistence():
    """Test save/load session"""
    session = TemplateInitQASession()
    # ... run session
    session.save_session(Path("/tmp/test-greenfield-session.json"))

    loaded = TemplateInitQASession.load_session(Path("/tmp/test-greenfield-session.json"))
    assert loaded.template_name == session.answers.template_name
```

## Integration with TASK-011

Q&A answers are passed to AI generation:

```python
# /template-init command flow (TASK-011)
def template_init():
    """Complete greenfield template creation flow"""

    # Step 1: Q&A (TASK-001B)
    qa = TemplateInitQASession()
    answers = qa.run()

    if not answers:
        return  # User cancelled

    # Step 2: AI Generation
    # AI uses answers to generate intelligent defaults
    from .ai_generator import AITemplateGenerator

    generator = AITemplateGenerator(greenfield_context=answers)
    template = generator.generate(answers)

    # Step 3: Agent Setup
    from .agent_orchestration import get_agents_for_template

    agents = get_agents_for_template(
        analysis=template.inferred_analysis,
        enable_external=False  # Phase 1
    )

    # Step 4: Save Template
    save_template(template, agents, answers.template_name)
```

## Shared Infrastructure with TASK-001

**Opportunity for Reuse** (from architectural review):

Both TASK-001 (brownfield) and TASK-001B (greenfield) share common infrastructure:

```python
# src/commands/shared/base_qa_session.py

class BaseQASession:
    """Shared Q&A session base class"""

    def save_session(self, session_file: Path):
        """Common save logic"""
        pass

    @staticmethod
    def load_session(session_file: Path):
        """Common load logic"""
        pass

    def _show_summary_section(self, title: str, items: dict):
        """Common summary display"""
        pass
```

**Estimated Savings**: 2-3 hours if shared infrastructure is implemented first.

## Definition of Done

- [ ] Interactive Q&A flow implemented with all 9 sections (~40 questions)
- [ ] Context-dependent questions (UI, backend, data access)
- [ ] Session save/load functionality working
- [ ] Input validation for all questions
- [ ] Summary display before proceeding
- [ ] Option to skip Q&A (advanced users)
- [ ] Unit tests for Q&A flow passing (>85% coverage)
- [ ] Integration with TASK-011 (passes context to AI generator)
- [ ] User-friendly error messages and help text
- [ ] Conditional sections based on technology choices

**Estimated Time**: 8 hours | **Complexity**: 5/10 | **Priority**: HIGH

**Rationale for Higher Complexity**:
- 9 sections vs 8 questions (brownfield)
- Conditional logic (UI, backend, data access)
- Context-dependent framework selection
- More complex data structure (GreenfieldAnswers)

## Benefits

- ✅ Guides users through technology decisions
- ✅ Provides intelligent defaults for AI generation
- ✅ Comprehensive coverage of architecture decisions
- ✅ Conditional questions reduce noise (only ask relevant)
- ✅ Sets expectations for template capabilities
- ✅ Familiar UX (same pattern as /gather-requirements and /template-create)
- ✅ Reduces AI token usage (focused generation)
- ✅ Better user experience (guided vs guessing)

---

**Created**: 2025-11-01
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Blocks**: TASK-011 (Template Init Command Orchestrator)
**Integration**: Provides GreenfieldAnswers → AI Template Generator → Agent Orchestration
