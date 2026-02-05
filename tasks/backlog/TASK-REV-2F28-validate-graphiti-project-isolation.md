---
id: TASK-REV-2F28
title: Validate Graphiti project isolation for repo migration
status: review_complete
created: 2026-02-04T15:00:00Z
updated: 2026-02-04T16:45:00Z
priority: normal
tags: [graphiti, knowledge-graph, data-migration, review]
task_type: review
complexity: 3
decision_required: true
review_results:
  mode: architectural
  depth: quick
  score: 72
  findings_count: 6
  recommendations_count: 4
  decision: configure_explicit_id
  report_path: .claude/reviews/TASK-REV-2F28-graphiti-isolation-review.md
  completed_at: 2026-02-04T16:30:00Z
implementation_task: TASK-GR-PID-001
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Validate Graphiti project isolation for repo migration

## Context

Working on YouTube Transcript MCP project at:
- Current: https://github.com/RichWoollcott/youtube-transcript-mcp
- Potential migration: https://github.com/guardkit/guardkit-examples

Need to validate that Graphiti data is stored with project identifiers such that moving repositories won't cause issues with the knowledge graph data in Neo4j.

## Review Objectives

1. **Analyze current project isolation mechanism** - How does Graphiti namespace project data?
2. **Identify potential migration risks** - What could break if repo is moved/renamed?
3. **Document safe migration procedure** - If issues exist, how to mitigate?
4. **Validate dual-use viability** - Can project serve both personal and example purposes?

## Files to Analyze

- `guardkit/knowledge/graphiti_client.py` - Core client with project prefixing
- `guardkit/integrations/graphiti/project.py` - Project namespace management
- `guardkit/knowledge/project_seeding.py` - How knowledge is seeded with project context
- `/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp/docs/research/GRAPHITI-KNOWLEDGE.md` - Current knowledge captured

## Questions to Answer

1. **How are group_ids constructed?**
   - Are they prefixed with project name?
   - What happens if project name changes?

2. **What is the source of project name?**
   - Is it derived from directory name (mutable)?
   - Is it stored in config (portable)?
   - Can it be overridden explicitly?

3. **Can knowledge be migrated?**
   - Is there a mechanism to update project prefixes?
   - Would data need to be re-seeded after migration?

4. **What's the recommended approach?**
   - Migrate before seeding significant knowledge?
   - Set explicit project_id in config to decouple from directory?
   - Accept re-seeding as acceptable overhead?

## Acceptance Criteria

- [ ] Document how project isolation currently works (group_id prefixing)
- [ ] Identify what happens when repository/directory name changes
- [ ] Provide clear recommendation for youtube-transcript-mcp migration
- [ ] If issues exist, document mitigation steps

## Related Resources

- Feature specs: `/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp/docs/features/`
- Walking skeleton plan: `/Users/richardwoollcott/Projects/appmilla_github/youtube-transcript-mcp/tasks/backlog/walking-skeleton/`
- First feature planned via `/feature-plan`: FEAT-SKEL-001

## Decision Options

After review, decide between:

1. **[M]igrate Early** - Move to guardkit-examples before significant knowledge seeding
2. **[C]onfigure Explicit ID** - Set project_id in config to decouple from directory name
3. **[A]ccept Re-seeding** - Move when ready, re-seed knowledge as needed
4. **[N]o Action Needed** - If isolation mechanism is already robust enough

## Implementation Notes

### Review Completed: 2026-02-04

**Decision**: [C]onfigure Explicit ID

**Findings Summary**:
1. Project isolation uses `{project_id}__{group_name}` pattern
2. `project_id` defaults to directory name via `get_current_project_name()`
3. Moving/renaming directory orphans all project-scoped knowledge
4. Config already supports `project_id` field, but it's not wired up properly
5. `_get_client_and_config()` in CLI doesn't pass `settings.project_id` to GraphitiConfig

**Implementation Task Created**: TASK-GR-PID-001
- Always use explicit `project_id` from `.guardkit/graphiti.yaml`
- Set during `guardkit init` (one-time detection from directory)
- Survives repo moves/clones
- No confusing questions for users

**Report**: [.claude/reviews/TASK-REV-2F28-graphiti-isolation-review.md](../../.claude/reviews/TASK-REV-2F28-graphiti-isolation-review.md)
