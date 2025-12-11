"""
Rules Structure Generator

Generates modular .claude/rules/ structure for Claude Code's memory system.
Implements path-specific conditional loading for reduced context window usage.

This generator creates a modular rules directory structure that supports:
- Path-specific rules (only load when relevant files are touched)
- Recursive discovery in subdirectories
- Conditional loading with paths: frontmatter
- Reduced context window usage (target: <5KB core CLAUDE.md)
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

from ..codebase_analyzer.models import CodebaseAnalysis
from .path_pattern_inferrer import PathPatternInferrer

logger = logging.getLogger(__name__)


@dataclass
class RuleFile:
    """Represents a single rules file."""
    path: str  # Relative path (e.g., "rules/code-style.md")
    content: str
    paths_filter: Optional[str] = None  # paths: frontmatter value


@dataclass
class ValidationIssue:
    """Represents a validation issue found during template generation."""
    level: str  # "warning" or "error"
    file: str
    message: str
    suggestion: str = ""


class RulesStructureGenerator:
    """
    Generate modular .claude/rules/ structure for Claude Code.

    This implements the new Claude Code memory system that supports:
    - Path-specific rules (only load when relevant)
    - Recursive discovery in subdirectories
    - Conditional loading with paths: frontmatter

    The generator creates a minimal core CLAUDE.md (~5KB) and moves detailed
    content into path-specific rules files that load conditionally.
    """

    def __init__(
        self,
        analysis: CodebaseAnalysis,
        agents: List,
        output_path: Path
    ):
        """
        Initialize the rules structure generator.

        Args:
            analysis: CodebaseAnalysis containing technology stack and architecture info
            agents: List of agent metadata objects
            output_path: Base output path for generated files
        """
        self.analysis = analysis
        self.agents = agents
        self.output_path = output_path
        self.path_inferrer = PathPatternInferrer(analysis)

    def generate(self) -> Dict[str, str]:
        """
        Generate rules structure.

        Returns:
            Dictionary mapping file paths to content

        Example:
            {
                "CLAUDE.md": "# Core Guide...",
                "rules/code-style.md": "---\npaths: **/*.py\n---\n...",
                "rules/testing.md": "---\npaths: **/*.test.*\n---\n...",
                "rules/patterns/repository.md": "...",
                "rules/guidance/api-specialist.md": "---\npaths: **/api/**\n---\n..."
            }
        """
        rules = {}

        # 1. Core CLAUDE.md (minimal, ~5KB)
        rules["CLAUDE.md"] = self._generate_core_claudemd()

        # 2. Code style rules (conditional by file type)
        rules["rules/code-style.md"] = self._generate_code_style_rules()

        # 3. Testing rules (conditional on test files)
        rules["rules/testing.md"] = self._generate_testing_rules()

        # 4. Pattern-specific rules (one file per pattern)
        for pattern in self.analysis.architecture.patterns:
            pattern_slug = self._slugify(pattern)
            rules[f"rules/patterns/{pattern_slug}.md"] = self._generate_pattern_rules(pattern)

        # 5. Agent guidance (one per agent, with path inference)
        for agent in self.agents:
            agent_slug = self._slugify(agent.name)
            rules[f"rules/guidance/{agent_slug}.md"] = self._generate_guidance_rules(agent)

        return rules

    def validate_guidance_sizes(self, rules_dir: Path) -> List[ValidationIssue]:
        """
        Validate guidance files stay under size threshold.

        This ensures progressive disclosure benefits are maintained
        by keeping guidance files slim (path-triggered hints only).

        Args:
            rules_dir: Path to .claude/rules/ directory

        Returns:
            List of validation issues (warnings for oversized files)
        """
        MAX_GUIDANCE_SIZE = 5 * 1024  # 5KB
        issues = []

        guidance_dir = rules_dir / "guidance"
        if not guidance_dir.exists():
            return issues

        for file in guidance_dir.glob("*.md"):
            size = file.stat().st_size
            if size > MAX_GUIDANCE_SIZE:
                issues.append(ValidationIssue(
                    level="warning",
                    file=str(file),
                    message=f"Guidance file {file.name} exceeds 5KB ({size:,} bytes)",
                    suggestion=(
                        "Guidance files should be slim summaries (<3KB). "
                        "Move detailed content to agents/{name}.md or agents/{name}-ext.md"
                    )
                ))

        return issues

    def _generate_core_claudemd(self) -> str:
        """
        Generate minimal core CLAUDE.md (~5KB).

        The core file contains only essential information:
        - Project overview (1-2 paragraphs)
        - Quick start commands
        - Link to rules/ for detailed guidance

        Returns:
            Minimal CLAUDE.md content
        """
        primary_lang = self.analysis.technology.primary_language
        frameworks = ", ".join(self.analysis.technology.framework_list) or "None"
        arch_style = self.analysis.architecture.architectural_style

        content = f"""# {Path(self.analysis.codebase_path).name}

## Project Overview

This is a {primary_lang} project using {frameworks}.
Architecture: {arch_style}

## Quick Start

```bash
# Install dependencies
{self._get_install_command()}

# Run tests
{self._get_test_command()}

# Start development
{self._get_dev_command()}
```

## Detailed Guidance

For detailed code style, testing patterns, architecture patterns, and agent-specific
guidance, see the `.claude/rules/` directory. Rules load automatically when you
work on relevant files.

- **Code Style**: `.claude/rules/code-style.md`
- **Testing**: `.claude/rules/testing.md`
- **Patterns**: `.claude/rules/patterns/`
- **Guidance**: `.claude/rules/guidance/`

## Technology Stack

**Language**: {primary_lang}
**Frameworks**: {frameworks}
**Architecture**: {arch_style}
"""
        return content.strip()

    def _generate_code_style_rules(self) -> str:
        """
        Generate code style rules with path filtering.

        Returns:
            Code style rules content with paths: frontmatter
        """
        primary_lang = self.analysis.technology.primary_language

        # Infer file extensions from language
        extensions = self._get_language_extensions(primary_lang)
        paths_filter = ", ".join([f"**/*{ext}" for ext in extensions])

        frontmatter = self._generate_frontmatter(paths_filter)

        content = f"""{frontmatter}# Code Style Guide

## Language: {primary_lang}

### Naming Conventions

{self._get_naming_conventions(primary_lang)}

### Formatting

{self._get_formatting_rules(primary_lang)}

### Best Practices

{self._get_language_best_practices(primary_lang)}
"""
        return content.strip()

    def _generate_testing_rules(self) -> str:
        """
        Generate testing rules with path filtering.

        Only loads when working on test files.

        Returns:
            Testing rules content with paths: frontmatter
        """
        paths_filter = "**/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*"
        frontmatter = self._generate_frontmatter(paths_filter)

        testing_frameworks = ", ".join(self.analysis.technology.testing_framework_list) or "pytest/unittest"

        content = f"""{frontmatter}# Testing Guide

## Testing Frameworks

{testing_frameworks}

## Test Structure

- Unit tests: Test individual functions/methods
- Integration tests: Test component interactions
- E2E tests: Test full user workflows

## Coverage Requirements

- Minimum line coverage: 80%
- Minimum branch coverage: 75%
- All public APIs must have tests

## Test Naming

{self._get_test_naming_conventions()}

## Best Practices

- Keep tests focused and isolated
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
"""
        return content.strip()

    def _generate_pattern_rules(self, pattern: str) -> str:
        """
        Generate rules for a specific design pattern.

        Args:
            pattern: Name of the design pattern (e.g., "Repository Pattern")

        Returns:
            Pattern-specific rules content
        """
        pattern_slug = self._slugify(pattern)

        content = f"""# {pattern}

## Overview

{self._get_pattern_description(pattern)}

## Implementation

{self._get_pattern_implementation_guide(pattern)}

## Example

{self._get_pattern_example(pattern)}

## Best Practices

{self._get_pattern_best_practices(pattern)}
"""
        return content.strip()

    def _read_enhanced_agent_content(self, agent_name: str) -> Optional[str]:
        """
        Read enhanced agent content from disk if available.

        TASK-RULES-ENHANCE: Enables using rich /agent-enhance content in rules/guidance.

        Args:
            agent_name: Name of the agent (e.g., "repository-specialist")

        Returns:
            Enhanced agent content or None if not found
        """
        # Check agents directory in output path
        agent_file = self.output_path / "agents" / f"{agent_name}.md"
        if agent_file.exists():
            try:
                content = agent_file.read_text()
                logger.debug(f"Read enhanced agent content from {agent_file}")
                return content
            except Exception as e:
                logger.warning(f"Failed to read enhanced agent file {agent_file}: {e}")
        return None

    def _merge_paths_into_frontmatter(
        self,
        content: str,
        paths_filter: str
    ) -> str:
        """
        Merge paths filter into existing frontmatter or add new frontmatter.

        Args:
            content: Original content (may have frontmatter)
            paths_filter: Path patterns to add

        Returns:
            Content with paths in frontmatter
        """
        if not paths_filter:
            return content

        # Check if content has frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                existing_fm = parts[1].strip()
                body = parts[2].strip()

                # Check if paths already in frontmatter
                if "paths:" in existing_fm:
                    # Already has paths, return as-is
                    return content

                # Add paths to existing frontmatter
                new_fm = f"---\npaths: {paths_filter}\n{existing_fm}\n---\n\n"
                return new_fm + body

        # No frontmatter - add new one with paths
        frontmatter = self._generate_frontmatter(paths_filter)
        return frontmatter + content

    def _generate_guidance_rules(self, agent) -> str:
        """
        Generate guidance file for an agent with path inference.

        TASK-RULES-ENHANCE: Now uses enhanced agent content when available,
        falling back to stub content for non-enhanced agents.

        Args:
            agent: Agent metadata object

        Returns:
            Agent-specific guidance content with paths: frontmatter
        """
        agent_slug = self._slugify(agent.name)

        # Try to read enhanced agent content first (TASK-RULES-ENHANCE)
        enhanced_content = self._read_enhanced_agent_content(agent_slug)

        # Get path filter for conditional loading
        agent_technologies = getattr(agent, 'technologies', [])
        paths_filter = self.path_inferrer.infer_for_agent(
            agent.name,
            agent_technologies
        )

        if enhanced_content:
            # Use enhanced content with path frontmatter
            logger.info(f"Using enhanced content for agent: {agent.name}")
            return self._merge_paths_into_frontmatter(enhanced_content, paths_filter)

        # Fallback to stub generation (original behavior)
        logger.debug(f"No enhanced content for agent: {agent.name}, using stub")
        frontmatter = self._generate_frontmatter(paths_filter) if paths_filter else ""

        content = f"""{frontmatter}# {agent.name}

## Purpose

{getattr(agent, 'purpose', 'Specialized agent for specific tasks')}

## Capabilities

{self._get_agent_capabilities(agent)}

## Usage

{self._get_agent_usage_guide(agent)}

## Best Practices

{self._get_agent_best_practices(agent)}
"""
        return content.strip()

    def _infer_agent_paths(self, agent_name: str) -> str:
        """
        DEPRECATED: Use PathPatternInferrer instead.

        Infer path patterns for conditional agent loading.

        This method is kept for backward compatibility but is no longer used.
        The new PathPatternInferrer class provides more intelligent inference
        based on codebase analysis.

        Args:
            agent_name: Name of the agent (e.g., "repository-specialist")

        Returns:
            Comma-separated path patterns, or empty string for always-load
        """
        path_mappings = {
            'repository': '**/Repositories/**/*.cs, **/repositories/**/*.py',
            'viewmodel': '**/ViewModels/**/*.cs, **/*ViewModel.cs',
            'service': '**/Services/**/*.cs, **/services/**/*.py',
            'engine': '**/Engines/**/*.cs, **/*Engine.cs',
            'testing': '**/tests/**/*.*, **/*.test.*',
            'api': '**/Controllers/**/*.cs, **/api/**/*.py, **/router*.py',
            'database': '**/models/*.py, **/crud/*.py, **/db/**',
            'query': '**/*query*, **/*api*, **/*fetch*',
            'form': '**/*form*, **/*validation*',
            'component': '**/components/**/*.tsx, **/components/**/*.jsx',
        }

        agent_lower = agent_name.lower()
        for key, paths in path_mappings.items():
            if key in agent_lower:
                return paths

        return ""  # No conditional loading (always load)

    def _generate_frontmatter(self, paths: Optional[str]) -> str:
        """
        Generate YAML frontmatter with paths filter.

        Args:
            paths: Comma-separated list of path patterns

        Returns:
            YAML frontmatter block or empty string if no paths
        """
        if not paths:
            return ""
        return f"""---
paths: {paths}
---

"""

    def _slugify(self, name: str) -> str:
        """
        Convert name to slug format.

        Args:
            name: Human-readable name

        Returns:
            URL-safe slug

        Examples:
            "Repository Pattern" -> "repository-pattern"
            "API_Specialist" -> "api-specialist"
        """
        return name.lower().replace(" ", "-").replace("_", "-")

    # Helper methods for content generation

    def _get_install_command(self) -> str:
        """Get installation command based on technology stack."""
        lang = self.analysis.technology.primary_language.lower()
        if lang == "python":
            return "pip install -r requirements.txt"
        elif lang in ["javascript", "typescript"]:
            return "npm install"
        elif lang == "c#":
            return "dotnet restore"
        else:
            return "# See project documentation"

    def _get_test_command(self) -> str:
        """Get test command based on testing framework."""
        testing = self.analysis.technology.testing_framework_list
        if any("pytest" in t.lower() for t in testing):
            return "pytest tests/ -v"
        elif any("jest" in t.lower() for t in testing):
            return "npm test"
        elif any("xunit" in t.lower() or "nunit" in t.lower() for t in testing):
            return "dotnet test"
        else:
            return "# See project documentation"

    def _get_dev_command(self) -> str:
        """Get development command based on frameworks."""
        frameworks = self.analysis.technology.framework_list
        if any("fastapi" in f.lower() for f in frameworks):
            return "uvicorn main:app --reload"
        elif any("flask" in f.lower() for f in frameworks):
            return "flask run"
        elif any("react" in f.lower() or "next" in f.lower() for f in frameworks):
            return "npm run dev"
        else:
            return "# See project documentation"

    def _get_language_extensions(self, language: str) -> List[str]:
        """Get file extensions for a programming language."""
        extensions_map = {
            "Python": [".py", ".pyx"],
            "JavaScript": [".js", ".jsx", ".mjs"],
            "TypeScript": [".ts", ".tsx"],
            "C#": [".cs"],
            "Java": [".java"],
            "Go": [".go"],
            "Rust": [".rs"],
            "Ruby": [".rb"],
            "PHP": [".php"],
        }
        return extensions_map.get(language, [".txt"])

    def _get_naming_conventions(self, language: str) -> str:
        """Get naming conventions for a language."""
        conventions = {
            "Python": "- Functions/variables: snake_case\n- Classes: PascalCase\n- Constants: UPPER_CASE",
            "JavaScript": "- Functions/variables: camelCase\n- Classes: PascalCase\n- Constants: UPPER_CASE",
            "TypeScript": "- Functions/variables: camelCase\n- Classes/Interfaces: PascalCase\n- Constants: UPPER_CASE",
            "C#": "- Methods/Properties: PascalCase\n- Local variables: camelCase\n- Constants: PascalCase",
        }
        return conventions.get(language, "- Follow language conventions")

    def _get_formatting_rules(self, language: str) -> str:
        """Get formatting rules for a language."""
        rules = {
            "Python": "- Use Black formatter\n- Max line length: 88 characters\n- Use type hints",
            "JavaScript": "- Use Prettier\n- Max line length: 100 characters\n- Use semicolons",
            "TypeScript": "- Use Prettier\n- Max line length: 100 characters\n- Strict type checking",
            "C#": "- Follow C# coding conventions\n- Max line length: 120 characters\n- Use var when type is obvious",
        }
        return rules.get(language, "- Follow language conventions")

    def _get_language_best_practices(self, language: str) -> str:
        """Get language-specific best practices."""
        practices = {
            "Python": "- Use list comprehensions\n- Prefer f-strings\n- Use context managers",
            "JavaScript": "- Use const by default\n- Avoid var\n- Use arrow functions",
            "TypeScript": "- Enable strict mode\n- Avoid any type\n- Use interfaces over types",
            "C#": "- Use async/await\n- Implement IDisposable\n- Use nullable reference types",
        }
        return practices.get(language, "- Follow language best practices")

    def _get_test_naming_conventions(self) -> str:
        """Get test naming conventions."""
        return """- test_<method_name>_<scenario>_<expected_result>
- Example: test_get_user_with_valid_id_returns_user
- Use descriptive names that explain the test"""

    def _get_pattern_description(self, pattern: str) -> str:
        """Get description for a design pattern."""
        descriptions = {
            "Repository": "Mediates between domain and data mapping layers",
            "Factory": "Creates objects without specifying exact classes",
            "Singleton": "Ensures a class has only one instance",
            "Observer": "Defines one-to-many dependency between objects",
            "Strategy": "Defines family of algorithms and makes them interchangeable",
        }
        for key, desc in descriptions.items():
            if key.lower() in pattern.lower():
                return desc
        return f"Implementation of {pattern}"

    def _get_pattern_implementation_guide(self, pattern: str) -> str:
        """Get implementation guide for a pattern."""
        return f"See codebase examples for {pattern} implementation details."

    def _get_pattern_example(self, pattern: str) -> str:
        """Get code example for a pattern."""
        # Look for examples in the codebase
        examples = self.analysis.example_files
        for example in examples:
            if pattern.lower() in " ".join(example.patterns_used).lower():
                return f"See: {example.path}"
        return "No examples found in codebase."

    def _get_pattern_best_practices(self, pattern: str) -> str:
        """Get best practices for a pattern."""
        return f"- Keep {pattern} implementations focused\n- Follow SOLID principles\n- Write comprehensive tests"

    def _get_agent_capabilities(self, agent) -> str:
        """Get agent capabilities."""
        if hasattr(agent, 'capabilities'):
            return "\n".join([f"- {cap}" for cap in agent.capabilities])
        return "- Specialized task handling"

    def _get_agent_usage_guide(self, agent) -> str:
        """Get agent usage guide."""
        return f"This agent is automatically invoked when working on relevant files."

    def _get_agent_best_practices(self, agent) -> str:
        """Get agent best practices."""
        return "- Follow agent guidance\n- Review generated code\n- Ask for clarification when needed"
