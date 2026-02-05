"""Parser for full markdown document capture.

This parser captures the entire content of a markdown document as a single
episode (or multiple episodes for large documents). It's useful for:
- Research documents
- Project knowledge bases
- Design documents
- Any markdown file where full content capture is valuable

Unlike the project_doc parser which extracts specific sections, this parser
preserves the entire document content.
"""

import re
from pathlib import Path
from typing import Any

import frontmatter

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)


# Default chunk size threshold (10KB)
DEFAULT_CHUNK_THRESHOLD = 10 * 1024


class FullDocParser(BaseParser):
    """Parser that captures entire markdown document content.

    Creates episodes containing the full document content, with optional
    chunking for large documents (>10KB by default).

    This parser is explicit-only - it will not auto-detect files.
    Users must specify --type full_doc to use it.

    Attributes:
        chunk_threshold: Size in bytes above which documents are chunked.
            Default is 10KB.
    """

    def __init__(self, chunk_threshold: int = DEFAULT_CHUNK_THRESHOLD):
        """Initialize the parser.

        Args:
            chunk_threshold: Size threshold in bytes for chunking.
                Documents larger than this are split by top-level sections.
        """
        self._chunk_threshold = chunk_threshold

    @property
    def parser_type(self) -> str:
        """Return the unique parser type identifier.

        Returns:
            "full_doc"
        """
        return "full_doc"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            [".md", ".markdown"]
        """
        return [".md", ".markdown"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given content.

        This parser is explicit-only, so it always returns False.
        Users must specify --type full_doc to use this parser.

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            False (always - explicit parser only)
        """
        # This parser is explicit-only to avoid conflicts with other parsers
        return False

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse content and return episodes.

        Captures the entire document content. For documents larger than
        the chunk threshold, splits content by top-level sections (## headers).

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed (for context).

        Returns:
            ParseResult containing extracted episodes, warnings, and success status.
        """
        episodes: list[EpisodeData] = []
        warnings: list[str] = []

        # Handle empty content
        if not content or not content.strip():
            warnings.append("Empty content provided")
            return ParseResult(episodes=[], warnings=warnings, success=False)

        # Parse YAML frontmatter if present
        try:
            post = frontmatter.loads(content)
            markdown_content = post.content
            fm_metadata = post.metadata if post.metadata else {}
        except Exception as e:
            warnings.append(f"Error parsing YAML frontmatter: {e}")
            markdown_content = content
            fm_metadata = {}

        # Extract document title from first heading
        title = self._extract_title(markdown_content)
        if not title:
            title = Path(file_path).stem
            warnings.append("No title heading found, using filename as title")

        # Get file metadata
        file_size = len(content.encode("utf-8"))
        file_metadata = {
            "file_path": file_path,
            "file_size": file_size,
            "title": title,
        }

        # Include frontmatter if present
        if fm_metadata:
            file_metadata["frontmatter"] = fm_metadata

        # Decide whether to chunk based on size
        if file_size > self._chunk_threshold:
            # Chunk by top-level sections
            chunks = self._chunk_by_sections(markdown_content, title)
            if len(chunks) > 1:
                warnings.append(
                    f"Large document ({file_size} bytes) split into {len(chunks)} chunks"
                )
                for i, chunk in enumerate(chunks):
                    chunk_metadata = file_metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["chunk_total"] = len(chunks)
                    chunk_metadata["chunk_title"] = chunk["title"]

                    episodes.append(
                        self._create_episode(
                            content=chunk["content"],
                            file_path=file_path,
                            metadata=chunk_metadata,
                            chunk_suffix=f"_chunk_{i}",
                        )
                    )
            else:
                # Document too large but no sections to chunk by
                warnings.append(
                    f"Large document ({file_size} bytes) has no section headers for chunking"
                )
                episodes.append(
                    self._create_episode(
                        content=markdown_content,
                        file_path=file_path,
                        metadata=file_metadata,
                    )
                )
        else:
            # Single episode for the whole document
            episodes.append(
                self._create_episode(
                    content=markdown_content,
                    file_path=file_path,
                    metadata=file_metadata,
                )
            )

        return ParseResult(episodes=episodes, warnings=warnings, success=True)

    def _extract_title(self, content: str) -> str | None:
        """Extract document title from first heading.

        Args:
            content: Markdown content to search.

        Returns:
            Title text if found, None otherwise.
        """
        # Look for first # heading (single or double)
        match = re.search(r"^#{1,2}\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _chunk_by_sections(
        self, content: str, document_title: str
    ) -> list[dict[str, str]]:
        """Split content into chunks by top-level sections.

        Chunks are created at ## (h2) headers. Content before the first
        ## header is included in an "Introduction" chunk if present.

        Args:
            content: Markdown content to chunk.
            document_title: Title of the full document.

        Returns:
            List of dicts with 'title' and 'content' keys.
        """
        # Pattern for ## headers (h2 level)
        header_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)

        # Find all h2 headers and their positions
        matches = list(header_pattern.finditer(content))

        if not matches:
            # No h2 headers, return whole content
            return [{"title": document_title, "content": content}]

        chunks: list[dict[str, str]] = []

        # Check for content before first h2
        first_header_pos = matches[0].start()
        if first_header_pos > 0:
            intro_content = content[:first_header_pos].strip()
            if intro_content:
                chunks.append(
                    {
                        "title": f"{document_title} - Introduction",
                        "content": intro_content,
                    }
                )

        # Extract content for each h2 section
        for i, match in enumerate(matches):
            section_title = match.group(1).strip()
            start_pos = match.start()

            # Find end position (next header or end of content)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            section_content = content[start_pos:end_pos].strip()
            chunks.append(
                {
                    "title": f"{document_title} - {section_title}",
                    "content": section_content,
                }
            )

        return chunks

    def _create_episode(
        self,
        content: str,
        file_path: str,
        metadata: dict[str, Any],
        chunk_suffix: str = "",
    ) -> EpisodeData:
        """Create an EpisodeData instance for the document or chunk.

        Args:
            content: The content for the episode.
            file_path: Path to the source file.
            metadata: Metadata dictionary.
            chunk_suffix: Optional suffix for entity_id (for chunks).

        Returns:
            EpisodeData instance.
        """
        return EpisodeData(
            content=content,
            group_id="project_knowledge",
            entity_type="full_doc",
            entity_id=f"{file_path}{chunk_suffix}",
            metadata=metadata,
        )
