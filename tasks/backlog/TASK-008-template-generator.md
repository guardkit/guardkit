---
id: TASK-008
title: Template Generator from Example Files
status: backlog
created: 2025-11-01T20:45:00Z
updated: 2025-11-02T00:00:00Z
priority: high
complexity: 5
estimated_hours: 7
tags: [template-generation, ai-assisted, placeholder-extraction]
epic: EPIC-001
feature: template-generation
dependencies: [TASK-002]
blocks: [TASK-010]
---

# TASK-008: Template Generator from Example Files

## Objective

Generate .template files from AI-identified good example files using AI assistance to extract patterns and create placeholders.

**Purpose**: Convert concrete example files into reusable templates with intelligent placeholder extraction (not regex-based).

## Context

**Input**: `CodebaseAnalysis` with `example_files` from TASK-002
**Output**: `TemplateCollection` (list of CodeTemplate objects)
**Data Contract**: See [template-contracts.md](../../docs/data-contracts/template-contracts.md#codetemplate)

**Key Principle**: Use AI (Claude Code) for placeholder extraction, not algorithmic parsing. This ensures intelligent understanding of:
- Business concepts vs implementation details
- Naming patterns and conventions
- Context-appropriate abstraction

## Acceptance Criteria

- [ ] Generate .template files from example files
- [ ] AI-assisted placeholder extraction
- [ ] Preserve code structure and patterns
- [ ] Quality scoring for each template
- [ ] Syntax validation for generated templates
- [ ] Template path inference (where to save)
- [ ] Placeholder documentation
- [ ] Support for multiple languages (C#, TypeScript, Python, Java)
- [ ] Manual review capability (optional)
- [ ] Template deduplication
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration with TASK-010

## Implementation

```python
# src/commands/template_create/template_generator.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict
import re
from ai_client import AIClient  # Claude Code integration

class TemplateGenerator:
    """Generate .template files from example files using AI"""

    def __init__(self, analysis: CodebaseAnalysis, ai_client: Optional[AIClient] = None):
        self.analysis = analysis
        self.ai_client = ai_client or AIClient()
        self.generated_templates: List[CodeTemplate] = []

    def generate(self, max_templates: Optional[int] = None) -> TemplateCollection:
        """
        Generate templates from all example files

        Args:
            max_templates: Maximum number of templates to generate (None = all)

        Returns:
            TemplateCollection with all generated templates
        """
        templates = []

        # Sort example files by quality score (highest first)
        sorted_examples = sorted(
            self.analysis.example_files,
            key=lambda x: x.quality_score,
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

        return TemplateCollection(
            templates=templates,
            total_count=len(templates),
            by_type=self._count_by_type(templates)
        )

    def _generate_template(self, example_file: ExampleFile) -> Optional[CodeTemplate]:
        """
        Generate a single template from an example file using AI

        Args:
            example_file: Example file to convert to template

        Returns:
            CodeTemplate or None if generation fails
        """
        # Read file content
        file_path = Path(example_file.path)
        if not file_path.exists():
            print(f"Example file not found: {example_file.path}")
            return None

        content = file_path.read_text()

        # Ask AI to generate template
        template_content, placeholders = self._ai_extract_placeholders(
            content=content,
            file_path=example_file.path,
            language=example_file.language,
            purpose=example_file.purpose
        )

        if not template_content:
            return None

        # Infer template path
        template_path = self._infer_template_path(example_file)

        # Create template name
        template_name = self._create_template_name(example_file)

        # Determine patterns demonstrated
        patterns = self._identify_patterns(content, example_file)

        return CodeTemplate(
            schema_version="1.0.0",
            name=template_name,
            original_path=example_file.path,
            template_path=template_path,
            content=template_content,
            placeholders=placeholders,
            file_type=example_file.file_type,
            language=example_file.language,
            purpose=example_file.purpose or "Generated from example",
            quality_score=example_file.quality_score,
            patterns=patterns
        )

    def _ai_extract_placeholders(
        self,
        content: str,
        file_path: str,
        language: str,
        purpose: Optional[str]
    ) -> tuple[str, List[str]]:
        """
        Use AI to extract placeholders from example file

        Args:
            content: File content
            file_path: Original file path
            language: Programming language
            purpose: File purpose

        Returns:
            (template_content, list_of_placeholders)
        """
        prompt = self._create_extraction_prompt(content, file_path, language, purpose)

        # Call AI
        response = self.ai_client.generate(prompt)

        # Parse AI response
        template_content, placeholders = self._parse_ai_response(response)

        return template_content, placeholders

    def _create_extraction_prompt(
        self,
        content: str,
        file_path: str,
        language: str,
        purpose: Optional[str]
    ) -> str:
        """Create prompt for AI placeholder extraction"""
        return f"""Convert this {language} file into a reusable template by replacing specific values with placeholders.

**Original File**: {file_path}
**Purpose**: {purpose or 'Not specified'}
**Language**: {language}

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

    def _parse_ai_response(self, response: str) -> tuple[str, List[str]]:
        """
        Parse AI response to extract template content and placeholders

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
        """Extract placeholder names from template content"""
        # Match {{PlaceholderName}} pattern
        pattern = r'\{\{([A-Za-z][A-Za-z0-9_]*)\}\}'
        matches = re.findall(pattern, content)

        # Return unique placeholders
        return list(set(matches))

    def _infer_template_path(self, example_file: ExampleFile) -> str:
        """
        Infer where to save template in template directory structure

        Args:
            example_file: Example file

        Returns:
            Relative path within templates/ directory
        """
        original_path = Path(example_file.path)

        # Try to match with layers
        for layer in self.analysis.layers:
            layer_path = Path(layer.path)
            try:
                # Check if example file is within layer
                relative = original_path.relative_to(layer_path)
                # Use layer name as top-level directory
                return f"templates/{layer.name}/{relative.parent / (original_path.stem + '.template')}"
            except ValueError:
                continue

        # Fallback: Use file type
        file_type = example_file.file_type or "other"
        return f"templates/{file_type}/{original_path.name}.template"

    def _create_template_name(self, example_file: ExampleFile) -> str:
        """Create template file name"""
        original_name = Path(example_file.path).name
        return f"{original_name}.template"

    def _identify_patterns(self, content: str, example_file: ExampleFile) -> List[str]:
        """
        Identify patterns demonstrated in the code

        Args:
            content: File content
            example_file: Example file metadata

        Returns:
            List of pattern names
        """
        patterns = []

        # Check for common patterns
        if "ErrorOr<" in content or "Result<" in content:
            patterns.append("Result type pattern")

        if "async " in content and "await " in content:
            patterns.append("Async/await")

        if "interface I" in content:
            patterns.append("Interface-based abstraction")

        if "record " in content or "sealed class" in content:
            patterns.append("Immutable data structures")

        if "repository" in content.lower():
            patterns.append("Repository pattern")

        if "ViewModel" in content:
            patterns.append("MVVM")

        if "Controller" in content:
            patterns.append("MVC")

        # Language-specific patterns
        lang = example_file.language.lower() if example_file.language else ""

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
        Validate generated template

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
        """Validate language-specific syntax"""
        errors = []
        lang = template.language.lower() if template.language else ""

        if lang in ["csharp", "c#"]:
            # Check for basic C# syntax
            if "namespace " in template.content and not re.search(r'namespace\s+[A-Za-z{]', template.content):
                errors.append("Invalid namespace syntax")

        elif lang in ["typescript", "javascript"]:
            # Check for basic TypeScript syntax
            pass  # TypeScript validation would require actual parsing

        elif lang == "python":
            # Check for basic Python syntax
            if "def " in template.content and not re.search(r'def\s+[a-z_]', template.content):
                errors.append("Invalid function definition syntax")

        return errors

    def _deduplicate_templates(self, templates: List[CodeTemplate]) -> List[CodeTemplate]:
        """
        Remove duplicate templates based on content similarity

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
        """Create hash for template deduplication"""
        # Use sorted placeholders and file type
        placeholder_str = ",".join(sorted(template.placeholders))
        return f"{template.file_type}:{placeholder_str}:{len(template.content)}"

    def _count_by_type(self, templates: List[CodeTemplate]) -> Dict[str, int]:
        """Count templates by file type"""
        counts = {}
        for template in templates:
            file_type = template.file_type or "unknown"
            counts[file_type] = counts.get(file_type, 0) + 1
        return counts

    def save_templates(self, collection: TemplateCollection, output_dir: Path):
        """
        Save all templates to disk

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

    def generate_with_review(
        self,
        max_templates: Optional[int] = None,
        interactive: bool = False
    ) -> TemplateCollection:
        """
        Generate templates with optional manual review

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
            print(f"Quality: {template.quality_score}/10")
            print(f"Placeholders: {', '.join(template.placeholders)}")
            print("\nContent preview:")
            print(template.content[:300] + "..." if len(template.content) > 300 else template.content)

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
        """Allow manual editing of template content"""
        # This would integrate with user's editor
        # For now, just return original
        print("Manual editing not implemented in this version")
        return content
```

## AI Client Integration

```python
# src/ai_client.py

from typing import Optional

class AIClient:
    """Client for AI-assisted operations"""

    def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Generate AI response for given prompt

        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens to generate

        Returns:
            AI-generated response
        """
        # This would integrate with Claude Code API
        # For now, return placeholder
        raise NotImplementedError("AI client integration required")

    def analyze_code(self, code: str, language: str) -> Dict[str, any]:
        """Analyze code structure"""
        raise NotImplementedError("AI client integration required")
```

## Testing Strategy

```python
# tests/test_template_generator.py

def test_template_generation():
    """Test template generation from example files"""
    analysis = create_mock_codebase_analysis(
        example_files=[
            ExampleFile(
                path="src/Domain/Products/GetProducts.cs",
                file_type="domain_operation",
                language="C#",
                purpose="Domain operation example",
                quality_score=9
            )
        ]
    )

    generator = TemplateGenerator(analysis, ai_client=MockAIClient())
    collection = generator.generate()

    assert collection.total_count == 1
    assert len(collection.templates) == 1
    assert collection.templates[0].language == "C#"

def test_ai_placeholder_extraction():
    """Test AI placeholder extraction"""
    content = """
    namespace MyCompany.MyApp.Domain.Products;

    public class GetProducts
    {
        public List<Product> Execute()
        {
            return new List<Product>();
        }
    }
    """

    generator = TemplateGenerator(create_mock_codebase_analysis(), MockAIClient())

    template_content, placeholders = generator._ai_extract_placeholders(
        content=content,
        file_path="test.cs",
        language="C#",
        purpose="Test"
    )

    assert "{{" in template_content
    assert "}}" in template_content
    assert len(placeholders) > 0

def test_placeholder_extraction_from_content():
    """Test placeholder extraction from template content"""
    content = "namespace {{ProjectName}}.{{Layer}};\n\npublic class {{Verb}}{{Entity}}"

    generator = TemplateGenerator(create_mock_codebase_analysis())
    placeholders = generator._extract_placeholders_from_content(content)

    assert "ProjectName" in placeholders
    assert "Layer" in placeholders
    assert "Verb" in placeholders
    assert "Entity" in placeholders

def test_template_path_inference():
    """Test template path inference"""
    analysis = create_mock_codebase_analysis(
        layers=[
            LayerInfo(name="Domain", path="src/Domain", purpose="Business logic", patterns=[], file_count=10)
        ]
    )

    example_file = ExampleFile(
        path="src/Domain/Products/GetProducts.cs",
        file_type="domain_operation",
        language="C#"
    )

    generator = TemplateGenerator(analysis)
    template_path = generator._infer_template_path(example_file)

    assert "templates/Domain/" in template_path
    assert ".template" in template_path

def test_pattern_identification():
    """Test pattern identification"""
    content = """
    public ErrorOr<Product> GetProduct(int id)
    {
        if (id <= 0)
            return Error.Validation("Invalid ID");

        return new Product { Id = id };
    }
    """

    example_file = ExampleFile(
        path="test.cs",
        file_type="code",
        language="C#"
    )

    generator = TemplateGenerator(create_mock_codebase_analysis())
    patterns = generator._identify_patterns(content, example_file)

    assert "Result type pattern" in patterns

def test_template_validation():
    """Test template validation"""
    # Valid template
    valid_template = CodeTemplate(
        name="Test.template",
        original_path="test.cs",
        template_path="templates/test.template",
        content="namespace {{ProjectName}};\n\npublic class {{ClassName}} {}",
        placeholders=["ProjectName", "ClassName"],
        file_type="code",
        language="C#",
        quality_score=8
    )

    generator = TemplateGenerator(create_mock_codebase_analysis())
    result = generator._validate_template(valid_template)

    assert result.is_valid

    # Invalid template (bad placeholder format)
    invalid_template = CodeTemplate(
        name="Test.template",
        original_path="test.cs",
        template_path="templates/test.template",
        content="namespace {{project_name}};",  # snake_case placeholder
        placeholders=["project_name"],  # Should be PascalCase
        file_type="code",
        language="C#",
        quality_score=8
    )

    result = generator._validate_template(invalid_template)
    assert not result.is_valid
    assert any("Invalid placeholder format" in err for err in result.errors)

def test_template_deduplication():
    """Test template deduplication"""
    templates = [
        CodeTemplate(
            name="Test1.template",
            original_path="test1.cs",
            template_path="templates/test1.template",
            content="namespace {{ProjectName}}; class {{ClassName}} {}",
            placeholders=["ProjectName", "ClassName"],
            file_type="code"
        ),
        CodeTemplate(
            name="Test2.template",
            original_path="test2.cs",
            template_path="templates/test2.template",
            content="namespace {{ProjectName}}; class {{ClassName}} {}",  # Same structure
            placeholders=["ProjectName", "ClassName"],
            file_type="code"
        ),
        CodeTemplate(
            name="Test3.template",
            original_path="test3.cs",
            template_path="templates/test3.template",
            content="interface {{InterfaceName}} {}",  # Different
            placeholders=["InterfaceName"],
            file_type="code"
        )
    ]

    generator = TemplateGenerator(create_mock_codebase_analysis())
    unique = generator._deduplicate_templates(templates)

    # Should keep Test1 and Test3 (Test2 is duplicate of Test1)
    assert len(unique) == 2
```

## Integration with TASK-010

```python
# From TASK-010 orchestrator
from template_generator import TemplateGenerator

template_gen = TemplateGenerator(analysis, ai_client)
collection = template_gen.generate(max_templates=20)  # Limit to top 20

# Validate
if collection.total_count == 0:
    raise GenerationError("No templates generated")

# Save
template_gen.save_templates(collection, template_dir)

print(f"Generated {collection.total_count} templates")
print(f"By type: {collection.by_type}")
```

## Manual Review Mode

```python
# Optional: Generate with manual review
collection = template_gen.generate_with_review(
    max_templates=10,
    interactive=True
)
```

## Definition of Done

- [ ] Complete TemplateGenerator class implemented
- [ ] AI-assisted placeholder extraction working
- [ ] Template path inference working
- [ ] Pattern identification working
- [ ] Template validation working
- [ ] Deduplication working
- [ ] Support for C#, TypeScript, Python, Java
- [ ] Quality scoring preserved
- [ ] Save templates to disk
- [ ] Manual review mode (optional)
- [ ] Unit tests passing (>85% coverage)
- [ ] Integration tests with TASK-010 passing

**Estimated Time**: 7 hours | **Complexity**: 5/10 | **Priority**: HIGH

**Rationale**: Higher complexity due to AI integration, prompt engineering, and multi-language support. The AI-first approach is critical - no regex-based placeholder extraction. The system must intelligently understand business concepts vs implementation details.

---

**Created**: 2025-11-01
**Updated**: 2025-11-02 (expanded specification)
**Status**: ✅ **READY FOR IMPLEMENTATION**
**Dependencies**: TASK-002 (CodebaseAnalysis)
**Blocks**: TASK-010 (Template Create)

## Notes

**AI Integration**: This task requires integration with Claude Code's AI API for intelligent placeholder extraction. The prompt engineering is critical to success - the AI must understand:
- Business concepts (entities, verbs, namespaces)
- Language-specific patterns
- What should be abstracted vs what should remain concrete
- Appropriate placeholder naming

**Alternative Implementation**: If AI integration is not available initially, a simpler regex-based approach can be used as a fallback, but quality will be lower.
