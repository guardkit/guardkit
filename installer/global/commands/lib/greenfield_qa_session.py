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


def generate_boundary_sections(agent_type: str, technology: str) -> dict:
    """
    Generate ALWAYS/NEVER/ASK boundary sections for agent.

    Reused from template-create's agent enhancement logic (TASK-STND-773D).

    Args:
        agent_type: Type of agent (testing, repository, api, etc.)
        technology: Primary technology (python, typescript, csharp)

    Returns:
        dict with 'always', 'never', 'ask' lists

    Example:
        >>> boundaries = generate_boundary_sections('testing', 'python')
        >>> len(boundaries['always'])  # 5-7 rules
        5
    """
    boundaries = {
        "always": [],  # 5-7 rules
        "never": [],   # 5-7 rules
        "ask": []      # 3-5 scenarios
    }

    # Technology-specific boundaries (port from agent-content-enhancer.md)
    if agent_type == "testing":
        boundaries["always"] = [
            "✅ Run build verification before tests (block if compilation fails)",
            "✅ Execute in technology-specific test runner (pytest/vitest/dotnet test)",
            "✅ Report failures with actionable error messages (aid debugging)",
            "✅ Enforce 100% test pass rate (zero tolerance for failures)",
            "✅ Validate test coverage thresholds (ensure quality gates met)"
        ]
        boundaries["never"] = [
            "❌ Never approve code with failing tests (zero tolerance policy)",
            "❌ Never skip compilation check (prevents false positive test runs)",
            "❌ Never modify test code to make tests pass (integrity violation)",
            "❌ Never ignore coverage below threshold (quality gate bypass prohibited)",
            "❌ Never run tests without dependency installation (environment consistency required)"
        ]
        boundaries["ask"] = [
            "⚠️ Coverage 70-79%: Ask if acceptable given task complexity and risk level",
            "⚠️ Performance tests failing: Ask if acceptable for non-production changes",
            "⚠️ Flaky tests detected: Ask if should quarantine or fix immediately"
        ]
    elif agent_type == "repository":
        boundaries["always"] = [
            "✅ Inject repositories via constructor (enforces DI pattern)",
            "✅ Return ErrorOr<T> for all operations (consistent error handling)",
            "✅ Use async/await for database operations (prevents thread blocking)",
            "✅ Implement IDisposable for database connections (resource cleanup)",
            "✅ Validate input parameters before database access (prevent injection)"
        ]
        boundaries["never"] = [
            "❌ Never use `new()` for repository instantiation (breaks testability and DI)",
            "❌ Never expose IQueryable outside repository (violates encapsulation)",
            "❌ Never use raw SQL without parameterization (SQL injection risk)",
            "❌ Never ignore database errors (silent failures prohibited)",
            "❌ Never commit transactions within repository (violates SRP)"
        ]
        boundaries["ask"] = [
            "⚠️ Complex joins across >3 tables: Ask if raw SQL vs EF Core query",
            "⚠️ Caching strategy needed: Ask if in-memory vs distributed cache",
            "⚠️ Soft delete vs hard delete: Ask for data retention policy decision"
        ]
    elif agent_type == "api":
        boundaries["always"] = [
            "✅ Validate all input parameters (prevent injection and bad data)",
            "✅ Return consistent response format (successful and error responses)",
            "✅ Use appropriate HTTP status codes (200/201/400/404/500)",
            "✅ Implement request/response logging (audit trail and debugging)",
            "✅ Apply rate limiting for endpoints (prevent abuse)"
        ]
        boundaries["never"] = [
            "❌ Never expose internal errors to clients (security risk)",
            "❌ Never skip authentication/authorization checks (security violation)",
            "❌ Never return sensitive data in responses (data leakage)",
            "❌ Never use GET for state-changing operations (violates REST)",
            "❌ Never ignore content-type headers (prevents incorrect parsing)"
        ]
        boundaries["ask"] = [
            "⚠️ Large payload (>10MB): Ask if streaming vs standard response",
            "⚠️ Long-running operation (>30s): Ask if async pattern needed",
            "⚠️ Multiple related endpoints: Ask if batch endpoint makes sense"
        ]
    elif agent_type == "service":
        boundaries["always"] = [
            "✅ Inject dependencies via constructor (enforce DI pattern)",
            f"✅ Follow {technology} naming conventions (maintain consistency)",
            "✅ Validate inputs at service boundary (prevent bad data propagation)",
            "✅ Return explicit success/failure results (no silent failures)",
            "✅ Log important operations and errors (enable debugging and audit)"
        ]
        boundaries["never"] = [
            "❌ Never instantiate dependencies with `new()` (breaks DI and testing)",
            "❌ Never swallow exceptions without logging (silent failures prohibited)",
            "❌ Never mix business logic with infrastructure (violates separation of concerns)",
            "❌ Never return null for collections (return empty collections instead)",
            "❌ Never expose implementation details in interfaces (violates encapsulation)"
        ]
        boundaries["ask"] = [
            "⚠️ Complex business logic: Ask if should be moved to domain model",
            "⚠️ Multiple database calls: Ask if transaction needed",
            "⚠️ Caching opportunity: Ask if caching appropriate for this operation"
        ]
    else:
        # Generic boundaries for other agent types
        boundaries["always"] = [
            f"✅ Follow {technology} best practices (maintain code quality)",
            "✅ Validate all inputs (prevent bad data)",
            "✅ Handle errors gracefully (never crash silently)",
            "✅ Document public interfaces (enable team collaboration)",
            "✅ Write unit tests for core logic (ensure correctness)"
        ]
        boundaries["never"] = [
            "❌ Never ignore exceptions (detect issues early)",
            "❌ Never hardcode configuration (use environment variables)",
            "❌ Never skip logging (maintain observability)",
            "❌ Never violate separation of concerns (maintain modularity)",
            "❌ Never commit secrets or credentials (security risk)"
        ]
        boundaries["ask"] = [
            "⚠️ Complex algorithm: Ask if optimization needed vs readability",
            "⚠️ External service call: Ask if retry logic needed",
            "⚠️ Performance concern: Ask if caching appropriate"
        ]

    return boundaries


def validate_boundary_sections(boundaries: dict) -> tuple[bool, list]:
    """
    Validate boundary sections meet requirements.

    Reused from template-create validation (TASK-STND-773D).

    Args:
        boundaries: Dict with 'always', 'never', 'ask' keys

    Returns:
        (is_valid, error_list)

    Validation rules:
    - ALWAYS: 5-7 rules with ✅ prefix
    - NEVER: 5-7 rules with ❌ prefix
    - ASK: 3-5 scenarios with ⚠️ prefix
    """
    errors = []

    # Check counts
    always_count = len(boundaries.get("always", []))
    never_count = len(boundaries.get("never", []))
    ask_count = len(boundaries.get("ask", []))

    if always_count < 5 or always_count > 7:
        errors.append(f"ALWAYS section must have 5-7 rules (has {always_count})")
    if never_count < 5 or never_count > 7:
        errors.append(f"NEVER section must have 5-7 rules (has {never_count})")
    if ask_count < 3 or ask_count > 5:
        errors.append(f"ASK section must have 3-5 scenarios (has {ask_count})")

    # Check emoji format
    for rule in boundaries.get("always", []):
        if not rule.startswith("✅"):
            errors.append(f"ALWAYS rule missing ✅ prefix: {rule[:50]}")
    for rule in boundaries.get("never", []):
        if not rule.startswith("❌"):
            errors.append(f"NEVER rule missing ❌ prefix: {rule[:50]}")
    for scenario in boundaries.get("ask", []):
        if not scenario.startswith("⚠️"):
            errors.append(f"ASK scenario missing ⚠️ prefix: {scenario[:50]}")

    return len(errors) == 0, errors


class QualityScorer:
    """Calculate template quality score from Q&A answers."""

    def __init__(self, session_data: dict, template_path: Path):
        """
        Initialize quality scorer.

        Args:
            session_data: Q&A session answers
            template_path: Path to generated template
        """
        self.session_data = session_data
        self.template_path = template_path

    def calculate_score(self) -> dict:
        """
        Calculate 0-10 quality score from Q&A answers.

        Unlike template-create (codebase analysis), this scores based on:
        - Architecture pattern clarity
        - Testing strategy completeness
        - Error handling approach
        - Documentation planning
        - Agent coverage
        - Technology stack maturity

        Returns:
            dict with overall score, component scores, grade
        """
        scores = {
            'architecture_clarity': self._score_architecture(),
            'testing_coverage': self._score_testing(),
            'error_handling': self._score_error_handling(),
            'documentation': self._score_documentation(),
            'agent_coverage': self._score_agents(),
            'tech_stack_maturity': self._score_tech_stack()
        }

        overall = sum(scores.values()) / len(scores)

        return {
            'overall_score': round(overall, 1),
            'component_scores': scores,
            'grade': self._calculate_grade(overall),
            'production_ready': overall >= 7.0
        }

    def _score_architecture(self) -> float:
        """Score architecture pattern clarity (0-10)."""
        pattern = self.session_data.get('architecture_pattern', 'unknown')
        layer_org = self.session_data.get('layer_organization', 'single')

        # Known pattern: +5
        score = 5.0 if pattern not in ['unknown', 'simple'] else 2.0

        # Clear architecture patterns get bonus
        if pattern in ['mvvm', 'clean', 'hexagonal', 'layered']:
            score += 2.0

        # Layer organization: +3 for multi-project, +1 for single
        if layer_org in ['by-layer', 'by-feature', 'hybrid']:
            score += 3.0
        elif layer_org == 'single':
            score += 1.0

        return min(10.0, score)

    def _score_testing(self) -> float:
        """Score testing strategy (0-10)."""
        test_types = self.session_data.get('testing_scope', [])
        test_framework = self.session_data.get('unit_testing_framework', 'unknown')
        test_pattern = self.session_data.get('test_pattern', 'none')

        # Test type coverage: +2 per type (unit, integration, e2e)
        score = min(6.0, len(test_types) * 2.0)

        # Test framework specified: +2
        if test_framework not in ['unknown', '']:
            score += 2.0

        # Test pattern: +2 for AAA or BDD
        if test_pattern in ['aaa', 'bdd']:
            score += 2.0

        return min(10.0, score)

    def _score_error_handling(self) -> float:
        """Score error handling approach (0-10)."""
        error_strategy = self.session_data.get('error_handling', 'unknown')
        validation = self.session_data.get('validation_approach', 'minimal')

        # Error handling strategy scores
        strategies = {
            'result': 9.0,
            'exceptions': 7.0,
            'codes': 6.0,
            'mixed': 7.5,
            'minimal': 3.0,
            'unknown': 2.0
        }

        score = strategies.get(error_strategy, 5.0)

        # Validation bonus: +1 for good validation
        if validation in ['fluent', 'annotations']:
            score = min(10.0, score + 1.0)

        return score

    def _score_documentation(self) -> float:
        """Score documentation planning (0-10)."""
        doc_paths = self.session_data.get('documentation_paths')
        doc_text = self.session_data.get('documentation_text')
        doc_urls = self.session_data.get('documentation_urls')
        standard_folders = self.session_data.get('standard_folders', [])

        score = 0.0

        # Has documentation input: +4
        if doc_paths or doc_text or doc_urls:
            score += 4.0

        # Includes docs/ folder: +3
        if 'docs' in standard_folders:
            score += 3.0

        # Multiple documentation sources: +3
        sources = sum([bool(doc_paths), bool(doc_text), bool(doc_urls)])
        if sources >= 2:
            score += 3.0
        elif sources == 1:
            score += 2.0

        return min(10.0, score)

    def _score_agents(self) -> float:
        """Score agent coverage (0-10)."""
        agents_dir = self.template_path / "agents"
        if not agents_dir.exists():
            return 3.0

        agent_count = len(list(agents_dir.glob("*.md")))

        # Score based on agent count
        if agent_count >= 6:
            return 10.0
        elif agent_count >= 4:
            return 8.0
        elif agent_count >= 2:
            return 6.0
        elif agent_count >= 1:
            return 4.0
        else:
            return 2.0

    def _score_tech_stack(self) -> float:
        """Score technology stack maturity (0-10)."""
        language = self.session_data.get('primary_language', 'unknown')
        framework = self.session_data.get('framework', 'unknown')

        # Mature stacks: Python, TypeScript, C#, Java
        mature_languages = {'python', 'typescript', 'csharp', 'java'}

        score = 5.0  # Base score

        if language.lower() in mature_languages:
            score += 3.0

        if framework not in ['unknown', '']:
            score += 2.0

        return min(10.0, score)

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= 9.5:
            return 'A+'
        elif score >= 9.0:
            return 'A'
        elif score >= 8.5:
            return 'A-'
        elif score >= 8.0:
            return 'B+'
        elif score >= 7.5:
            return 'B'
        elif score >= 7.0:
            return 'B-'
        elif score >= 6.5:
            return 'C+'
        elif score >= 6.0:
            return 'C'
        elif score >= 5.0:
            return 'D'
        else:
            return 'F'

    def generate_report(self, scores: dict) -> None:
        """Generate quality-report.md in template directory."""
        from datetime import datetime

        report = f"""# Template Quality Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Template**: {self.template_path.name}
**Overall Score**: {scores['overall_score']}/10 (Grade: {scores['grade']})
**Production Ready**: {'✅ Yes' if scores['production_ready'] else '❌ No'}

---

## Component Scores

| Component | Score | Status |
|-----------|-------|--------|
| Architecture Clarity | {scores['component_scores']['architecture_clarity']:.1f}/10 | {'✅' if scores['component_scores']['architecture_clarity'] >= 7 else '⚠️'} |
| Testing Coverage | {scores['component_scores']['testing_coverage']:.1f}/10 | {'✅' if scores['component_scores']['testing_coverage'] >= 7 else '⚠️'} |
| Error Handling | {scores['component_scores']['error_handling']:.1f}/10 | {'✅' if scores['component_scores']['error_handling'] >= 7 else '⚠️'} |
| Documentation | {scores['component_scores']['documentation']:.1f}/10 | {'✅' if scores['component_scores']['documentation'] >= 7 else '⚠️'} |
| Agent Coverage | {scores['component_scores']['agent_coverage']:.1f}/10 | {'✅' if scores['component_scores']['agent_coverage'] >= 7 else '⚠️'} |
| Tech Stack Maturity | {scores['component_scores']['tech_stack_maturity']:.1f}/10 | {'✅' if scores['component_scores']['tech_stack_maturity'] >= 7 else '⚠️'} |

---

## Analysis

### Architecture Clarity ({scores['component_scores']['architecture_clarity']:.1f}/10)
"""

        pattern = self.session_data.get('architecture_pattern', 'unknown')
        layer_org = self.session_data.get('layer_organization', 'single')

        report += f"- **Pattern**: {pattern}\n"
        report += f"- **Organization**: {layer_org}\n"

        if scores['component_scores']['architecture_clarity'] < 7:
            report += "\n**Recommendation**: Consider using well-known pattern (MVVM, Clean, Hexagonal)\n"

        report += f"\n### Testing Coverage ({scores['component_scores']['testing_coverage']:.1f}/10)\n"
        test_types = self.session_data.get('testing_scope', [])
        test_framework = self.session_data.get('unit_testing_framework', 'unknown')

        report += f"- **Test Types**: {', '.join(test_types) if test_types else 'None specified'}\n"
        report += f"- **Test Framework**: {test_framework}\n"

        if scores['component_scores']['testing_coverage'] < 7:
            report += "\n**Recommendation**: Add unit, integration, and e2e testing\n"

        report += f"\n### Error Handling ({scores['component_scores']['error_handling']:.1f}/10)\n"
        error_strategy = self.session_data.get('error_handling', 'unknown')
        validation = self.session_data.get('validation_approach', 'minimal')

        report += f"- **Strategy**: {error_strategy}\n"
        report += f"- **Validation**: {validation}\n"

        if scores['component_scores']['error_handling'] < 7:
            report += "\n**Recommendation**: Use Result/Either types for better error handling\n"

        report += f"\n### Documentation ({scores['component_scores']['documentation']:.1f}/10)\n"
        doc_sources = []
        if self.session_data.get('documentation_paths'):
            doc_sources.append('file paths')
        if self.session_data.get('documentation_text'):
            doc_sources.append('text input')
        if self.session_data.get('documentation_urls'):
            doc_sources.append('URLs')

        report += f"- **Sources**: {', '.join(doc_sources) if doc_sources else 'None provided'}\n"

        if scores['component_scores']['documentation'] < 7:
            report += "\n**Recommendation**: Provide architecture documentation and coding standards\n"

        report += f"\n### Agent Coverage ({scores['component_scores']['agent_coverage']:.1f}/10)\n"
        agents_dir = self.template_path / "agents"
        agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0

        report += f"- **Agent Count**: {agent_count}\n"

        if scores['component_scores']['agent_coverage'] < 7:
            report += "\n**Recommendation**: Add more specialized agents for better automation\n"

        report += f"\n### Tech Stack Maturity ({scores['component_scores']['tech_stack_maturity']:.1f}/10)\n"
        language = self.session_data.get('primary_language', 'unknown')
        framework = self.session_data.get('framework', 'unknown')

        report += f"- **Language**: {language}\n"
        report += f"- **Framework**: {framework}\n"

        report += "\n---\n\n## Recommendations\n\n"

        if scores['overall_score'] < 7:
            report += "⚠️ **Action Required**: Template quality below production threshold (7/10)\n\n"

        # Component-specific recommendations
        for component, score in scores['component_scores'].items():
            if score < 7:
                report += f"- **{component.replace('_', ' ').title()}**: Score {score:.1f}/10 - Needs improvement\n"

        if scores['production_ready']:
            report += "\n✅ **Template Ready**: Quality meets production standards\n"

        # Write report
        report_path = self.template_path / "quality-report.md"
        report_path.write_text(report)
        print(f"\n📄 Quality report saved: {report_path}")


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

    def __init__(self, no_create_agent_tasks: bool = False, output_location: str = 'global'):
        """
        Initialize Q&A session.

        Args:
            no_create_agent_tasks: Skip agent enhancement task creation (default: False)
            output_location: Where to save template ('global' or 'repo')
        """
        if not INQUIRER_AVAILABLE:
            raise ImportError(
                "inquirer library not installed. "
                "Install with: pip install inquirer"
            )

        self.answers: Optional[GreenfieldAnswers] = None
        self._session_data: dict = {}
        self.no_create_agent_tasks = no_create_agent_tasks
        self.output_location = output_location

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

    def _get_template_path(self, template_name: str) -> Path:
        """
        Get template save path based on output location.

        Port of template-create two-location support (TASK-068).

        Args:
            template_name: Name of template

        Returns:
            Path to save template

        Example:
            >>> session = TemplateInitQASession(output_location='repo')
            >>> path = session._get_template_path('my-template')
            >>> 'installer/global/templates' in str(path)
            True
        """
        if self.output_location == 'repo':
            # Repository location for team distribution
            base_path = Path.cwd() / 'installer' / 'global' / 'templates'
        else:
            # Personal location (default)
            base_path = Path.home() / '.agentecflow' / 'templates'

        return base_path / template_name

    def _display_location_guidance(self, template_path: Path) -> None:
        """
        Display location-specific usage guidance.

        Args:
            template_path: Where template was saved
        """
        print("\n" + "=" * 70)
        print("  Template Saved")
        print("=" * 70 + "\n")

        if self.output_location == 'repo':
            print(f"✅ Repository template: {template_path}")
            print()
            print("This template is now available for:")
            print("  • Team distribution (git commit)")
            print("  • Public sharing")
            print("  • Global discovery")
            print()
            print("Next steps:")
            print("  1. Review generated template")
            print("  2. Commit to repository: git add installer/global/templates/")
            print("  3. Share with team: git push")
            print()
            print("Usage:")
            print(f"  taskwright init {template_path.name}")
        else:
            print(f"✅ Personal template: {template_path}")
            print()
            print("This template is for:")
            print("  • Personal use")
            print("  • Local development")
            print("  • Experimentation")
            print()
            print("To share with team, create repository template:")
            print(f"  /template-init --output-location=repo")
            print()
            print("Usage:")
            print(f"  taskwright init {template_path.name}")

    def perform_quality_scoring(self, template_path: Path) -> dict:
        """
        Perform quality scoring on generated template.

        This method should be called after Phase 4 (Save Template) by the
        template-init command orchestrator.

        Args:
            template_path: Path to the generated template directory

        Returns:
            dict: Quality scores with overall score, component scores, and grade

        Example:
            >>> session = TemplateInitQASession()
            >>> # ... run Q&A session ...
            >>> template_path = Path("~/.agentecflow/templates/my-template")
            >>> scores = session.perform_quality_scoring(template_path)
            >>> print(f"Quality: {scores['overall_score']}/10")
        """
        if not self._session_data:
            print("⚠️ No session data available for quality scoring.")
            return {}

        print("\n" + "=" * 70)
        print("  Quality Assessment")
        print("=" * 70 + "\n")

        # Create scorer and calculate scores
        scorer = QualityScorer(self._session_data, template_path)
        quality_scores = scorer.calculate_score()
        scorer.generate_report(quality_scores)

        # Display summary
        print(f"📊 Quality Score: {quality_scores['overall_score']}/10 (Grade: {quality_scores['grade']})")
        print(f"   Production Ready: {'✅ Yes' if quality_scores['production_ready'] else '❌ No'}\n")

        # Component summary
        for component, score in quality_scores['component_scores'].items():
            status = '✅' if score >= 7 else '⚠️'
            print(f"   {status} {component.replace('_', ' ').title()}: {score:.1f}/10")

        print()

        return quality_scores

    def _create_agent_enhancement_tasks(
        self,
        template_name: str,
        agent_files: List[Path]
    ) -> List[str]:
        """
        Create enhancement tasks for generated agents.

        Port of template-create's Phase 8 task creation (TASK-UX-3A8D).

        Args:
            template_name: Name of the created template
            agent_files: List of generated agent file paths

        Returns:
            List of created task IDs

        Example:
            >>> agent_files = [Path('agents/test-agent.md')]
            >>> task_ids = session._create_agent_enhancement_tasks('my-template', agent_files)
            >>> len(task_ids)
            1
        """
        import uuid
        from datetime import datetime

        task_ids = []
        tasks_dir = Path("tasks/backlog")
        tasks_dir.mkdir(parents=True, exist_ok=True)

        for agent_file in agent_files:
            agent_name = agent_file.stem

            # Generate task ID (UUID-based for uniqueness)
            # Uses up to 15 chars of agent name + 8 chars of UUID
            prefix = agent_name[:15].upper()
            unique_id = uuid.uuid4().hex[:8].upper()
            task_id = f"TASK-{prefix}-{unique_id}"

            # Get primary language for technology-specific guidance
            primary_language = self._session_data.get('primary_language', 'technology')

            # Create task file content (markdown format)
            task_content = f"""---
id: {task_id}
title: "Enhance {agent_name} agent with boundary sections"
status: backlog
created: {datetime.now().isoformat()}Z
updated: {datetime.now().isoformat()}Z
priority: medium
tags: [agent-enhancement, {template_name}, template-init]
complexity: 3
estimated_hours: 1
metadata:
  agent_file: {str(agent_file)}
  template_name: {template_name}
  agent_name: {agent_name}
  created_by: template-init
  enhancement_type: boundary-sections
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Enhance {agent_name} Agent with Boundary Sections

## Description

Enhance the `{agent_name}` agent generated by `/template-init` to include comprehensive ALWAYS/NEVER/ASK boundary sections with technology-specific rules.

## Acceptance Criteria

- [ ] Agent includes 5-7 ALWAYS rules with ✅ prefix
- [ ] Agent includes 5-7 NEVER rules with ❌ prefix
- [ ] Agent includes 3-5 ASK scenarios with ⚠️ prefix
- [ ] All rules have brief rationales in parentheses
- [ ] Boundaries are {primary_language}-specific
- [ ] Rules are actionable and specific

## Enhancement Options

**Option A (Recommended - Fast)**:
```bash
/agent-enhance {template_name}/{agent_name} --hybrid
```
Duration: 2-5 minutes per agent

**Option B (Optional - Full Workflow)**:
```bash
/task-work {task_id}
```
Duration: 30-60 minutes with full quality gates

Both options use the same AI enhancement logic with boundary validation.

## Agent File Location

`{agent_file}`

## Template

Template: `{template_name}`
Created by: `/template-init` (greenfield)
"""

            # Save task file
            task_file = tasks_dir / f"{task_id}.md"
            task_file.write_text(task_content)
            task_ids.append(task_id)

        return task_ids

    def _display_enhancement_options(self, task_ids: List[str], template_name: str) -> None:
        """
        Display enhancement options to user.

        Port of template-create's enhancement guidance (TASK-DOC-1C5A).

        Args:
            task_ids: List of created task IDs
            template_name: Name of the template
        """
        print("\n" + "=" * 70)
        print("  Agent Enhancement Tasks Created")
        print("=" * 70 + "\n")

        print(f"📋 Created {len(task_ids)} enhancement task(s):")
        for task_id in task_ids[:5]:  # Show first 5
            print(f"   - {task_id}")
        if len(task_ids) > 5:
            print(f"   ... and {len(task_ids) - 5} more")

        print("\n" + "=" * 70)
        print("  Boundary Sections Information")
        print("=" * 70 + "\n")

        print("Enhanced agents will include:")
        print("  • ALWAYS (5-7 rules): Non-negotiable actions")
        print("  • NEVER (5-7 rules): Prohibited actions")
        print("  • ASK (3-5 scenarios): Escalation situations")
        print()
        print("Format: [emoji] [action] ([brief rationale])")
        print("  ✅ ALWAYS prefix (green checkmark)")
        print("  ❌ NEVER prefix (red X)")
        print("  ⚠️ ASK prefix (warning sign)")
        print()
        print("Example:")
        print("  ✅ Run build verification before tests (block if compilation fails)")
        print("  ❌ Never approve code with failing tests (zero tolerance policy)")
        print("  ⚠️ Coverage 70-79%: Ask if acceptable given task complexity")

        print("\n" + "=" * 70)
        print("  Enhancement Options")
        print("=" * 70 + "\n")

        print("Option A (Recommended - Fast):")
        print(f"  /agent-enhance {template_name}/<agent-name> --hybrid")
        print("  Duration: 2-5 minutes per agent")
        print("  Uses AI to generate technology-specific boundaries")
        print()
        print("Option B (Optional - Full Workflow):")
        print("  /task-work <task-id>")
        print("  Duration: 30-60 minutes per agent")
        print("  Full task workflow with quality gates")
        print()
        print("Both options use the same AI enhancement logic.")
        print("Choose based on how much time you have available.\n")

    def _generate_agent(self, agent_type: str, agent_name: str = "") -> str:
        """
        Generate agent markdown with boundary sections.

        This method will be called by Phase 3 agent generation orchestrator.
        It generates a complete agent definition including ALWAYS/NEVER/ASK boundaries.

        Args:
            agent_type: Type of agent (testing, repository, api, service, etc.)
            agent_name: Optional custom name for the agent

        Returns:
            str: Complete agent markdown content with boundaries

        Example:
            >>> session = TemplateInitQASession()
            >>> session._session_data = {'primary_language': 'python', 'framework': 'fastapi'}
            >>> agent_content = session._generate_agent('testing', 'testing-agent')
            >>> assert '## Boundaries' in agent_content
        """
        technology = self._session_data.get('primary_language', 'unknown')
        framework = self._session_data.get('framework', '')

        # Generate boundary sections
        boundaries = generate_boundary_sections(agent_type, technology)

        # Validate boundaries
        is_valid, errors = validate_boundary_sections(boundaries)
        if not is_valid:
            print(f"⚠️ Boundary validation warnings for {agent_type}:")
            for error in errors:
                print(f"   - {error}")

        # Format boundaries into markdown
        boundary_section = "\n## Boundaries\n\n"
        boundary_section += "### ALWAYS\n"
        for rule in boundaries["always"]:
            boundary_section += f"- {rule}\n"
        boundary_section += "\n### NEVER\n"
        for rule in boundaries["never"]:
            boundary_section += f"- {rule}\n"
        boundary_section += "\n### ASK\n"
        for scenario in boundaries["ask"]:
            boundary_section += f"- {scenario}\n"

        # Generate base agent content (placeholder - will be implemented by orchestrator)
        agent_content = self._generate_base_agent_content(agent_type, agent_name, technology, framework)

        # Insert boundary section after Quick Start (or at appropriate location)
        # Split agent content and insert boundaries
        if "## Quick Start" in agent_content:
            # Insert after Quick Start section
            parts = agent_content.split("## Quick Start", 1)
            if len(parts) == 2:
                # Find the end of Quick Start section (next ## heading or end)
                quick_start_part = parts[1]
                next_section_idx = quick_start_part.find("\n## ")
                if next_section_idx > 0:
                    agent_content = (
                        parts[0] + "## Quick Start" +
                        quick_start_part[:next_section_idx] +
                        boundary_section +
                        quick_start_part[next_section_idx:]
                    )
                else:
                    agent_content = parts[0] + "## Quick Start" + quick_start_part + boundary_section
        else:
            # No Quick Start section, add boundaries after metadata
            if "---" in agent_content:
                # Find end of frontmatter
                parts = agent_content.split("---", 2)
                if len(parts) >= 3:
                    agent_content = parts[0] + "---" + parts[1] + "---" + boundary_section + parts[2]
            else:
                # Just prepend to content
                agent_content = boundary_section + "\n" + agent_content

        return agent_content

    def _generate_base_agent_content(
        self,
        agent_type: str,
        agent_name: str,
        technology: str,
        framework: str
    ) -> str:
        """
        Generate base agent content without boundaries.

        This is a placeholder that will be enhanced by the full Phase 3 orchestrator.
        For now, it returns minimal agent structure.

        Args:
            agent_type: Type of agent
            agent_name: Name for the agent
            technology: Primary technology
            framework: Framework choice

        Returns:
            str: Base agent markdown content
        """
        # Placeholder implementation - will be replaced by full orchestrator
        name = agent_name or f"{agent_type}-agent"

        content = f"""---
name: {name}
type: {agent_type}
technology: {technology}
framework: {framework}
phase: implementation
---

# {name.title().replace('-', ' ')}

{technology.upper()}/{framework} {agent_type} specialist

## Quick Start

This agent specializes in {agent_type} for {technology} projects using {framework}.

## Capabilities

- Technology-specific {agent_type} implementation
- Best practices enforcement
- Quality assurance

## When to Use

Use this agent when working on {agent_type}-related tasks in your {technology}/{framework} project.
"""
        return content

    def ensure_validation_compatibility(self, template_path: Path) -> None:
        """
        Ensure template is compatible with /template-validate command.

        Adds required manifest fields and directory structure.

        Args:
            template_path: Path to generated template

        Example:
            >>> session = TemplateInitQASession()
            >>> session.ensure_validation_compatibility(Path('/tmp/template'))
            >>> (template_path / ".validation-compatible").exists()
            True
        """
        from datetime import datetime
        import json

        # Ensure required directories exist
        (template_path / "templates").mkdir(exist_ok=True)
        (template_path / "agents").mkdir(exist_ok=True)

        # Read existing manifest
        manifest_path = template_path / "template-manifest.json"
        if not manifest_path.exists():
            manifest_path = template_path / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
        else:
            manifest = {}

        # Add required validation fields if missing
        if 'schema_version' not in manifest:
            manifest['schema_version'] = '1.0.0'

        if 'complexity' not in manifest:
            # Estimate complexity from template structure
            num_agents = len(list((template_path / "agents").glob("*.md")))
            num_templates = len(list((template_path / "templates").glob("*"))) if (template_path / "templates").exists() else 0
            manifest['complexity'] = min(10, 3 + (num_agents // 2) + (num_templates // 3))

        if 'confidence_score' not in manifest:
            # Default confidence for greenfield (no codebase analysis)
            manifest['confidence_score'] = 75

        if 'created_at' not in manifest:
            manifest['created_at'] = datetime.now().isoformat()

        if 'validation_compatible' not in manifest:
            manifest['validation_compatible'] = True

        # Write updated manifest (prefer template-manifest.json for consistency)
        output_manifest_path = template_path / "template-manifest.json"
        output_manifest_path.write_text(json.dumps(manifest, indent=2))

        # Create compatibility marker
        marker_path = template_path / ".validation-compatible"
        marker_path.write_text(f"1.0.0\nCreated: {datetime.now().isoformat()}\n")

        print(f"✅ Template validation-compatible: {template_path.name}")

    def display_validation_guidance(self, template_path: Path) -> None:
        """
        Display /template-validate usage guidance.

        Args:
            template_path: Path to generated template
        """
        print("\n" + "=" * 70)
        print("  Comprehensive Validation Available")
        print("=" * 70 + "\n")

        print("Your template is now compatible with comprehensive audit:\n")
        print(f"  /template-validate {template_path}")
        print()
        print("Level 3 validation provides:")
        print("  • Interactive 16-section audit")
        print("  • Section-by-section analysis")
        print("  • AI-assisted recommendations")
        print("  • Comprehensive audit report")
        print("  • Duration: 30-60 minutes\n")
        print("Run when:")
        print("  • Deploying to production")
        print("  • Sharing with team")
        print("  • Critical quality requirements\n")


# Module exports
__all__ = [
    "GreenfieldAnswers",
    "TemplateInitQASession",
    "QualityScorer",
    "generate_boundary_sections",
    "validate_boundary_sections",
]
