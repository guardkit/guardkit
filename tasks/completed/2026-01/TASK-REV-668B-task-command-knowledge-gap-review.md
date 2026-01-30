---
id: TASK-REV-668B
title: Review task-create and task-work to Address Implementation Knowledge Gap
status: completed
priority: high
created: 2026-01-30
updated: 2026-01-30
task_type: review
review_mode: architectural
review_depth: comprehensive
complexity: 7
tags: [task-create, task-work, knowledge-gap, library-migration, root-cause]
parent_review: TASK-GC-72AF
related_analysis: .claude/reviews/TASK-GC-72AF-stub-analysis.md
decision_required: true
review_results:
  mode: architectural
  depth: comprehensive
  score: 78
  findings_count: 4
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-REV-668B-knowledge-gap-review.md
  completed_at: 2026-01-30
---

# TASK-REV-668B: Review task-create and task-work to Address Implementation Knowledge Gap

## Problem Statement

During TASK-GC-72AF (Graphiti Core Migration), `/task-work` produced stub implementations because the AI **knew what to do conceptually but lacked concrete implementation knowledge**. The task said "migrate to graphiti-core" but didn't provide:

- `from graphiti_core import Graphiti` import statement
- Example API calls like `Graphiti.search()`
- Return types (Edge objects vs dictionaries)
- Initialization requirements

**The Root Cause**: Task descriptions tell the AI *what* to do, not *how* to call the specific library/API.

**Evidence** from the stub:
```python
async def _execute_search(self, ...):
    # In production, this would call Graphiti's search API  <-- Knew what, not how
    return []  # <-- Stub because lacked implementation details
```

## Review Objectives

1. **Analyze** how `/task-create` captures implementation requirements
2. **Analyze** how `/task-work` uses context to generate implementations
3. **Identify** gaps where library/API knowledge should be provided
4. **Recommend** enhancements to prevent stub implementations
5. **Design** a "library context" mechanism for migration tasks

## Review Scope

### Files to Review

| File | Purpose |
|------|---------|
| `installer/core/commands/task-create.md` | Task creation workflow |
| `installer/core/commands/task-work.md` | Implementation workflow |
| `.claude/commands/task-create.md` | Local task-create if different |
| `.claude/commands/task-work.md` | Local task-work if different |
| `docs/workflows/task-review-workflow.md` | Review workflow context |

### Questions to Answer

1. **Task Creation Phase**:
   - Does `/task-create` ask about library dependencies?
   - Can task descriptions include "implementation hints"?
   - Should there be a `library_context` frontmatter field?

2. **Implementation Phase**:
   - Does Phase 2 (Planning) fetch library documentation?
   - Does the MCP context7 integration provide enough API details?
   - Should `/task-work` auto-fetch library docs for migration tasks?

3. **Knowledge Sources**:
   - Can we leverage context7 MCP for library API examples?
   - Should task descriptions include code snippets?
   - Should there be a "reference implementation" field?

4. **Detection & Prevention**:
   - Should `/task-create` detect "migration" tasks and prompt for API details?
   - Should Phase 2.5 (Architectural Review) check for library knowledge?
   - Should there be a "dry run" that shows planned API calls?

## Proposed Enhancements to Evaluate

### Enhancement A: Library Context in Task Frontmatter

```yaml
---
id: TASK-XXX
title: Migrate to graphiti-core library
library_context:
  package: graphiti-core
  imports:
    - "from graphiti_core import Graphiti"
  initialization: |
    graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
    await graphiti.build_indices()
  key_methods:
    - name: search
      signature: "async def search(query: str, group_ids: List[str], num_results: int) -> List[Edge]"
      returns: "List of Edge objects with uuid, fact, name, created_at, score attributes"
    - name: add_episode
      signature: "async def add_episode(name: str, body: str, group_id: str) -> EpisodeResult"
---
```

### Enhancement B: Auto-fetch Library Docs in Phase 2

```markdown
### Phase 2.1: Library Context Gathering (NEW)

**IF** task description mentions library migration OR library_context is specified:

1. **QUERY** context7 MCP for library documentation
2. **EXTRACT** key API patterns:
   - Import statements
   - Initialization code
   - Method signatures
   - Return types
3. **INJECT** into implementation planning context

**DISPLAY** to user:
```
Library Context Gathered:
  Package: graphiti-core
  Key Methods: search(), add_episode(), build_indices()
  Documentation: [context7 snippets]

Proceed with planning? [Y/n]
```
```

### Enhancement C: Migration Task Detection in task-create

When `/task-create` detects keywords like "migrate", "switch to", "replace with":

```markdown
**DETECT** migration task indicators:
- "migrate to {library}"
- "switch from X to Y"
- "replace {old} with {new}"

**IF** migration detected:

1. **ASK** user for library context:
   - Package name
   - Key imports needed
   - Reference documentation URL (optional)

2. **AUTO-FETCH** from context7 if package name provided

3. **INCLUDE** in task frontmatter as `library_context`
```

### Enhancement D: "Show Planned API Calls" Checkpoint

Add to Phase 2.8 (Human Checkpoint):

```markdown
**DISPLAY** planned library usage:

```
Planned API Calls:
  1. graphiti = Graphiti(neo4j_uri, user, password)
  2. await graphiti.build_indices()
  3. results = await graphiti.search(query, group_ids, num_results)
  4. await graphiti.add_episode(name, body, group_id)

Do these match the library's actual API? [Y/n/Fetch docs]
```

If user selects "Fetch docs", query context7 and display API signatures.
```

## Decision Points

After review, decide:

1. **Which enhancements to implement** (A, B, C, D, combination, or alternative)
2. **Priority order** for implementation
3. **Whether to create subtasks** for each enhancement
4. **Integration with existing context7 MCP** usage

## Acceptance Criteria

- [ ] Analyzed current task-create and task-work command flows
- [ ] Identified specific gaps where library knowledge is missing
- [ ] Evaluated each proposed enhancement (A, B, C, D)
- [ ] Recommended implementation approach with rationale
- [ ] Created follow-up implementation tasks if approved
- [ ] Documented findings in review report

## Expected Outputs

1. **Review Report** at `.claude/reviews/TASK-REV-668B-knowledge-gap-review.md`
2. **Decision** on which enhancements to implement
3. **Implementation Tasks** (if [I]mplement chosen at checkpoint)

## Related Tasks

- **TASK-SD-CA08**: Stub detection quality gate (prevention mechanism)
- **TASK-GC-72AF**: Original task that exposed this issue

## Notes

This is a **root cause** analysis. TASK-SD-CA08 (stub detection) is a **symptom treatment**. Both are needed:
- Stub detection catches failures after they happen
- This review prevents failures from happening by ensuring the AI has implementation knowledge

## Complexity Assessment

- **Files to Review**: 4-6 command specifications
- **Analysis Depth**: Deep dive into workflow phases
- **Decision Complexity**: Multiple enhancement options to evaluate
- **Dependencies**: context7 MCP integration understanding

**Complexity Score**: 7/10 (comprehensive review with design decisions)
