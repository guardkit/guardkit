# Context Addition Deep-Dive

Comprehensive guide to the architecture and implementation of GuardKit's Graphiti context addition feature.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Parser System](#parser-system)
4. [Episode Generation](#episode-generation)
5. [Metadata Strategy](#metadata-strategy)
6. [Implementation Details](#implementation-details)
7. [Extension Points](#extension-points)
8. [Performance Considerations](#performance-considerations)

---

## Overview

The context addition feature allows users to add structured knowledge from markdown files to the Graphiti knowledge graph. This enables semantic search across project documentation, architecture decisions, feature specifications, and other artifacts.

### Design Goals

1. **Automatic Detection**: Detect document type from filename and content
2. **Structured Extraction**: Extract metadata and relationships
3. **Flexible Input**: Support single files or bulk directory operations
4. **Type Safety**: Validate content against expected structure
5. **Extensibility**: Easy to add new parser types
6. **Error Handling**: Graceful degradation with clear error messages

### Use Cases

- **Project Setup**: Seed initial project documentation
- **Architecture Decisions**: Track ADRs in knowledge graph
- **Feature Planning**: Make feature specs searchable
- **Knowledge Management**: Centralize project knowledge
- **Onboarding**: Help new team members discover context

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│          guardkit graphiti add-context          │
│                  (CLI Command)                  │
└────────────────┬────────────────────────────────┘
                 │
                 ├─ Path Resolution
                 ├─ File Discovery (glob patterns)
                 └─ Batch Processing
                          │
         ┌────────────────┴────────────────┐
         │      ParserRegistry             │
         │  - register(parser)             │
         │  - get_parser(type)             │
         │  - detect_parser(file, content) │
         └────────┬────────────────────────┘
                  │
          ┌───────┴────────┐
          │  Parser Chain  │
          └───────┬────────┘
                  │
      ┌───────────┼───────────────────────┐
      │           │                       │
┌─────▼─────┐ ┌──▼──────┐ ┌──────────▼──────────┐
│   ADR     │ │ Feature │ │ ProjectOverview     │
│  Parser   │ │  Spec   │ │     Parser          │
└─────┬─────┘ └──┬──────┘ └──────────┬──────────┘
      │          │                    │
      └──────────┴────────────────────┘
                 │
          ┌──────▼──────┐
          │  ParseResult│
          │  - success  │
          │  - episodes │
          │  - warnings │
          └──────┬──────┘
                 │
        ┌────────▼────────┐
        │  GraphitiClient │
        │  add_episode()  │
        └─────────────────┘
```

### Data Flow

```
User Input (file/directory)
    │
    ├─> Path Resolution
    │   └─> File Discovery (glob)
    │
    ├─> For each file:
    │   ├─> Read content
    │   ├─> Detect parser (registry)
    │   ├─> Parse content → ParseResult
    │   │   ├─> Extract metadata
    │   │   ├─> Generate episodes
    │   │   └─> Collect warnings
    │   │
    │   └─> Add episodes to Graphiti
    │       └─> client.add_episode()
    │
    └─> Summary Report
        ├─> Files processed
        ├─> Episodes added
        ├─> Warnings
        └─> Errors
```

---

## Parser System

### Base Parser Interface

All parsers implement the `BaseParser` abstract base class:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class EpisodeData:
    """Data for creating a Graphiti episode."""
    entity_id: str          # Unique identifier (e.g., "ADR-001")
    entity_type: str        # Type (e.g., "adr", "task")
    content: str            # Full text content
    group_id: str           # Graphiti group (e.g., "guardkit__project_decisions")
    metadata: dict          # Additional metadata

@dataclass
class ParseResult:
    """Result of parsing a file."""
    success: bool
    episodes: list[EpisodeData]
    warnings: list[str]

class BaseParser(ABC):
    @property
    @abstractmethod
    def parser_type(self) -> str:
        """Unique identifier for this parser."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this parser handles."""
        pass

    @abstractmethod
    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given content."""
        pass

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse content and return structured result."""
        pass
```

### Parser Registry

The registry manages parser registration and selection:

```python
class ParserRegistry:
    def __init__(self):
        self._parsers: dict[str, BaseParser] = {}
        self._extension_map: dict[str, str] = {}

    def register(self, parser: BaseParser):
        """Register a parser and its extensions."""
        self._parsers[parser.parser_type] = parser
        for ext in parser.supported_extensions:
            self._extension_map[ext.lower()] = parser.parser_type

    def get_parser(self, parser_type: str) -> Optional[BaseParser]:
        """Get parser by type name."""
        return self._parsers.get(parser_type)

    def detect_parser(self, file_path: str, content: str) -> Optional[BaseParser]:
        """Auto-detect appropriate parser."""
        # Strategy 1: Extension-based detection
        ext = Path(file_path).suffix.lower()
        if ext in self._extension_map:
            parser_type = self._extension_map[ext]
            parser = self._parsers.get(parser_type)
            if parser and parser.can_parse(content, file_path):
                return parser

        # Strategy 2: Try all parsers via can_parse
        for parser in self._parsers.values():
            if parser.can_parse(content, file_path):
                return parser

        return None
```

### Detection Strategy

Parser selection follows this priority order:

1. **Explicit `--type` flag**: Use specified parser directly
2. **Filename pattern**: Match against known patterns (ADR-\*, FEATURE-SPEC-\*)
3. **Content analysis**: Call `can_parse()` on all parsers
4. **Fallback**: Use generic `project-doc` parser

**Example - ADR Detection**:

```python
class ADRParser(BaseParser):
    def can_parse(self, content: str, file_path: str) -> bool:
        # Check filename pattern
        filename = Path(file_path).name.lower()
        if filename.startswith('adr-'):
            return True

        # Check content structure
        has_status = '## Status' in content or '## status' in content.lower()
        has_context = '## Context' in content or '## context' in content.lower()
        has_decision = '## Decision' in content or '## decision' in content.lower()

        return has_status and has_context and has_decision
```

---

## Episode Generation

### Episode Structure

Each parser generates one or more episodes from a single file:

**ADR Parser** (1 episode):
```python
EpisodeData(
    entity_id="ADR-001",
    entity_type="adr",
    content="[Full ADR text with all sections]",
    group_id="guardkit__project_decisions",
    metadata={
        "title": "Use Graphiti for persistent memory",
        "status": "Accepted",
        "decision_date": "2024-01-15",
        "entity_type": "adr",
        "source_file": "docs/architecture/ADR-001.md"
    }
)
```

**Feature Spec Parser** (N episodes):
```python
# Feature overview episode
EpisodeData(
    entity_id="FEAT-AUTH",
    entity_type="feature-spec",
    content="[Feature overview with objectives, phases]",
    group_id="guardkit__feature_specs",
    metadata={...}
)

# Task episodes (one per task)
EpisodeData(
    entity_id="TASK-AUTH-001",
    entity_type="task",
    content="[Task description and acceptance criteria]",
    group_id="guardkit__feature_specs",
    metadata={
        "feature_id": "FEAT-AUTH",
        "wave": 1,
        "depends_on": [],
        ...
    }
)
```

### Group ID Strategy

Group IDs organize episodes into logical collections:

**System-Level Groups**:
- `guardkit_templates`
- `guardkit_patterns`
- `guardkit_workflows`
- `product_knowledge`
- `command_workflows`
- `quality_gate_phases`

**Project-Level Groups**:
- `{project}__project_overview`
- `{project}__project_architecture`
- `{project}__feature_specs`
- `{project}__project_decisions`
- `{project}__project_docs`

**Format**: `{namespace}__{category}`
- System namespace: `guardkit`, `product_knowledge`, etc.
- Project namespace: `{project_name}` (e.g., `myapp`)
- Category: `overview`, `decisions`, `feature_specs`, etc.

### Content Formatting

Episode content is formatted for optimal semantic search:

**ADR Content Template**:
```
# ADR-{number}: {title}

Status: {status}
Date: {decision_date}

## Context

{context_text}

## Decision

{decision_text}

## Consequences

{consequences_text}

Source: {file_path}
```

**Feature Spec Content Template**:
```
# Feature: {feature_name}

Feature ID: {feature_id}
Status: {status}
Priority: {priority}

## Overview

{overview_text}

## Objectives

{objectives_list}

## Phases

{phases_list}

## Dependencies

{dependencies_list}

Source: {file_path}
```

---

## Metadata Strategy

### Standard Metadata Fields

All episodes include these standard fields:

```python
{
    "entity_id": "unique-identifier",
    "entity_type": "adr | feature-spec | task | project-overview | project-doc",
    "source_file": "relative/path/to/file.md",
    "_metadata": {
        "source": "add_context",
        "created_at": "2024-01-30T12:00:00Z",
        "updated_at": "2024-01-30T12:00:00Z",
        "parser_type": "adr",
        "parser_version": "1.0.0"
    }
}
```

### Type-Specific Metadata

**ADR Metadata**:
```python
{
    "title": "Decision title",
    "status": "Accepted | Rejected | Proposed | Deprecated",
    "decision_date": "2024-01-15",
    "context": "Background...",
    "decision": "We will...",
    "consequences": "Benefits and trade-offs..."
}
```

**Feature Spec Metadata**:
```python
{
    "feature_id": "FEAT-AUTH",
    "feature_name": "User Authentication",
    "status": "planned | in_progress | completed",
    "priority": "high | medium | low",
    "phases": ["planning", "implementation", "testing"],
    "dependencies": ["FEAT-DB"]
}
```

**Task Metadata**:
```python
{
    "task_id": "TASK-AUTH-001",
    "task_name": "Implement JWT tokens",
    "status": "backlog | in_progress | completed",
    "priority": "high | medium | low",
    "feature_id": "FEAT-AUTH",
    "depends_on": ["TASK-AUTH-002"],
    "wave": 1,
    "implementation_mode": "task-work | direct | manual"
}
```

### Metadata Usage

**Semantic Search**:
- Status filtering: Find all "Accepted" ADRs
- Priority sorting: High-priority tasks first
- Dependency tracking: Tasks that depend on X

**Deduplication**:
- `entity_id` uniqueness check
- `source_file` tracking prevents re-adding
- `updated_at` timestamp for version detection

**Provenance**:
- `source_file` tracks origin
- `parser_type` identifies extraction method
- `created_at` / `updated_at` for audit trail

---

## Implementation Details

### CLI Command Implementation

```python
@graphiti.command("add-context")
@click.argument("path")
@click.option("--type", "parser_type", help="Force parser type")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing")
@click.option("--dry-run", is_flag=True, help="Preview only")
@click.option("--pattern", default="**/*.md", help="Glob pattern")
@click.option("--verbose", "-v", is_flag=True, help="Detailed output")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
def add_context(path, parser_type, force, dry_run, pattern, verbose, quiet):
    """Add context from files to Graphiti."""
    asyncio.run(_cmd_add_context(path, parser_type, force, dry_run, pattern, verbose, quiet))

async def _cmd_add_context(path, parser_type, force, dry_run, pattern, verbose, quiet):
    # 1. Validate inputs
    target_path = Path(path)
    if not target_path.exists():
        console.print(f"[red]Error: Path does not exist: {path}[/red]")
        raise SystemExit(1)

    # 2. Connect to Graphiti
    client = GraphitiClient()
    await client.initialize()

    # 3. Collect files to process
    files = []
    if target_path.is_file():
        files.append(path)
    else:
        files.extend(str(f) for f in target_path.glob(pattern) if f.is_file())

    # 4. Process each file
    registry = ParserRegistry()
    for file_path in files:
        content = Path(file_path).read_text()

        # Detect or use specified parser
        parser = registry.get_parser(parser_type) if parser_type else registry.detect_parser(file_path, content)

        if not parser:
            console.print(f"[yellow]No parser for: {file_path}[/yellow]")
            continue

        # Parse the file
        result = parser.parse(content, file_path)

        # Add episodes to Graphiti
        if not dry_run:
            for episode in result.episodes:
                await client.add_episode(
                    name=episode.entity_id,
                    episode_body=episode.content,
                    group_id=episode.group_id,
                    metadata=episode.metadata
                )

    # 5. Close client
    await client.close()
```

### Error Handling

**File-Level Errors**:
```python
try:
    content = Path(file_path).read_text()
except Exception as e:
    errors.append(f"{file_path}: Error reading file - {e}")
    continue
```

**Parse-Level Errors**:
```python
result = parser.parse(content, file_path)
if not result.success:
    errors.append(f"{file_path}: Parse failed")
    for warn in result.warnings:
        warnings.append(f"{file_path}: {warn}")
    continue
```

**Episode-Level Errors**:
```python
try:
    await client.add_episode(...)
except Exception as e:
    errors.append(f"{file_path}: Error adding episode - {e}")
```

### Batch Processing

Files are processed sequentially to maintain order and handle errors gracefully:

```python
for file_path in files_to_process:
    try:
        # Read → Parse → Add
        process_file(file_path)
        files_processed += 1
    except Exception as e:
        errors.append(f"{file_path}: {e}")
        continue  # Continue with next file
```

**Benefits**:
- Partial success (some files succeed even if others fail)
- Clear error reporting per file
- Graceful degradation

**Trade-offs**:
- Sequential processing (not parallel)
- Slower for large batches
- Could optimize with async batching

---

## Extension Points

### Adding New Parser Types

1. **Create Parser Class**:

```python
from guardkit.integrations.graphiti.parsers.base import BaseParser, ParseResult, EpisodeData

class MyCustomParser(BaseParser):
    @property
    def parser_type(self) -> str:
        return "custom-type"

    @property
    def supported_extensions(self) -> list[str]:
        return [".md", ".txt"]

    def can_parse(self, content: str, file_path: str) -> bool:
        # Custom detection logic
        return "## My Custom Marker" in content

    def parse(self, content: str, file_path: str) -> ParseResult:
        # Extract metadata
        metadata = self._extract_metadata(content)

        # Create episode
        episode = EpisodeData(
            entity_id=metadata["id"],
            entity_type="custom-type",
            content=content,
            group_id=f"{project}__custom_docs",
            metadata=metadata
        )

        return ParseResult(
            success=True,
            episodes=[episode],
            warnings=[]
        )
```

2. **Register Parser**:

```python
# In guardkit/integrations/graphiti/parsers/__init__.py
from .my_custom import MyCustomParser

__all__ = [
    "BaseParser",
    "MyCustomParser",  # Add to exports
    # ...
]
```

3. **Use in CLI**:

```bash
guardkit graphiti add-context docs/ --type custom-type
```

### Customizing Metadata

Override `_extract_metadata()` in your parser:

```python
def _extract_metadata(self, content: str) -> dict:
    # Custom extraction logic
    metadata = {
        "custom_field_1": extract_field_1(content),
        "custom_field_2": extract_field_2(content),
        "entity_type": self.parser_type,
    }
    return metadata
```

### Adding Validation Rules

Implement custom validation in `parse()`:

```python
def parse(self, content: str, file_path: str) -> ParseResult:
    warnings = []

    # Required sections check
    if "## Required Section" not in content:
        warnings.append("Missing required section")

    # Validation checks
    if not self._validate_structure(content):
        return ParseResult(
            success=False,
            episodes=[],
            warnings=["Invalid structure"]
        )

    # Continue with parsing...
```

---

## Performance Considerations

### File Discovery Optimization

**Current**: Python glob with `Path.glob(pattern)`

**Optimization opportunities**:
- Cache file lists for repeated operations
- Parallel file reading (asyncio)
- Skip unchanged files (checksum comparison)

### Parsing Performance

**Current**: Sequential processing per file

**Bottlenecks**:
- File I/O (disk reads)
- Regex matching in parsers
- Network calls to Graphiti

**Optimizations**:
- Batch episode additions (single API call)
- Parallel parsing with `asyncio.gather()`
- Parser result caching

### Memory Usage

**Current approach**:
- Load full file content into memory
- Create all episodes before adding
- Single file at a time

**Memory profile**:
- Small files (<100KB): Minimal impact
- Large files (>1MB): Could stream content
- Many files (1000+): Process in batches

### Graphiti API Efficiency

**Current**: One API call per episode

**Optimization**:
```python
# Instead of:
for episode in episodes:
    await client.add_episode(...)

# Use batch operation:
await client.add_episodes_batch(episodes)
```

### Caching Strategy

**File-level cache**:
```python
# Skip unchanged files
file_hash = hashlib.sha256(content.encode()).hexdigest()
if existing_episode_hash == file_hash:
    skip_file()
```

**Parser-level cache**:
```python
# Cache parsed results
@lru_cache(maxsize=128)
def parse_file(file_path: str) -> ParseResult:
    ...
```

---

## Testing Strategy

### Unit Tests

**Parser tests**:
```python
def test_adr_parser_detects_valid_adr():
    parser = ADRParser()
    content = """
    # ADR-001: Title

    ## Status
    Accepted

    ## Context
    ...

    ## Decision
    ...
    """
    assert parser.can_parse(content, "ADR-001.md")

def test_adr_parser_extracts_metadata():
    parser = ADRParser()
    result = parser.parse(valid_adr_content, "ADR-001.md")
    assert result.success
    assert len(result.episodes) == 1
    assert result.episodes[0].metadata["status"] == "Accepted"
```

**Registry tests**:
```python
def test_registry_detects_by_filename():
    registry = ParserRegistry()
    registry.register(ADRParser())

    parser = registry.detect_parser("ADR-001.md", content)
    assert parser.parser_type == "adr"
```

### Integration Tests

**End-to-end command tests**:
```python
async def test_add_context_single_file(tmp_path):
    # Create test file
    adr_file = tmp_path / "ADR-001.md"
    adr_file.write_text(valid_adr_content)

    # Run command
    await _cmd_add_context(str(adr_file), None, False, False, "**/*.md", False, False)

    # Verify episode in Graphiti
    results = await client.search("ADR-001", group_ids=["test__project_decisions"])
    assert len(results) > 0
```

---

## See Also

- [Graphiti Add Context Guide](../../guides/graphiti-add-context.md) - Command reference
- [Graphiti Parsers Guide](../../guides/graphiti-parsers.md) - Parser documentation
- [Episode Metadata Deep-Dive](episode-metadata.md) - Metadata schema details
- [Graphiti Integration Guide](../../guides/graphiti-integration-guide.md) - Overall architecture
