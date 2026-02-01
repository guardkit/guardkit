---
id: TASK-GR-002-I
title: Documentation for context addition
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: medium
tags:
- graphiti
- context-addition
- documentation
- mvp-phase-2
task_type: documentation
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: direct
wave: 9
conductor_workspace: gr-mvp-wave9-docs
complexity: 3
depends_on:
- TASK-GR-002-F
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T08:07:04.706426'
  last_updated: '2026-02-01T08:14:21.695736'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T08:07:04.706426'
    player_summary: 'Created comprehensive documentation for the Graphiti context
      addition feature. This includes: 1) Command reference guide (graphiti-add-context.md)
      with all CLI options, examples, and use cases. 2) Parser reference guide (graphiti-parsers.md)
      documenting all available parsers (ADR, feature-spec, project-overview, project-doc)
      with detection criteria and metadata extraction details. 3) Deep-dive architecture
      guide (context-addition.md) covering system architecture, parser implementation,
      episode g'
    player_success: true
    coach_success: true
---

# Task: Documentation for context addition

## Description

Create comprehensive documentation for the context addition feature, including command usage, parser documentation, and best practices.

## Acceptance Criteria

- [ ] Command reference documentation
- [ ] Parser type documentation
- [ ] Usage examples
- [ ] Best practices guide
- [ ] Troubleshooting section

## Implementation Notes

### Documentation Files

```
docs/
├── guides/
│   ├── graphiti-add-context.md    # New - command guide
│   └── graphiti-parsers.md        # New - parser reference
└── deep-dives/
    └── graphiti/
        └── context-addition.md    # New - detailed guide
```

### Command Reference Content

```markdown
# guardkit graphiti add-context

Add context to Graphiti from files or directories.

## Usage

\`\`\`bash
guardkit graphiti add-context [OPTIONS] <PATH>
\`\`\`

## Arguments

| Argument | Description |
|----------|-------------|
| PATH | File or directory to add |

## Options

| Option | Description | Default |
|--------|-------------|---------|
| --type TEXT | Force parser type | Auto-detect |
| --force | Overwrite existing context | false |
| --dry-run | Preview without changes | false |
| --pattern TEXT | Glob pattern for directories | **/*.md |
| --verbose | Detailed output | false |
| --quiet | Minimal output | false |

## Examples

\`\`\`bash
# Add a feature spec
guardkit graphiti add-context docs/feature-spec-auth.md

# Add all ADRs
guardkit graphiti add-context docs/adr/ --pattern "ADR-*.md"

# Preview what would be added
guardkit graphiti add-context . --dry-run

# Force specific parser
guardkit graphiti add-context custom.md --type project-overview
\`\`\`
```

### Parser Reference Content

```markdown
# Graphiti Parsers

## Available Parsers

### feature-spec
Parses feature specification documents.
- File pattern: `FEATURE-SPEC-*.md`, `*-feature-spec.md`
- Extracts: Feature name, tasks, phases, dependencies

### adr
Parses Architecture Decision Records.
- File pattern: `ADR-*.md`
- Extracts: Title, status, context, decision, consequences

### project-overview
Parses project overview documents.
- File pattern: `CLAUDE.md`, `README.md`
- Extracts: Purpose, tech stack, architecture
```

### Files to Create

- `docs/guides/graphiti-add-context.md`
- `docs/guides/graphiti-parsers.md`
- `docs/deep-dives/graphiti/context-addition.md`

## Test Requirements

- [ ] N/A - documentation task

## Notes

Final task in MVP - ensures feature is documented.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
