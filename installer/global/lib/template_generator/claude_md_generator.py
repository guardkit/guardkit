"""
CLAUDE.md Generator

Generates comprehensive CLAUDE.md documentation from AI-provided architecture analysis.
Creates human-readable project instructions that guide Claude Code when working with
template-generated projects.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
import frontmatter
import json
import yaml

from ..codebase_analyzer.models import (
    CodebaseAnalysis,
    ArchitectureInfo,
    LayerInfo,
    ExampleFile,
)
from .models import TemplateClaude, AgentMetadata, TemplateSplitOutput
from .ai_client import AIClient


class ClaudeMdGenerator:
    """Generate CLAUDE.md from CodebaseAnalysis

    Transforms AI-analyzed codebase structure into comprehensive documentation
    that guides Claude Code in maintaining project consistency and quality.
    """

    def __init__(self, analysis: CodebaseAnalysis, agents: Optional[List] = None, output_path: Optional[Path] = None):
        """Initialize generator with analysis results

        Args:
            analysis: CodebaseAnalysis from TASK-002
            agents: Optional list of GeneratedAgent objects (from Phase 7)
                   If provided, will scan and document actual agents
                   If None, generates generic agent guidance (backward compatible)
            output_path: Optional path to template output directory
                        Used to find agent files for enhanced documentation
        """
        self.analysis = analysis
        self.agents = agents
        self.output_path = output_path
        self.ai_client = AIClient()

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

    def _generate_architecture_overview(self, summary_only: bool = False) -> str:
        """Generate architecture overview section

        Args:
            summary_only: If True, generate compact summary for core content

        Returns:
            Markdown describing architecture patterns and layers
        """
        arch = self.analysis.architecture

        if summary_only:
            # Compact version for core (target: ~500 bytes)
            return f"# Architecture Overview\n\nThis template follows **{arch.architectural_style}** architecture.\n\n**For detailed architecture**: See `docs/patterns/README.md`"

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

    def _generate_technology_stack_summary(self) -> str:
        """Generate compact technology stack for core content

        Returns:
            Markdown with abbreviated technology stack
        """
        tech = self.analysis.technology
        stack = [
            "# Technology Stack",
            "",
            f"- **Primary Language**: {tech.primary_language}"
        ]

        # Show max 3 frameworks
        if tech.frameworks:
            fw_names = [str(fw)[:30] for fw in tech.frameworks[:3]]
            if len(tech.frameworks) > 3:
                fw_names.append(f"... and {len(tech.frameworks) - 3} more")
            stack.append(f"- **Frameworks**: {', '.join(fw_names)}")

        stack.append("")
        stack.append("**For complete stack details**: See `docs/reference/README.md`")

        return "\n".join(stack)

    def _generate_project_structure(self, max_depth: int = None) -> str:
        """Generate project structure section

        Args:
            max_depth: Maximum directory depth (None = full tree)

        Returns:
            Markdown describing folder structure with explanations
        """
        structure = [
            "# Project Structure",
            "",
            "```"
        ]

        # TASK-FIX-PD03: Use actual directory tree if available
        if self.analysis.project_structure:
            # Use real directory tree from file discovery
            structure_text = self.analysis.project_structure

            # Apply truncation if max_depth specified
            if max_depth:
                lines = structure_text.split('\n')
                truncated = []
                for line in lines:
                    # Calculate depth based on leading spaces
                    depth = len(line) - len(line.lstrip())
                    if depth <= (max_depth * 2):  # 2 spaces per level
                        truncated.append(line)
                structure_text = '\n'.join(truncated)
                # Add truncation notice
                if len(truncated) < len(lines):
                    structure_text += f"\n... ({len(lines) - len(truncated)} more directories)\n\n**For full project structure**: See `docs/reference/README.md`"

            structure.append(structure_text)
        elif self.analysis.architecture.layers:
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

        # Add explanations for key directories (only when using layer-based structure)
        # TASK-FIX-PD03: Skip directory descriptions if using actual project_structure
        if not self.analysis.project_structure and self.analysis.architecture.layers:
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

        # Add template validation checklist
        standards.extend(self._generate_validation_checklist())

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

    def _generate_validation_checklist(self) -> List[str]:
        """Generate template validation checklist

        Returns:
            List of markdown lines for validation checklist
        """
        checklist = [
            "## Template Validation Checklist",
            "",
            "Before using this template, verify:",
            "",
            "### CRUD Completeness",
            "- [ ] Create operation (endpoint + handler + validator)",
            "- [ ] Read operation (GetById + List + handlers)",
            "- [ ] Update operation (endpoint + handler + validator)",
            "- [ ] Delete operation (endpoint + handler + validator)",
            "",
            "### Layer Symmetry",
            "- [ ] All UseCases commands have Web endpoints",
            "- [ ] All Web endpoints have UseCases handlers",
            "- [ ] Repository interfaces exist for all operations",
            "",
        ]

        # Add REPR Pattern section if applicable (FastEndpoints/Web API pattern)
        arch_style = self.analysis.architecture.architectural_style.lower()
        if any(term in arch_style for term in ['web', 'api', 'fastendpoints']):
            checklist.extend([
                "### REPR Pattern (if using FastEndpoints)",
                "- [ ] Each endpoint has Request/Response/Validator",
                "- [ ] Validators use FluentValidation",
                "- [ ] Routes follow RESTful conventions",
                "",
            ])

        checklist.extend([
            "### Pattern Consistency",
            "- [ ] All entities follow same operation structure",
            "- [ ] Naming conventions consistent",
            "- [ ] Placeholders consistently applied",
            "",
            "See documentation for detailed validation checklist.",
            ""
        ])

        return checklist

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

        # If agents were provided (Phase 7 executed first), document them
        if self.agents:
            return self._generate_dynamic_agent_usage()

        # Fallback: Generate generic guidance (backward compatible)
        usage.extend([
            "## When to Use Agents",
            "",
            "- Use **domain-specific agents** for business logic",
            "- Use **testing agents** for test generation",
            "- Use **UI agents** for view/component creation",
            "- Use **architectural agents** for design review",
            "",
            "## Agent Response Format",
            "",
            "When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:",
            "",
            "**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)",
            "",
            "**Key Requirements**:",
            "- Field name: `response` (NOT `result`)",
            "- Data type: JSON-encoded string (NOT object)",
            "- All 9 required fields must be present",
            "",
            "See the specification for complete schema and examples.",
            ""
        ])

        return "\n".join(usage)

    def _generate_dynamic_agent_usage(self) -> str:
        """Generate agent usage section based on actual agents

        Returns:
            Markdown describing actual agents generated for this template
        """
        usage = [
            "# Agent Usage",
            "",
            "This template includes specialized agents tailored to this project's patterns:",
            ""
        ]

        # Get agent files from output path
        agent_metadata_list = []

        if self.output_path:
            # Read from template output directory
            agent_dir = self.output_path / "agents"
            if agent_dir.exists():
                for agent_file in sorted(agent_dir.glob("*.md")):
                    # Read metadata from file
                    metadata_dict = self._read_agent_metadata_from_file(agent_file)
                    if metadata_dict:
                        # Enhance with AI
                        enhanced = self._enhance_agent_info_with_ai(metadata_dict)

                        # Infer category
                        category = self._infer_category(
                            metadata_dict['name'],
                            metadata_dict.get('tags', [])
                        )

                        # Create AgentMetadata object
                        agent_metadata = AgentMetadata(
                            name=metadata_dict['name'],
                            purpose=enhanced['purpose'],
                            capabilities=[],  # Not extracted from file for now
                            when_to_use=enhanced['when_to_use'],
                            category=category
                        )

                        agent_metadata_list.append(agent_metadata)

        # Fallback to old method if agents were provided
        elif self.agents:
            for agent in self.agents:
                metadata = self._extract_agent_metadata(agent)
                if metadata:
                    agent_metadata_list.append(metadata)

        # If no agents found, return generic guidance
        if not agent_metadata_list:
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

        # Group agents by category
        by_category = {}
        for metadata in agent_metadata_list:
            category = metadata.category.title()
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(metadata)

        # Generate documentation by category
        for category, agents in sorted(by_category.items()):
            usage.append(f"## {category} Agents")
            usage.append("")

            for agent in agents:
                usage.append(f"### {agent.name}")
                usage.append(f"**Purpose**: {agent.purpose}")
                usage.append("")

                if agent.capabilities:
                    usage.append("**Capabilities**:")
                    for capability in agent.capabilities[:5]:  # Max 5
                        usage.append(f"- {capability}")
                    usage.append("")

                usage.append(f"**When to Use**: {agent.when_to_use}")
                usage.append("")

        # Add general guidance
        usage.extend([
            "## General Guidance",
            "",
            "- Use agents when implementing features that match their expertise",
            "- Agents understand this project's specific patterns and conventions",
            "- For tasks outside agent specializations, rely on general Claude capabilities",
            "",
            "## Agent Response Format",
            "",
            "When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:",
            "",
            "**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)",
            "",
            "**Key Requirements**:",
            "- Field name: `response` (NOT `result`)",
            "- Data type: JSON-encoded string (NOT object)",
            "- All 9 required fields must be present",
            "",
            "See the specification for complete schema and examples.",
            ""
        ])

        return "\n".join(usage)

    def _read_agent_metadata_from_file(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Read agent frontmatter and extract metadata from file

        Args:
            agent_file: Path to agent .md file

        Returns:
            Dictionary with agent metadata or None if extraction fails
        """
        try:
            content = agent_file.read_text(encoding='utf-8')

            # Extract frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter_data = yaml.safe_load(parts[1])
                    return {
                        'name': frontmatter_data.get('name', agent_file.stem),
                        'description': frontmatter_data.get('description', ''),
                        'technologies': frontmatter_data.get('technologies', []),
                        'tools': frontmatter_data.get('tools', []),
                        'priority': frontmatter_data.get('priority', 5),
                    }

            return None

        except Exception:
            return None

    def _categorize_agent_by_keywords(self, agent_metadata: Dict[str, Any]) -> str:
        """Categorize agent based on technologies and description keywords.

        Uses priority order: database > testing > api > domain > ui > general
        to prevent false matches from generic keywords like 'view'.

        Args:
            agent_metadata: Dict with 'name', 'description', 'technologies' keys

        Returns:
            Category string: 'database', 'api', 'ui', 'domain', 'testing', or 'general'
        """
        # Check technologies first (most reliable)
        technologies_lower = [t.lower() for t in agent_metadata.get('technologies', [])]

        # Database technologies
        database_techs = {
            'firestore', 'firebase', 'realm', 'mongodb', 'postgresql', 'mysql',
            'sqlite', 'supabase', 'dynamodb', 'redis', 'database'
        }
        if any(any(tech in t for tech in database_techs) for t in technologies_lower):
            return 'database'

        # Testing technologies
        testing_techs = {'pytest', 'jest', 'mocha', 'xunit', 'nunit', 'vitest', 'testing'}
        if any(any(tech in t for tech in testing_techs) for t in technologies_lower):
            return 'testing'

        # API technologies
        api_techs = {'fastapi', 'express', 'flask', 'django', 'asp.net', 'spring', 'rest', 'api'}
        if any(any(tech in t for tech in api_techs) for t in technologies_lower):
            return 'api'

        # UI technologies
        ui_techs = {'react', 'vue', 'angular', 'svelte', 'xaml', 'swiftui'}
        if any(any(tech in t for tech in ui_techs) for t in technologies_lower):
            return 'ui'

        # Fallback to description keyword matching
        desc_lower = agent_metadata.get('description', '').lower()

        # Database keywords (highest priority)
        database_keywords = {
            'database', 'firestore', 'firebase', 'realm', 'mongodb', 'postgresql',
            'mysql', 'crud', 'persistence', 'query', 'collection', 'document',
            'repository', 'data access', 'orm', 'migration', 'sql'
        }
        if any(keyword in desc_lower for keyword in database_keywords):
            return 'database'

        # Testing keywords
        testing_keywords = {'test', 'testing', 'coverage', 'assertion', 'mock', 'fixture', 'spec'}
        if any(keyword in desc_lower for keyword in testing_keywords):
            return 'testing'

        # API keywords
        api_keywords = {'api', 'endpoint', 'route', 'request', 'response', 'rest', 'graphql', 'controller'}
        if any(keyword in desc_lower for keyword in api_keywords):
            return 'api'

        # Domain keywords
        domain_keywords = {'domain', 'business logic', 'business', 'operation', 'service', 'usecase'}
        if any(keyword in desc_lower for keyword in domain_keywords):
            return 'domain'

        # UI keywords (lowest priority - removed 'view' to prevent false matches)
        ui_keywords = {'ui', 'component', 'screen', 'page', 'xaml', 'jsx', 'interface', 'frontend'}
        if any(keyword in desc_lower for keyword in ui_keywords):
            return 'ui'

        return 'general'

    def _enhance_agent_info_with_ai(self, agent_metadata: Dict[str, Any]) -> Dict[str, str]:
        """Use AI to generate enhanced agent documentation

        Args:
            agent_metadata: Basic metadata from agent file

        Returns:
            Dictionary with 'purpose' and 'when_to_use' keys
        """
        try:
            # Build technology list
            technologies = agent_metadata.get('technologies', [])
            if isinstance(technologies, list):
                tech_str = ', '.join(technologies) if technologies else 'general development'
            else:
                tech_str = str(technologies)

            # Build tools list
            tools = agent_metadata.get('tools', [])
            if isinstance(tools, str):
                tools_str = tools
            else:
                tools_str = ', '.join(tools) if tools else 'standard development tools'

            prompt = f"""Generate documentation for a specialized AI agent:

Agent Name: {agent_metadata['name']}
Description: {agent_metadata['description']}
Technologies: {tech_str}
Tools Available: {tools_str}

Generate:
1. **Purpose**: A concise 1-sentence summary (use the description as base)
2. **When to Use**: 2-3 specific scenarios when developers should use this agent

Format your response as JSON:
{{
    "purpose": "...",
    "when_to_use": "Use this agent when: (1) scenario one, (2) scenario two, (3) scenario three"
}}

Make "When to Use" specific and actionable. Focus on concrete development tasks.

Examples of good "When to Use":
- "Use this agent when implementing data access layers, creating repository interfaces, working with database migrations, or building offline-first persistence"
- "Use this agent when creating ViewModels, implementing data binding, handling property change notifications, or building MVVM-based UI components"

Respond ONLY with valid JSON."""

            # Try to use AI client
            try:
                response = self.ai_client.generate(
                    prompt=prompt,
                    max_tokens=500
                )

                # Parse JSON response
                result = json.loads(response)
                return result

            except (NotImplementedError, Exception):
                # Fallback: Generate basic guidance without AI
                purpose = agent_metadata['description']

                # Use categorization to generate appropriate guidance (TASK-FIX-PD05)
                category = self._categorize_agent_by_keywords(agent_metadata)

                when_to_use_templates = {
                    'database': "Use this agent when implementing database operations, data persistence layers, query optimization, or repository patterns",
                    'testing': "Use this agent when writing tests, validating test coverage, setting up testing infrastructure, or creating test fixtures",
                    'api': "Use this agent when creating API endpoints, implementing request handlers, defining web routes, or building REST/GraphQL services",
                    'domain': "Use this agent when implementing business logic, creating domain operations, defining core functionality, or building service layers",
                    'ui': "Use this agent when creating UI components, implementing user interfaces, building screens, or handling presentation logic",
                    'general': f"Use this agent when working with {agent_metadata['name'].replace('-', ' ')}"
                }

                when_to_use = when_to_use_templates.get(category, when_to_use_templates['general'])

                return {
                    'purpose': purpose,
                    'when_to_use': when_to_use
                }

        except Exception:
            # Ultimate fallback
            return {
                'purpose': agent_metadata.get('description', 'Specialized development agent'),
                'when_to_use': f"Use this agent for tasks related to {agent_metadata.get('name', 'development')}"
            }

    def _extract_agent_metadata(self, agent) -> Optional[AgentMetadata]:
        """Extract metadata from a GeneratedAgent and enhance with AI

        Args:
            agent: GeneratedAgent object with full_definition
                   May also be a deserialized object from checkpoint resume

        Returns:
            AgentMetadata or None if extraction fails
        """
        try:
            # TASK-FIX-RESUME: Use getattr for safety with deserialized agents
            agent_name = getattr(agent, 'name', None)
            full_definition = getattr(agent, 'full_definition', None)

            # Skip agents without required attributes
            if not agent_name:
                return None

            # If no full_definition, create minimal metadata from available attributes
            if not full_definition or not isinstance(full_definition, str):
                agent_description = getattr(agent, 'description', f'Agent for {agent_name}')
                agent_tags = getattr(agent, 'tags', [])
                agent_priority = getattr(agent, 'priority', 5)

                # Build minimal metadata
                agent_metadata_dict = {
                    'name': agent_name,
                    'description': agent_description,
                    'technologies': agent_tags if isinstance(agent_tags, list) else [],
                    'tools': getattr(agent, 'tools', []),
                    'priority': agent_priority
                }

                # Use AI to generate "when to use" guidance
                enhanced = self._enhance_agent_info_with_ai(agent_metadata_dict)

                # Infer category from name and tags
                category = self._infer_category(agent_name, agent_tags if isinstance(agent_tags, list) else [])

                return AgentMetadata(
                    name=agent_name,
                    purpose=enhanced['purpose'],
                    capabilities=[],
                    when_to_use=enhanced['when_to_use'],
                    category=category
                )

            # Parse frontmatter from agent markdown
            post = frontmatter.loads(full_definition)
            metadata = post.metadata

            # Extract first paragraph from content as purpose
            content_lines = post.content.strip().split('\n')
            purpose = metadata.get('description', '')

            # Extract capabilities from content (look for bullet lists)
            capabilities = []
            in_capabilities = False
            for line in content_lines:
                if '## Capabilities' in line or '## Patterns' in line:
                    in_capabilities = True
                    continue
                elif line.startswith('##'):
                    in_capabilities = False
                elif in_capabilities and line.strip().startswith('-'):
                    capabilities.append(line.strip()[2:].strip())

            # Build agent metadata dict for AI enhancement
            agent_metadata_dict = {
                'name': agent_name,
                'description': purpose,
                'technologies': metadata.get('technologies', metadata.get('tags', [])),
                'tools': metadata.get('tools', []),
                'priority': metadata.get('priority', 5)
            }

            # Use AI to generate better "when to use" guidance
            enhanced = self._enhance_agent_info_with_ai(agent_metadata_dict)

            # Infer category from name and tags
            category = self._infer_category(agent_name, metadata.get('tags', []))

            return AgentMetadata(
                name=agent_name,
                purpose=enhanced['purpose'],  # Use AI-enhanced purpose
                capabilities=capabilities[:5],  # Max 5
                when_to_use=enhanced['when_to_use'],  # Use AI-generated guidance
                category=category
            )

        except Exception as e:
            # If extraction fails, return None (agent will be skipped)
            return None

    def _infer_category(self, name: str, tags: List[str]) -> str:
        """Infer agent category from name and tags

        Args:
            name: Agent name
            tags: List of tags

        Returns:
            Category name
        """
        name_lower = name.lower()
        tags_lower = [t.lower() for t in tags]

        # Domain category
        if 'domain' in name_lower or 'domain' in tags_lower:
            return 'domain'

        # UI category
        if any(term in name_lower for term in ['ui', 'view', 'page', 'component']):
            return 'ui'
        if any(term in tags_lower for term in ['ui', 'frontend', 'view']):
            return 'ui'

        # Testing category
        if 'test' in name_lower or 'test' in tags_lower:
            return 'testing'

        # Architecture category
        if any(term in name_lower for term in ['architect', 'review', 'design']):
            return 'architecture'
        if 'architecture' in tags_lower:
            return 'architecture'

        # Default to general
        return 'general'

    # ===== Phase 5.6 Split Output Methods (TASK-PD-005) =====

    def _get_quality_standards_data(self) -> Dict[str, Any]:
        """Extract quality standards data (DRY fix)

        Returns:
            Dictionary with quality standards data
        """
        quality = self.analysis.quality
        return {
            'solid_compliance': quality.solid_compliance,
            'dry_compliance': quality.dry_compliance,
            'yagni_compliance': quality.yagni_compliance,
            'improvements': quality.improvements
        }

    def _get_agent_metadata_list(self) -> List[AgentMetadata]:
        """Extract agent metadata list (DRY fix)

        Returns:
            List of AgentMetadata objects
        """
        agent_metadata_list = []

        if self.output_path:
            # Read from template output directory
            agent_dir = self.output_path / "agents"
            if agent_dir.exists():
                for agent_file in sorted(agent_dir.glob("*.md")):
                    metadata_dict = self._read_agent_metadata_from_file(agent_file)
                    if metadata_dict:
                        enhanced = self._enhance_agent_info_with_ai(metadata_dict)
                        category = self._infer_category(
                            metadata_dict['name'],
                            metadata_dict.get('tags', [])
                        )
                        agent_metadata = AgentMetadata(
                            name=metadata_dict['name'],
                            purpose=enhanced['purpose'],
                            capabilities=[],
                            when_to_use=enhanced['when_to_use'],
                            category=category
                        )
                        agent_metadata_list.append(agent_metadata)
        elif self.agents:
            for agent in self.agents:
                metadata = self._extract_agent_metadata(agent)
                if metadata:
                    agent_metadata_list.append(metadata)

        return agent_metadata_list

    def _generate_loading_instructions(self) -> str:
        """Generate loading instructions section

        Returns:
            Markdown with instructions for loading extended content
        """
        instructions = [
            "# How to Load This Template",
            "",
            "This template documentation is split into three files for optimal loading:",
            "",
            "1. **CLAUDE.md** (this file) - Core architecture and quick reference",
            "2. **docs/patterns/README.md** - Detailed patterns and best practices",
            "3. **docs/reference/README.md** - Code examples and complete reference",
            "",
            "## Loading Strategy",
            "",
            "- **Start here**: Read CLAUDE.md for architecture overview and essential guidance",
            "- **When implementing**: Load `docs/patterns/README.md` for pattern details",
            "- **When troubleshooting**: Load `docs/reference/README.md` for examples and workflows",
            "",
            "## Why Split?",
            "",
            "Splitting reduces initial context load by ~70% while keeping essential information immediately available.",
            ""
        ]
        return "\n".join(instructions)

    def _generate_quality_standards_summary(self) -> str:
        """Generate quality standards summary (DRY fix)

        Returns:
            Markdown with quality standards summary
        """
        quality_data = self._get_quality_standards_data()

        summary = [
            "# Quality Standards",
            "",
            "## Quick Reference",
            "",
            "- **Unit Test Coverage**: ≥80%",
            "- **Branch Coverage**: ≥75%",
            f"- **SOLID Compliance**: {quality_data['solid_compliance']:.0f}/100",
            f"- **DRY Compliance**: {quality_data['dry_compliance']:.0f}/100",
            f"- **YAGNI Compliance**: {quality_data['yagni_compliance']:.0f}/100",
            ""
        ]

        # Add testing framework if available
        if self.analysis.technology.testing_frameworks:
            test_fw = self.analysis.technology.testing_frameworks[0]
            summary.append(f"- **Test Framework**: {test_fw}")
            summary.append("")

        summary.extend([
            "**For detailed standards**: See `docs/patterns/README.md`",
            ""
        ])

        return "\n".join(summary)

    def _group_agents_by_category(self, agents: List[AgentMetadata]) -> Dict[str, List[AgentMetadata]]:
        """Group agents by category (helper for agent usage summary)

        Args:
            agents: List of AgentMetadata objects

        Returns:
            Dictionary mapping category to list of agents
        """
        by_category = {}
        for metadata in agents:
            category = metadata.category.title()
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(metadata)
        return by_category

    def _generate_agent_usage_summary(self) -> str:
        """Generate agent usage summary

        Returns:
            Markdown with agent usage summary
        """
        usage = [
            "# Agent Usage",
            "",
            "This template includes specialized agents for common tasks.",
            ""
        ]

        agent_metadata_list = self._get_agent_metadata_list()

        if not agent_metadata_list:
            usage.extend([
                "## Quick Guide",
                "",
                "- Use **domain-specific agents** for business logic",
                "- Use **testing agents** for test generation",
                "- Use **UI agents** for view/component creation",
                "",
                "**For detailed agent documentation**: See `docs/reference/README.md`",
                ""
            ])
            return "\n".join(usage)

        # Group and show categories only
        by_category = self._group_agents_by_category(agent_metadata_list)

        usage.extend([
            "## Available Agent Categories",
            ""
        ])

        for category, agents in sorted(by_category.items()):
            agent_names = [f"`{a.name}`" for a in agents]
            usage.append(f"- **{category}**: {', '.join(agent_names)}")

        usage.extend([
            "",
            "**For detailed agent documentation**: See `docs/reference/README.md`",
            ""
        ])

        return "\n".join(usage)

    def _generate_core(self) -> str:
        """Generate core CLAUDE.md content (≤10KB target)

        Returns:
            Markdown with essential content only
        """
        sections = [
            self._generate_loading_instructions(),
            self._generate_architecture_overview(summary_only=True),  # Compact
            self._generate_technology_stack_summary(),  # Compact version
            self._generate_project_structure(max_depth=2),  # Truncated to 2 levels
            self._generate_quality_standards_summary(),
            self._generate_agent_usage_summary()
        ]
        return "\n\n".join(sections)

    def _generate_patterns_extended(self) -> str:
        """Generate extended patterns content

        Returns:
            Markdown with complete patterns and best practices
        """
        # Delegate to existing method
        patterns = self._generate_patterns()

        # Add full quality standards
        quality_standards = self._generate_quality_standards()

        return "\n\n".join([patterns, quality_standards])

    def _generate_reference_extended(self) -> str:
        """Generate extended reference content

        Returns:
            Markdown with examples, testing, workflows, and troubleshooting
        """
        sections = [
            self._generate_examples(),
            self._generate_naming_conventions(),
            self._generate_agent_usage()  # Full agent documentation
        ]
        return "\n\n".join(sections)

    def generate_split(self) -> TemplateSplitOutput:
        """Generate split CLAUDE.md output with size validation

        Returns:
            TemplateSplitOutput with validated core size

        Raises:
            ValueError: If core content exceeds 10KB limit
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        output = TemplateSplitOutput(
            core_content=self._generate_core(),
            patterns_content=self._generate_patterns_extended(),
            reference_content=self._generate_reference_extended(),
            generated_at=timestamp
        )

        # Validate size constraints
        is_valid, error_msg = output.validate_size_constraints()
        if not is_valid:
            raise ValueError(f"Size validation failed: {error_msg}")

        return output

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
