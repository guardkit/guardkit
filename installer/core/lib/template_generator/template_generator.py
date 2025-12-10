"""
Template Generator - AI-Assisted Template Creation

Generates .template files from example code files using AI to intelligently
extract placeholders while preserving code structure and patterns.

TASK-IMP-TC-F8A3: Enhanced placeholder extraction using centralized patterns.
"""

from pathlib import Path
from typing import List, Optional, Dict, Tuple
import re
import importlib

# Import using importlib to avoid 'global' keyword issue
_analyzer_models_module = importlib.import_module('installer.core.lib.codebase_analyzer.models')
_ai_client_module = importlib.import_module('installer.core.lib.template_generator.ai_client')
_models_module = importlib.import_module('installer.core.lib.template_generator.models')
_path_resolver_module = importlib.import_module('installer.core.lib.template_generator.path_resolver')
_placeholder_module = importlib.import_module('installer.core.lib.template_generator.placeholder_patterns')

CodebaseAnalysis = _analyzer_models_module.CodebaseAnalysis
ExampleFile = _analyzer_models_module.ExampleFile

AIClient = _ai_client_module.AIClient

CodeTemplate = _models_module.CodeTemplate
TemplateCollection = _models_module.TemplateCollection
ValidationResult = _models_module.ValidationResult
PlaceholderExtractionError = _models_module.PlaceholderExtractionError

TemplatePathResolver = _path_resolver_module.TemplatePathResolver

# TASK-IMP-TC-F8A3: Import placeholder extraction
PlaceholderExtractor = _placeholder_module.PlaceholderExtractor
PlaceholderResult = _placeholder_module.PlaceholderResult


class TemplateGenerator:
    """Generate .template files from example files using AI."""

    def __init__(
        self,
        analysis: CodebaseAnalysis,
        ai_client: Optional[AIClient] = None,
        manifest: Optional[Dict] = None
    ):
        """
        Initialize template generator.

        Args:
            analysis: Codebase analysis result
            ai_client: AI client for placeholder extraction (optional, uses default if not provided)
            manifest: Optional manifest dict for project-specific replacements (TASK-IMP-TC-F8A3)
        """
        self.analysis = analysis
        self.ai_client = ai_client or AIClient()
        self.generated_templates: List[CodeTemplate] = []
        self.path_resolver = TemplatePathResolver()
        # TASK-IMP-TC-F8A3: Initialize placeholder extractor with manifest
        self.placeholder_extractor = PlaceholderExtractor(manifest=manifest)

    def generate(self, max_templates: Optional[int] = None) -> TemplateCollection:
        """
        Generate templates from all example files.

        Args:
            max_templates: Maximum number of templates to generate (None = all)

        Returns:
            TemplateCollection with all generated templates
        """
        templates = []

        # Sort example files by quality score (highest first) if available
        sorted_examples = sorted(
            self.analysis.example_files,
            key=lambda x: getattr(x, 'quality_score', 0) if hasattr(x, 'quality_score') else 0,
            reverse=True
        )

        # Limit if specified
        examples_to_process = sorted_examples[:max_templates] if max_templates else sorted_examples

        for example_file in examples_to_process:
            try:
                template = self._generate_template(example_file)

                if template:
                    # Validate template
                    validation = self._validate_template(template)
                    if validation.is_valid:
                        templates.append(template)
                    else:
                        print(f"Template validation failed for {example_file.path}: {validation.errors}")

            except Exception as e:
                print(f"Failed to generate template from {example_file.path}: {e}")
                continue

        # Deduplicate templates
        templates = self._deduplicate_templates(templates)

        # Print classification summary
        print("\n" + self.path_resolver.get_classification_summary())

        # Print warnings if there are any
        if self.path_resolver.warnings:
            print(f"\n⚠️  Classification warnings ({len(self.path_resolver.warnings)}):")
            for warning in self.path_resolver.warnings[:5]:
                print(f"  {warning}")
            if len(self.path_resolver.warnings) > 5:
                print(f"  ... and {len(self.path_resolver.warnings) - 5} more")

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type=self._count_by_type(templates)
        )

    def _generate_template(self, example_file: ExampleFile) -> Optional[CodeTemplate]:
        """
        Generate a single template from an example file using AI.

        Args:
            example_file: Example file to convert to template

        Returns:
            CodeTemplate or None if generation fails
        """
        # Construct file path relative to codebase root
        codebase_path = Path(self.analysis.codebase_path)
        file_path = codebase_path / example_file.path

        if not file_path.exists():
            print(f"Example file not found: {file_path}")
            return None

        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
            return None

        # Determine language from example file or infer from extension
        language = getattr(example_file, 'language', None)
        if not language:
            language = self._infer_language(file_path)

        # Ask AI to generate template
        try:
            template_content, placeholders = self._ai_extract_placeholders(
                content=content,
                file_path=str(example_file.path),
                language=language,
                purpose=example_file.purpose
            )
        except PlaceholderExtractionError as e:
            print(f"Failed to extract placeholders: {e}")
            return None

        if not template_content:
            return None

        # Infer template path
        template_path = self._infer_template_path(example_file)

        # Create template name
        template_name = self._create_template_name(example_file)

        # Determine patterns demonstrated
        patterns = self._identify_patterns(content, example_file)

        # Extract quality score if available
        quality_score = None
        if hasattr(example_file, 'quality_score'):
            quality_score = example_file.quality_score

        # Extract file type if available
        file_type = None
        if hasattr(example_file, 'file_type'):
            file_type = example_file.file_type

        return CodeTemplate(
            schema_version="1.0.0",
            name=template_name,
            original_path=example_file.path,
            template_path=template_path,
            content=template_content,
            placeholders=placeholders,
            file_type=file_type,
            language=language,
            purpose=example_file.purpose or "Generated from example",
            quality_score=quality_score,
            patterns=patterns
        )

    def _ai_extract_placeholders(
        self,
        content: str,
        file_path: str,
        language: str,
        purpose: Optional[str]
    ) -> Tuple[str, List[str]]:
        """
        Use AI to extract placeholders from example file.

        Args:
            content: File content
            file_path: Original file path
            language: Programming language
            purpose: File purpose

        Returns:
            (template_content, list_of_placeholders)

        Raises:
            PlaceholderExtractionError: If extraction fails
        """
        prompt = self._create_extraction_prompt(content, file_path, language, purpose)

        try:
            # Call AI
            response = self.ai_client.generate(prompt)

            # Parse AI response
            template_content, placeholders = self._parse_ai_response(response)

            return template_content, placeholders

        except NotImplementedError:
            # Fallback: Use enhanced placeholder extraction (TASK-IMP-TC-F8A3)
            return self._fallback_placeholder_extraction(content, language, file_path)
        except Exception as e:
            raise PlaceholderExtractionError(f"Failed to extract placeholders: {e}")

    def _create_extraction_prompt(
        self,
        content: str,
        file_path: str,
        language: str,
        purpose: Optional[str]
    ) -> str:
        """Create prompt for AI placeholder extraction with completeness requirements."""

        completeness_requirements = """

**CRITICAL - TEMPLATE COMPLETENESS**:

You are generating SCAFFOLDING for complete features, not just examples.

CRUD Completeness Rule:
- If any CRUD operation exists, ALL must be generated:
  ✓ Create (POST)
  ✓ Read (GET by ID, GET collection)
  ✓ Update (PUT)
  ✓ Delete (DELETE)

Layer Symmetry Rule:
- If UseCases has UpdateEntity → Web must have Update endpoint
- If Web has Delete endpoint → UseCases must have DeleteEntity
- Operations must exist in ALL relevant layers

REPR Pattern Completeness:
- Each endpoint requires:
  ✓ Endpoint class (e.g., Create.cs)
  ✓ Request DTO (e.g., CreateEntityRequest.cs)
  ✓ Response DTO (e.g., CreateEntityResponse.cs) [if non-void]
  ✓ Validator (e.g., CreateEntityValidator.cs)

Remember: Users need COMPLETE CRUD operations, not representative samples.
"""

        return f"""Convert this {language} file into a reusable template by replacing specific values with placeholders.

**Original File**: {file_path}
**Purpose**: {purpose or 'Not specified'}
**Language**: {language}

{completeness_requirements}

**Instructions**:
1. Identify project-specific values (e.g., class names, namespaces, entity names, verbs)
2. Replace them with descriptive placeholders using {{{{PlaceholderName}}}} format
3. Preserve the code structure, patterns, and best practices
4. Keep generic/reusable code unchanged
5. Use PascalCase for placeholder names (e.g., {{{{ProjectName}}}}, {{{{EntityName}}}}, {{{{Verb}}}})

**Examples of what to replace**:
- Project/namespace: "MyCompany.MyApp" → "{{{{ProjectName}}}}"
- Entity names: "Product", "Order" → "{{{{EntityName}}}}"
- Verb operations: "Get", "Create", "Update" → "{{{{Verb}}}}"
- Specific strings: "Products", "Users" → "{{{{EntityNamePlural}}}}"

**Examples of what NOT to replace**:
- Language keywords
- Framework types/classes
- Common patterns (ErrorOr, Result, etc.)
- Standard library imports

**Original Content**:
```{language}
{content}
```

**Output Format**:
Return ONLY the templated content (no explanation).
After the template, on a new line starting with "PLACEHOLDERS:", list all placeholders used.

Example:
```
{{{{Namespace}}}}.Domain.{{{{EntityNamePlural}}}};

public class {{{{Verb}}}}{{{{EntityName}}}}
{{
    // implementation
}}
```
PLACEHOLDERS: Namespace, EntityNamePlural, Verb, EntityName
"""

    def _parse_ai_response(self, response: str) -> Tuple[str, List[str]]:
        """
        Parse AI response to extract template content and placeholders.

        Args:
            response: AI response text

        Returns:
            (template_content, list_of_placeholders)
        """
        # Split response into template and placeholders
        parts = response.split("PLACEHOLDERS:")

        template_content = parts[0].strip()

        # Extract placeholders list
        placeholders = []
        if len(parts) > 1:
            placeholder_text = parts[1].strip()
            # Parse comma-separated list
            placeholders = [p.strip() for p in placeholder_text.split(",")]
        else:
            # Fallback: Extract placeholders from template content
            placeholders = self._extract_placeholders_from_content(template_content)

        # Remove code fence if present
        if template_content.startswith("```"):
            lines = template_content.split("\n")
            # Remove first line (```language)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            template_content = "\n".join(lines)

        return template_content, placeholders

    def _extract_placeholders_from_content(self, content: str) -> List[str]:
        """Extract placeholder names from template content."""
        # Match {{PlaceholderName}} pattern
        pattern = r'\{\{([A-Za-z][A-Za-z0-9_]*)\}\}'
        matches = re.findall(pattern, content)

        # Return unique placeholders
        return list(set(matches))

    def _fallback_placeholder_extraction(
        self,
        content: str,
        language: str,
        file_path: str = ""
    ) -> Tuple[str, List[str]]:
        """
        Fallback placeholder extraction when AI is not available.

        TASK-IMP-TC-F8A3: Enhanced with comprehensive regex-based extraction
        using centralized PlaceholderExtractor.

        Args:
            content: File content
            language: Programming language
            file_path: Original file path (used to determine patterns)

        Returns:
            (template_content, list_of_placeholders)
        """
        # Use the centralized PlaceholderExtractor (TASK-IMP-TC-F8A3)
        result = self.placeholder_extractor.extract(content, file_path)

        # Log coverage for debugging
        is_valid, message = self.placeholder_extractor.validate_coverage(result)
        if not is_valid:
            print(f"  ⚠️  {message}")

        return result.content, result.placeholders

    def _infer_language(self, file_path: Path) -> str:
        """Infer programming language from file extension."""
        extension_map = {
            '.cs': 'C#',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.py': 'Python',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
        }
        return extension_map.get(file_path.suffix, 'Unknown')

    def _infer_template_path(self, example_file: ExampleFile) -> str:
        """
        Infer where to save template in template directory structure.

        Uses the path resolver with Strategy pattern:
        1. LayerClassificationStrategy - AI-provided layer info (PRIMARY)
        2. PatternClassificationStrategy - filename pattern inference (FALLBACK)
        3. Fallback to templates/other/ when classification fails

        Args:
            example_file: Example file

        Returns:
            Relative path within templates/ directory
        """
        return self.path_resolver.resolve(example_file, self.analysis)

    def _create_template_name(self, example_file: ExampleFile) -> str:
        """Create template file name."""
        original_name = Path(example_file.path).name
        return f"{original_name}.template"

    def _identify_patterns(self, content: str, example_file: ExampleFile) -> List[str]:
        """
        Identify patterns demonstrated in the code.

        Args:
            content: File content
            example_file: Example file metadata

        Returns:
            List of pattern names
        """
        patterns = []

        # Use patterns from example file if available
        if hasattr(example_file, 'patterns_used'):
            patterns.extend(example_file.patterns_used)

        # Check for common patterns in content
        if "ErrorOr<" in content or "Result<" in content:
            if "Result type pattern" not in patterns:
                patterns.append("Result type pattern")

        if "async " in content and "await " in content:
            if "Async/await" not in patterns:
                patterns.append("Async/await")

        if "interface I" in content:
            if "Interface-based abstraction" not in patterns:
                patterns.append("Interface-based abstraction")

        if "record " in content or "sealed class" in content:
            if "Immutable data structures" not in patterns:
                patterns.append("Immutable data structures")

        if "repository" in content.lower():
            if "Repository pattern" not in patterns:
                patterns.append("Repository pattern")

        if "ViewModel" in content:
            if "MVVM" not in patterns:
                patterns.append("MVVM")

        if "Controller" in content:
            if "MVC" not in patterns:
                patterns.append("MVC")

        # Language-specific patterns
        language = getattr(example_file, 'language', '')
        if language:
            lang = language.lower()

            if lang in ["csharp", "c#"]:
                if "INotifyPropertyChanged" in content:
                    patterns.append("Property change notification")
                if "[Required]" in content or "[StringLength" in content:
                    patterns.append("Data annotations")

            elif lang in ["typescript", "javascript"]:
                if "useState" in content or "useEffect" in content:
                    patterns.append("React hooks")
                if "type " in content and " = " in content:
                    patterns.append("Type aliases")

            elif lang == "python":
                if "@dataclass" in content:
                    patterns.append("Dataclasses")
                if "with " in content:
                    patterns.append("Context managers")

        return patterns

    def _validate_template(self, template: CodeTemplate) -> ValidationResult:
        """
        Validate generated template.

        Args:
            template: Template to validate

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # Check template has content
        if not template.content:
            errors.append("Template content is empty")

        # Check placeholders were extracted
        if not template.placeholders:
            warnings.append("No placeholders found in template")

        # Check placeholder format
        for placeholder in template.placeholders:
            if not re.match(r'^[A-Z][A-Za-z0-9_]*$', placeholder):
                errors.append(f"Invalid placeholder format: {placeholder} (should be PascalCase)")

        # Check placeholders exist in content
        for placeholder in template.placeholders:
            placeholder_pattern = f"{{{{{placeholder}}}}}"
            if placeholder_pattern not in template.content:
                warnings.append(f"Placeholder {placeholder} not found in template content")

        # Language-specific validation
        if template.language:
            lang_errors = self._validate_language_syntax(template)
            errors.extend(lang_errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_language_syntax(self, template: CodeTemplate) -> List[str]:
        """Validate language-specific syntax."""
        errors = []
        lang = template.language.lower() if template.language else ""

        if lang in ["csharp", "c#"]:
            # Check for basic C# syntax
            if "namespace " in template.content:
                if not re.search(r'namespace\s+[A-Za-z{]', template.content):
                    errors.append("Invalid namespace syntax")

        elif lang in ["typescript", "javascript"]:
            # TypeScript validation would require actual parsing
            # Basic check: if has class/function keywords
            pass

        elif lang == "python":
            # Check for basic Python syntax
            if "def " in template.content:
                if not re.search(r'def\s+[a-z_]', template.content):
                    errors.append("Invalid function definition syntax")

        return errors

    def _deduplicate_templates(self, templates: List[CodeTemplate]) -> List[CodeTemplate]:
        """
        Remove duplicate templates based on content similarity.

        Args:
            templates: List of templates

        Returns:
            Deduplicated list
        """
        if not templates:
            return templates

        unique_templates = []
        seen_hashes = set()

        for template in templates:
            # Create simple hash based on placeholders and structure
            content_hash = self._template_hash(template)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_templates.append(template)

        return unique_templates

    def _template_hash(self, template: CodeTemplate) -> str:
        """Create hash for template deduplication."""
        # Use sorted placeholders and file type
        placeholder_str = ",".join(sorted(template.placeholders))
        file_type = template.file_type or "unknown"
        content_len = len(template.content)
        return f"{file_type}:{placeholder_str}:{content_len}"

    def _count_by_type(self, templates: List[CodeTemplate]) -> Dict[str, int]:
        """Count templates by file type."""
        counts: Dict[str, int] = {}
        for template in templates:
            file_type = template.file_type or "unknown"
            counts[file_type] = counts.get(file_type, 0) + 1
        return counts

    def save_templates(self, collection: TemplateCollection, output_dir: Path):
        """
        Save all templates to disk.

        Args:
            collection: Template collection
            output_dir: Output directory (template root)
        """
        for template in collection.templates:
            # Create full path
            template_path = output_dir / template.template_path

            # Create directory if needed
            template_path.parent.mkdir(parents=True, exist_ok=True)

            # Write template content
            template_path.write_text(template.content)

            print(f"Saved template: {template_path}")

    def generate_with_review(
        self,
        max_templates: Optional[int] = None,
        interactive: bool = False
    ) -> TemplateCollection:
        """
        Generate templates with optional manual review.

        Args:
            max_templates: Maximum templates to generate
            interactive: If True, prompt for review of each template

        Returns:
            TemplateCollection with approved templates
        """
        collection = self.generate(max_templates)

        if not interactive:
            return collection

        # Manual review mode
        approved_templates = []

        for template in collection.templates:
            print(f"\n--- Template: {template.name} ---")
            print(f"Original: {template.original_path}")
            if template.quality_score:
                print(f"Quality: {template.quality_score}/10")
            print(f"Placeholders: {', '.join(template.placeholders)}")
            print("\nContent preview:")
            preview = template.content[:300] + "..." if len(template.content) > 300 else template.content
            print(preview)

            response = input("\nApprove this template? (y/n/edit): ").lower()

            if response == 'y':
                approved_templates.append(template)
            elif response == 'edit':
                # Allow manual editing
                edited_content = self._manual_edit(template.content)
                template.content = edited_content
                approved_templates.append(template)
            # 'n' or anything else = skip

        return TemplateCollection(
            templates=approved_templates,
            total_count=len(approved_templates),
            by_type=self._count_by_type(approved_templates)
        )

    def _manual_edit(self, content: str) -> str:
        """
        Allow manual editing of template content.

        Note: This would integrate with user's editor in production.
        For now, just return original.
        """
        print("Manual editing not implemented in this version")
        return content
