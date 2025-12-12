"""
Path pattern generation for guidance files.

Generates glob patterns based on agent stack and capabilities metadata.
"""

from typing import Any


# Stack to path pattern mapping
STACK_PATTERNS = {
    "python": "**/*.py",
    "typescript": "**/*.{ts,tsx}",
    "react": "**/*.tsx, **/components/**",
    "fastapi": "**/api/**/*.py",
    "nextjs": "**/*.{ts,tsx}, **/app/**",
    "dotnet": "**/*.cs",
    "javascript": "**/*.{js,jsx}",
}

# Phase to path pattern mapping
PHASE_PATTERNS = {
    "testing": "**/tests/**, **/test_*.py, **/*.test.{ts,tsx}",
    "database": "**/models/**, **/repositories/**",
    "api": "**/api/**, **/routes/**",
}

# Capability to path pattern mapping
CAPABILITY_PATTERNS = {
    "database": "**/models/**, **/repositories/**",
    "orm": "**/models/**",
    "testing": "**/tests/**",
    "api": "**/api/**",
    "routes": "**/routes/**",
    "components": "**/components/**",
}


def generate_path_patterns(metadata: dict[str, Any]) -> str:
    """
    Generate path patterns from agent stack and capabilities.

    Args:
        metadata: Agent metadata dict with 'stack', 'phase', 'capabilities' keys

    Returns:
        Comma-separated path patterns, or empty string for cross-stack agents

    Examples:
        stack: python, fastapi → paths: **/api/**/*.py
        stack: react, typescript → paths: **/*.tsx, **/components/**
        phase: testing → paths: **/tests/**
    """
    if not metadata:
        return ""

    stack = metadata.get("stack", [])
    phase = metadata.get("phase", "")
    capabilities = metadata.get("capabilities", [])

    # Handle cross-stack agents (no specific paths)
    if "cross-stack" in stack:
        return ""

    patterns = set()

    # Add patterns from stack
    for stack_item in stack:
        if stack_item in STACK_PATTERNS:
            patterns.add(STACK_PATTERNS[stack_item])

    # Add patterns from phase
    if phase in PHASE_PATTERNS:
        patterns.add(PHASE_PATTERNS[phase])

    # Add patterns from capabilities
    for cap in capabilities:
        if cap in CAPABILITY_PATTERNS:
            patterns.add(CAPABILITY_PATTERNS[cap])

    # If we still have no patterns but have a stack, use generic for that stack
    if not patterns and stack:
        primary_stack = stack[0]
        if primary_stack in STACK_PATTERNS:
            patterns.add(STACK_PATTERNS[primary_stack])

    return ", ".join(sorted(patterns))
