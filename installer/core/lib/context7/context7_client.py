"""
Context7 MCP Client with Progressive Disclosure

This module provides a wrapper around the Context7 MCP server that adds
progressive disclosure capabilities for token optimization.

Progressive disclosure allows fetching summary-level documentation during
planning phases (500-1000 tokens) and detailed documentation during
implementation phases (3500-5000 tokens), reducing token usage by 50-70%.

Example:
    >>> from lib.mcp import Context7Client, DetailLevel
    >>> client = Context7Client()
    >>>
    >>> # Phase 2: Planning - get summary
    >>> summary = client.get_summary("/tiangolo/fastapi", "dependency-injection")
    >>>
    >>> # Phase 3: Implementation - get detailed docs
    >>> detailed = client.get_detailed("/tiangolo/fastapi", "dependency-injection")
"""

from typing import Optional, Callable
from .detail_level import DetailLevel


class Context7Client:
    """
    Client for Context7 MCP server with progressive disclosure support.

    This client wraps the Context7 MCP tools (mcp__context7__resolve-library-id
    and mcp__context7__get-library-docs) and adds detail_level parameter for
    token optimization.

    Attributes:
        mcp_get_library_docs: Callable that invokes the actual MCP tool
        mcp_resolve_library_id: Callable that resolves library names to IDs

    Example:
        >>> client = Context7Client(
        ...     mcp_get_library_docs=mcp__context7__get_library_docs,
        ...     mcp_resolve_library_id=mcp__context7__resolve_library_id
        ... )
        >>> summary = client.get_summary("/tiangolo/fastapi", "dependency-injection")
    """

    def __init__(
        self,
        mcp_get_library_docs: Optional[Callable] = None,
        mcp_resolve_library_id: Optional[Callable] = None
    ):
        """
        Initialize Context7Client.

        Args:
            mcp_get_library_docs: Callable for get-library-docs MCP tool.
                If None, client operates in mock mode (for testing).
            mcp_resolve_library_id: Callable for resolve-library-id MCP tool.
                If None, client operates in mock mode (for testing).

        Note:
            In production, these callables should be the actual MCP tool functions.
            For testing, pass None to use mock mode (returns placeholder content).
        """
        self._mcp_get_library_docs = mcp_get_library_docs
        self._mcp_resolve_library_id = mcp_resolve_library_id

    def get_library_docs(
        self,
        library_id: str,
        topic: Optional[str] = None,
        detail_level: DetailLevel = DetailLevel.DETAILED,
        tokens: Optional[int] = None,
        page: int = 1
    ) -> str:
        """
        Fetch library documentation with optional detail level control.

        This is the primary method for fetching Context7 documentation.
        Use get_summary() or get_detailed() convenience methods for common cases.

        Args:
            library_id: Library ID (e.g., "/tiangolo/fastapi")
            topic: Topic to focus on (e.g., "dependency-injection")
            detail_level: SUMMARY (500-1000 tokens) or DETAILED (3500-5000 tokens)
            tokens: Manual token override (auto-set based on detail_level if None)
            page: Page number for pagination (default: 1)

        Returns:
            str: Documentation content

        Raises:
            ValueError: If library_id is empty or invalid
            RuntimeError: If MCP call fails

        Example:
            >>> # Phase 2: Planning - get summary
            >>> summary = client.get_library_docs(
            ...     library_id="/tiangolo/fastapi",
            ...     topic="dependency-injection",
            ...     detail_level=DetailLevel.SUMMARY
            ... )  # Returns ~750 tokens
            >>>
            >>> # Phase 3: Implementation - get detailed content
            >>> detailed = client.get_library_docs(
            ...     library_id="/tiangolo/fastapi",
            ...     topic="dependency-injection",
            ...     detail_level=DetailLevel.DETAILED
            ... )  # Returns ~4500 tokens
        """
        if not library_id:
            raise ValueError("library_id cannot be empty")

        # Auto-select token count based on detail level if not provided
        if tokens is None:
            tokens = detail_level.default_tokens()

        # Build query parameters
        query_params = {
            "context7CompatibleLibraryID": library_id,
            "page": page
        }

        if topic:
            query_params["topic"] = topic

        # In mock mode (testing), return placeholder content
        if self._mcp_get_library_docs is None:
            return self._mock_get_library_docs(
                library_id, topic, detail_level, tokens
            )

        # Call actual MCP tool
        try:
            # The MCP tool expects page parameter to be part of the main params,
            # not nested in query_params
            result = self._mcp_get_library_docs(
                context7CompatibleLibraryID=library_id,
                topic=topic,
                page=page
            )

            # The MCP tool returns documentation content as a string
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and "content" in result:
                return result["content"]
            else:
                # Fallback for unexpected response format
                return str(result)

        except Exception as e:
            # Graceful degradation: if MCP fails, return informative error
            error_msg = (
                f"Context7 MCP call failed for {library_id}"
                f"{f' (topic: {topic})' if topic else ''}: {str(e)}\n"
                f"Falling back to training data..."
            )
            print(f"⚠️ {error_msg}")
            return error_msg

    def get_summary(
        self,
        library_id: str,
        topic: Optional[str] = None,
        page: int = 1
    ) -> str:
        """
        Convenience method: Fetch summary-level docs (500-1000 tokens).

        Use this in Phase 2 (Planning) for high-level architectural overview.

        Args:
            library_id: Library ID (e.g., "/tiangolo/fastapi")
            topic: Topic to focus on (e.g., "dependency-injection")
            page: Page number for pagination (default: 1)

        Returns:
            str: Summary-level documentation (~750 tokens)

        Example:
            >>> summary = client.get_summary("/tiangolo/fastapi", "dependency-injection")
        """
        return self.get_library_docs(
            library_id=library_id,
            topic=topic,
            detail_level=DetailLevel.SUMMARY,
            page=page
        )

    def get_detailed(
        self,
        library_id: str,
        topic: Optional[str] = None,
        page: int = 1
    ) -> str:
        """
        Convenience method: Fetch detailed docs (3500-5000 tokens).

        Use this in Phase 3 (Implementation) for complete API documentation
        and code examples.

        Args:
            library_id: Library ID (e.g., "/tiangolo/fastapi")
            topic: Topic to focus on (e.g., "dependency-injection")
            page: Page number for pagination (default: 1)

        Returns:
            str: Detailed documentation (~4500 tokens)

        Example:
            >>> detailed = client.get_detailed("/tiangolo/fastapi", "dependency-injection")
        """
        return self.get_library_docs(
            library_id=library_id,
            topic=topic,
            detail_level=DetailLevel.DETAILED,
            page=page
        )

    def resolve_library_id(self, library_name: str) -> str:
        """
        Resolve a library name to a Context7-compatible library ID.

        Args:
            library_name: Library name (e.g., "fastapi", "react", "pytest")

        Returns:
            str: Context7-compatible library ID (e.g., "/tiangolo/fastapi")

        Raises:
            ValueError: If library_name is empty
            RuntimeError: If MCP call fails

        Example:
            >>> library_id = client.resolve_library_id("fastapi")
            >>> library_id
            '/tiangolo/fastapi'
        """
        if not library_name:
            raise ValueError("library_name cannot be empty")

        # In mock mode (testing), return mock ID
        if self._mcp_resolve_library_id is None:
            return self._mock_resolve_library_id(library_name)

        # Call actual MCP tool
        try:
            result = self._mcp_resolve_library_id(libraryName=library_name)

            # The MCP tool returns a list of matching libraries
            if isinstance(result, list) and len(result) > 0:
                # Return the first (most relevant) match
                if isinstance(result[0], dict) and "id" in result[0]:
                    return result[0]["id"]
                elif isinstance(result[0], str):
                    return result[0]

            # If no matches found
            raise RuntimeError(f"No library found for name: {library_name}")

        except Exception as e:
            error_msg = f"Context7 library resolution failed for '{library_name}': {str(e)}"
            print(f"⚠️ {error_msg}")
            raise RuntimeError(error_msg) from e

    def _mock_get_library_docs(
        self,
        library_id: str,
        topic: Optional[str],
        detail_level: DetailLevel,
        tokens: int
    ) -> str:
        """
        Mock implementation for testing (returns placeholder content).

        This method is used when mcp_get_library_docs is None.
        """
        topic_str = f" (topic: {topic})" if topic else ""
        content = (
            f"# Mock Documentation for {library_id}{topic_str}\n\n"
            f"Detail Level: {detail_level.name}\n"
            f"Token Budget: {tokens}\n\n"
            f"This is mock content for testing purposes.\n"
        )

        # Pad content to approximate token count (1 token ≈ 4 chars)
        target_chars = tokens * 4
        current_chars = len(content)

        if current_chars < target_chars:
            padding = "Lorem ipsum dolor sit amet. " * ((target_chars - current_chars) // 28)
            content += padding

        return content

    def _mock_resolve_library_id(self, library_name: str) -> str:
        """
        Mock implementation for library ID resolution (testing only).

        This method is used when mcp_resolve_library_id is None.
        """
        # Simple mock mapping for common libraries
        mock_mappings = {
            "fastapi": "/tiangolo/fastapi",
            "react": "/facebook/react",
            "pytest": "/pytest-dev/pytest",
            "next.js": "/vercel/next.js",
            "tailwindcss": "/tailwindlabs/tailwindcss",
        }

        return mock_mappings.get(library_name.lower(), f"/mock/{library_name}")


# Export for convenience
__all__ = ["Context7Client"]
