"""
Greenfield Q&A Session for /template-init command.

This module implements an interactive Q&A session that guides users through
greenfield template creation from scratch (no existing codebase). It gathers
technology stack and architecture decisions before AI generates intelligent defaults.

Architecture:
    - GreenfieldAnswers: Dataclass holding all user responses from 10 sections
    - TemplateInitQASession: Main coordinator for interactive Q&A flow

Example:
    >>> from greenfield_qa_session import TemplateInitQASession
    >>>
    >>> session = TemplateInitQASession()
    >>> answers = session.run()
    >>> if answers:
    ...     session.save_session()
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

try:
    import inquirer
    from inquirer import Text, List as InquirerList, Checkbox, Confirm
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False


@dataclass
class GreenfieldAnswers:
    """
    Answers from greenfield Q&A session.

    Captures all user responses across 10 sections for greenfield template creation.

    Attributes:
        # Section 1: Template Identity
        template_name: Template identifier name
        template_purpose: Purpose of the template (quick_start, team_standards, etc.)

        # Section 2: Technology Stack
        primary_language: Primary programming language
        framework: Framework choice (context-dependent on language)
        framework_version: Version of the framework

        # Section 3: Architecture
        architecture_pattern: Architecture pattern (MVVM, Clean, Hexagonal, etc.)
        domain_modeling: Domain logic organization approach

        # Section 4: Project Structure
        layer_organization: Project structure preference
        standard_folders: List of standard folders to include

        # Section 5: Testing
        unit_testing_framework: Unit testing framework choice
        testing_scope: List of test types to include
        test_pattern: Test pattern preference (AAA, BDD, none)

        # Section 6: Error Handling
        error_handling: Error handling strategy
        validation_approach: Input validation strategy

        # Section 7: Dependency Management
        dependency_injection: DI approach
        configuration_approach: Configuration management approach

        # Section 8: UI/Navigation (optional)
        ui_architecture: UI architecture pattern (if UI framework)
        navigation_pattern: Navigation approach (if UI framework)

        # Section 9: Additional Patterns
        data_access: Data access pattern (if applicable)
        api_pattern: API pattern preference (if backend)
        state_management: State management approach (if UI)

        # Section 10: Documentation Input
        documentation_paths: List of file paths to documentation
        documentation_text: Direct text input of documentation
        documentation_urls: List of URLs to documentation
        documentation_usage: How to use provided documentation

    Example:
        >>> answers = GreenfieldAnswers(
        ...     template_name="my-maui-template",
        ...     template_purpose="production",
        ...     primary_language="csharp",
        ...     framework="maui",
        ...     # ... other fields
        ... )
    """
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

    # Section 10: Documentation Input
    documentation_paths: Optional[List[Path]] = None
    documentation_text: Optional[str] = None
    documentation_urls: Optional[List[str]] = None
    documentation_usage: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert answers to dictionary for serialization.

        Returns:
            dict: Serializable dictionary with all answers

        Example:
            >>> answers.to_dict()
            {
                "template_name": "my-template",
                "template_purpose": "production",
                ...
            }
        """
        data = asdict(self)
        # Convert Path objects to strings
        if self.documentation_paths:
            data["documentation_paths"] = [str(p) for p in self.documentation_paths]
        return data

    @staticmethod
    def from_dict(data: dict) -> "GreenfieldAnswers":
        """
        Create GreenfieldAnswers from dictionary.

        Args:
            data: Dictionary with answer data

        Returns:
            GreenfieldAnswers: Reconstructed answers object

        Example:
            >>> data = {"template_name": "my-template", ...}
            >>> answers = GreenfieldAnswers.from_dict(data)
        """
        # Convert string paths back to Path objects
        if data.get("documentation_paths"):
            data["documentation_paths"] = [Path(p) for p in data["documentation_paths"]]

        return GreenfieldAnswers(**data)


class TemplateInitQASession:
    """
    Interactive Q&A session for /template-init (greenfield).

    Guides users through creating a new project template from scratch by
    asking structured questions across 10 sections. Handles conditional
    sections based on technology choices and provides session persistence.

    Example:
        >>> session = TemplateInitQASession()
        >>> answers = session.run()
        >>> if answers:
        ...     session.save_session()
        ...     print(f"Template: {answers.template_name}")
    """

    def __init__(self):
        """Initialize Q&A session."""
        if not INQUIRER_AVAILABLE:
            raise ImportError(
                "inquirer library not installed. "
                "Install with: pip install inquirer"
            )

        self.answers: Optional[GreenfieldAnswers] = None
        self._session_data: dict = {}

    def run(self) -> Optional[GreenfieldAnswers]:
        """
        Run interactive Q&A session for greenfield template creation.

        Executes all 10 sections sequentially, with conditional sections
        based on technology choices. Displays summary and confirms before
        proceeding.

        Returns:
            GreenfieldAnswers: User responses, or None if cancelled

        Example:
            >>> session = TemplateInitQASession()
            >>> answers = session.run()
            >>> if answers:
            ...     print(f"Collected {len(answers.to_dict())} answers")
        """
        print("\n" + "=" * 60)
        print("  /template-init - Greenfield Template Creation")
        print("=" * 60 + "\n")

        print("This Q&A will guide you through creating a new project template.")
        print("Press Ctrl+C at any time to save and exit.\n")

        try:
            # Section 1: Template Identity
            self._section1_identity()

            # Section 2: Technology Stack
            self._section2_technology()

            # Section 3: Architecture
            self._section3_architecture()

            # Section 4: Project Structure
            self._section4_structure()

            # Section 5: Testing
            self._section5_testing()

            # Section 6: Error Handling
            self._section6_error_handling()

            # Section 7: Dependency Management
            self._section7_dependencies()

            # Section 8: UI/Navigation (conditional)
            if self._is_ui_framework(self._session_data.get("framework", "")):
                self._section8_ui_navigation()

            # Section 9: Additional Patterns
            self._section9_additional_patterns()

            # Section 10: Documentation Input
            self._section10_documentation()

            # Build final answers
            self.answers = GreenfieldAnswers(**self._session_data)

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

        except KeyboardInterrupt:
            print("\n\nQ&A session interrupted. Saving partial session...")
            self._save_partial_session()
            return None

        except Exception as e:
            print(f"\n\nError during Q&A session: {e}")
            return None

    def _section1_identity(self) -> None:
        """Section 1: Template Identity."""
        print("\n" + "-" * 60)
        print("  Section 1: Template Identity")
        print("-" * 60 + "\n")

        questions = [
            Text(
                'template_name',
                message="Template name",
                default="my-template"
            ),
            InquirerList(
                'template_purpose',
                message="Template purpose",
                choices=[
                    ("Start new projects quickly", "quick_start"),
                    ("Enforce team standards", "team_standards"),
                    ("Prototype/experiment", "prototype"),
                    ("Production-ready scaffold", "production"),
                ]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self._session_data.update(answers)

    def _section2_technology(self) -> None:
        """Section 2: Technology Stack."""
        print("\n" + "-" * 60)
        print("  Section 2: Technology Stack")
        print("-" * 60 + "\n")

        # Primary language
        language_question = [
            InquirerList(
                'primary_language',
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
        ]

        language_answer = inquirer.prompt(language_question)
        if language_answer:
            self._session_data.update(language_answer)

            # Framework (context-dependent)
            framework = self._ask_framework(language_answer['primary_language'])
            self._session_data['framework'] = framework

            # Framework version
            version_questions = [
                InquirerList(
                    'framework_version_choice',
                    message="Framework version",
                    choices=[
                        ("Latest stable [RECOMMENDED]", "latest"),
                        ("Specific version", "specific"),
                        ("LTS (long-term support)", "lts"),
                    ]
                )
            ]

            version_answer = inquirer.prompt(version_questions)
            if version_answer:
                if version_answer['framework_version_choice'] == "specific":
                    specific_question = [Text('framework_version', message="Specify version")]
                    specific_answer = inquirer.prompt(specific_question)
                    if specific_answer:
                        self._session_data['framework_version'] = specific_answer['framework_version']
                else:
                    self._session_data['framework_version'] = version_answer['framework_version_choice']

    def _ask_framework(self, language: str) -> str:
        """
        Ask framework based on language selection.

        Args:
            language: Primary language chosen by user

        Returns:
            str: Framework choice
        """
        if language == "csharp":
            questions = [
                InquirerList(
                    'framework',
                    message=".NET framework/platform",
                    choices=[
                        (".NET MAUI (mobile/desktop)", "maui"),
                        ("ASP.NET Core (web API)", "aspnet-core"),
                        ("Blazor (web UI)", "blazor"),
                        ("WPF (desktop)", "wpf"),
                        ("Console application", "console"),
                    ]
                )
            ]

        elif language == "typescript":
            questions = [
                InquirerList(
                    'framework',
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
            ]

        elif language == "python":
            questions = [
                InquirerList(
                    'framework',
                    message="Python framework",
                    choices=[
                        ("FastAPI (web API)", "fastapi"),
                        ("Django (full-stack)", "django"),
                        ("Flask (web API)", "flask"),
                        ("Data science (Jupyter/pandas)", "data-science"),
                        ("CLI application", "cli"),
                    ]
                )
            ]

        else:
            questions = [Text('framework', message=f"Specify framework for {language}")]

        answer = inquirer.prompt(questions)
        return answer['framework'] if answer else ""

    def _section3_architecture(self) -> None:
        """Section 3: Architecture."""
        print("\n" + "-" * 60)
        print("  Section 3: Architecture Pattern")
        print("-" * 60 + "\n")

        questions = [
            InquirerList(
                'architecture_pattern',
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
            ),
            InquirerList(
                'domain_modeling',
                message="Domain logic organization",
                choices=[
                    ("Rich domain models (entities with behavior)", "rich"),
                    ("Anemic models + service layer", "anemic"),
                    ("Functional domain operations (verb-based)", "functional"),
                    ("Data-centric (minimal domain layer)", "data-centric"),
                ]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self._session_data.update(answers)

    def _section4_structure(self) -> None:
        """Section 4: Project Structure."""
        print("\n" + "-" * 60)
        print("  Section 4: Project Structure")
        print("-" * 60 + "\n")

        questions = [
            InquirerList(
                'layer_organization',
                message="Project structure preference",
                choices=[
                    ("Single project (simple)", "single"),
                    ("Multiple projects by layer", "by-layer"),
                    ("Multiple projects by feature", "by-feature"),
                    ("Hybrid (layers + features)", "hybrid"),
                ]
            ),
            Checkbox(
                'standard_folders',
                message="Include standard folders (Space to select, Enter to continue)",
                choices=[
                    ("src/ (source code)", "src"),
                    ("tests/ (test code)", "tests"),
                    ("docs/ (documentation)", "docs"),
                    ("scripts/ (build/deploy)", "scripts"),
                    (".github/ (GitHub workflows)", "github"),
                    ("docker/ (containers)", "docker"),
                ],
                default=["src", "tests"]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            # Extract values from tuples (inquirer returns tuples for checkbox)
            if isinstance(answers.get('standard_folders'), list):
                if answers['standard_folders'] and isinstance(answers['standard_folders'][0], tuple):
                    answers['standard_folders'] = [item[1] if isinstance(item, tuple) else item
                                                   for item in answers['standard_folders']]
            self._session_data.update(answers)

    def _section5_testing(self) -> None:
        """Section 5: Testing Strategy."""
        print("\n" + "-" * 60)
        print("  Section 5: Testing Strategy")
        print("-" * 60 + "\n")

        # Unit testing framework
        framework_questions = [
            InquirerList(
                'unit_testing_framework_choice',
                message="Unit testing framework",
                choices=[
                    ("Auto-select best for language [RECOMMENDED]", "auto"),
                    ("Specify framework", "specify"),
                ]
            )
        ]

        framework_answer = inquirer.prompt(framework_questions)
        if framework_answer:
            if framework_answer['unit_testing_framework_choice'] == "specify":
                specific_question = [Text('unit_testing_framework', message="Testing framework name")]
                specific_answer = inquirer.prompt(specific_question)
                if specific_answer:
                    self._session_data['unit_testing_framework'] = specific_answer['unit_testing_framework']
            else:
                self._session_data['unit_testing_framework'] = "auto"

        # Testing scope and pattern
        scope_questions = [
            Checkbox(
                'testing_scope',
                message="Types of tests to include (Space to select, Enter to continue)",
                choices=[
                    ("Unit tests", "unit"),
                    ("Integration tests", "integration"),
                    ("End-to-end tests", "e2e"),
                    ("Performance tests", "performance"),
                    ("Security tests", "security"),
                ],
                default=["unit", "integration"]
            ),
            InquirerList(
                'test_pattern',
                message="Test pattern preference",
                choices=[
                    ("Arrange-Act-Assert (AAA)", "aaa"),
                    ("Given-When-Then (BDD)", "bdd"),
                    ("No preference", "none"),
                ]
            ),
        ]

        scope_answers = inquirer.prompt(scope_questions)
        if scope_answers:
            # Extract values from tuples
            if isinstance(scope_answers.get('testing_scope'), list):
                if scope_answers['testing_scope'] and isinstance(scope_answers['testing_scope'][0], tuple):
                    scope_answers['testing_scope'] = [item[1] if isinstance(item, tuple) else item
                                                     for item in scope_answers['testing_scope']]
            self._session_data.update(scope_answers)

    def _section6_error_handling(self) -> None:
        """Section 6: Error Handling."""
        print("\n" + "-" * 60)
        print("  Section 6: Error Handling")
        print("-" * 60 + "\n")

        questions = [
            InquirerList(
                'error_handling',
                message="Error handling strategy",
                choices=[
                    ("Result/Either type (ErrorOr<T>, Result<T, E>)", "result"),
                    ("Exceptions (try-catch)", "exceptions"),
                    ("Error codes/status objects", "codes"),
                    ("Mixed approach", "mixed"),
                    ("Minimal (language defaults)", "minimal"),
                ]
            ),
            InquirerList(
                'validation_approach',
                message="Input validation strategy",
                choices=[
                    ("FluentValidation (or equivalent)", "fluent"),
                    ("Data annotations/attributes", "annotations"),
                    ("Manual validation in code", "manual"),
                    ("Minimal validation", "minimal"),
                ]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self._session_data.update(answers)

    def _section7_dependencies(self) -> None:
        """Section 7: Dependency Management."""
        print("\n" + "-" * 60)
        print("  Section 7: Dependency Management")
        print("-" * 60 + "\n")

        questions = [
            InquirerList(
                'dependency_injection',
                message="Dependency injection approach",
                choices=[
                    ("Built-in DI container [RECOMMENDED]", "builtin"),
                    ("Third-party DI (Autofac, etc.)", "third-party"),
                    ("Manual DI (constructor injection)", "manual"),
                    ("Not needed", "none"),
                ]
            ),
            InquirerList(
                'configuration_approach',
                message="Configuration approach",
                choices=[
                    ("JSON files (appsettings.json)", "json"),
                    ("Environment variables", "env"),
                    ("Both (JSON + env vars)", "both"),
                    ("Configuration service", "service"),
                    ("Minimal (hardcoded)", "minimal"),
                ]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self._session_data.update(answers)

    def _section8_ui_navigation(self) -> None:
        """Section 8: UI/Navigation (optional)."""
        print("\n" + "-" * 60)
        print("  Section 8: UI/Navigation")
        print("-" * 60 + "\n")

        questions = [
            InquirerList(
                'ui_architecture',
                message="UI architecture pattern",
                choices=[
                    ("MVVM (ViewModel binding)", "mvvm"),
                    ("MVC (Model-View-Controller)", "mvc"),
                    ("Component-based (React, Vue)", "component"),
                    ("Simple code-behind", "codebehind"),
                ]
            ),
            InquirerList(
                'navigation_pattern',
                message="Navigation approach",
                choices=[
                    ("Framework-recommended [RECOMMENDED]", "recommended"),
                    ("Custom navigation", "custom"),
                    ("Minimal (single page)", "minimal"),
                ]
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            self._session_data.update(answers)

    def _section9_additional_patterns(self) -> None:
        """Section 9: Additional Patterns."""
        print("\n" + "-" * 60)
        print("  Section 9: Additional Patterns")
        print("-" * 60 + "\n")

        # Data access
        data_access_question = [
            Confirm(
                'needs_data_access',
                message="Does this template need data access?",
                default=True
            )
        ]

        data_access_answer = inquirer.prompt(data_access_question)
        if data_access_answer and data_access_answer['needs_data_access']:
            data_access_pattern = [
                InquirerList(
                    'data_access',
                    message="Data access pattern",
                    choices=[
                        ("Repository pattern", "repository"),
                        ("Direct database access", "direct"),
                        ("CQRS (separate read/write)", "cqrs"),
                        ("Event sourcing", "eventsourcing"),
                    ]
                )
            ]
            pattern_answer = inquirer.prompt(data_access_pattern)
            if pattern_answer:
                self._session_data['data_access'] = pattern_answer['data_access']
        else:
            self._session_data['data_access'] = None

        # API pattern (if backend)
        if self._is_backend_framework(self._session_data.get("framework", "")):
            api_questions = [
                InquirerList(
                    'api_pattern',
                    message="API pattern preference",
                    choices=[
                        ("REST (resource-based)", "rest"),
                        ("REPR (Request-Endpoint-Response)", "repr"),
                        ("Minimal APIs", "minimal"),
                        ("GraphQL", "graphql"),
                        ("gRPC", "grpc"),
                    ]
                )
            ]
            api_answer = inquirer.prompt(api_questions)
            if api_answer:
                self._session_data['api_pattern'] = api_answer['api_pattern']
        else:
            self._session_data['api_pattern'] = None

        # State management (if UI)
        if self._is_ui_framework(self._session_data.get("framework", "")):
            state_questions = [
                InquirerList(
                    'state_management_choice',
                    message="State management approach",
                    choices=[
                        ("Framework-recommended [RECOMMENDED]", "recommended"),
                        ("Minimal (local state only)", "minimal"),
                        ("Specify library", "specify"),
                    ]
                )
            ]
            state_answer = inquirer.prompt(state_questions)
            if state_answer:
                if state_answer['state_management_choice'] == "specify":
                    specific_question = [Text('state_management', message="State management library")]
                    specific_answer = inquirer.prompt(specific_question)
                    if specific_answer:
                        self._session_data['state_management'] = specific_answer['state_management']
                else:
                    self._session_data['state_management'] = state_answer['state_management_choice']
        else:
            self._session_data['state_management'] = None

    def _section10_documentation(self) -> None:
        """Section 10: Documentation Input."""
        print("\n" + "-" * 60)
        print("  Section 10: Documentation Input")
        print("-" * 60 + "\n")

        print("Do you have documentation to guide template creation?")
        print("Examples: ADRs, coding standards, API specs, design docs, engineering guidelines\n")

        doc_questions = [
            InquirerList(
                'documentation_input_type',
                message="Documentation input method",
                choices=[
                    ("Provide file paths", "paths"),
                    ("Paste text directly", "text"),
                    ("Provide URLs", "urls"),
                    ("None", "none"),
                ]
            )
        ]

        doc_answer = inquirer.prompt(doc_questions)
        if not doc_answer or doc_answer['documentation_input_type'] == "none":
            self._session_data['documentation_paths'] = None
            self._session_data['documentation_text'] = None
            self._session_data['documentation_urls'] = None
            self._session_data['documentation_usage'] = None
            return

        input_type = doc_answer['documentation_input_type']

        if input_type == "paths":
            path_question = [Text('doc_paths', message="Enter file paths (comma-separated)")]
            path_answer = inquirer.prompt(path_question)
            if path_answer and path_answer['doc_paths']:
                paths = [Path(p.strip()) for p in path_answer['doc_paths'].split(',')]
                self._session_data['documentation_paths'] = paths

        elif input_type == "text":
            text_question = [Text('doc_text', message="Paste documentation text (or path to file)")]
            text_answer = inquirer.prompt(text_question)
            if text_answer:
                self._session_data['documentation_text'] = text_answer['doc_text']

        elif input_type == "urls":
            url_question = [Text('doc_urls', message="Enter URLs (comma-separated)")]
            url_answer = inquirer.prompt(url_question)
            if url_answer and url_answer['doc_urls']:
                urls = [u.strip() for u in url_answer['doc_urls'].split(',')]
                self._session_data['documentation_urls'] = urls

        # Ask about usage if documentation provided
        if input_type != "none":
            usage_questions = [
                InquirerList(
                    'documentation_usage',
                    message="How should we use this documentation?",
                    choices=[
                        ("Follow patterns/standards strictly", "strict"),
                        ("Use as general guidance", "guidance"),
                        ("Extract naming conventions only", "naming"),
                        ("Understand architecture reasoning", "reasoning"),
                    ]
                )
            ]
            usage_answer = inquirer.prompt(usage_questions)
            if usage_answer:
                self._session_data['documentation_usage'] = usage_answer['documentation_usage']

    def _is_ui_framework(self, framework: str) -> bool:
        """
        Check if framework is UI-focused.

        Args:
            framework: Framework identifier

        Returns:
            bool: True if UI framework
        """
        ui_frameworks = [
            "maui", "blazor", "wpf",
            "react-nextjs", "react-vite", "angular", "vue"
        ]
        return framework in ui_frameworks

    def _is_backend_framework(self, framework: str) -> bool:
        """
        Check if framework is backend-focused.

        Args:
            framework: Framework identifier

        Returns:
            bool: True if backend framework
        """
        backend_frameworks = [
            "aspnet-core", "nestjs", "express",
            "fastapi", "django", "flask"
        ]
        return framework in backend_frameworks

    def _show_summary(self) -> None:
        """Display summary of answers."""
        if not self.answers:
            return

        print("\n" + "=" * 60)
        print("  Q&A Summary")
        print("=" * 60 + "\n")

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

        if self.answers.documentation_paths or self.answers.documentation_text or self.answers.documentation_urls:
            print(f"\nDocumentation:")
            if self.answers.documentation_paths:
                print(f"  Paths: {len(self.answers.documentation_paths)} file(s)")
            if self.answers.documentation_text:
                print(f"  Text: {len(self.answers.documentation_text)} characters")
            if self.answers.documentation_urls:
                print(f"  URLs: {len(self.answers.documentation_urls)} URL(s)")
            if self.answers.documentation_usage:
                print(f"  Usage: {self.answers.documentation_usage}")

        print()

    def save_session(self, session_file: Optional[Path] = None) -> None:
        """
        Save Q&A session for resuming later.

        Args:
            session_file: Optional path to save session (default: .template-init-session.json)

        Example:
            >>> session.save_session()
            ✓ Session saved to .template-init-session.json
        """
        if not self.answers:
            print("⚠️ No answers to save.")
            return

        if session_file is None:
            session_file = Path(".template-init-session.json")

        data = self.answers.to_dict()
        session_file.write_text(json.dumps(data, indent=2))
        print(f"✓ Session saved to {session_file}")

    @staticmethod
    def load_session(session_file: Optional[Path] = None) -> Optional[GreenfieldAnswers]:
        """
        Load saved Q&A session.

        Args:
            session_file: Optional path to load session from

        Returns:
            GreenfieldAnswers: Loaded answers, or None if file not found

        Example:
            >>> answers = TemplateInitQASession.load_session()
            >>> if answers:
            ...     print(f"Loaded template: {answers.template_name}")
        """
        if session_file is None:
            session_file = Path(".template-init-session.json")

        if not session_file.exists():
            return None

        data = json.loads(session_file.read_text())
        return GreenfieldAnswers.from_dict(data)

    def _save_partial_session(self) -> None:
        """Save partial session data when interrupted."""
        if not self._session_data:
            print("No data to save.")
            return

        session_file = Path(".template-init-partial-session.json")
        session_file.write_text(json.dumps(self._session_data, indent=2, default=str))
        print(f"\n✓ Partial session saved to {session_file}")
        print("You can review and manually edit this file if needed.\n")


# Module exports
__all__ = [
    "GreenfieldAnswers",
    "TemplateInitQASession",
]
