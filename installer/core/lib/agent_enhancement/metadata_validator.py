"""
Metadata Validator for Agent Enhancement.

Provides validation and normalization of agent discovery metadata,
specifically handling stack value normalization and library detection.

TASK-META-FIX: Fix agent stack metadata validation warnings.
"""

from typing import List, Tuple, Set
import logging

logger = logging.getLogger(__name__)

# Valid stack values (from agent_discovery.py)
VALID_STACKS: Set[str] = {
    # Core languages
    'python', 'javascript', 'typescript', 'csharp', 'java',
    'go', 'rust', 'ruby', 'php', 'swift', 'kotlin', 'dart',

    # Frameworks/Platforms
    'react', 'dotnet', 'maui', 'flutter',

    # Technologies
    'xaml', 'realm',

    # Meta
    'cross-stack'
}

# Stack normalizations for common variations
STACK_NORMALIZATIONS = {
    'dotnet-maui': 'maui',
    'dotnet-core': 'dotnet',
    'dotnet-xaml': 'xaml',
    'react-native': 'react',
    'c#': 'csharp',
    '.net': 'dotnet',
    'node': 'javascript',
    'nodejs': 'javascript',
    'node.js': 'javascript',
    'ts': 'typescript',
    'js': 'javascript',
    'py': 'python',
}

# Library/package names that should NOT be in stack (belong in keywords)
LIBRARY_NOT_STACK: Set[str] = {
    # Error handling libraries
    'erroror', 'error-or', 'result',

    # Testing libraries
    'nsubstitute', 'xunit', 'nunit', 'mstest',
    'pytest', 'vitest', 'jest', 'mocha', 'jasmine',

    # API libraries
    'fastapi', 'flask', 'django', 'express', 'nestjs',

    # Database/ORM libraries
    'sqlalchemy', 'entity-framework', 'ef-core',
    'prisma', 'sequelize', 'typeorm',

    # State management
    'redux', 'zustand', 'mobx', 'recoil',
    'react-query', 'tanstack-query',

    # Mobile
    'realm-db', 'sqlite',

    # Other common libraries
    'pydantic', 'zod', 'axios', 'lodash',
}


def validate_stack(stack: List[str]) -> Tuple[List[str], List[str]]:
    """
    Validate and normalize stack values.

    Args:
        stack: List of stack values from agent metadata

    Returns:
        Tuple of (normalized_stack, warnings)
        - normalized_stack: Cleaned list with valid values only
        - warnings: List of warning messages for invalid/normalized values

    Examples:
        >>> validate_stack(['dotnet-maui', 'csharp'])
        (['maui', 'csharp'], ["Normalized 'dotnet-maui' to 'maui'"])

        >>> validate_stack(['Python', 'erroror'])
        (['python'], ["'erroror' is a library, moved to keywords"])
    """
    if not stack:
        return [], []

    normalized = []
    warnings = []
    libraries_found = []

    for item in stack:
        if not isinstance(item, str):
            warnings.append(f"Skipped non-string value: {item}")
            continue

        item_lower = item.lower().strip()

        # Check for normalization needed (compound names, aliases)
        if item_lower in STACK_NORMALIZATIONS:
            normalized_value = STACK_NORMALIZATIONS[item_lower]
            normalized.append(normalized_value)
            warnings.append(f"Normalized '{item}' to '{normalized_value}'")

        # Check if library mistakenly in stack
        elif item_lower in LIBRARY_NOT_STACK:
            libraries_found.append(item)
            warnings.append(f"'{item}' is a library, not a stack - moved to keywords")
            # Don't add to normalized stack

        # Check if valid stack value
        elif item_lower in VALID_STACKS:
            normalized.append(item_lower)

        # Unknown value - keep but warn
        else:
            warnings.append(f"Unknown stack value '{item}' - consider using keywords instead")
            normalized.append(item_lower)

    return normalized, warnings


def is_library(value: str) -> bool:
    """
    Check if a value is a library name rather than a stack.

    Args:
        value: Value to check

    Returns:
        True if value is a known library name

    Examples:
        >>> is_library('erroror')
        True
        >>> is_library('python')
        False
    """
    if not isinstance(value, str):
        return False
    return value.lower().strip() in LIBRARY_NOT_STACK


def normalize_stack_value(value: str) -> Tuple[str, bool]:
    """
    Normalize a single stack value.

    Args:
        value: Stack value to normalize

    Returns:
        Tuple of (normalized_value, was_normalized)

    Examples:
        >>> normalize_stack_value('dotnet-maui')
        ('maui', True)
        >>> normalize_stack_value('python')
        ('python', False)
    """
    if not isinstance(value, str):
        return str(value), False

    value_lower = value.lower().strip()

    if value_lower in STACK_NORMALIZATIONS:
        return STACK_NORMALIZATIONS[value_lower], True

    return value_lower, value_lower != value


def extract_libraries_from_stack(stack: List[str]) -> Tuple[List[str], List[str]]:
    """
    Extract library names from stack list.

    Args:
        stack: List of stack values

    Returns:
        Tuple of (clean_stack, libraries)
        - clean_stack: Stack list with libraries removed
        - libraries: List of library names found

    Examples:
        >>> extract_libraries_from_stack(['python', 'erroror', 'fastapi'])
        (['python'], ['erroror', 'fastapi'])
    """
    clean_stack = []
    libraries = []

    for item in stack:
        if is_library(item):
            libraries.append(item.lower().strip())
        else:
            clean_stack.append(item)

    return clean_stack, libraries


def post_process_metadata(metadata: dict) -> Tuple[dict, List[str]]:
    """
    Post-process metadata to fix common issues.

    This function:
    1. Normalizes stack values (e.g., dotnet-maui → maui)
    2. Moves library names from stack to keywords
    3. Returns warnings for any changes made

    Args:
        metadata: Enhancement metadata dictionary

    Returns:
        Tuple of (fixed_metadata, warnings)

    Examples:
        >>> metadata = {'stack': ['dotnet-maui', 'erroror']}
        >>> fixed, warnings = post_process_metadata(metadata)
        >>> fixed['stack']
        ['maui']
        >>> 'erroror' in fixed.get('keywords', [])
        True
    """
    if not metadata:
        return metadata, []

    warnings = []
    result = metadata.copy()

    # Process stack field
    if 'stack' in result and isinstance(result['stack'], list):
        original_stack = result['stack']

        # Step 1: Extract libraries FIRST from original stack (before normalization removes them)
        stack_without_libs, libraries = extract_libraries_from_stack(original_stack)

        # Step 2: Normalize remaining stack values
        normalized_stack, normalize_warnings = validate_stack(stack_without_libs)
        warnings.extend(normalize_warnings)

        # Update stack with normalized values
        result['stack'] = normalized_stack

        # Move libraries to keywords
        if libraries:
            keywords = result.get('keywords', [])
            if not isinstance(keywords, list):
                keywords = []

            for lib in libraries:
                if lib not in keywords:
                    keywords.append(lib)
                    warnings.append(f"'{lib}' is a library, moved from stack to keywords")

            result['keywords'] = keywords

    return result, warnings
