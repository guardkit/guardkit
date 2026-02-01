"""Base classes for content parsers.

This module defines the abstract base class for parsers and the
data structures used for parse results.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class EpisodeData:
    """Data for a single episode to be added to Graphiti.

    An episode represents a unit of knowledge that will be stored
    in the Graphiti knowledge graph.

    Attributes:
        content: The text content of the episode.
        group_id: Identifier for grouping related episodes.
        entity_type: Type of entity this episode represents.
        entity_id: Unique identifier for the entity.
        metadata: Additional metadata associated with the episode.
    """

    content: str
    group_id: str
    entity_type: str
    entity_id: str
    metadata: dict[str, Any]


@dataclass
class ParseResult:
    """Result of parsing a file.

    Contains the parsed episodes, any warnings generated during
    parsing, and a success indicator.

    Attributes:
        episodes: List of EpisodeData extracted from the file.
        warnings: List of warning messages generated during parsing.
        success: Whether parsing completed successfully.
    """

    episodes: list[EpisodeData]
    warnings: list[str]
    success: bool


class BaseParser(ABC):
    """Abstract base class for content parsers.

    All parsers must implement this interface to be usable with
    the ParserRegistry.

    Subclasses must implement:
        - parser_type: Unique identifier for the parser type
        - supported_extensions: List of file extensions this parser handles
        - parse: Parse content and return episodes
        - can_parse: Check if this parser can handle given content

    Example:
        >>> class MarkdownParser(BaseParser):
        ...     @property
        ...     def parser_type(self) -> str:
        ...         return "markdown"
        ...
        ...     @property
        ...     def supported_extensions(self) -> list[str]:
        ...         return [".md", ".markdown"]
        ...
        ...     def parse(self, content: str, file_path: str) -> ParseResult:
        ...         # Parse markdown content
        ...         ...
        ...
        ...     def can_parse(self, content: str, file_path: str) -> bool:
        ...         return file_path.endswith((".md", ".markdown"))
    """

    @property
    @abstractmethod
    def parser_type(self) -> str:
        """Return the unique parser type identifier.

        Returns:
            A string identifier for this parser type (e.g., "markdown", "task").
        """
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of file extensions this parser handles (e.g., [".md", ".markdown"]).
            Extensions should include the leading dot.
        """
        pass

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse content and return episodes.

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed (for context).

        Returns:
            ParseResult containing extracted episodes, warnings, and success status.
        """
        pass

    @abstractmethod
    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given content.

        This method should perform a quick check to determine if
        this parser is appropriate for the given content. It may
        check file extension, content markers, or structure.

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            True if this parser can handle the content, False otherwise.
        """
        pass
