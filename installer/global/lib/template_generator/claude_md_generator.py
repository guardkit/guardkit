"""
CLAUDE.md Generator

Generates comprehensive CLAUDE.md documentation from AI-provided architecture analysis.
Creates human-readable project instructions that guide Claude Code when working with
template-generated projects.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..codebase_analyzer.models import (
    CodebaseAnalysis,
    ArchitectureInfo,
    LayerInfo,
    ExampleFile,
)
from .models import TemplateClaude


class ClaudeMdGenerator:
    """Generate CLAUDE.md from CodebaseAnalysis

    Transforms AI-analyzed codebase structure into comprehensive documentation
    that guides Claude Code in maintaining project consistency and quality.
    """

    def __init__(self, analysis: CodebaseAnalysis):
        """Initialize generator with analysis results

        Args:
            analysis: CodebaseAnalysis from TASK-002
        """
        self.analysis = analysis

    def generate(self) -> TemplateClaude:
        """Generate complete CLAUDE.md content from analysis

        Returns:
            TemplateClaude with all sections populated
        """
        return TemplateClaude(
            schema_version="1.0.0",
            architecture_overview=self._generate_architecture_overview(),
            technology_stack=self._generate_technology_stack(),
            project_structure=self._generate_project_structure(),
            naming_conventions=self._generate_naming_conventions(),
            patterns=self._generate_patterns(),
            examples=self._generate_examples(),
            quality_standards=self._generate_quality_standards(),
            agent_usage=self._generate_agent_usage(),
            generated_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            confidence_score=self.analysis.overall_confidence.percentage / 100.0,
        )

    def _generate_architecture_overview(self) -> str:
        """Generate architecture overview section

        Returns:
            Markdown describing architecture patterns and layers
        """
        arch = self.analysis.architecture
        overview = [
            "# Architecture Overview",
            "",
            f"This template follows **{arch.architectural_style}** architecture.",
            "",
        ]

        # Add architecture-specific description
        if "MVVM" in arch.architectural_style or "Model-View-ViewModel" in arch.architectural_style:
            overview.extend([
                "## MVVM Pattern",
                "",
                "- **Model**: Business entities and data structures",
                "- **View**: UI components and visual elements (XAML)",
                "- **ViewModel**: Presentation logic and view state",
                "",
            ])
        elif "Clean Architecture" in arch.architectural_style or "Clean" == arch.architectural_style:
            overview.extend([
                "## Clean Architecture",
                "",
                "- **Domain**: Business rules and entities (core)",
                "- **Application**: Use cases and application logic",
                "- **Infrastructure**: External concerns (database, API, files)",
                "- **Presentation**: UI and user interaction",
                "",
            ])
        elif "MVC" in arch.architectural_style or "Model-View-Controller" in arch.architectural_style:
            overview.extend([
                "## MVC Pattern",
                "",
                "- **Model**: Data and business logic",
                "- **View**: User interface templates",
                "- **Controller**: Request handling and coordination",
                "",
            ])
        elif "Layered" in arch.architectural_style:
            overview.extend([
                "## Layered Architecture",
                "",
                "The application is organized in horizontal layers with clear separation of concerns.",
                "",
            ])

        # Add layer descriptions if available
        if arch.layers:
            overview.extend([
                "## Layers",
                ""
            ])

            for layer in arch.layers:
                overview.append(f"### {layer.name}")
                overview.append(layer.description)

                if layer.typical_files:
                    overview.append(f"**Example Files**: {', '.join(layer.typical_files[:3])}")

                if layer.dependencies:
                    overview.append(f"**Dependencies**: {', '.join(layer.dependencies)}")

                overview.append("")

        # Add dependency flow
        overview.extend([
            "## Dependency Flow",
            "",
            arch.dependency_flow,
            ""
        ])

        # Add key patterns
        if arch.patterns:
            overview.extend([
                "## Key Patterns",
                "",
                *[f"- {pattern}" for pattern in arch.patterns],
                ""
            ])

        return "\n".join(overview)

    def _generate_technology_stack(self) -> str:
        """Generate technology stack section

        Returns:
            Markdown describing technology stack and versions
        """
        tech = self.analysis.technology
        stack = [
            "# Technology Stack",
            "",
            f"- **Primary Language**: {tech.primary_language}"
        ]

        # Add frameworks
        if tech.frameworks:
            stack.append("- **Frameworks**:")
            for fw in tech.frameworks:
                stack.append(f"  - {fw}")

        # Add testing frameworks
        if tech.testing_frameworks:
            stack.extend([
                "- **Testing**:",
                *[f"  - {fw}" for fw in tech.testing_frameworks]
            ])

        # Add build tools
        if tech.build_tools:
            stack.extend([
                "- **Build Tools**:",
                *[f"  - {tool}" for tool in tech.build_tools]
            ])

        # Add databases
        if tech.databases:
            stack.extend([
                "- **Databases**:",
                *[f"  - {db}" for db in tech.databases]
            ])

        # Add infrastructure
        if tech.infrastructure:
            stack.extend([
                "- **Infrastructure**:",
                *[f"  - {infra}" for infra in tech.infrastructure]
            ])

        stack.append("")
        return "\n".join(stack)

    def _generate_project_structure(self) -> str:
        """Generate project structure section

        Returns:
            Markdown describing folder structure with explanations
        """
        structure = [
            "# Project Structure",
            "",
            "```"
        ]

        # Generate directory tree from layers
        if self.analysis.architecture.layers:
            # Sort layers by typical hierarchy
            sorted_layers = self._sort_layers_hierarchically(self.analysis.architecture.layers)

            for layer in sorted_layers:
                # Use layer name as directory indicator
                indent = "  " * self._get_layer_depth(layer.name)
                structure.append(f"{indent}{layer.name}/  # {layer.description}")

                # Add example files if available
                if layer.typical_files:
                    for file_pattern in layer.typical_files[:2]:  # Max 2 examples
                        structure.append(f"{indent}  └── {file_pattern}")

        structure.extend([
            "```",
            ""
        ])

        # Add explanations for key directories
        if self.analysis.architecture.layers:
            structure.append("## Directory Descriptions")
            structure.append("")

            for layer in self.analysis.architecture.layers:
                structure.append(f"### `{layer.name}`")
                structure.append(layer.description)

                if layer.dependencies:
                    structure.append(f"**Dependencies**: {', '.join(layer.dependencies)}")

                structure.append("")

        return "\n".join(structure)

    def _sort_layers_hierarchically(self, layers: List[LayerInfo]) -> List[LayerInfo]:
        """Sort layers in typical hierarchical order

        Args:
            layers: List of LayerInfo objects

        Returns:
            Sorted list with typical ordering (Domain first, Infrastructure last, etc.)
        """
        # Define typical layer ordering
        order_map = {
            "Domain": 0,
            "Core": 0,
            "Application": 1,
            "Services": 2,
            "API": 3,
            "Presentation": 3,
            "UI": 3,
            "Web": 3,
            "Infrastructure": 4,
            "Data": 4,
        }

        def get_order(layer: LayerInfo) -> int:
            return order_map.get(layer.name, 5)

        return sorted(layers, key=get_order)

    def _get_layer_depth(self, layer_name: str) -> int:
        """Get indentation depth for layer visualization

        Args:
            layer_name: Name of the layer

        Returns:
            Indentation level (0-2)
        """
        # Core/Domain layers at root level
        if layer_name in ["Domain", "Core"]:
            return 0
        # Application/Services at level 1
        elif layer_name in ["Application", "Services"]:
            return 0
        # Everything else at level 0 (flat structure)
        else:
            return 0

    def _generate_naming_conventions(self) -> str:
        """Generate naming conventions section

        Returns:
            Markdown describing naming rules with examples
        """
        conventions = [
            "# Naming Conventions",
            ""
        ]

        # Check if we have example files to extract patterns from
        example_files = self.analysis.example_files

        if not example_files:
            conventions.append("Follow language-standard naming conventions.")
            conventions.append("")
            return "\n".join(conventions)

        # Group examples by layer/purpose
        by_purpose = self._group_examples_by_purpose(example_files)

        for purpose, files in by_purpose.items():
            title = purpose.replace("_", " ").title()
            conventions.append(f"## {title}")

            # Extract naming pattern from examples
            pattern = self._infer_naming_pattern(files)
            if pattern:
                conventions.append(f"**Pattern**: `{pattern}`")

            # Add examples
            conventions.append("**Examples**:")
            for file in files[:3]:  # Max 3 examples
                file_name = Path(file.path).name
                conventions.append(f"- `{file_name}`")

            conventions.append("")

        return "\n".join(conventions)

    def _group_examples_by_purpose(self, examples: List[ExampleFile]) -> dict:
        """Group example files by purpose/type

        Args:
            examples: List of example files

        Returns:
            Dictionary mapping purpose to list of files
        """
        grouped = {}
        for example in examples:
            purpose = example.purpose if example.purpose else "Other"
            # Simplify purpose to category
            if "domain" in purpose.lower() or "operation" in purpose.lower():
                category = "Domain Operations"
            elif "view" in purpose.lower() or "page" in purpose.lower():
                category = "Views"
            elif "viewmodel" in purpose.lower():
                category = "ViewModels"
            elif "test" in purpose.lower():
                category = "Tests"
            elif "model" in purpose.lower() or "entity" in purpose.lower():
                category = "Models"
            else:
                category = "Other"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(example)

        return grouped

    def _infer_naming_pattern(self, files: List[ExampleFile]) -> Optional[str]:
        """Infer naming pattern from example files

        Args:
            files: List of example files with similar purpose

        Returns:
            Inferred pattern or None
        """
        if not files:
            return None

        # Get file names
        names = [Path(f.path).stem for f in files]

        # Look for common patterns
        if len(names) >= 2:
            # Check for verb-entity pattern (e.g., GetProducts, CreateOrder)
            if all(self._has_verb_entity_pattern(name) for name in names):
                return "{{Verb}}{{Entity}}"

            # Check for entity-suffix pattern (e.g., ProductPage, OrderPage)
            common_suffix = self._find_common_suffix(names)
            if common_suffix:
                return f"{{{{Entity}}}}{common_suffix}"

            # Check for prefix-entity pattern
            common_prefix = self._find_common_prefix(names)
            if common_prefix:
                return f"{common_prefix}{{{{Entity}}}}"

        # Default: just use the first name as example
        return names[0] if names else None

    def _has_verb_entity_pattern(self, name: str) -> bool:
        """Check if name follows verb-entity pattern

        Args:
            name: File name (without extension)

        Returns:
            True if name appears to follow verb-entity pattern
        """
        common_verbs = ["Get", "Create", "Update", "Delete", "List", "Find", "Search", "Add", "Remove", "Set"]
        return any(name.startswith(verb) for verb in common_verbs)

    def _find_common_suffix(self, names: List[str]) -> Optional[str]:
        """Find common suffix in names

        Args:
            names: List of names

        Returns:
            Common suffix or None
        """
        if len(names) < 2:
            return None

        common_suffixes = ["Page", "View", "ViewModel", "Model", "Service", "Repository", "Controller", "Test"]
        for suffix in common_suffixes:
            if all(name.endswith(suffix) for name in names):
                return suffix

        return None

    def _find_common_prefix(self, names: List[str]) -> Optional[str]:
        """Find common prefix in names

        Args:
            names: List of names

        Returns:
            Common prefix or None
        """
        if len(names) < 2:
            return None

        # Find longest common prefix
        prefix = names[0]
        for name in names[1:]:
            while not name.startswith(prefix) and prefix:
                prefix = prefix[:-1]

        # Only return if prefix is meaningful (3+ characters)
        return prefix if len(prefix) >= 3 else None

    def _generate_patterns(self) -> str:
        """Generate patterns and best practices section

        Returns:
            Markdown describing patterns and best practices
        """
        patterns = [
            "# Patterns and Best Practices",
            ""
        ]

        # Architecture-specific patterns
        arch_patterns = self.analysis.architecture.patterns
        if arch_patterns:
            patterns.append("## Architectural Patterns")
            patterns.append("")
            for pattern in arch_patterns:
                patterns.append(f"- **{pattern}**")
            patterns.append("")

        # Quality-based patterns
        good_patterns = self.analysis.quality.strengths
        if good_patterns:
            patterns.append("## Recommended Practices")
            patterns.append("")
            for pattern in good_patterns:
                patterns.append(f"- {pattern}")
            patterns.append("")

        # Language-specific best practices
        patterns.extend(self._generate_language_best_practices())

        return "\n".join(patterns)

    def _generate_language_best_practices(self) -> List[str]:
        """Generate language-specific best practices

        Returns:
            List of markdown lines
        """
        lang = self.analysis.technology.primary_language.lower()
        practices = ["## Language-Specific Best Practices", ""]

        if lang in ["csharp", "c#"]:
            practices.extend([
                "- Use nullable reference types",
                "- Prefer records for immutable data",
                "- Use expression-bodied members when appropriate",
                "- Follow async/await patterns consistently",
                "- Apply SOLID principles",
                ""
            ])
        elif lang in ["typescript", "javascript"]:
            practices.extend([
                "- Use strict TypeScript mode",
                "- Prefer const over let",
                "- Use async/await over callbacks",
                "- Leverage type inference where appropriate",
                "- Follow functional programming patterns",
                ""
            ])
        elif lang == "python":
            practices.extend([
                "- Follow PEP 8 style guide",
                "- Use type hints for all functions",
                "- Prefer dataclasses for data structures",
                "- Use context managers for resources",
                "- Apply SOLID principles",
                ""
            ])
        elif lang in ["java", "kotlin"]:
            practices.extend([
                "- Use immutable objects when possible",
                "- Leverage Optional for nullable values",
                "- Follow functional programming patterns",
                "- Use try-with-resources for resource management",
                "- Apply SOLID principles",
                ""
            ])
        else:
            practices.extend([
                "- Follow language-standard conventions",
                "- Write self-documenting code",
                "- Keep functions small and focused",
                "- Apply SOLID principles",
                ""
            ])

        return practices

    def _generate_examples(self) -> str:
        """Generate code examples section

        Returns:
            Markdown with code examples demonstrating patterns
        """
        examples = [
            "# Code Examples",
            ""
        ]

        # Use example files from analysis
        if not self.analysis.example_files:
            examples.append("Code examples are available in the template files.")
            examples.append("")
            return "\n".join(examples)

        # Group by layer
        by_layer = {}
        for example_file in self.analysis.example_files:
            layer = example_file.layer if example_file.layer else "General"
            if layer not in by_layer:
                by_layer[layer] = []
            by_layer[layer].append(example_file)

        # Generate examples for each layer
        for layer, files in by_layer.items():
            examples.append(f"## {layer} Examples")
            examples.append("")

            # Use best example (highest quality score)
            best_file = max(files, key=lambda f: sum(1 for _ in f.key_concepts) * 10 + len(f.patterns_used))

            examples.append(f"**File**: `{best_file.path}`")
            examples.append(f"**Purpose**: {best_file.purpose}")

            if best_file.patterns_used:
                examples.append(f"**Patterns**: {', '.join(best_file.patterns_used)}")

            if best_file.key_concepts:
                examples.append("**Key Concepts**:")
                for concept in best_file.key_concepts:
                    examples.append(f"- {concept}")

            examples.append("")
            examples.append("See template files for complete implementation examples.")
            examples.append("")

        return "\n".join(examples)

    def _generate_quality_standards(self) -> str:
        """Generate quality standards section

        Returns:
            Markdown with quality guidelines and testing requirements
        """
        standards = [
            "# Quality Standards",
            ""
        ]

        # Testing requirements
        standards.extend([
            "## Testing",
            "",
            "- **Unit Test Coverage**: ≥80%",
            "- **Branch Coverage**: ≥75%",
        ])

        # Add testing framework info
        if self.analysis.technology.testing_frameworks:
            test_fw = self.analysis.technology.testing_frameworks[0]
            standards.append(f"- **Test Framework**: {test_fw}")

        standards.extend([
            "- Test all business logic",
            "- Test error cases and edge cases",
            "- Use descriptive test names",
            ""
        ])

        # Code quality metrics from analysis
        quality = self.analysis.quality
        standards.extend([
            "## Code Quality",
            "",
            f"- **SOLID Compliance**: {quality.solid_compliance:.0f}/100",
            f"- **DRY Compliance**: {quality.dry_compliance:.0f}/100",
            f"- **YAGNI Compliance**: {quality.yagni_compliance:.0f}/100",
            "- Write self-documenting code",
            "- Keep methods small and focused",
            "- Use meaningful names",
            ""
        ])

        # Add improvements if suggested
        if quality.improvements:
            standards.extend([
                "## Areas for Improvement",
                "",
                *[f"- {improvement}" for improvement in quality.improvements],
                ""
            ])

        # Language-specific standards
        standards.extend(self._generate_language_quality_standards())

        return "\n".join(standards)

    def _generate_language_quality_standards(self) -> List[str]:
        """Generate language-specific quality standards

        Returns:
            List of markdown lines
        """
        lang = self.analysis.technology.primary_language.lower()
        standards = []

        if lang in ["csharp", "c#"]:
            standards.extend([
                "## C# Specific",
                "",
                "- Enable nullable reference types",
                "- No compiler warnings allowed",
                "- Follow Microsoft naming conventions",
                "- Use code analysis (analyzers)",
                ""
            ])
        elif lang in ["typescript", "javascript"]:
            standards.extend([
                "## TypeScript Specific",
                "",
                "- Strict mode enabled",
                "- No `any` types (use `unknown` if needed)",
                "- ESLint passing with zero warnings",
                "- Prettier formatting",
                ""
            ])
        elif lang == "python":
            standards.extend([
                "## Python Specific",
                "",
                "- Type hints on all public functions",
                "- Black formatting",
                "- Pylint score ≥8.0",
                "- No star imports",
                ""
            ])

        return standards

    def _generate_agent_usage(self) -> str:
        """Generate agent usage section

        Returns:
            Markdown describing which agents to use when
        """
        usage = [
            "# Agent Usage",
            "",
            "This template includes specialized agents for common tasks:",
            ""
        ]

        # Use suggested agents from analysis if available
        # Note: This would typically come from TASK-004A (AI Agent Generator)
        # For now, we'll generate generic guidance based on architecture

        usage.extend([
            "## When to Use Agents",
            "",
            "- Use **domain-specific agents** for business logic",
            "- Use **testing agents** for test generation",
            "- Use **UI agents** for view/component creation",
            "- Use **architectural agents** for design review",
            ""
        ])

        return "\n".join(usage)

    def to_markdown(self, claude: TemplateClaude) -> str:
        """Convert TemplateClaude to full CLAUDE.md content

        Args:
            claude: TemplateClaude instance

        Returns:
            Complete CLAUDE.md file content
        """
        return claude.to_markdown()

    def save(self, claude: TemplateClaude, output_path: Path) -> None:
        """Save CLAUDE.md to file

        Args:
            claude: TemplateClaude instance
            output_path: Path where to save the file
        """
        content = self.to_markdown(claude)
        output_path.write_text(content, encoding='utf-8')
