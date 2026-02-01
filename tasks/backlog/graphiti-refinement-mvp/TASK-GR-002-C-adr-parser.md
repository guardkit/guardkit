---
id: TASK-GR-002-C
title: Implement ADRParser
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- context-addition
- parser
- adr
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 7
conductor_workspace: gr-mvp-wave7-parsers
complexity: 3
depends_on:
- TASK-GR-002-A
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:30:15.465645'
  last_updated: '2026-02-01T07:36:28.763167'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:30:15.465645'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement ADRParser

## Description

Implement a parser for Architecture Decision Records (ADR-*.md) that extracts decision information for Graphiti seeding.

## Acceptance Criteria

- [ ] Parse ADR standard format
- [ ] Extract: title, status, context, decision, consequences
- [ ] Create decision episode for Graphiti
- [ ] Handle various ADR formats
- [ ] Support ADR numbering conventions

## Implementation Notes

### Parser Implementation

```python
class ADRParser(BaseParser):
    """Parser for Architecture Decision Records."""

    @property
    def parser_type(self) -> str:
        return "adr"

    @property
    def supported_extensions(self) -> List[str]:
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this is an ADR."""
        filename = Path(file_path).name.lower()
        return (
            filename.startswith("adr-") or
            "## status" in content.lower() and
            "## context" in content.lower() and
            "## decision" in content.lower()
        )

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse ADR into episode."""
        episodes = []

        # Extract ADR sections
        title = self._extract_title(content)
        status = self._extract_section(content, "status")
        context = self._extract_section(content, "context")
        decision = self._extract_section(content, "decision")
        consequences = self._extract_section(content, "consequences")

        # Create ADR episode
        adr_content = f"""
        Architecture Decision: {title}

        Status: {status}

        Context:
        {context}

        Decision:
        {decision}

        Consequences:
        {consequences}
        """

        episode = EpisodeData(
            content=adr_content,
            group_id="project_decisions",
            entity_type="adr",
            entity_id=f"adr_{slugify(title)}",
            metadata={
                "source_path": file_path,
                "status": status,
            }
        )
        episodes.append(episode)

        return ParseResult(episodes=episodes, warnings=[], success=True)
```

### Standard ADR Format

```markdown
# ADR-001: Use Graphiti for Knowledge Storage

## Status
Accepted

## Context
We need persistent knowledge storage...

## Decision
We will use Graphiti with Neo4j...

## Consequences
- Good: Semantic search capability
- Bad: Additional infrastructure
```

### Files to Create

- `src/guardkit/integrations/graphiti/parsers/adr.py`

## Test Requirements

- [ ] Unit tests with sample ADRs
- [ ] Test section extraction
- [ ] Test various ADR formats

## Notes

Simpler than FeatureSpecParser - more standard format.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)
