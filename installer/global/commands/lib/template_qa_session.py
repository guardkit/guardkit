"""
Template Q&A Session Manager.

Main class for running the interactive Q&A session.
Uses Python stdlib only (no external dependencies).

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Try relative imports first, fall back to absolute imports
try:
    from . import template_qa_questions as questions
    from . import template_qa_validator as validator
    from . import template_qa_display as display
    from . import template_qa_persistence as persistence
except ImportError:
    import template_qa_questions as questions
    import template_qa_validator as validator
    import template_qa_display as display
    import template_qa_persistence as persistence


@dataclass
class GreenfieldAnswers:
    """
    Complete answers from greenfield Q&A session.

    This dataclass holds all user responses from the 10 question sections.
    """

    # Section 1: Template Identity (required fields)
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

    # Section 1: Template Identity (optional fields)
    description: Optional[str] = None
    version: str = "1.0.0"
    author: Optional[str] = None

    # Section 8: UI/Navigation (optional)
    ui_architecture: Optional[str] = None
    navigation_pattern: Optional[str] = None

    # Section 9: Additional Patterns
    needs_data_access: Optional[bool] = None
    data_access: Optional[str] = None
    api_pattern: Optional[str] = None
    state_management: Optional[str] = None

    # Section 10: Documentation Input
    has_documentation: Optional[bool] = None
    documentation_input_method: Optional[str] = None
    documentation_paths: Optional[List[Path]] = None
    documentation_text: Optional[str] = None
    documentation_urls: Optional[List[str]] = None
    documentation_usage: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert Path objects to strings
        if data.get("documentation_paths"):
            data["documentation_paths"] = [str(p) for p in data["documentation_paths"]]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GreenfieldAnswers":
        """Create from dictionary (for deserialization)."""
        # Convert string paths back to Path objects
        if data.get("documentation_paths"):
            data["documentation_paths"] = [Path(p) for p in data["documentation_paths"]]
        return cls(**data)


class TemplateQASession:
    """
    Interactive Q&A session manager for /template-init (greenfield).

    Handles the complete flow of asking questions, validating answers,
    and managing session state.
    """

    def __init__(self, session_file: Optional[Path] = None, skip_qa: bool = False):
        """
        Initialize Q&A session.

        Args:
            session_file: Optional path to session file for save/resume
            skip_qa: If True, use default values for all questions
        """
        self.session_file = session_file
        self.skip_qa = skip_qa
        self.answers: Dict[str, Any] = {}
        self.result: Optional[GreenfieldAnswers] = None

    def run(self) -> Optional[GreenfieldAnswers]:
        """
        Run the complete Q&A session.

        Returns:
            GreenfieldAnswers with user responses, or None if cancelled
        """
        # Show intro
        if not self.skip_qa:
            self._show_intro()

        # Check for existing session
        if not self.skip_qa and self._check_resume_session():
            # User chose to resume
            pass

        try:
            # Run through all sections
            self._section1_identity()
            self._section2_technology()
            self._section3_architecture()
            self._section4_structure()
            self._section5_testing()
            self._section6_error_handling()
            self._section7_dependencies()

            # Conditional sections
            if self._is_ui_framework(self.answers.get("framework", "")):
                self._section8_ui_navigation()

            if self._is_backend_framework(self.answers.get("framework", "")) or \
               self._is_ui_framework(self.answers.get("framework", "")):
                self._section9_additional_patterns()

            self._section10_documentation()

            # Build result
            self.result = self._build_result()

            # Show summary and confirm
            if not self.skip_qa:
                display.print_complete_summary(self.result.to_dict())

                if not self._confirm_proceed():
                    display.print_info("Q&A session cancelled. Run command again to restart.")
                    return None

            return self.result

        except KeyboardInterrupt:
            display.print_info("\n\nSession interrupted. Saving progress...")
            self._save_session()
            display.print_success(f"Session saved to {self.session_file or persistence.DEFAULT_SESSION_FILE}")
            display.print_info("Run the command again to resume from where you left off.")
            sys.exit(0)

        except Exception as e:
            display.print_error(f"Unexpected error: {e}")
            display.print_info("Attempting to save session...")
            try:
                self._save_session()
                display.print_success("Session saved successfully")
            except:
                pass
            raise

    def _show_intro(self) -> None:
        """Display intro banner and instructions."""
        display.print_banner("/template-init - Greenfield Template Creation")
        display.print_info("This Q&A will guide you through creating a new project template.")
        display.print_info("Press Ctrl+C at any time to save and exit.\n")

    def _check_resume_session(self) -> bool:
        """Check if user wants to resume an existing session."""
        if persistence.session_exists(self.session_file):
            summary = persistence.get_session_summary(self.session_file)
            display.print_info(
                f"Found existing session saved at {summary.get('saved_at', 'unknown time')}"
            )
            display.print_info(f"Progress: {summary.get('sections_completed', 0)} sections completed")

            prompt = display.prompt_confirm("Resume from saved session?", default=True)
            response = input(prompt).strip().lower()

            try:
                if not response or validator.validate_confirm(response):
                    # Load session
                    self.answers = persistence.load_session(self.session_file)
                    display.print_success("Session loaded successfully")
                    return True
            except validator.ValidationError:
                pass

        return False

    def _save_session(self) -> None:
        """Save current session state."""
        persistence.save_session(self.answers, self.session_file)

    def _ask_question(self, question: questions.Question) -> Any:
        """
        Ask a single question and return validated answer.

        Args:
            question: Question object to ask

        Returns:
            Validated answer
        """
        # Check if question should be asked (conditional logic)
        if not questions.should_ask_question(question, self.answers):
            return None

        # Skip if using defaults
        if self.skip_qa:
            return question.default

        # Ask based on question type
        if question.type == "text":
            return self._ask_text(question)
        elif question.type == "choice":
            return self._ask_choice(question)
        elif question.type == "multi_choice":
            return self._ask_multi_choice(question)
        elif question.type == "confirm":
            return self._ask_confirm(question)
        else:
            raise ValueError(f"Unknown question type: {question.type}")

    def _ask_text(self, question: questions.Question) -> str:
        """Ask a text question."""
        prompt = display.prompt_text(question.text, question.default, question.help_text)

        while True:
            response = input(prompt).strip()

            # Use default if empty
            if not response and question.default:
                response = question.default

            # Validate
            try:
                if question.id == "template_name":
                    return validator.validate_template_name(response)
                elif question.validation == "non_empty":
                    return validator.validate_non_empty(response)
                elif question.validation == "min_length_10":
                    return validator.validate_text_length(response, min_length=10, field_name="Description")
                elif question.validation == "version_string":
                    return validator.validate_version_string(response)
                else:
                    return response
            except validator.ValidationError as e:
                display.print_error(str(e))
                prompt = "Please try again: "

    def _ask_choice(self, question: questions.Question) -> str:
        """Ask a single choice question."""
        # Get choices (may be context-dependent)
        choices = question.choices
        if question.id == "framework":
            language = self.answers.get("primary_language", "")
            choices = questions.get_framework_choices(language)

        prompt = display.prompt_choice(question.text, choices, question.default, question.help_text)

        while True:
            response = input(prompt).strip()

            # Use default if empty
            if not response and question.default:
                return question.default

            # Convert number to value
            try:
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1][1]
                else:
                    display.print_error(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                # Try direct value match
                try:
                    return validator.validate_choice(response, choices)
                except validator.ValidationError as e:
                    display.print_error(str(e))

            prompt = "Please try again: "

    def _ask_multi_choice(self, question: questions.Question) -> List[str]:
        """Ask a multi-choice question."""
        prompt = display.prompt_multi_choice(question.text, question.choices, question.help_text)

        while True:
            response = input(prompt).strip()

            # Use defaults if empty
            if not response:
                defaults = [choice[1] for choice in question.choices if len(choice) > 2 and choice[2]]
                if defaults:
                    return defaults

            # Parse numbers
            try:
                numbers = validator.validate_numeric_list(response, min_value=1, max_value=len(question.choices))
                selected = [question.choices[n - 1][1] for n in numbers]
                return selected
            except validator.ValidationError as e:
                display.print_error(str(e))
                prompt = "Please try again: "

    def _ask_confirm(self, question: questions.Question) -> bool:
        """Ask a confirmation question."""
        prompt = display.prompt_confirm(question.text, question.default, question.help_text)

        while True:
            response = input(prompt).strip()

            # Use default if empty
            if not response:
                return question.default

            try:
                return validator.validate_confirm(response)
            except validator.ValidationError as e:
                display.print_error(str(e))
                prompt = "Please try again: "

    def _section1_identity(self) -> None:
        """Section 1: Template Identity."""
        if not self.skip_qa:
            display.print_section_header("Section 1: Template Identity")

        for question in questions.SECTION1_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section2_technology(self) -> None:
        """Section 2: Technology Stack."""
        if not self.skip_qa:
            display.print_section_header("Section 2: Technology Stack")

        # Primary language
        lang_question = questions.SECTION2_QUESTIONS[0]
        self.answers[lang_question.id] = self._ask_question(lang_question)

        # Framework (context-dependent)
        framework_question = questions.Question(
            id="framework",
            section="Technology Stack",
            text=".NET framework/platform:" if self.answers["primary_language"] == "csharp" else "Framework:",
            type="choice",
            choices=[],  # Will be populated in _ask_choice
            default="maui" if self.answers["primary_language"] == "csharp" else "fastapi"
        )
        self.answers["framework"] = self._ask_question(framework_question)

        # Version
        version_question = questions.SECTION2_QUESTIONS[1]
        self.answers[version_question.id] = self._ask_question(version_question)

        # Handle specific version input
        if self.answers["framework_version"] == "specific" and not self.skip_qa:
            specific_prompt = display.prompt_text("Specify version")
            specific_version = input(specific_prompt).strip()
            try:
                self.answers["framework_version"] = validator.validate_version_string(specific_version)
            except validator.ValidationError:
                display.print_warning("Invalid version format, using 'latest'")
                self.answers["framework_version"] = "latest"

    def _section3_architecture(self) -> None:
        """Section 3: Architecture Pattern."""
        if not self.skip_qa:
            display.print_section_header("Section 3: Architecture Pattern")

        for question in questions.SECTION3_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section4_structure(self) -> None:
        """Section 4: Project Structure."""
        if not self.skip_qa:
            display.print_section_header("Section 4: Project Structure")

        for question in questions.SECTION4_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section5_testing(self) -> None:
        """Section 5: Testing Strategy."""
        if not self.skip_qa:
            display.print_section_header("Section 5: Testing Strategy")

        for question in questions.SECTION5_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

        # Handle specific framework input
        if self.answers.get("unit_testing_framework") == "specify" and not self.skip_qa:
            specific_prompt = display.prompt_text("Testing framework name")
            self.answers["unit_testing_framework"] = input(specific_prompt).strip() or "auto"

    def _section6_error_handling(self) -> None:
        """Section 6: Error Handling."""
        if not self.skip_qa:
            display.print_section_header("Section 6: Error Handling")

        for question in questions.SECTION6_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section7_dependencies(self) -> None:
        """Section 7: Dependency Management."""
        if not self.skip_qa:
            display.print_section_header("Section 7: Dependency Management")

        for question in questions.SECTION7_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section8_ui_navigation(self) -> None:
        """Section 8: UI/Navigation (conditional)."""
        if not self.skip_qa:
            display.print_section_header("Section 8: UI/Navigation")

        for question in questions.SECTION8_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

    def _section9_additional_patterns(self) -> None:
        """Section 9: Additional Patterns."""
        if not self.skip_qa:
            display.print_section_header("Section 9: Additional Patterns")

        for question in questions.SECTION9_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

        # Handle specific state management input
        if self.answers.get("state_management") == "specify" and not self.skip_qa:
            specific_prompt = display.prompt_text("State management library")
            self.answers["state_management"] = input(specific_prompt).strip() or "recommended"

    def _section10_documentation(self) -> None:
        """Section 10: Documentation Input."""
        if not self.skip_qa:
            display.print_section_header("Section 10: Documentation Input")

        for question in questions.SECTION10_QUESTIONS:
            answer = self._ask_question(question)
            if answer is not None:
                self.answers[question.id] = answer

        # Handle documentation input based on method
        if self.answers.get("has_documentation") and not self.skip_qa:
            method = self.answers.get("documentation_input_method")

            if method == "paths":
                self._collect_documentation_paths()
            elif method == "text":
                self._collect_documentation_text()
            elif method == "urls":
                self._collect_documentation_urls()

    def _collect_documentation_paths(self) -> None:
        """Collect file paths for documentation."""
        display.print_info("Enter file paths (one per line, empty line to finish):")
        paths = []

        while True:
            path_str = input("  Path: ").strip()
            if not path_str:
                break

            try:
                path = validator.validate_file_path(path_str, must_exist=True)
                paths.append(path)
                display.print_success(f"Added: {path}")
            except validator.ValidationError as e:
                display.print_error(str(e))

        self.answers["documentation_paths"] = paths

    def _collect_documentation_text(self) -> None:
        """Collect pasted text for documentation."""
        display.print_info("Paste documentation text (Ctrl+D or Ctrl+Z to finish):")
        lines = []

        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass

        self.answers["documentation_text"] = "\n".join(lines)

    def _collect_documentation_urls(self) -> None:
        """Collect URLs for documentation."""
        display.print_info("Enter URLs (one per line, empty line to finish):")
        urls = []

        while True:
            url_str = input("  URL: ").strip()
            if not url_str:
                break

            try:
                url = validator.validate_url(url_str)
                urls.append(url)
                display.print_success(f"Added: {url}")
            except validator.ValidationError as e:
                display.print_error(str(e))

        self.answers["documentation_urls"] = urls

    def _is_ui_framework(self, framework: str) -> bool:
        """Check if framework is UI-focused."""
        ui_frameworks = ["maui", "blazor", "wpf", "react-nextjs", "react-vite", "angular", "vue"]
        return framework in ui_frameworks

    def _is_backend_framework(self, framework: str) -> bool:
        """Check if framework is backend-focused."""
        backend_frameworks = ["aspnet-core", "nestjs", "express", "fastapi", "django", "flask"]
        return framework in backend_frameworks

    def _confirm_proceed(self) -> bool:
        """Ask user to confirm proceeding with template generation."""
        prompt = display.prompt_confirm(
            "Proceed with template generation using these settings?",
            default=True
        )
        response = input(prompt).strip()

        if not response:
            return True  # Default is True

        try:
            return validator.validate_confirm(response)
        except validator.ValidationError:
            return False

    def _build_result(self) -> GreenfieldAnswers:
        """Build GreenfieldAnswers from collected answers."""
        return GreenfieldAnswers(
            # Section 1
            template_name=self.answers.get("template_name", "my-template"),
            template_purpose=self.answers.get("template_purpose", "quick_start"),
            description=self.answers.get("description"),
            version=self.answers.get("version", "1.0.0"),
            author=self.answers.get("author"),
            # Section 2
            primary_language=self.answers.get("primary_language", "csharp"),
            framework=self.answers.get("framework", "maui"),
            framework_version=self.answers.get("framework_version", "latest"),
            # Section 3
            architecture_pattern=self.answers.get("architecture_pattern", "mvvm"),
            domain_modeling=self.answers.get("domain_modeling", "rich"),
            # Section 4
            layer_organization=self.answers.get("layer_organization", "single"),
            standard_folders=self.answers.get("standard_folders", ["src", "tests"]),
            # Section 5
            unit_testing_framework=self.answers.get("unit_testing_framework", "auto"),
            testing_scope=self.answers.get("testing_scope", ["unit", "integration"]),
            test_pattern=self.answers.get("test_pattern", "aaa"),
            # Section 6
            error_handling=self.answers.get("error_handling", "result"),
            validation_approach=self.answers.get("validation_approach", "fluent"),
            # Section 7
            dependency_injection=self.answers.get("dependency_injection", "builtin"),
            configuration_approach=self.answers.get("configuration_approach", "both"),
            # Section 8
            ui_architecture=self.answers.get("ui_architecture"),
            navigation_pattern=self.answers.get("navigation_pattern"),
            # Section 9
            needs_data_access=self.answers.get("needs_data_access"),
            data_access=self.answers.get("data_access"),
            api_pattern=self.answers.get("api_pattern"),
            state_management=self.answers.get("state_management"),
            # Section 10
            has_documentation=self.answers.get("has_documentation"),
            documentation_input_method=self.answers.get("documentation_input_method"),
            documentation_paths=self.answers.get("documentation_paths"),
            documentation_text=self.answers.get("documentation_text"),
            documentation_urls=self.answers.get("documentation_urls"),
            documentation_usage=self.answers.get("documentation_usage"),
        )


# Module exports
__all__ = [
    "GreenfieldAnswers",
    "TemplateQASession",
]
