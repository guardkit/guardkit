"""
Agent Markdown Parser

Parses agent markdown files into structured data for analysis and transformation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import yaml

# TASK-FIX-7C3D: Import file I/O utilities
from installer.core.lib.utils.file_io import safe_read_file


@dataclass
class CodeBlock:
    """Represents a code block in the agent markdown."""

    language: str
    start_line: int
    end_line: int
    content: str


@dataclass
class Section:
    """Represents a markdown section (heading and its content)."""

    title: str
    level: int  # Heading level (1-6)
    start_line: int
    end_line: int
    content: str


@dataclass
class AgentStructure:
    """Structured representation of an agent markdown file."""

    frontmatter: dict
    sections: list[Section]
    code_blocks: list[CodeBlock]
    raw_content: str
    frontmatter_end_line: int


def extract_frontmatter(content: str) -> tuple[dict, int]:
    """
    Extract YAML frontmatter from markdown content.

    Args:
        content: Raw markdown content

    Returns:
        Tuple of (frontmatter dict, end line number)
    """
    lines = content.split('\n')

    # Find frontmatter boundaries
    in_frontmatter = False
    frontmatter_start = -1
    frontmatter_end = -1

    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
                frontmatter_start = i
            else:
                frontmatter_end = i
                break

    if frontmatter_start == -1 or frontmatter_end == -1:
        return {}, 0

    # Extract and parse YAML
    frontmatter_text = '\n'.join(lines[frontmatter_start + 1:frontmatter_end])

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter or {}, frontmatter_end + 1
    except yaml.YAMLError:
        return {}, frontmatter_end + 1


def find_sections(content: str, frontmatter_end: int) -> list[Section]:
    """
    Find all markdown sections (headings and their content).

    Args:
        content: Raw markdown content
        frontmatter_end: Line number where frontmatter ends

    Returns:
        List of Section objects
    """
    lines = content.split('\n')
    sections = []

    # Pattern to match markdown headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    current_section: Optional[dict] = None

    for i in range(frontmatter_end, len(lines)):
        line = lines[i]
        match = heading_pattern.match(line)

        if match:
            # Save previous section if exists
            if current_section:
                current_section['end_line'] = i - 1
                current_section['content'] = '\n'.join(
                    lines[current_section['start_line']:current_section['end_line'] + 1]
                )
                sections.append(Section(**current_section))

            # Start new section
            level = len(match.group(1))
            title = match.group(2).strip()
            current_section = {
                'title': title,
                'level': level,
                'start_line': i,
                'end_line': -1,
                'content': ''
            }

    # Save last section
    if current_section:
        current_section['end_line'] = len(lines) - 1
        current_section['content'] = '\n'.join(
            lines[current_section['start_line']:current_section['end_line'] + 1]
        )
        sections.append(Section(**current_section))

    return sections


def find_code_blocks(content: str, frontmatter_end: int) -> list[CodeBlock]:
    """
    Find all code blocks in the markdown content.

    Args:
        content: Raw markdown content
        frontmatter_end: Line number where frontmatter ends

    Returns:
        List of CodeBlock objects
    """
    lines = content.split('\n')
    code_blocks = []

    # Pattern to match code block start
    code_start_pattern = re.compile(r'^```(\w+)?')

    in_code_block = False
    current_block: Optional[dict] = None

    for i in range(frontmatter_end, len(lines)):
        line = lines[i]

        if not in_code_block:
            match = code_start_pattern.match(line.strip())
            if match:
                in_code_block = True
                language = match.group(1) or ''
                current_block = {
                    'language': language,
                    'start_line': i,
                    'end_line': -1,
                    'content': ''
                }
        else:
            # Check for end of code block
            if line.strip() == '```':
                if current_block:
                    current_block['end_line'] = i
                    # Extract content (excluding fence markers)
                    current_block['content'] = '\n'.join(
                        lines[current_block['start_line'] + 1:current_block['end_line']]
                    )
                    code_blocks.append(CodeBlock(**current_block))
                    current_block = None
                    in_code_block = False

    return code_blocks


def parse_agent(file_path: Path) -> AgentStructure:
    """
    Parse an agent markdown file into structured data.

    Args:
        file_path: Path to the agent markdown file

    Returns:
        AgentStructure object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a markdown file
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Agent file not found: {file_path}")

    if file_path.suffix != '.md':
        raise ValueError(f"File must be a markdown file (.md): {file_path}")

    # Read file content with error handling (TASK-FIX-7C3D)
    success, content = safe_read_file(file_path)
    if not success:
        # content is error message
        raise ValueError(f"Cannot read agent file: {content}")

    # Parse components
    frontmatter, frontmatter_end = extract_frontmatter(content)
    sections = find_sections(content, frontmatter_end)
    code_blocks = find_code_blocks(content, frontmatter_end)

    return AgentStructure(
        frontmatter=frontmatter,
        sections=sections,
        code_blocks=code_blocks,
        raw_content=content,
        frontmatter_end_line=frontmatter_end
    )
