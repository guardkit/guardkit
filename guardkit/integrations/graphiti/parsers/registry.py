"""Parser registry for managing content parsers.

This module provides the ParserRegistry class for registering,
retrieving, and auto-detecting content parsers.
"""

from pathlib import Path
from typing import Optional

from guardkit.integrations.graphiti.parsers.base import BaseParser


class ParserRegistry:
    """Registry for content parsers.

    The registry maintains a collection of parsers and provides
    methods for:
    - Registering new parsers
    - Retrieving parsers by type name
    - Auto-detecting the appropriate parser for a file

    Example:
        >>> registry = ParserRegistry()
        >>> registry.register(MarkdownParser())
        >>> registry.register(TaskParser())
        >>>
        >>> # Get by type
        >>> parser = registry.get_parser("markdown")
        >>>
        >>> # Auto-detect
        >>> parser = registry.detect_parser("README.md", "# Title")
    """

    def __init__(self) -> None:
        """Initialize an empty parser registry."""
        self._parsers: dict[str, BaseParser] = {}
        self._extension_map: dict[str, str] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser with the registry.

        The parser will be stored by its type name, and extension
        mappings will be created for all supported extensions.

        Args:
            parser: The parser to register.

        Note:
            If a parser with the same type already exists, it will
            be replaced. Extension mappings are also overwritten.
        """
        self._parsers[parser.parser_type] = parser
        for ext in parser.supported_extensions:
            # Store extensions in lowercase for case-insensitive matching
            self._extension_map[ext.lower()] = parser.parser_type

    def get_parser(self, parser_type: Optional[str]) -> Optional[BaseParser]:
        """Get a parser by its type name.

        Args:
            parser_type: The type identifier of the parser to retrieve.

        Returns:
            The parser if found, None otherwise.
        """
        if parser_type is None:
            return None
        return self._parsers.get(parser_type)

    def detect_parser(
        self,
        file_path: str,
        content: str,
    ) -> Optional[BaseParser]:
        """Auto-detect the appropriate parser for a file.

        Detection follows this strategy:
        1. Try to find a parser by file extension
        2. Verify the parser can handle the content with can_parse()
        3. If no extension match, try all parsers via can_parse()

        Args:
            file_path: Path to the file (used for extension detection).
            content: The file content (used for content-based detection).

        Returns:
            The detected parser if found, None if no suitable parser.
        """
        # Handle empty file path
        if not file_path:
            return self._try_all_parsers(content, file_path)

        # Extract extension (case-insensitive)
        ext = Path(file_path).suffix.lower()

        # Strategy 1: Try extension mapping
        if ext in self._extension_map:
            parser_type = self._extension_map[ext]
            parser = self._parsers.get(parser_type)
            if parser and parser.can_parse(content, file_path):
                return parser

        # Strategy 2: Try all parsers via can_parse
        return self._try_all_parsers(content, file_path)

    def _try_all_parsers(
        self,
        content: str,
        file_path: str,
    ) -> Optional[BaseParser]:
        """Try all registered parsers via their can_parse method.

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            The first parser that can handle the content, None if none found.
        """
        for parser in self._parsers.values():
            if parser.can_parse(content, file_path):
                return parser
        return None
