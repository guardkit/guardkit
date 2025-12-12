"""Code style rules generator."""

from pathlib import Path
from typing import Dict, Optional


def generate_code_style_rules(language: str) -> str:
    """
    Generate language-specific code style rules.

    Args:
        language: Programming language (e.g., "python", "typescript", "javascript")

    Returns:
        Markdown content for code-style.md with paths frontmatter
    """
    templates = {
        "python": _python_template,
        "typescript": _typescript_template,
        "javascript": _javascript_template,
        "csharp": _csharp_template,
        "java": _java_template,
    }

    template_func = templates.get(language.lower(), _generic_template)
    return template_func(language)


def _python_template(language: str) -> str:
    """Python code style template."""
    return """---
paths: **/*.py
---

# Python Code Style

## Formatting

- Use Black for code formatting (line length: 88)
- Use isort for import sorting
- Follow PEP 8 style guidelines

## Type Hints

- Add type hints to all function signatures
- Use `typing` module for complex types
- Enable strict mypy checking

## Imports

- Group imports: standard library, third-party, local
- Use absolute imports over relative imports
- Avoid wildcard imports (`from module import *`)

## Naming Conventions

- `snake_case` for functions, variables, modules
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Private members prefix with `_`

## Documentation

- Use docstrings for all public functions/classes
- Follow Google or NumPy docstring format
- Include type information in docstrings

## Best Practices

- Prefer list comprehensions over map/filter
- Use context managers (`with` statement) for resources
- Avoid mutable default arguments
- Use `pathlib.Path` instead of `os.path`
"""


def _typescript_template(language: str) -> str:
    """TypeScript code style template."""
    return """---
paths: **/*.{ts,tsx}
---

# TypeScript Code Style

## Formatting

- Use Prettier for code formatting
- 2-space indentation
- Single quotes for strings
- Semicolons required

## Type Safety

- Enable strict mode in tsconfig.json
- Avoid `any` type - use `unknown` instead
- Use type inference where possible
- Define interfaces for object shapes

## Naming Conventions

- `camelCase` for variables and functions
- `PascalCase` for classes, interfaces, types
- `UPPER_CASE` for constants
- Prefix interfaces with `I` (optional)

## Imports

- Use ES6 import/export syntax
- Group imports: external, internal, types
- Use index files for cleaner imports

## React-Specific (if applicable)

- Functional components over class components
- Use hooks for state and lifecycle
- Props interface for component props
- `FC` type for functional components

## Best Practices

- Use `const` by default, `let` when needed
- Prefer template literals over string concatenation
- Use optional chaining (`?.`) and nullish coalescing (`??`)
- Destructure objects and arrays
"""


def _javascript_template(language: str) -> str:
    """JavaScript code style template."""
    return """---
paths: **/*.{js,jsx}
---

# JavaScript Code Style

## Formatting

- Use Prettier for code formatting
- 2-space indentation
- Single quotes for strings
- Semicolons required

## ES6+ Features

- Use `const` and `let` instead of `var`
- Use arrow functions for callbacks
- Use template literals for string interpolation
- Use destructuring for objects and arrays

## Naming Conventions

- `camelCase` for variables and functions
- `PascalCase` for classes and constructors
- `UPPER_CASE` for constants

## Imports

- Use ES6 import/export syntax
- Group imports logically
- Avoid default exports for utilities

## Best Practices

- Use strict mode (`'use strict'`)
- Avoid global variables
- Use `===` over `==`
- Handle errors properly (try/catch)
- Use async/await over promises chains
"""


def _csharp_template(language: str) -> str:
    """C# code style template."""
    return """---
paths: **/*.cs
---

# C# Code Style

## Formatting

- Use Visual Studio/Rider formatter
- 4-space indentation
- Opening braces on new line (Allman style)

## Naming Conventions

- `PascalCase` for classes, methods, properties
- `camelCase` for local variables, parameters
- `_camelCase` for private fields
- `IPascalCase` for interfaces

## Type Usage

- Use `var` when type is obvious
- Prefer explicit types for clarity
- Use nullable reference types

## Best Practices

- Use LINQ for collection operations
- Async/await for asynchronous code
- Dispose pattern for resources (`IDisposable`)
- Use dependency injection
"""


def _java_template(language: str) -> str:
    """Java code style template."""
    return """---
paths: **/*.java
---

# Java Code Style

## Formatting

- 4-space indentation
- Opening braces on same line
- One class per file

## Naming Conventions

- `PascalCase` for classes, interfaces
- `camelCase` for methods, variables
- `UPPER_CASE` for constants
- Interface names without `I` prefix

## Best Practices

- Use streams for collection operations
- Try-with-resources for autocloseable
- Prefer immutability where possible
- Use Optional for nullable values
"""


def _generic_template(language: str) -> str:
    """Generic code style template for unknown languages."""
    return f"""---
paths: **/*.{language}
---

# {language.title()} Code Style

## General Guidelines

- Follow language-specific conventions
- Use consistent formatting throughout
- Write clear, self-documenting code
- Add comments for complex logic

## Best Practices

- Keep functions small and focused
- Use meaningful variable names
- Avoid deep nesting
- Handle errors appropriately
- Write tests for your code
"""
