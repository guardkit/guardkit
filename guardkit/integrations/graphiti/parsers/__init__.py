"""Parser infrastructure for Graphiti context addition.

This package provides a registry-based parser system for handling
different file types when adding context to Graphiti.
"""

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)
from guardkit.integrations.graphiti.parsers.feature_spec import FeatureSpecParser
from guardkit.integrations.graphiti.parsers.project_doc_parser import ProjectDocParser
from guardkit.integrations.graphiti.parsers.project_overview import ProjectOverviewParser
from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

__all__ = [
    "BaseParser",
    "EpisodeData",
    "FeatureSpecParser",
    "ParseResult",
    "ParserRegistry",
    "ProjectDocParser",
    "ProjectOverviewParser",
]
