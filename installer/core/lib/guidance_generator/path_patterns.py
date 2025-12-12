"""
Path pattern generation for guidance files.

Generates glob patterns based on agent metadata (stack, phase, capabilities).
This module is technology-agnostic - specific patterns come from agent/template
metadata, not hardcoded mappings.

Priority order:
1. Explicit 'paths' field in agent metadata (highest priority, direct passthrough)
2. Phase-based patterns (testing, database, api)
3. Capability-based patterns (generic concepts)
4. Stack-based patterns (language file extensions only)
"""

from typing import Any


# Stack to file extension mapping (language-agnostic - just file types)
STACK_PATTERNS = {
    "python": "**/*.py",
    "typescript": "**/*.{ts,tsx}",
    "javascript": "**/*.{js,jsx}",
    "dotnet": "**/*.cs",
    "csharp": "**/*.cs",
    "go": "**/*.go",
    "rust": "**/*.rs",
    "java": "**/*.java",
    "kotlin": "**/*.kt",
    "swift": "**/*.swift",
    "ruby": "**/*.rb",
    "php": "**/*.php",
}

# Phase to path pattern mapping (generic concepts, not technology-specific)
PHASE_PATTERNS = {
    "testing": "**/tests/**, **/test/**",
    "database": "**/models/**, **/repositories/**, **/db/**",
    "api": "**/api/**, **/routes/**, **/endpoints/**",
    "ui": "**/components/**, **/views/**, **/pages/**",
}

# Capability to path pattern mapping (generic concepts only)
CAPABILITY_PATTERNS = {
    "database": "**/models/**, **/repositories/**",
    "orm": "**/models/**",
    "testing": "**/tests/**",
    "api": "**/api/**",
    "routes": "**/routes/**",
    "components": "**/components/**",
    "views": "**/views/**",
    "controllers": "**/controllers/**",
    "services": "**/services/**",
}


def generate_path_patterns(metadata: dict[str, Any]) -> str:
    """
    Generate path patterns from agent metadata.

    This function is technology-agnostic. Specific path patterns should be
    defined in the agent's frontmatter 'paths' field, which takes priority
    over any generated patterns.

    Args:
        metadata: Agent metadata dict with optional keys:
            - 'paths': Explicit path patterns (highest priority, passthrough)
            - 'stack': List of technology stacks (for file extensions)
            - 'phase': Development phase (testing, database, api, ui)
            - 'capabilities': List of capability keywords

    Returns:
        Comma-separated path patterns, or empty string for cross-stack agents

    Examples:
        paths: "**/Repositories/**/*.cs" → **/Repositories/**/*.cs (passthrough)
        stack: [python] → **/*.py
        phase: testing → **/tests/**, **/test/**
        capabilities: [database] → **/models/**, **/repositories/**
    """
    if not metadata:
        return ""

    # Priority 0: Direct paths field (highest priority - passthrough)
    # This allows agents to define their own technology-specific patterns
    explicit_paths = metadata.get("paths", "")
    if explicit_paths:
        return explicit_paths

    stack = metadata.get("stack", [])
    phase = metadata.get("phase", "")
    capabilities = metadata.get("capabilities", [])

    # Handle cross-stack agents (no specific paths)
    if "cross-stack" in stack:
        return ""

    patterns = set()

    # Priority 1: Add patterns from phase
    if phase in PHASE_PATTERNS:
        patterns.add(PHASE_PATTERNS[phase])

    # Priority 2: Add patterns from capabilities
    for cap in capabilities:
        cap_lower = cap.lower() if isinstance(cap, str) else str(cap).lower()
        if cap_lower in CAPABILITY_PATTERNS:
            patterns.add(CAPABILITY_PATTERNS[cap_lower])

    # Priority 3: Add patterns from stack (file extensions only)
    if not patterns:
        for stack_item in stack:
            if stack_item in STACK_PATTERNS:
                patterns.add(STACK_PATTERNS[stack_item])

    # Final fallback: use primary stack's file extension
    if not patterns and stack:
        primary_stack = stack[0]
        if primary_stack in STACK_PATTERNS:
            patterns.add(STACK_PATTERNS[primary_stack])

    return ", ".join(sorted(patterns))
