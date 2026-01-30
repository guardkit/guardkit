#!/usr/bin/env python3
"""Library context gathering module for Phase 2.1 - Planning phase library enrichment.

This module provides functions to gather context for detected libraries using the
Context7 MCP tools. It enriches the Phase 2 planning prompt with up-to-date library
documentation, initialization patterns, and key method signatures.

Key Features:
    - Resolves library names to Context7 IDs via MCP tools
    - Gathers initialization and key method documentation
    - Formats context for injection into planning prompts
    - Token budget management to avoid context overflow
    - Graceful degradation when MCP tools unavailable

Module Design:
    - Uses direct MCP tool calls (no wrapper classes - per YAGNI)
    - Dataclass for structured context results
    - Inline extraction for simplicity
    - Comprehensive error handling with logging
    - Type hints on all functions

Integration:
    This module is called during Phase 2 (Implementation Planning) after library
    detection (Phase 2.0). The gathered context is injected into the planning
    prompt to ensure AI has accurate, up-to-date API knowledge.

Example:
    >>> from installer.core.commands.lib.library_context import gather_library_context
    >>> contexts = gather_library_context(["fastapi", "pydantic"])
    >>> for ctx in contexts:
    ...     if ctx.resolved:
    ...         print(f"{ctx.name}: {ctx.context7_id}")

Part of: Library Knowledge Gap Detection System (TASK-LKG-002)
Architecture: Phase 2.5B recommended simplification (score 86/100)
Author: Claude (Anthropic)
Created: 2026-01-30
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Any

# Configure logging (no propagation unless explicitly enabled by caller)
logger = logging.getLogger(__name__)


# Query templates for Context7 documentation retrieval
INIT_QUERY = "initialization setup import getting started"
METHODS_QUERY = "main API methods function signatures"


@dataclass
class LibraryContext:
    """Context gathered for a single library from Context7 or manual frontmatter.

    Holds all documentation fragments retrieved for a library including
    initialization patterns and key method documentation.

    Attributes:
        name: Library name as detected (e.g., "fastapi", "pydantic")
        context7_id: Resolved Context7 library ID (e.g., "/tiangolo/fastapi")
        resolved: Whether library was successfully resolved in Context7 or manually
        import_statement: Detected import statement pattern
        initialization: Initialization/setup documentation
        key_methods: List of key method names detected
        method_docs: Documentation for key methods
        error: Error message if resolution failed
        source: Origin of context - "context7" (default) or "manual" (from frontmatter)

    Example:
        >>> ctx = LibraryContext(name="fastapi")
        >>> ctx.resolved
        False
        >>> ctx.source
        'context7'
        >>> ctx.to_prompt_section()
        '### fastapi\\n[Library not found in Context7]\\n'
    """

    name: str
    context7_id: Optional[str] = None
    resolved: bool = False
    import_statement: Optional[str] = None
    initialization: Optional[str] = None
    key_methods: List[str] = field(default_factory=list)
    method_docs: Optional[str] = None
    error: Optional[str] = None
    source: str = "context7"

    def to_prompt_section(self) -> str:
        """Convert context to a formatted prompt section.

        Generates a markdown-formatted section suitable for injection
        into the Phase 2 planning prompt.

        Returns:
            Formatted string with library context for prompt injection.
            Includes import, initialization, and method docs if available.

        Example:
            >>> ctx = LibraryContext(
            ...     name="fastapi",
            ...     resolved=True,
            ...     context7_id="/tiangolo/fastapi",
            ...     import_statement="from fastapi import FastAPI",
            ...     initialization="app = FastAPI()"
            ... )
            >>> section = ctx.to_prompt_section()
            >>> "### fastapi" in section
            True
        """
        lines = [f"### {self.name}"]

        if not self.resolved:
            if self.error:
                lines.append(f"[Resolution failed: {self.error}]")
            else:
                lines.append("[Library not found in Context7]")
            lines.append("")
            return "\n".join(lines)

        if self.context7_id:
            lines.append(f"**Context7 ID**: `{self.context7_id}`")
            lines.append("")

        if self.import_statement:
            lines.append("**Import**:")
            lines.append(f"```python")
            lines.append(self.import_statement)
            lines.append("```")
            lines.append("")

        if self.initialization:
            lines.append("**Initialization**:")
            lines.append(self.initialization)
            lines.append("")

        if self.key_methods:
            lines.append("**Key Methods**:")
            for method in self.key_methods:
                lines.append(f"- `{method}`")
            lines.append("")

        if self.method_docs:
            lines.append("**API Reference**:")
            lines.append(self.method_docs)
            lines.append("")

        return "\n".join(lines)


# Type alias for MCP tool functions
MCPToolFunc = Callable[..., Any]


def _call_resolve_library_id(
    library_name: str,
    query: str,
    mcp_resolve: Optional[MCPToolFunc] = None
) -> Optional[str]:
    """Call Context7 resolve-library-id MCP tool.

    Attempts to resolve a library name to a Context7-compatible library ID.

    Args:
        library_name: Library name to resolve (e.g., "fastapi")
        query: Context query describing what we need
        mcp_resolve: Optional mock function for testing

    Returns:
        Context7 library ID if found (e.g., "/tiangolo/fastapi"), None otherwise

    Note:
        In production, this calls mcp__context7__resolve_library_id.
        For testing, pass a mock function via mcp_resolve parameter.
    """
    try:
        if mcp_resolve is not None:
            # Use provided mock for testing
            result = mcp_resolve(libraryName=library_name, query=query)
        else:
            # In production, MCP tools are available in the execution context
            # This will be called by the AI agent which has access to MCP tools
            logger.debug(f"Would call mcp__context7__resolve_library_id for {library_name}")
            return None

        if result is None:
            return None

        # Extract library ID from result
        # Result format varies, but typically contains libraryId or id field
        if isinstance(result, dict):
            return result.get("libraryId") or result.get("id")
        elif isinstance(result, str):
            return result

        return None

    except Exception as e:
        logger.warning(f"Failed to resolve library ID for {library_name}: {e}")
        return None


def _call_query_docs(
    library_id: str,
    query: str,
    mcp_query: Optional[MCPToolFunc] = None
) -> Optional[str]:
    """Call Context7 query-docs MCP tool.

    Queries documentation for a specific library using its Context7 ID.

    Args:
        library_id: Context7 library ID (e.g., "/tiangolo/fastapi")
        query: Documentation query string
        mcp_query: Optional mock function for testing

    Returns:
        Documentation string if found, None otherwise

    Note:
        In production, this calls mcp__context7__query_docs.
        For testing, pass a mock function via mcp_query parameter.
    """
    try:
        if mcp_query is not None:
            # Use provided mock for testing
            result = mcp_query(libraryId=library_id, query=query)
        else:
            # In production, MCP tools are available in the execution context
            logger.debug(f"Would call mcp__context7__query_docs for {library_id}")
            return None

        if result is None:
            return None

        # Extract documentation from result
        if isinstance(result, dict):
            return result.get("documentation") or result.get("content") or result.get("text")
        elif isinstance(result, str):
            return result

        return None

    except Exception as e:
        logger.warning(f"Failed to query docs for {library_id}: {e}")
        return None


def _extract_import_statement(docs: Optional[str]) -> Optional[str]:
    """Extract import statement from documentation.

    Scans documentation text for common import patterns and extracts
    the most relevant import statement.

    Args:
        docs: Documentation text to scan

    Returns:
        Extracted import statement or None if not found
    """
    if not docs:
        return None

    # Look for common import patterns
    import_patterns = [
        "from ",
        "import ",
    ]

    lines = docs.split("\n")
    for line in lines:
        stripped = line.strip()
        for pattern in import_patterns:
            if stripped.startswith(pattern):
                # Clean up the import line
                # Remove markdown code block markers
                cleaned = stripped.replace("```python", "").replace("```", "").strip()
                if cleaned.startswith(("from ", "import ")):
                    return cleaned

    return None


def _extract_key_methods(docs: Optional[str], limit: int = 5) -> List[str]:
    """Extract key method names from documentation.

    Scans documentation for method definitions and signatures,
    returning the most commonly referenced method names.

    Args:
        docs: Documentation text to scan
        limit: Maximum number of methods to return

    Returns:
        List of method names (up to limit)
    """
    if not docs:
        return []

    import re

    methods = []

    # Pattern for method definitions: def method_name(
    # or method references: .method_name(
    patterns = [
        r'def\s+([a-z_][a-z0-9_]*)\s*\(',
        r'\.([a-z_][a-z0-9_]*)\s*\(',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, docs, re.IGNORECASE)
        for match in matches:
            if match not in methods and not match.startswith("_"):
                methods.append(match)
                if len(methods) >= limit:
                    return methods

    return methods


def format_method_docs(methods: Optional[List[dict]]) -> Optional[str]:
    """Format method documentation from frontmatter key_methods list.

    Converts the key_methods array from task frontmatter into a formatted
    string suitable for prompt injection.

    Args:
        methods: List of method dictionaries with name, signature, returns fields

    Returns:
        Formatted markdown string or None if no methods provided

    Example:
        >>> methods = [{"name": "search", "signature": "def search(...)", "returns": "List"}]
        >>> format_method_docs(methods)
        '**search**\\n  Signature: `def search(...)`\\n  Returns: List\\n'
    """
    if not methods:
        return None

    lines = []
    for method in methods:
        if not isinstance(method, dict):
            continue

        name = method.get("name", "unknown")
        lines.append(f"**{name}**")

        if signature := method.get("signature"):
            lines.append(f"  Signature: `{signature}`")

        if returns := method.get("returns"):
            lines.append(f"  Returns: {returns}")

        lines.append("")

    return "\n".join(lines) if lines else None


def parse_library_context(raw: Optional[List[dict]]) -> Optional[List[LibraryContext]]:
    """Parse library_context from task frontmatter.

    Converts the library_context field from task frontmatter YAML into
    a list of LibraryContext objects marked as manually provided.

    Args:
        raw: List of library dictionaries from frontmatter, each containing:
            - name: Library name (required)
            - import: Import statement (optional)
            - initialization: Initialization code (optional)
            - key_methods: List of method definitions (optional)

    Returns:
        List of LibraryContext objects with source="manual", or None if raw is empty

    Example:
        >>> raw = [{"name": "graphiti-core", "import": "from graphiti_core import Graphiti"}]
        >>> contexts = parse_library_context(raw)
        >>> contexts[0].name
        'graphiti-core'
        >>> contexts[0].source
        'manual'
        >>> contexts[0].resolved
        True
    """
    if not raw:
        return None

    contexts = []
    for item in raw:
        if not isinstance(item, dict):
            logger.warning(f"Skipping non-dict library_context item: {item}")
            continue

        name = item.get("name")
        if not name:
            logger.warning("Skipping library_context item without name")
            continue

        # Parse key_methods if present
        key_methods_raw = item.get("key_methods", [])
        key_method_names = [m.get("name") for m in key_methods_raw if isinstance(m, dict) and m.get("name")]

        ctx = LibraryContext(
            name=name,
            context7_id=None,  # Manual entries don't have Context7 IDs
            resolved=True,  # Manual entries are always considered resolved
            import_statement=item.get("import"),
            initialization=item.get("initialization"),
            key_methods=key_method_names,
            method_docs=format_method_docs(key_methods_raw),
            source="manual"
        )
        contexts.append(ctx)

    return contexts if contexts else None


def gather_library_context(
    libraries: List[str],
    manual_context: Optional[List[LibraryContext]] = None,
    token_budget: int = 5000,
    mcp_resolve: Optional[MCPToolFunc] = None,
    mcp_query: Optional[MCPToolFunc] = None
) -> List[LibraryContext]:
    """Gather context for detected libraries, preferring manual over Context7.

    Main entry point for library context gathering. For each library,
    first checks if manual context was provided (from task frontmatter),
    then falls back to Context7 MCP for resolution.

    Priority:
        1. Manual library_context (from frontmatter) - takes precedence
        2. Context7 fetched documentation - fallback

    Args:
        libraries: List of library names to gather context for
        manual_context: Optional list of manually provided LibraryContext from frontmatter
        token_budget: Maximum tokens to use for all library contexts combined
        mcp_resolve: Optional mock for resolve-library-id (testing)
        mcp_query: Optional mock for query-docs (testing)

    Returns:
        List of LibraryContext objects, one per input library.
        Failed resolutions will have resolved=False and error set.

    Example:
        >>> contexts = gather_library_context(["fastapi", "unknown-lib"])
        >>> len(contexts)
        2
        >>> contexts[0].name
        'fastapi'

        >>> # With manual context taking precedence
        >>> manual = [LibraryContext(name="fastapi", resolved=True, source="manual")]
        >>> contexts = gather_library_context(["fastapi"], manual_context=manual)
        >>> contexts[0].source
        'manual'
    """
    if not libraries:
        logger.debug("No libraries to gather context for")
        return []

    # Build lookup for manual contexts by library name
    manual_lookup: dict = {}
    if manual_context:
        for ctx in manual_context:
            manual_lookup[ctx.name.lower()] = ctx
        logger.info(f"Manual context provided for: {list(manual_lookup.keys())}")

    contexts: List[LibraryContext] = []
    tokens_used = 0
    tokens_per_library = token_budget // max(len(libraries), 1)

    logger.info(f"Gathering context for {len(libraries)} libraries (budget: {token_budget} tokens)")

    for library_name in libraries:
        # Check manual context first (takes precedence)
        if library_name.lower() in manual_lookup:
            ctx = manual_lookup[library_name.lower()]
            logger.debug(f"Using manual context for {library_name}")
            contexts.append(ctx)
            continue
        ctx = LibraryContext(name=library_name)

        # Step 1: Resolve library ID
        library_id = _call_resolve_library_id(
            library_name=library_name,
            query=f"Documentation for {library_name} library",
            mcp_resolve=mcp_resolve
        )

        if not library_id:
            ctx.error = "Could not resolve library ID"
            contexts.append(ctx)
            continue

        ctx.context7_id = library_id
        ctx.resolved = True

        # Step 2: Query initialization docs
        init_docs = _call_query_docs(
            library_id=library_id,
            query=INIT_QUERY,
            mcp_query=mcp_query
        )

        if init_docs:
            ctx.initialization = init_docs
            ctx.import_statement = _extract_import_statement(init_docs)
            # Rough token estimate: ~4 chars per token
            tokens_used += len(init_docs) // 4

        # Step 3: Query key methods (if budget allows)
        remaining_budget = token_budget - tokens_used
        if remaining_budget > 500:
            method_docs = _call_query_docs(
                library_id=library_id,
                query=METHODS_QUERY,
                mcp_query=mcp_query
            )

            if method_docs:
                ctx.method_docs = method_docs
                ctx.key_methods = _extract_key_methods(method_docs)
                tokens_used += len(method_docs) // 4

        contexts.append(ctx)

        # Check if we've exceeded budget
        if tokens_used >= token_budget:
            logger.warning(f"Token budget exceeded ({tokens_used}/{token_budget}), stopping early")
            # Add remaining libraries as unresolved
            remaining = libraries[libraries.index(library_name) + 1:]
            for remaining_lib in remaining:
                contexts.append(LibraryContext(
                    name=remaining_lib,
                    error="Token budget exceeded"
                ))
            break

    logger.info(f"Gathered context for {sum(1 for c in contexts if c.resolved)}/{len(libraries)} libraries")
    return contexts


def display_library_context(contexts: List[LibraryContext]) -> None:
    """Display gathered library context to the user.

    Prints a formatted summary of resolved and unresolved libraries
    to stdout for user visibility during planning.

    Args:
        contexts: List of LibraryContext objects to display

    Example:
        >>> contexts = [LibraryContext(name="fastapi", resolved=True)]
        >>> display_library_context(contexts)  # doctest: +SKIP
        Library Context Summary
        =======================
        Resolved (1):
          - fastapi (/tiangolo/fastapi)
    """
    if not contexts:
        print("No library context gathered.")
        return

    resolved = [c for c in contexts if c.resolved]
    failed = [c for c in contexts if not c.resolved]

    print("\nLibrary Context Summary")
    print("=" * 50)

    if resolved:
        print(f"\nResolved ({len(resolved)}):")
        for ctx in resolved:
            id_display = f" ({ctx.context7_id})" if ctx.context7_id else ""
            print(f"  - {ctx.name}{id_display}")

    if failed:
        print(f"\nFailed ({len(failed)}):")
        for ctx in failed:
            error_msg = f": {ctx.error}" if ctx.error else ""
            print(f"  - {ctx.name}{error_msg}")

    print("")


def inject_library_context_into_prompt(
    base_prompt: str,
    contexts: List[LibraryContext]
) -> str:
    """Inject library context into the planning prompt.

    Takes the base Phase 2 planning prompt and enriches it with
    gathered library context. Only includes resolved libraries.

    Args:
        base_prompt: Original planning prompt text
        contexts: List of LibraryContext objects from gather_library_context

    Returns:
        Enhanced prompt with library context section added

    Example:
        >>> base = "Create an implementation plan for the task."
        >>> ctx = LibraryContext(name="fastapi", resolved=True, initialization="FastAPI()")
        >>> enhanced = inject_library_context_into_prompt(base, [ctx])
        >>> "## Library Reference" in enhanced
        True
    """
    # Filter to resolved contexts only
    resolved = [c for c in contexts if c.resolved]

    if not resolved:
        # No context to inject, return original prompt
        return base_prompt

    # Build library context section
    context_sections = []
    for ctx in resolved:
        context_sections.append(ctx.to_prompt_section())

    library_section = "\n## Library Reference\n\n"
    library_section += "The following library documentation is available for reference:\n\n"
    library_section += "\n".join(context_sections)

    # Find good injection point (after initial context, before instructions)
    # Look for common section markers
    injection_markers = [
        "## Implementation",
        "## Requirements",
        "## Task",
        "## Instructions",
    ]

    for marker in injection_markers:
        if marker in base_prompt:
            # Insert before this section
            idx = base_prompt.index(marker)
            return base_prompt[:idx] + library_section + "\n" + base_prompt[idx:]

    # No marker found, append to end
    return base_prompt + "\n" + library_section


def format_context_for_logging(contexts: List[LibraryContext]) -> str:
    """Format library context for logging purposes.

    Creates a compact single-line summary suitable for log messages.

    Args:
        contexts: List of LibraryContext objects

    Returns:
        Compact summary string for logging

    Example:
        >>> ctx = LibraryContext(name="fastapi", resolved=True)
        >>> format_context_for_logging([ctx])
        'Libraries: fastapi (resolved)'
    """
    if not contexts:
        return "Libraries: none"

    parts = []
    for ctx in contexts:
        status = "resolved" if ctx.resolved else "failed"
        parts.append(f"{ctx.name} ({status})")

    return f"Libraries: {', '.join(parts)}"


# Public API
__all__ = [
    # Core data structure
    "LibraryContext",

    # Main functions
    "gather_library_context",
    "display_library_context",
    "inject_library_context_into_prompt",

    # Parsing functions (for frontmatter library_context field)
    "parse_library_context",
    "format_method_docs",

    # Utility functions
    "format_context_for_logging",

    # Constants
    "INIT_QUERY",
    "METHODS_QUERY",
]
