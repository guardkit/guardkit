---
id: TASK-DOC-6064
title: Update GitHub Pages Documentation for Graphiti Full Doc Parser and Learnings
type: feature
priority: medium
status: completed
created: 2025-02-05
completed: 2026-02-05
tags: [documentation, graphiti, github-pages, parser]
complexity: 5
---

# Update GitHub Pages Documentation for Graphiti Full Doc Parser and Learnings

## Description

Update the MkDocs GitHub Pages documentation to reflect the new `full_doc` parser implementation (TASK-GR-FULL-DOC-PARSER) and bug fixes discovered during Graphiti integration testing. Several documentation pages contain outdated or inaccurate information about parser types, parser registration, project namespacing, and the `guardkit init` command.

## Context

During implementation and testing of the Graphiti integration, the following issues were discovered and fixed in code but the GitHub Pages documentation was not updated:

### Bug Fixes Applied (Code Already Updated)

1. **Parser type naming**: CLI help text used hyphens (`project-doc`) but actual parser types use underscores (`project_doc`). Documentation still shows hyphens in some places.
2. **Parser registration**: `ParserRegistry()` was created empty - parsers were not being registered in the `add_context` command. Fixed in `graphiti.py`.
3. **Metadata type mismatch**: `add_episode()` expected `EpisodeMetadata` object but CLI was passing plain dict. Fixed to embed metadata in content.
4. **Group ID naming**: Parser used `project-{section}` (hyphen) but search expected `project_{section}` (underscore). Fixed in `project_doc_parser.py`.
5. **Missing `.guardkit/graphiti.yaml`**: `guardkit init` (shell script) was not creating the Graphiti config file. Fixed in `init-project.sh`.

### New Feature (Code Already Implemented)

6. **Full Document Parser (`full_doc`)**: New parser that captures entire markdown document content, solving the limitation where `project_doc` only captured sections matching specific headers (purpose, tech_stack, architecture).

## Acceptance Criteria

### 1. Update Parsers Reference Page (`docs/guides/graphiti-parsers.md`)

- [ ] Add new section for Full Document Parser (`full_doc`) with:
  - Detection criteria (explicit-only, `can_parse()` returns False)
  - Episodes created (single episode or chunked for >10KB documents)
  - Group ID: `project_knowledge`
  - Entity type: `full_doc`
  - Extracted metadata (title, frontmatter, file_path, file_size)
  - Chunking behavior for large documents (splits by `##` headers)
  - Example usage with `--type full_doc`
- [ ] Fix parser type names throughout: use underscores (`project_doc`, `feature_spec`, `project_overview`) not hyphens
- [ ] Update "Project Doc Parser" section to accurately describe its behavior:
  - Only parses CLAUDE.md and README.md (not a fallback parser)
  - Creates episodes per section (purpose, tech_stack, architecture)
  - Group IDs: `project_purpose`, `project_tech_stack`, `project_architecture`
- [ ] Update Parser Selection Logic to include `full_doc` and clarify that `project_doc` is NOT a fallback
- [ ] Update parser count references (now 5 parsers, not 4)

### 2. Update Add Context Page (`docs/guides/graphiti-add-context.md`)

- [ ] Add `full_doc` to Supported Parser Types table
- [ ] Add `full_doc` usage examples:
  ```bash
  guardkit graphiti add-context docs/research/GRAPHITI-KNOWLEDGE.md --type full_doc --force
  ```
- [ ] Fix parser type values in `--type` option: use underscores
- [ ] Add section about chunking behavior for large documents
- [ ] Update Episodes Created section to include Full Doc Parser

### 3. Update CLI Commands Page (`docs/guides/graphiti-commands.md`)

- [ ] Update `add-context` supported document types to include full_doc
- [ ] Fix `--type` option values: use underscores (`project_doc`, not `project-doc`)
- [ ] Add `project_knowledge` to searchable groups list

### 4. Update Setup Guide (`docs/setup/graphiti-setup.md`)

- [ ] Document that `guardkit init` now creates `.guardkit/graphiti.yaml`
- [ ] Document the `project_id` field and its purpose (namespace prefixing)
- [ ] Add troubleshooting section for missing `.guardkit/graphiti.yaml`
- [ ] Document how project_id is auto-generated from directory name

### 5. Update Integration Guide (`docs/guides/graphiti-integration-guide.md`)

- [ ] Add full_doc parser to parser overview section
- [ ] Update any parser type references to use underscores
- [ ] Add mention of project_knowledge search group

### 6. Cross-Check All Graphiti Documentation

- [ ] Search all docs for `project-doc`, `feature-spec`, `project-overview` (with hyphens) and update to underscores where referring to parser type identifiers
- [ ] Verify group ID references use underscores consistently
- [ ] Ensure parser count is correct (5 parsers) throughout all pages

## Implementation Notes

### Key Documentation Files to Update

| File | Changes |
|------|---------|
| `docs/guides/graphiti-parsers.md` | Add full_doc section, fix parser types, fix project_doc description |
| `docs/guides/graphiti-add-context.md` | Add full_doc examples, fix --type values |
| `docs/guides/graphiti-commands.md` | Add full_doc to supported types, fix --type values |
| `docs/setup/graphiti-setup.md` | Document .guardkit/graphiti.yaml creation |
| `docs/guides/graphiti-integration-guide.md` | Add full_doc mentions, fix parser types |
| `docs/guides/graphiti-project-namespaces.md` | Verify group naming consistency |
| `docs/deep-dives/graphiti/context-addition.md` | Add full_doc parser details |
| `docs/architecture/graphiti-architecture.md` | Update parser architecture section |

### Parser Type Reference (Correct Values)

| Parser | Type Identifier | Use with `--type` |
|--------|----------------|-------------------|
| ADR | `adr` | `--type adr` |
| Feature Spec | `feature_spec` | `--type feature_spec` |
| Project Overview | `project_overview` | `--type project_overview` |
| Project Doc | `project_doc` | `--type project_doc` |
| Full Document | `full_doc` | `--type full_doc` |

### Full Doc Parser Details

```python
class FullDocParser(BaseParser):
    parser_type = "full_doc"
    supported_extensions = [".md", ".markdown"]

    # Explicit-only: can_parse() returns False
    # Must use --type full_doc

    # Creates episodes:
    # - Single episode for docs <= chunk_threshold (default 10KB)
    # - Multiple episodes (chunked by ## headers) for larger docs

    # Group ID: "project_knowledge"
    # Entity type: "full_doc"
```

### Naming Convention Clarification

The documentation should be clear about the difference:
- **Parser type identifiers** (used with `--type`): Use underscores (`full_doc`, `project_doc`)
- **CLI display names**: Can use more readable names in help text
- **Group IDs**: Use underscores (`project_knowledge`, `project_purpose`)

## Testing Requirements

- [ ] Build docs locally with `mkdocs serve` and verify all pages render
- [ ] Verify all internal links between updated pages still work
- [ ] Check that new full_doc parser section appears in Knowledge Graph > Reference > Parsers
- [ ] Verify search finds "full_doc" and "full document parser" content

## Related

- `TASK-GR-FULL-DOC-PARSER` - Implementation of the full document parser (COMPLETED)
- Previous session bug fixes to `graphiti.py`, `project_doc_parser.py`, `init-project.sh`
- MkDocs config: `mkdocs.yml`
- GitHub Pages deployment: `.github/workflows/docs.yml`
