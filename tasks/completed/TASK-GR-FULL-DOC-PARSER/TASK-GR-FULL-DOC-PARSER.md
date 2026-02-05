---
id: TASK-GR-FULL-DOC-PARSER
title: Add Full Document Parser for Generic Markdown
type: feature
priority: medium
status: COMPLETED
created: 2025-02-04
completed: 2026-02-05
tags: [graphiti, parser, knowledge-capture]
---

# Add Full Document Parser for Generic Markdown

## Problem Statement

The existing `project_doc` parser only captures content from sections with specific header patterns (purpose, tech_stack, architecture). Content in other sections (Core Tools, Technology Decisions, etc.) isn't captured, limiting the knowledge that can be stored in Graphiti.

**Current Behavior:**
- `project_doc` parser looks for specific headers: overview, purpose, tech stack, architecture
- Content in unmatched sections is silently ignored
- User has no way to capture full document content

**Example:** A document like `GRAPHITI-KNOWLEDGE.md` with sections:
- `## Project Overview` → Captured (matches "project overview")
- `### Architecture` → Captured (matches "architecture")
- `## Core Tools` → **NOT captured**
- `## Technology Decisions` → **NOT captured**

## Proposed Solution

Create a new `full_doc` parser that captures the entire document content as a single episode, useful for:
- Research documents
- Project knowledge bases
- Design documents
- Any markdown file where full content is valuable

## Acceptance Criteria

1. **New Parser Type**: `full_doc`
   - Parser type identifier: `"full_doc"`
   - Supported extensions: `.md`, `.markdown`
   - `can_parse()`: Returns true for any markdown file (or use explicit `--type full_doc`)

2. **Episode Creation**:
   - Creates a single episode containing the full document content
   - Group ID: `project_knowledge` (searchable by default)
   - Entity type: `full_doc`
   - Entity ID: File path

3. **Metadata Extraction**:
   - Extract document title from first `#` heading
   - Extract YAML frontmatter if present
   - Include file path and size in metadata

4. **CLI Integration**:
   - Add to parser registry in `graphiti.py`
   - Add to CLI help text for `--type` option
   - Add `project_knowledge` to default search groups

5. **Content Handling**:
   - Optionally chunk large documents (>10KB) into multiple episodes
   - Preserve markdown formatting
   - Handle documents without headings gracefully

## Implementation Notes

### Parser Structure

```python
class FullDocParser(BaseParser):
    """Parser that captures entire markdown document content."""

    @property
    def parser_type(self) -> str:
        return "full_doc"

    @property
    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def can_parse(self, content: str, file_path: str) -> bool:
        # Only match when explicitly requested via --type full_doc
        # Don't auto-detect to avoid conflicts with other parsers
        return False

    def parse(self, content: str, file_path: str) -> ParseResult:
        # Extract title from first heading
        # Parse frontmatter
        # Create single episode with full content
        pass
```

### Group ID Decision

Use `project_knowledge` as the group_id so it's searchable by default. The search command already includes many project groups.

### Large Document Handling

For documents >10KB, consider chunking by top-level sections (`##` headers) to create multiple episodes. This improves:
- Embedding quality (smaller, focused chunks)
- Search relevance (matches specific sections)
- Token efficiency

## Testing Requirements

1. Unit tests for `FullDocParser`:
   - Test `parser_type` returns `"full_doc"`
   - Test `supported_extensions` returns markdown extensions
   - Test `can_parse()` returns False (explicit-only)
   - Test full document capture
   - Test title extraction
   - Test frontmatter extraction
   - Test chunking for large documents

2. Integration tests:
   - Add full document via CLI
   - Search finds content from full document
   - Verify episode metadata

## Files to Modify

- `guardkit/integrations/graphiti/parsers/full_doc_parser.py` (NEW)
- `guardkit/integrations/graphiti/parsers/__init__.py` (add export)
- `guardkit/cli/graphiti.py` (register parser, update help text)
- `tests/integrations/graphiti/parsers/test_full_doc_parser.py` (NEW)

## Usage Example

```bash
# Capture entire document content
guardkit graphiti add-context docs/research/GRAPHITI-KNOWLEDGE.md --type full_doc --force

# Search for any content in the document
guardkit graphiti search "transcript" --limit 5
guardkit graphiti search "youtube" --limit 5
```

## Related

- `project_doc` parser: Structured extraction for CLAUDE.md/README.md
- `project_overview` parser: Project overview episodes
- `adr` parser: Architecture Decision Records
- `feature_spec` parser: Feature specifications

## Notes

- This parser is explicit-only (`can_parse` returns False) to avoid conflicts with specialized parsers
- Users must specify `--type full_doc` to use it
- Good for one-off knowledge capture where structure doesn't match existing parsers
