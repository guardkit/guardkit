# Graphiti Parsers Reference

Complete reference for content parsers used by `guardkit graphiti add-context`.

## Overview

Parsers extract structured information from markdown files and convert them into episodes for the Graphiti knowledge graph. Each parser is specialized for a specific document type and extracts relevant metadata, relationships, and content.

GuardKit includes **5 parsers**:

| Parser | Type Identifier | Auto-Detect | Use Case |
|--------|----------------|-------------|----------|
| [ADR Parser](#adr-parser-adr) | `adr` | Yes | Architecture Decision Records |
| [Feature Spec Parser](#feature-spec-parser-feature-spec) | `feature-spec` | Yes | Feature specifications |
| [Project Overview Parser](#project-overview-parser-project_overview) | `project_overview` | Yes | High-level project information |
| [Project Doc Parser](#project-doc-parser-project_doc) | `project_doc` | Yes (CLAUDE.md/README.md only) | Section extraction from project docs |
| [Full Document Parser](#full-document-parser-full_doc) | `full_doc` | No (explicit only) | Complete markdown document capture |

## Available Parsers

### ADR Parser (`adr`)

Parses Architecture Decision Records to extract decisions, rationale, and consequences.

#### Detection Criteria

**Filename patterns**:
- `ADR-*.md` (e.g., `ADR-001-use-graphiti.md`)
- `adr-*.md` (case-insensitive)

**Content-based detection**:
- Must contain all three required sections:
  - `## Status`
  - `## Context`
  - `## Decision`

#### Episodes Created

**1 episode per ADR**:
- **Entity ID**: ADR number (e.g., `ADR-001`)
- **Entity Type**: `adr`
- **Group ID**: `{project}__project_decisions`
- **Content**: Full ADR text including all sections

#### Extracted Metadata

```json
{
  "title": "Use Graphiti for persistent memory",
  "status": "Accepted",
  "decision_date": "2024-01-15",
  "context": "Need persistent memory across sessions...",
  "decision": "We will use Graphiti knowledge graph...",
  "consequences": "Benefits: ... Trade-offs: ...",
  "entity_type": "adr",
  "source_file": "docs/architecture/ADR-001-use-graphiti.md"
}
```

#### ADR Structure Requirements

```markdown
# ADR-001: Use Graphiti for Persistent Memory

## Status

Accepted

## Context

[Problem description and background]

## Decision

[The decision made and key reasoning]

## Consequences

[Positive and negative outcomes]
```

**Required sections**:
- `## Status` - Decision status (Proposed, Accepted, Rejected, Deprecated)
- `## Context` - Background and problem description
- `## Decision` - The decision made

**Optional sections**:
- `## Consequences` - Outcomes and trade-offs
- `## Alternatives Considered` - Other options evaluated
- `## References` - Related documents

#### Example Usage

```bash
# Auto-detect ADR by filename
guardkit graphiti add-context docs/architecture/ADR-001-use-graphiti.md

# Force ADR parser for non-standard filename
guardkit graphiti add-context custom-decision.md --type adr

# Add all ADRs
guardkit graphiti add-context docs/architecture/ --pattern "ADR-*.md"
```

---

### Feature Spec Parser (`feature-spec`)

Parses feature specification documents to extract feature details and constituent tasks.

#### Detection Criteria

**Filename patterns**:
- `FEATURE-SPEC-*.md` (e.g., `FEATURE-SPEC-authentication.md`)
- `*-feature-spec.md` (e.g., `authentication-feature-spec.md`)
- `feature-*.md`

**Content-based detection**:
- Contains YAML frontmatter with `feature_id` field
- Contains `## Tasks` section

#### Episodes Created

**Multiple episodes per spec**:
1. **Feature overview episode**:
   - **Entity ID**: Feature ID from frontmatter
   - **Entity Type**: `feature-spec`
   - **Content**: Feature description, objectives, phases

2. **Task episodes** (1 per task):
   - **Entity ID**: Task ID (e.g., `TASK-AUTH-001`)
   - **Entity Type**: `task`
   - **Content**: Task description, acceptance criteria, dependencies

**Group ID**: `{project}__feature_specs`

#### Extracted Metadata

**Feature metadata**:
```json
{
  "feature_id": "FEAT-AUTH",
  "feature_name": "User Authentication",
  "status": "planned",
  "priority": "high",
  "phases": ["planning", "implementation", "testing"],
  "dependencies": ["FEAT-DB"],
  "entity_type": "feature-spec",
  "source_file": "docs/features/FEATURE-SPEC-authentication.md"
}
```

**Task metadata**:
```json
{
  "task_id": "TASK-AUTH-001",
  "task_name": "Implement JWT tokens",
  "status": "backlog",
  "priority": "high",
  "feature_id": "FEAT-AUTH",
  "depends_on": [],
  "wave": 1,
  "entity_type": "task",
  "source_file": "docs/features/FEATURE-SPEC-authentication.md"
}
```

#### Feature Spec Structure

```markdown
---
feature_id: FEAT-AUTH
feature_name: User Authentication
status: planned
priority: high
---

# Feature: User Authentication

## Overview

[Feature description]

## Objectives

- Secure user login
- JWT token management

## Tasks

### TASK-AUTH-001: Implement JWT tokens

**Status**: backlog
**Priority**: high
**Wave**: 1

Description: Create JWT token generation and validation.

Acceptance Criteria:
- [ ] Token generation works
- [ ] Token validation works

Dependencies: []

### TASK-AUTH-002: Create login endpoint

[Task details...]

## Phases

- Planning
- Implementation
- Testing

## Dependencies

- FEAT-DB (Database setup)
```

#### Example Usage

```bash
# Auto-detect by filename
guardkit graphiti add-context docs/features/FEATURE-SPEC-authentication.md

# Force feature-spec parser
guardkit graphiti add-context custom-spec.md --type feature-spec

# Add all feature specs
guardkit graphiti add-context docs/ --pattern "FEATURE-SPEC-*.md"
```

---

### Project Overview Parser (`project_overview`)

Parses project overview documents to extract high-level project information, tech stack, and architecture.

#### Detection Criteria

**Filename patterns**:
- `CLAUDE.md`
- `README.md`

**Content-based detection**:
- Contains project context markers
- Has sections like "Tech Stack", "Architecture", "Core Principles"

#### Episodes Created

**1-2 episodes per document**:
- **Main episode**:
  - **Entity ID**: `{project}_overview`
  - **Entity Type**: `project`
  - **Group ID**: `{project}__project_overview`
  - **Content**: Full project overview with all sections
- **Architecture episode** (if architecture section > 500 chars):
  - **Entity Type**: `architecture`
  - **Group ID**: `{project}__project_architecture`

#### Extracted Metadata

```json
{
  "project_name": "guardkit",
  "project_purpose": "Lightweight AI-assisted development workflow",
  "tech_stack": ["Python", "Click", "Neo4j", "Graphiti"],
  "architecture": "CLI-based with plugin architecture",
  "core_principles": ["Quality First", "Pragmatic Approach"],
  "entity_type": "project",
  "source_file": "CLAUDE.md"
}
```

#### Project Overview Structure

```markdown
# GuardKit - Lightweight Task Workflow System

## Project Context

This is an AI-powered task workflow system...

## Core Principles

1. Quality First
2. Pragmatic Approach
3. AI/Human Collaboration

## Technology Stack Detection

The system will detect your project's technology stack:
- React/TypeScript → Playwright + Vitest
- Python API → pytest

## Architecture

- CLI-based command structure
- Pluggable parser system
- Neo4j knowledge graph backend
```

**Key sections**:
- Project description and purpose
- Core principles or philosophy
- Technology stack
- Architecture overview
- Workflow descriptions

#### Example Usage

```bash
# Add project overview
guardkit graphiti add-context CLAUDE.md

# Force project_overview parser
guardkit graphiti add-context overview.md --type project_overview

# Add README as project overview
guardkit graphiti add-context README.md
```

---

### Project Doc Parser (`project_doc`)

Extracts specific sections (purpose, tech stack, architecture) from `CLAUDE.md` and `README.md` files.

**Note**: This parser is **not** a fallback for general markdown files. It only handles `CLAUDE.md` and `README.md` and creates separate episodes for each recognized section. For capturing entire documents, use the [Full Document Parser](#full-document-parser-full_doc) with `--type full_doc`.

#### Detection Criteria

**Filename patterns** (case-insensitive):
- `CLAUDE.md` / `CLAUDE.markdown`
- `README.md` / `README.markdown`

**Not a fallback**: Does **not** match arbitrary markdown files. Only parses the two filenames above.

#### Episodes Created

**Multiple episodes per document** (1 per recognized section):

1. **Purpose episode** (if purpose/overview section found):
   - **Entity Type**: `project_doc`
   - **Group ID**: `{project}__project_purpose`
   - **Content**: Purpose/overview section content

2. **Tech Stack episode** (if tech stack section found):
   - **Entity Type**: `project_doc`
   - **Group ID**: `{project}__project_tech_stack`
   - **Content**: Technology stack section content

3. **Architecture episode** (if architecture section found):
   - **Entity Type**: `project_doc`
   - **Group ID**: `{project}__project_architecture`
   - **Content**: Architecture/patterns section content

#### Section Detection

The parser looks for these header patterns (case-insensitive):

| Section | Header Patterns |
|---------|----------------|
| **Purpose** | overview, purpose, about, description, what is this, project overview |
| **Tech Stack** | tech stack, technologies, stack, built with, technology stack, dependencies |
| **Architecture** | architecture, patterns, structure, design, system design, project structure |

#### Extracted Metadata

```json
{
  "section_type": "purpose",
  "frontmatter": {},
  "entity_type": "project_doc",
  "source_file": "CLAUDE.md"
}
```

#### Example Usage

```bash
# Auto-detect from CLAUDE.md
guardkit graphiti add-context CLAUDE.md

# Explicit project_doc parser
guardkit graphiti add-context CLAUDE.md --type project_doc

# Add README
guardkit graphiti add-context README.md
```

---

### Full Document Parser (`full_doc`)

Captures the entire content of a markdown document as a single episode (or multiple episodes for large documents). This is an **explicit-only** parser - it will not auto-detect files. You must specify `--type full_doc` to use it.

Unlike the [Project Doc Parser](#project-doc-parser-project_doc) which extracts only specific sections from CLAUDE.md/README.md, this parser preserves the **entire document content** and works with **any markdown file**.

#### Detection Criteria

**Explicit-only**: `can_parse()` always returns `False`.
- Must use `--type full_doc` flag
- Will not be selected by auto-detection

**Supported extensions**: `.md`, `.markdown`

#### Episodes Created

**Small documents** (< 10KB):
- **1 episode** containing the full document
- **Entity ID**: File path
- **Entity Type**: `full_doc`
- **Group ID**: `{project}__project_knowledge`

**Large documents** (>= 10KB):
- **Multiple episodes** (chunked by `##` headers)
- Each chunk becomes a separate episode
- Entity IDs include chunk suffix (e.g., `path/to/file.md_chunk_0`)
- Chunk metadata includes `chunk_index`, `chunk_total`, `chunk_title`

#### Chunking Behavior

Documents larger than the chunk threshold (default: 10KB) are split by `##` (h2) headers:

1. Content before the first `##` header becomes an "Introduction" chunk
2. Each `##` section becomes a separate chunk
3. If no `##` headers exist, the document remains a single episode

```
Large Document (15KB)
├── Chunk 0: "Document Title - Introduction" (content before first ##)
├── Chunk 1: "Document Title - Overview" (## Overview section)
├── Chunk 2: "Document Title - Architecture" (## Architecture section)
└── Chunk 3: "Document Title - Implementation" (## Implementation section)
```

#### Extracted Metadata

```json
{
  "file_path": "docs/research/GRAPHITI-KNOWLEDGE.md",
  "file_size": 15360,
  "title": "Graphiti Knowledge Capture",
  "frontmatter": {},
  "chunk_index": 0,
  "chunk_total": 4,
  "chunk_title": "Graphiti Knowledge Capture - Introduction"
}
```

#### Example Usage

```bash
# Capture entire document content
guardkit graphiti add-context docs/research/GRAPHITI-KNOWLEDGE.md --type full_doc

# Capture and overwrite existing
guardkit graphiti add-context docs/design/architecture-overview.md --type full_doc --force

# Preview what would be captured
guardkit graphiti add-context docs/guides/workflow.md --type full_doc --dry-run --verbose
```

#### When to Use full_doc vs Other Parsers

| Scenario | Recommended Parser |
|----------|-------------------|
| Architecture Decision Records | `adr` (auto-detected) |
| Feature specifications | `feature-spec` (auto-detected) |
| CLAUDE.md/README.md section extraction | `project_doc` (auto-detected) |
| CLAUDE.md/README.md full project overview | `project_overview` (auto-detected) |
| Research documents, design docs, guides | `full_doc` (explicit: `--type full_doc`) |
| Any markdown file - full capture | `full_doc` (explicit: `--type full_doc`) |

---

## Parser Selection Logic

The `add-context` command uses this selection strategy:

### 1. Explicit Type (--type)

```bash
guardkit graphiti add-context file.md --type adr
guardkit graphiti add-context docs/research/doc.md --type full_doc
```

**Behavior**:
- Uses specified parser directly
- Skips auto-detection
- Parser must be registered
- Fails if parser doesn't exist

**Available type values**: `adr`, `feature-spec`, `project_overview`, `project_doc`, `full_doc`

### 2. Filename Pattern Matching

**Priority order**:
1. **ADR**: `ADR-*.md`, `adr-*.md`
2. **Feature Spec**: `FEATURE-SPEC-*.md`, `*-feature-spec.md`
3. **Project Overview**: `CLAUDE.md`, `README.md`
4. **Project Doc**: `CLAUDE.md`, `README.md` (section extraction)

**Behavior**:
- Checks filename against known patterns
- If match found, uses corresponding parser
- Validates with `can_parse()` method
- Falls through if validation fails

**Note**: `full_doc` is **never auto-detected** - it must be specified with `--type full_doc`.

### 3. Content-Based Detection

**Behavior**:
- Tries all registered parsers in order
- Each parser checks content with `can_parse()`
- First parser that returns `True` is selected

**Detection criteria examples**:
- **ADR**: Has `## Status`, `## Context`, `## Decision`
- **Feature Spec**: Has YAML frontmatter with `feature_id`
- **Project Overview**: CLAUDE.md or README.md with project context markers
- **Project Doc**: CLAUDE.md or README.md (extracts purpose/tech_stack/architecture sections)
- **Full Doc**: Never auto-detected (`can_parse()` always returns `False`)

### 4. No Fallback

If no parser matches a file and no `--type` is specified, the file is skipped with a warning:
```
No parser found for: file.md (unsupported)
```

To capture general markdown files, use `--type full_doc` explicitly.

---

## Parser Configuration

### Registering Custom Parsers

```python
from guardkit.integrations.graphiti.parsers import ParserRegistry, BaseParser

# Create custom parser
class CustomParser(BaseParser):
    @property
    def parser_type(self) -> str:
        return "custom"

    @property
    def supported_extensions(self) -> list[str]:
        return [".md", ".txt"]

    def can_parse(self, content: str, file_path: str) -> bool:
        # Custom detection logic
        return "## Custom Marker" in content

    def parse(self, content: str, file_path: str) -> ParseResult:
        # Custom parsing logic
        ...

# Register with registry
registry = ParserRegistry()
registry.register(CustomParser())
```

### Parser Priority

When multiple parsers match:

1. **Filename pattern** (highest priority)
2. **Content-based detection** (tries all parsers via `can_parse()`)
3. **No match**: File is skipped with a warning (there is no fallback parser)

---

## Metadata in Episodes

All parsers include standard metadata in episodes:

```json
{
  "entity_id": "ADR-001",
  "entity_type": "adr",
  "source_file": "docs/architecture/ADR-001.md",
  "_metadata": {
    "source": "add_context",
    "created_at": "2024-01-30T12:00:00Z",
    "updated_at": "2024-01-30T12:00:00Z",
    "parser_type": "adr",
    "parser_version": "1.0.0"
  }
}
```

**Standard fields**:
- `entity_id`: Unique identifier for the entity
- `entity_type`: Type of entity (adr, feature-spec, task, etc.)
- `source_file`: Original file path
- `_metadata.source`: Always `"add_context"`
- `_metadata.parser_type`: Parser that created the episode
- `_metadata.created_at`: ISO timestamp
- `_metadata.updated_at`: ISO timestamp

---

## Parser Output

### Success

```python
ParseResult(
    success=True,
    episodes=[
        EpisodeData(
            entity_id="ADR-001",
            entity_type="adr",
            content="[Full ADR content]",
            group_id="guardkit__project_decisions",
            metadata={...}
        )
    ],
    warnings=[]
)
```

### Warnings

```python
ParseResult(
    success=True,
    episodes=[...],
    warnings=[
        "Missing optional section: Consequences",
        "No decision date specified"
    ]
)
```

### Failure

```python
ParseResult(
    success=False,
    episodes=[],
    warnings=[
        "Missing required section: Decision",
        "Invalid YAML frontmatter"
    ]
)
```

---

## Best Practices

### 1. Use Standard Filename Patterns

**Good**:
```
docs/architecture/ADR-001-use-graphiti.md
docs/features/FEATURE-SPEC-authentication.md
CLAUDE.md
```

**Avoid**:
```
docs/decision1.md  # Harder to detect as ADR
docs/auth-spec.md  # May not match feature-spec pattern
my-overview.md     # Won't match project-overview
```

### 2. Include Required Sections

**ADR - Required**:
- `## Status`
- `## Context`
- `## Decision`

**Feature Spec - Required**:
- YAML frontmatter with `feature_id`
- `## Tasks` section

**Project Overview - Recommended**:
- Project description
- Tech stack section
- Architecture section

### 3. Use YAML Frontmatter

```markdown
---
feature_id: FEAT-AUTH
feature_name: User Authentication
status: planned
priority: high
---

# Feature: User Authentication
```

**Benefits**:
- Structured metadata extraction
- Better semantic search
- Easier to query in Graphiti

### 4. Consistent Naming Conventions

**Use**:
- `ADR-{number}-{slug}.md` for ADRs
- `FEATURE-SPEC-{slug}.md` for feature specs
- `TASK-{prefix}-{number}` for task IDs

**Why**:
- Parsers can auto-detect
- Better organization
- Easier bulk operations

### 5. Validate Before Adding

```bash
# Dry run to check parser detection
guardkit graphiti add-context docs/ --dry-run --verbose

# Review what would be added
# Fix any warnings or unsupported files
# Then add for real
guardkit graphiti add-context docs/
```

---

## Troubleshooting

### Parser Not Detecting File

**Symptom**: "No parser found for: file.md (unsupported)"

**Solutions**:

1. **Check filename pattern**:
   ```bash
   # Rename to match pattern
   mv decision.md ADR-001-decision.md
   ```

2. **Add required sections**:
   ```markdown
   ## Status
   Accepted

   ## Context
   ...

   ## Decision
   ...
   ```

3. **Force specific parser**:
   ```bash
   guardkit graphiti add-context file.md --type adr
   ```

4. **Use verbose to see why it failed**:
   ```bash
   guardkit graphiti add-context file.md --verbose
   ```

### Parse Failed

**Symptom**: "Error: file.md: Parse failed"

**Common causes**:

1. **Missing required sections** (ADR):
   - Add `## Status`, `## Context`, `## Decision`

2. **Invalid YAML frontmatter** (Feature Spec):
   ```markdown
   ---
   feature_id: FEAT-AUTH  # Required
   feature_name: Authentication
   ---
   ```

3. **Malformed task sections**:
   - Ensure task IDs are unique
   - Include required fields (status, priority)

### Warnings About Missing Sections

**Symptom**: "Warning: Missing optional section: Consequences"

**Action**: Warnings don't prevent parsing, but adding the sections improves searchability.

**Add optional sections**:
```markdown
## Consequences

### Positive
- Better memory across sessions

### Negative
- Requires Neo4j setup
```

---

## See Also

- [Graphiti Add Context Guide](graphiti-add-context.md) - Command reference
- [Context Addition Deep-Dive](../deep-dives/graphiti/context-addition.md) - Parser architecture
- [Graphiti Commands Guide](graphiti-commands.md) - All Graphiti CLI commands
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Overall integration
