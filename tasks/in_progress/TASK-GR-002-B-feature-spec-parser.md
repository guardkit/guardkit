---
complexity: 4
conductor_workspace: gr-mvp-wave7-parsers
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-002-A
feature_id: FEAT-GR-MVP
id: TASK-GR-002-B
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- context-addition
- parser
- feature-spec
- mvp-phase-2
task_type: feature
title: Implement FeatureSpecParser
updated: 2026-02-01 00:00:00+00:00
wave: 7
---

# Task: Implement FeatureSpecParser

## Description

Implement a parser for feature specification files (FEATURE-SPEC-*.md) that extracts structured information for Graphiti seeding.

## Acceptance Criteria

- [x] Parse feature spec frontmatter
- [x] Extract: feature name, description, tasks, dependencies
- [x] Create episodes for feature overview and tasks
- [x] Handle various feature spec formats
- [x] Provide helpful errors for malformed specs

## Implementation Notes

### Parser Implementation

```python
class FeatureSpecParser(BaseParser):
    """Parser for feature specification files."""

    @property
    def parser_type(self) -> str:
        return "feature-spec"

    @property
    def supported_extensions(self) -> List[str]:
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this is a feature spec."""
        filename = Path(file_path).name.lower()
        return filename.startswith("feature-spec") or "feature spec" in content.lower()[:500]

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse feature spec into episodes."""
        episodes = []
        warnings = []

        # 1. Parse frontmatter
        try:
            frontmatter, body = self._parse_frontmatter(content)
        except Exception as e:
            return ParseResult(episodes=[], warnings=[str(e)], success=False)

        # 2. Extract feature overview
        feature_name = frontmatter.get("name", self._extract_title(body))
        overview_episode = EpisodeData(
            content=self._create_overview_content(frontmatter, body),
            group_id="feature_specs",
            entity_type="feature_spec",
            entity_id=f"feature_{slugify(feature_name)}",
            metadata={"source_path": file_path}
        )
        episodes.append(overview_episode)

        # 3. Extract tasks if present
        tasks = self._extract_tasks(body)
        for task in tasks:
            task_episode = EpisodeData(
                content=self._create_task_content(task),
                group_id="feature_specs",
                entity_type="feature_task",
                entity_id=f"task_{task['id']}",
                metadata={"parent_feature": feature_name}
            )
            episodes.append(task_episode)

        return ParseResult(episodes=episodes, warnings=warnings, success=True)
```

### Expected Frontmatter

```yaml
---
name: Graphiti Refinement MVP
status: ready
reviewed: TASK-REV-1505
architecture_score: 78
phases:
  - name: Phase 0
    tasks: [PRE-000-A, PRE-000-B, PRE-000-C]
---
```

### Files to Create

- `src/guardkit/integrations/graphiti/parsers/feature_spec.py`

## Test Requirements

- [x] Unit tests with sample feature specs
- [x] Test frontmatter parsing
- [x] Test task extraction
- [x] Test malformed spec handling

## Notes

Most complex parser - feature specs have rich structure.

## References

- [FEAT-GR-002 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-002-context-addition-command.md)