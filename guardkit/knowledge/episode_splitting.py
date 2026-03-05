"""Content-aware episode splitting for Graphiti knowledge seeding.

Large episodes (e.g., project_architecture, complex rules) trigger expensive
Phase 4 edge resolution in graphiti-core (O(edges x graph_size)). This module
splits large content at markdown section boundaries so each episode contributes
fewer edges per call.

Splitting strategy:
- Content <= max_chars: returned as-is in a single chunk
- Content > max_chars: split at ``## `` heading boundaries
- Sections larger than max_chars are kept whole (no mid-section breaks)
- Adjacent small sections are merged to minimise total chunk count

Usage::

    from guardkit.knowledge.episode_splitting import split_episode_content

    chunks = split_episode_content(content)
    for chunk in chunks:
        await client.add_episode(
            name=f"my_episode_chunk{chunk.chunk_index}",
            episode_body=json.dumps({
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
            }),
            group_id="project_overview",
        )
"""

import re
from dataclasses import dataclass
from typing import List

MAX_EPISODE_CHARS = 2000


@dataclass
class EpisodeChunk:
    """A chunk of episode content with positional metadata.

    Attributes:
        content: The markdown text for this chunk.
        chunk_index: 1-based position of this chunk within the full episode.
        total_chunks: Total number of chunks the episode was split into.
    """

    content: str
    chunk_index: int
    total_chunks: int


def split_episode_content(
    content: str,
    max_chars: int = MAX_EPISODE_CHARS,
) -> List[EpisodeChunk]:
    """Split large episode content into smaller chunks at markdown section boundaries.

    If *content* is at or under *max_chars*, a single :class:`EpisodeChunk` is
    returned (chunk_index=1, total_chunks=1).  Otherwise the content is split at
    ``## `` heading boundaries and adjacent sections are greedily merged to keep
    each chunk close to *max_chars*.

    A section that on its own exceeds *max_chars* is included as-is without
    further splitting — mid-section breaks would destroy readability.

    Args:
        content: The markdown content to potentially split.
        max_chars: Maximum characters per chunk.  Defaults to
            :data:`MAX_EPISODE_CHARS` (2000).

    Returns:
        A non-empty list of :class:`EpisodeChunk` instances.  At minimum one
        chunk is always returned even for empty content.

    Examples::

        >>> chunks = split_episode_content("# Title\\n\\nShort content.")
        >>> len(chunks)
        1
        >>> chunks[0].chunk_index
        1
        >>> chunks[0].total_chunks
        1
    """
    # Guard against None
    if not content:
        return [EpisodeChunk(content=content or "", chunk_index=1, total_chunks=1)]

    # Fast path: content fits in a single chunk
    if len(content) <= max_chars:
        return [EpisodeChunk(content=content, chunk_index=1, total_chunks=1)]

    # Split at ## headings, keeping the heading with its section body
    # Pattern explanation:
    #   (?=^## )  — positive look-ahead for a line starting with "## "
    # We use re.MULTILINE so ^ matches the start of every line.
    raw_sections = re.split(r"(?m)(?=^## )", content)

    # Filter out empty strings from the split
    sections: List[str] = [s for s in raw_sections if s]

    # If there are no ## headings (or only one section after split), return as-is
    if len(sections) <= 1:
        return [EpisodeChunk(content=content, chunk_index=1, total_chunks=1)]

    # Greedy merge: accumulate sections into chunks, flushing when adding
    # the next section would exceed max_chars.
    raw_chunks: List[str] = []
    current_parts: List[str] = []
    current_len: int = 0

    for section in sections:
        section_len = len(section)

        if not current_parts:
            # Always start a new chunk with the first section
            current_parts.append(section)
            current_len = section_len
        elif current_len + section_len <= max_chars:
            # Merge into current chunk
            current_parts.append(section)
            current_len += section_len
        else:
            # Flush current chunk and start fresh
            raw_chunks.append("".join(current_parts))
            current_parts = [section]
            current_len = section_len

    # Don't forget the last accumulation
    if current_parts:
        raw_chunks.append("".join(current_parts))

    total = len(raw_chunks)
    return [
        EpisodeChunk(content=chunk_text, chunk_index=idx + 1, total_chunks=total)
        for idx, chunk_text in enumerate(raw_chunks)
    ]
