"""
Prompt Builder for Agent Invocation

Constructs context-aware prompts for the architectural-reviewer agent,
incorporating template context from TASK-001 and codebase information.

Following architectural review recommendations:
- Single responsibility (prompt construction only)
- Template-driven for maintainability
- Clear separation from agent invocation logic
"""

from pathlib import Path
from typing import Dict, List, Optional
import importlib

# Import using importlib to avoid 'global' keyword issue
_exclusions_module = importlib.import_module('lib.codebase_analyzer.exclusions')

DEFAULT_EXCLUSIONS = _exclusions_module.DEFAULT_EXCLUSIONS
should_exclude_path = _exclusions_module.should_exclude_path


class PromptBuilder:
    """
    Builds structured prompts for architectural-reviewer agent.

    This class focuses solely on prompt construction, following SRP.
    It incorporates template context from the template creation workflow
    (TASK-001) to provide relevant context to the agent.
    """

    def __init__(self, template_context: Optional[Dict[str, str]] = None):
        """
        Initialize prompt builder.

        Args:
            template_context: Context from template creation (TASK-001)
                            Contains: name, language, framework, description
        """
        self.template_context = template_context or {}

    def build_analysis_prompt(
        self,
        codebase_path: Path,
        file_samples: List[Dict[str, str]],
        directory_structure: str,
        max_files: int = 10
    ) -> str:
        """
        Build comprehensive analysis prompt for architectural-reviewer.

        Args:
            codebase_path: Path to the codebase being analyzed
            file_samples: List of sample files with content
                         Format: [{"path": "...", "content": "..."}]
            directory_structure: Tree view of directory structure
            max_files: Maximum number of file samples to include

        Returns:
            Formatted prompt string ready for agent invocation
        """
        # Build context section
        context_section = self._build_context_section(codebase_path)

        # Build file samples section
        samples_section = self._build_samples_section(file_samples[:max_files])

        # Build directory structure section
        structure_section = self._build_structure_section(directory_structure)

        # Build analysis request section
        request_section = self._build_request_section()

        # Combine all sections
        prompt = f"""
{context_section}

{structure_section}

{samples_section}

{request_section}
""".strip()

        return prompt

    def _build_context_section(self, codebase_path: Path) -> str:
        """Build the context section of the prompt."""
        context_lines = [
            "# Codebase Analysis Request",
            "",
            f"**Codebase Path**: {codebase_path}",
        ]

        if self.template_context:
            context_lines.append("")
            context_lines.append("## Template Context")
            context_lines.append("")
            context_lines.append("This analysis is for creating a template with the following characteristics:")

            if "name" in self.template_context:
                context_lines.append(f"- **Template Name**: {self.template_context['name']}")
            if "language" in self.template_context:
                context_lines.append(f"- **Primary Language**: {self.template_context['language']}")
            if "framework" in self.template_context:
                context_lines.append(f"- **Framework**: {self.template_context['framework']}")
            if "description" in self.template_context:
                context_lines.append(f"- **Description**: {self.template_context['description']}")

        return "\n".join(context_lines)

    def _build_structure_section(self, directory_structure: str) -> str:
        """Build the directory structure section."""
        return f"""
## Directory Structure

```
{directory_structure}
```
""".strip()

    def _build_samples_section(self, file_samples: List[Dict[str, str]]) -> str:
        """Build the file samples section."""
        if not file_samples:
            return "## File Samples\n\nNo file samples available."

        lines = [
            "## File Samples",
            "",
            f"Analyzing {len(file_samples)} representative files from the codebase:",
            ""
        ]

        for i, sample in enumerate(file_samples, 1):
            path = sample.get("path", "unknown")
            content = sample.get("content", "")
            language = self._detect_language_from_path(path)

            lines.append(f"### Sample {i}: `{path}`")
            lines.append("")
            lines.append(f"```{language}")
            lines.append(content)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _build_request_section(self) -> str:
        """Build the analysis request section with completeness guidance."""
        completeness_guidance = """
## Completeness Analysis Guidance

When analyzing this codebase:
- Identify ALL CRUD operations for each entity (Create/Read/Update/Delete/List)
- Note layer symmetry: UseCases operations should have corresponding Web endpoints
- Recognize patterns that require supporting files (Validators, Specs, Repositories)
- Recommend complete operation sets, not partial implementations
- Ensure all operations appear in relevant layers (Domain → Application → Infrastructure → Web)

This analysis will be used to create COMPLETE SCAFFOLDING templates, not just representative samples.
"""

        # TASK-51B2: Add AI-native metadata inference guidance when no template_context provided
        metadata_inference_guidance = ""
        if not self.template_context:
            metadata_inference_guidance = """
## AI-Native Metadata Inference (TASK-51B2)

**IMPORTANT**: No template context was provided. You must infer ALL template metadata directly from the codebase:

1. **Template Name**: Suggest based on language + framework (e.g., "fastapi-python", "react-typescript", "nextjs-fullstack")
2. **Primary Language**: Analyze file extensions (.py, .ts, .cs, .go, .rs) and config files
   - Python: setup.py, pyproject.toml, requirements.txt, Pipfile
   - TypeScript: package.json, tsconfig.json
   - .NET: *.csproj, *.sln
   - Go: go.mod, go.sum
   - Rust: Cargo.toml

3. **Framework**: Analyze dependencies and imports
   - Python: Read requirements.txt, pyproject.toml dependencies
   - TypeScript: Read package.json dependencies
   - .NET: Read *.csproj PackageReference elements
   - Go: Read go.mod require statements
   - Common frameworks: FastAPI, Flask, Django, React, Next.js, Vue, Angular, ASP.NET, Express

4. **Architecture Pattern**: Analyze folder structure and code organization
   - Look for: api/, models/, services/, controllers/, views/, components/, domain/, infrastructure/
   - Identify: Layered, MVC, MVVM, Clean Architecture, Hexagonal, Microservices, N-Tier

5. **Testing Framework**: Analyze test files and dependencies
   - Python: pytest, unittest, nose
   - TypeScript: Jest, Vitest, Mocha, Jasmine
   - .NET: xUnit, NUnit, MSTest
   - Go: testing package, testify

**Include these inferred values** in the JSON response under a new "metadata" section:
```json
{
  "metadata": {
    "template_name": "fastapi-python",
    "template_type": "Backend API",
    "primary_language": "Python",
    "framework": "FastAPI",
    "framework_version": "0.104.0",
    "architecture_pattern": "Layered (API routes + CRUD + models)",
    "testing_framework": "pytest",
    "confidence_score": 95
  }
}
```

**Do NOT ask questions. Do NOT use external detection code. Infer everything from the codebase itself.**
"""

        return f"""
{completeness_guidance}
{metadata_inference_guidance}

## Analysis Request

Please analyze this codebase and provide a comprehensive architectural assessment in JSON format:

```json
{{
  "technology": {{
    "primary_language": "...",
    "frameworks": ["..."],
    "testing_frameworks": ["..."],
    "build_tools": ["..."],
    "databases": ["..."],
    "infrastructure": ["..."],
    "confidence": {{
      "level": "high|medium|low|uncertain",
      "percentage": 95.0,
      "reasoning": "Why this confidence level"
    }}
  }},
  "architecture": {{
    "patterns": ["Repository", "Factory", "..."],
    "architectural_style": "Clean Architecture|Layered|...",
    "layers": [
      {{
        "name": "Domain",
        "description": "Core business logic",
        "typical_files": ["models.py", "entities.py"],
        "dependencies": []
      }}
    ],
    "key_abstractions": ["User", "Order", "..."],
    "dependency_flow": "Inward toward domain",
    "confidence": {{
      "level": "high|medium|low|uncertain",
      "percentage": 90.0,
      "reasoning": "Why this confidence level"
    }}
  }},
  "quality": {{
    "overall_score": 85.0,
    "solid_compliance": 80.0,
    "dry_compliance": 85.0,
    "yagni_compliance": 90.0,
    "test_coverage": 75.0,
    "code_smells": ["Duplicated validation logic in 3 files"],
    "strengths": ["Clear separation of concerns", "..."],
    "improvements": ["Extract common validation logic", "..."],
    "confidence": {{
      "level": "high|medium|low|uncertain",
      "percentage": 85.0,
      "reasoning": "Why this confidence level"
    }}
  }},
  "example_files": [
    {{
      "path": "src/domain/user.py",
      "purpose": "User entity with business logic",
      "layer": "Domain",
      "patterns_used": ["Entity", "Value Object"],
      "key_concepts": ["User", "Email", "Password"]
    }},
    {{
      "path": "src/application/create_user_usecase.py",
      "purpose": "Create user use case orchestrating business logic",
      "layer": "Application",
      "patterns_used": ["Use Case", "Command"],
      "key_concepts": ["Validation", "Repository", "Events"]
    }},
    {{
      "path": "src/infrastructure/repositories/user_repository.py",
      "purpose": "User repository implementing data access",
      "layer": "Infrastructure",
      "patterns_used": ["Repository", "Data Mapper"],
      "key_concepts": ["Database", "ORM", "Queries"]
    }},
    {{
      "path": "src/web/api/routes/users.py",
      "purpose": "User API endpoints and request handling",
      "layer": "Presentation",
      "patterns_used": ["REST", "Controller"],
      "key_concepts": ["Routes", "Validation", "DTOs"]
    }},
    {{
      "path": "src/domain/validators/email_validator.py",
      "purpose": "Email validation business rule",
      "layer": "Domain",
      "patterns_used": ["Value Object", "Validator"],
      "key_concepts": ["Validation", "Business Rules"]
    }},
    {{
      "path": "tests/unit/domain/test_user.py",
      "purpose": "Unit tests for User entity",
      "layer": "Testing",
      "patterns_used": ["Unit Test", "Fixture"],
      "key_concepts": ["Assertions", "Test Cases"]
    }},
    {{
      "path": "src/infrastructure/database/models.py",
      "purpose": "ORM models for database mapping",
      "layer": "Infrastructure",
      "patterns_used": ["ORM", "Data Model"],
      "key_concepts": ["Schema", "Relationships"]
    }},
    {{
      "path": "src/shared/exceptions.py",
      "purpose": "Custom domain exceptions",
      "layer": "Domain",
      "patterns_used": ["Exception Hierarchy"],
      "key_concepts": ["Error Handling", "Domain Errors"]
    }},
    {{
      "path": "src/application/dtos/user_dto.py",
      "purpose": "Data transfer objects for user operations",
      "layer": "Application",
      "patterns_used": ["DTO", "Serialization"],
      "key_concepts": ["Data Transfer", "Validation"]
    }},
    {{
      "path": "src/web/middleware/authentication.py",
      "purpose": "Authentication middleware",
      "layer": "Presentation",
      "patterns_used": ["Middleware", "Decorator"],
      "key_concepts": ["Auth", "Security", "JWT"]
    }}
  ]
}}
```

## Template File Selection Guidelines

**CRITICAL**: The `example_files` section above is for **TEMPLATE GENERATION**.
These files will become `.template` files with placeholders like `{{{{ProjectName}}}}`, `{{{{Namespace}}}}`, etc.

**Your Task**: Return 10-20 diverse example files that should become templates.
- **DO NOT** just return 1 example file - provide 10-20 files covering all layers
- **DIVERSITY IS CRITICAL** - Include files from domain, data, service, presentation, testing layers
- **TEMPLATE-WORTHY FILES** - Focus on files that developers would want as scaffolding:
  * Entities/Models (User, Order, Product)
  * Repositories (data access patterns)
  * Services/Use Cases (business logic orchestration)
  * Controllers/Routes (API endpoints)
  * Views/Components (UI elements)
  * Validators (business rules)
  * DTOs/Requests/Responses (data transfer)
  * Tests (unit, integration)
  * Middleware/Filters (cross-cutting concerns)
  * Configuration files (settings, dependency injection)

**What makes a good template file?**
1. **Representative** - Shows typical pattern for that layer
2. **Reusable** - Developer would want this as starting point
3. **Complete** - Demonstrates full pattern (CRUD operations, validation, error handling)
4. **Diverse** - Covers different architectural layers

**Example Response Strategy**:
For a FastAPI project, return example_files like:
- `app/domain/entities/user.py` (Domain entity)
- `app/domain/validators/email_validator.py` (Domain validation)
- `app/application/use_cases/create_user.py` (Application use case)
- `app/application/dtos/user_dto.py` (Data transfer object)
- `app/infrastructure/repositories/user_repository.py` (Repository)
- `app/infrastructure/database/models.py` (ORM models)
- `app/api/routes/users.py` (API routes)
- `app/api/middleware/auth.py` (Middleware)
- `tests/unit/test_user_entity.py` (Unit test)
- `tests/integration/test_user_api.py` (Integration test)

For a React project, return example_files like:
- `src/components/Button/Button.tsx` (Component)
- `src/components/Form/Form.tsx` (Form component)
- `src/hooks/useAuth.ts` (Custom hook)
- `src/hooks/useFetch.ts` (Data fetching hook)
- `src/services/api.ts` (API service)
- `src/utils/validation.ts` (Validation utilities)
- `src/store/userSlice.ts` (State management)
- `src/types/user.ts` (TypeScript types)
- `src/__tests__/Button.test.tsx` (Component test)
- `src/__tests__/hooks.test.ts` (Hook test)

**Remember**: These become `.template` files that developers scaffold with `taskwright init`.
Provide 10-20 diverse, template-worthy files covering all architectural layers.

Focus on:
1. **Technology Stack**: Accurate identification of languages, frameworks, and tools
2. **Architecture Patterns**: Design patterns and architectural style used
3. **SOLID Principles**: Compliance with Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
4. **DRY Principle**: Code reuse and avoidance of duplication
5. **YAGNI Principle**: Simplicity and avoiding over-engineering
6. **Quality Assessment**: Overall code quality, strengths, and areas for improvement
7. **Confidence Scores**: Your confidence in each assessment (high: 90%+, medium: 70-89%, low: 50-69%, uncertain: <50%)

Provide specific examples and reasoning for your assessments.
""".strip()

    def _detect_language_from_path(self, path: str) -> str:
        """Detect syntax highlighting language from file path."""
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".cs": "csharp",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
        }

        path_obj = Path(path)
        return ext_map.get(path_obj.suffix, "text")

    def build_quick_analysis_prompt(self, codebase_path: Path, structure_summary: str) -> str:
        """
        Build a quick analysis prompt for when detailed file content isn't available.

        Args:
            codebase_path: Path to codebase
            structure_summary: Brief summary of directory structure

        Returns:
            Simplified prompt for quick analysis
        """
        context = self._build_context_section(codebase_path)

        return f"""
{context}

## Structure Summary

{structure_summary}

## Quick Analysis Request

Based on the directory structure and template context, provide a high-level
architectural assessment. Focus on:

1. Technology stack identification
2. Likely architectural patterns
3. Basic quality assessment

Return results in the same JSON format as detailed analysis, but with
lower confidence scores due to limited information.
""".strip()


class FileCollector:
    """
    Collects representative files from codebase for analysis.

    Separate class following SRP - focuses on file system operations.
    """

    def __init__(self, codebase_path: Path, max_files: int = 10):
        """
        Initialize file collector.

        Args:
            codebase_path: Path to codebase
            max_files: Maximum number of files to collect
        """
        self.codebase_path = Path(codebase_path)
        self.max_files = max_files

        # Note: Exclusion patterns are now centralized in DEFAULT_EXCLUSIONS
        # from the exclusions module

    def collect_samples(self) -> List[Dict[str, str]]:
        """
        Collect representative file samples from codebase.

        Returns:
            List of dictionaries with 'path' and 'content' keys
        """
        samples = []
        collected = 0

        # Priority order: Look for key files first
        priority_patterns = [
            "**/*service*.py", "**/*service*.ts", "**/*service*.cs",
            "**/*model*.py", "**/*model*.ts", "**/*entity*.cs",
            "**/*repository*.py", "**/*repository*.ts", "**/*repository*.cs",
            "**/domain/**/*.py", "**/domain/**/*.ts", "**/Domain/**/*.cs",
        ]

        # Collect priority files first
        for pattern in priority_patterns:
            if collected >= self.max_files:
                break

            for file_path in self.codebase_path.glob(pattern):
                if collected >= self.max_files:
                    break

                if self._should_include(file_path):
                    content = self._read_file_safely(file_path)
                    if content:
                        samples.append({
                            "path": str(file_path.relative_to(self.codebase_path)),
                            "content": content
                        })
                        collected += 1

        # Fill remaining slots with any source files
        if collected < self.max_files:
            for ext in [".py", ".ts", ".tsx", ".cs", ".java"]:
                if collected >= self.max_files:
                    break

                for file_path in self.codebase_path.rglob(f"*{ext}"):
                    if collected >= self.max_files:
                        break

                    if self._should_include(file_path) and not any(
                        s["path"] == str(file_path.relative_to(self.codebase_path))
                        for s in samples
                    ):
                        content = self._read_file_safely(file_path)
                        if content:
                            samples.append({
                                "path": str(file_path.relative_to(self.codebase_path)),
                                "content": content
                            })
                            collected += 1

        return samples

    def get_directory_tree(self, max_depth: int = 4) -> str:
        """
        Generate a directory tree representation.

        Args:
            max_depth: Maximum depth to traverse

        Returns:
            String representation of directory tree
        """
        lines = []
        self._build_tree(self.codebase_path, lines, "", 0, max_depth)
        return "\n".join(lines)

    def _build_tree(
        self,
        directory: Path,
        lines: List[str],
        prefix: str,
        current_depth: int,
        max_depth: int
    ):
        """Recursively build directory tree."""
        if current_depth >= max_depth:
            return

        try:
            entries = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            entries = [e for e in entries if not self._should_ignore(e)]

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                current_prefix = "└── " if is_last else "├── "
                lines.append(f"{prefix}{current_prefix}{entry.name}")

                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    self._build_tree(entry, lines, prefix + extension, current_depth + 1, max_depth)
        except PermissionError:
            pass

    def _should_include(self, file_path: Path) -> bool:
        """Check if file should be included in samples."""
        if self._should_ignore(file_path):
            return False

        # Only include source code files
        source_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".java", ".go", ".rs"}
        if file_path.suffix not in source_extensions:
            return False

        # Skip test files for now (we want production code examples)
        if "test" in file_path.name.lower():
            return False

        # Skip files that are too large (> 10KB)
        try:
            if file_path.stat().st_size > 10 * 1024:
                return False
        except OSError:
            return False

        return True

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored using centralized exclusion patterns."""
        return should_exclude_path(path)

    def _read_file_safely(self, file_path: Path, max_lines: int = 100) -> Optional[str]:
        """
        Read file content safely with error handling.

        Args:
            file_path: Path to file
            max_lines: Maximum number of lines to read

        Returns:
            File content or None if read fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append("... (truncated)")
                        break
                    lines.append(line.rstrip())
                return "\n".join(lines)
        except (UnicodeDecodeError, PermissionError, OSError):
            return None
