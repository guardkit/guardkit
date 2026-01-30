# FEAT-GR-002: Context Addition Command

> **Purpose**: Provide an explicit CLI command (`guardkit graphiti add-context`) for adding project-specific knowledge to Graphiti.
>
> **Priority**: High
> **Estimated Complexity**: 5
> **Dependencies**: FEAT-GR-001 (group IDs and schemas)

---

## Problem Statement

After initial project setup, users need a way to add additional context to Graphiti:

1. **Feature specifications** - Detailed specs from `docs/features/*.md`
2. **Architecture decisions** - ADRs from `docs/adr/*.md`
3. **Implementation guides** - Technical documentation
4. **Domain knowledge** - Business context and terminology
5. **Project updates** - Refreshing CLAUDE.md content after changes

Currently there's no command to do this - users would need to manually craft episodes.

---

## Proposed Solution

### Command: `guardkit graphiti add-context`

```bash
# Add a feature specification
guardkit graphiti add-context --type feature docs/features/FEAT-SKEL-001-walking-skeleton.md

# Add project overview from CLAUDE.md
guardkit graphiti add-context --type project-overview CLAUDE.md

# Add an architecture decision record
guardkit graphiti add-context --type adr docs/adr/ADR-001-use-fastmcp.md

# Add implementation guide
guardkit graphiti add-context --type guide docs/IMPLEMENTATION-GUIDE.md

# Add domain knowledge
guardkit graphiti add-context --type domain docs/DOMAIN-GLOSSARY.md

# Add multiple files at once
guardkit graphiti add-context --type feature docs/features/*.md

# Force update (replace existing)
guardkit graphiti add-context --type feature docs/features/FEAT-SKEL-001.md --force
```

### Context Types

| Type | Source | Group ID | Description |
|------|--------|----------|-------------|
| `feature` | Feature spec markdown | `feature_specs` | Feature requirements and success criteria |
| `project-overview` | CLAUDE.md or similar | `project_overview` | Project purpose, goals, architecture |
| `adr` | ADR markdown | `project_decisions` | Architecture Decision Records |
| `guide` | Implementation guides | `project_knowledge` | How-to documentation |
| `domain` | Glossaries, business docs | `domain_knowledge` | Domain terminology and concepts |
| `constraint` | Requirements docs | `project_constraints` | Technical/business constraints |

---

## Technical Requirements

### CLI Implementation

```python
# guardkit/cli/graphiti_commands.py

import click
from pathlib import Path
from typing import List, Optional

from guardkit.knowledge.context_ingestor import ContextIngestor


@click.group()
def graphiti():
    """Graphiti knowledge graph commands."""
    pass


@graphiti.command("add-context")
@click.option(
    "--type", "-t",
    type=click.Choice([
        "feature", "project-overview", "adr", 
        "guide", "domain", "constraint"
    ]),
    required=True,
    help="Type of context to add"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force update if context already exists"
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def add_context(type: str, force: bool, files: tuple):
    """Add context from markdown files to Graphiti.
    
    Examples:
    
        guardkit graphiti add-context --type feature docs/features/FEAT-001.md
        
        guardkit graphiti add-context --type project-overview CLAUDE.md
        
        guardkit graphiti add-context --type adr docs/adr/*.md
    """
    import asyncio
    
    if not files:
        click.echo("Error: No files specified", err=True)
        raise SystemExit(1)
    
    # Expand globs and collect all files
    all_files = []
    for file_pattern in files:
        path = Path(file_pattern)
        if path.is_file():
            all_files.append(path)
        else:
            # Handle glob patterns
            all_files.extend(Path(".").glob(file_pattern))
    
    if not all_files:
        click.echo("Error: No matching files found", err=True)
        raise SystemExit(1)
    
    # Process files
    ingestor = ContextIngestor()
    results = asyncio.run(ingestor.ingest_files(
        files=all_files,
        context_type=type,
        force_update=force
    ))
    
    # Report results
    for result in results:
        if result.success:
            click.echo(f"✓ Added: {result.file_path} -> {result.episode_name}")
        else:
            click.echo(f"✗ Failed: {result.file_path} - {result.error}", err=True)
    
    # Summary
    success_count = sum(1 for r in results if r.success)
    click.echo(f"\nAdded {success_count}/{len(results)} context items")
```

### Context Ingestor

```python
# guardkit/knowledge/context_ingestor.py

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .graphiti_client import get_graphiti
from .parsers import (
    FeatureSpecParser,
    ProjectOverviewParser,
    ADRParser,
    GuideParser,
    DomainParser,
    ConstraintParser
)


@dataclass
class IngestResult:
    """Result of ingesting a single file."""
    file_path: Path
    success: bool
    episode_name: Optional[str] = None
    error: Optional[str] = None


class ContextIngestor:
    """Ingests markdown files into Graphiti as structured episodes."""
    
    PARSERS = {
        "feature": FeatureSpecParser,
        "project-overview": ProjectOverviewParser,
        "adr": ADRParser,
        "guide": GuideParser,
        "domain": DomainParser,
        "constraint": ConstraintParser
    }
    
    GROUP_IDS = {
        "feature": "feature_specs",
        "project-overview": "project_overview",
        "adr": "project_decisions",
        "guide": "project_knowledge",
        "domain": "domain_knowledge",
        "constraint": "project_constraints"
    }
    
    def __init__(self):
        self.graphiti = get_graphiti()
    
    async def ingest_files(
        self,
        files: List[Path],
        context_type: str,
        force_update: bool = False
    ) -> List[IngestResult]:
        """Ingest multiple files into Graphiti."""
        
        results = []
        parser_class = self.PARSERS.get(context_type)
        group_id = self.GROUP_IDS.get(context_type)
        
        if not parser_class or not group_id:
            return [IngestResult(
                file_path=f,
                success=False,
                error=f"Unknown context type: {context_type}"
            ) for f in files]
        
        parser = parser_class()
        
        for file_path in files:
            result = await self._ingest_single_file(
                file_path=file_path,
                parser=parser,
                group_id=group_id,
                force_update=force_update
            )
            results.append(result)
        
        return results
    
    async def _ingest_single_file(
        self,
        file_path: Path,
        parser,
        group_id: str,
        force_update: bool
    ) -> IngestResult:
        """Ingest a single file."""
        
        try:
            # Parse the file
            content = file_path.read_text()
            parsed = parser.parse(content, file_path)
            
            # Generate episode name
            episode_name = self._generate_episode_name(parsed, group_id)
            
            # Check if exists (unless force)
            if not force_update:
                exists = await self._episode_exists(episode_name, group_id)
                if exists:
                    return IngestResult(
                        file_path=file_path,
                        success=False,
                        error="Already exists (use --force to update)"
                    )
            
            # Add to Graphiti
            success = await self.graphiti.add_episode(
                name=episode_name,
                episode_body=parsed.to_dict(),
                group_id=group_id
            )
            
            if success:
                return IngestResult(
                    file_path=file_path,
                    success=True,
                    episode_name=episode_name
                )
            else:
                return IngestResult(
                    file_path=file_path,
                    success=False,
                    error="Failed to add to Graphiti"
                )
        
        except Exception as e:
            return IngestResult(
                file_path=file_path,
                success=False,
                error=str(e)
            )
    
    def _generate_episode_name(self, parsed, group_id: str) -> str:
        """Generate unique episode name."""
        
        if hasattr(parsed, 'id') and parsed.id:
            return f"{group_id}_{parsed.id}"
        elif hasattr(parsed, 'title') and parsed.title:
            slug = parsed.title.lower().replace(' ', '_')[:50]
            return f"{group_id}_{slug}"
        else:
            return f"{group_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _episode_exists(self, name: str, group_id: str) -> bool:
        """Check if episode already exists."""
        
        results = await self.graphiti.search(
            query=name,
            group_ids=[group_id],
            num_results=1
        )
        return len(results) > 0 and name in str(results[0])
```

### Parsers

#### Feature Spec Parser

```python
# guardkit/knowledge/parsers/feature_spec_parser.py

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ParsedFeatureSpec:
    """Parsed feature specification."""
    
    entity_type: str = "feature_spec"
    id: str = ""
    title: str = ""
    description: str = ""
    
    # Requirements
    success_criteria: List[str] = field(default_factory=list)
    technical_requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    
    # Context
    dependencies: List[str] = field(default_factory=list)
    related_features: List[str] = field(default_factory=list)
    
    # Implementation hints
    implementation_notes: str = ""
    testing_strategy: str = ""
    
    # Metadata
    priority: str = ""
    estimated_complexity: int = 0
    source_file: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "technical_requirements": self.technical_requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "dependencies": self.dependencies,
            "related_features": self.related_features,
            "implementation_notes": self.implementation_notes,
            "testing_strategy": self.testing_strategy,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "source_file": self.source_file
        }


class FeatureSpecParser:
    """Parses feature specification markdown files."""
    
    def parse(self, content: str, file_path: Path) -> ParsedFeatureSpec:
        """Parse feature spec markdown into structured data."""
        
        spec = ParsedFeatureSpec()
        spec.source_file = str(file_path)
        
        # Extract ID from filename (e.g., FEAT-SKEL-001-walking-skeleton.md)
        filename = file_path.stem
        id_match = re.match(r'(FEAT-[A-Z0-9]+-\d+)', filename)
        if id_match:
            spec.id = id_match.group(1)
        
        # Parse sections
        sections = self._split_sections(content)
        
        # Title from first H1
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            spec.title = title_match.group(1).strip()
        
        # Description (first paragraph after title)
        spec.description = sections.get("_intro", "")
        
        # Success criteria
        if "success criteria" in sections:
            spec.success_criteria = self._extract_list(sections["success criteria"])
        
        # Technical requirements
        if "technical requirements" in sections:
            spec.technical_requirements = self._extract_list(sections["technical requirements"])
        
        # Acceptance criteria
        if "acceptance criteria" in sections:
            spec.acceptance_criteria = self._extract_list(sections["acceptance criteria"])
        
        # Dependencies
        if "dependencies" in sections:
            spec.dependencies = self._extract_list(sections["dependencies"])
        
        # Implementation notes
        if "implementation notes" in sections:
            spec.implementation_notes = sections["implementation notes"]
        elif "implementation" in sections:
            spec.implementation_notes = sections["implementation"]
        
        # Testing strategy
        if "testing" in sections:
            spec.testing_strategy = sections["testing"]
        elif "testing strategy" in sections:
            spec.testing_strategy = sections["testing strategy"]
        
        # Priority from frontmatter or content
        priority_match = re.search(r'priority[:\s]+(\w+)', content, re.IGNORECASE)
        if priority_match:
            spec.priority = priority_match.group(1).lower()
        
        # Complexity
        complexity_match = re.search(r'complexity[:\s]+(\d+)', content, re.IGNORECASE)
        if complexity_match:
            spec.estimated_complexity = int(complexity_match.group(1))
        
        return spec
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """Split markdown into sections by headers."""
        
        sections = {}
        current_section = "_intro"
        current_content = []
        
        for line in content.split('\n'):
            # Check for H2 or H3 headers
            header_match = re.match(r'^#{2,3}\s+(.+)$', line)
            if header_match:
                # Save previous section
                sections[current_section] = '\n'.join(current_content).strip()
                current_section = header_match.group(1).lower().strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_list(self, content: str) -> List[str]:
        """Extract list items from markdown content."""
        
        items = []
        for line in content.split('\n'):
            # Match bullet points or numbered lists
            match = re.match(r'^[\s]*[-*\d.]+\s+(.+)$', line)
            if match:
                items.append(match.group(1).strip())
        
        return items
```

#### ADR Parser

```python
# guardkit/knowledge/parsers/adr_parser.py

@dataclass
class ParsedADR:
    """Parsed Architecture Decision Record."""
    
    entity_type: str = "adr"
    id: str = ""
    title: str = ""
    status: str = ""  # proposed | accepted | deprecated | superseded
    
    # Core ADR fields
    context: str = ""
    decision: str = ""
    rationale: str = ""
    consequences: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    
    # Relationships
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    related_adrs: List[str] = field(default_factory=list)
    
    # Metadata
    date: str = ""
    source_file: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "rationale": self.rationale,
            "consequences": self.consequences,
            "alternatives_considered": self.alternatives_considered,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "related_adrs": self.related_adrs,
            "date": self.date,
            "source_file": self.source_file
        }


class ADRParser:
    """Parses ADR markdown files."""
    
    def parse(self, content: str, file_path: Path) -> ParsedADR:
        """Parse ADR markdown into structured data."""
        
        adr = ParsedADR()
        adr.source_file = str(file_path)
        
        # Extract ID from filename (e.g., ADR-001-use-fastmcp.md)
        filename = file_path.stem
        id_match = re.match(r'(ADR-\d+)', filename)
        if id_match:
            adr.id = id_match.group(1)
        
        # Parse sections (standard ADR format)
        sections = self._split_sections(content)
        
        # Title
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            adr.title = title_match.group(1).strip()
        
        # Status
        status_match = re.search(r'status[:\s]+(\w+)', content, re.IGNORECASE)
        if status_match:
            adr.status = status_match.group(1).lower()
        
        # Core sections
        adr.context = sections.get("context", "")
        adr.decision = sections.get("decision", "")
        adr.rationale = sections.get("rationale", "") or sections.get("justification", "")
        
        # Consequences
        if "consequences" in sections:
            adr.consequences = self._extract_list(sections["consequences"])
        
        # Alternatives
        if "alternatives" in sections:
            adr.alternatives_considered = self._extract_list(sections["alternatives"])
        elif "alternatives considered" in sections:
            adr.alternatives_considered = self._extract_list(sections["alternatives considered"])
        
        # Date
        date_match = re.search(r'date[:\s]+(\d{4}-\d{2}-\d{2})', content, re.IGNORECASE)
        if date_match:
            adr.date = date_match.group(1)
        
        return adr
```

---

## Success Criteria

1. **Command works for all context types** - feature, project-overview, adr, guide, domain, constraint
2. **Glob patterns supported** - Can add multiple files with `*.md`
3. **Duplicate detection** - Warns if already exists (unless --force)
4. **Structured parsing** - Extracts meaningful fields from markdown
5. **Clear feedback** - Shows success/failure for each file
6. **Queryable results** - Added content can be queried via Graphiti

---

## Implementation Tasks

| Task ID | Description | Estimate |
|---------|-------------|----------|
| TASK-GR-002A | Create CLI command structure with Click | 2h |
| TASK-GR-002B | Implement ContextIngestor class | 3h |
| TASK-GR-002C | Implement FeatureSpecParser | 2h |
| TASK-GR-002D | Implement ADRParser | 2h |
| TASK-GR-002E | Implement ProjectOverviewParser (CLAUDE.md) | 2h |
| TASK-GR-002F | Implement remaining parsers (guide, domain, constraint) | 3h |
| TASK-GR-002G | Add duplicate detection and --force handling | 1h |
| TASK-GR-002H | Add tests for parsers and ingestor | 3h |
| TASK-GR-002I | Update documentation | 1h |

**Total Estimate**: 19 hours

---

## Usage Examples

### Adding Feature Specs

```bash
# Add single feature spec
$ guardkit graphiti add-context --type feature docs/features/FEAT-SKEL-001-walking-skeleton.md
✓ Added: docs/features/FEAT-SKEL-001-walking-skeleton.md -> feature_specs_FEAT-SKEL-001

# Add all feature specs
$ guardkit graphiti add-context --type feature docs/features/FEAT-*.md
✓ Added: docs/features/FEAT-SKEL-001-walking-skeleton.md -> feature_specs_FEAT-SKEL-001
✓ Added: docs/features/FEAT-SKEL-002-video-info-tool.md -> feature_specs_FEAT-SKEL-002
✓ Added: docs/features/FEAT-SKEL-003-transcript-tool.md -> feature_specs_FEAT-SKEL-003
✓ Added: docs/features/FEAT-INT-001-insight-extraction.md -> feature_specs_FEAT-INT-001

Added 4/4 context items
```

### Updating Project Overview

```bash
# Update after editing CLAUDE.md
$ guardkit graphiti add-context --type project-overview CLAUDE.md
✗ Failed: CLAUDE.md - Already exists (use --force to update)

$ guardkit graphiti add-context --type project-overview CLAUDE.md --force
✓ Added: CLAUDE.md -> project_overview_youtube_mcp

Added 1/1 context items
```

### Verifying Added Context

```bash
# Query to verify
$ guardkit graphiti search "FEAT-SKEL-001 requirements"
Results from feature_specs:
  - FEAT-SKEL-001: Walking skeleton with basic MCP server...
    Success criteria: ping tool responds, Docker container runs...
```

---

## Integration with Existing Commands

### `/feature-plan` Integration

After FEAT-GR-003, `/feature-plan` can auto-invoke this:

```bash
# When user runs:
/feature-plan "implement FEAT-SKEL-001" --context docs/features/FEAT-SKEL-001.md

# Internally runs:
guardkit graphiti add-context --type feature docs/features/FEAT-SKEL-001.md
# Then proceeds with planning using the seeded context
```

---

## Future Enhancements

1. **YAML frontmatter support** - Parse standard frontmatter in markdown
2. **Custom parsers** - Allow user-defined parsers for project-specific formats
3. **Batch import** - `guardkit graphiti import-all` to scan and import everything
4. **Watch mode** - Auto-update when files change
