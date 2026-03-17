"""Parser for YAML document capture.

This parser captures YAML files (e.g., assumptions.yaml, config files)
as Graphiti episodes. It converts YAML content to a readable text
representation suitable for knowledge graph ingestion.
"""

from pathlib import Path
from typing import Any

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)


class YAMLParser(BaseParser):
    """Parser that captures YAML document content.

    Creates episodes from YAML files, converting structured data
    into text episodes suitable for Graphiti ingestion.

    Supports .yaml and .yml extensions.
    """

    @property
    def parser_type(self) -> str:
        return "yaml"

    @property
    def supported_extensions(self) -> list[str]:
        return [".yaml", ".yml"]

    def can_parse(self, content: str, file_path: str) -> bool:
        if not file_path:
            return False
        lower_path = file_path.lower()
        return lower_path.endswith(".yaml") or lower_path.endswith(".yml")

    def parse(self, content: str, file_path: str) -> ParseResult:
        episodes: list[EpisodeData] = []
        warnings: list[str] = []

        if not content or not content.strip():
            warnings.append("Empty content provided")
            return ParseResult(episodes=[], warnings=warnings, success=False)

        # Use the filename as the title
        title = Path(file_path).stem

        file_size = len(content.encode("utf-8"))
        metadata: dict[str, Any] = {
            "file_path": file_path,
            "file_size": file_size,
            "title": title,
            "format": "yaml",
        }

        # Wrap YAML content with context for the LLM to process
        episode_content = (
            f"# {title}\n\n"
            f"Source: {file_path}\n\n"
            f"```yaml\n{content}\n```"
        )

        episodes.append(
            EpisodeData(
                content=episode_content,
                group_id="project_knowledge",
                entity_type="yaml_doc",
                entity_id=file_path,
                metadata=metadata,
            )
        )

        return ParseResult(episodes=episodes, warnings=warnings, success=True)
