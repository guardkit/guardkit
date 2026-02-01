"""Parser infrastructure for Graphiti context addition.

This package provides a registry-based parser system for handling
different file types when adding context to Graphiti.
"""

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

__all__ = [
    "BaseParser",
    "EpisodeData",
    "ParseResult",
    "ParserRegistry",
]
