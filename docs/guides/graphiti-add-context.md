# guardkit graphiti add-context

Add context to Graphiti from markdown files or directories.

## Overview

The `guardkit graphiti add-context` command adds content from markdown files to the Graphiti knowledge graph. It uses specialized parsers to extract structured information from different document types (ADRs, feature specs, project overviews) and creates episodes that can be semantically searched.

## Usage

```bash
guardkit graphiti add-context [OPTIONS] <PATH>
```

## Arguments

| Argument | Description |
|----------|-------------|
| PATH | File or directory to add (required) |

## Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--type TEXT` | | Force specific parser type | Auto-detect |
| `--force` | `-f` | Overwrite existing context | false |
| `--dry-run` | | Preview without making changes | false |
| `--pattern TEXT` | | Glob pattern for directories | `**/*.md` |
| `--verbose` | `-v` | Show detailed processing output | false |
| `--quiet` | `-q` | Suppress non-error output | false |

**Note**: `--verbose` and `--quiet` are mutually exclusive.

## Examples

### Add a Single File

```bash
# Add an Architecture Decision Record
guardkit graphiti add-context docs/architecture/ADR-001-use-graphiti.md

# Add a feature specification
guardkit graphiti add-context docs/features/FEATURE-SPEC-authentication.md

# Add project overview
guardkit graphiti add-context CLAUDE.md
```

### Add Multiple Files from Directory

```bash
# Add all markdown files in directory (recursive)
guardkit graphiti add-context docs/architecture/

# Add only ADR files
guardkit graphiti add-context docs/ --pattern "ADR-*.md"

# Add all feature specs
guardkit graphiti add-context docs/ --pattern "**/FEATURE-SPEC-*.md"
```

### Force Specific Parser

```bash
# Treat file as ADR even if filename doesn't match pattern
guardkit graphiti add-context custom-decision.md --type adr

# Force project_overview parser
guardkit graphiti add-context overview.md --type project_overview

# Force feature-spec parser
guardkit graphiti add-context spec.md --type feature-spec

# Capture entire document with full_doc parser
guardkit graphiti add-context docs/research/GRAPHITI-KNOWLEDGE.md --type full_doc

# Capture and overwrite existing
guardkit graphiti add-context docs/design/overview.md --type full_doc --force
```

### Preview Mode (Dry Run)

```bash
# See what would be added without actually adding
guardkit graphiti add-context docs/ --dry-run

# Dry run with verbose output to see all episodes
guardkit graphiti add-context docs/ --dry-run --verbose
```

### Verbose Output

```bash
# Show detailed parsing information
guardkit graphiti add-context docs/ --verbose

# Output includes:
# - Which parser is used for each file
# - Number of episodes extracted
# - Episode IDs and types
# - Warnings and errors
```

### Quiet Mode

```bash
# Suppress all output except errors (for automation)
guardkit graphiti add-context docs/ --quiet

# Shows only:
# - Fatal errors
# - Warnings (always shown even in quiet mode)
```

### Overwrite Existing Content

```bash
# Update existing episodes with new content
guardkit graphiti add-context docs/ADR-001.md --force

# Useful when:
# - ADR status changed (Proposed → Accepted)
# - Feature spec updated with new tasks
# - Project overview modified
```

## Output

### Standard Output

```
Graphiti Add Context

Connected to Graphiti

  ✓ docs/architecture/ADR-001.md (adr)
  ✓ docs/features/FEATURE-SPEC-auth.md (feature-spec)
  ✓ CLAUDE.md (project_overview)

Summary:
  Added 3 files, 8 episodes
```

### Verbose Output

```
Graphiti Add Context

Connected to Graphiti

Parsing docs/architecture/ADR-001.md with adr
  Found 1 episodes
    - ADR-001 (adr)
  ✓ docs/architecture/ADR-001.md (adr)

Parsing docs/features/FEATURE-SPEC-auth.md with feature-spec
  Found 5 episodes
    - FEATURE-SPEC-auth (feature-spec)
    - TASK-AUTH-001 (task)
    - TASK-AUTH-002 (task)
    - TASK-AUTH-003 (task)
    - TASK-AUTH-004 (task)
  ✓ docs/features/FEATURE-SPEC-auth.md (feature-spec)

Summary:
  Added 2 files, 6 episodes
```

### Dry Run Output

```
Graphiti Add Context

Connected to Graphiti

  ✓ docs/architecture/ADR-001.md (adr)
  ✓ docs/features/FEATURE-SPEC-auth.md (feature-spec)

Dry run complete - Would add:
  2 files, 6 episodes
```

### Warnings and Errors

```
Warnings:
  Warning: docs/incomplete.md: Missing required section 'Decision'

Errors:
  Error: docs/invalid.md: Parse failed
```

## Parser Auto-Detection

The command automatically detects the appropriate parser based on:

1. **Filename patterns** (primary):
   - `ADR-*.md` → ADR parser
   - `FEATURE-SPEC-*.md`, `*-feature-spec.md` → Feature spec parser
   - `CLAUDE.md`, `README.md` → Project overview parser or Project doc parser

2. **Content structure** (fallback):
   - Presence of ADR sections (Status, Context, Decision)
   - Feature spec structure (Tasks, Phases, Dependencies)
   - Project overview markers

3. **No fallback**: Files that don't match any parser are skipped with a warning.

**Note**: The `full_doc` parser is never auto-detected. Use `--type full_doc` to capture general markdown files.

Use `--type` to override auto-detection.

## Supported Parser Types

| Type | Description | Auto-Detect | Use `--type` |
|------|-------------|-------------|--------------|
| `adr` | Architecture Decision Records | Yes | `--type adr` |
| `feature-spec` | Feature specifications | Yes | `--type feature-spec` |
| `project_overview` | Project overview documents | Yes | `--type project_overview` |
| `project_doc` | Section extraction from CLAUDE.md/README.md | Yes | `--type project_doc` |
| `full_doc` | Full document capture (entire markdown content) | **No** (explicit only) | `--type full_doc` |

**Note**: The `full_doc` parser is explicit-only and will never be auto-detected. You must specify `--type full_doc` to use it.

For detailed parser information, see [Graphiti Parsers Guide](graphiti-parsers.md).

## Episodes Created

The command creates episodes in Graphiti based on the parser type:

### ADR Parser
- **1 episode per ADR**: Complete decision record
- **Group ID**: `{project}__project_decisions`
- **Entity Type**: `adr`
- **Metadata**: Title, status, decision date

### Feature Spec Parser
- **1 episode for spec**: Feature overview
- **1 episode per task**: Individual task details
- **Group ID**: `{project}__feature_specs`
- **Entity Types**: `feature-spec`, `task`
- **Metadata**: Dependencies, priorities, phases

### Project Overview Parser
- **1-2 episodes**: Project overview + architecture (if rich)
- **Group IDs**: `{project}__project_overview`, `{project}__project_architecture`
- **Entity Types**: `project`, `architecture`
- **Metadata**: Tech stack, architecture, purpose

### Project Doc Parser
- **Multiple episodes per document**: One per recognized section (purpose, tech_stack, architecture)
- **Group IDs**: `{project}__project_purpose`, `{project}__project_tech_stack`, `{project}__project_architecture`
- **Entity Type**: `project_doc`
- **Only parses**: CLAUDE.md and README.md

### Full Document Parser
- **1 episode** for documents < 10KB, **multiple episodes** for larger documents (chunked by `##` headers)
- **Group ID**: `{project}__project_knowledge`
- **Entity Type**: `full_doc`
- **Metadata**: File path, file size, title, frontmatter, chunk information
- **Explicit only**: Must use `--type full_doc`

#### Chunking Behavior

Documents larger than 10KB are automatically split by `##` (h2) headers:

- Content before the first `##` becomes an "Introduction" chunk
- Each `##` section becomes a separate episode
- If no `##` headers exist, the document remains a single episode
- Chunk metadata includes `chunk_index`, `chunk_total`, and `chunk_title`

```bash
# Example: Large research document gets chunked
guardkit graphiti add-context docs/research/GRAPHITI-KNOWLEDGE.md --type full_doc --verbose

# Output:
#   Large document (15360 bytes) split into 4 chunks
#   ✓ docs/research/GRAPHITI-KNOWLEDGE.md (full_doc) - 4 episodes
```

## When to Use add-context

### Initial Project Setup
Add core project documentation to Graphiti:

```bash
# Add project overview
guardkit graphiti add-context CLAUDE.md

# Add all architecture decisions
guardkit graphiti add-context docs/architecture/ --pattern "ADR-*.md"

# Add all feature specs
guardkit graphiti add-context docs/features/ --pattern "FEATURE-SPEC-*.md"
```

### After Creating New Documentation
Add newly created docs:

```bash
# New ADR
guardkit graphiti add-context docs/architecture/ADR-042-use-redis.md

# New feature spec
guardkit graphiti add-context docs/features/FEATURE-SPEC-notifications.md
```

### After Updating Documentation
Update existing episodes with new content:

```bash
# ADR status changed (Proposed → Accepted)
guardkit graphiti add-context docs/architecture/ADR-023.md --force

# Feature spec updated with new tasks
guardkit graphiti add-context docs/features/FEATURE-SPEC-auth.md --force
```

### Bulk Operations
Add multiple documents at once:

```bash
# All documentation
guardkit graphiti add-context docs/

# Only architecture docs
guardkit graphiti add-context docs/architecture/

# Specific pattern
guardkit graphiti add-context docs/ --pattern "**/design-*.md"
```

## Best Practices

### 1. Preview First with --dry-run
Always preview before bulk operations:

```bash
guardkit graphiti add-context docs/ --dry-run
```

### 2. Use Specific Patterns
Narrow down to specific file types:

```bash
# Better
guardkit graphiti add-context docs/ --pattern "ADR-*.md"

# Instead of
guardkit graphiti add-context docs/
```

### 3. Use --force for Updates
When updating existing content, use `--force`:

```bash
guardkit graphiti add-context docs/ADR-001.md --force
```

### 4. Verify After Adding
Check that episodes were created:

```bash
guardkit graphiti add-context docs/ADR-001.md
guardkit graphiti verify --verbose
```

### 5. Use --verbose for Debugging
When troubleshooting parser detection:

```bash
guardkit graphiti add-context docs/ --verbose
```

### 6. Group Related Additions
Add related documents together:

```bash
# Add all ADRs
guardkit graphiti add-context docs/architecture/ --pattern "ADR-*.md"

# Then add all feature specs
guardkit graphiti add-context docs/features/ --pattern "FEATURE-SPEC-*.md"
```

## Troubleshooting

### File Not Detected by Parser

**Symptom**: "No parser found for: file.md (unsupported)"

**Solution**:
```bash
# Check file content structure
cat file.md

# Force specific parser
guardkit graphiti add-context file.md --type adr

# Or rename file to match pattern
mv file.md ADR-042-file.md
```

### Parse Failed

**Symptom**: "Error: file.md: Parse failed"

**Solution**:
```bash
# Use verbose to see detailed error
guardkit graphiti add-context file.md --verbose

# Check for required sections (ADR: Status, Context, Decision)
# Check for valid YAML frontmatter
```

### No Files Found

**Symptom**: "No files found matching pattern"

**Solution**:
```bash
# Check pattern syntax (glob patterns)
guardkit graphiti add-context docs/ --pattern "*.md"  # Only in docs/
guardkit graphiti add-context docs/ --pattern "**/*.md"  # Recursive

# Verify files exist
ls docs/*.md
```

### Connection Failed

**Symptom**: "Graphiti connection failed or disabled"

**Solution**:
```bash
# Check Graphiti status
guardkit graphiti status

# Verify Neo4j is running
docker ps | grep neo4j

# Check configuration
cat ~/.guardkit/config.yaml
```

### Episodes Not Searchable

**Symptom**: Episodes added but not found in searches

**Solution**:
```bash
# Wait for Graphiti indexing (can take 1-2 minutes)

# Verify episodes exist
guardkit graphiti verify --verbose

# Check group IDs in search queries
```

## Advanced Usage

### Custom Glob Patterns

```bash
# All markdown in specific subdirectories
guardkit graphiti add-context docs/ --pattern "{architecture,features}/**/*.md"

# Exclude certain files
guardkit graphiti add-context docs/ --pattern "**/!(README).md"

# Multiple patterns (run separately)
guardkit graphiti add-context docs/ --pattern "ADR-*.md"
guardkit graphiti add-context docs/ --pattern "FEATURE-*.md"
```

### Automation Scripts

```bash
#!/bin/bash
# add-all-docs.sh

# Preview first
guardkit graphiti add-context docs/ --dry-run

# If preview looks good, add
if [ $? -eq 0 ]; then
  guardkit graphiti add-context docs/ --quiet
  echo "Documentation added to Graphiti"
fi
```

### CI/CD Integration

```yaml
# .github/workflows/update-graphiti.yml
name: Update Graphiti

on:
  push:
    paths:
      - 'docs/**/*.md'

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Add changed docs to Graphiti
        run: |
          guardkit graphiti add-context docs/ --force --quiet
```

## See Also

- [Graphiti Parsers Guide](graphiti-parsers.md) - Detailed parser documentation
- [Graphiti Commands Guide](graphiti-commands.md) - All Graphiti CLI commands
- [Context Addition Deep-Dive](../deep-dives/graphiti/context-addition.md) - Architecture and implementation details
- [Graphiti Integration Guide](graphiti-integration-guide.md) - Overall integration architecture
