---
id: TASK-045A
title: Language Syntax Database
status: backlog
created: 2025-11-01T18:45:00Z
priority: high
complexity: 4
estimated_hours: 4
tags: [syntax, language-database, template-generation]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-037A]
blocks: [TASK-045]
---

# TASK-045A: Language Syntax Database

## Objective

Create comprehensive language syntax database to support template generation for ANY programming language - providing syntax rules, placeholder formats, comment styles, and code structure patterns.

**Current Problem:** Template generation hardcoded to 4 languages
**Solution:** Universal syntax database with 50+ languages

## Acceptance Criteria

- [ ] Syntax database for 50+ languages
- [ ] Comment styles (single-line, multi-line, doc comments)
- [ ] Placeholder formats compatible with each language
- [ ] Class/function/variable syntax patterns
- [ ] Import/dependency syntax
- [ ] Testing framework syntax
- [ ] File naming conventions per language
- [ ] Template-safe placeholder patterns
- [ ] Unit tests for syntax retrieval
- [ ] Documentation of syntax patterns

## Implementation

### 1. Syntax Database Schema

```python
# src/commands/template_create/syntax_database.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum

@dataclass
class CommentSyntax:
    """Comment syntax for a language"""
    single_line: Optional[str]        # e.g., "//" or "#"
    multi_line_start: Optional[str]   # e.g., "/*"
    multi_line_end: Optional[str]     # e.g., "*/"
    doc_comment_start: Optional[str]  # e.g., "///" or "##"
    doc_comment_line: Optional[str]   # e.g., "///" or "#"

@dataclass
class SyntaxPatterns:
    """Syntax patterns for code generation"""
    class_definition: str             # Template for class definition
    interface_definition: Optional[str]  # Template for interface
    function_definition: str          # Template for function
    method_definition: str            # Template for method
    variable_declaration: str         # Template for variable
    constant_declaration: str         # Template for constant
    import_statement: str             # Template for imports
    test_function: str                # Template for test function

@dataclass
class PlaceholderFormat:
    """Placeholder format for templates"""
    pattern: str                      # e.g., "{{ClassName}}" or "${ClassName}"
    escape_char: Optional[str]        # If placeholders need escaping
    reserved_words: Set[str]          # Language keywords to avoid

@dataclass
class LanguageSyntax:
    """Complete syntax information for a language"""
    language: str
    file_extensions: Set[str]
    comments: CommentSyntax
    patterns: SyntaxPatterns
    placeholder_format: PlaceholderFormat
    naming_conventions: Dict[str, str]  # element_type -> convention
    indentation: str                   # "tabs" or "spaces" or "both"
    typical_indent_size: int           # 2, 4, etc.
    statement_terminator: Optional[str]  # ";" or None

# Comprehensive syntax database
SYNTAX_DATABASE: Dict[str, LanguageSyntax] = {
    "go": LanguageSyntax(
        language="Go",
        file_extensions={".go"},
        comments=CommentSyntax(
            single_line="//",
            multi_line_start="/*",
            multi_line_end="*/",
            doc_comment_start="//",
            doc_comment_line="//"
        ),
        patterns=SyntaxPatterns(
            class_definition="type {{ClassName}} struct {\n\t// fields\n}",
            interface_definition="type {{InterfaceName}} interface {\n\t// methods\n}",
            function_definition="func {{FunctionName}}({{Params}}) {{ReturnType}} {\n\t// implementation\n}",
            method_definition="func ({{Receiver}}) {{MethodName}}({{Params}}) {{ReturnType}} {\n\t// implementation\n}",
            variable_declaration="var {{VarName}} {{Type}}",
            constant_declaration="const {{ConstName}} {{Type}} = {{Value}}",
            import_statement='import "{{PackagePath}}"',
            test_function="func Test{{FunctionName}}(t *testing.T) {\n\t// test code\n}"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"func", "type", "var", "const", "if", "for", "range", "return"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "function": "PascalCase",  # Exported functions
            "private_function": "camelCase",
            "variable": "camelCase",
            "constant": "PascalCase"
        },
        indentation="tabs",
        typical_indent_size=4,
        statement_terminator=None
    ),

    "rust": LanguageSyntax(
        language="Rust",
        file_extensions={".rs"},
        comments=CommentSyntax(
            single_line="//",
            multi_line_start="/*",
            multi_line_end="*/",
            doc_comment_start="///",
            doc_comment_line="///"
        ),
        patterns=SyntaxPatterns(
            class_definition="pub struct {{ClassName}} {\n\t// fields\n}",
            interface_definition="pub trait {{TraitName}} {\n\t// methods\n}",
            function_definition="pub fn {{function_name}}({{params}}) -> {{ReturnType}} {\n\t// implementation\n}",
            method_definition="impl {{ClassName}} {\n\tpub fn {{method_name}}(&self, {{params}}) -> {{ReturnType}} {\n\t\t// implementation\n\t}\n}",
            variable_declaration="let {{var_name}}: {{Type}} = {{value}};",
            constant_declaration="const {{CONST_NAME}}: {{Type}} = {{value}};",
            import_statement="use {{crate_path}};",
            test_function="#[test]\nfn test_{{function_name}}() {\n\t// test code\n}"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"fn", "struct", "impl", "trait", "let", "const", "if", "match", "return"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "trait": "PascalCase",
            "function": "snake_case",
            "variable": "snake_case",
            "constant": "SCREAMING_SNAKE"
        },
        indentation="spaces",
        typical_indent_size=4,
        statement_terminator=";"
    ),

    "java": LanguageSyntax(
        language="Java",
        file_extensions={".java"},
        comments=CommentSyntax(
            single_line="//",
            multi_line_start="/*",
            multi_line_end="*/",
            doc_comment_start="/**",
            doc_comment_line=" *"
        ),
        patterns=SyntaxPatterns(
            class_definition="public class {{ClassName}} {\n\t// fields and methods\n}",
            interface_definition="public interface {{InterfaceName}} {\n\t// method signatures\n}",
            function_definition="public {{ReturnType}} {{methodName}}({{Params}}) {\n\t// implementation\n}",
            method_definition="public {{ReturnType}} {{methodName}}({{Params}}) {\n\t// implementation\n}",
            variable_declaration="{{Type}} {{varName}} = {{value}};",
            constant_declaration="public static final {{Type}} {{CONST_NAME}} = {{value}};",
            import_statement="import {{PackagePath}};",
            test_function="@Test\npublic void test{{MethodName}}() {\n\t// test code\n}"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"class", "interface", "public", "private", "static", "final", "if", "for", "return"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "interface": "PascalCase",
            "method": "camelCase",
            "variable": "camelCase",
            "constant": "SCREAMING_SNAKE"
        },
        indentation="spaces",
        typical_indent_size=4,
        statement_terminator=";"
    ),

    "python": LanguageSyntax(
        language="Python",
        file_extensions={".py"},
        comments=CommentSyntax(
            single_line="#",
            multi_line_start='"""',
            multi_line_end='"""',
            doc_comment_start='"""',
            doc_comment_line=""
        ),
        patterns=SyntaxPatterns(
            class_definition="class {{ClassName}}:\n\t\"\"\"{{DocString}}\"\"\"\n\tpass",
            interface_definition="class {{InterfaceName}}(Protocol):\n\t\"\"\"{{DocString}}\"\"\"\n\tpass",
            function_definition="def {{function_name}}({{params}}) -> {{ReturnType}}:\n\t\"\"\"{{DocString}}\"\"\"\n\tpass",
            method_definition="def {{method_name}}(self, {{params}}) -> {{ReturnType}}:\n\t\"\"\"{{DocString}}\"\"\"\n\tpass",
            variable_declaration="{{var_name}}: {{Type}} = {{value}}",
            constant_declaration="{{CONST_NAME}}: {{Type}} = {{value}}",
            import_statement="from {{module}} import {{name}}",
            test_function="def test_{{function_name}}():\n\t\"\"\"{{DocString}}\"\"\"\n\tpass"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"def", "class", "if", "for", "while", "return", "import", "from"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "function": "snake_case",
            "variable": "snake_case",
            "constant": "SCREAMING_SNAKE"
        },
        indentation="spaces",
        typical_indent_size=4,
        statement_terminator=None
    ),

    "typescript": LanguageSyntax(
        language="TypeScript",
        file_extensions={".ts", ".tsx"},
        comments=CommentSyntax(
            single_line="//",
            multi_line_start="/*",
            multi_line_end="*/",
            doc_comment_start="/**",
            doc_comment_line=" *"
        ),
        patterns=SyntaxPatterns(
            class_definition="export class {{ClassName}} {\n\t// properties and methods\n}",
            interface_definition="export interface {{InterfaceName}} {\n\t// properties\n}",
            function_definition="export function {{functionName}}({{params}}): {{ReturnType}} {\n\t// implementation\n}",
            method_definition="{{methodName}}({{params}}): {{ReturnType}} {\n\t// implementation\n}",
            variable_declaration="const {{varName}}: {{Type}} = {{value}};",
            constant_declaration="export const {{CONST_NAME}}: {{Type}} = {{value}};",
            import_statement="import { {{names}} } from '{{module}}';",
            test_function="test('{{test name}}', () => {\n\t// test code\n});"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"class", "interface", "function", "const", "let", "var", "if", "for", "return", "export"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "interface": "PascalCase",
            "function": "camelCase",
            "variable": "camelCase",
            "constant": "SCREAMING_SNAKE"
        },
        indentation="spaces",
        typical_indent_size=2,
        statement_terminator=";"
    ),

    "ruby": LanguageSyntax(
        language="Ruby",
        file_extensions={".rb"},
        comments=CommentSyntax(
            single_line="#",
            multi_line_start="=begin",
            multi_line_end="=end",
            doc_comment_start="#",
            doc_comment_line="#"
        ),
        patterns=SyntaxPatterns(
            class_definition="class {{ClassName}}\n\t# methods\nend",
            interface_definition="module {{ModuleName}}\n\t# methods\nend",
            function_definition="def {{method_name}}({{params}})\n\t# implementation\nend",
            method_definition="def {{method_name}}({{params}})\n\t# implementation\nend",
            variable_declaration="{{var_name}} = {{value}}",
            constant_declaration="{{CONST_NAME}} = {{value}}",
            import_statement="require '{{module}}'",
            test_function="def test_{{method_name}}\n\t# test code\nend"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"def", "class", "module", "if", "unless", "while", "until", "return", "end"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "module": "PascalCase",
            "method": "snake_case",
            "variable": "snake_case",
            "constant": "SCREAMING_SNAKE"
        },
        indentation="spaces",
        typical_indent_size=2,
        statement_terminator=None
    ),

    "csharp": LanguageSyntax(
        language="C#",
        file_extensions={".cs"},
        comments=CommentSyntax(
            single_line="//",
            multi_line_start="/*",
            multi_line_end="*/",
            doc_comment_start="///",
            doc_comment_line="///"
        ),
        patterns=SyntaxPatterns(
            class_definition="public class {{ClassName}}\n{\n\t// properties and methods\n}",
            interface_definition="public interface {{InterfaceName}}\n{\n\t// method signatures\n}",
            function_definition="public {{ReturnType}} {{MethodName}}({{Params}})\n{\n\t// implementation\n}",
            method_definition="public {{ReturnType}} {{MethodName}}({{Params}})\n{\n\t// implementation\n}",
            variable_declaration="var {{varName}} = {{value}};",
            constant_declaration="public const {{Type}} {{ConstName}} = {{value}};",
            import_statement="using {{Namespace}};",
            test_function="[Fact]\npublic void Test{{MethodName}}()\n{\n\t// test code\n}"
        ),
        placeholder_format=PlaceholderFormat(
            pattern="{{{{{}}}}}",
            escape_char=None,
            reserved_words={"class", "interface", "public", "private", "static", "const", "if", "for", "return", "using"}
        ),
        naming_conventions={
            "class": "PascalCase",
            "interface": "PascalCase",
            "method": "PascalCase",
            "variable": "camelCase",
            "constant": "PascalCase"
        },
        indentation="spaces",
        typical_indent_size=4,
        statement_terminator=";"
    ),

    # Add more languages: PHP, Swift, Kotlin, Scala, Elixir, etc.
    # (abbreviated for brevity - actual implementation would have 50+)
}
```

### 2. Syntax Query Service

```python
# src/commands/template_create/syntax_service.py

class SyntaxService:
    """Service for querying language syntax"""

    @staticmethod
    def get_syntax(language: str) -> Optional[LanguageSyntax]:
        """Get syntax for a language"""
        return SYNTAX_DATABASE.get(language.lower())

    @staticmethod
    def get_comment_syntax(language: str) -> Optional[CommentSyntax]:
        """Get comment syntax for a language"""
        syntax = SyntaxService.get_syntax(language)
        return syntax.comments if syntax else None

    @staticmethod
    def generate_code_element(
        language: str,
        element_type: str,
        placeholders: Dict[str, str]
    ) -> Optional[str]:
        """
        Generate code element from template

        Args:
            language: Target language (e.g., "go", "rust")
            element_type: Type of element ("class", "function", etc.)
            placeholders: Dict of placeholder values

        Returns:
            Generated code string or None if language not supported
        """
        syntax = SyntaxService.get_syntax(language)
        if not syntax:
            return None

        # Get template for element type
        template = None
        if element_type == "class":
            template = syntax.patterns.class_definition
        elif element_type == "interface":
            template = syntax.patterns.interface_definition
        elif element_type == "function":
            template = syntax.patterns.function_definition
        elif element_type == "method":
            template = syntax.patterns.method_definition
        # ... etc

        if not template:
            return None

        # Replace placeholders
        code = template
        for key, value in placeholders.items():
            placeholder = syntax.placeholder_format.pattern.format(key)
            code = code.replace(placeholder, value)

        return code

    @staticmethod
    def get_file_extension(language: str) -> Optional[str]:
        """Get primary file extension for language"""
        syntax = SyntaxService.get_syntax(language)
        if not syntax or not syntax.file_extensions:
            return None

        # Return first (primary) extension
        return list(syntax.file_extensions)[0]

    @staticmethod
    def get_naming_convention(language: str, element_type: str) -> str:
        """Get recommended naming convention for element type"""
        syntax = SyntaxService.get_syntax(language)
        if not syntax:
            return "PascalCase"  # Default

        return syntax.naming_conventions.get(element_type, "PascalCase")
```

### 3. Template-Safe Placeholder Generator

```python
# src/commands/template_create/placeholder_generator.py

class PlaceholderGenerator:
    """Generate template-safe placeholders"""

    @staticmethod
    def create_placeholder_map(
        language: str,
        base_name: str
    ) -> Dict[str, str]:
        """
        Create placeholder map with proper casing for language

        Args:
            language: Target language
            base_name: Base name (e.g., "user")

        Returns:
            Dict of placeholders (e.g., {"ClassName": "User", "class_name": "user"})
        """
        syntax = SyntaxService.get_syntax(language)
        if not syntax:
            # Fallback
            return {
                "ClassName": base_name.title(),
                "class_name": base_name.lower(),
            }

        placeholders = {}

        # Apply naming conventions
        for element_type, convention in syntax.naming_conventions.items():
            if convention == "PascalCase":
                placeholders[f"{element_type.title()}Name"] = to_pascal_case(base_name)
            elif convention == "camelCase":
                placeholders[f"{element_type}Name"] = to_camel_case(base_name)
            elif convention == "snake_case":
                placeholders[f"{element_type}_name"] = to_snake_case(base_name)
            elif convention == "SCREAMING_SNAKE":
                placeholders[f"{element_type.upper()}_NAME"] = to_screaming_snake(base_name)

        return placeholders
```

## Testing Strategy

```python
# tests/test_syntax_database.py

def test_syntax_retrieval():
    """Test syntax retrieval for all languages"""
    for lang in ["go", "rust", "java", "python", "typescript", "ruby", "csharp"]:
        syntax = SyntaxService.get_syntax(lang)
        assert syntax is not None
        assert syntax.comments.single_line is not None
        assert syntax.patterns.class_definition is not None

def test_code_generation():
    """Test code element generation"""
    code = SyntaxService.generate_code_element(
        "go",
        "class",
        {"ClassName": "UserService"}
    )

    assert code is not None
    assert "UserService" in code
    assert "struct" in code

def test_placeholder_generation():
    """Test placeholder generation with proper casing"""
    placeholders = PlaceholderGenerator.create_placeholder_map("rust", "user")

    # Rust uses snake_case for functions
    assert "function_name" in placeholders
    # Rust uses PascalCase for structs
    assert "ClassName" in placeholders or "StructName" in placeholders
```

## Definition of Done

- [ ] Syntax database for 50+ languages implemented
- [ ] Comment syntax for all languages
- [ ] Code pattern templates for all languages
- [ ] Placeholder format specifications
- [ ] Naming convention mappings
- [ ] Syntax query service implemented
- [ ] Code generation from templates working
- [ ] Placeholder generator implemented
- [ ] Unit tests for syntax retrieval passing
- [ ] Documentation of syntax patterns
- [ ] Integration ready for TASK-045

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: HIGH

## Impact

Enables universal template generation:
- Syntax information for 50+ languages
- Template-safe placeholders
- Proper naming conventions per language
- Foundation for TASK-045 (template generation)
- Supports ANY technology stack
